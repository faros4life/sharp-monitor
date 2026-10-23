#!/usr/bin/env python3
"""
Auto-placement executor - DRY RUN (Oct 23, 2026 spec). THIS FILE CONTAINS NO ORDER CODE: it cannot place, change
or cancel anything on any exchange. It reads Muse's AUTO-PLACE VERDICTS emails, runs every skip check, prices all 4
books after fees, sizes the stake, and emails what it WOULD have placed.

Verdict email (from Muse, to the Bets address): subject contains "AUTO-PLACE VERDICTS"; body holds a JSON array of
plays. Each play needs: play_key, sport, game ("Away @ Home", as in alerts.json), bet (alert text as in alerts.json,
e.g. "Oklahoma City Thunder -8.5 (-108)"), start_utc. Optional: late (bool).

Public repo: the Actions log prints counts only. Everything else goes by email.
"""
import email
import hashlib
import imaplib
import json
import os
import re
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import book_check as bc
import liquidity_monitor as lm

UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")          # + money: risk UNIT; - money: risk to win UNIT
MIN_LEAD_MIN = float(os.environ.get("EXEC_MIN_LEAD_MIN", "") or "60")
CAP_LINE = -130                                                  # spreads/totals: never worse than -130
PMUS = "https://gateway.polymarket.us"
PMUS_FEE = 0.0695                                                # Polymarket US taker: 0.0695 x C x p x (1-p)
PMUS_LEAGUES = {"NFL": ["nfl"], "NBA": ["nba"], "NHL": ["nhl"], "MLB": ["mlb"], "NCAAF": ["cfb", "ncaaf", "college-football"],
                "NCAAB": ["cbb", "ncaab", "college-basketball"]}
BANNED_SPORTS = {"UFC", "MMA", "BOXING", "TENNIS", "ATP", "WTA", "SOCCER", "EPL", "MLS", "LA LIGA", "SERIE A",
                 "BUNDESLIGA", "LIGUE 1", "LIGA MX", "UCL"}
BANNED_WORDS = ("parlay", "1h", "1q", "first half", "1st half", "first quarter", "1st quarter", "home run", " hr ")
BOOKS = ("novig", "prophetx", "kalshi", "polymarket_us")
LOG = []   # counts only for the public log


def gmail():
    user = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("EMAIL_TO", "").strip() or user
    if not (user and pw):
        raise SystemExit("Email not configured.")
    return user, pw, to


# ---------------------------------------------------------------- verdicts in, dedupe
def pid(play_key):
    return "xpid" + hashlib.sha1(play_key.encode()).hexdigest()[:12]


def imap_open():
    user, pw, _ = gmail()
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(user, pw)
    M.select('"[Gmail]/All Mail"', readonly=True)
    return M


def gsearch(M, query):
    typ, data = M.uid("SEARCH", "X-GM-RAW", '"' + query.replace('"', '') + '"')
    return (data[0].split() if typ == "OK" and data and data[0] else [])


def body_text(raw):
    msg = email.message_from_bytes(raw)
    parts = msg.walk() if msg.is_multipart() else [msg]
    for p in parts:
        if p.get_content_type() == "text/plain":
            return p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="ignore")
    return ""


def read_verdicts(M):
    plays = []
    for uid in gsearch(M, "subject:AUTO-PLACE VERDICTS newer_than:2d"):
        typ, data = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            continue
        txt = body_text(data[0][1])
        i, j = txt.find("["), txt.rfind("]")
        if i < 0 or j <= i:
            continue
        try:
            arr = json.loads(txt[i:j + 1])
        except Exception:
            LOG.append("verdict email with unreadable JSON")
            continue
        for p in arr if isinstance(arr, list) else []:
            if isinstance(p, dict) and p.get("play_key"):
                plays.append(p)
    seen, out = set(), []
    for p in plays:
        if p["play_key"] not in seen:
            seen.add(p["play_key"])
            out.append(p)
    return out


def already_handled(M, p):
    return bool(gsearch(M, pid(p["play_key"])))


# ---------------------------------------------------------------- Polymarket US (public gateway, no key)
_PMUS = {}


def pmus_events(sport):
    if sport not in _PMUS:
        evs = []
        for slug in PMUS_LEAGUES.get(sport, []):
            try:
                d = lm.get(f"{PMUS}/v2/leagues/{slug}/events", {"limit": 200})
                evs = d.get("events") or []
                if evs:
                    break
            except Exception:
                continue
        _PMUS[sport] = evs
    return _PMUS[sport]


def pmus_type(mk):
    smt = (mk.get("sportsMarketType") or mk.get("sportsMarketTypeV2") or mk.get("marketType") or "").lower()
    if "spread" in smt or "handicap" in smt:
        return "spread"
    if "total" in smt or "over_under" in smt:
        return "total"
    if "winner" in smt or "money" in smt:
        return "moneyline"
    return None


def pmus_game_markets(ev, markets):
    """All markets of one game: by gameId (from the listed winner market or the event), else by event id."""
    gid = next((m.get("gameId") for m in markets if m.get("gameId")), None) or ev.get("gameId")
    tries = []
    if gid:
        tries.append(("gameId", f"{PMUS}/v1/markets", {"gameId": gid, "limit": 100}))
    if ev.get("slug"):
        tries.append(("event slug", f"{PMUS}/v1/events/slug/{ev['slug']}", None))
        tries.append(("events?slug", f"{PMUS}/v1/events", {"slug": ev["slug"]}))
    if ev.get("id"):
        tries.append(("events?id", f"{PMUS}/v1/events", {"id": ev["id"]}))
    for how, url, params in tries:
        try:
            d = lm.get(url, params)
        except Exception as ex:
            _PMUS["how"] = f"{how}: {str(ex)[:40]}"
            continue
        mks = d.get("markets") if isinstance(d, dict) else d
        if isinstance(d, dict) and not mks:
            mks = (d.get("event") or {}).get("markets")
        if isinstance(d, dict) and not mks and d.get("events"):
            mks = [m for e in d["events"] for m in (e.get("markets") or [])]
        if mks:
            _PMUS["how"] = f"{how}: {len(mks)} markets"
            return [m for m in mks if isinstance(m, dict)]
        _PMUS["how"] = f"{how}: none"
    return []


def pmus_check(al, mtype, side, line, price, teams):
    st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    arow = {"league": al["sport"], "date": st.astimezone(lm.ET).date().isoformat(), "teams": list(teams)}
    for ev in pmus_events(al["sport"]):
        names = [t.get("name") for t in (ev.get("teams") or []) if t.get("name")]
        et = tuple(names[:2]) if len(names) >= 2 else lm.split_teams(ev.get("title") or "")
        when = ev.get("startTime") or ev.get("startDate") or ev.get("eventDate")
        try:
            d = datetime.fromisoformat(str(when).replace("Z", "+00:00")).astimezone(lm.ET).date().isoformat()
        except Exception:
            d = arow["date"]
        if not et or not lm.same_game(arow, {"league": al["sport"], "date": d, "teams": list(et)}):
            continue
        cands = []
        markets = list(ev.get("markets") or [])
        if mtype != "moneyline":   # league listing carries the winner market only: fetch this game's other markets
            markets += pmus_game_markets(ev, markets)
        for mk in markets:
            mt = pmus_type(mk)
            if mt != mtype or not mk.get("slug"):
                continue
            for s in mk.get("marketSides") or []:
                desc = (s.get("description") or s.get("identifier") or "")
                if mtype == "total":
                    ok = ("over" in desc.lower() and side == "OVER") or ("under" in desc.lower() and side == "UNDER")
                else:
                    t = lm.team_side(desc, list(teams), al["sport"])
                    ok = t == side
                if ok:
                    ln = lm.num(mk.get("line"))
                    sline = ln if (mtype != "spread" or s.get("long") is not False) else (-ln if ln is not None else None)
                    cands.append((mk, bool(s.get("long", True)), sline))
        if not cands:
            seen = [f"{mk.get('sportsMarketType') or mk.get('marketType')} line={mk.get('line')} sides="
                    + "/".join(f"{s.get('description') or s.get('identifier')}({'L' if s.get('long') else 'S'})"
                               for s in mk.get("marketSides") or []) for mk in markets[:8]]
            seen.append(f"fetch: {_PMUS.get('how', '-')}")
            return {"status": "market_not_on_polymarket_us", "seen": seen}
        mk, is_long, pline = (cands[0] if line is None else
                              min(cands, key=lambda c: abs((c[2] if c[2] is not None else 1e9) - line)))
        book = (lm.get(f"{PMUS}/v1/markets/{mk['slug']}/book") or {}).get("marketData") or {}
        def px(x):
            v = x.get("px")
            return lm.num(v.get("value") if isinstance(v, dict) else v)
        if is_long:   # buy YES = take offers
            levels = [(px(o), px(o) * lm.num(o.get("qty"))) for o in book.get("offers") or [] if px(o) is not None]
        else:         # buy NO = sell YES into bids: cost 1 - bid
            levels = [(round(1 - px(b), 4), (1 - px(b)) * lm.num(b.get("qty"))) for b in book.get("bids") or [] if px(b) is not None]
        return bc.ladder_result(levels, price, line, pline, {"market_slug": mk["slug"], "long_side": is_long}, PMUS_FEE)
    return {"status": "game_not_on_polymarket_us",
            "seen": [ev.get("title") for ev in pmus_events(al["sport"])[:0]] or [f"{len(pmus_events(al['sport']))} {al['sport']} events listed"]}


# ---------------------------------------------------------------- Novig positions (read-only key) for dedupe/conflict
def novig_positions():
    try:
        import novig_signed as nv
        if not nv.ready():
            return None
        d = nv.get("/v3/portfolio/positions", {"keyId": nv._S["id"]})
        out = []
        for v in (d.values() if isinstance(d, dict) else [d]):
            out += v if isinstance(v, list) else (v.get("items") or [] if isinstance(v, dict) else [])
        return [p for p in out if int(p.get("qty") or 0) > 0]
    except Exception:
        return None


def novig_conflict(al, mtype, side, teams, nres, pos, mks_by_event):
    """'duplicate' / 'conflict' / None from Peter's open Novig positions on this game. Spread and moneyline on the same
    team count as the same play; opposite team = conflict. Totals only against totals."""
    if not pos or nres.get("status") != "ok":
        return None
    mid = nres.get("market_id")
    ev = next((e for e, mks in mks_by_event.items() if any(m["marketId"] == mid for m in mks)), None)
    if not ev:
        return None
    by_id = {m["marketId"]: m for m in mks_by_event[ev]}
    for p in pos:
        m = by_id.get(p.get("marketId"))
        if not m:
            continue
        pt = bc.N_MKT.get((m.get("marketType") or "").upper())
        name = next((o.get("name") or "" for o in m.get("outcomes") or [] if o.get("outcomeId") == p.get("outcomeId")), "")
        if mtype == "total" and pt == "total":
            ps = "OVER" if "over" in name.lower() else "UNDER"
            return "duplicate" if ps == side else "conflict"
        if mtype in ("moneyline", "spread") and pt in ("moneyline", "spread"):
            t = lm.team_side(name, list(teams), al["sport"])
            if t is not None:
                return "duplicate" if t == side else "conflict"
    return None


# ---------------------------------------------------------------- one play
def book_line(r):
    for k in ("line", "novig_line", "prophetx_line"):
        if r.get(k) is not None:
            return lm.num(r.get(k))
    return None


def line_ok(mtype, side, alert_line, bl):
    """The book's line is the alert line or BETTER for this side (spread: more points; over: lower; under: higher)."""
    if mtype == "moneyline":
        return True
    if alert_line is None or bl is None:
        return False
    if mtype == "spread":
        return bl >= alert_line - 1e-9
    return bl <= alert_line + 1e-9 if side == "OVER" else bl >= alert_line - 1e-9


def american_to_prob(a):
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def stake_for(am):
    risk = UNIT if am > 0 else UNIT * abs(am) / 100
    win = UNIT * am / 100 if am > 0 else UNIT
    return round(risk, 2), round(win, 2)


def evaluate(p, now, evs_by, mks_by_event, pos):
    al = {"sport": (p.get("sport") or "").upper(), "game": p.get("game") or "", "bet": p.get("bet") or "",
          "start_utc": p.get("start_utc") or ""}
    out = {"play": p, "pid": pid(p["play_key"])}
    text = f" {al['bet']} {p.get('market') or ''} ".lower()
    if al["sport"] in BANNED_SPORTS or any(w in text for w in BANNED_WORDS):
        return dict(out, verdict="SKIP", reason="banned market/sport")
    try:
        st = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00"))
    except Exception:
        return dict(out, verdict="SKIP", reason="no start time")
    lead = (st - now).total_seconds() / 60
    if p.get("late"):
        return dict(out, verdict="SKIP", reason="late (alert tagged late)")
    if lead < MIN_LEAD_MIN:
        return dict(out, verdict="SKIP", reason=f"late ({round(lead)} min to start)")
    teams = lm.split_teams(al["game"])
    mtype, side, line, price = bc.parse_bet(al["bet"], teams, al["sport"]) if teams else (None, None, None, None)
    if not mtype or side is None or price is None:
        return dict(out, verdict="SKIP", reason="could not read the bet")
    res = {}
    try:
        res["novig"] = bc.check_alert(al, evs_by, mks_by_event)
    except Exception as ex:
        res["novig"] = {"status": f"error: {str(ex)[:80]}"}
    if res["novig"].get("status") == "game_not_on_novig":   # show what Novig lists that day (names only)
        day = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00")).astimezone(lm.ET).date()
        res["novig"]["seen"] = sorted({e.get("description") for e in evs_by.values()
                                       if lm.N_LEAGUE.get((e.get("league") or "").upper().strip()) == al["sport"]
                                       and datetime.fromtimestamp(e["startsTs"] / 1000, lm.ET).date() == day
                                       and (set(lm.toks(e.get("description"))) & (lm.toks(teams[0]) | lm.toks(teams[1])))})[:6]
    for b, fn in (("prophetx", bc.px_check), ("kalshi", bc.kalshi_check), ("polymarket_us", pmus_check)):
        try:
            res[b] = fn(al, mtype, side, line, price, teams)
        except Exception as ex:
            res[b] = {"status": f"error: {str(ex)[:80]}"}
    if res["prophetx"].get("status") == "game_not_on_prophetx":
        try:
            words = lm.toks(teams[0]) | lm.toks(teams[1])
            res["prophetx"]["seen"] = [e.get("name") for e in bc.px_events(al["sport"])
                                       if set(lm.toks(e.get("name"))) & words][:6]
        except Exception:
            pass
    out.update(mtype=mtype, side=side, line=line, price=price, lead=round(lead), books=res)
    c = novig_conflict(al, mtype, side, teams, res["novig"], pos, mks_by_event)
    if c == "conflict":
        return dict(out, verdict="SKIP", reason="CONFLICT: opposite side already held on Novig (first side stays)")
    if c == "duplicate":
        return dict(out, verdict="SKIP", reason="duplicate: already holding this side on Novig")
    cands = []
    for b, r in res.items():
        am = r.get("best_price_american")
        if r.get("status") != "ok" or am is None:
            continue
        if not (r.get("exact_line") or line_ok(mtype, side, line, book_line(r))):
            continue
        if am >= price and (r.get("dollars_at_alert_price_or_better") or 0) > 0:
            cands.append((b, am, r.get("dollars_at_alert_price_or_better") or 0))
    if not cands:
        live = [r for r in res.values() if r.get("status") == "ok"]
        if live and not any(r.get("exact_line") or line_ok(mtype, side, line, book_line(r)) for r in live):
            return dict(out, verdict="SKIP", reason=f"line: alert line {line:+g} no longer offered on any book" if line is not None
                        else "line: not offered")
        return dict(out, verdict="SKIP", reason=f"price: alert number {price:+d} not available after fees on any book")
    def line_score(b):   # higher = better line for this side (tie-break at equal price)
        bl = book_line(res[b])
        if bl is None or mtype == "moneyline":
            return 0
        return -bl if (mtype == "total" and side == "OVER") else bl
    cands.sort(key=lambda x: (-x[1], -line_score(x[0])))
    full = [c for c in cands if c[2] >= stake_for(c[1])[0]]
    b, am, avail = (full or cands)[0]
    if mtype in ("spread", "total") and am < CAP_LINE:
        return dict(out, verdict="SKIP", reason=f"price cap: best {am:+d} is worse than {CAP_LINE}")
    risk, win = stake_for(am)
    bl = book_line(res[b])
    return dict(out, verdict="WOULD PLACE", book=b, american=am, risk=risk, to_win=win, fillable=round(min(avail, risk), 2),
                partial=avail < risk, others=[c for c in cands if c[0] != b],
                better_line=(bl if (bl is not None and line is not None and abs(bl - line) > 1e-9) else None))


# ---------------------------------------------------------------- report
def money(x):
    return f"${x:,.0f}"


def fmt(r):
    p = r["play"]
    head = f"[{r['pid']}] {p.get('sport')} {p.get('game')} | {p.get('bet')}"
    if r["verdict"] == "SKIP":
        return f"SKIP  {head}\n      reason: {r['reason']}"
    s = (f"WOULD PLACE  {head}\n      {r['book']} at {r['american']:+d} after fees"
         + (f" on a BETTER line {r['better_line']:+g}" if r.get("better_line") is not None and r['mtype'] == 'spread'
            else (f" on a BETTER line {r['better_line']:g}" if r.get("better_line") is not None else ""))
         + f" | risk {money(r['risk'])} to win {money(r['to_win'])}"
         + (f" | only {money(r['fillable'])} fillable at {r['price']:+d} or better (partial)" if r["partial"] else ""))
    if r.get("others"):
        s += "\n      also at the number: " + ", ".join(f"{b} {am:+d} ({money(d)} avail)" for b, am, d in r["others"])
    return s


def book_lines(r):
    out = []
    for b in BOOKS:
        x = (r.get("books") or {}).get(b) or {}
        if x.get("status") == "ok":
            ln = x.get("line", x.get("novig_line", x.get("prophetx_line")))
            out.append(f"        {b:<14} best {x.get('best_price_american')} line {ln}{'' if x.get('exact_line') else ' (not exact)'}"
                       f" | {money(x.get('dollars_at_alert_price_or_better') or 0)} at alert price or better")
        else:
            out.append(f"        {b:<14} {x.get('status', 'not checked')}"
                       + (f" | listed: {'; '.join(str(v) for v in x['seen'])}" if x.get("seen") else ""))
    return out


def send(subject, body):
    user, pw, to = gmail()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())


def main():
    now = datetime.now(timezone.utc)
    M = imap_open()
    plays = read_verdicts(M)
    new = [p for p in plays if not already_handled(M, p)]
    M.logout()
    print(f"Verdict plays seen (2 days): {len(plays)}; new: {len(new)}")
    if not new:
        return
    lo = int(now.timestamp() * 1000)
    hi = int((now + timedelta(days=3)).timestamp() * 1000)
    try:
        evs, mks = bc.novig_catalog(lo, hi)
    except Exception:
        evs, mks = [], []
    evs_by = {e["eventId"]: e for e in evs}
    mks_by_event = {}
    for mk in mks:
        mks_by_event.setdefault(mk.get("eventId"), []).append(mk)
    pos = novig_positions()
    results = []
    for p in new:
        try:
            results.append(evaluate(p, now, evs_by, mks_by_event, pos))
        except Exception as ex:
            results.append({"play": p, "pid": pid(p["play_key"]), "verdict": "SKIP", "reason": f"error: {str(ex)[:100]}"})
    nw = sum(1 for r in results if r["verdict"] == "WOULD PLACE")
    body = [f"AUTO-PLACE DRY RUN | {now.astimezone(lm.ET).strftime('%a %b %d %I:%M %p ET')} | NOTHING WAS PLACED", "",
            f"Unit {money(UNIT)} | + money risks the unit, - money risks to win the unit | prices are AFTER fees.",
            "Checks: banned, late (<60 min), duplicate/conflict (Novig positions only until other keys exist), "
            "alert number or better, -130 cap on spreads/totals. Balances not checked yet (no trading keys).", ""]
    for r in results:
        body.append(fmt(r))
        if r.get("books"):
            body += book_lines(r)
        body.append("")
    body.append("Novig positions check: " + ("done" if pos is not None else "unavailable this run"))
    send(f"DRY RUN | {nw} would place, {len(results) - nw} skipped | {now.astimezone(lm.ET).strftime('%b %d %I:%M %p')}",
         "\n".join(body))
    print(f"Dry-run email sent: {nw} would place, {len(results) - nw} skipped.")   # counts only


if __name__ == "__main__":
    main()

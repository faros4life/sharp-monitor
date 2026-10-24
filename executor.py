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
RULES = "r2"   # bump when routing rules change so open plays are re-evaluated once (r2: equivalent-price lines, Oct 23)


def pid(play_key):
    return "xpid" + hashlib.sha1((RULES + "|" + play_key).encode()).hexdigest()[:12]


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
    for uid in gsearch(M, "subject:AUTO-PLACE VERDICTS -subject:TEST newer_than:2d"):   # Muse's verdicts only, never tests
        typ, data = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            continue
        txt = body_text(data[0][1])
        arr, dec = None, json.JSONDecoder()
        for m in re.finditer(r"\[", txt):   # tolerate plain text before/after the JSON array
            try:
                cand, _ = dec.raw_decode(txt[m.start():])
            except Exception:
                continue
            if isinstance(cand, list) and cand and isinstance(cand[0], dict):
                arr = cand
                break
        if arr is None:
            LOG.append("verdict email with unreadable JSON")
            continue
        for p in arr if isinstance(arr, list) else []:
            if isinstance(p, dict) and not str(p.get("play_key") or "").upper().startswith("TEST") \
                    and (p.get("play_key") or derive_key(p)):
                plays.append(dict(p, play_key=p.get("play_key") or derive_key(p)))
    seen, out = set(), []
    for p in plays:   # one play per game+side, whatever key it arrived with (spread and ML on a team = one play)
        keys = {p["play_key"], derive_key(p) or p["play_key"]}
        if not keys & seen:
            seen |= keys
            out.append(p)
    return out


def derive_key(p):
    """No play_key (e.g. a raw alerts.json entry): sport|game|market|side, so repeat alerts on one play count once."""
    try:
        teams = lm.split_teams(p.get("game") or "")
        mt, sd, _, _ = bc.parse_bet(p.get("bet") or "", teams, (p.get("sport") or "").upper()) if teams else (None, None, None, None)
        if not mt or sd is None:
            return None
        side = sd if isinstance(sd, str) else teams[sd]
        return f"{(p.get('sport') or '').upper()}|{p.get('game')}|{'side' if mt in ('spread', 'moneyline') else mt}|{side}"
    except Exception:
        return None


def wp(key):
    """Token written ONLY on WOULD PLACE / PLACED entries, so the opposite side can find a side already taken."""
    return "xwp" + hashlib.sha1(key.encode()).hexdigest()[:12]


def opposite_key(p):
    k = derive_key(p)
    if not k:
        return None
    sport, game, kind, side = k.split("|", 3)
    if kind == "total":
        return f"{sport}|{game}|total|{'UNDER' if side == 'OVER' else 'OVER'}"
    teams = lm.split_teams(game) or ()
    other = [t for t in teams if t != side]
    return f"{sport}|{game}|side|{other[0]}" if other else None


def already_handled(M, p):
    """Handled before under its own key OR under the play's game+side key (so a re-sent play never runs twice)."""
    keys = {p["play_key"], derive_key(p) or p["play_key"]}
    return any(gsearch(M, pid(k)) for k in keys)


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
    """FULL-GAME markets only: never halves, quarters, periods, innings or team totals."""
    smt = (mk.get("sportsMarketType") or mk.get("sportsMarketTypeV2") or mk.get("marketType") or "").lower()
    if "full_game" not in smt or any(w in smt for w in ("half", "quarter", "period", "inning", "team_total", "player")):
        return None
    if any(w in smt for w in ("spread", "handicap", "run_line", "puck_line")):
        return "spread"
    if "total" in smt or "over_under" in smt:
        return "total"
    if "winner" in smt or "money" in smt:
        return "moneyline"
    return None


def pmus_side_team(s, ev, teams, sport):
    """Which game team a market side is: by teamId against the event's teams, else by its description."""
    tid = s.get("teamId") or s.get("participantId")
    if tid is not None:
        for t in ev.get("teams") or []:
            if str(t.get("id")) == str(tid) or str(t.get("participantId")) == str(tid):
                return lm.team_side(t.get("name") or "", list(teams), sport)
    return lm.team_side(s.get("description") or s.get("identifier") or "", list(teams), sport)


def pmus_game_markets(ev, markets):
    """All markets of one game (cached per run): by gameId, else the event's own page."""
    ck = ("game", ev.get("slug") or ev.get("id") or id(ev))
    if ck not in _PMUS:
        _PMUS[ck] = _pmus_game_markets(ev, markets)
    return _PMUS[ck]


def _pmus_game_markets(ev, markets):
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
                    ok = pmus_side_team(s, ev, teams, al["sport"]) == side
                if ok:
                    ln = lm.num(mk.get("line"))
                    if mtype == "spread":   # the side's own signed line is in its label, e.g. "+12.50" / "-12.50"
                        sl = lm.signed_num(desc)
                        sline = sl if sl is not None else (ln if s.get("long") is not False else (-ln if ln is not None else None))
                    else:
                        sline = ln
                    cands.append((mk, bool(s.get("long", True)), sline))
        if not cands:
            seen, types = [], set()
            for mk in markets:   # one example per team-level market type (skip player props)
                t = str(mk.get("sportsMarketType") or mk.get("marketType"))
                if "player" in t.lower() or t in types:
                    continue
                types.add(t)
                seen.append(f"{t} line={mk.get('line')} sides="
                            + "/".join(f"{s.get('description') or s.get('identifier')}({'L' if s.get('long') else 'S'})"
                                       for s in mk.get("marketSides") or []))
            seen = seen[:12]
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
_NVERR = {"why": ""}


def novig_positions():
    try:
        import novig_signed as nv
        if not nv.ready():
            _NVERR["why"] = "key not ready"
            return None
        d = nv.get("/v3/portfolio/positions", {"keyId": nv._S["id"]})
        out = []
        for v in (d.values() if isinstance(d, dict) else [d]):
            out += v if isinstance(v, list) else (v.get("items") or [] if isinstance(v, dict) else [])
        return [p for p in out if int(p.get("qty") or 0) > 0]
    except Exception as ex:
        _NVERR["why"] = str(ex)[:120]
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


def evaluate(p, now, evs_by, mks_by_event, pos, taken=None):
    al = {"sport": (p.get("sport") or "").upper(), "game": p.get("game") or "", "bet": p.get("bet") or "",
          "start_utc": p.get("start_utc") or ""}
    dk = derive_key(p)
    out = {"play": p, "pid": pid(p["play_key"]) + (f" {pid(dk)}" if dk and dk != p["play_key"] else "")}
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
    def probe(ln):
        """Each book's ladder at one line (the books pick their nearest strike; kept only if it IS this line)."""
        got = {}
        try:
            got["novig"] = bc.check_alert(dict(al, bet=bet_at(al["bet"], mtype, line, ln)), evs_by, mks_by_event)
        except Exception as ex:
            got["novig"] = {"status": f"error: {str(ex)[:80]}"}
        for b, fn in (("prophetx", bc.px_check), ("kalshi", bc.kalshi_check), ("polymarket_us", pmus_check)):
            try:
                got[b] = fn(al, mtype, side, ln, price, teams)
            except Exception as ex:
                got[b] = {"status": f"error: {str(ex)[:80]}"}
        return got

    res = probe(line)   # the alert line (also what the report's book table shows)
    if res["novig"].get("status") == "game_not_on_novig":   # show what Novig lists that day (names only)
        day = datetime.fromisoformat(al["start_utc"].replace("Z", "+00:00")).astimezone(lm.ET).date()
        res["novig"]["seen"] = sorted({e.get("description") for e in evs_by.values()
                                       if lm.N_LEAGUE.get((e.get("league") or "").upper().strip()) == al["sport"]
                                       and datetime.fromtimestamp(e["startsTs"] / 1000, lm.ET).date() == day
                                       and (set(lm.toks(e.get("description"))) & (lm.toks(teams[0]) | lm.toks(teams[1])))})[:6]
    if res["prophetx"].get("status") == "game_not_on_prophetx":
        try:
            words = lm.toks(teams[0]) | lm.toks(teams[1])
            res["prophetx"]["seen"] = [e.get("name") for e in bc.px_events(al["sport"])
                                       if set(lm.toks(e.get("name"))) & words][:6]
        except Exception:
            pass
    out.update(mtype=mtype, side=side, line=line, price=price, lead=round(lead), books=res)
    ok_ = opposite_key(p)
    if taken and ok_ and taken(ok_):
        return dict(out, verdict="SKIP", reason="CONFLICT: the other side of this game was already taken (first side stays)")
    c = novig_conflict(al, mtype, side, teams, res["novig"], pos, mks_by_event)
    if c == "conflict":
        return dict(out, verdict="SKIP", reason="CONFLICT: opposite side already held on Novig (first side stays)")
    if c == "duplicate":
        return dict(out, verdict="SKIP", reason="duplicate: already holding this side on Novig")

    # --- every nearby line on every book, converted to its EQUIVALENT price at the alert line (Peter, Oct 23)
    ladders = {}   # (book, line) -> result
    lines = [line] if (mtype == "moneyline" or line is None) else [line + d for d in (0, -0.5, 0.5, -1.0, 1.0)]
    for ln in lines:
        got = res if ln == line else probe(ln)
        for b, r in got.items():
            bl = book_line(r) if mtype != "moneyline" else None
            if r.get("status") == "ok" and r.get("best_price_american") is not None and \
                    (mtype == "moneyline" or (bl is not None and abs(bl - ln) < 1e-9)):
                ladders[(b, bl)] = r
    hp, hp_src = half_point(ladders, mtype, side, al["sport"])
    alert_cost = american_to_prob(price)
    cands = []
    for (b, bl), r in ladders.items():
        hb = 0.0 if mtype == "moneyline" else better_halfpoints(mtype, side, line, bl)
        am = r["best_price_american"]
        c_eq = american_to_prob(am) - hb * hp
        if c_eq > alert_cost + 1e-9:
            continue
        thr = lm.american(min(max(alert_cost + hb * hp, 0.01), 0.99))   # worst acceptable real price at this line
        avail = sum(d for a, d in levels(b, r) if a is not None and thr is not None and a >= thr)
        if avail <= 0:
            continue
        cands.append({"book": b, "line": bl, "am": am, "eq": lm.american(min(max(c_eq, 0.01), 0.99)), "c_eq": c_eq,
                      "hb": hb, "avail": avail})
    if not cands:
        if not ladders:
            return dict(out, verdict="SKIP", reason="no book lists this market near the alert line")
        return dict(out, verdict="SKIP", reason=f"price: nothing at or better than {price:+d} at {fmt_line(mtype, line)} "
                                                f"(equivalent, after fees; half point = {hp * 100:.1f}c {hp_src})")
    capped = [c for c in cands if not (mtype in ("spread", "total") and c["am"] < CAP_LINE)]
    if not capped:
        best = min(cands, key=lambda c: c["c_eq"])
        return dict(out, verdict="SKIP", reason=f"price cap: best take is {best['book']} {best['am']:+d} at "
                                                f"{fmt_line(mtype, best['line'])}, worse than {CAP_LINE}")
    capped.sort(key=lambda c: (round(c["c_eq"], 6), -c["hb"]))   # best equivalent price; tie -> better line
    full = [c for c in capped if c["avail"] >= stake_for(c["am"])[0]]
    pick = (full or capped)[0]
    risk, win = stake_for(pick["am"])
    return dict(out, verdict="WOULD PLACE", book=pick["book"], american=pick["am"], take_line=pick["line"],
                equiv=pick["eq"], hp=hp, hp_src=hp_src, risk=risk, to_win=win,
                fillable=round(min(pick["avail"], risk), 2), partial=pick["avail"] < risk,
                others=[c for c in capped if c is not pick][:5])


def fmt_line(mtype, ln):
    if mtype == "moneyline" or ln is None:
        return "ML"
    return f"{ln:+g}" if mtype == "spread" else f"{ln:g}"


def bet_at(bet, mtype, alert_line, ln):
    """The alert text with its line swapped (Novig's checker reads the line from the bet text)."""
    if mtype == "moneyline" or alert_line is None or ln == alert_line:
        return bet
    old = f"{alert_line:+g}" if mtype == "spread" else f"{alert_line:g}"
    new = f"{ln:+g}" if mtype == "spread" else f"{ln:g}"
    return bet.replace(old, new, 1) if old in bet else bet.replace(f"{abs(alert_line):g}", f"{abs(ln):g}", 1)


def better_halfpoints(mtype, side, alert_line, bl):
    """How many half points better (+) or worse (-) the book's line is for this side."""
    if alert_line is None or bl is None:
        return 0.0
    d = (bl - alert_line) if (mtype == "spread" or side == "UNDER") else (alert_line - bl)
    return d / 0.5


HP_FALLBACK = {"NBA": 0.027, "NCAAB": 0.030, "NFL": 0.030, "NCAAF": 0.028, "NHL": 0.09, "MLB": 0.07}


def half_point(ladders, mtype, side, sport):
    """Value of a half point (probability) from the live ladders: price gap between adjacent lines on the same book.
    Median across books, kept within 0.5x-2x of the standard value; standard value when the ladders can't say."""
    fb = HP_FALLBACK.get(sport, 0.03)
    if mtype == "moneyline":
        return 0.0, ""
    gaps = []
    by_book = {}
    for (b, bl), r in ladders.items():
        by_book.setdefault(b, {})[bl] = american_to_prob(r["best_price_american"])
    for b, m in by_book.items():
        ls = sorted(m)
        for x, y in zip(ls, ls[1:]):
            if abs((y - x) - 0.5) < 1e-9:
                gaps.append(abs(m[y] - m[x]))
    if not gaps:
        return fb, "(standard)"
    gaps.sort()
    g = gaps[len(gaps) // 2]
    return min(max(g, fb / 2), fb * 2), f"(live, {len(gaps)} gap{'s' if len(gaps) > 1 else ''})"


def levels(book, r):
    """[(American price after fees, dollars)] from a checker's ladder."""
    out = []
    for x in r.get("buy_levels") or []:
        a = x.get("american_after_fee", x.get("american"))
        out.append((a, x.get("dollars") or 0))
    if not out and r.get("best_price_american") is not None:
        out.append((r["best_price_american"], r.get("dollars_at_alert_price_or_better") or 0))
    return out


# ---------------------------------------------------------------- report
def bet_text(r, ln, am):
    """'Houston Cougars +7.5 -130' / 'Over 55.5 -127' / 'Spurs ML +110'"""
    p, mt, side = r["play"], r.get("mtype"), r.get("side")
    teams = lm.split_teams(p.get("game") or "") or ("", "")
    who = side.title() if side in ("OVER", "UNDER") else (teams[side] if isinstance(side, int) else "?")
    ln_s = "ML" if mt == "moneyline" else (f"{ln:+g}" if mt == "spread" else f"{ln:g}")
    return f"{who} {ln_s} {am:+d}"


def short(r):
    return bet_text(r, r.get("take_line"), r["american"]).replace(" ML ", " ")


BOOK_NAME = {"novig": "Novig", "prophetx": "ProphetX", "kalshi": "Kalshi", "polymarket_us": "Polymarket US"}


def plain(r):
    p = r["play"]
    game = p.get("game") or ""
    if r["verdict"] == "WOULD PLACE":
        moved = r.get("mtype") != "moneyline" and r.get("take_line") is not None and abs(r["take_line"] - r["line"]) > 1e-9
        s = (f"  - {bet_text(r, r.get('take_line'), r['american'])} on {BOOK_NAME.get(r['book'], r['book'])}: "
             f"risk {money(r['risk'])} to win {money(r['to_win'])}.  ({p.get('sport')} {game})")
        s += f"\n      Alert was {p.get('bet')}" + (f"; this line is worth {r['equiv']:+d} at the alert number." if moved else ".")
        if r.get("partial"):
            s += f" Only {money(r['fillable'])} available at that price, so it would be a partial bet."
        return s
    return f"  - {p.get('bet')}  ({p.get('sport')} {game}): {plain_reason(r['reason'])}"


def plain_reason(reason):
    rl = reason.lower()
    if rl.startswith("price cap"):
        return "price is worse than -130."
    if rl.startswith("price"):
        return "the price is gone (nothing at the alert number or better, after fees)."
    if rl.startswith("line"):
        return "the line has moved away on every book."
    if rl.startswith("late"):
        return "too close to start (under 60 min)."
    if rl.startswith("conflict"):
        return "you already have the OTHER side of this game (first side stays)."
    if rl.startswith("duplicate"):
        return "you already have this bet."
    if rl.startswith("banned"):
        return "banned market (tennis, UFC, soccer, 1H/1Q, props or parlays)."
    return reason


def money(x):
    return f"${x:,.0f}"


def fmt(r):
    p = r["play"]
    dk = derive_key(p)
    tag = r["pid"] + (f" {wp(dk)}" if (r["verdict"] != "SKIP" and dk) else "")
    head = f"[{tag}] {p.get('sport')} {p.get('game')} | {p.get('bet')}"
    if r["verdict"] == "SKIP":
        return f"SKIP  {head}\n      reason: {r['reason']}"
    moved = r["mtype"] != "moneyline" and r.get("take_line") is not None and abs(r["take_line"] - r["line"]) > 1e-9
    s = (f"WOULD PLACE  {head}\n      {r['book']} {fmt_line(r['mtype'], r.get('take_line'))} at {r['american']:+d} after fees"
         + (f" (= {r['equiv']:+d} at {fmt_line(r['mtype'], r['line'])}; half point {r['hp'] * 100:.1f}c {r['hp_src']})" if moved else "")
         + f" | risk {money(r['risk'])} to win {money(r['to_win'])}"
         + (f" | only {money(r['fillable'])} fillable at an equivalent price (partial)" if r["partial"] else ""))
    if r.get("others"):
        s += "\n      next best: " + ", ".join(f"{c['book']} {fmt_line(r['mtype'], c['line'])} {c['am']:+d} (= {c['eq']:+d}, "
                                             f"{money(c['avail'])})" for c in r["others"])
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
    results, taken_now = [], set()
    M2 = imap_open()

    def taken(k):   # this run, or any earlier WOULD PLACE / PLACED entry
        return k in taken_now or bool(gsearch(M2, wp(k)))
    for p in new:
        try:
            r = evaluate(p, now, evs_by, mks_by_event, pos, taken)
            results.append(r)
            if r["verdict"] != "SKIP" and derive_key(p):
                taken_now.add(derive_key(p))
        except Exception as ex:
            results.append({"play": p, "pid": pid(p["play_key"]), "verdict": "SKIP", "reason": f"error: {str(ex)[:100]}"})
    M2.logout()
    nw = sum(1 for r in results if r["verdict"] == "WOULD PLACE")
    when = now.astimezone(lm.ET).strftime('%a %b %d %I:%M %p ET')
    body = [f"DRY RUN - nothing was bet ({when})", ""]
    places = [r for r in results if r["verdict"] == "WOULD PLACE"]
    skips = [r for r in results if r["verdict"] != "WOULD PLACE"]
    if places:
        body.append(f"WOULD BET ({len(places)})")
        body += [plain(r) for r in places]
        body.append("")
    if skips:
        body.append(f"SKIPPED ({len(skips)})")
        body += [plain(r) for r in skips]
        body.append("")
    if pos is None:
        body += [f"Note: couldn't check your Novig positions this run ({_NVERR['why']}). Live mode would bet nothing.", ""]
    body += ["", "-" * 60, "DETAILS (for Muse)",
             f"Unit {money(UNIT)}: + money risks the unit, - money risks to win it. Prices after fees. Routing: every line within "
             "1 point on every book converted to its equivalent price at the alert line (half point from live ladders); best "
             "equivalent wins, ties to the better line; -130 cap on the price taken. Novig positions: "
             + ("checked" if pos is not None else "unavailable") + ".", ""]
    for r in results:
        body.append(fmt(r))
        if r.get("books"):
            body += book_lines(r)
        body.append("")
    first = ", ".join(short(r) for r in places[:3]) + ("..." if len(places) > 3 else "")
    send(f"Bets dry run: {nw} would bet" + (f" ({first})" if places else "") + f", {len(results) - nw} skipped",
         "\n".join(body))
    print(f"Dry-run email sent: {nw} would place, {len(results) - nw} skipped.")   # counts only


if __name__ == "__main__":
    main()

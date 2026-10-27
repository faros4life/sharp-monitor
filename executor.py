#!/usr/bin/env python3
"""
Auto-placement executor (Oct 23 spec; LIVE phase 1 added Oct 26). Real orders happen ONLY through px_live.place()
(ProphetX, fill-or-kill, phase-1 plays with Muse AGREE, $50 unit) and ONLY when the repo variable EXEC_LIVE is "on";
px_live refuses on STOP, the $100 per-order guard and the $1,500 daily stop. Everything else stays a dry run. It reads Muse's AUTO-PLACE VERDICTS emails, runs every skip check, prices all 4
books after fees, sizes the stake, and emails what it WOULD have placed.

Verdict email (from Muse, to the Bets address): subject contains "AUTO-PLACE VERDICTS"; body holds a JSON array of
plays. Each play needs: play_key, sport, game ("Away @ Home", as in alerts.json), bet (alert text as in alerts.json,
e.g. "Oklahoma City Thunder -8.5 (-108)"), start_utc. Optional: late (bool).
Array plays are AGREE. A play with a "verdict" field other than AGREE is never placed. Deliberate kills go on their own
plain-text line, one per play: DISAGREE: {"sport": "NBA", "game": "Away @ Home", "bet": "<alert text>"} -> clears the
watchdog only. An email may carry an empty array [] plus DISAGREE lines.

Public repo: the Actions log prints counts only. Everything else goes by email.
"""
import email
import email.utils
import email.header
import hashlib
import imaplib
import json
import os
import re
import smtplib
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import book_check as bc
import liquidity_monitor as lm
import agree_rules
import positions
import px_live

UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")          # + money: risk UNIT; - money: risk to win UNIT
SOURCE = (os.environ.get("EXEC_SOURCE", "") or "both").lower()  # muse | rules | both (dry run: both, side by side)
RULES_LOOKBACK_H = 6                                             # coded rules look at alerts first sent in the last 6 h
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


def gsearch_strict(M, query):
    """gsearch that RAISES on a failed search (for safety checks that must fail closed)."""
    typ, data = M.uid("SEARCH", "X-GM-RAW", '"' + query.replace('"', '') + '"')
    if typ != "OK":
        raise RuntimeError("Gmail search failed")
    return data[0].split() if data and data[0] else []


def body_text(raw):
    msg = email.message_from_bytes(raw)
    parts = msg.walk() if msg.is_multipart() else [msg]
    for p in parts:
        if p.get_content_type() == "text/plain":
            return p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="ignore")
    return ""


MUSE_DISAGREE = set()   # keys Muse killed on purpose: clear the watchdog, never placed


def read_verdicts(M):
    plays = []
    for uid in gsearch(M, "subject:AUTO-PLACE VERDICTS -subject:TEST newer_than:2d"):   # Muse's verdicts only, never tests
        typ, data = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            continue
        txt = body_text(data[0][1])
        if txt.lstrip().upper().startswith("TEST"):
            continue   # TEST in the body's first word also counts: a test email never feeds live
        try:
            vt = email.utils.parsedate_to_datetime(email.message_from_bytes(data[0][1]).get("Date")).astimezone(timezone.utc)
            vts = vt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            vts = None
        arr, dec = None, json.JSONDecoder()
        for line in txt.splitlines():   # Muse's deliberate kills: DISAGREE: {"sport":..,"game":..,"bet":..} (watchdog only)
            m = re.match(r"\s*DISAGREE:\s*(\{.*\})\s*$", line)
            if m:
                try:
                    d = json.loads(m.group(1))
                    MUSE_DISAGREE.update(k for k in (d.get("play_key"), derive_key(d)) if k)
                except Exception:
                    LOG.append("unreadable DISAGREE line")
        empty = False
        for m in re.finditer(r"\[", txt):   # tolerate plain text before/after the JSON array
            try:
                cand, _ = dec.raw_decode(txt[m.start():])
            except Exception:
                continue
            if isinstance(cand, list) and cand and isinstance(cand[0], dict):
                arr = cand
                break
            if cand == []:
                empty = True
        if arr is None:
            if not empty:
                LOG.append("verdict email with unreadable JSON")
            continue
        for p in arr if isinstance(arr, list) else []:
            if not isinstance(p, dict) or str(p.get("play_key") or "").upper().startswith("TEST"):
                continue
            if p.get("verdict") is not None and str(p.get("verdict")).strip().upper() != "AGREE":
                MUSE_DISAGREE.update(k for k in (p.get("play_key"), derive_key(p)) if k)   # never a bet
                continue
            if p.get("play_key") or derive_key(p):
                plays.append(dict(p, play_key=p.get("play_key") or derive_key(p), verdict_utc=vts))
    seen, out = set(), []
    for p in plays:   # one play per game+side, whatever key it arrived with (spread and ML on a team = one play)
        keys = {p["play_key"], derive_key(p) or p["play_key"]}
        if not keys & seen:
            seen |= keys
            out.append(p)
    return out


def rule_plays(now):
    """New alerts from alerts.json (the checkout is the latest feed) with the coded AGREE decision attached."""
    try:
        with open("alerts.json") as f:
            feed = json.load(f).get("alerts") or []
    except Exception as ex:
        LOG.append(f"alerts.json unreadable: {str(ex)[:60]}")
        return []
    out = []
    for a in feed:
        try:
            t = datetime.fromisoformat((a.get("alert_utc") or "").replace("Z", "+00:00"))
            st = datetime.fromisoformat(a["start_utc"].replace("Z", "+00:00"))
        except Exception:
            continue
        if t < now - timedelta(hours=RULES_LOOKBACK_H) or st <= now or not a.get("sent_to_phone"):
            continue   # gate 1 (not sent = log only, no verdict) is applied here, so muted alerts add no email noise
        p = {"sport": a.get("sport"), "game": a.get("game"), "bet": a.get("bet"), "start_utc": a.get("start_utc"),
             "late": a.get("late"), "source": "rules", "alert_utc": a.get("alert_utc"), "rules": agree_rules.decide(a)}
        k = derive_key(p)
        if not k:
            continue
        out.append(dict(p, play_key="rule|" + k))
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


def load_feed():
    try:
        with open("alerts.json") as f:
            return json.load(f).get("alerts") or []
    except Exception:
        return []


def feed_entry(p, feed):
    """The alerts.json entry (first alert per game/market/side) for a play, matched on sport|game|market|side."""
    k = derive_key(p)
    if not k:
        return None
    for a in feed:
        if a.get("game") == p.get("game") and derive_key(a) == k:
            return a
    return None


def iso_t(x):
    try:
        return datetime.fromisoformat((x or "").replace("Z", "+00:00"))
    except Exception:
        return None


LIVE_UNIT = 50.0   # phase-1 live unit (Peter + Muse, Oct 25); the dry run tags what WOULD GO LIVE at this size


def live_stake(am):
    risk = LIVE_UNIT if am > 0 else LIVE_UNIT * abs(am) / 100
    return round(risk, 2), round(LIVE_UNIT * am / 100 if am > 0 else LIVE_UNIT, 2)


WATCH_MIN = 10   # Oct 27 (Muse): a phase-1-qualifying alert with no Muse verdict 10 min after the executor saw it -> push


def _first_email_time(M, token):
    """Internal date (UTC) of the earliest email carrying this token, or None."""
    uids = gsearch_strict(M, token)
    best = None
    for uid in uids[:5]:
        typ, data = M.uid("FETCH", uid, "(INTERNALDATE)")
        if typ == "OK" and data and data[0]:
            m = re.search(rb'INTERNALDATE "([^"]+)"', data[0] if isinstance(data[0], bytes) else data[0][0])
            if m:
                t = datetime.fromtimestamp(time.mktime(imaplib.Internaldate2tuple(b'INTERNALDATE "' + m.group(1) + b'"')), timezone.utc)
                best = t if best is None or t < best else best
    return best


def muse_watchdog(now, muse_plays, rplays, feed):
    """Every run: phase-1-qualifying SENT alerts (coded view, ignoring Muse AGREE) whose executor decision is 10+ min old
    with NO Muse verdict on the same game+market+side -> one phone push per play ('No Muse verdict'), recorded by a
    token in a short email so it never repeats. 2:00-5:00 AM ET is Muse's pause: those alerts get their 10 min from
    5:00 AM, and no push is sent inside the pause. Counts only in the public log."""
    et = now.astimezone(lm.ET)
    if 2 <= et.hour < 5:
        return 0
    have = set(MUSE_DISAGREE)   # a deliberate DISAGREE is a verdict, not a missing one
    for p in muse_plays:
        have |= {p.get("play_key"), derive_key(p)}
    late = []
    try:
        M = imap_open()
        try:
            for p in rplays:
                k = derive_key(p)
                if not k or k in have:
                    continue
                ent = feed_entry(p, feed)
                if not ent or not agree_rules.phase1(ent, True)[0]:
                    continue
                tok = "xwdog" + hashlib.sha1(k.encode()).hexdigest()[:12]
                if gsearch_strict(M, tok):
                    continue   # already pushed once
                seen = _first_email_time(M, pid(p["play_key"]))   # the executor's decision email for this play
                if seen is None:
                    continue   # not decided yet (this run decides it); the clock starts then
                start = seen
                st_et = seen.astimezone(lm.ET)
                if 2 <= st_et.hour < 5:   # decided inside the pause: the clock starts at 5:00 AM ET
                    start = st_et.replace(hour=5, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
                if now - start >= timedelta(minutes=WATCH_MIN):
                    late.append((p, ent, tok, round((now - start).total_seconds() / 60)))
        finally:
            M.logout()
    except Exception as ex:
        print(f"watchdog check failed: {str(ex)[:60]}")
        return 0
    for p, ent, tok, mins in late:
        msg = (f"{p.get('sport')} {p.get('game')} | {p.get('bet')}\nQualifies for LIVE, but no Muse verdict after {mins} min. "
               "Live won't bet it without Muse AGREE. Ping Muse.")
        push("No Muse verdict: " + (p.get("bet") or "")[:50], msg)
        tg("NO MUSE VERDICT\n" + msg)
        try:
            send(f"Bets watchdog: no Muse verdict ({(p.get('bet') or '')[:40]})", msg + f"\n\n{tok}")
        except Exception:
            pass
    print(f"Watchdog: {len(late)} qualifying play(s) with no Muse verdict after {WATCH_MIN} min")   # counts only
    return len(late)


def held_tok(key):
    """Token on HELD entries (positions unreadable): the play is NOT marked handled, so the next run retries it;
    this token only stops the phone alert from repeating every 10 minutes."""
    return "xheld" + hashlib.sha1(key.encode()).hexdigest()[:12]


def push(title, body):
    """Phone alert through the same ntfy topic as the sharp alerts (no amounts)."""
    topic = os.environ.get("NTFY_TOPIC", "")
    if not topic:
        return
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
                                     headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high",
                                              "Tags": "warning"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as ex:
        print(f"push failed: {str(ex)[:60]}")


def tg(text):
    """Fill/error message to Peter's Telegram (Oct 27; Xfinity has no email-to-text). Secrets TELEGRAM_BOT_TOKEN /
    TELEGRAM_CHAT_ID; missing or failing = silently skipped (ntfy still fires). Nothing printed to the public log."""
    tok, chat = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip(), (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not tok or not chat:
        return
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     data=json.dumps({"chat_id": chat, "text": text[:3500]}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        print("telegram send failed")


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
    if p.get("source") == "rules":   # separate namespace, so Muse's verdict on the same play is still evaluated
        return bool(gsearch(M, pid(p["play_key"])))
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
        out = []
        # main wallet + the auto-place subaccount (the executor will bet from the subaccount)
        for kid in dict.fromkeys([nv._S["id"], (os.environ.get("NOVIG_TRADE_KEY_ID") or "").strip()]):
            if not kid:
                continue
            try:
                d = nv.get("/v3/portfolio/positions", {"keyId": kid})
            except Exception as ex:
                if kid == nv._S["id"]:
                    raise
                _NVERR["sub"] = str(ex)[:80]   # subaccount not readable with the read key: main wallet still checked
                continue
            for v in (d.values() if isinstance(d, dict) else [d]):
                out += v if isinstance(v, list) else (v.get("items") or [] if isinstance(v, dict) else [])
        _NVERR["src"] = "cloud read"
        return [p for p in out if int(p.get("qty") or 0) > 0]
    except Exception as ex:
        _NVERR["why"] = str(ex)[:120]
        snap = novig_snapshot()   # Oct 27: cloud read failed (often HTTP 451) -> the home runner's snapshot, if fresh
        if snap is not None:
            return snap
        return None


SNAP_URL = "https://api.github.com/repos/faros4life/novig-runner/contents/snapshot/novig_positions.json?ref=main"
SNAP_MAX_MIN = 15


def novig_snapshot():
    """Novig positions written every 5 min by Peter's home runner (private repo novig-runner), read with a token scoped
    read-only to that repo (secret NOVIG_SNAPSHOT_TOKEN). Older than 15 min, failed, or unreadable -> None (held)."""
    tok = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
    if not tok:
        _NVERR["why"] += " | no snapshot token"
        return None
    try:
        req = urllib.request.Request(SNAP_URL, headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github.raw+json",
                                                        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor"})
        with urllib.request.urlopen(req, timeout=15) as r:
            snap = json.loads(r.read().decode())
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(snap["snapshot_utc"].replace("Z", "+00:00"))).total_seconds() / 60
        if not snap.get("ok"):
            _NVERR["why"] += f" | home snapshot failed ({str(snap.get('error'))[:60]})"
            return None
        if age > SNAP_MAX_MIN:
            _NVERR["why"] += f" | home snapshot {age:.0f} min old (max {SNAP_MAX_MIN})"
            return None
        _NVERR["src"] = f"home snapshot, {age:.0f} min old (cloud read failed)"
        return [p for p in snap.get("positions") or [] if int(p.get("qty") or 0) > 0]
    except Exception as ex:
        _NVERR["why"] += f" | home snapshot unreadable ({str(ex)[:60]})"
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


WIN_FEE = {"prophetx": 0.02}   # fee on winnings: a ProphetX win nets 98% of the screen payout


def stake_for(am):
    risk = UNIT if am > 0 else UNIT * abs(am) / 100
    win = UNIT * am / 100 if am > 0 else UNIT
    return round(risk, 2), round(win, 2)


def evaluate(p, now, evs_by, mks_by_event, pos, taken=None, held=None):
    al = {"sport": (p.get("sport") or "").upper(), "game": p.get("game") or "", "bet": p.get("bet") or "",
          "start_utc": p.get("start_utc") or ""}
    dk = derive_key(p)
    out = {"play": p, "pid": pid(p["play_key"]) + (f" {pid(dk)}" if dk and dk != p["play_key"]
                                                   and p.get("source") != "rules" else "")}   # rules keep their own namespace
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
    c2 = positions.conflict(dict(al), mtype, side, teams, held or {})
    if c2:
        bn = BOOK_NAME.get(c2[1], c2[1])
        if c2[0] == "conflict":
            return dict(out, verdict="SKIP", reason=f"CONFLICT: opposite side already held on {bn} (first side stays)")
        return dict(out, verdict="SKIP", reason=f"duplicate: already holding this side on {bn}")

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
        shown = r.get("best_price_american_displayed")
        cands.append({"book": b, "line": bl, "am": am, "shown": int(shown) if shown is not None else am, "eq": lm.american(min(max(c_eq, 0.01), 0.99)), "c_eq": c_eq,
                      "hb": hb, "avail": avail, "thr": thr, "buy": r.get("buy_levels") or []})
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
    # stake is sized on the price on the book's screen (Peter, Oct 25: same as ntfy and Muse); routing/cap stay after-fee
    full = [c for c in capped if c["avail"] >= stake_for(c["shown"])[0]]
    pick = (full or capped)[0]
    risk, win = stake_for(pick["shown"])
    nets = round(win * (1 - WIN_FEE.get(pick["book"], 0)), 2)
    pxc = next((c for c in capped if c["book"] == "prophetx"), None)   # phase-1 live is ProphetX only
    return dict(out, verdict="WOULD PLACE", book=pick["book"], american=pick["am"], shown=pick["shown"], take_line=pick["line"],
                px=({"am": pxc["am"], "shown": pxc["shown"], "line": pxc["line"], "avail": pxc["avail"], "thr": pxc["thr"],
                     "buy": pxc["buy"]} if pxc else None),
                equiv=pick["eq"], hp=hp, hp_src=hp_src, risk=risk, to_win=win, nets=nets,
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


def src_tag(p):
    return "[coded rules] " if p.get("source") == "rules" else ("[Muse] " if SOURCE == "both" else "")


def lag_text(p, now=None):
    try:
        t = datetime.fromisoformat(p["alert_utc"].replace("Z", "+00:00"))
        return f"{((now or datetime.now(timezone.utc)) - t).total_seconds() / 60:.0f} min after the alert"
    except Exception:
        return ""


def plain(r):
    p = r["play"]
    txt = _plain(r)
    return "  - " + src_tag(p) + (txt[4:] if txt.startswith("  - ") else txt)


def _plain(r):
    p = r["play"]
    game = p.get("game") or ""
    if r["verdict"] == "WOULD PLACE":
        moved = r.get("mtype") != "moneyline" and r.get("take_line") is not None and abs(r["take_line"] - r["line"]) > 1e-9
        s = (f"  - {bet_text(r, r.get('take_line'), r.get('shown', r['american']))} on {BOOK_NAME.get(r['book'], r['book'])}: "
             f"risk {money(r['risk'])} to win {money(r['to_win'])}"
             + (f" (nets {money(r['nets'])} after fee)" if r.get("nets") is not None and r["nets"] < r["to_win"] else "")
             + f".  ({p.get('sport')} {game})")
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


def order_note(o):
    if not o or o.get("status") == "dry":
        return ""
    if o["status"] == "placed":
        return (f"  [PLACED: ${o.get('filled_stake') or 0:,.2f} filled" + (f" at {o['avg_price']:+d}" if o.get("avg_price") else "")
                + f", asked ${o.get('asked_stake') or 0:,.2f}, order {o.get('order_id')}]")
    return f"  [{o['status'].upper()}: {o.get('reason')}]"


def money(x):
    return f"${x:,.0f}"


def fmt(r):
    p = r["play"]
    dk = derive_key(p)
    if r["verdict"] == "HELD":   # no xpid token: the play stays new and is retried next run
        return f"HELD  [{held_tok(dk or p['play_key'])}] {p.get('sport')} {p.get('game')} | {p.get('bet')}\n      reason: {r['reason']}"
    tag = r["pid"] + (f" {wp(dk)}" if (r["verdict"] == "WOULD PLACE" and dk and p.get("source") != "rules") else "")
    head = f"{src_tag(p)}[{tag}] {p.get('sport')} {p.get('game')} | {p.get('bet')}"
    if p.get("source") == "rules":
        head += f"\n      decided {lag_text(p)}; flags (never veto): {'; '.join(p['rules'].get('flags') or []) or '-'}"
    if r["verdict"] == "SKIP":
        return f"SKIP  {head}\n      reason: {r['reason']}"
    moved = r["mtype"] != "moneyline" and r.get("take_line") is not None and abs(r["take_line"] - r["line"]) > 1e-9
    s = (f"WOULD PLACE  {head}\n      {r['book']} {fmt_line(r['mtype'], r.get('take_line'))} at {r['american']:+d} after fees"
         + (f" (= {r['equiv']:+d} at {fmt_line(r['mtype'], r['line'])}; half point {r['hp'] * 100:.1f}c {r['hp_src']})" if moved else "")
         + f" | screen {r.get('shown', r['american']):+d} | risk {money(r['risk'])} to win {money(r['to_win'])}"
         + (f" (nets {money(r['nets'])})" if r.get("nets") is not None and r["nets"] < r["to_win"] else "")
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


def px_limit(pxd, stake):
    """(strike_id, limit price, stake) for a ProphetX fill-or-kill: walk the ladder best price first, only levels at
    or better than the alert-equivalent threshold, until the stake is covered. Stake shrinks to what's there."""
    thr = pxd.get("thr")
    lv = sorted((x for x in pxd.get("buy") or [] if x.get("american_after_fee") is not None and thr is not None
                 and x["american_after_fee"] >= thr and x.get("strike_id")), key=lambda x: -x["american"])
    got, limit = 0.0, None
    for x in lv:
        got += x.get("dollars") or 0
        limit = x["american"]
        if got >= stake:
            break
    if not lv:
        return None, None, 0.0
    return lv[0]["strike_id"], limit, round(min(stake, got), 2)


def bot_orders(M, days=4):
    """{order_id: book} the bot PLACED in the last few days, read from its own 'Bets LIVE:' emails' LEDGER rows.
    Gmail is the registry (nothing financial in the public repo). None if unreadable -> live refuses (fail closed).
    Oct 27 fix (found by the brake check): match the SUBJECT PREFIX exactly ('Bets LIVE:'), via IMAP SUBJECT + SINCE and
    a header re-check, so dry-run emails (whose body says 'WOULD GO LIVE') are never read as live ones."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
        typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", since)
        if typ != "OK":
            return None
        ids = {}
        for uid in (data[0].split() if data and data[0] else []):
            typ, d = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not d or not d[0]:
                return None
            raw = d[0][1]
            subj = str(email.header.make_header(email.header.decode_header(email.message_from_bytes(raw).get("Subject") or "")))
            if not subj.startswith("Bets LIVE:"):
                continue   # IMAP SUBJECT is a substring match; only the executor's own live run emails count
            txt = body_text(raw)
            i = txt.rfind("LEDGER (machine-readable")
            if i < 0:
                return None   # a live email without its ledger: can't trust the registry
            rows, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
            for row in rows:
                lo = row.get("live_order") or {}
                if lo.get("status") == "placed" and lo.get("order_id"):
                    ids[str(lo["order_id"])] = lo.get("book") or "prophetx"
        return ids
    except Exception:
        return None


def _h(x):
    return hashlib.sha1(str(x).encode()).hexdigest()[:12]


GUARD = {"ok": None, "why": ""}


def live_guards():
    """Once per run, before any live order (Oct 27): load the bot-order registry so the $1,500 daily stop counts only
    the bot's own orders, not Peter's manual bets. Unreadable registry = refuse (fail closed). No loss-streak pause
    (Peter, Oct 27: no 3-loss rule)."""
    if GUARD["ok"] is not None:
        return GUARD["ok"], GUARD["why"]
    ok, why = False, ""
    try:
        M = imap_open()
        try:
            ids = bot_orders(M)
        finally:
            M.logout()
        px_live.set_bot_orders(None if ids is None else list(ids))
        if ids is None:
            why = "couldn't read the bot's order registry in Gmail (fail closed)"
        else:
            ok = True
    except Exception as ex:
        why = f"live guard check failed ({str(ex)[:60]}) - fail closed"
    GUARD.update(ok=ok, why=why)
    return ok, why


def live_order(r):
    """Phase-1 live order on ProphetX (only when EXEC_LIVE is on). Returns the order record for the email/ledger."""
    lv, p = r["live"], r["play"]
    hr = agree_rules.hr_priced(r.get("entry") or {})   # Oct 27: re-check the PRICING book at placement; unknown = refuse
    if hr is not False:
        return {"status": "refused", "reason": "Hard Rock-priced alert: never live" if hr else "pricing book unknown (fail closed)"}
    db = agree_rules.deadband(dict(r.get("entry") or {}, sent_to_phone=True))   # Oct 27 retail deadband re-check
    if db is not False:
        return {"status": "refused", "reason": "retail deadband: non-ProphetX at -119 to -110 after fee" if db
                else "after-fee price unknown (fail closed)"}
    if not px_live.LIVE:
        return {"status": "dry", "reason": "live is off"}
    g_ok, g_why = live_guards()
    if not g_ok:
        return {"status": "refused", "reason": g_why}
    strike, limit, stake = px_limit(lv["px"], lv["risk"])
    if not strike or stake < 5:
        return {"status": "refused", "reason": f"ProphetX ladder can't cover $5+ at the alert number (have ${stake:.2f})"}
    label = f"{p.get('sport')} {p.get('game')} | {bet_text(r, lv['line'], limit)}"
    res = px_live.place(strike, limit, stake, label)
    if res["status"] == "placed":
        fs, ap = res.get("filled_stake") or 0, res.get("avg_price")
        if fs and ap:
            win = (fs * 100 / abs(ap) if ap < 0 else fs * ap / 100) * 0.98
            tg(f"FILLED ProphetX: {bet_text(r, lv['line'], ap)}\n${fs:,.2f} at {ap:+d} -> wins ${win:,.2f} after the 2% fee"
               f"{'' if fs >= stake - 0.01 else f' (partial: asked ${stake:,.2f})'}\n{p.get('sport')} {p.get('game')}\n"
               "Send STOP on ntfy to pause.")
        else:
            tg(f"NO FILL ProphetX: {bet_text(r, lv['line'], limit)}\nFill-or-kill got nothing at {limit:+d} or better"
               + ("" if res.get("fills_read") else " (fill read failed: check My Trades)") + ".")
        push("PLACED: " + bet_text(r, lv["line"], limit)[:60],
             f"{label}\nProphetX fill-or-kill: ${res.get('filled_stake') or 0:,.2f} filled"
             + (f" at {res['avg_price']:+d}" if res.get("avg_price") else "") + f" (asked ${stake:,.2f}, limit {limit:+d})."
             + ("" if res.get("fills_read") else " Fill read failed: check My Trades."))
    elif res["status"] == "error":
        tg(f"LIVE ORDER ERROR ProphetX: {(p.get('bet') or '')[:60]}\n{res['reason'][:200]}\nCheck My Trades before retrying.")
        push("LIVE ORDER ERROR: " + (p.get("bet") or "")[:50], f"{label}\n{res['reason']}\nCheck ProphetX My Trades before retrying.")
    return dict(res, asked_stake=stake, limit=limit)


def ledger_row(r, run_start):
    p, e = r["play"], r.get("entry") or {}
    at = iso_t(e.get("alert_utc") or p.get("alert_utc"))
    dec = r.get("decided_utc") or run_start
    vt = iso_t(p.get("verdict_utc"))
    lv = r.get("live") or {}
    return {"key": derive_key(p) or p.get("play_key"), "source": p.get("source") or "muse", "verdict": r["verdict"],
            "reason": r.get("reason"), "alert_utc": e.get("alert_utc") or p.get("alert_utc"), "verdict_utc": p.get("verdict_utc"),
            "run_start_utc": run_start.strftime("%Y-%m-%dT%H:%M:%SZ"), "decided_utc": dec.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "latency_s": round((dec - at).total_seconds()) if at else None,
            "muse_delay_s": round((vt - at).total_seconds()) if (vt and at) else None,
            "alert_book": e.get("book_key"), "alert_price_after_fee": e.get("price_after_fee"), "alert_line": e.get("point"),
            "fill_book": r.get("book"), "fill_price_after_fee": r.get("american"), "fill_screen": r.get("shown"),
            "fill_line": r.get("take_line"), "live": bool(lv.get("go")), "live_nfl": bool(lv.get("nfl")), "live_why_not": lv.get("why"),
            "live_px_price_after_fee": lv.get("am"), "live_px_line": lv.get("line"),
            # Oct 27 gettable-price counter (Muse): phase-1 qualifying (coded view, ignoring Muse AGREE), ProphetX at the
            # alert price or better at check (equivalent price, same rule as live), best ProphetX price seen at the alert line
            "p1_qualifies": (agree_rules.phase1(e, True)[0] if e else None),
            "px_gettable": ((r.get("px") is not None) if r.get("books") else None),
            "px_best_after_fee": ((r.get("books") or {}).get("prophetx") or {}).get("best_price_american"),
            "px_best_line": ((r.get("books") or {}).get("prophetx") or {}).get("line"),
            "live_order": dict({k: (lv.get("order") or {}).get(k) for k in ("status", "reason", "order_id", "asked_stake", "limit",
                                                                            "filled_stake", "avg_price")},
                               book=(lv.get("order") or {}).get("book") or "prophetx") if lv.get("order") else None}


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
    plays = read_verdicts(M) if SOURCE in ("muse", "both") else []
    rplays = rule_plays(now) if SOURCE in ("rules", "both") else []
    new = [p for p in plays + rplays if not already_handled(M, p)]
    M.logout()
    feed = load_feed()
    # wake time: this run's start vs the newest SENT alert (Oct 26; counts/seconds only in the public log)
    sent_ts = [iso_t(a.get("alert_utc")) for a in feed if a.get("sent_to_phone") and iso_t(a.get("alert_utc"))]
    newest = max(sent_ts) if sent_ts else None
    wake_s = (now - newest).total_seconds() if newest and now - newest < timedelta(minutes=30) else None
    trig = os.environ.get("GITHUB_EVENT_NAME", "local")
    if SOURCE in ("both",):
        muse_watchdog(now, plays, rplays, feed)
    print(f"Verdict plays seen (2 days): {len(plays)}; coded-rule alerts: {len(rplays)}; new: {len(new)}")
    if wake_s is not None:
        print(f"Wake: run started {wake_s:.0f}s after the newest sent alert (trigger: {trig})")
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
    held = positions.all_positions()   # Kalshi / ProphetX / Polymarket US open positions (read-only)
    if pos is None or any(v is None for v in held.values()):   # one immediate retry before holding anything
        time.sleep(5)
        if pos is None:
            pos = novig_positions()
        retry = {"kalshi": positions.kalshi_positions, "prophetx": positions.px_positions,
                 "polymarket_us": positions.pmus_positions}
        for b in [b for b, v in held.items() if v is None]:
            held[b] = retry[b]()
    blind = (["Novig"] if pos is None else []) + [BOOK_NAME[b] for b, v in held.items() if v is None]
    results, taken_now = [], set()
    M2 = imap_open()

    def taken(k):   # this run, or any earlier WOULD PLACE / PLACED entry
        return k in taken_now or bool(gsearch(M2, wp(k)))
    for p in new:
        try:
            ent = feed_entry(p, feed) or {}
            if ent:
                fs = agree_rules.first_side(ent, feed)
                if fs:   # coded fix 2 (Oct 26): first side stays against ANY earlier sent alert
                    ft = iso_t(fs.get("alert_utc"))
                    results.append({"play": p, "pid": pid(p["play_key"]), "verdict": "SKIP", "entry": ent,
                                    "reason": f"CONFLICT: opposite side of an earlier sent alert ({fs.get('bet')}, "
                                              f"{ft.astimezone(lm.ET).strftime('%a %I:%M %p ET') if ft else '?'}) - first side stays"})
                    continue
            if p.get("source") == "rules" and p["rules"]["verdict"] != "AGREE":
                d = p["rules"]
                results.append({"play": p, "pid": pid(p["play_key"]), "verdict": "SKIP",
                                "reason": f"rules gate {d['gate']}: {d['reason']}"})
                continue
            r = evaluate(p, now, evs_by, mks_by_event, pos, None if p.get("source") == "rules" else taken, held)
            r["entry"] = ent
            if p.get("source") != "rules" and ent:   # phase-1 live tag (Muse plays only: needs Muse AGREE)
                ok, why = agree_rules.phase1(ent, True)   # NCAAF/NBA spreads + unders, NFL unders only (Peter, Oct 26)
                if ok and r["verdict"] == "WOULD PLACE" and r.get("px"):
                    lr, lw = live_stake(r["px"]["shown"])
                    r["live"] = {"go": True, "risk": lr, "to_win": lw, "am": r["px"]["am"], "shown": r["px"]["shown"],
                                 "line": r["px"]["line"], "partial": r["px"]["avail"] < lr, "px": r["px"],
                                 "nfl": (ent.get("sport") or "").upper() == "NFL"}
                elif ok:
                    r["live"] = {"go": False, "why": ["ProphetX has nothing at the alert number or better"
                                                      if r["verdict"] == "WOULD PLACE" else (r.get("reason") or "skipped")]}
                else:
                    r["live"] = {"go": False, "why": why}
            if r["verdict"] == "WOULD PLACE" and blind:
                # can't see what's already held on every book: hold, retry next run, alert the phone once
                r = dict(r, verdict="HELD", reason="positions unreadable on " + ", ".join(blind))
                dk = derive_key(p) or p["play_key"]
                if not gsearch(M2, held_tok(dk)):
                    push("Bet held: " + (p.get("bet") or "")[:60],
                         f"{p.get('sport')} {p.get('game')}\nCouldn't check your open bets on {', '.join(blind)}. "
                         "Retrying every 10 min while the price is there. If you know you don't hold the other side, "
                         "you can place it by hand.")
            if r["verdict"] == "WOULD PLACE" and (r.get("live") or {}).get("go"):
                r["live"]["order"] = live_order(r)
            results.append(r)
            if r["verdict"] == "WOULD PLACE" and derive_key(p) and p.get("source") != "rules":
                taken_now.add(derive_key(p))
        except Exception as ex:
            results.append({"play": p, "pid": pid(p["play_key"]), "verdict": "SKIP", "reason": f"error: {str(ex)[:100]}"})
        results[-1]["decided_utc"] = datetime.now(timezone.utc)
    M2.logout()
    nw = sum(1 for r in results if r["verdict"] == "WOULD PLACE")
    when = now.astimezone(lm.ET).strftime('%a %b %d %I:%M %p ET')
    body = [(f"LIVE ON for phase 1 (ProphetX, ${LIVE_UNIT:.0f}); everything else is a dry run ({when})" if px_live.LIVE
             else f"DRY RUN - nothing was bet ({when})"), ""]
    places = [r for r in results if r["verdict"] == "WOULD PLACE"]
    helds = [r for r in results if r["verdict"] == "HELD"]
    skips = [r for r in results if r["verdict"] not in ("WOULD PLACE", "HELD")]
    if helds:
        body.append(f"HELD - retrying next run ({len(helds)})")
        body += [f"  - {r['play'].get('bet')}  ({r['play'].get('sport')} {r['play'].get('game')}): couldn't check your open "
                 f"bets on {', '.join(blind)}; it will try again in 10 minutes." for r in helds]
        body.append("")
    golive = [r for r in results if (r.get("live") or {}).get("go")]
    body.append(f"WOULD GO LIVE - phase 1, ${LIVE_UNIT:.0f} on ProphetX ({len(golive)})")
    body += [f"  - {bet_text(r, r['live']['line'], r['live']['shown'])} on ProphetX: risk {money(r['live']['risk'])} to win "
             f"{money(r['live']['to_win'])}  ({r['play'].get('sport')} {r['play'].get('game')})"
             + order_note(r['live'].get('order'))
             + ("  [partial: not all of it at this price]" if r["live"]["partial"] else "")
             + ("  [NFL: tagged for the dry run; in/out decided at the pre-live review]" if r["live"].get("nfl") else "")
             for r in golive] or ["  - none this run"]
    near = [r for r in results if r.get("live") and not r["live"]["go"] and len(r["live"].get("why") or []) == 1]
    if near:
        body.append("  (missed phase 1 on one condition: "
                    + "; ".join(f"{r['play'].get('bet')} - {r['live']['why'][0]}" for r in near) + ")")
    body.append("")
    if places:
        body.append(f"WOULD BET ({len(places)})")
        body += [plain(r) for r in places]
        body.append("")
    if skips:
        body.append(f"SKIPPED ({len(skips)})")
        body += [plain(r) for r in skips]
        body.append("")
    if pos is None:
        body += [f"Note: couldn't check your Novig positions this run ({_NVERR['why']}). Bets are held and retried next run.", ""]
    if any(v is None for v in held.values()):
        body += ["Note: positions not checked on " + ", ".join(BOOK_NAME[b] for b, v in held.items() if v is None)
                 + " this run (after one retry). Bets are held and retried next run.", ""]
    body += ["", "-" * 60, "DETAILS (for Muse)",
             f"Unit {money(UNIT)}: + money risks the unit, - money risks to win it. Prices after fees. Routing: every line within "
             "1 point on every book converted to its equivalent price at the alert line (half point from live ladders); best "
             "equivalent wins, ties to the better line; -130 cap on the price taken. Novig positions: "
             + (f"checked ({_NVERR.get('src', 'cloud read')})" if pos is not None else "unavailable") + "; " + positions.status_line(held) + ".", ""]
    for r in results:
        body.append(fmt(r))
        if r.get("books"):
            body += book_lines(r)
        body.append("")
    body += [f"Wake: this run started {wake_s:.0f}s after the newest sent alert (trigger: {trig})." if wake_s is not None
             else f"Wake: no sent alert in the last 30 min (trigger: {trig}).", ""]
    q = [r for r in results if r.get("entry") and agree_rules.phase1(r["entry"], True)[0]]
    if q:
        g = [r for r in q if r.get("px") is not None]
        body += [f"Gettable check (phase-1 qualifying this run, coded view): {len(q)} qualifying; ProphetX at the alert price "
                 f"or better at check: {len(g)}; not gettable: {sum(1 for r in q if r.get('books') and r.get('px') is None)}.", ""]
    if GUARD["ok"] is not None:
        body += [f"Live guards: {'OK' if GUARD['ok'] else 'REFUSED'}" + (f" - {GUARD['why']}" if GUARD["why"] else "")
                 + " (the daily stop counts only the bot's own orders).", ""]
    body += ["LEDGER (machine-readable, one row per play; latency = decision time minus first alert time)",
             json.dumps([ledger_row(r, now) for r in results], separators=(",", ":"))]
    first = ", ".join(short(r) for r in places[:3]) + ("..." if len(places) > 3 else "")
    nplaced = sum(1 for r in golive if (r["live"].get("order") or {}).get("status") == "placed")
    send((f"Bets LIVE: {nplaced} placed, " if px_live.LIVE else "Bets dry run: ") + f"{len(golive)} would go live, {nw} would bet" + (f" ({first})" if places else "") + (f", {len(helds)} held" if helds else "")
         + f", {len(skips)} skipped",
         "\n".join(body))
    print(f"Dry-run email sent: {len(golive)} would go live, {nw} would place, {len(helds)} held, {len(skips)} skipped.")   # counts only


if __name__ == "__main__":
    main()

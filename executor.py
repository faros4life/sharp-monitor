#!/usr/bin/env python3
"""
Auto-placement executor (Oct 23 spec; LIVE phase 1 added Oct 26). Real orders happen ONLY when the repo variable
EXEC_LIVE is "on": phase-1 plays on the coded rules AGREE (Oct 30; Muse is a veto, EXEC_RULES_LIVE=0 restores the gate),
$300 to win, best after-fee price on ProphetX / Kalshi / Polymarket US / Novig, resting bids Novig then Kalshi; refused on
STOP, the $415 per-order cap and the $2,250 daily stop. Everything else stays a dry run. It reads Muse's AUTO-PLACE VERDICTS emails, runs every skip check, prices all 4
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
import math
from concurrent.futures import ThreadPoolExecutor
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
import lane2   # Nov 4: Lane 2 LOW-limit sharp alerts, DRY RUN ONLY (Peter 4:01 PM "no live play")
import positions
import px_live
import book_live

UNIT = float(os.environ.get("EXEC_UNIT", "") or "300")          # + money: risk UNIT; - money: risk to win UNIT
SOURCE = (os.environ.get("EXEC_SOURCE", "") or "both").lower()  # muse | rules | both (dry run: both, side by side)
RULES_LOOKBACK_H = 6                                             # coded rules look at alerts first sent in the last 6 h
MIN_LEAD_MIN = float(os.environ.get("EXEC_MIN_LEAD_MIN", "") or "60")
CAP_LINE = -130                                                  # spreads/totals: never worse than -130
PMUS = "https://gateway.polymarket.us"
PMUS_FEE = 0.06                                                  # Polymarket US taker, their published schedule
# ELIGIBILITY FREEZE (Peter, Nov 6): correcting the taker fee DOWN makes every Polymarket US net
# price better, so a raw price that used to miss the -130 cap or the alert threshold could now
# clear it. That would be the correction CREATING a bet, which Peter prohibited. So selection and
# economics use the corrected 0.06, while the eligibility GATES price Polymarket US at the old,
# stricter coefficient. The correction can therefore improve which venue we choose, and can never
# make a bet eligible that was not eligible before.
PMUS_QUAL_FEE = 0.0695
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


def imap_close(M):
    """Logout is a courtesy, never a result. Nov 8: Gmail dropped the socket on imap_close(M) and
    failed signal-alerts run 42510394524 AFTER every piece of its work was done - a completed run
    reported as a failure. A send on a half-closed TLS socket raises SSLEOFError/IMAP4.abort, and
    there is nothing to recover: the mailbox was opened readonly and the server reaps the session
    anyway. So never let the close fail the caller. Use this everywhere instead of imap_close(M)."""
    try:
        M.logout()
    except Exception:
        pass


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
MANUAL_HELD = {}   # Oct 30: play key -> "duplicate"/"conflict" from Peter's manual bets on books the bot can't read


def read_manual(M):
    """Peter's manual bets on books with no read path (Hard Rock), logged as private 'Bets manual:' notes in the Bets
    inbox (last 3 days). Body lines: MANUAL: {"sport": "NBA", "game": "Away @ Home", "bet": "Under 225.5 (-110)", "book": "Hard Rock"}
    (bet text in the feed's format WITH the price: "Team +3.5 (-110)", "Team ML (+130)", "Under 225.5 (-110)")
    Same side -> duplicate, other side -> conflict: no live order or resting bid on either."""
    for uid in gsearch(M, 'subject:"Bets manual" newer_than:3d'):
        typ, data = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            continue
        for line in body_text(data[0][1]).splitlines():
            m = re.match(r"\s*MANUAL:\s*(\{.*\})\s*$", line)
            if not m:
                continue
            try:
                d = json.loads(m.group(1))
            except Exception:
                LOG.append("unreadable MANUAL line")
                continue
            k, ok_ = derive_key(d), opposite_key(d)
            if k:
                MANUAL_HELD[k] = "duplicate"
            if ok_:
                MANUAL_HELD.setdefault(ok_, "conflict")


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


BOARD_LIVE = (os.environ.get("EXEC_BOARD_LIVE") or "off").strip().lower() == "on"   # Lane 3 money switch (repo variable)
BOARD_CONFIRM_MIN = 15   # Lane 3: a PLAY call must still be PLAY 15 min after it posted (the board's gettable-price basis)


def board_plays(now):
    """Nov 3 (Peter 2:01 PM "ok build"; rulebook v5 Lane 3): board PLAY calls (NBA totals, overs and unders) that
    survive: money not pulled, price not moved toward the side, still PLAY >= 15 min after posting, game not started.
    Same downstream path as every play: books checked, line floor, caps, stacking, positions, live guards. Places money
    only when EXEC_BOARD_LIVE is "on" AND live is on; otherwise a dry-run WOULD PLACE.

    LABEL CORRECTION, Nov 6 (Peter). This read "Bets Board v2 PLAY calls" and stamped every row it emitted
    "board v2 PLAY (Lane 3)". It never selected on v2. It filters on r["tag"], and score() leaves the V3
    tag there (v2 is kept in r["v2"], v1 in r["v1"]), so the shadow has been driven by the v3 rule - NBA
    total, 4h+ lead, money still there, one play per game, nightly cap 5 - which applies no money,
    confirmation, sharp-agreement or fights test. Rows now carry the version that actually produced them
    plus what v2 and v1 said, so the shadow record reads honestly. Selection, sizing, alerts and orders
    are UNCHANGED by this correction.

    Dedup caveat, same date: derive_key() still keys on the raw game STRING, not event_id.py's canonical
    event. So two books naming one game differently ("Cavaliers vs. Thunder" / "Cleveland vs Oklahoma
    City") are still two keys here, while two different lines on one game-string collapse into one. Not
    changed in this commit - it alters selection, which needs Peter's approval."""
    try:
        import board_build as bb
        _, rows, _ = bb.build(upcoming=True)
    except Exception as ex:
        LOG.append(f"board unreadable: {str(ex)[:60]}")
        return []
    out, seen = [], set()
    for r in sorted(rows, key=lambda r: r["at"]):
        x = r["x"]
        if r.get("tag") != "PLAY" or r.get("status") != "still there" or x.get("pulled") or x.get("artifact"):
            continue
        if (x.get("league") or "") != "NBA" or x.get("market") != "total":
            continue
        st = iso_t(x.get("start_utc"))
        if not st or st <= now or not r.get("at") or now - r["at"] < timedelta(minutes=BOARD_CONFIRM_MIN):
            continue
        sd, ln, am = x.get("side"), x.get("line"), x.get("price_american")
        if sd not in ("OVER", "UNDER") or ln is None or am is None:
            continue
        p = {"sport": "NBA", "game": x.get("game") or "", "bet": f"{'Over' if sd == 'OVER' else 'Under'} {float(ln):g} ({int(am):+d})",
             "start_utc": x.get("start_utc"), "late": False, "source": "board", "alert_utc": x.get("alerted_utc"),
             "rules": {"verdict": "AGREE", "gate": None,
                       # Nov 6: the version that actually produced this row, not "v2" as it used to say.
                       "reason": f"board v3 PLAY (Lane 3) [v2={r.get('v2')}, v1={r.get('v1')}]"},
             "board_entry": {"alert_utc": x.get("alerted_utc"), "book_key": x.get("book"), "price_after_fee": am,
                             "point": ln, "sport": "NBA", "bet": None}}
        k = derive_key(p)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(dict(p, play_key="board|" + k))
    return out


def same_bet(k1, k2):
    """Same bet from two lanes despite different game spellings ('Hawks vs. Hornets' / 'Atlanta Hawks @ Charlotte Hornets'):
    same league, market and side, and each team of one shares a name word with a team of the other."""
    try:
        a = (k1.split("|", 1)[1] if k1.startswith(("board|", "rule|")) else k1).split("|")
        b = (k2.split("|", 1)[1] if k2.startswith(("board|", "rule|")) else k2).split("|")
        if len(a) != 4 or len(b) != 4 or a[0] != b[0] or a[2] != b[2]:
            return False
        ta, tb = lm.split_teams(a[1]) or (), lm.split_teams(b[1]) or ()
        if len(ta) != 2 or len(tb) != 2:
            return False
        sa, sb = [lm.toks(x, a[0]) for x in ta], [lm.toks(x, a[0]) for x in tb]
        if not all(any(x & y for y in sb) for x in sa):
            return False
        if a[2] == "total":
            return a[3] == b[3]
        return bool(lm.toks(a[3], a[0]) & lm.toks(b[3], a[0]))
    except Exception:
        return False


def opp_bet(k1, k2):
    """Nov 3 (Peter 2:51 PM: "if a bet is in and the other side comes in, the 2nd bet does not get played"): k2 is the OTHER
    side of k1's game and market (totals: OVER vs UNDER; spreads / moneylines: the other team), across any lane."""
    try:
        a = (k1.split("|", 1)[1] if k1.startswith(("board|", "rule|")) else k1).split("|")
        b = (k2.split("|", 1)[1] if k2.startswith(("board|", "rule|")) else k2).split("|")
        if len(a) != 4 or len(b) != 4 or a[0] != b[0] or a[2] != b[2]:
            return False
        ta, tb = lm.split_teams(a[1]) or (), lm.split_teams(b[1]) or ()
        if len(ta) != 2 or len(tb) != 2:
            return False
        sa, sb = [lm.toks(x, a[0]) for x in ta], [lm.toks(x, a[0]) for x in tb]
        if not all(any(x & y for y in sb) for x in sa):
            return False
        if a[2] == "total":
            return {a[3], b[3]} == {"OVER", "UNDER"}
        return not (lm.toks(a[3], a[0]) & lm.toks(b[3], a[0]))
    except Exception:
        return False


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


LIVE_UNIT = 300.0   # phase-1 live unit, to win (Oct 28, Peter: $50 -> $200; Nov 9, Peter: $200 -> $300. Same basis:
                    # to-win on minus, risk on plus. The $415 per-order cap and $2,250 daily stop moved with it - at
                    # $300 to win, -130 risks $390, which the old $275 cap would have refused on every minus-money order.
MIN_ORDER = 50.0    # Oct 28: smallest order / routing remainder worth placing (was $5)

# BOARD v3 / LIQ-BOT CONTROLLED PILOT UNIT (Peter, 11 Nov, written approval). Its own unit, so Lane 1
# is untouched at $300. Same to-win/risk asymmetry as Lane 1: minus money sizes to WIN the unit,
# plus money RISKS it. Every sizing helper below takes `unit` and DEFAULTS TO LIVE_UNIT, so every
# pre-existing Lane 1 call site is byte-for-byte unchanged in behaviour.
BOARD_UNIT = 200.0


def unit_for(lane):
    """The live unit for a lane. Only the board pilot differs; everything else is Lane 1's unit."""
    return BOARD_UNIT if str(lane or "") == "board" else LIVE_UNIT


def live_stake(am, unit=None):
    """(risk, to_win) for one unit, per PETER'S RULE, Nov 10: "If + money we bet 300. That's the rule."

    Minus money sizes to WIN the unit: -110 risks $330 to win $300.
    Plus money RISKS the unit: +150 risks $300 to win $450.

    This asymmetry is DELIBERATE and is not to be "corrected". I changed it on Nov 10 after a
    review called the unit inconsistent - the mechanics I described were right (plus money does
    risk $300 rather than win $300) but the intent was not mine to infer, and Peter's rule is the
    rule. Reverted within minutes; no order was placed in the window. The lesson is that verifying
    a finding's arithmetic is not the same as verifying that the behaviour is unintended, and a
    live-money default is exactly where that distinction matters.

    ProphetX takes 2% of winnings (liquidity_monitor.PX_FEE), so the minus-money $300 nets about
    $294 there. Left as gross, per the same rule.

    `unit` overrides the lane's stake and defaults to LIVE_UNIT, so Lane 1 call sites are unchanged.
    The board pilot passes BOARD_UNIT ($200 to win).
    """
    u = float(unit if unit else LIVE_UNIT)
    risk = u if am > 0 else u * abs(am) / 100
    return round(risk, 2), round(u * am / 100 if am > 0 else u, 2)


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
            imap_close(M)
    except Exception as ex:
        print(f"watchdog check failed: {str(ex)[:60]}")
        return 0
    for p, ent, tok, mins in late:
        head = f"{p.get('sport')} {p.get('game')} | {p.get('bet')}\nQualifies for LIVE, no Muse verdict after {mins} min. "
        # THE TEXT HAS TO MATCH THE GATE, and for ten days it did not. Since Oct 30 Muse is a VETO:
        # RULES_LIVE defaults on, so a missing verdict blocks nothing and only a DISAGREE stops a
        # play. The phone push below was correctly silenced then, but this message still said "Live
        # won't bet it without Muse AGREE. Ping Muse." and the EMAIL sent it unconditionally. On
        # Nov 9 I read that line in the watchdog mail and told Peter the reason there were no plays
        # was Muse's silence. It was not - Lane 1 is totals-unders-only and the day's candidates
        # were overs and spreads. A stale sentence in an alert cost a wrong answer, so the text now
        # follows RULES_LIVE instead of restating a gate that is off.
        msg = head + ("This blocks nothing - Muse is a veto, so only a DISAGREE stops a play. "
                      "Note only, no action needed." if RULES_LIVE else
                      "Live won't bet it without Muse AGREE. Ping Muse.")
        if not RULES_LIVE:   # Oct 30: with coded-AGREE live, a missing Muse verdict blocks nothing -> no phone message
            push("No Muse verdict: " + (p.get("bet") or "")[:50], msg, mirror=False)
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


def push(title, body, mirror=True):
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
    if mirror:   # Oct 27 (Peter): every ntfy push also lands in Telegram; mirror=False where a tg() line already says it
        tg(f"{title}\n{body}")


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
    """Handled before under its own key OR under the play's game+side key (so a re-sent play never runs twice).

    Nov 8: gsearch_strict, NOT gsearch. This is the duplicate-bet guard, and lenient gsearch returns
    [] on a failed Gmail search - which this function then reads as "never placed before" and the bot
    places the bet a second time. A guard that answers "no" when it cannot see is fail-open on money.
    Strict raises instead, which aborts the run and places nothing. Run 42351892592 (7 Nov) proved the
    search layer really does drop mid-call: SSLEOFError inside this very function."""
    if p.get("source") in ("rules", "lane2"):   # separate namespace, so Muse's verdict on the same play is still evaluated (Lane 2 too: it never blocks or is blocked by another lane's record)
        return bool(gsearch_strict(M, pid(p["play_key"])))
    keys = {p["play_key"], derive_key(p) or p["play_key"]}
    return any(gsearch_strict(M, pid(k)) for k in keys)


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
    if "full_game" not in smt or any(w in smt for w in ("half", "quarter", "period", "inning", "team_total", "player",
                                                         "team_points")):   # Nov 4: team points totals (slug "-tt-")
        return None
    if "-tt-" in (mk.get("slug") or ""):
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
        # PMUS_FEE prices the economics; PMUS_QUAL_FEE freezes every eligibility gate at the old rate
        return bc.ladder_result(levels, price, line, pline, {"market_slug": mk["slug"], "long_side": is_long},
                                PMUS_FEE, PMUS_QUAL_FEE)
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


def _snap_read(tok):
    req = urllib.request.Request(SNAP_URL, headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github.raw+json",
                                                    "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor"})
    with urllib.request.urlopen(req, timeout=15) as r:
        snap = json.loads(r.read().decode())
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(snap["snapshot_utc"].replace("Z", "+00:00"))).total_seconds() / 60
    return snap, age


def _snap_refresh(tok):
    """Oct 28: GitHub runs the home PC's 5-minute schedule late (gaps of an hour seen), so when the snapshot is stale the
    executor asks the home PC for a fresh one now (workflow_dispatch; the token has Actions write on novig-runner)."""
    for wf in ("novig-positions_1.yml", "novig-positions.yml"):
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/faros4life/novig-runner/actions/workflows/{wf}/dispatches",
                                         data=json.dumps({"ref": "main"}).encode(), method="POST", headers={
                                             "Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                                             "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor",
                                             "Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15).read()
            return True
        except Exception:
            continue
    return False


def novig_snapshot():
    """Novig positions written by Peter's home runner (private repo novig-runner), read with a token scoped to that repo
    (secret NOVIG_SNAPSHOT_TOKEN). Stale (>15 min) -> ask the home PC for a fresh one and wait up to ~90 s.
    Still stale, failed, or unreadable -> None (held)."""
    tok = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
    if not tok:
        _NVERR["why"] += " | no snapshot token"
        return None
    try:
        snap, age = _snap_read(tok)
        if (age > SNAP_MAX_MIN or not snap.get("ok")) and _snap_refresh(tok):
            for _ in range(9):
                time.sleep(10)
                try:
                    s2, a2 = _snap_read(tok)
                except Exception:
                    continue
                if a2 < age:
                    snap, age = s2, a2
                    break
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


LIVE_BOOKS = tuple(b.strip() for b in (os.environ.get("EXEC_LIVE_BOOKS") or "prophetx,kalshi,polymarket_us,novig").split(",")
                   if b.strip())   # Oct 28 (Peter): books the bot may fill phase-1 plays on; repo VARIABLE EXEC_LIVE_BOOKS
PX_TOL_CENTS = 2   # Peter, Oct 27: ProphetX (the live book) may fill up to 2 cents worse than the alert's after-fee price
# Peter, Nov 11: Novig gets the SAME 2-cent allowance as ProphetX, on BOTH lanes (phase 1 and board v3).
# Kalshi and Polymarket US keep zero tolerance - their fee-adjusted pricing rules are unchanged.
# Eligibility only: the allowance widens the gate and the depth threshold, never the ranking key (c_eq).
TOL_BOOKS = tuple(x.strip() for x in (os.environ.get("EXEC_TOL_BOOKS", "") or "prophetx,novig").split(",") if x.strip())

# Peter, Nov 6: on an EXACT net-price tie, a fixed documented venue order, applied identically in
# selection and in reporting, so the choice is deliberate and reproducible rather than whatever
# order a dict happened to iterate in.
VENUE_ORDER = ("novig", "prophetx", "kalshi", "polymarket_us")


def venue_rank(book):
    return VENUE_ORDER.index(book) if book in VENUE_ORDER else len(VENUE_ORDER)


def qual_price(am, book):
    """The price the ELIGIBILITY gates see. Identical to `am` everywhere except Polymarket US,
    where it is re-priced at the old, stricter taker fee so the fee correction cannot admit a bet
    that would previously have been skipped. Pure arithmetic: invert the new fee to recover the
    screen price, then re-apply the old one."""
    if book != "polymarket_us":
        return am
    if am is None:
        return None
    try:
        e = american_to_prob(am)                      # cost after the CORRECTED fee
        k = PMUS_FEE
        c = ((1 + k) - math.sqrt((1 + k) ** 2 - 4 * k * e)) / (2 * k) if k else e   # screen cost
        q = PMUS_QUAL_FEE
        v = lm.american(min(max(c + q * c * (1 - c), 0.01), 0.99))                  # old-fee cost
        return v if v is not None else None
    except Exception:
        # FAILS CLOSED (Peter, Nov 6). Returning `am` here would hand an eligibility gate the
        # PERMISSIVE 0.06 price, which is exactly the thing the freeze exists to prevent. A
        # Polymarket US candidate whose frozen basis cannot be computed is rejected, not admitted.
        return None


def cents_worse(am, c):
    """An American price c cents worse for the bettor (-109 -> -111; +105 -> +103; +101 -> -101)."""
    am = int(am)
    if am < 0:
        return am - c
    w = am - c
    return w if w >= 100 else -(100 + (100 - w))


WIN_FEE = {"prophetx": 0.02}   # fee on winnings: a ProphetX win nets 98% of the screen payout.
# NHL is NOT on this schedule - ProphetX prices NHL on a 0.035 taker scale. sharp_monitor.net()
# carries that split; this table is used for the win-net display below, which is a non-NHL path.


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
        """Each book's ladder at one line (the books pick their nearest strike; kept only if it IS this line).
        Oct 31: the 4 books are read at the same time (ProphetX keeps its own 1/sec pace)."""
        def one(b):
            try:
                if b == "novig":
                    return bc.check_alert(dict(al, bet=bet_at(al["bet"], mtype, line, ln)), evs_by, mks_by_event)
                fn = {"prophetx": bc.px_check, "kalshi": bc.kalshi_check, "polymarket_us": pmus_check}[b]
                return fn(al, mtype, side, ln, price, teams)
            except Exception as ex:
                return {"status": f"error: {str(ex)[:80]}"}
        books = ("novig", "prophetx", "kalshi", "polymarket_us")
        with ThreadPoolExecutor(max_workers=4) as tp:
            return dict(zip(books, tp.map(one, books)))

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
    with ThreadPoolExecutor(max_workers=4) as tp:   # Oct 31: the nearby lines are probed at the same time
        probed = dict(zip(lines[1:], tp.map(probe, lines[1:])))
    for ln in lines:
        got = res if ln == line else probed[ln]
        for b, r in got.items():
            bl = book_line(r) if mtype != "moneyline" else None
            if r.get("status") == "ok" and r.get("best_price_american") is not None and \
                    (mtype == "moneyline" or (bl is not None and abs(bl - ln) < 1e-9)):
                ladders[(b, bl)] = r
    hp, hp_src = half_point(ladders, mtype, side, al["sport"])
    # Oct 27 (Peter): the bar is the alert's AFTER-FEE price (what the alert really cost), compared with each book's
    # after-fee price - before this, the alert's screen price was compared with after-fee prices, so a ProphetX alert
    # could never be matched on ProphetX itself (its 2% fee always made it ~2c worse than its own screen).
    ent0 = feed_entry(p, load_feed()) or {}
    alert_af = ent0.get("price_after_fee") if ent0.get("price_after_fee") is not None else p.get("price_after_fee")
    try:
        alert_af = int(alert_af) if alert_af is not None else price
    except Exception:
        alert_af = price
    alert_cost = american_to_prob(alert_af)
    px_tol = american_to_prob(cents_worse(alert_af, PX_TOL_CENTS)) - alert_cost   # Oct 27 ProphetX, Nov 11 Novig: may be 2c worse
    floor = p.get("floor_line") if mtype in ("spread", "total") else None
    cands, floor_blocked, no_qual_basis = [], 0, 0
    for (b, bl), r in ladders.items():
        if floor is not None and better_halfpoints(mtype, side, floor, bl) < -1e-9:
            floor_blocked += 1   # Oct 31 (Muse): the alert's bet-only-at LINE is a hard floor, whatever the converted price
            continue
        hb = 0.0 if mtype == "moneyline" else better_halfpoints(mtype, side, line, bl)
        am = r["best_price_american"]
        # frozen for Polymarket US, identical elsewhere. The ladder now carries it directly; the
        # arithmetic inversion stays only as a fallback for a checker that has not been updated.
        am_q = r.get("best_price_american_qual")
        if am_q is None:
            am_q = qual_price(am, b)
        if am_q is None:                              # FAILS CLOSED: no frozen basis -> no candidate
            no_qual_basis += 1
            continue
        c_eq = american_to_prob(am) - hb * hp
        c_eq_q = american_to_prob(am_q) - hb * hp     # what the eligibility gates compare
        tol = px_tol if b in TOL_BOOKS else 0.0
        if c_eq_q > alert_cost + tol + 1e-9:          # gate on the frozen price, never the improved one
            continue
        thr = lm.american(min(max(alert_cost + tol + hb * hp, 0.01), 0.99))   # worst acceptable real price at this line
        if mtype in ("spread", "total") and thr is not None:
            thr = max(thr, CAP_LINE)   # Oct 28: never fill below the -130 after-fee cap, whatever the line conversion says
        # the liquidity gate reads the FROZEN per-level price, never the corrected one
        avail = sum(d for a, d in levels(b, r, qual=True) if a is not None and thr is not None and a >= thr)
        if avail <= 0:
            continue
        shown = r.get("best_price_american_displayed")
        cands.append({"book": b, "line": bl, "am": am, "shown": int(shown) if shown is not None else am, "eq": lm.american(min(max(c_eq, 0.01), 0.99)), "c_eq": c_eq,
                      "am_q": am_q,
                      "hb": hb, "avail": avail, "thr": thr, "buy": r.get("buy_levels") or [],
                      "ids": {k: r.get(k) for k in ("kalshi_buy", "market_slug", "long_side", "outcome_id") if r.get(k) is not None}})
    if not cands:
        if no_qual_basis:
            return dict(out, verdict="SKIP", reason=f"no frozen qualification price on "
                                                    f"{no_qual_basis} candidate(s) - rejected safely")
        if not ladders:
            return dict(out, verdict="SKIP", reason="no book lists this market near the alert line")
        if floor_blocked and floor_blocked == len(ladders):
            return dict(out, verdict="SKIP", reason=f"no fill - blocked by bet-only-at floor ({fmt_line(mtype, floor)})")
        return dict(out, verdict="SKIP", reason=f"price: nothing at or better than {alert_af:+d} after fees "
                                                f"({'/'.join(TOL_BOOKS)}: {cents_worse(alert_af, PX_TOL_CENTS):+d}) at {fmt_line(mtype, line)} "
                                                f"(equivalent, after fees; half point = {hp * 100:.1f}c {hp_src})"
                                                + (f"; {floor_blocked} line(s) blocked by bet-only-at floor "
                                                   f"({fmt_line(mtype, floor)})" if floor_blocked else ""))
    # the -130 cap applies to the FROZEN price too, so the correction cannot lift a bet over it
    capped = [c for c in cands if not (mtype in ("spread", "total") and c["am_q"] < CAP_LINE)]
    if not capped:
        best = min(cands, key=lambda c: c["c_eq"])
        return dict(out, verdict="SKIP", reason=f"price cap: best take is {best['book']} {best['am']:+d} at "
                                                f"{fmt_line(mtype, best['line'])}, worse than {CAP_LINE}")
    # best equivalent price; tie -> better line; still tied -> the fixed documented venue order
    capped.sort(key=lambda c: (round(c["c_eq"], 6), -c["hb"], venue_rank(c["book"])))
    # stake is sized on the price on the book's screen (Peter, Oct 25: same as ntfy and Muse); routing/cap stay after-fee
    full = [c for c in capped if c["avail"] >= stake_for(c["shown"])[0]]
    pick = (full or capped)[0]
    risk, win = stake_for(pick["shown"])
    nets = round(win * (1 - WIN_FEE.get(pick["book"], 0)), 2)
    pxc = next((c for c in capped if c["book"] == "prophetx"), None)
    # Oct 28 (Peter): phase-1 live fills on the best after-fee price among the LIVE books
    # (ProphetX keeps its 2c; Novig gets the same 2c from Nov 11 - see TOL_BOOKS)
    lcs = [c for c in capped if c["book"] in LIVE_BOOKS]
    _u = unit_for("board" if p.get("source") == "board" else None)
    lfull = [c for c in lcs if c["avail"] >= live_stake(c["shown"], _u)[0]]
    lc = (lfull or lcs)[0] if lcs else None
    return dict(out, verdict="WOULD PLACE", book=pick["book"], american=pick["am"], shown=pick["shown"], take_line=pick["line"],
                px=({"am": pxc["am"], "shown": pxc["shown"], "line": pxc["line"], "avail": pxc["avail"], "thr": pxc["thr"],
                     "buy": pxc["buy"]} if pxc else None),
                lc=({"book": lc["book"], "am": lc["am"], "shown": lc["shown"], "line": lc["line"], "avail": lc["avail"],
                     "thr": lc["thr"], "buy": lc["buy"], "ids": lc["ids"]} if lc else None),
                lcs=[{"book": c["book"], "am": c["am"], "shown": c["shown"], "line": c["line"], "avail": c["avail"],
                      "thr": c["thr"], "buy": c["buy"], "ids": c["ids"]} for c in lcs],
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


def levels(book, r, qual=False):
    """[(American price after fees, dollars)] from a checker's ladder.

    qual=True returns the FROZEN eligibility price per level (Peter, Nov 6). Every gate - threshold,
    liquidity, full size, partial size and the -130 cap - reads this one, so a fee correction can
    never lift a level over a gate it previously failed. Identical to the economic price on every
    venue except Polymarket US."""
    out = []
    # FAILS CLOSED for Polymarket US (Peter, Nov 6): when a frozen price is missing we contribute
    # NO liquidity from that level rather than falling back to the permissive economic price.
    strict = bool(qual) and book == "polymarket_us"
    for x in r.get("buy_levels") or []:
        if qual:
            a = x.get("american_after_fee_qual")
            if a is None:
                if strict:
                    continue                          # no frozen basis -> this level does not count
                a = x.get("american_after_fee", x.get("american"))
        else:
            a = x.get("american_after_fee", x.get("american"))
        out.append((a, x.get("dollars") or 0))
    if not out:
        if qual:
            b = r.get("best_price_american_qual")
            if b is None and strict:
                return []                             # no frozen basis at all -> no liquidity
            if b is None:
                b = r.get("best_price_american")
        else:
            b = r.get("best_price_american")
        if b is not None:
            out.append((b, r.get("dollars_at_alert_price_or_better") or 0))
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
    return ("[coded rules] " if p.get("source") == "rules" else "[board Lane 3] " if p.get("source") == "board"
            else "[Lane 2 dry run] " if p.get("source") == "lane2"
            else ("[Muse] " if SOURCE == "both" else ""))


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
    rested = ((r.get("live") or {}).get("rest") or {}).get("status") == "placed"   # Oct 28: a resting bid takes the side too
    tag = r["pid"] + (f" {wp(dk)}" if ((r["verdict"] == "WOULD PLACE" or rested) and dk and p.get("source") not in ("rules", "lane2")) else "")   # Nov 4: a Lane 2 dry-run row never marks a side as taken
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
    NONPX["today"] = 0.0
    # Nov 1 (Peter, "1a"): a non-ProphetX bot bet whose game is already graded in the feed no longer counts as lost:
    # a WIN or PUSH frees its money for the daily stop, a LOSS counts in full, ungraded still counts in full (safe side).
    graded = {}
    try:
        for e in load_feed():
            k = derive_key(e)
            if k and e.get("result") in ("W", "L", "P"):
                graded[k] = e["result"]
    except Exception:
        graded = {}
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
                for is_rest, lo in ([(False, row.get("live_order") or {}), (True, row.get("live_rest") or {})]
                                    + [(False, x or {}) for x in (row.get("live_more") or [])]):
                    if lo.get("status") != "placed" or not lo.get("order_id"):
                        continue
                    ids[str(lo["order_id"])] = lo.get("book") or "prophetx"
                    if row.get("key"):
                        LIVEKEYS.add(row["key"])
                    try:   # Oct 28: Kalshi / PM US / Novig dollars risked TODAY (ET) count as lost in the daily stop
                        d_et = datetime.fromisoformat(str(row.get("decided_utc")).replace("Z", "+00:00")).astimezone(lm.ET).date()
                    except Exception:
                        d_et = None
                    # BOARD v3 PILOT ACCOUNTING (Peter, 11 Nov). Same ledger pass, same ET day. The
                    # ledger row already carries "source", so the board lane is separable without a
                    # new registry. The PLAY COUNT is taken BEFORE the settled-win skip, because a
                    # won play still used one of the 10 slots; the RISK figure is taken after, so a
                    # settled win or push stops consuming the $1,500.
                    if row.get("source") == "board" and d_et in (None, datetime.now(lm.ET).date()):
                        if row.get("key"):
                            BOARD["keys"].add(row["key"])      # one intended bet = one play, so a
                            # retry, a top-up or a partial fill of the same key never counts twice
                        if graded.get(row.get("key")) not in ("W", "P"):
                            fs_b = lo.get("filled_stake")
                            BOARD["risk"] += (max(float(fs_b or 0), float(lo.get("asked_stake") or 0))
                                              if (is_rest or fs_b is None) else float(fs_b))
                    if graded.get(row.get("key")) in ("W", "P"):
                        continue   # settled win/push: not a loss toward the daily stop
                    if (lo.get("book") or "prophetx") != "prophetx" and d_et in (None, datetime.now(lm.ET).date()):
                        fs = lo.get("filled_stake")   # fill-or-kill: what filled (unknown = all asked); resting: all asked
                        NONPX["today"] += (max(float(fs or 0), float(lo.get("asked_stake") or 0)) if (is_rest or fs is None)
                                           else float(fs))
        BOARD["known"] = True   # the ledger parsed, so today's board exposure above is real
        return ids
    except Exception:
        return None


def _h(x):
    return hashlib.sha1(str(x).encode()).hexdigest()[:12]


GUARD = {"ok": None, "why": ""}
NONPX = {"today": 0.0}   # Oct 28: bot dollars risked today on books other than ProphetX (from the ledger registry)

# ---------------------------------------------------------------- Board v3 pilot limits (Peter, 11 Nov)
# Lane-specific and ADDITIONAL to the global stop, which is untouched: px_live.preflight() still runs
# first and still refuses on the aggregate $2,250. These limits can only ever REFUSE a board order.
BOARD_DAILY_RISK = float(os.environ.get("EXEC_BOARD_DAILY_RISK", "") or "1500")
BOARD_MAX_PLAYS = int(os.environ.get("EXEC_BOARD_MAX_PLAYS", "") or "10")   # was 5 on the board; 10 for the pilot
# DAY BOUNDARY: America/New_York (lm.ET), the same boundary the global daily stop uses. A play is
# counted on the ET date of its decided_utc, so a 1 AM ET order belongs to that ET day, not UTC's.
BOARD = {"risk": 0.0, "keys": set(), "known": False}


def board_gate(risk, key=None):
    """(ok, why) for ONE board v3 order of `risk` dollars. Fail closed.

    Enforced HERE, in the executor, not on the board page - the board only tags calls, it cannot
    know what was submitted or is resting. Counts submitted AND resting orders; a retry, top-up or
    partial fill of the same intended bet shares its key and never counts as an extra play.

    The 10-play cap CANNOT override the risk limit: both are checked, and either one refuses."""
    if not BOARD["known"]:
        # The board ledger was not readable this run, so today's board exposure is unknown. An
        # unknown exposure can never be allowed to place money - same rule as the global registry.
        return False, "board exposure unknown this run (ledger unreadable) - fail closed"
    n = len(BOARD["keys"]) + (0 if (key and key in BOARD["keys"]) else 1)
    if n > BOARD_MAX_PLAYS:
        return False, (f"board play cap: {len(BOARD['keys'])} already submitted or resting today (ET), "
                       f"cap {BOARD_MAX_PLAYS}")
    try:
        risk = float(risk or 0)
    except Exception:
        return False, "board order risk unreadable - fail closed"
    if risk <= 0:
        return False, "board order risk is zero - fail closed"
    if BOARD["risk"] + risk > BOARD_DAILY_RISK + 1e-9:
        return False, (f"board daily risk limit: ${BOARD['risk']:,.2f} already at risk today (ET) + "
                       f"${risk:,.2f} would exceed ${BOARD_DAILY_RISK:,.0f}")
    return True, (f"ok (board today: {len(BOARD['keys'])}/{BOARD_MAX_PLAYS} plays, "
                  f"${BOARD['risk']:,.2f}/${BOARD_DAILY_RISK:,.0f} at risk)")


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
            imap_close(M)
        px_live.set_bot_orders(None if ids is None else list(ids))
        book_live.set_exposure(NONPX["today"])
        if ids is None:
            why = "couldn't read the bot's order registry in Gmail (fail closed)"
        else:
            ok = True
    except Exception as ex:
        why = f"live guard check failed ({str(ex)[:60]}) - fail closed"
    GUARD.update(ok=ok, why=why)
    return ok, why


def live_order(r):
    """Phase-1 live order (only when EXEC_LIVE is on): ProphetX here, Kalshi / Polymarket US via live_order_other (Oct 28).
    Returns the order record for the email/ledger."""
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
    if lv.get("book", "prophetx") != "prophetx":
        return live_order_other(r)
    strike, limit, stake = px_limit(lv["px"], lv["risk"])
    if not strike or stake < MIN_ORDER - 0.01:
        return {"status": "refused", "reason": f"ProphetX ladder can't cover ${MIN_ORDER:.0f}+ at the alert number (have ${stake:.2f})"}
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
             + ("" if res.get("fills_read") else " Fill read failed: check My Trades."), mirror=False)
    elif res["status"] == "error":
        tg(f"LIVE ORDER ERROR ProphetX: {(p.get('bet') or '')[:60]}\n{res['reason'][:200]}\nCheck My Trades before retrying.")
        push("LIVE ORDER ERROR: " + (p.get("bet") or "")[:50], f"{label}\n{res['reason']}\nCheck ProphetX My Trades before retrying.", mirror=False)
    return dict(res, asked_stake=stake, limit=limit, book="prophetx")


def _got(o):
    """Dollars an order took: filled if read, everything asked if unknown (Novig via the home PC, unread fills)."""
    if not o or o.get("status") != "placed":
        return 0.0
    if o.get("sent_to_runner") or o.get("filled_stake") is None:
        return float(o.get("asked_stake") or 0)
    return float(o.get("filled_stake") or 0)


def live_remainder(r):
    """Oct 28 (Peter): the unit is $200 total per play across venues. After the best book's fill, take what's left on
    the next live books at the alert number or better (each its own threshold), skipping remainders under MIN_ORDER.
    Stops at the first refusal or error (fail closed)."""
    lv, more = r["live"], []
    first = lv.get("order") or {}
    if first.get("status") != "placed":
        return more
    target = lv["risk"]
    used = {lv["book"]}
    got = _got(first)
    for c in (r.get("lcs") or []):
        rem = round(target - got - sum(_got(o) for o in more), 2)
        if rem < MIN_ORDER - 0.01:
            break
        if c["book"] in used:
            continue
        used.add(c["book"])
        save = dict(lv)
        lv.update(book=c["book"], px=c, ids=c.get("ids") or {}, risk=rem, line=c["line"], am=c["am"], shown=c["shown"])
        try:
            o = live_order(r)
        finally:
            lv.update({k: save[k] for k in ("book", "px", "ids", "risk", "line", "am", "shown")})
        o = dict(o, book=o.get("book") or c["book"])
        more.append(o)
        if o.get("status") != "placed":
            break
    return more


def live_order_other(r):
    """Oct 28 (Peter): phase-1 live fill on Kalshi or Polymarket US when that book has the best after-fee price.
    Same unit, cap, STOP and daily stop (book_live counts these dollars as lost until settled)."""
    lv, p = r["live"], r["play"]
    book, ids = lv["book"], lv.get("ids") or {}
    name = BOOK_NAME.get(book, book)
    limit_cost, count = book_live.plan(lv["px"].get("buy"), lv["px"].get("thr"), lv["risk"])
    stake = round(count * limit_cost, 2) if limit_cost else 0.0
    if not limit_cost or stake < MIN_ORDER - 0.01:
        return {"status": "refused", "book": book, "reason": f"{name} ladder can't cover ${MIN_ORDER:.0f}+ at the alert number (have ${stake:.2f})"}
    limit_am = lm.american(limit_cost)
    label = f"{p.get('sport')} {p.get('game')} | {bet_text(r, lv['line'], limit_am)}"
    if book == "kalshi":
        kb = ids.get("kalshi_buy") or []
        if len(kb) != 1:
            return {"status": "refused", "book": book, "reason": "Kalshi market ambiguous (not exactly one market) - fail closed"}
        res = book_live.kalshi_place(kb[0]["ticker"], kb[0]["buy"], limit_cost, count, label)
    elif book == "polymarket_us":
        if not ids.get("market_slug") or ids.get("long_side") is None:
            return {"status": "refused", "book": book, "reason": "Polymarket US market unknown - fail closed"}
        res = book_live.pmus_place(ids["market_slug"], bool(ids["long_side"]), limit_cost, count, label)
    elif book == "novig":   # Novig contracts pay 1c: plan() counted $1 contracts, so x100
        if not ids.get("outcome_id"):
            return {"status": "refused", "book": book, "reason": "Novig outcome unknown - fail closed"}
        res = book_live.novig_place(ids["outcome_id"], limit_cost, count * 100, label, None, derive_key(p) or "")
    else:
        return {"status": "refused", "book": book, "reason": f"no live order code for {name}"}
    res = dict(res, book=book)
    if res["status"] == "placed" and res.get("sent_to_runner"):
        tg(f"SENT TO NOVIG (home PC): {bet_text(r, lv['line'], limit_am)}\nfill-or-kill, ${stake:,.2f} at {limit_am:+d} or better. "
           f"The fill result follows in the next run.\n{p.get('sport')} {p.get('game')}")
        return dict(res, asked_stake=stake, limit=limit_am)
    if res["status"] == "placed":
        fs, ac = res.get("filled_stake") or 0, res.get("avg_cost")
        ap = lm.american(ac) if ac else None
        res["avg_price"] = ap
        if fs and ac:
            win = res.get("contracts", 0) * (1 - ac)
            tg(f"FILLED {name}: {bet_text(r, lv['line'], ap)}\n${fs:,.2f} at {ap:+d} (before the {name} fee) -> wins about "
               f"${win:,.2f}{'' if fs >= stake - 0.5 else f' (partial: asked ${stake:,.2f})'}\n{p.get('sport')} {p.get('game')}\n"
               "Send STOP on ntfy to pause.")
        else:
            tg(f"NO FILL {name}: {bet_text(r, lv['line'], limit_am)}\nFill-or-kill got nothing at {limit_am:+d} or better"
               + ("" if res.get("fills_read") else f" (fill read failed: check {name})") + ".")
        push("PLACED: " + bet_text(r, lv["line"], limit_am)[:60],
             f"{label}\n{name} fill-or-kill: ${fs:,.2f} filled" + (f" at {ap:+d}" if ap else "")
             + f" (asked ${stake:,.2f}, limit {limit_am:+d})." + ("" if res.get("fills_read") else f" Fill read failed: check {name}."),
             mirror=False)
    elif res["status"] == "error":
        tg(f"LIVE ORDER ERROR {name}: {(p.get('bet') or '')[:60]}\n{res['reason'][:200]}\nCheck {name} before retrying.")
        push("LIVE ORDER ERROR: " + (p.get("bet") or "")[:50], f"{label}\n{res['reason']}\nCheck {name} before retrying.", mirror=False)
    if res.get("status") == "placed" and not res.get("fills_read"):
        res["filled_stake"] = None   # unknown fill: the daily stop counts everything asked
    return dict(res, asked_stake=stake, limit=limit_am)


# Oct 30 (Peter, after Muse's (a)/(b) answers): phase-1 goes live on the CODED rules AGREE, no wait for Muse.
# Muse is a veto: a DISAGREE on the play's key blocks any live order not yet sent. EXEC_RULES_LIVE=0 restores the gate.
RULES_LIVE = (os.environ.get("EXEC_RULES_LIVE") or "1").strip() != "0"
LIVEKEYS = set()   # play keys the bot already sent a live order or resting bid for (ledger registry + this run)
REST_BOOKS = tuple(b.strip() for b in (os.environ.get("EXEC_REST_BOOKS") or "novig,kalshi").split(",") if b.strip())
REST_BEFORE_MIN = 30   # resting bids expire this long before the listed start
# Polymarket US resting: priced as a TAKER until the maker flag is PROVEN. participateDontInitiate
# is what earns the rebate, and this venue has already been caught accepting a field
# (goodTillTime) and silently discarding it - so until pmus_rest_order_test's pdi_test shows the
# flag surviving a read-back, pricing a bid on the rebate would be claiming money we may not get.
# Taker pricing is strictly conservative: it can only make us bid LESS aggressively. Peter flips
# EXEC_PMUS_REST_MAKER=1 once the verdict is in.
PMUS_REST_MAKER = (os.environ.get("EXEC_PMUS_REST_MAKER") or "").strip() == "1"
PMUS_MAKER_REBATE = -0.0125   # Polymarket's published maker rebate: the venue pays us to post


def rest_wanted(r):
    """A phase-1 play (Muse AGREE) where nothing filled at the alert number: no live book had it (price skip), or the
    fill-or-kill came back empty. Never for conflicts, duplicates, caps, holds or refusals."""
    lv = r.get("live")
    if not lv or not px_live.LIVE or not REST_BOOKS:
        return False
    if lv.get("go"):
        o = lv.get("order") or {}
        allo = [o] + list(lv.get("more") or [])
        if o.get("status") != "placed" or any(x.get("status") == "error" for x in allo):
            return False
        if (o.get("fills_read") is True and not o.get("sent_to_runner") and not (o.get("filled_stake") or 0)
                and not any(_got(x) > 0 for x in (lv.get("more") or []))):
            return True   # nothing filled anywhere: rest the full unit
        rem = round(float(lv.get("risk") or 0) - sum(_got(x) for x in allo), 2)
        if rem >= MIN_ORDER - 0.01:   # Oct 31 (Peter): a partial fill rests a bid for the unfilled part
            lv["rest_risk"] = rem
            return True
        return False
    if r.get("books") is None:
        return False
    if r.get("verdict") == "WOULD PLACE":
        return lv.get("why") == ["no live book has the alert number or better"]
    return r.get("verdict") == "SKIP" and str(r.get("reason") or "").startswith("price:") and lv.get("why") == [r.get("reason")]


def novig_grid_floor(p, levels):
    """Oct 30 fix: Novig only accepts prices on its grid ('price is not on the submittable price grid' killed the
    Rockets/Mavs resting bid at 0.528). Snap DOWN (never a worse price than the alert) to the grid seen on the live
    book: 0.005 steps if every listed price sits on 0.005 and some are off 0.01, else whole cents (the safe default)."""
    pr = [round(float(lv.get("price")), 4) for lv in levels if lv.get("price") is not None]
    on = lambda v, st: abs(v / st - round(v / st)) < 1e-6
    step = 0.005 if pr and all(on(v, 0.005) for v in pr) and any(not on(v, 0.01) for v in pr) else 0.01
    return round(math.floor(p / step + 1e-9) * step, 3)


def pmus_rest_note(order_id, slug, expire, p):
    """Record ONE Polymarket US resting bid so a later run can cancel it. Returns True if recorded.

    WHY A RECORD IS NEEDED AT ALL, when Kalshi and Novig need none: their expiries work. This
    venue accepts goodTillTime and then stores the order as TIME_IN_FORCE_DAY with goodTillTime
    null, so a bid left alone rests until the end of the day - straight through the start of the
    game. Peter's rule is that a resting bid comes off at T-30. Only an explicit cancel can do
    that here, and a cancel needs BOTH the order id and the marketSlug: the id-only route is
    rejected with code 3 (proven on a live order, run 42750863769).

    GMAIL IS THE REGISTRY, exactly as it is for bot_orders() and the watchdog. Nothing financial
    goes in the public repo, and a repo file would also race the workflows that push it. The
    subject prefix is matched exactly so nothing else is ever read as a resting record."""
    if not order_id or not slug:
        return False
    try:
        send(f"Bets PMUS REST: {(p.get('bet') or '')[:40]}",
             f"{p.get('sport')} {p.get('game')} | {p.get('bet')}\n"
             f"Resting on Polymarket US until T-30. This venue discards the expiry, so this bid is "
             f"cancelled explicitly by a later executor run.\n\n"
             f"PMUSREST {order_id} {slug} {int(expire.timestamp())}")
        return True
    except Exception as ex:
        print(f"PM US resting record FAILED ({str(ex)[:60]}) - the bid is unmanaged")
        return False


def pmus_rest_sweep(now):
    """Cancel every Polymarket US resting bid that has reached T-30. Counts only in the public log.

    Runs once per executor run. Reads the PMUSREST records out of Gmail, skips any already
    cancelled (a second token, so a cancel is never attempted twice), and for the rest cancels
    only those whose recorded expiry has passed.

    FAIL LOUD, NOT QUIET. A resting bid we cannot cancel is live money past the point Peter said
    it must be off the book, so a failed cancel sends a phone push rather than only printing. The
    cancel itself is verified by book_live.pmus_cancel, which reads the order back - a 2xx from
    this venue is not proof, as goodTillTime already showed.

    Inert while Polymarket US is not in REST_BOOKS: nothing writes PMUSREST records, so there is
    nothing to find."""
    if "polymarket_us" not in REST_BOOKS:
        return 0
    done = 0
    try:
        M = imap_open()
        try:
            since = (now - timedelta(days=2)).strftime("%d-%b-%Y")
            typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets PMUS REST:"', "SINCE", since)
            if typ != "OK":
                print("PM US sweep: could not read the resting records")
                return 0
            for uid in (data[0].split() if data and data[0] else []):
                typ, d = M.uid("FETCH", uid, "(RFC822)")
                if typ != "OK" or not d or not d[0]:
                    continue
                raw = d[0][1]
                # IMAP SUBJECT is a SUBSTRING match - that was the Oct 27 bug which read dry-run
                # mail as live. Re-check the prefix on the real header before trusting the body.
                subj = str(email.header.make_header(email.header.decode_header(
                    email.message_from_bytes(raw).get("Subject") or "")))
                if not subj.startswith("Bets PMUS REST:"):
                    continue
                body = body_text(raw)
                m = re.search(r"PMUSREST (\S+) (\S+) (\d+)", body or "")
                if not m:
                    continue
                oid, slug, exp = m.group(1), m.group(2), int(m.group(3))
                if gsearch_strict(M, "pmusdone" + oid):
                    continue                      # already cancelled on an earlier run
                if now.timestamp() < exp:
                    continue                      # not yet at T-30
                res = book_live.pmus_cancel(oid, slug)
                ok = res.get("status") == "cancelled"
                send(f"Bets PMUS {'CANCELLED' if ok else 'CANCEL FAILED'}: {slug[:40]}",
                     f"Resting bid {oid} on {slug} reached T-30.\n"
                     f"{res.get('status')}: {res.get('state') or res.get('reason') or ''}\n\n"
                     f"pmusdone{oid}")
                if not ok:
                    push("PM US cancel FAILED", f"{slug}\n{oid}\n{str(res.get('reason'))[:120]}\n"
                                                f"Cancel it in the app - it rests until end of day.", mirror=False)
                done += 1
        finally:
            imap_close(M)
    except Exception as ex:
        print(f"PM US sweep failed: {str(ex)[:60]}")
        return 0
    print(f"PM US resting sweep: {done} bid(s) at T-30 handled")   # counts only
    return done


def rest_bid(r):
    """Rest ONE bid at the alert's after-fee number (no 2c extra) on the first REST_BOOKS book that lists the exact
    alert line: Kalshi (good-till-cancelled with an expiry) or Novig (GTT on the home PC). Same unit, cap, STOP and
    daily stop as live fills; the whole amount counts as risked until it expires or settles."""
    p, e, books = r["play"], r.get("entry") or {}, r.get("books") or {}
    try:
        st = datetime.fromisoformat(str(p.get("start_utc")).replace("Z", "+00:00"))
    except Exception:
        return {"status": "refused", "reason": "no start time"}
    expire = st - timedelta(minutes=REST_BEFORE_MIN)
    secs = (expire - datetime.now(timezone.utc)).total_seconds()
    if secs < 600:
        return {"status": "refused", "reason": "under 40 min to the start: no resting bid"}
    af = e.get("price_after_fee")
    if af is None:
        return {"status": "refused", "reason": "alert after-fee price unknown (fail closed)"}
    p_star = american_to_prob(int(af))
    risk, _ = live_stake(int(af), unit_for((r.get("live") or {}).get("lane")))
    if (r.get("live") or {}).get("rest_risk"):   # Oct 31: only the unfilled part of a partial fill
        risk = min(risk, float(r["live"]["rest_risk"]))
    g_ok, g_why = live_guards()
    if not g_ok:
        return {"status": "refused", "reason": g_why}
    why_not = []
    for b in REST_BOOKS:
        x = books.get(b) or {}
        if x.get("status") != "ok" or not x.get("exact_line"):
            why_not.append(f"{BOOK_NAME.get(b, b)}: no exact-line market")
            continue
        if b == "kalshi":
            kb = x.get("kalshi_buy") or []
            c = book_live.kalshi_cost_for(p_star, bc.TAKER_COEF["kalshi"])
            if len(kb) != 1 or not c:
                why_not.append("Kalshi: market ambiguous")
                continue
            n = int(risk // c)
            if n * c < MIN_ORDER - 0.01:
                why_not.append(f"Kalshi: under ${MIN_ORDER:.0f}")
                continue
            res = book_live.kalshi_place(kb[0]["ticker"], kb[0]["buy"], c, n, f"{p.get('sport')} {p.get('game')} | {p.get('bet')}",
                                         int(expire.timestamp()))
        elif b == "novig":
            if not x.get("outcome_id"):
                why_not.append("Novig: outcome unknown")
                continue
            c = novig_grid_floor(p_star, x.get("buy_levels") or [])
            q = int(risk // c * 100)
            res = book_live.novig_place(x["outcome_id"], c, q, f"{p.get('sport')} {p.get('game')} | {p.get('bet')}",
                                        int(secs * 1000), derive_key(p) or "")
        elif b == "polymarket_us":
            # Nov 10. Until now this fell through to the `else: continue` below, which meant
            # putting polymarket_us in REST_BOOKS placed NOTHING and said nothing - the worst
            # failure available, because it looks like success. Resting and cancelling are both
            # proven on this venue now (variant B rests; POST /v1/order/{id}/cancel + marketSlug
            # cancels and reads back ORDER_STATE_CANCELED), so the branch can exist.
            if not x.get("market_slug") or x.get("long_side") is None:
                why_not.append("Polymarket US: market unknown")
                continue
            # The fee coefficient comes from the BOOKS ENTRY, not a constant. book_check.TAKER_COEF
            # carries 'polymarket': 0.03 while the entry is built with the corrected 0.06, and
            # picking the wrong one silently mis-prices every bid. taker_fee_coef is whatever this
            # entry was actually scored with.
            coef = PMUS_MAKER_REBATE if PMUS_REST_MAKER else (x.get("taker_fee_coef") or 0.06)
            c = book_live.kalshi_cost_for(p_star, coef)   # same solver; verified for a negative coef
            if not c:
                why_not.append("Polymarket US: no price clears the alert number")
                continue
            n = int(risk // c)
            if n * c < MIN_ORDER - 0.01:
                why_not.append(f"Polymarket US: under ${MIN_ORDER:.0f}")
                continue
            res = book_live.pmus_place(x["market_slug"], bool(x["long_side"]), c, n,
                                       f"{p.get('sport')} {p.get('game')} | {p.get('bet')}",
                                       int(expire.timestamp()))
            # THE EXPIRY IS NOT AN EXIT HERE. The venue stores the order as TIME_IN_FORCE_DAY with
            # goodTillTime null, so this bid does NOT come off by itself at T-30 the way Kalshi's
            # and Novig's do. pmus_rest_note below records the id AND the slug (cancelling by id
            # alone is rejected with code 3), and pmus_rest_sweep cancels it on a later run. If
            # that record is not written the bid is unmanaged, so a failure to record is reported.
            if isinstance(res, dict) and res.get("status") == "placed":
                res["rest_recorded"] = pmus_rest_note(res.get("order_id"), x["market_slug"], expire, p)
        else:
            continue
        res = dict(res, book=b, limit=lm.american(c), asked_stake=round(risk, 2), expires_utc=expire.strftime("%Y-%m-%dT%H:%M:%SZ"))
        name = BOOK_NAME.get(b, b)
        when = expire.astimezone(lm.ET).strftime("%I:%M %p ET")
        if res["status"] == "placed":
            got = res.get("filled_stake") or 0
            tg(f"RESTING BID {name}: {p.get('bet')} at {lm.american(c):+d} (= the alert's {int(af):+d} after fees), "
               f"${risk:,.2f}" + (f"; ${got:,.2f} filled right away" if got else "") + f". Cancels itself at {when}.\n"
               f"{p.get('sport')} {p.get('game')}\nSTOP on ntfy does NOT cancel it: cancel in the {name} app if needed.")
        elif res["status"] == "error":
            tg(f"RESTING BID ERROR {name}: {(p.get('bet') or '')[:60]}\n{res['reason'][:200]}\nCheck {name} before retrying.")
        if res["status"] == "refused":   # Oct 30: a clean refusal falls through to the next book (Novig first, else Kalshi)
            why_not.append(f"{name}: {res.get('reason')}")
            continue
        return res
    return {"status": "refused", "reason": "; ".join(why_not) or "no resting book"}


def novig_reports():
    """Oct 28: the home runner writes each Novig order's result to snapshot/novig_orders.json; report each new or
    changed result to Telegram once (token email = the record, the same pattern as the watchdog). Counts only in the log."""
    recs = book_live.novig_results() if (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip() else []
    if not recs:
        return 0
    n = 0
    M = imap_open()
    try:
        for x in recs[-30:]:
            st = str(x.get("status") or "?").upper()
            if st in ("PENDING", "SENT", "UNKNOWN") and not int(x.get("filled_qty") or 0):
                continue   # not final yet: report when it settles (the home PC re-reads every 5 min)
            if st == "FILLED" and not int(x.get("filled_qty") or 0):
                continue   # status says filled but the amount isn't confirmed yet (old-format record): never say "no fill"
            c, q, fq = lm.num(x.get("price")) or 0, int(x.get("qty") or 0), int(x.get("filled_qty") or 0)
            cost = x.get("filled_cost")
            tok = "xnvr" + hashlib.sha1(f"{x.get('client_id')}|{st}|{fq}|{cost}".encode()).hexdigest()[:12]
            if gsearch_strict(M, tok):
                continue
            ap = lm.num(x.get("avg_price"))
            if st in ("REFUSED", "REJECTED"):
                head = f"NOVIG {st}"
            elif q and fq >= q:
                head = "NOVIG FILLED"
            elif fq > 0:
                head = "NOVIG PARTIAL FILL"
            elif st == "OPEN":
                head = "NOVIG RESTING (nothing filled yet)"
            else:
                head = "NOVIG NO FILL"
            msg = f"{head}: {x.get('label') or ''}"
            if fq > 0:
                pay = fq / 100
                msg += (f"\n{fq:,} of {q:,} contracts: ${(cost if cost is not None else fq * c / 100):,.2f} to pay ${pay:,.2f}"
                        + (f" (avg {lm.american(ap):+d})" if ap else ""))
            elif st not in ("REFUSED", "REJECTED"):
                msg += f"\nlimit {lm.american(c):+d}, ${q * c / 100:,.2f} asked; nothing traded"
            if x.get("tif") == "GTT" and st == "OPEN":
                msg += "\nResting until 30 min before the start (cancel in the Novig app if needed)."
            if x.get("error"):
                msg += f"\n{str(x['error'])[:160]}"
            tg(msg)
            try:
                send(f"Bets Novig order: {head.replace('NOVIG ', '')}", msg + f"\n\n{tok}")
            except Exception:
                pass
            n += 1
    finally:
        imap_close(M)
    print(f"Novig order reports sent: {n}")
    return n


def kalshi_rest_reports():
    """Oct 30 (Muse): a Kalshi resting bid that fills must message Peter at fill time (the next run, within ~10 min),
    not ride a later summary. Reads the bot's placed Kalshi resting bids (last 2 days) from its own 'Bets LIVE:' ledger
    rows, checks each order, and messages once per new fill amount (token email = the record). Counts only in the log."""
    M = imap_open()
    n = 0
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%d-%b-%Y")
        typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", since)
        rests = {}
        for uid in (data[0].split() if typ == "OK" and data and data[0] else []):
            typ, d = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not d or not d[0]:
                continue
            txt = body_text(d[0][1])
            i = txt.rfind("LEDGER (machine-readable")
            if i < 0:
                continue
            try:
                rows, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
            except Exception:
                continue
            for row in rows:
                lo = row.get("live_rest") or {}
                if lo.get("book") == "kalshi" and lo.get("status") == "placed" and lo.get("order_id"):
                    rests[str(lo["order_id"])] = (row, lo)
        for oid, (row, lo) in rests.items():
            try:
                st, d = book_live._k_call("GET", f"/portfolio/orders/{oid}")
            except Exception:
                continue
            o = d.get("order") or {}
            fc = lm.num(o.get("fill_count_fp")) or lm.num(o.get("fill_count")) or \
                ((lm.num(o.get("taker_fill_count")) or 0) + (lm.num(o.get("maker_fill_count")) or 0))
            if not fc:
                continue
            tok = "xkrf" + hashlib.sha1(f"{oid}|{fc}".encode()).hexdigest()[:12]
            if gsearch_strict(M, tok):
                continue
            rem = lm.num(o.get("remaining_count_fp")) or lm.num(o.get("remaining_count")) or 0
            head = "KALSHI RESTING BID FILLED" if not rem else "KALSHI RESTING BID PARTIAL FILL"
            msg = (f"{head}: {row.get('key', '').replace('|', ' ')}\n{fc:g} contracts at the {lo.get('limit')} limit"
                   + (f"; {rem:g} still resting until {lo.get('expires_utc')}" if rem else ""))
            push(head.title(), msg, mirror=False)
            tg(msg)
            try:
                send(f"Bets Kalshi order: {head.replace('KALSHI ', '')}", msg + f"\n\n{tok}")
            except Exception:
                pass
            n += 1
    finally:
        imap_close(M)
    print(f"Kalshi resting-fill reports sent: {n}")
    return n


def books_snapshot(r):
    """Queue #7 price capture (Nov 2, Peter yes): every book's after-fee price at the alert line at decision time.
    Logging only - never used for a decision; any problem returns None so the run is unaffected."""
    try:
        if not r.get("books"):
            return None
        out = {}
        for b in BOOKS:
            x = (r.get("books") or {}).get(b) or {}
            if x.get("status") == "ok":
                out[b] = {"best_after_fee": (int(x["best_price_american"]) if x.get("best_price_american") is not None else None), "line": book_line(x),
                          "exact_line": bool(x.get("exact_line")),
                          "dollars_at_alert_or_better": round(float(x.get("dollars_at_alert_price_or_better") or 0), 2)}
            else:
                out[b] = {"status": x.get("status", "not checked")}
        return out
    except Exception:
        return None


_OLDRULE_FEED = {}


def old_rule_block(r):
    """Nov 2 (Peter yes): tag a play the OLD first-side rule (any earlier sent alert) would have blocked but the new
    live-only rule lets through, so the rule change can be measured. Logging only; any problem returns None."""
    try:
        e = r.get("entry")
        if not e:
            return None
        if "feed" not in _OLDRULE_FEED:
            _OLDRULE_FEED["feed"] = load_feed()
        feed = _OLDRULE_FEED["feed"]
        fs = agree_rules.first_side(e, feed)
        if not fs or agree_rules.first_side(e, feed, live_only=True):
            return None
        return {"bet": fs.get("bet"), "book": fs.get("book"), "alert_utc": fs.get("alert_utc")}
    except Exception:
        return None


def _cap_units(asked, am, unit=None):
    """Spec #4 unit: to-win $300 (Nov 9; was $200). Plus money counts risk/unit; minus money counts to-win/unit.

    THE DIVISOR IS THE LANE'S UNIT, not a constant. Left at 200 while LIVE_UNIT moved to 300, a full-size Lane 1
    play scored 1.5 units and tripped the 1.0-unit stacking cap on every order. The board pilot reintroduces exactly
    that hazard in the other direction: a $200-to-win board play divided by 300 would score 0.67 units and under-count
    its own exposure. So the unit travels with the play (Peter, 11 Nov: "correct the existing $200/$300
    accounting-divisor mismatch"). Defaults to LIVE_UNIT, so Lane 1 is unchanged."""
    asked, am, u = float(asked or 0), float(am or 0), float(unit if unit else LIVE_UNIT)
    if asked <= 0 or am == 0:
        return 0.0
    # Matches Peter's rule exactly: plus money counts RISK/300 because a plus-money unit IS $300
    # risked; minus money counts TO-WIN/300 because a minus-money unit is $300 to win. I briefly
    # changed both branches to payout/300 on Nov 10 when I changed live_stake; reverted with it.
    return asked / u if am > 0 else asked * 100.0 / abs(am) / u


def stack_cap_report(r):
    """Spec #4 STACKING CAP - REPORT ONLY (Peter yes, Nov 2). Never changes an order. Counts this play's live order +
    resting bid + top-ups at asked stake (a bid that can fill is exposure) and flags anything over 1.0 unit. Held
    positions: the duplicate rule already skips a play when the same side is held on a readable book, so held
    before = 0 on readable books; Hard Rock is never readable (labelled unknown). Any problem returns None."""
    try:
        lv = r.get("live") or {}
        orders = [lv.get("order"), lv.get("rest")] + list(lv.get("more") or [])
        bad = ("fail", "reject", "error", "cancel", "skip", "refus", "not ", "none")
        units = 0.0
        for o in orders:
            if not o or any(w in str(o.get("status") or "").lower() for w in bad):
                continue
            units += _cap_units(o.get("asked_stake"), o.get("limit") or o.get("avg_price"),
                                unit_for((r.get("live") or {}).get("lane")))
        if units <= 0:
            return None
        return {"order_units": round(units, 3), "held_units_before": 0.0,
                "held_source": "positions read (duplicate rule); Hard Rock unknown",
                "would_cap": units > 1.0 + 1e-6, "trim_to_units": 1.0 if units > 1.0 + 1e-6 else None}
    except Exception:
        return None


# Nov 3 (Peter 4:38 PM, rulebook v5 price check, option b): at the moment of a live order, re-read Pinnacle. Fresher than
# PIN_MAX_AGE_S -> the order goes, with Pinnacle's age, no-vig fair and our gap to it logged. Stale or missing -> the
# live order is skipped (logged). Never an edge gate: the gap is recorded only.
PIN_MAX_AGE_S = int(os.environ.get("PIN_MAX_AGE_S", "") or "300")
PIN_SPORT = {"NFL": "americanfootball_nfl", "NCAAF": "americanfootball_ncaaf", "NBA": "basketball_nba",
             "NCAAB": "basketball_ncaab", "NHL": "icehockey_nhl", "MLB": "baseball_mlb"}
_PIN, _PIN_AT = {}, {}


def _pin_events(sk):
    at = _PIN_AT.get(sk)
    if sk not in _PIN or (at and (datetime.now(timezone.utc) - at).total_seconds() > 240):   # re-read on long runs
        key = os.environ.get("ODDS_API_KEY", "")
        _PIN[sk] = None
        if key:
            try:
                url = (f"https://api.the-odds-api.com/v4/sports/{sk}/odds?bookmakers=pinnacle&markets=spreads,totals"
                       f"&oddsFormat=american&dateFormat=iso&apiKey={key}")
                with urllib.request.urlopen(url, timeout=20) as resp:
                    _PIN[sk] = json.loads(resp.read().decode())
                _PIN_AT[sk] = datetime.now(timezone.utc)
            except Exception:
                _PIN[sk] = None
    return _PIN[sk]


def pin_check(p, lc, now):
    """{'ok', 'age_s', 'changed_s', 'pin_line', 'fair_am', 'gap_pct', 'why'} for the live candidate lc (our book, line, price
    after fee). age_s = how old our Pinnacle read is (the guard); changed_s = time since Pinnacle last moved this market
    (logged only: a steady price is still a current price)."""
    out = {"ok": False, "age_s": None, "changed_s": None, "pin_line": None, "fair_am": None, "gap_pct": None, "why": ""}
    try:
        lg = (p.get("sport") or "").upper()
        sk = PIN_SPORT.get(lg)
        if not sk or not os.environ.get("ODDS_API_KEY"):
            out["why"] = "Pinnacle not readable here (no key or sport)"
            return out
        evs = _pin_events(sk)
        if evs is None:
            out["why"] = "Pinnacle read failed"
            return out
        teams = lm.split_teams(p.get("game") or "")
        mt, sd, _, _ = bc.parse_bet(p.get("bet") or "", teams, lg) if teams else (None, None, None, None)
        if mt not in ("total", "spread") or sd is None:
            out["why"] = "bet not mapped to a Pinnacle market"
            return out
        tt = [lm.toks(x, lg) for x in teams]
        ev = next((e for e in evs if all(any(t & lm.toks(n, lg) for n in (e.get("home_team"), e.get("away_team"))) for t in tt)), None)
        if not ev:
            out["why"] = "game not on Pinnacle"
            return out
        bk = next((b for b in ev.get("bookmakers") or [] if b.get("key") == "pinnacle"), None)
        mk = next((m for m in (bk or {}).get("markets") or [] if m.get("key") == ("totals" if mt == "total" else "spreads")), None)
        if not mk or len(mk.get("outcomes") or []) != 2:
            out["why"] = "Pinnacle has no price for this market"
            return out
        lu = iso_t(mk.get("last_update") or (bk or {}).get("last_update"))
        out["changed_s"] = round((now - lu).total_seconds()) if lu else None
        out["age_s"] = round((now - _PIN_AT[sk]).total_seconds()) if _PIN_AT.get(sk) else None
        oc = mk["outcomes"]
        if mt == "total":
            mine = next((o for o in oc if o.get("name", "").upper() == sd), None)
        else:
            mine = next((o for o in oc if lm.toks(o.get("name"), lg) & tt[sd]), None)
        if mine:
            q = [american_to_prob(o["price"]) for o in oc]
            fair = american_to_prob(mine["price"]) / sum(q)
            out["pin_line"], out["fair_am"] = mine.get("point"), lm.american(fair)
            am = lc.get("am")
            if am is not None:
                dec = 1 + (am / 100 if am > 0 else 100 / abs(am))
                out["gap_pct"] = round((fair * dec - 1) * 100, 2)
        if out["age_s"] is None or out["age_s"] > PIN_MAX_AGE_S:
            out["why"] = (f"Pinnacle read {out['age_s']}s old (max {PIN_MAX_AGE_S}s)" if out["age_s"] is not None
                          else "Pinnacle read has no time")
            return out
        out["ok"] = True
        return out
    except Exception as ex:
        out["why"] = f"Pinnacle check error ({str(ex)[:40]})"
        return out


def pin_note(pc):
    if not pc:
        return ""
    bits = [f"read {pc['age_s']}s ago" if pc.get("age_s") is not None else "read time ?"]
    if pc.get("changed_s") is not None:
        bits.append(f"last moved {pc['changed_s'] // 60} min ago")
    if pc.get("fair_am") is not None:
        bits.append(f"fair {pc['fair_am']:+d}" + (f" at {pc['pin_line']:g}" if pc.get("pin_line") is not None else ""))
    if pc.get("gap_pct") is not None:
        bits.append(f"our price vs fair {pc['gap_pct']:+.1f}%")
    return "  [Pinnacle " + ", ".join(bits) + "]"


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
            "fill_line": r.get("take_line"),
            # Nov 6 (Peter, $25-50k NBA forward paper test): depth at the chosen price and whether the unit fits. Logging only.
            "fill_avail": r.get("fillable"), "fill_partial": r.get("partial"), "live": bool(lv.get("go")), "live_nfl": bool(lv.get("nfl")), "live_why_not": lv.get("why"),
            "live_px_price_after_fee": lv.get("am"), "live_px_line": lv.get("line"), "live_book": lv.get("book"),
            "pin_check": lv.get("pin"),   # Nov 3: Pinnacle age / fair / our gap at the order (gap logged, never a gate)
            # Oct 27 gettable-price counter (Muse): phase-1 qualifying (coded view, ignoring Muse AGREE), ProphetX at the
            # alert price or better at check (equivalent price, same rule as live), best ProphetX price seen at the alert line
            "p1_qualifies": (agree_rules.phase1(e, True)[0] if e else None),
            "px_gettable": ((r.get("px") is not None) if r.get("books") else None),
            "px_best_after_fee": ((r.get("books") or {}).get("prophetx") or {}).get("best_price_american"),
            "px_best_line": ((r.get("books") or {}).get("prophetx") or {}).get("line"),
            "books_at_decision": books_snapshot(r),
            "old_rule_would_block": old_rule_block(r),
            "stack_cap": stack_cap_report(r),
            "lane2": ({k: e.get(k) for k in ("label", "limit", "limit_how", "median", "market", "book_key", "hr_priced", "edge_pct",
                                              "edge_band", "lead_min", "timing", "top25")} if p.get("source") == "lane2" else None),
            "live_order": dict({k: (lv.get("order") or {}).get(k) for k in ("status", "reason", "order_id", "asked_stake", "limit",
                                                                            "filled_stake", "avg_price")},
                               book=(lv.get("order") or {}).get("book") or "prophetx") if lv.get("order") else None,
            "live_rest": ({k: (lv.get("rest") or {}).get(k) for k in ("status", "reason", "book", "order_id", "asked_stake",
                                                                       "limit", "filled_stake", "expires_utc")}
                          if lv.get("rest") else None),
            "live_more": [{k: o.get(k) for k in ("status", "reason", "book", "order_id", "asked_stake", "limit", "filled_stake",
                                                  "avg_price")} for o in (lv.get("more") or [])]}


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
    try:
        read_manual(M)
    except Exception:
        LOG.append("manual-bet notes unreadable")
    rplays = rule_plays(now) if SOURCE in ("rules", "both") else []
    bplays = board_plays(now)   # Nov 3: Lane 3 (board NBA totals)
    try:   # Nov 4: Lane 2 (Muse registration 3:48 PM) - dry run only, no live path exists for these plays
        import clv_ledger as _cl
        l2plays = [dict(p, play_key="lane2|" + (derive_key(p) or ""))   # Nov 4 fix: Lane 2 rows need their own play_key
                   for p in lane2.plays(now, load_feed(), lane2.markets(_cl, now)) if derive_key(p)]
    except Exception as ex:
        LOG.append(f"lane 2 unavailable: {str(ex)[:60]}")
        l2plays = []
    new = [p for p in plays + rplays + bplays + l2plays if not already_handled(M, p)]
    imap_close(M)
    feed = load_feed()
    # wake time: this run's start vs the newest SENT alert (Oct 26; counts/seconds only in the public log)
    sent_ts = [iso_t(a.get("alert_utc")) for a in feed if a.get("sent_to_phone") and iso_t(a.get("alert_utc"))]
    newest = max(sent_ts) if sent_ts else None
    wake_s = (now - newest).total_seconds() if newest and now - newest < timedelta(minutes=30) else None
    trig = os.environ.get("GITHUB_EVENT_NAME", "local")
    if SOURCE in ("both",):
        muse_watchdog(now, plays, rplays, feed)
    # Before anything else this run: pull any Polymarket US resting bid that has reached T-30.
    # It goes here, ahead of the new-order work, because a bid past T-30 is live money sitting on
    # the book after the point Peter said it must be off - that takes priority over placing more.
    # Its own try/except is inside the function; a sweep failure must not stop the run.
    try:
        pmus_rest_sweep(now)
    except Exception as ex:
        print(f"PM US sweep call failed: {str(ex)[:60]}")
    try:
        novig_reports()
    except Exception as ex:
        print(f"novig report check failed: {str(ex)[:60]}")
    try:
        kalshi_rest_reports()
    except Exception as ex:
        print(f"kalshi resting-fill check failed: {str(ex)[:60]}")
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
    with ThreadPoolExecutor(max_workers=4) as tp:   # Oct 31: all 4 position reads at the same time
        f_nv = tp.submit(novig_positions)
        f_h = {b: tp.submit(fn) for b, fn in (("kalshi", positions.kalshi_positions), ("prophetx", positions.px_positions),
                                              ("polymarket_us", positions.pmus_positions))}
        pos = f_nv.result()
        held = {b: f.result() for b, f in f_h.items()}   # Kalshi / ProphetX / Polymarket US open positions (read-only)
    if pos is None or any(v is None for v in held.values()):   # one immediate retry before holding anything
        time.sleep(5)
        if pos is None:
            pos = novig_positions()
        retry = {"kalshi": positions.kalshi_positions, "prophetx": positions.px_positions,
                 "polymarket_us": positions.pmus_positions}
        for b in [b for b, v in held.items() if v is None]:
            held[b] = retry[b]()
    blind = (["Novig"] if pos is None else []) + [BOOK_NAME[b] for b, v in held.items() if v is None]
    # Oct 29 (Muse): when a book's positions can't be read and a LIVE-eligible play (phase-1, Muse AGREE) is waiting,
    # re-read every 60 s inside this run (up to 4 min - the runs queue behind each other, so not longer), and push an
    # escalation at ~3 min naming the play and the book so it can be placed by hand while the number is live.
    # Unreadable still means no order (fail closed).
    if blind:
        p1 = []
        for p in new:
            e1 = feed_entry(p, load_feed()) if p.get("source") != "rules" else None
            if e1 and agree_rules.phase1(e1, True)[0]:
                p1.append(p)
        retry = {"kalshi": positions.kalshi_positions, "prophetx": positions.px_positions,
                 "polymarket_us": positions.pmus_positions}
        pushed = False
        for i in range(4 if p1 else 0):
            time.sleep(60)
            if pos is None:
                pos = novig_positions()
            for b in [b for b, v in held.items() if v is None]:
                held[b] = retry[b]()
            blind = (["Novig"] if pos is None else []) + [BOOK_NAME[b] for b, v in held.items() if v is None]
            if not blind:
                break
            if i == 2 and not pushed:
                why = "; ".join(f"{BOOK_NAME[b]}: {positions.WHY.get(b, '?')}" for b, v in held.items() if v is None)
                if pos is None:
                    why += ("; " if why else "") + f"Novig: {(_NVERR.get('why') or '?').strip(' |')[:80]}"
                for p in p1:
                    push("LIVE play held: " + (p.get("bet") or "")[:50],
                         f"{p.get('sport')} {p.get('game')}\n{p.get('bet')}\nCan't read your open bets on {', '.join(blind)} "
                         f"for 3 min ({why[:160]}). The bot won't bet it blind. Place it by hand if you want it now.")
                pushed = True
        print(f"Held-retry: {len(p1)} live-eligible play(s); still unreadable: {len(blind)} book(s)")   # counts only
    if px_live.LIVE and new:
        live_guards()   # Oct 30: load the ledger registry FIRST, so LIVEKEYS blocks a second live order on a play
    results, taken_now = [], set()
    M2 = imap_open()

    def taken(k):   # this run, or any earlier WOULD PLACE / PLACED entry
        # Nov 8: strict, for the same reason as already_handled. This is "first side stays": a
        # failed search returning [] reads as "the side is free" and the bot takes the opposite
        # side of a position it already holds. Raise rather than guess.
        return k in taken_now or bool(gsearch_strict(M2, wp(k)))
    for p in new:
        try:
            ent = feed_entry(p, feed) or {}
            if ent:
                fs = agree_rules.first_side(ent, feed, live_only=True)
                if fs:   # coded fix 2 (Oct 26) + Nov 2 (Peter): only an earlier LIVE-ELIGIBLE sent alert keeps the first side
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
            if ent.get("floor_line") is not None and p.get("floor_line") is None:
                p = dict(p, floor_line=ent["floor_line"])   # Oct 31: the alert's bet-only-at line (hard floor)
            r = evaluate(p, now, evs_by, mks_by_event, pos, None if p.get("source") in ("rules", "lane2") else taken, held)
            r["entry"] = ent
            if p.get("source") == "lane2":   # Nov 4: Lane 2 - priced and logged like any dry-run play; NEVER live (Peter "no live play")
                r["entry"] = ent = p.get("lane2_entry") or {}
                r["live"] = {"go": False, "lane": "lane2", "why": [f"Lane 2 is dry-run only (Peter Nov 4) - {p['rules']['reason']}"]}
            elif p.get("source") == "board":   # Lane 3: its own live decision (never the phase-1 filter), own record
                r["entry"] = ent = p.get("board_entry") or {}
                lk = derive_key(p) or p["play_key"]
                why = [] if BOARD_LIVE else ["board lane not switched on (EXEC_BOARD_LIVE)"]
                if lk in MANUAL_HELD:
                    why.append(f"{MANUAL_HELD[lk]} with Peter's manual bet (Bets manual note)")
                if lk in LIVEKEYS or any(same_bet(lk, k) for k in LIVEKEYS):
                    why.append("a live order or resting bid was already sent for this bet (another lane)")
                if any(opp_bet(lk, k) for k in LIVEKEYS):
                    why.append("CONFLICT: the other side of this game was already bet (first side stays)")
                if not why and r["verdict"] == "WOULD PLACE" and r.get("lc"):
                    lc = r["lc"]
                    lr, lw = live_stake(lc["shown"], BOARD_UNIT)   # $200 to win (board pilot), never Lane 1's $300
                    g_ok, g_why = board_gate(lr, lk)   # board-only cap and daily risk limit; fail closed
                    if not g_ok:
                        why.append(g_why)
                if not why and r["verdict"] == "WOULD PLACE" and r.get("lc"):
                    r["live"] = {"go": True, "book": lc["book"], "risk": lr, "to_win": lw, "am": lc["am"], "shown": lc["shown"],
                                 "line": lc["line"], "partial": lc["avail"] < lr, "px": lc, "ids": lc.get("ids") or {},
                                 "nfl": False, "lane": "board", "unit": BOARD_UNIT}
                elif not why:
                    r["live"] = {"go": False, "lane": "board", "why": ["no live book has the alert number or better"
                                                                        if r["verdict"] == "WOULD PLACE" else (r.get("reason") or "skipped")]}
                else:
                    r["live"] = {"go": False, "lane": "board", "why": why}
            elif ent and (p.get("source") != "rules" or RULES_LIVE):   # phase-1 live tag (Oct 30: coded AGREE goes live too)
                ok, why = agree_rules.phase1(ent, True)   # totals unders NBA/NCAAF/NFL + NCAAF overs (Nov 3/Nov 4); spreads paper. See agree_rules.PHASE1
                lk = derive_key(p) or p["play_key"]
                if ok and lk in MUSE_DISAGREE:
                    ok, why = False, ["Muse DISAGREE (veto)"]
                elif ok and lk in MANUAL_HELD:
                    ok, why = False, [f"{MANUAL_HELD[lk]} with Peter's manual bet (Bets manual note)"]
                elif ok and lk in LIVEKEYS:
                    ok, why = False, ["a live order or resting bid was already sent for this play"]
                elif ok and any(opp_bet(lk, k) for k in LIVEKEYS):   # Nov 3 (Peter 2:51 PM): first side stays, any lane
                    ok, why = False, ["CONFLICT: the other side of this game was already bet (first side stays)"]
                if ok and r["verdict"] == "WOULD PLACE" and r.get("lc"):
                    lc = r["lc"]
                    lr, lw = live_stake(lc["shown"])
                    r["live"] = {"go": True, "book": lc["book"], "risk": lr, "to_win": lw, "am": lc["am"], "shown": lc["shown"],
                                 "line": lc["line"], "partial": lc["avail"] < lr, "px": lc, "ids": lc.get("ids") or {},
                                 "nfl": (ent.get("sport") or "").upper() == "NFL"}
                elif ok:
                    r["live"] = {"go": False, "why": ["no live book has the alert number or better"
                                                      if r["verdict"] == "WOULD PLACE" else (r.get("reason") or "skipped")]}
                else:
                    r["live"] = {"go": False, "why": why}
            if r["verdict"] == "WOULD PLACE" and blind and (r.get("live") or {}).get("go"):
                # Oct 30 (Muse): HOLD only live-eligible phase-1 plays; a paper play (e.g. grade C) stays a paper WOULD PLACE
                # can't see what's already held on every book: hold, retry next run, alert the phone once
                r = dict(r, verdict="HELD", reason="positions unreadable on " + ", ".join(blind))
                dk = derive_key(p) or p["play_key"]
                if not gsearch(M2, held_tok(dk)):
                    push("Bet held: " + (p.get("bet") or "")[:60],
                         f"{p.get('sport')} {p.get('game')}\nCouldn't check your open bets on {', '.join(blind)}. "
                         "Retrying every 10 min while the price is there. If you know you don't hold the other side, "
                         "you can place it by hand.")
            if r["verdict"] == "WOULD PLACE" and (r.get("live") or {}).get("go"):   # Nov 3: price check at the order
                pc = pin_check(p, r["live"], datetime.now(timezone.utc))
                r["live"]["pin"] = pc
                if not pc["ok"]:
                    r["live"] = {"go": False, "lane": r["live"].get("lane"), "pin": pc,
                                 "why": [f"price check: {pc['why']} - live order skipped (Peter Nov 3)"]}
            if r["verdict"] == "WOULD PLACE" and (r.get("live") or {}).get("go"):
                r["live"]["order"] = live_order(r)
                r["live"]["more"] = live_remainder(r)   # Oct 28: $200 total per play across venues
                LIVEKEYS.add(derive_key(p) or p["play_key"])
            if rest_wanted(r):   # Oct 28 (Peter): nothing filled at the number -> rest a bid until 30 min before the start
                r["live"]["rest"] = rest_bid(r)
                LIVEKEYS.add(derive_key(p) or p["play_key"])
            results.append(r)
            if (r["verdict"] == "WOULD PLACE" or ((r.get("live") or {}).get("rest") or {}).get("status") == "placed") \
                    and derive_key(p) and p.get("source") not in ("rules", "board", "lane2"):
                taken_now.add(derive_key(p))
        except Exception as ex:
            results.append({"play": p, "pid": pid(p["play_key"]), "verdict": "SKIP", "reason": f"error: {str(ex)[:100]}"})
        results[-1]["decided_utc"] = datetime.now(timezone.utc)
    imap_close(M2)
    nw = sum(1 for r in results if r["verdict"] == "WOULD PLACE")
    when = now.astimezone(lm.ET).strftime('%a %b %d %I:%M %p ET')
    body = [(f"LIVE ON for phase 1 (${LIVE_UNIT:.0f} to win, best price on {', '.join(BOOK_NAME.get(b, b) for b in LIVE_BOOKS)}); everything else is a dry run ({when})" if px_live.LIVE
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
    body.append(f"WOULD GO LIVE - phase 1, ${LIVE_UNIT:.0f} to win, best live book ({len(golive)})")
    body += [f"  - {bet_text(r, r['live']['line'], r['live']['shown'])} on {BOOK_NAME.get(r['live'].get('book', 'prophetx'), 'ProphetX')}: risk {money(r['live']['risk'])} to win "
             f"{money(r['live']['to_win'])}  ({r['play'].get('sport')} {r['play'].get('game')})"
             + order_note(r['live'].get('order'))
             + "".join(f" + {BOOK_NAME.get(o.get('book'), o.get('book'))}" + order_note(o) for o in (r['live'].get('more') or []))
             + ("  [partial: not all of it at this price]" if r["live"]["partial"] else "")
             + pin_note(r["live"].get("pin"))
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
    body += [lane2.summary_line(), ""]   # Nov 4: Lane 2 counts (private email; dollars never in the public log)
    if GUARD["ok"] is not None:
        body += [f"Live guards: {'OK' if GUARD['ok'] else 'REFUSED'}" + (f" - {GUARD['why']}" if GUARD["why"] else "")
                 + " (the daily stop counts only the bot's own orders).", ""]
    try:   # spec #4 stacking cap, REPORT ONLY (Nov 2): counts only, nothing is changed
        _sc = [x for x in (stack_cap_report(r) for r in results) if x]
        body += [f"Stack cap (report-only): {sum(1 for x in _sc if x['would_cap'])} would-cap of {len(_sc)} live order set(s)"
                 + "".join(f" | {x['order_units']}u" for x in _sc if x["would_cap"]), ""]
    except Exception:
        pass
    body += ["LEDGER (machine-readable, one row per play; latency = decision time minus first alert time)",
             json.dumps([ledger_row(r, now) for r in results], separators=(",", ":"))]
    first = ", ".join(short(r) for r in places[:3]) + ("..." if len(places) > 3 else "")
    nplaced = sum(1 for r in golive if (r["live"].get("order") or {}).get("status") == "placed")
    send((f"Bets LIVE: {nplaced} placed, " if px_live.LIVE else "Bets dry run: ") + f"{len(golive)} would go live, {nw} would bet" + (f" ({first})" if places else "") + (f", {len(helds)} held" if helds else "")
         + f", {len(skips)} skipped",
         "\n".join(body))
    print(f"Dry-run email sent: {len(golive)} would go live, {nw} would place, {len(helds)} held, {len(skips)} skipped.")   # counts only
    rested = sum(1 for r in results if ((r.get("live") or {}).get("rest") or {}).get("status") == "placed")
    if nplaced or rested:   # Oct 29 (Muse): a private balances email right after any live order or resting bid
        try:
            import balances
            os.environ["BAL_REASON"] = "after a live order"
            balances.main()
        except Exception as ex:
            print(f"balances email failed: {str(ex)[:60]}")


if __name__ == "__main__":
    main()

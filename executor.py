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
import collections
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
import uuid   # Nov 11: client-side id for the write-ahead order intent
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import book_check as bc
import liquidity_monitor as lm
try:   # Nov 11: fee-model stamp for the ledger's fee_basis (logging only; never a gate)
    from clv_std import FEE_MODEL
except Exception:
    FEE_MODEL = None
import agree_rules
import lane2   # Nov 4: Lane 2 LOW-limit sharp alerts, DRY RUN ONLY (Peter 4:01 PM "no live play")
import positions
import px_live
import book_live
import registry

UNIT = float(os.environ.get("EXEC_UNIT", "") or "300")          # + money: risk UNIT; - money: risk to win UNIT
SOURCE = (os.environ.get("EXEC_SOURCE", "") or "both").lower()  # muse | rules | both (dry run: both, side by side)
RULES_LOOKBACK_H = 6                                             # coded rules look at alerts first sent in the last 6 h
MIN_LEAD_MIN = float(os.environ.get("EXEC_MIN_LEAD_MIN", "") or "60")
CAP_LINE = -130                                                  # spreads/totals: never worse than -130
BLIND_STREAK_AT = 5   # Nov 11 (Peter): consecutive blind runs before the POSITIONS UNREADABLE push.
                      # Notification cadence ONLY - it does not change when the bot goes blind, and
                      # a blind run still places nothing on any venue, exactly as before.
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


INTENT_SUBJECT_PREFIX = "Bets LIVE: order intent"   # what journal_intent sends
INTENT_CLEAR_PREFIX = "INTENT CLEARED"              # Peter's manual authorization. THE BOT NEVER SENDS THIS.


_GM_LABELS = re.compile(rb"X-GM-LABELS\s*\(([^)]*)\)", re.I)


def _gm_labels(meta):
    """Exact Gmail label tokens from an IMAP FETCH METADATA line only - never header or body bytes.

    Nov 11 (Peter): the previous version joined every byte of the FETCH response and looked for the
    text \\Sent anywhere in it. The response includes the fetched headers, so an INBOUND message
    whose SUBJECT merely contained \\Sent would have been read as carrying the \\Sent label and
    would have cleared an order intent. Authorization must never read attacker-supplied bytes.

    Returns a set of normalised tokens (quotes stripped, a wire-escaped \\\\Sent folded to \\Sent)."""
    m = _GM_LABELS.search(meta or b"")
    if not m:
        return set()
    out = set()
    for tok in re.findall(rb'"[^"]*"|\S+', m.group(1)):
        t = tok.decode("utf-8", "ignore").strip('"')
        if t.startswith("\\\\"):
            t = t[1:]
        out.add(t)
    return out


def _addr(header):
    """The bare address out of a From/Sender header ('Peter G <a@b.com>' -> 'a@b.com'), lowercased."""
    return (email.utils.parseaddr(header or "")[1] or "").strip().lower()


def authorized_senders():
    """Addresses allowed to clear an order intent: the account itself and EMAIL_TO. Nothing else.
    Nov 11 (Peter): "only an authorized sender can clear an unresolved order intent."
    Raises if the account is not configured, so an unconfigured run cannot clear anything."""
    user, _pw, to = gmail()
    return {a for a in (_addr(user), _addr(to)) if a}


def subject_hits(M, needle, prefix, days=4, senders=None):
    """UIDs whose SUBJECT contains `needle` AND whose real Subject header starts with `prefix`.

    Nov 11. Subject-only, never the body: the first version of the intent clearance searched
    X-GM-RAW for a token that the intent email's OWN BODY contained, so every intent cleared
    itself the moment it was written and the fail-closed guard could never fire. Searching
    subjects with a prefix the bot never emits removes that whole class of self-match.

    IMAP SUBJECT is a substring match (the Oct 27 bug: dry-run mail read as live), so the real
    header is always re-checked. Raises on any failed search or fetch, so callers fail closed."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = M.uid("SEARCH", None, "SUBJECT", '"' + str(needle).replace('"', '') + '"', "SINCE", since)
    if typ != "OK":
        raise RuntimeError("Gmail subject search failed")
    out = []
    for uid in (data[0].split() if data and data[0] else []):
        typ, d = M.uid("FETCH", uid, "(X-GM-LABELS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM SENDER)])")
        if typ != "OK" or not d or not d[0]:
            raise RuntimeError("Gmail header fetch failed")
        msg = email.message_from_bytes(d[0][1] if isinstance(d[0], tuple) else d[0])
        subj = str(email.header.make_header(email.header.decode_header(msg.get("Subject") or "")))
        if not (subj.startswith(prefix) and str(needle) in subj):
            continue
        if senders is not None:
            # A From header PROVES NOTHING - anyone can forge it, and this mailbox is
            # [Gmail]/All Mail, which includes RECEIVED mail. So authorization is the \Sent
            # label: a message reaches Sent only by being sent THROUGH the authenticated
            # account, which no forged inbound message can do. Credentials, not a header.
            # METADATA ONLY. d[0][0] is the FETCH metadata line; d[0][1] is the fetched header
            # payload, which is attacker-supplied and is never consulted for authorization.
            meta = d[0][0] if (isinstance(d[0], tuple) and len(d[0]) > 1) else b""
            if "\\Sent" not in _gm_labels(meta):
                continue
            # Belt and braces, after the label: the address must still be an authorized one.
            frm, snd = _addr(msg.get("From")), _addr(msg.get("Sender"))
            if frm not in senders or (snd and snd not in senders):
                continue
        out.append(uid)
    return out


def intent_cleared(M, cid):
    """True only for a DISTINCT, AUTHENTICATED, MANUAL authorization: an email whose SUBJECT starts
    with 'INTENT CLEARED', names this client_id, carries Gmail's \\Sent label, AND whose From is an
    authorized address.

    Why the label and not the header (Muse's question, Nov 11): a From header is trivially forged,
    and this mailbox is [Gmail]/All Mail, which includes RECEIVED mail - so a forged inbound message
    claiming to be Peter would otherwise have cleared an intent. The \\Sent label cannot be forged
    from outside: a message only reaches Sent by being sent THROUGH the authenticated account, so
    clearance now rests on account credentials rather than on a header anyone can type.

    No automated email of this system carries that subject, so the bot cannot clear its own intent.
    Raises on a failed search or an unconfigured account -> the caller keeps refusing."""
    return bool(subject_hits(M, cid, INTENT_CLEAR_PREFIX, senders=authorized_senders()))


def intent_verified(cid, row):
    """Durable read-back of a pre-order record. Returns (ok, where).

    Nov 11 (Peter): intent_readable() opened a FRESH IMAP connection per try and slept 5s between
    up to 3 tries, PER ORDER, because Gmail's index lags its own SMTP. The private store has no such
    lag: a contents PUT returns only on a confirmed commit, and a GET then reads the row straight
    back - measured at 0.33s against 114.2s for the Gmail registry read. So the store is tried
    first and the Gmail poll becomes the fallback.

    The RULE IS UNWEAKENED: no order is submitted until its pre-order record has been read back out
    of a durable store. What changes is which store answers, not whether one has to.

    Both stores still receive the row - send() already put it in Gmail before this is called - so
    crash recovery works whichever path bot_orders() takes on the next run: the Gmail ledger scan
    and the store read both see the intent and both latch live orders until Peter clears it.
    Fail-closed is preserved end to end: if neither store can confirm the row, this returns False
    and the caller submits nothing."""
    if registry.enabled():
        try:
            if registry.put_rows([row]):
                d = registry.load()
                if d is not None:
                    for r in d.get("orders") or []:
                        lo = r.get("live_order") or r.get("live_rest") or {}
                        if str(lo.get("client_id") or "") == str(cid) and lo.get("intent"):
                            return True, "private store"
        except Exception as ex:
            LOG.append(f"registry intent verify failed: {str(ex)[:50]}")
    return bool(intent_readable(cid)), "Gmail"


def intent_readable(cid, tries=3, wait=5):
    """Nov 11 (Peter): SMTP success is NOT storage. Confirm the intent row can actually be READ
    BACK from the registry before any order is submitted - the same discipline the Polymarket
    order path already follows ('acceptance is never proof - read the order back').

    Retries for Gmail's indexing delay. Returns False if it still cannot be read, and the caller
    then submits NOTHING. Note the deliberate asymmetry: a stored-but-not-yet-indexed intent will
    later show as unconfirmed and lock live orders until cleared, even though no order was placed.
    That is the safe direction - a refused play costs a play, an untracked order costs money."""
    for i in range(tries):
        if i:
            time.sleep(wait)
        try:
            with perf("intent read-back (Gmail login per try)"):
                M = imap_open()
            try:
                if subject_hits(M, cid, INTENT_SUBJECT_PREFIX):
                    return True
            finally:
                imap_close(M)
        except Exception:
            pass
    return False


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
    # Nov 11: this was gsearch(M, 'subject:"Bets manual" newer_than:3d') and it cost 202.0s - 50.7%
    # of the whole run, the single largest item in PERF - to read about eight tiny notes.
    #
    # gsearch() does query.replace('"', ''), which STRIPS THE PHRASE QUOTES. Gmail then read
    # `subject:Bets manual newer_than:3d` as "subject contains Bets" AND "the message contains
    # manual anywhere" - so it matched every Bets LIVE:/signal:/watchdog: email of the last three
    # days that happens to use the word (the run emails say "MANUAL ONLY" and "manual bets"), and
    # then fetched each one whole, 38KB ledgers included. Megabytes, to find eight one-line notes.
    #
    # Now an IMAP SUBJECT + SINCE search with a real header re-check, which is the pattern
    # bot_orders() already uses for exactly this reason: IMAP SUBJECT is a substring match, so the
    # header prefix is confirmed before the body is trusted (reading dry-run mail as live was a real
    # bug on Oct 27).
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%d-%b-%Y")
    typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets manual"', "SINCE", since)
    uids = (data[0].split() if typ == "OK" and data and data[0] else [])
    for uid in uids:
        typ, data = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            continue
        subj = str(email.header.make_header(email.header.decode_header(
            email.message_from_bytes(data[0][1]).get("Subject") or "")))
        if not subj.startswith("Bets manual"):
            continue   # substring match: only Peter's own manual-bet notes count
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


# ---------------------------------------------------------------- R1 live lane (Peter, 11 Nov)
R1_LIVE = (os.environ.get("EXEC_R1_LIVE") or "off").strip().lower() == "on"   # R1 money switch (repo variable; Peter flips it)
R1_UNIT = 200.0   # Peter, 11 Nov: own $200 unit, Lane 1 stays at $300. Same to-win (minus) / risk (plus) rule.
R1_DAILY_RISK = float(os.environ.get("EXEC_R1_DAILY_RISK", "") or "2000")   # Nov 11 (Peter): 1500 -> 2000   # its own daily limit ON TOP of the global stop
R1_MAX_PLAYS = int(os.environ.get("EXEC_R1_MAX_PLAYS", "") or "10")
R1 = {"risk": 0.0, "keys": set(), "known": False}


def r1_plays(now):
    """R1 (non-Top-25 college, ProphetX-priced, spreads + totals unders, 4h+, not late, -119 or better, not
    Matchbook-only): read straight from alerts.json, because these alerts are MUTED on the phone (sent_to_phone is
    False) and rule_plays skips muted alerts. FIRST alert per game+market+side only: a repeat never bets. Same
    downstream path as every play: books checked, line floor (the alert's own line), caps, stacking, positions,
    live guards. Places money only when EXEC_R1_LIVE is "on" AND live is on; otherwise a dry-run WOULD PLACE."""
    try:
        with open("alerts.json") as f:
            feed = json.load(f).get("alerts") or []
    except Exception as ex:
        LOG.append(f"alerts.json unreadable (r1): {str(ex)[:60]}")
        return []
    out, seen = [], set()
    for a in sorted(feed, key=lambda a: a.get("alert_utc") or ""):
        ok, _ = agree_rules.r1(a)
        if not ok:
            continue
        t, st = iso_t(a.get("alert_utc")), iso_t(a.get("start_utc"))
        if not t or not st or t < now - timedelta(hours=RULES_LOOKBACK_H) or st <= now:
            continue
        p = {"sport": a.get("sport"), "game": a.get("game"), "bet": a.get("bet"), "start_utc": a.get("start_utc"),
             "late": False, "source": "r1", "alert_utc": a.get("alert_utc"),
             "rules": {"verdict": "AGREE", "gate": None, "reason": "R1 (non-Top-25 college, ProphetX-priced)"},
             "r1_entry": a}
        k = derive_key(p)
        if not k or k in seen:
            continue   # first alert only
        seen.add(k)
        out.append(dict(p, play_key="r1|" + k))
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
# Nov 11 (Peter): "BEST PRICE FIRST, NOT MAXIMUM DOLLARS FILLED." How much worse than the BEST
# available qualifying level the size walk may go, in probability cents. 0 = best-priced depth only;
# the stake shrinks to what is there rather than paying up to fill the unit. This is a ceiling on
# slippage WITHIN a venue's ladder - it does not touch eligibility (PX_TOL_CENTS), the -130 cap, the
# bet-only-at floor or the venue ranking. Repo VARIABLE EXEC_BEST_SLIP_CENTS if it ever needs loosening.
BEST_SLIP = max(0.0, float(os.environ.get("EXEC_BEST_SLIP_CENTS") or 0)) / 100.0
# Nov 11: how many plays are probed at once to warm the cache. Bounded because ProphetX serialises
# behind _PX_PACE (1 request/1.1s) whatever the concurrency, so more workers buy nothing on that
# venue and only add load to the other three. Repo VARIABLE EXEC_PREFETCH_WORKERS.
PREFETCH_WORKERS = max(1, min(8, int(os.environ.get("EXEC_PREFETCH_WORKERS") or 4)))

# BOARD v3 / LIQ-BOT CONTROLLED PILOT UNIT (Peter, 11 Nov, written approval). Its own unit, so Lane 1
# is untouched at $300. Same to-win/risk asymmetry as Lane 1: minus money sizes to WIN the unit,
# plus money RISKS it. Every sizing helper below takes `unit` and DEFAULTS TO LIVE_UNIT, so every
# pre-existing Lane 1 call site is byte-for-byte unchanged in behaviour.
BOARD_UNIT = 200.0


def unit_for(lane):
    """The live unit for a lane. The board pilot ($200) and R1 ($200) differ; everything else is Lane 1's unit."""
    return BOARD_UNIT if str(lane or "") == "board" else R1_UNIT if str(lane or "") == "r1" else LIVE_UNIT


LANE_NAME = {"board": "BOARD V3", "r1": "R1", "lane2": "LANE 2", "rules": "PHASE 1"}


def lane_report(results):
    """Nov 11 (Peter): separate performance reporting per lane. Each live lane has its OWN unit,
    play cap and daily risk limit, so one combined number hides which lane is near its ceiling.
    Report only - nothing here feeds a decision. Private email, so dollars are fine; the public
    Actions log still prints counts only."""
    out = ["LANES (this run; today's exposure is ET-day, from the ledger registry)"]
    for lane, name, unit, cap, lim, store, on in (
            ("rules", "Phase 1", LIVE_UNIT, None, None, None, px_live.LIVE),
            ("board", "Board v3", BOARD_UNIT, BOARD_MAX_PLAYS, BOARD_DAILY_RISK, BOARD, BOARD_LIVE),
            ("r1", "R1", R1_UNIT, R1_MAX_PLAYS, R1_DAILY_RISK, R1, R1_LIVE)):
        rs = [r for r in results if (r.get("play") or {}).get("source") == lane
              or (lane == "rules" and (r.get("play") or {}).get("source") in (None, "muse", "rules"))]
        placed = [r for r in rs if ((r.get("live") or {}).get("order") or {}).get("status") == "placed"]
        rested = [r for r in rs if ((r.get("live") or {}).get("rest") or {}).get("status") == "placed"]
        line = (f"  {name}: {'LIVE' if on else 'OFF'} | unit ${unit:,.0f} | {len(rs)} play(s) this run, "
                f"{len(placed)} placed, {len(rested)} rested")
        if store is not None:
            line += ("  |  today: " + (f"{len(store['keys'])}/{cap} plays, ${store['risk']:,.2f}/${lim:,.0f}"
                                       if store["known"] else "exposure UNKNOWN (fail closed)"))
        out.append(line)
    out.append(f"  Global stop (all lanes together): ${px_live.DAILY_STOP:,.0f}; per-order guard "
               f"${px_live.MAX_ORDER:,.0f}. Each lane's own limit applies ON TOP of it.")
    return "\n".join(out)


def lane_of(r):
    """The lane a result belongs to. Phase 1 is the default: its plays carry no lane marker, and an
    UNLABELLED notification is exactly what Peter asked to stop seeing (Nov 11)."""
    lv, src = (r.get("live") or {}), str((r.get("play") or {}).get("source") or "")
    return str(lv.get("lane") or "") or (src if src in LANE_NAME else "rules")


def lane_tag(r):
    """'[R1] ' / '[BOARD V3] ' / '[PHASE 1] ' - which lane fired, on EVERY notification."""
    return f"[{LANE_NAME.get(lane_of(r), 'PHASE 1')}] "


def live_play_alert(r):
    """Nov 11 (Peter): R1 is a LIVE BOT LANE, so its qualifying plays must reach the phone like
    Phase 1's do. R1's own signal alerts are MUTED upstream by the non-Top-25 filter
    (NCAAF_TOP25=filter), so without this the only R1 notification was the fill - Peter would see
    money move before he saw the play.

    Fires once per play, at the moment the lane has decided to bet and the order is about to go in.
    Deduped across runs for free: already_handled() greps Gmail for the play's pid, every run email
    carries it, so a play is never processed - or alerted - twice. Non-qualifying signals are
    untouched and stay muted; this is not a paper-alert firehose.

    Carries game, bet, line, after-fee alert odds, exchange and the PROPOSED stake. push() sends
    ntfy and mirrors to Telegram once, so there is exactly one message per channel."""
    p, lv = r.get("play") or {}, (r.get("live") or {})
    # Nov 11 (Peter, "retry"): a retried play must not re-alert. A refusal now leaves the play new
    # so the next run re-evaluates it, which without this would send an identical LIVE PLAY message
    # every few minutes until tip-off - around a hundred for an evening game. The xrty token written
    # by the refusing run is looked up in the SAME batched search as the xpid tokens, so suppression
    # costs no extra round trip. If the map is unavailable the alert still goes out: being told
    # twice is the right failure, being told nothing is not.
    if p.get("play_key") and any(SEEN["tok"].get(retry_tok(k)) for k in handled_keys(p)):
        return
    e = r.get("entry") or {}
    af = e.get("price_after_fee")
    bk = lv.get("book") or "?"
    body = "\n".join(x for x in [
        f"{p.get('sport') or ''} {p.get('game') or ''}".strip(),
        p.get("bet") or "",
        (f"alert {int(af):+d} after fees" if af is not None else ""),
        (f"routing to {BOOK_NAME.get(bk, bk)} at {int(lv['shown']):+d}"
         f" ({int(lv['am']):+d} after fees)" if lv.get("shown") is not None and lv.get("am") is not None
         else f"routing to {BOOK_NAME.get(bk, bk)}"),
        (f"line {fmt_line('total' if ' Over ' in f" {p.get('bet') or ''} " or ' Under ' in f" {p.get('bet') or ''} " else 'spread', lv['line'])}"
         if lv.get("line") is not None else ""),
        (f"proposed stake ${float(lv['risk']):,.2f}"
         + (f" to win ${float(lv['to_win']):,.2f}" if lv.get("to_win") else "") if lv.get("risk") else ""),
        ("PARTIAL expected: depth is short of the full stake" if lv.get("partial") else ""),
        "Send STOP on ntfy to pause.",
    ] if x)
    push(f"{lane_tag(r)}LIVE PLAY: {(p.get('bet') or '')[:50]}", body)   # mirror=True: one ntfy, one Telegram


def lane_note(r, head, res=None, book=None, limit=None, extra=""):
    """ONE notification body for every lane and every order state, so no lane can drift into
    reporting less than another (Peter, Nov 11). Carries lane, state, game, bet and line, the
    execution odds AFTER FEES, the exchange, the stake, the fill status and the order id."""
    p, lv, res = r.get("play") or {}, (r.get("live") or {}), (res or {})
    bk = book or res.get("book") or lv.get("book") or "?"
    shown = res.get("avg_price") if res.get("avg_price") is not None else (
        limit if limit is not None else lv.get("am"))
    asked = res.get("asked_stake") if res.get("asked_stake") is not None else lv.get("risk")
    fs, oid = res.get("filled_stake"), res.get("order_id")
    out = [f"{lane_tag(r)}{head}", f"{p.get('sport') or ''} {p.get('game') or ''}".strip()]
    out.append(p.get("bet") or "")          # the alert, as Peter saw it
    took = bet_text(r, lv.get("line"), shown) if shown is not None else ""
    if took and "?" not in took:             # the line actually taken, when it differs
        out.append(f"took: {took}")
    elif lv.get("line") is not None and shown is not None:
        out.append(f"took: {fmt_line((r.get('reval') or {}).get('mtype'), lv['line'])} at {int(shown):+d}")
    out.append(f"{BOOK_NAME.get(bk, bk)}" + (f" at {int(shown):+d} after fees" if shown is not None else ""))
    if asked:
        out.append(f"stake ${float(asked):,.2f}"
                   + (f" to win ${float(lv['to_win']):,.2f}" if lv.get("to_win") else ""))
    if fs is None:
        out.append("fill: UNKNOWN - counted in full until a read confirms it")
    elif float(fs) <= 0:
        out.append("fill: NONE")
    elif asked and float(fs) < float(asked) - 0.01:
        out.append(f"fill: PARTIAL ${float(fs):,.2f} of ${float(asked):,.2f}")
    else:
        out.append(f"fill: FULL ${float(fs):,.2f}")
    out.append(f"order {oid}" if oid else "order id: none")
    if extra:
        out.append(extra)
    return "\n".join(x for x in out if x)


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


def retry_tok(key):
    """Token on a play whose order was REFUSED with nothing placed (Peter, Nov 11: "retry").

    Deliberately NOT an xpid: already_handled() must keep answering "not handled" so the next run
    re-evaluates the play from scratch. Its only job is to stop the LIVE PLAY phone alert repeating
    on every retry - the same division of labour as held_tok(). Nine candidates were permanently
    skipped on Nov 11 because a refusal wrote a real xpid, which read as a completed decision."""
    return "xrty" + hashlib.sha1(key.encode()).hexdigest()[:12]


def order_retryable(r):
    """True only when this run placed NOTHING for this play and the refusal can change by next run.

    Defaults to NOT retryable in every uncertain case, because the two mistakes are not symmetric:
    wrongly retrying a PLACED order risks a double bet, while wrongly not retrying a refused one
    costs an opportunity. So this demands positive proof that nothing went out - a refused status,
    no order id, no resting bid, and no placed remainder on any other venue. A "dry" status (live
    switch off) is NOT retryable either: nothing is ever placed in that mode, so retrying would
    re-alert the same play every run forever."""
    lv = (r.get("live") or {})
    o = lv.get("order") or {}
    if r.get("verdict") != "WOULD PLACE" or o.get("status") != "refused":
        return False
    if o.get("order_id") or o.get("filled_stake"):
        return False                                   # something exists at a venue - never retry
    if (lv.get("rest") or {}).get("status") == "placed":
        return False
    return not any((m or {}).get("status") == "placed" for m in (lv.get("more") or []))


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


def handled_keys(p):
    """The pid namespace(s) this play is deduped under - the ONLY place that rule lives.

    source rules/lane2 get their own namespace, so Muse's verdict on the same play is still
    evaluated (Lane 2 too: it never blocks or is blocked by another lane's record)."""
    if p.get("source") in ("rules", "lane2"):
        return {p["play_key"]}
    return {p["play_key"], derive_key(p) or p["play_key"]}


LEDGER_ROWS = []   # Nov 11: the ledger rows bot_orders() parsed THIS RUN, from whichever store it
# read. kalshi_rest_reports() reuses them instead of running a second full "Bets LIVE:" scan with
# its own RFC822 fetches - the same work, done twice, measured at 68.6s. Empty means bot_orders()
# has not run or could not read, and the reporter then falls back to its own scan.
TOKRE = re.compile(r"\b(?:xpid|xrty|xwp)[0-9a-f]{12}\b")
TOKENS_SEEN = set()   # Nov 11: every dedupe/side token found while bot_orders already had the
# "Bets LIVE:" emails open. Collected there so the token backfill costs NO extra Gmail scan.
SEEN = {"tok": {}}   # this run's token map from handled_pids(): xpid -> handled, xrty -> already alerted
HANDLED_DAYS = 4   # Nov 11 (Peter, "why are you looking back so far"): the dedupe search had NO date
# bound at all - X-GM-RAW "xpid..." scanned the whole mailbox history, for every pid, every run, which
# is why one search cost ~30s. Bounded to the same 4-day window bot_orders() already uses for the
# order registry, so the two stores cover the same period and a play cannot be "forgotten" by one
# while the other still counts its money. Games here start within hours of the alert, so a pid older
# than four days cannot belong to a live play.


def handled_pids(M, cands, chunk=20, days=HANDLED_DAYS):
    """{pid: True/False} for every candidate's pids, in ONE Gmail search instead of two per play.

    Nov 11 (Peter, "we need to get rid of checking emails"): already_handled() ran up to two
    X-GM-RAW searches per candidate. Measured on run 43052291191: 9 candidates, 15:50:46 -> 15:55:16
    = 4.5 minutes of serial Gmail round-trips to conclude "new: 0" - about 30s per candidate, and
    the single largest cost in the run, larger than the 79s registry read.

    Gmail's raw search takes OR, and a message matching `a OR b` is a superset of the messages any
    single-term search would return. So: one OR search per chunk finds the few run emails carrying
    ANY of the pids, those messages are fetched once, and each pid is then checked against that text
    in memory. Per-pid answers are identical; the round trips go from 2N to roughly 1.

    FAILS CLOSED exactly as gsearch_strict does. Nov 8's rule still governs: this is the
    duplicate-bet guard, and a guard that answers "no" when it cannot see is fail-open on money, so
    every failure raises and aborts the run rather than reporting "never placed before". Run
    42351892592 (7 Nov) proved the search layer really does drop mid-call (SSLEOFError inside this
    very function), which is why nothing here is wrapped in a forgiving try."""
    # Both token families in the SAME search: xpid answers "handled, never touch again" and xrty
    # answers "refused before, retry but do not re-alert". Asking for them together costs nothing
    # extra - same round trips, same fetched messages.
    want = sorted({pid(k) for p in cands for k in handled_keys(p)}
                  | {retry_tok(k) for p in cands for k in handled_keys(p)})
    if not want:
        return {}
    # Nov 11 (Peter): the private registry answers this when it is known complete AND the claim is
    # fresh - no Gmail at all. Measured 13.6s on Gmail for 21 candidates against ~0.3s for one
    # contents GET. Until the token backfill has run, or if the store cannot be read, Gmail is used
    # exactly as before: a store that might be missing a token must never answer "not handled",
    # because that is how a play gets processed - or bet - twice.
    if registry.enabled():
        try:
            if registry.tokens_complete():
                have = registry.token_set()
                return {x: (x in have) for x in want}
        except Exception as ex:
            LOG.append(f"token store unreadable, using Gmail: {str(ex)[:50]}")
    uids, seen = [], set()
    for i in range(0, len(want), chunk):
        q = f"newer_than:{days}d (" + " OR ".join(want[i:i + chunk]) + ")"
        typ, data = M.uid("SEARCH", "X-GM-RAW", '"' + q + '"')
        if typ != "OK":
            raise RuntimeError("Gmail search failed")   # same contract as gsearch_strict
        for u in (data[0].split() if data and data[0] else []):
            if u not in seen:
                seen.add(u)
                uids.append(u)
    blob = []
    for u in uids:
        typ, d = M.uid("FETCH", u, "(RFC822)")   # RFC822: the same surface X-GM-RAW searched
        if typ != "OK" or not d or not d[0]:
            raise RuntimeError("Gmail fetch failed")
        raw = d[0][1] if isinstance(d[0], tuple) and len(d[0]) > 1 else b""
        blob.append(raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw))
    text = "\n".join(blob)
    return {x: (x in text) for x in want}


def already_handled(M, p, seen=None):
    """Handled before under its own key OR under the play's game+side key (so a re-sent play never runs twice).

    `seen` is the handled_pids() map for this run. Passed, this is a dict lookup and touches no
    network; omitted, it falls back to the original per-pid strict searches so every existing caller
    and test keeps working unchanged."""
    keys = handled_keys(p)
    if seen is not None:
        return any(seen.get(pid(k), False) for k in keys)
    # same date bound as the batched path, so the two agree and neither scans the whole mailbox
    return any(gsearch_strict(M, f"newer_than:{HANDLED_DAYS}d {pid(k)}") for k in keys)


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
    # Nov 11 (Peter, "fail closed quickly"): the refresh wait runs ONCE PER RUN.
    #
    # Measured on run 43083072268: positions first attempt 80.0s, retry 239.4s, and Novig ended
    # blind anyway. novig_positions() is called twice per run - the parallel read and then the
    # parallel retry - and each call that found a stale snapshot asked the home PC for a fresh one
    # and slept up to 90s waiting. Waiting a second time cannot help: nothing between the two
    # attempts makes a home PC that did not answer in 90 seconds answer in the next 90.
    #
    # Fails closed exactly as before - a stale snapshot still returns None, Novig is still blind,
    # and no live order goes out on any venue. It just reaches that answer in seconds.
    if _NVERR.get("waited"):
        _NVERR["why"] += " | snapshot still stale (refresh already awaited this run)"
        return None
    try:
        snap, age = _snap_read(tok)
        if (age > SNAP_MAX_MIN or not snap.get("ok")) and _snap_refresh(tok):
            _NVERR["waited"] = True   # one refresh wait per run, however many callers ask
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
            ck = md_key(b, al, mtype, side, ln, price, teams)
            if ck in MD["c"]:          # same game, same market, same side, same line, same alert
                MD["hit"] += 1         # -> the identical call; serve it instead of refetching
                return MD["c"][ck]
            MD["miss"] += 1
            t0 = time.time()   # Nov 11: per-venue call count and elapsed (PERF; measurement only)
            try:
                if b == "novig":
                    r = bc.check_alert(dict(al, bet=bet_at(al["bet"], mtype, line, ln)), evs_by, mks_by_event)
                else:
                    fn = {"prophetx": bc.px_check, "kalshi": bc.kalshi_check, "polymarket_us": pmus_check}[b]
                    r = fn(al, mtype, side, ln, price, teams)
                perf_venue(b, time.time() - t0, (r or {}).get("status") == "ok")
                MD["c"][ck] = r
                return r
            except Exception as ex:
                perf_venue(b, time.time() - t0, False)
                e = {"status": f"error: {str(ex)[:80]}"}
                MD["c"][ck] = e   # an error is a result too: do not hammer a failing venue per play
                return e
        books = ("novig", "prophetx", "kalshi", "polymarket_us")
        with ThreadPoolExecutor(max_workers=4) as tp:
            return dict(zip(books, tp.map(one, books)))

    with perf("probe alert line"):
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
    with perf("probe nearby lines"):
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
    # Nov 11 (Peter, "original alert line or strictly better"): board v3 plays carry NO floor_line -
    # the board producer never writes one (0 of 1045 rows in board/calls.json), so the Oct 31
    # bet-only-at floor never bound on Lane 3. Without it, better_halfpoints could convert to a
    # WORSE line whenever an estimated half-point value (half_point(), HP_FALLBACK when the ladders
    # cannot say) appeared to compensate, with only the -130 cap behind it. A board play's floor is
    # its OWN alert line. Lane 1 is untouched: it keeps the floor its producer supplies.
    if floor is None and mtype in ("spread", "total") and (p.get("source") == "board" or p.get("source") == "r1"):   # R1 too: its own alert line or strictly better
        floor = line
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
    _u = unit_for(p.get("source") if p.get("source") in ("board", "r1") else None)
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
                others=[c for c in capped if c is not pick][:5],
                # Nov 11 (Peter, check 8): what revalidate() needs to RE-READ the chosen venue at
                # order time. probe() is a closure inside evaluate, so the inputs are stashed here
                # rather than reconstructed at the order site - reparsing is where drift creeps in.
                reval={"al": al, "mtype": mtype, "side": side, "price": price, "teams": teams,
                       "line": line, "alert_af": alert_af, "alert_cost": alert_cost,
                       "px_tol": px_tol, "hp": hp})


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
            else "[R1] " if p.get("source") == "r1"
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
    if order_retryable(r):
        # Nov 11 (Peter, "retry"): refused with nothing placed, so NO xpid and NO xwp - the play
        # stays new for the next run and the opposite side stays free, because neither a bet nor a
        # side was actually taken. Only the alert-suppressing token is written.
        tag = retry_tok(dk or p["play_key"])
    else:
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


# ---------------------------------------------------------------- PERF (Nov 11, Peter: instrument
# the silent block). A run's own log showed 465 of 596 seconds inside ONE gap with no output, so
# where the time goes was a guess. This records elapsed seconds per operation and CALL COUNTS per
# venue, and prints them at the end of the run. Counts and seconds only - no amounts, so it is safe
# in the public Actions log. Pure measurement: nothing here feeds a decision.
# ---------------------------------------------------------------- per-run market-data cache
# Nov 11 (Peter): "avoid repeatedly fetching the same game across Phase 1, Board v3 and R1" and
# "cache reusable market data within each run without using stale quotes for order submission".
#
# evaluate() probes 5 lines x 4 books PER PLAY. When one game qualifies in more than one lane - an
# NBA total under can be a Phase 1 play AND a Board v3 play - every one of those reads is repeated.
#
# SOUNDNESS. The key is every input the readers actually use. bc.px_check / kalshi_check /
# pmus_check read al["sport"], al["start_utc"], al["bet"], teams, mtype, side, line AND price -
# price matters because ladder_result() derives dollars_at_alert_price_or_better from it. Equal keys
# therefore mean equal arguments, so a cached value is the value the call would have returned.
#
# ORDER TIME IS NEVER CACHED. revalidate() goes through reread_book(), which calls the readers
# directly and never consults this cache, so the price, depth and market status behind an actual
# order are always read fresh. The cache serves EVALUATION only, which is exactly the line Peter
# drew.
MD = {"c": {}, "hit": 0, "miss": 0}


def md_key(b, al, mtype, side, ln, price, teams):
    return (b, al.get("sport"), al.get("start_utc"), al.get("bet"), mtype, side,
            None if ln is None else round(float(ln), 2), price, tuple(teams or ()))


PERF = {"t": collections.OrderedDict(), "n": collections.Counter(), "venue": collections.Counter(),
        "venue_s": collections.Counter(), "err": collections.Counter()}


class perf:
    """with perf('label'): ... - accumulates elapsed seconds and a count under that label.

    Nov 11: optional n, for a block that does n units of work in one bracket (one Gmail search per
    candidate play, say). The report then shows the real call count instead of x1, which is what
    makes a per-item cost readable."""

    def __init__(self, label, n=1, rollup=False):
        self.label = label
        self.n = n
        # rollup: this bracket ENCLOSES other brackets, so its seconds are a superset of theirs.
        # Reported, but excluded from the percentage denominator - otherwise the same seconds are
        # counted twice and every other row's share is understated (Nov 11: evaluate encloses the
        # probes, and a duplicated label on the registry read read as "bot_orders runs twice").
        self.rollup = rollup

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *a):
        d = time.time() - self.t0
        PERF["t"][self.label] = PERF["t"].get(self.label, 0.0) + d
        PERF["n"][self.label] += self.n
        if self.rollup:
            PERF.setdefault("roll", set()).add(self.label)
        return False


def perf_venue(book, secs, ok=True):
    """One venue read: its elapsed seconds and whether it came back usable."""
    PERF["venue"][book] += 1
    PERF["venue_s"][book] += secs
    if not ok:
        PERF["err"][book] += 1


def perf_report():
    """One block at the end of the run. Slowest operation first."""
    out = ["PERF (seconds and call counts only; measurement, never a gate)"]
    roll = PERF.get("roll") or set()
    tot = sum(v for k, v in PERF["t"].items() if k not in roll) or 1.0
    for lab, sec in sorted(PERF["t"].items(), key=lambda kv: -kv[1]):
        if lab in roll:   # a superset of the brackets inside it: shown, not counted
            out.append(f"  {lab:<34} {sec:8.1f}s  (rollup)  x{PERF['n'][lab]}")
        else:
            out.append(f"  {lab:<34} {sec:8.1f}s  {100 * sec / tot:5.1f}%  x{PERF['n'][lab]}")
    out.append(f"  {'MEASURED TOTAL (excl. rollups)':<34} {tot:8.1f}s")
    if MD["hit"] or MD["miss"]:
        tot = MD["hit"] + MD["miss"]
        out.append(f"  market-data cache: {MD['hit']} hit / {MD['miss']} fetched "
                   f"({100 * MD['hit'] / max(tot, 1):.0f}% of {tot} reads served from cache)")
    if PERF["venue"]:
        out.append("  venue reads (calls / seconds / unusable):")
        for b, n in PERF["venue"].most_common():
            out.append(f"    {b:<16} {n:5d} calls  {PERF['venue_s'][b]:7.1f}s  "
                       f"{PERF['venue_s'][b] / max(n, 1):5.2f}s each  {PERF['err'][b]} unusable")
    return "\n".join(out)


MKT = {"evs": None, "mks": None}   # the market map main() built this run; revalidate() needs it for Novig


def reread_book(book, ln, rv):
    """One venue's CURRENT ladder at one line, using the same readers probe() uses.
    probe() is a closure inside evaluate(), so this mirrors its `one(b)` rather than reparsing."""
    al, mtype, side, price, teams = rv["al"], rv["mtype"], rv["side"], rv["price"], rv["teams"]
    if book == "novig":
        if MKT["evs"] is None or MKT["mks"] is None:
            return None
        return bc.check_alert(dict(al, bet=bet_at(al["bet"], mtype, rv["line"], ln)), MKT["evs"], MKT["mks"])
    fn = {"prophetx": bc.px_check, "kalshi": bc.kalshi_check, "polymarket_us": pmus_check}.get(book)
    return fn(al, mtype, side, ln, price, teams) if fn else None


def revalidate(r, stake=None):
    """Nov 11 (Peter, check 8): re-read the CHOSEN venue's own book immediately before submitting.

    Before this the only order-time re-read was Pinnacle fair (the Nov 3 price check). The venue's
    own price, depth and market status came from evaluate(), which on a 30-minute workflow running
    up to 3 catch-up passes can be many minutes stale - the order could be sent against a book that
    had moved, thinned, or closed.

    Returns (ok, why, fresh). `fresh` is the re-read ladder row, so the order is sized from CURRENT
    levels, not the stale ones. The bar is the IDENTICAL gate the play qualified under: the frozen
    qualification price, the stored px_tol (so ProphetX and Novig keep their 2c and nobody else
    gets any), the same line, and the -130 cap.

    FAILS CLOSED everywhere: unreadable venue, closed or missing market, a move to another line, a
    price worse than the gate, no frozen basis, or no depth at the threshold all mean NO ORDER.
    Depth short of the full stake is NOT a refusal - it flows to the existing partial-fill shrink,
    so a full fill is still never assumed."""
    lv, rv = r.get("live") or {}, r.get("reval") or {}
    book, ln = lv.get("book"), lv.get("line")
    if not rv or not book:
        return False, "no revalidation basis recorded - fail closed", None
    mtype = rv.get("mtype")
    if mtype != "moneyline" and ln is None:
        return False, "no line to revalidate against - fail closed", None
    try:
        fresh = reread_book(book, ln, rv)
    except Exception as ex:
        return False, f"{book} could not be re-read before the order ({str(ex)[:60]}) - fail closed", None
    if not fresh or fresh.get("status") != "ok":
        return False, (f"{book} is not quoting this market at order time "
                       f"({(fresh or {}).get('status', 'unreadable')}) - fail closed"), None
    am = fresh.get("best_price_american")
    if am is None:
        return False, f"{book} has no price at order time - fail closed", None
    if mtype != "moneyline":
        bl = book_line(fresh)
        if bl is None or abs(bl - ln) > 1e-9:
            return False, (f"{book} moved off {fmt_line(mtype, ln)} before the order "
                           f"(now {fmt_line(mtype, bl)}) - fail closed"), None
    am_q = fresh.get("best_price_american_qual")
    if am_q is None:
        am_q = qual_price(am, book)
    if am_q is None:
        return False, f"{book} has no frozen qualification price at order time - fail closed", None
    tol = rv.get("px_tol", 0.0) if book in TOL_BOOKS else 0.0
    # Nov 11 FIX: compare the EQUIVALENT price at the alert line, exactly as evaluate()'s gate does
    # (c_eq_q = american_to_prob(am_q) - hb * hp). Before this the raw price at the CHOSEN line was
    # compared against the bar for the ALERT line, with the half-point credit dropped. A better line
    # always carries a worse raw price - that is why it is worth taking - so this refused EVERY play
    # that routed to a better line whenever the improvement outran the 2c allowance. PROVEN on the
    # Nov 11 Denver vs Memphis play from its own ledger row: "now -111, allowed -102" was -111 at
    # 231.5 judged against the 230.5 bar, when its own threshold was -118 and its equivalent at the
    # alert line was +104 against an alert of -100. (The Lakers refusal that day is NOT this bug:
    # -130 against a -121 alert sat inside the 2c allowance even raw. Its reason was never
    # recovered - the run logs had expired - so it stays an open item rather than a second example.)
    # hp is the stored evaluate-time value, so the bar stays the IDENTICAL one the play qualified
    # under; hb is recomputed from the alert line to the re-read line, which book_line() has just
    # confirmed is still the chosen line.
    hb = 0.0 if mtype == "moneyline" else better_halfpoints(mtype, rv.get("side"), rv["line"], ln)
    c_eq_q = american_to_prob(am_q) - hb * (rv.get("hp") or 0.0)
    if c_eq_q > rv["alert_cost"] + tol + 1e-9:
        # the worst acceptable RAW price at this line - the same number evaluate() stored as thr,
        # so the message can never again quote a bar from a different line than the price it refused
        allowed = (lv.get("px") or {}).get("thr")
        at_alert = lm.american(min(max(c_eq_q, 0.01), 0.99))
        return False, (f"{book} moved worse than the alert gate before the order "
                       f"(now {am_q:+d} at {fmt_line(mtype, ln)} = {at_alert:+d} at "
                       f"{fmt_line(mtype, rv['line'])}"
                       + (f", allowed {allowed:+d}" if allowed is not None else "")
                       + ") - fail closed"), None
    if mtype in ("spread", "total") and am_q < CAP_LINE:
        return False, f"{book} is now below the {CAP_LINE} cap ({am_q:+d}) - fail closed", None
    thr = (lv.get("px") or {}).get("thr")
    avail = sum(d for a, d in levels(book, fresh, qual=True)
                if a is not None and thr is not None and a >= thr)
    if avail <= 0:
        return False, f"{book} has no depth at or better than the alert number at order time - fail closed", None
    short = (f"; depth ${avail:,.0f} short of ${stake:,.0f} - partial rules apply"
             if stake and avail < float(stake) else "")
    return True, f"re-read {book} at order time: {am:+d}, depth ${avail:,.0f}{short}", fresh


def px_limit(pxd, stake, slip=None):
    """(strike_id, limit price, stake) for a ProphetX fill-or-kill: walk the ladder best price first, only levels at
    or better than the alert-equivalent threshold, until the stake is covered. Stake shrinks to what's there.

    Nov 11 (Peter, "BEST PRICE FIRST, NOT MAXIMUM DOLLARS FILLED"): the walk now stops at the BEST
    AVAILABLE price. Before this it kept descending to worse levels purely to reach `stake`, set the
    order's limit to the worst level it reached, and sized every contract at that worst price - so the
    bot paid up to widen the fill, and the 2c tolerance behaved as a target rather than a ceiling
    (`thr` is built as alert_cost + tol, so nothing anchored the walk to what was actually on offer).
    `thr` stays the OUTER eligibility bound. Levels worse than the best qualifying one by more than
    `slip` are no longer taken to reach the unit; the stake shrinks to the best-priced depth and
    live_remainder() takes what is left to the next VENUE at its own threshold.

    The one exception is MIN_ORDER: a sub-minimum order is refused outright and the play is lost, so
    while the walk has not yet gathered MIN_ORDER it may still extend past the slip bound (Peter,
    Nov 11: guard kept). It never extends past `thr` or the -130 cap, which are unchanged."""
    thr = pxd.get("thr")
    if slip is None:
        slip = BEST_SLIP
    lv = sorted((x for x in pxd.get("buy") or [] if x.get("american_after_fee") is not None and thr is not None
                 and x["american_after_fee"] >= thr and x.get("strike_id")), key=lambda x: -x["american"])
    got, limit = 0.0, None
    best = american_to_prob(lv[0]["american_after_fee"]) if lv else None
    for x in lv:
        # price-first: a worse level is taken only while the fill is still short of MIN_ORDER
        if (best is not None and american_to_prob(x["american_after_fee"]) > best + slip + 1e-9
                and got >= MIN_ORDER - 0.01):
            break
        got += x.get("dollars") or 0
        limit = x["american"]
        if got >= stake:
            break
    if not lv:
        return None, None, 0.0
    return lv[0]["strike_id"], limit, round(min(stake, got), 2)


def _account_rows(rows, graded, ids, seen_oids, _intents, _confirmed):
    """The ledger-row accounting, lifted out of bot_orders() UNCHANGED so that both the Gmail
    registry and the private store feed the identical rules (Nov 11).

    Extracted rather than reimplemented on purpose: one copy of the daily-stop, board/R1 lane and
    dedupe arithmetic means the two stores cannot drift apart. Mutates ids, seen_oids, _intents,
    _confirmed, LIVEKEYS, BOARD, R1 and NONPX exactly as the inline loop did."""
    for row in rows:
        for is_rest, lo in ([(False, row.get("live_order") or {}), (True, row.get("live_rest") or {})]
                            + [(False, x or {}) for x in (row.get("live_more") or [])]):
            if lo.get("status") != "placed" or not lo.get("order_id"):
                continue
            oid = str(lo["order_id"])
            ids[oid] = lo.get("book") or "prophetx"
            if row.get("key"):
                LIVEKEYS.add(row["key"])
            # Nov 11: ONE ORDER IS COUNTED ONCE. ids is a dict and BOARD["keys"] is a set, so
            # both already dedupe - but BOARD["risk"] and NONPX["today"] are running sums, so
            # the same order described in two 'Bets LIVE:' emails used to add its money twice.
            # That now happens by design (journal_order writes a row the moment an order is
            # placed, and the end-of-run ledger writes the same order again) and could already
            # happen when a catch-up pass re-sent a ledger. Identity is the ORDER ID: the money
            # below is accumulated on first sight only. Over-counting is the safe direction but
            # it is still wrong - it would silently shrink the $1,500 board limit and the daily
            # stop. ids and LIVEKEYS are set above, so dedupe never weakens duplicate blocking.
            # Nov 11: the money identity is the CLIENT ID when there is one, so the
            # write-ahead intent row and the confirmed row for the SAME order count once -
            # while ids above still carries the venue's real order_id, which is the only
            # field linking a ProphetX TRADE back to an order.
            cid = lo.get("client_id")
            if cid:   # resolved AFTER the loop: IMAP order is not chronological, so a
                # confirmed row may be read before its own intent row.
                (_intents if lo.get("intent") else _confirmed)[str(cid)] = row
            if str(cid or oid) in seen_oids:
                continue
            seen_oids.add(str(cid or oid))
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
            if row.get("source") == "r1" and d_et in (None, datetime.now(lm.ET).date()):   # same rules as the board block above
                if row.get("key"):
                    R1["keys"].add(row["key"])
                if graded.get(row.get("key")) not in ("W", "P"):
                    fs_r = lo.get("filled_stake")
                    R1["risk"] += (max(float(fs_r or 0), float(lo.get("asked_stake") or 0))
                                   if (is_rest or fs_r is None) else float(fs_r))
            if graded.get(row.get("key")) in ("W", "P"):
                continue   # settled win/push: not a loss toward the daily stop
            if (lo.get("book") or "prophetx") != "prophetx" and d_et in (None, datetime.now(lm.ET).date()):
                fs = lo.get("filled_stake")   # fill-or-kill: what filled (unknown = all asked); resting: all asked
                NONPX["today"] += (max(float(fs or 0), float(lo.get("asked_stake") or 0)) if (is_rest or fs is None)
                                   else float(fs))


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
        ids, seen_oids = {}, set()   # seen_oids: one order's money is counted once (Nov 11)
        _intents, _confirmed = {}, {}   # write-ahead intents vs confirmed orders, by client_id
        all_rows = []
        # ---- Nov 11 (Peter, "b2"): the private store, when it is KNOWN COMPLETE for this window.
        # Measured: this Gmail read is 81.4s (~200 serial full-message IMAP fetches); one contents
        # GET of the store is ~0.25s. The switch is registry.complete_through(): until a backfill
        # proves the store holds every row Gmail holds for the window, Gmail is read instead, because
        # a store missing history would UNDERCOUNT exposure - fail-open on the one guard that caps a
        # losing day. Any failed write to the store clears that marker, so a dropped write sends the
        # next run back to the slow, complete path on its own.
        cut = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        rdata = None
        if registry.enabled():
            try:
                with perf("registry read (private store)"):
                    if registry.is_complete(cut):
                        rdata = registry.load()
            except Exception:
                rdata = None
        if rdata is not None:
            store_rows = rdata.get("orders") or []
            LEDGER_ROWS[:] = store_rows
            _account_rows(store_rows, graded, ids, seen_oids, _intents, _confirmed)
            # re-assert completeness so the claim cannot outlive the ability to write it: a run that
            # cannot refresh the stamp lets it go stale, and the next run returns to Gmail by itself
            try:
                registry.set_complete_through(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
            except Exception:
                pass
            return _bot_orders_finish(M, ids, _intents, _confirmed)
        # ---- otherwise Gmail, which is always complete, and backfill the store from it
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
        with perf("registry read (Gmail IMAP)"):
            typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", since)
        if typ != "OK":
            return None
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
            TOKENS_SEEN.update(TOKRE.findall(txt))   # free: this text is already in hand
            rows, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
            all_rows.extend(rows)
            _account_rows(rows, graded, ids, seen_oids, _intents, _confirmed)
        # BACKFILL: Gmail was complete for this window, so copying its rows in makes the store
        # complete too - and only then is the marker set. Both must succeed; if either fails the
        # marker is left unset and the next run simply reads Gmail again.
        if registry.enabled():
            try:
                with perf("registry backfill (private store)"):
                    if registry.put_rows(all_rows) and registry.put_tokens(TOKENS_SEEN):
                        registry.set_complete_through(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                        registry.set_tokens_complete()   # the same emails carried both
                    else:
                        registry.invalidate()
                        registry.invalidate_tokens()
            except Exception as ex:
                LOG.append(f"registry backfill failed: {str(ex)[:60]}")
        LEDGER_ROWS[:] = all_rows
        return _bot_orders_finish(M, ids, _intents, _confirmed)
    except Exception:
        return None


def _bot_orders_finish(M, ids, _intents, _confirmed):
    """Shared tail of bot_orders(): unresolved write-ahead intents, then the result.

    Nov 11: an intent with no confirmed order means an order MAY exist at the venue and the bot
    cannot tell (ProphetX trades carry no external_id). Attribution is uncertain, so live_guards()
    refuses every further live order until Peter clears it with an email whose SUBJECT begins
    "INTENT CLEARED <client_id>", after checking My Trades. Subject-only and manual: the bot never
    emits that subject, so it cannot clear its own intent. Unchanged by the store migration - the
    clearance is Peter's email either way."""
    INTENT["open"] = {}
    for k, row in _intents.items():
        if k in _confirmed:
            continue
        try:
            if intent_cleared(M, k):
                continue   # Peter's distinct, manual, subject-only authorization
        except Exception:
            pass           # cannot confirm it was cleared -> keep refusing (fail closed)
        INTENT["open"][k] = row
    BOARD["known"] = True   # the ledger parsed, so today's board exposure above is real
    R1["known"] = True      # ...and today's R1 exposure
    return ids


def _h(x):
    return hashlib.sha1(str(x).encode()).hexdigest()[:12]


GUARD = {"ok": None, "why": ""}
NONPX = {"today": 0.0}   # Oct 28: bot dollars risked today on books other than ProphetX (from the ledger registry)

# ---------------------------------------------------------------- Board v3 pilot limits (Peter, 11 Nov)
# Lane-specific and ADDITIONAL to the global stop, which is untouched: px_live.preflight() still runs
# first and still refuses on the aggregate $2,250. These limits can only ever REFUSE a board order.
BOARD_DAILY_RISK = float(os.environ.get("EXEC_BOARD_DAILY_RISK", "") or "2000")   # Nov 11 (Peter): 1500 -> 2000
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


def r1_gate(risk, key=None):
    """(ok, why) for ONE R1 order of `risk` dollars. Fail closed. Mirrors board_gate: counts submitted AND resting
    orders; a retry, top-up or partial fill of the same key never counts as an extra play. The play cap cannot
    override the risk limit, and neither overrides the global daily stop."""
    if not R1["known"]:
        return False, "R1 exposure unknown this run (ledger unreadable) - fail closed"
    n = len(R1["keys"]) + (0 if (key and key in R1["keys"]) else 1)
    if n > R1_MAX_PLAYS:
        return False, f"R1 play cap: {len(R1['keys'])} already submitted or resting today (ET), cap {R1_MAX_PLAYS}"
    try:
        risk = float(risk or 0)
    except Exception:
        return False, "R1 order risk unreadable - fail closed"
    if risk <= 0:
        return False, "R1 order risk is zero - fail closed"
    if R1["risk"] + risk > R1_DAILY_RISK + 1e-9:
        return False, (f"R1 daily risk limit: ${R1['risk']:,.2f} already at risk today (ET) + "
                       f"${risk:,.2f} would exceed ${R1_DAILY_RISK:,.0f}")
    return True, f"ok (R1 today: {len(R1['keys'])}/{R1_MAX_PLAYS} plays, ${R1['risk']:,.2f}/${R1_DAILY_RISK:,.0f} at risk)"


def live_guards():
    """Once per run, before any live order (Oct 27): load the bot-order registry so the $1,500 daily stop counts only
    the bot's own orders, not Peter's manual bets. Unreadable registry = refuse (fail closed). No loss-streak pause
    (Peter, Oct 27: no 3-loss rule)."""
    if GUARD["ok"] is not None:
        return GUARD["ok"], GUARD["why"]
    ok, why = False, ""
    try:
        # Nov 11: NO perf bracket here. This one wrapped bot_orders(), which has its own brackets
        # for the Gmail scan, the private-store read and the backfill - and one of them reused this
        # exact label. PERF sums per label, so the same seconds were counted twice and n showed x2,
        # which read as "bot_orders runs twice per run". It does not: GUARD caches it, once per run.
        # The inflated label also inflated the denominator every other percentage was computed
        # against. Brackets must not nest; the inner three are the accurate, non-overlapping ones.
        M = imap_open()
        try:
            ids = bot_orders(M)
        finally:
            imap_close(M)
        px_live.set_bot_orders(None if ids is None else list(ids))
        book_live.set_exposure(NONPX["today"])
        if ids is None:
            why = "couldn't read the bot's order registry in Gmail (fail closed)"
        elif INTENT["open"]:
            # Nov 11: a write-ahead intent with no confirmed order. An order of that size may exist
            # at the venue and ProphetX cannot tell us (trades carry no external_id), so the bot's
            # own exposure is uncertain - and uncertain exposure never places. This is what keeps a
            # lost order from accumulating across runs: the SECOND incident cannot happen.
            k, row = next(iter(INTENT["open"].items()))
            lo0 = row.get("live_order") or {}
            why = (f"unreconciled order intent {k} ({lo0.get('book')}, asked "
                   f"${float(lo0.get('asked_stake') or 0):,.2f}, {row.get('decided_utc')}): an order may "
                   f"exist at the venue with no confirmed record. Check My Trades, then clear it with an "
                   f"email whose SUBJECT begins {INTENT_CLEAR_PREFIX} {k}. "
                   + (f"{len(INTENT['open']) - 1} more also open. " if len(INTENT["open"]) > 1 else "")
                   + "No live order will be placed until then (fail closed)")
        else:
            ok = True
    except Exception as ex:
        why = f"live guard check failed ({str(ex)[:60]}) - fail closed"
    GUARD.update(ok=ok, why=why)
    return ok, why


def refuse(r, reason, book=None, **extra):
    """A refused order is a lane event. Nov 11 (Peter): live_play_alert() fires IMMEDIATELY before
    live_order(), and every early refusal here used to return silently - so Peter was told a bet was
    coming and never told it was not. On Nov 11 (Lakers @ Bucks, Under 231.5 at Novig) that silence
    read as a dead bot and he placed the bet by hand, creating a position the registry did not know
    about. A missing refusal message is therefore a correctness risk, not a cosmetic one.

    One message per refusal, lane-tagged, with the reason. Notification only: it changes no decision,
    no price and no size."""
    out = {"status": "refused", "reason": reason}
    if book:
        out["book"] = book
    out.update(extra)
    try:
        tg(lane_note(r, "ORDER REFUSED", out, out.get("book") or (r.get("live") or {}).get("book"),
                     None, extra=str(reason)[:200]))
    except Exception as e:
        LOG.append(f"refusal notify failed: {e}")   # never let the notifier change the refusal
    return out


def watchdog_once(now, plays, rplays, feed):
    """The Muse no-verdict watchdog, called from both of main()'s exit paths.

    Nov 11: moved OFF the pre-order path (measured 4.8-24.1s there). Its own email says "This
    blocks nothing - Muse is a veto, so only a DISAGREE stops a play", and read_verdicts() has
    already loaded those vetoes before any evaluation, so nothing downstream waits on it.

    It is a FUNCTION rather than two inline brackets because a perf label used in two places sums
    the same work under one name - the defect that made bot_orders look like it ran twice."""
    if SOURCE not in ("both",):
        return
    with perf("muse watchdog (Gmail)"):
        try:
            muse_watchdog(now, plays, rplays, feed)
        except Exception as ex:
            print(f"muse watchdog failed: {str(ex)[:60]}")


def run_tokens(results):
    """The dedupe / retry / side-taken tokens this run produced, in the SAME shape fmt() writes
    into the run email. Nov 11: the registry has to learn them or it would answer from an
    ever-staler snapshot while Gmail quietly stayed the only current source.

    Derived from the rendered tag rather than re-deriving the rules, so the two cannot disagree:
    whatever the email records as handled is exactly what the store records as handled."""
    toks = set()
    for r in results or []:
        try:
            toks.update(TOKRE.findall(fmt(r)))
        except Exception:
            continue
    return toks


def fill_reports():
    """Novig + Kalshi fill reporting, moved OFF the critical path (Peter, Nov 11: "stop reading
    emails till we fix this" / "we got to fix this").

    Measured on run 43052291191 from the log's own timestamps: 30s in novig_reports() and 46s in
    kalshi_rest_reports(), both running BEFORE any order work. kalshi_rest_reports() opens its own
    IMAP connection and repeats the SAME scan bot_orders() does - SEARCH "Bets LIVE:" then a full
    RFC822 fetch per email - so a single run was making three or four separate Gmail connections,
    each re-scanning the mailbox from scratch.

    Neither gates an order: both only report fills that already happened, and both dedupe on their
    own token emails, so a run that dies before reaching them simply reports next run. Running them
    after the orders therefore takes ~76s off every play's time-to-order and loses nothing.

    EXEC_FILL_REPORTS=off skips them entirely, for when Peter wants the mailbox left alone. Default
    on, because these are the only notice of a Novig or Kalshi resting fill and that is money
    information - speed is not worth going blind to a fill."""
    if (os.environ.get("EXEC_FILL_REPORTS") or "on").strip().lower() != "on":
        print("fill reports: skipped (EXEC_FILL_REPORTS=off)")
        return
    with perf("novig fill reports (Gmail)", rollup=True):   # encloses the snapshot read bracket
        try:
            novig_reports()
        except Exception as ex:
            print(f"novig report check failed: {str(ex)[:60]}")
    with perf("kalshi resting-fill reports (Gmail)", rollup=True):   # encloses sent_tokens
        try:
            kalshi_rest_reports()
        except Exception as ex:
            print(f"kalshi resting-fill check failed: {str(ex)[:60]}")


def live_order(r):
    """Phase-1 live order (only when EXEC_LIVE is on): ProphetX here, Kalshi / Polymarket US via live_order_other (Oct 28).
    Returns the order record for the email/ledger."""
    lv, p = r["live"], r["play"]
    if journal_latch_why():   # Nov 11: a lost durable row means unknown exposure - place nothing more.
        return refuse(r,                      # First gate, so no other refusal reason can mask it.
                      f"order journal failed earlier this run ({journal_latch_why()}) - no further "
                      f"orders until the next run's registry read reconciles exposure")
    hr = agree_rules.hr_priced(r.get("entry") or {})   # Oct 27: re-check the PRICING book at placement; unknown = refuse
    if hr is not False:
        return refuse(r, "Hard Rock-priced alert: never live" if hr else "pricing book unknown (fail closed)")
    db = agree_rules.deadband(dict(r.get("entry") or {}, sent_to_phone=True))   # Oct 27 retail deadband re-check
    if db is not False:
        return refuse(r, "retail deadband: non-ProphetX at -119 to -110 after fee" if db
                      else "after-fee price unknown (fail closed)")
    if not px_live.LIVE:
        return {"status": "dry", "reason": "live is off"}
    g_ok, g_why = live_guards()
    if not g_ok:
        return refuse(r, g_why)
    # Nov 11 (Peter, check 8): the venue's own price/depth/status, re-read NOW. Covers every book,
    # so it sits before the dispatch. On success the order is sized from the FRESH levels.
    rv_ok, rv_why, fresh = revalidate(r, lv.get("risk"))
    if not rv_ok:
        return refuse(r, rv_why, revalidated=False)
    if isinstance(lv.get("px"), dict):
        lv["px"] = dict(lv["px"], buy=fresh.get("buy_levels") or [],
                        am=fresh.get("best_price_american"),
                        shown=fresh.get("best_price_american_displayed") or fresh.get("best_price_american"))
    lv["reval"] = rv_why
    # Nov 11 (Peter): WRITE-AHEAD. The durable record is a precondition of the order, not a
    # consequence of it. If this cannot be stored, nothing is submitted - so a lost record can
    # never mean untracked exposure. Both lanes pass through here, before the book dispatch.
    i_ok, cid = journal_intent(r, lv.get("book", "prophetx"), lv.get("risk"))
    if not i_ok:
        return refuse(r, "could not store the pre-order record - nothing was submitted (fail closed)")
    lv["client_id"] = cid
    if lv.get("book", "prophetx") != "prophetx":
        return live_order_other(r)
    strike, limit, stake = px_limit(lv["px"], lv["risk"])
    if not strike or stake < MIN_ORDER - 0.01:
        return refuse(r, f"ProphetX ladder can't cover ${MIN_ORDER:.0f}+ at the alert number (have ${stake:.2f})", book="prophetx")
    label = f"{p.get('sport')} {p.get('game')} | {bet_text(r, lv['line'], limit)}"
    res = px_live.place(strike, limit, stake, label)
    if res.get("status") == "refused":   # Nov 11: a refusal is a lane event too
        tg(lane_note(r, "ORDER REFUSED", res, "prophetx", limit, extra=str(res.get("reason"))[:200]))
    if res["status"] == "placed":
        fs, ap = res.get("filled_stake") or 0, res.get("avg_price")
        if fs and ap:
            win = (fs * 100 / abs(ap) if ap < 0 else fs * ap / 100) * 0.98
            tg(lane_note(r, "FILLED", res, "prophetx", limit,
               extra="Send STOP on ntfy to pause."))
        else:
            tg(lane_note(r, "NO FILL", res, "prophetx", limit,
               extra="Fill-or-kill got nothing at this price or better."
                     + ("" if res.get("fills_read") else " Fill read failed: check My Trades.")))
        push("PLACED: " + bet_text(r, lv["line"], limit)[:60],
             f"{label}\nProphetX fill-or-kill: ${res.get('filled_stake') or 0:,.2f} filled"
             + (f" at {res['avg_price']:+d}" if res.get("avg_price") else "") + f" (asked ${stake:,.2f}, limit {limit:+d})."
             + ("" if res.get("fills_read") else " Fill read failed: check My Trades."), mirror=False)
    elif res["status"] == "error":
        tg(lane_note(r, "ORDER ERROR", res, "prophetx", limit,
                      extra=f"{res['reason'][:200]}\nCheck My Trades before retrying."))
        push("LIVE ORDER ERROR: " + (p.get("bet") or "")[:50], f"{label}\n{res['reason']}\nCheck ProphetX My Trades before retrying.", mirror=False)
    out = dict(res, asked_stake=stake, limit=limit, book="prophetx")
    if out.get("status") == "placed":   # Nov 11: durable registry row NOW, before anything can kill the run
        out["journaled"] = journal_order(r, out, cid=lv.get("client_id"))
    return out


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
    limit_cost, count = book_live.plan(lv["px"].get("buy"), lv["px"].get("thr"), lv["risk"],
                                       min_order=MIN_ORDER, slip=BEST_SLIP)   # Nov 11: price-first
    stake = round(count * limit_cost, 2) if limit_cost else 0.0
    if not limit_cost or stake < MIN_ORDER - 0.01:
        return refuse(r, f"{name} ladder can't cover ${MIN_ORDER:.0f}+ at the alert number (have ${stake:.2f})", book=book)
    limit_am = lm.american(limit_cost)
    label = f"{p.get('sport')} {p.get('game')} | {bet_text(r, lv['line'], limit_am)}"
    if book == "kalshi":
        kb = ids.get("kalshi_buy") or []
        if len(kb) != 1:
            return refuse(r, "Kalshi market ambiguous (not exactly one market) - fail closed", book=book)
        res = book_live.kalshi_place(kb[0]["ticker"], kb[0]["buy"], limit_cost, count, label)
    elif book == "polymarket_us":
        if not ids.get("market_slug") or ids.get("long_side") is None:
            return refuse(r, "Polymarket US market unknown - fail closed", book=book)
        res = book_live.pmus_place(ids["market_slug"], bool(ids["long_side"]), limit_cost, count, label)
    elif book == "novig":   # Novig contracts pay 1c: plan() counted $1 contracts, so x100
        if not ids.get("outcome_id"):
            return refuse(r, "Novig outcome unknown - fail closed", book=book)
        res = book_live.novig_place(ids["outcome_id"], limit_cost, count * 100, label, None, derive_key(p) or "")
    else:
        return refuse(r, f"no live order code for {name}", book=book)
    res = dict(res, book=book)
    if res["status"] == "placed" and res.get("sent_to_runner"):
        _sn = lane_note(r, "SENT TO NOVIG (home PC)", res, book, limit_am,
                        extra="Fill-or-kill at this price or better; the fill result follows next run.")
        push("Novig order sent", _sn, mirror=False)   # Nov 11 (Peter): ntfy only, off Telegram
        out = dict(res, asked_stake=stake, limit=limit_am)
        out["journaled"] = journal_order(r, out, cid=lv.get("client_id"))   # Nov 11: durable row now
        return out
    if res["status"] == "placed":
        fs, ac = res.get("filled_stake") or 0, res.get("avg_cost")
        ap = lm.american(ac) if ac else None
        res["avg_price"] = ap
        if fs and ac:
            win = res.get("contracts", 0) * (1 - ac)
            tg(lane_note(r, "FILLED", res, book, limit_am,
               extra="Send STOP on ntfy to pause."))
        else:
            tg(lane_note(r, "NO FILL", res, book, limit_am,
               extra="Fill-or-kill got nothing at this price or better."))
        push("PLACED: " + bet_text(r, lv["line"], limit_am)[:60],
             f"{label}\n{name} fill-or-kill: ${fs:,.2f} filled" + (f" at {ap:+d}" if ap else "")
             + f" (asked ${stake:,.2f}, limit {limit_am:+d})." + ("" if res.get("fills_read") else f" Fill read failed: check {name}."),
             mirror=False)
    elif res["status"] == "error":
        tg(lane_note(r, "ORDER ERROR", res, book, limit_am,
                      extra=f"{res['reason'][:200]}\nCheck {name} before retrying."))
        push("LIVE ORDER ERROR: " + (p.get("bet") or "")[:50], f"{label}\n{res['reason']}\nCheck {name} before retrying.", mirror=False)
    if res.get("status") == "placed" and not res.get("fills_read"):
        res["filled_stake"] = None   # unknown fill: the daily stop counts everything asked
    out = dict(res, asked_stake=stake, limit=limit_am)
    if out.get("status") == "placed":   # Nov 11: durable registry row NOW
        out["journaled"] = journal_order(r, out, cid=lv.get("client_id"))
    return out


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


def pmus_rest_note(order_id, slug, expire, p, lane="rules"):
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
             f"PMUSREST {order_id} {slug} {int(expire.timestamp())} {lane or 'rules'}")
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
                m = re.search(r"PMUSREST (\S+) (\S+) (\d+)(?:\s+(\S+))?", body or "")   # 4th group: lane (Nov 11; older records have none)
                if not m:
                    continue
                oid, slug, exp = m.group(1), m.group(2), int(m.group(3))
                rest_lane = m.group(4) or ""   # "" -> written before lanes were recorded
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
                # Nov 11 (Peter, notification reliability): submitted, partial, filled, rejected and
                # resting all reach Telegram already; a CANCEL only went to email, so the one order
                # state that silently frees exposure was the one Peter could not see on his phone.
                try:
                    tg(f"[{LANE_NAME.get(rest_lane, 'PHASE 1' if rest_lane in ('', 'rules') else rest_lane.upper())}] "
                       f"{'CANCELLED' if ok else 'CANCEL FAILED'} Polymarket US: resting bid on {slug[:40]} "
                       f"reached T-30.\n{res.get('status')}: {res.get('state') or res.get('reason') or ''}"
                       + ("" if ok else "\nIt rests until end of day - cancel it in the app."))
                except Exception:
                    pass   # notification must never change the cancel outcome
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
    if journal_latch_why():   # Nov 11: unknown exposure places nothing, resting bids included
        return {"status": "refused",
                "reason": f"order journal failed earlier this run ({journal_latch_why()}) - no further "
                          f"orders until the next run's registry read reconciles exposure"}
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
                res["rest_recorded"] = pmus_rest_note(res.get("order_id"), x["market_slug"], expire, p,
                                                      lane_of(r))
        else:
            continue
        res = dict(res, book=b, limit=lm.american(c), asked_stake=round(risk, 2), expires_utc=expire.strftime("%Y-%m-%dT%H:%M:%SZ"))
        if res.get("status") == "placed":   # Nov 11: durable row NOW; a resting bid outlives the run
            res["journaled"] = journal_order(r, res, is_rest=True, cid=(r.get("live") or {}).get("client_id"))
        name = BOOK_NAME.get(b, b)
        when = expire.astimezone(lm.ET).strftime("%I:%M %p ET")
        if res["status"] == "placed":
            got = res.get("filled_stake") or 0
            tg(f"{lane_tag(r)}RESTING BID {name}: {p.get('bet')} at {lm.american(c):+d} (= the alert's {int(af):+d} after fees), "
               f"${risk:,.2f}" + (f"; ${got:,.2f} filled right away" if got else "") + f". Cancels itself at {when}.\n"
               f"{p.get('sport')} {p.get('game')}\nSTOP on ntfy does NOT cancel it: cancel in the {name} app if needed.")
        elif res["status"] == "error":
            tg(f"{lane_tag(r)}RESTING BID ERROR {name}: {(p.get('bet') or '')[:60]}\n{res['reason'][:200]}\nCheck {name} before retrying.")
        if res["status"] == "refused":   # Oct 30: a clean refusal falls through to the next book (Novig first, else Kalshi)
            why_not.append(f"{name}: {res.get('reason')}")
            continue
        return res
    return {"status": "refused", "reason": "; ".join(why_not) or "no resting book"}


def sent_tokens(M, toks, days=None):
    """Which of these record tokens already appear in a sent report, in ONE bounded search per 20.

    The "token email is the record" pattern is how both fill reporters avoid reporting the same fill
    twice. Each of them used to run one UNBOUNDED gsearch_strict PER RECORD - up to 30 serial
    X-GM-RAW scans of the whole mailbox in novig_reports (67.4s) and one per resting order in
    kalshi_rest_reports. Same defect as read_manual and already_handled.

    FAILS CLOSED like gsearch_strict: a failed search or fetch RAISES, because a reporter that
    answers "not yet reported" when it cannot see would message Peter about the same fill again."""
    toks = sorted({t for t in toks if t})
    if not toks:
        return set()
    out, seen_uids = set(), set()
    for i in range(0, len(toks), 20):
        q = f"newer_than:{days or HANDLED_DAYS}d (" + " OR ".join(toks[i:i + 20]) + ")"
        with perf("sent_tokens: search"):
            typ, data = M.uid("SEARCH", "X-GM-RAW", '"' + q + '"')
        if typ != "OK":
            raise RuntimeError("Gmail search failed")
        # Nov 11: novig fill reports measured 160.8s with a 0.2s snapshot read, so the cost is here
        # - but whether it is the SEARCH or the per-message FETCH was unknown, and the two have
        # different fixes. Split and counted rather than guessed at; the message count says whether
        # the OR search is matching far more mail than the few small token emails it should.
        for uid in (data[0].split() if data and data[0] else []):
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            with perf("sent_tokens: fetch matched message", n=1):
                typ, d = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not d or not d[0]:
                raise RuntimeError("Gmail fetch failed")
            raw = d[0][1] if isinstance(d[0], tuple) and len(d[0]) > 1 else b""
            txt = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
            # not a bare substring test: a token must not be followed by another hex digit, so a
            # shorter token can never match inside a longer one. Real tokens are fixed-length
            # sha1 prefixes so this cannot bite today, but it is one line and removes the class.
            out.update(t for t in toks if re.search(re.escape(t) + r"(?![0-9a-fA-F])", txt))
    return out


def already_reported(M, toks, days=None):
    """Which fill-report tokens have already been sent. Registry first, Gmail for the rest.

    Nov 11: novig_reports measured 201.5s with a 0.4s snapshot read, so the cost is this lookup.
    The tokens are pure bookkeeping - "did I already tell Peter about this fill" - and belong in
    the store, not in a mailbox search.

    A token the store does not know is still checked in GMAIL rather than assumed unsent, because
    assuming unsent means messaging Peter about the same fill twice. Whatever Gmail then confirms
    is written back, so the store converges in a single run and later runs need no search at all.
    Fail-closed is unchanged: sent_tokens() still raises on a failed search or fetch."""
    toks = sorted({t for t in toks if t})
    if not toks:
        return set()
    hit = set()
    if registry.enabled():
        try:
            have = registry.token_set()
            hit = {t for t in toks if t in have}
        except Exception as ex:
            LOG.append(f"report-token store unreadable, using Gmail: {str(ex)[:50]}")
    rest = [t for t in toks if t not in hit]
    found = sent_tokens(M, rest, days=days) if rest else set()
    if found and registry.enabled():
        try:
            registry.put_tokens(found, outcome="reported")   # converge: next run needs no search
        except Exception:
            pass
    return hit | found


class ReportClaim:
    """Owns the "have I already told Peter about this fill" decision for one reporting pass.

    Nov 11 (Peter: "fix duplicate Novig fill notifications"): the old test was a Gmail search for
    the token email written AFTER the message went out. Gmail does not index a just-sent message
    before the next catch-up pass looks, so pass 2 saw nothing and re-sent everything - 27 fills
    delivered 70+ times in one afternoon, every repeat byte-identical.

    The claim is now an atomic registry WRITE taken BEFORE the send, so two overlapping passes
    cannot both win the same token. Gmail stays as the fallback for a store that cannot answer,
    searched once and lazily rather than per item.

    PARTIAL -> FULL is preserved untouched: the token carries status, filled_qty and filled_cost,
    so a 13,186-contract partial and the 44,000-contract fill that follows are different tokens
    and both report. Only a byte-identical repeat collides."""

    def __init__(self, M, toks, days=None):
        self.M, self.toks, self.days = M, list(toks), days
        self.reg = registry.enabled()
        self._gmail = None

    def _gmail_set(self):
        # fail-closed is unchanged: already_reported raises on a failed search rather than
        # answering "not yet reported", because that answer messages Peter about a fill twice.
        if self._gmail is None:
            self._gmail = already_reported(self.M, self.toks, days=self.days)
        return self._gmail

    def claim(self, tok):
        """True when THIS pass owns the send."""
        if self.reg:
            try:
                return registry.claim_token(tok)
            except Exception as ex:
                LOG.append(f"notify claim unavailable, using Gmail: {str(ex)[:50]}")
                self.reg = False   # one fallback for the rest of the pass, not one per item
        return tok not in self._gmail_set()

    def sent(self, tok):
        """Promote the claim to a completed send. The email remains the backup record."""
        if self.reg:
            try:
                registry.mark_handled([tok], "reported")
            except Exception as ex:
                LOG.append(f"notify mark failed: {str(ex)[:40]}")

    def failed(self, tok):
        """Drop the claim when the send did not go out, so the next pass retries immediately."""
        if self.reg:
            registry.release_token(tok)


def novig_reports():
    """Oct 28: the home runner writes each Novig order's result to snapshot/novig_orders.json; report each new or
    changed result to Telegram once (token email = the record, the same pattern as the watchdog). Counts only in the log."""
    with perf("novig snapshot read (private repo)"):
        recs = book_live.novig_results() if (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip() else []
    if not recs:
        return 0
    # Nov 11: decide WHICH records are even reportable before touching Gmail. The status filters
    # below are pure arithmetic on the snapshot, so running them first means a run with nothing
    # final to report opens no IMAP connection and issues no search at all - and that is the
    # common case, because the home runner re-reads every 5 minutes while most orders sit
    # unchanged. Measured at 73s and 119s in the two passes of run 43070374073, AFTER the search
    # batching, so the remaining cost was the connection and the search themselves.
    def _final(x):
        st = str(x.get("status") or "?").upper()
        fq = int(x.get("filled_qty") or 0)
        if st in ("PENDING", "SENT", "UNKNOWN") and not fq:
            return False
        if st == "FILLED" and not fq:
            return False
        return True
    if not any(_final(x) for x in recs[-30:]):
        print("novig fill reports: nothing final to report (no Gmail connection opened)")
        return 0
    n = 0
    M = imap_open()
    try:
        # Nov 11: this ran ONE UNBOUNDED gsearch_strict PER RECORD - up to 30 serial X-GM-RAW
        # searches over the whole mailbox, measured at 67.4s. Same shape as the read_manual and
        # already_handled defects: a per-item Gmail search with no date bound. The tokens for every
        # record are now resolved in one bounded OR search before the loop, which then only looks
        # the answer up. Report-or-not decisions are unchanged; a token already sent still suppresses.
        # FAILS CLOSED as before: the search raises on failure rather than reporting a fill twice.
        claimer = ReportClaim(M, ["xnvr" + hashlib.sha1(
            f"{x.get('client_id')}|{str(x.get('status') or '?').upper()}|"
            f"{int(x.get('filled_qty') or 0)}|{x.get('filled_cost')}".encode()).hexdigest()[:12]
            for x in recs[-30:]])
        for x in recs[-30:]:
            st = str(x.get("status") or "?").upper()
            if st in ("PENDING", "SENT", "UNKNOWN") and not int(x.get("filled_qty") or 0):
                continue   # not final yet: report when it settles (the home PC re-reads every 5 min)
            if st == "FILLED" and not int(x.get("filled_qty") or 0):
                continue   # status says filled but the amount isn't confirmed yet (old-format record): never say "no fill"
            c, q, fq = lm.num(x.get("price")) or 0, int(x.get("qty") or 0), int(x.get("filled_qty") or 0)
            cost = x.get("filled_cost")
            tok = "xnvr" + hashlib.sha1(f"{x.get('client_id')}|{st}|{fq}|{cost}".encode()).hexdigest()[:12]
            if not claimer.claim(tok):
                continue   # already sent, or another overlapping pass is sending it right now
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
            try:
                tg(msg)
            except Exception as ex:
                # nothing reached him: drop the claim so the next pass retries at once instead
                # of waiting out the stale window.
                claimer.failed(tok)
                LOG.append(f"novig report send failed: {str(ex)[:50]}")
                continue
            # Delivered. Promote the claim BEFORE the two best-effort copies below: the old code
            # wrote the record only when send() succeeded, so a single mail failure re-sent that
            # fill on every pass. Telegram delivery is the criterion; a failed ntfy or email copy
            # must never re-send BOTH.
            claimer.sent(tok)
            try:
                # Nov 11: same report on ntfy (Kalshi already does this), one claim covers both.
                push(head.title(), msg, mirror=False)
            except Exception as ex:
                LOG.append(f"novig report ntfy copy failed: {str(ex)[:40]}")
            try:
                send(f"Bets Novig order: {head.replace('NOVIG ', '')}", msg + f"\n\n{tok}")
            except Exception:
                pass   # backup record only; the registry claim above is the authority
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
        # Nov 11: this re-scanned "Bets LIVE:" with its own RFC822 fetch per email - the identical
        # work bot_orders() had already done moments earlier in the same run, measured at 68.6s.
        # It now reuses those parsed rows. The 2-day window is preserved by filtering on
        # decided_utc, so the set of resting orders checked is the same as before even though
        # bot_orders() reads a 4-day window. An empty cache (bot_orders not run, or unreadable)
        # falls back to the original scan, so this can only be faster, never blinder.
        cut = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        rests = {}
        src_rows, reused = list(LEDGER_ROWS), bool(LEDGER_ROWS)
        if not reused:
            since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%d-%b-%Y")
            typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", since)
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
                src_rows.extend(rows)
        for row in src_rows:
            lo = row.get("live_rest") or {}
            if lo.get("book") == "kalshi" and lo.get("status") == "placed" and lo.get("order_id"):
                if reused and str(row.get("decided_utc") or "")[:10] < cut:
                    continue   # keep the original 2-day window
                rests[str(lo["order_id"])] = (row, lo)
        print(f"kalshi resting check: {len(rests)} order(s), rows {'reused' if reused else 'rescanned'}")
        k_res = {}
        for oid in rests:
            try:
                k_res[oid] = (book_live._k_call("GET", f"/portfolio/orders/{oid}")[1].get("order") or {})
            except Exception:
                k_res[oid] = None
        k_toks = {}
        for oid, o in k_res.items():
            if not o:
                continue
            fc = lm.num(o.get("fill_count_fp")) or lm.num(o.get("fill_count")) or \
                ((lm.num(o.get("taker_fill_count")) or 0) + (lm.num(o.get("maker_fill_count")) or 0))
            if fc:
                k_toks[oid] = "xkrf" + hashlib.sha1(f"{oid}|{fc}".encode()).hexdigest()[:12]
        already = already_reported(M, list(k_toks.values()), days=2)
        for oid, (row, lo) in rests.items():
            try:
                st, d = (0, {"order": k_res.get(oid) or {}})
            except Exception:
                continue
            o = d.get("order") or {}
            fc = lm.num(o.get("fill_count_fp")) or lm.num(o.get("fill_count")) or \
                ((lm.num(o.get("taker_fill_count")) or 0) + (lm.num(o.get("maker_fill_count")) or 0))
            if not fc:
                continue
            tok = k_toks.get(oid) or ("xkrf" + hashlib.sha1(f"{oid}|{fc}".encode()).hexdigest()[:12])
            if tok in already:
                continue   # already reported for this fill amount (one batched search above)
            rem = lm.num(o.get("remaining_count_fp")) or lm.num(o.get("remaining_count")) or 0
            head = "KALSHI RESTING BID FILLED" if not rem else "KALSHI RESTING BID PARTIAL FILL"
            msg = (f"{head}: {row.get('key', '').replace('|', ' ')}\n{fc:g} contracts at the {lo.get('limit')} limit"
                   + (f"; {rem:g} still resting until {lo.get('expires_utc')}" if rem else ""))
            push(head.title(), msg, mirror=False)
            tg(msg)
            try:
                send(f"Bets Kalshi order: {head.replace('KALSHI ', '')}", msg + f"\n\n{tok}")
                # Nov 11: the token ALSO goes to the store, so the next run answers "already
                # reported" without a Gmail search. The email stays the backup record.
                if registry.enabled():
                    registry.put_tokens([tok], outcome="reported")
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
            # Nov 11 (Peter, check 10): every venue CONSIDERED for the live order, with its raw and
            # after-fee price, the line, the depth at the threshold, and the fee basis actually
            # applied - so the routing decision can be audited after the fact rather than inferred
            # from the winner alone. Logging only; nothing here feeds a decision.
            "venues_considered": [{"book": c.get("book"), "after_fee": c.get("am"), "screen": c.get("shown"),
                                   "line": c.get("line"), "depth_at_thr": c.get("avail"), "thr": c.get("thr"),
                                   "tolerance_cents": (PX_TOL_CENTS if c.get("book") in TOL_BOOKS else 0),
                                   "maker": False}
                                  for c in (r.get("lcs") or [])],
            "fee_basis": {"model": FEE_MODEL, "taker": True,
                          "win_fee": WIN_FEE.get(lv.get("book") or r.get("book")),
                          "tol_books": list(TOL_BOOKS), "tol_cents": PX_TOL_CENTS},
            # Nov 11 (check 8): what the order-time re-read of the chosen venue found, or why it refused
            "revalidated": lv.get("reval"),
            "journaled": (lv.get("order") or {}).get("journaled"),
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


JOURNAL = {"sent": 0, "failed": 0, "latch": None}
INTENT = {"open": {}}   # client_id -> row, for intents with no confirmed order. Non-empty = refuse.


def journal_intent(r, book, asked):
    """WRITE-AHEAD order record (Peter, Nov 11). The smallest fix that gives ProphetX durable
    attribution, given that the venue cannot provide it.

    MEASURED (px_live, Nov 10, 100 real trades): a ProphetX trade carries fee, id, matched_at,
    order_id, price, profit, quantity, status, strike, strike_id, winning_status. external_id is
    NOT among them, so a prefixed external_id is invisible at the point attribution happens -
    matching a settled trade back to "the bot placed this". A venue-recoverable bot id is therefore
    not available, and guessing at an undocumented orders endpoint is the Polymarket cancel mistake.

    So the record stops being a CONSEQUENCE of the order and becomes a PRECONDITION of it: this row
    is written BEFORE submitting, and the order is only submitted if the write succeeded. The
    failure mode inverts. Before: order placed, record lost, exposure untracked and unbounded across
    runs. Now: record fails -> no order at all -> nothing to track.

    If the run dies between this write and the submit, the registry already holds a row saying an
    order of this size MAY exist. bot_orders() counts it, so the next run cannot exceed its limits;
    its play key reaches LIVEKEYS, so the next run cannot repeat the bet; and because no confirmed
    row ever follows, the client_id stays in INTENT["open"] and live_guards() refuses every further
    live order until it is reconciled. Uncertain placement fails closed rather than being estimated.

    Returns (ok, client_id). Zero paid credits: Gmail SMTP only."""
    cid = uuid.uuid4().hex[:16]
    try:
        p = r.get("play") or {}
        row = {"key": p.get("play_key") or derive_key(p) or "", "source": p.get("source"),
               "intent": True, "client_id": cid,
               "decided_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "live_order": {"status": "placed", "order_id": "intent-" + cid, "book": book,
                              "asked_stake": round(float(asked or 0), 2), "filled_stake": None,
                              "client_id": cid, "intent": True}}
        send(f"{INTENT_SUBJECT_PREFIX} {book} {cid}",
             "ORDER INTENT - written BEFORE the order is submitted. The order is submitted only if this\n"
             "row can be READ BACK from the registry, so a failure here means NO order was placed.\n"
             "If no confirmed row follows this client id, an order MAY exist at the venue: the daily stop\n"
             "counts this row, duplicate blocking holds this play, and live orders refuse until it is\n"
             "reconciled.\n\n"
             "TO CLEAR IT, once ProphetX My Trades shows whether the order exists, send an email to this\n"
             "address whose SUBJECT LINE begins with the two words INTENT / CLEARED (no slash) followed by\n"
             "the client id shown in this subject. Nothing this system sends ever carries that subject, so\n"
             "it cannot clear itself - which an earlier version could, because the clearing token sat in\n"
             "this very body and the search read bodies. The clearance is subject-only and manual.\n"
             "Counts only.\n\n"
             "LEDGER (machine-readable, one row per play; latency = decision time minus first alert time)\n"
             + json.dumps([row]))
        _ok, _where = intent_verified(cid, row)   # SMTP success is not storage - read it back or place nothing
        if not _ok:
            try:
                tg(f"ORDER INTENT UNREADABLE: the pre-order record for {book} was sent but could not be "
                   f"read back from the registry (client id {cid}).\nNO ORDER WAS PLACED. If that row did "
                   f"store, it will hold live orders until you clear it - subject INTENT CLEARED {cid}.")
            except Exception:
                pass
            return False, None
        # intent_verified() wrote the row to the store and read it back; if it had to fall back to
        # Gmail the store may be missing this intent, so its completeness claim is dropped and the
        # next run reads Gmail, which has the row from the send() above.
        if registry.enabled() and _where != "private store":
            try:
                registry.invalidate()
            except Exception:
                pass
        LOG.append(f"intent {cid} verified from {_where}")
        return True, cid
    except Exception as ex:
        try:
            tg(f"ORDER INTENT FAILED: could not store the pre-order record for {book} "
               f"({str(ex)[:120]}).\nNO ORDER WAS PLACED - the run refused rather than bet without a "
               f"durable record. Nothing is untracked.")
        except Exception:
            pass
        return False, None


def journal_latch_why():
    """Nov 11 (Peter): "if journal persistence fails, prevent further orders until reconciliation
    establishes the actual exposure."

    A failed durable row means this run holds an order the registry may not know about, so the
    bot's own exposure is UNKNOWN - and unknown exposure is the one condition this system never
    places money under (the same rule as an unreadable registry or unreadable board exposure).
    The latch blocks every further order and resting bid for the rest of the run.

    Scope, stated plainly: the latch is per-run, which is the whole window it can act in. It is
    cleared by the next run, whose bot_orders() re-reads the Gmail registry and rebuilds exposure
    from the venue ledgers - that read IS the reconciliation. If the end-of-run ledger did send,
    the order is in the registry and nothing was lost; if the run was killed first, the order is
    missing and the latch is what stopped the run adding more to an exposure it could not count."""
    return JOURNAL["latch"]


def journal_order(r, lo, is_rest=False, cid=None):
    """Nov 11 (Peter, crash-safe order logging). Write ONE durable registry row the moment an order
    is placed, instead of only at the end of the run.

    The bot-order registry is the LEDGER block inside the run's 'Bets LIVE:' email, and that email
    is sent when the run finishes. An order placed at minute 8 of a 30-minute run that is then
    killed - which the Nov 10 timeout did, mid-pass - never reaches the registry at all. Two
    consequences, both real money: today_result() cannot attribute the order, so the DAILY STOP
    UNDERCOUNTS; and the play key never reaches LIVEKEYS, so the next run can place the SAME bet
    again. CLAUDE.md records this as a correctness risk rather than a lost run.

    The row is written in the EXACT shape bot_orders() already parses - subject prefixed
    'Bets LIVE:' plus a 'LEDGER (machine-readable' JSON array - so there is no second registry and
    no second parser (the ledger is extracted with rfind + raw_decode; do not invent another way).
    bot_orders() now counts each order id once, so this row and the end-of-run row for the same
    order cannot double-count its money.

    Best-effort by design: an order that ALREADY EXISTS at the venue must never be undone or
    retried because logging failed, so this never raises into the order path. A failure is LOUD -
    silence would restore exactly the defect this closes."""
    oid, book = lo.get("order_id"), (lo.get("book") or "prophetx")
    try:
        p = r.get("play") or {}
        row = {"key": p.get("play_key") or derive_key(p) or "",
               "source": p.get("source"), "journal": True,
               "decided_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               ("live_rest" if is_rest else "live_order"): {
                   "status": "placed", "order_id": oid, "book": book,
                   "asked_stake": lo.get("asked_stake") if lo.get("asked_stake") is not None else lo.get("asked"),
                   "filled_stake": lo.get("filled_stake"), "avg_price": lo.get("avg_price"),
                   "limit": lo.get("limit"), "resting": bool(is_rest or lo.get("resting")),
                   # Nov 11: resolves the write-ahead intent row and makes the money count once
                   "client_id": cid or (r.get("live") or {}).get("client_id"), "intent": False}}
        send(f"Bets LIVE: order journal {book} {oid}",
             "ORDER JOURNAL - one durable registry row, written the moment this order was placed, so a run\n"
             "killed before its end-of-run ledger cannot lose this order from the registry (daily-stop\n"
             "attribution and duplicate blocking both read that registry). The end-of-run ledger repeats\n"
             "this order; bot_orders() counts each order id once. Counts only - no amounts beyond the stake\n"
             "the registry already needs.\n\n"
             "LEDGER (machine-readable, one row per play; latency = decision time minus first alert time)\n"
             + json.dumps([row]))
        # Nov 11: the same row into the private store. If that write fails the store is no longer
        # known-complete, so its completeness marker is cleared and the next run reads Gmail, which
        # still has this row from the send() above. A dropped store write therefore costs speed, not
        # correctness. Never raises into the order path: the order already exists at the venue.
        if registry.enabled():
            try:
                if not registry.put_rows([row]):
                    registry.invalidate()
            except Exception as ex2:
                LOG.append(f"registry order write failed: {str(ex2)[:50]}")
                try:
                    registry.invalidate()
                except Exception:
                    pass
        JOURNAL["sent"] += 1
        return True
    except Exception as ex:
        JOURNAL["failed"] += 1
        # LATCH: no further orders this run. Exposure is now unknown, and unknown exposure never places.
        JOURNAL["latch"] = (f"{book} order {oid} is placed but its durable registry row did not send "
                            f"({str(ex)[:80]})")
        try:   # LOUD: without this row a kill loses the order from the registry
            tg(f"ORDER JOURNAL FAILED: {book} order {oid} is PLACED but its durable registry row did not "
               f"send ({str(ex)[:120]}).\nIf this run is killed before its ledger email, the daily stop will "
               f"undercount this order and another lane could repeat the bet. Check the ledger email.")
        except Exception:
            pass
        return False


def main():
    now = datetime.now(timezone.utc)
    # Nov 11: the PERF block accounted for 88s of a 982s run - 894 seconds were outside all seven
    # instrumentation points, which is 11x the largest thing being measured. These brackets cover
    # main()'s own phases so the dark time has somewhere to land. Measurement only, never a gate.
    with perf("imap open"):
        M = imap_open()
    with perf("read verdicts (Gmail)"):
        plays = read_verdicts(M) if SOURCE in ("muse", "both") else []
    try:
        with perf("read manual notes (Gmail)"):
            read_manual(M)
    except Exception:
        LOG.append("manual-bet notes unreadable")
    with perf("rule_plays"):
        rplays = rule_plays(now) if SOURCE in ("rules", "both") else []
    with perf("board_plays"):
        bplays = board_plays(now)   # Nov 3: Lane 3 (board NBA totals)
    try:   # Nov 11: R1 live lane (non-Top-25 college, read from alerts.json; muted alerts included). Never lets R1 stop a run.
        with perf("r1_plays"):
            r1plays = r1_plays(now)
    except Exception as ex:
        LOG.append(f"r1 unavailable: {str(ex)[:60]}")
        r1plays = []
    try:   # Nov 4: Lane 2 (Muse registration 3:48 PM) - dry run only, no live path exists for these plays
        with perf("lane 2 candidates"):
            import clv_ledger as _cl
            l2plays = [dict(p, play_key="lane2|" + (derive_key(p) or ""))   # Nov 4 fix: Lane 2 rows need their own play_key
                       for p in lane2.plays(now, load_feed(), lane2.markets(_cl, now)) if derive_key(p)]
    except Exception as ex:
        LOG.append(f"lane 2 unavailable: {str(ex)[:60]}")
        l2plays = []
    # one Gmail search PER CANDIDATE play - with dozens of candidates across five lanes this is the
    # prime suspect for the unmeasured time, so it is counted and the call count is printed
    _cand = plays + rplays + bplays + r1plays + l2plays
    with perf("handled_pids (one Gmail search)", n=len(_cand)):
        _seen = handled_pids(M, _cand)
    SEEN["tok"] = _seen   # live_play_alert() reads the xrty tokens from here to suppress re-alerts
    new = [p for p in _cand if not already_handled(M, p, _seen)]
    with perf("imap close"):
        imap_close(M)
    feed = load_feed()
    # wake time: this run's start vs the newest SENT alert (Oct 26; counts/seconds only in the public log)
    sent_ts = [iso_t(a.get("alert_utc")) for a in feed if a.get("sent_to_phone") and iso_t(a.get("alert_utc"))]
    newest = max(sent_ts) if sent_ts else None
    wake_s = (now - newest).total_seconds() if newest and now - newest < timedelta(minutes=30) else None
    trig = os.environ.get("GITHUB_EVENT_NAME", "local")
    # Before anything else this run: pull any Polymarket US resting bid that has reached T-30.
    # It goes here, ahead of the new-order work, because a bid past T-30 is live money sitting on
    # the book after the point Peter said it must be off - that takes priority over placing more.
    # Its own try/except is inside the function; a sweep failure must not stop the run.
    try:
        with perf("pmus rest sweep (T-30 money off the book)"):
            pmus_rest_sweep(now)
    except Exception as ex:
        print(f"PM US sweep call failed: {str(ex)[:60]}")
    print(f"Verdict plays seen (2 days): {len(plays)}; coded-rule alerts: {len(rplays)}; new: {len(new)}")
    if wake_s is not None:
        print(f"Wake: run started {wake_s:.0f}s after the newest sent alert (trigger: {trig})")
    if not new:
        # Nov 11: this early return skipped the whole report block, so a run with nothing to do
        # printed NO PERF and NO registry line - and those are exactly the cheap, frequent runs
        # whose timings are most readable, since nothing else happens in them. The 15:50 run took
        # 4.5 minutes to conclude "new: 0" and said nothing about where that went. Counts and
        # seconds only, safe for the public log.
        # nothing is waiting on this run, so cost here delays no order. The watchdog MUST still run
        # on this path: it flags a qualifying play with no Muse verdict, and that is precisely the
        # case where the play was already handled and `new` is empty. Moving it off the pre-order
        # path must not mean skipping it on the common run.
        watchdog_once(now, plays, rplays, feed)
        fill_reports()
        print(perf_report())
        try:
            import registry as _rg
            print(_rg.selftest())
        except Exception as _ex:
            print(f"registry selftest unavailable: {str(_ex)[:60]}")
        return
    lo = int(now.timestamp() * 1000)
    hi = int((now + timedelta(days=3)).timestamp() * 1000)
    try:
        with perf("novig catalog"):
            evs, mks = bc.novig_catalog(lo, hi)
    except Exception:
        evs, mks = [], []
    evs_by = {e["eventId"]: e for e in evs}
    mks_by_event = {}
    for mk in mks:
        mks_by_event.setdefault(mk.get("eventId"), []).append(mk)
    MD["c"].clear(); MD["hit"] = MD["miss"] = 0   # one cache per run, never across runs
    MKT["evs"], MKT["mks"] = evs_by, mks_by_event   # Nov 11: revalidate() re-reads Novig through this map
    with perf("positions read (first attempt)"), ThreadPoolExecutor(max_workers=4) as tp:   # Oct 31: all 4 position reads at the same time
        f_nv = tp.submit(novig_positions)
        f_h = {b: tp.submit(fn) for b, fn in (("kalshi", positions.kalshi_positions), ("prophetx", positions.px_positions),
                                              ("polymarket_us", positions.pmus_positions))}
        pos = f_nv.result()
        held = {b: f.result() for b, f in f_h.items()}   # Kalshi / ProphetX / Polymarket US open positions (read-only)
    if pos is None or any(v is None for v in held.values()):   # one immediate retry before holding anything
        # Nov 11: the retry used to re-read each failed venue SERIALLY, so three unreadable books
        # cost the sum of their latencies on top of the 5s settle. The first attempt has always
        # been parallel; the retry now matches it. Same reads, same fail-closed outcome - a venue
        # still unreadable after this is still "blind" and still places nothing.
        with perf("positions retry (after 5s)"):
            time.sleep(5)
            retry = {"kalshi": positions.kalshi_positions, "prophetx": positions.px_positions,
                     "polymarket_us": positions.pmus_positions}
            need = [b for b, v in held.items() if v is None]
            with ThreadPoolExecutor(max_workers=4) as tp:
                f_nv2 = tp.submit(novig_positions) if pos is None else None
                f_r = {b: tp.submit(retry[b]) for b in need}
                if f_nv2 is not None:
                    pos = f_nv2.result()
                for b, f in f_r.items():
                    held[b] = f.result()
    blind = (["Novig"] if pos is None else []) + [BOOK_NAME[b] for b, v in held.items() if v is None]
    # Oct 29 (Muse): when a book's positions can't be read and a LIVE-eligible play (phase-1, Muse AGREE) is waiting,
    # re-read every 60 s inside this run (up to 4 min - the runs queue behind each other, so not longer), and push an
    # escalation at ~3 min naming the play and the book so it can be placed by hand while the number is live.
    # Unreadable still means no order (fail closed).
    if blind:
        # Nov 11 (Peter, "GO. Implement the blind-loop replacement"): the 4-minute in-run polling
        # loop is GONE. It slept 60s up to four times hoping a venue recovered, and only pushed the
        # escalation at the ~3-minute mark - so it cost up to 240s PER PASS (measured at 138s/175s
        # in run 43070374073) and told Peter last.
        #
        # Replaced by: one parallel first attempt, one parallel retry after 5s (both above), then
        # stop. Healthy venues keep being evaluated, every play is still routed and alerted, and the
        # escalation fires IMMEDIATELY - three minutes earlier than before, which is three more
        # minutes to place by hand while the number is live.
        #
        # EXPOSURE IS NEVER ASSUMED ZERO. An unreadable venue means total exposure is unverifiable,
        # and unverifiable exposure blocks EVERY new live order for the run (live_guards + the
        # px_live/book_live exposure setters below), whatever the other three venues say. The
        # trade, accepted knowingly: a venue that blips and recovers within 60-240s used to let
        # this run place its play and now does not - it waits for the next scheduled run, which is
        # minutes away. Nothing is placed blind either way.
        why = "; ".join(f"{BOOK_NAME[b]}: {positions.WHY.get(b, '?')}" for b, v in held.items() if v is None)
        if pos is None:
            why += ("; " if why else "") + f"Novig: {(_NVERR.get('why') or '?').strip(' |')[:80]}"
        p1 = []
        for p in new:
            e1 = feed_entry(p, load_feed()) if p.get("source") != "rules" else None
            if e1 and agree_rules.phase1(e1, True)[0]:
                p1.append(p)
        # Nov 11 (Peter: "if it happens 5 times in a row then telegram me"): a venue that blips for
        # one run and recovers is noise - the run placed nothing, which is the safe outcome, and
        # the next run rechecks minutes later. A venue that stays blind IS worth a message. So the
        # summary is held until BLIND_STREAK_AT consecutive runs, then repeats every that many.
        #
        # This silences NOTHING that matters on its own: when a live-eligible play is held, the
        # per-play HELD path below pushes it immediately, deduped on held_tok, and this summary is
        # sent too. Quiet only ever means "blind, and nothing was waiting to place".
        #
        # Fail-safe: an uncountable streak (store unwritable) NOTIFIES. Going quiet because the
        # bookkeeping broke is the one outcome worth avoiding.
        streak = None
        try:
            streak = registry.bump_streak("positions_blind") if registry.enabled() else None
        except Exception as ex:
            LOG.append(f"blind streak uncountable, notifying: {str(ex)[:40]}")
        if p1 or streak is None or streak % BLIND_STREAK_AT == 0:
            push(f"POSITIONS UNREADABLE: {', '.join(blind)}",
                 f"Can't read your open bets on {', '.join(blind)} ({why[:160]}).\n"
                 + (f"{streak} runs in a row.\n" if streak and streak >= BLIND_STREAK_AT else "")
                 + f"Exposure cannot be verified, so NO new live orders this run on ANY venue"
                 + (f"; {len(p1)} live-eligible play(s) held - place by hand if you want them now."
                    if p1 else ". No live-eligible play is waiting.")
                 + "\nThe next scheduled run rechecks normally.")
        else:
            print(f"positions blind, run {streak} of {BLIND_STREAK_AT} - no push yet, nothing held")
        # No per-play push here: the per-play HELD path further down already sends one, deduped on
        # held_tok so it cannot repeat every run. Pushing again from here would double-notify, and
        # "prevent duplicate phone notifications for the same event" is a standing rule.
        print(f"positions blind: {', '.join(blind)} - exposure unverifiable, no live orders this run; "
              f"{len(p1)} live-eligible play(s) held")   # counts only
    elif registry.enabled():
        registry.reset_streak("positions_blind")   # every venue readable: the streak is over
    if px_live.LIVE and new:
        live_guards()   # Oct 30: load the ledger registry FIRST, so LIVEKEYS blocks a second live order on a play
    # Nov 11 (Peter, "finish this"): PARALLEL PROBE PREFETCH. probe alert line measured 107.2s
    # across 21 plays - 5.1s each - and is the largest item left on the critical path now that the
    # registry read is 6s and the blind positions loop is gone.
    #
    # Pruning probes was proven UNSAFE earlier today (half_point 0.01427 -> 0.01526 flips the pick
    # from 226.5 to 227.5), so nothing is removed and no price is recomputed. Instead evaluate() is
    # run once per play CONCURRENTLY, purely to warm the per-run MD cache, and the real serial loop
    # below then runs unchanged against cache hits.
    #
    # WHY A PREFETCH AND NOT A PARALLEL MAIN LOOP: the serial loop's ORDER carries "first side
    # stays" (taken_now) and LIVEKEYS sequencing, so reordering it would change which side of a
    # game wins a conflict. The loop is left exactly as it was.
    #
    # SAFE BECAUSE: evaluate() has no side effects beyond MD and PERF (asserted by test); taken is
    # passed as None so not one Gmail conflict search runs here; every result is DISCARDED and only
    # the cache survives; and MD is already bypassed at order time, so order pricing still comes
    # from a fresh venue read. ProphetX is unaffected either way - _PX_PACE holds a global lock at
    # 1 request/1.1s across parallel checks, which also makes PX the floor this cannot beat.
    if len(new) > 1:
        def _warm(p):
            try:
                evaluate(p, now, evs_by, mks_by_event, pos, None, held)
            except Exception:
                pass   # the serial pass handles real failures; this only warms the cache
        with perf("probe prefetch (parallel, cache warm)", n=len(new)), \
                ThreadPoolExecutor(max_workers=PREFETCH_WORKERS) as tp:
            list(tp.map(_warm, new))
    results, taken_now = [], set()
    M2 = imap_open()

    # Nov 11: taken() ran ONE UNBOUNDED X-GM-RAW search PER PLAY - the fourth instance of the
    # pattern already fixed in read_manual, already_handled and both fill reporters. evaluate()
    # calls it exactly once per play, with opposite_key(p), so every token it will ever ask for is
    # known up front and is resolved in ONE bounded batched search here.
    #
    # Bounded to HANDLED_DAYS, the same window the dedupe and the order registry use: a side taken
    # inside the period that can still matter is found, and games here start within hours of an
    # alert.
    _wp_ask = {wp(ok) for p in new if (ok := opposite_key(p))}
    _wp_from_store = False
    if registry.enabled() and _wp_ask:
        try:
            if registry.tokens_complete():
                _have = registry.token_set()
                _wp_hit, _wp_from_store = {t for t in _wp_ask if t in _have}, True
        except Exception as ex:
            LOG.append(f"token store unreadable for taken(), using Gmail: {str(ex)[:50]}")
    if not _wp_from_store:
        with perf("taken(): opposite-side check (one batched search)", n=len(_wp_ask), rollup=True):
            _wp_hit = sent_tokens(M2, sorted(_wp_ask), days=HANDLED_DAYS) if _wp_ask else set()

    def taken(k):   # this run, or any earlier WOULD PLACE / PLACED entry
        # Nov 8: strict, for the same reason as already_handled. This is "first side stays": a
        # failed search returning [] reads as "the side is free" and the bot takes the opposite
        # side of a position it already holds. Raise rather than guess - sent_tokens() raises on a
        # failed search or fetch, exactly as gsearch_strict did.
        if k in taken_now:
            return True
        tok = wp(k)
        if tok in _wp_ask:
            return tok in _wp_hit      # answered by the batched search above
        # a key the precompute did not cover must NEVER fall through as "free": ask for it.
        return bool(gsearch_strict(M2, f"newer_than:{HANDLED_DAYS}d {tok}"))
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
            with perf("evaluate (per play)", rollup=True):
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
            elif p.get("source") == "r1":   # R1 lane: its own live decision (never the phase-1 filter), own $200 unit and daily limit
                r["entry"] = ent = p.get("r1_entry") or {}
                lk = derive_key(p) or p["play_key"]
                why = [] if R1_LIVE else ["R1 lane not switched on (EXEC_R1_LIVE)"]
                if lk in MANUAL_HELD:
                    why.append(f"{MANUAL_HELD[lk]} with Peter's manual bet (Bets manual note)")
                if lk in LIVEKEYS or any(same_bet(lk, k) for k in LIVEKEYS):
                    why.append("a live order or resting bid was already sent for this bet (another lane)")
                if any(opp_bet(lk, k) for k in LIVEKEYS):
                    why.append("CONFLICT: the other side of this game was already bet (first side stays)")
                if not why and r["verdict"] == "WOULD PLACE" and r.get("lc"):
                    lc = r["lc"]
                    lr, lw = live_stake(lc["shown"], R1_UNIT)   # $200 to win, never Lane 1's $300
                    g_ok, g_why = r1_gate(lr, lk)
                    if not g_ok:
                        why.append(g_why)
                if not why and r["verdict"] == "WOULD PLACE" and r.get("lc"):
                    r["live"] = {"go": True, "book": lc["book"], "risk": lr, "to_win": lw, "am": lc["am"], "shown": lc["shown"],
                                 "line": lc["line"], "partial": lc["avail"] < lr, "px": lc, "ids": lc.get("ids") or {},
                                 "nfl": False, "lane": "r1", "unit": R1_UNIT}
                elif not why:
                    r["live"] = {"go": False, "lane": "r1", "why": ["no live book has the alert number or better"
                                                                    if r["verdict"] == "WOULD PLACE" else (r.get("reason") or "skipped")]}
                else:
                    r["live"] = {"go": False, "lane": "r1", "why": why}
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
                try:   # Nov 11 (Peter): EVERY live play alerts, all three lanes, before the order
                    live_play_alert(r)
                except Exception as ex:
                    print(f"live play alert failed: {str(ex)[:60]}")   # never block the order
                with perf("live_order (revalidate + intent + submit)"):
                    r["live"]["order"] = live_order(r)
                with perf("live_remainder (next venue)"):
                    r["live"]["more"] = live_remainder(r)   # Oct 28: $200 total per play across venues
                LIVEKEYS.add(derive_key(p) or p["play_key"])
            if rest_wanted(r):   # Oct 28 (Peter): nothing filled at the number -> rest a bid until 30 min before the start
                with perf("rest_bid"):
                    r["live"]["rest"] = rest_bid(r)
                LIVEKEYS.add(derive_key(p) or p["play_key"])
            results.append(r)
            if (r["verdict"] == "WOULD PLACE" or ((r.get("live") or {}).get("rest") or {}).get("status") == "placed") \
                    and derive_key(p) and p.get("source") not in ("rules", "board", "r1", "lane2"):
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
    body += [lane_report(results), ""]   # Nov 11: per-lane counts and exposure, Board v3 and R1 separate
    try:
        # Nov 11: teach the store this run's tokens BEFORE the email goes out, so a crash between
        # the two cannot leave the registry claiming completeness while missing them. A failed
        # write clears the token marker, and the next run reads Gmail - which has them from the
        # email below - rather than trusting an incomplete store.
        try:
            if registry.enabled() and not registry.put_tokens(run_tokens(results)):
                registry.invalidate_tokens()
        except Exception as _ex:
            LOG.append(f"token write failed: {str(_ex)[:50]}")
            try:
                registry.invalidate_tokens()
            except Exception:
                pass
        # AFTER every order, never before: these gate nothing (Nov 11). The watchdog moved here
        # from the pre-order path for the same reason - its own email says "This blocks nothing -
        # Muse is a veto, so only a DISAGREE stops a play", and read_verdicts() already loaded
        # those vetoes before any evaluation. Measured at 4.8-24.1s.
        watchdog_once(now, plays, rplays, feed)
        fill_reports()
        body += [perf_report(), ""]   # Nov 11: where the run's time actually went
        print(perf_report())          # and in the public log, counts/seconds only
        # Nov 11 (Peter, "b2"): the private-GitHub store proves itself against the real API while
        # bot_orders() is still reading Gmail, so a broken transport cannot stop him betting. Its
        # read time is the number to compare with the 79s Gmail registry read. Counts only, no
        # amounts: safe for the public log. Never allowed to affect the run.
        try:
            import registry as _rg
            _st = _rg.selftest()
            body += [_st, ""]
            print(_st)
        except Exception as _ex:
            LOG.append(f"registry selftest unavailable: {str(_ex)[:60]}")
    except Exception:
        pass
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

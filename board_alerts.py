#!/usr/bin/env python3
"""
BETS BOARD PHONE ALERTS (Nov 2, 2026; Peter 18:35: "yes" to a phone alert when a new PLAY call shows on the board).
Runs inside the bets-board job, right after each rebuild's inputs land. Sends one ntfy push the first time a row is called
PLAY while its money is still there (same rules as the board: board_build.score). Already-sent rows are remembered in
lanes/board_alerts.json. Paper signal; check the price.

Each record holds (Peter, Nov 6 - the file used to store only a timestamp under an opaque key, so the Polymarket rows
were unreadable: their key carries a pm_market_id and nothing else, while the docstring claimed "game, side and time
only" and in fact stored none of the game or the side):
  when, tag, game, league, market, side, line, price, price_american, best_price, best_price_american,
  best_price_book, book, alerted_utc, market_id
market_id is the book's own identifier (Kalshi market_ticker / Polymarket pm_market_id), kept so a row can always be
traced to the exact market even if the naming changes. Still public data only - no stakes, balances or keys.

Records written before Nov 6 hold a bare timestamp string. They are migrated in place ONLY where the row can be
reconstructed exactly: the alert is re-found in the liquidity feed by (key, alerted_utc), the same pair the record key
is built from, so a hit is an identity match rather than a guess. A record that cannot be re-found keeps its timestamp
under "when" and gains no invented fields.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
import urllib.request

import board_build as bb

FILE = "lanes/board_alerts.json"
TOPIC = (os.environ.get("NTFY_TOPIC") or "").strip()
TAGS = [t.strip().upper() for t in (os.environ.get("BOARD_ALERT_TAGS") or "PLAY").split(",") if t.strip()]
# Nov 4 (Peter via Muse, 7:42 AM): board PLAY pushes OFF - Lane 3 is off, so every board call is paper. Rows are still
# recorded as sent (so turning it back on never floods old calls). BOARD_PUSH=on brings the push back.
PUSH = (os.environ.get("BOARD_PUSH") or "off").strip().lower() == "on"
# Nov 8 (Peter, via Muse): board PLAY calls also go to TELEGRAM. Scope is deliberately narrow -
# a NEW PLAY, and a PLAY that is dropped BEFORE THE GAME STARTS. LEAN and DEAD first sightings
# stay silent, as do flips after tip-off, which are history rather than something to act on.
# This is a NOTIFICATION path only. Lane 3 remains paper: no order path exists here and none is
# added. BOARD_PUSH (ntfy) is untouched and still off.
# Nov 9 (Peter, 9:55 AM): "FOR NOW TURN OFF PUSH NOTIFICATIONS TO TELEGRAM BETS BOARD WE WILL REVISIT HOW WE PLAY".
# Default is OFF, and bets-board.yml no longer passes BOARD_TG at all, so the repo variable cannot switch it
# back on by itself. Rows are still recorded as sent, so turning it back on never floods the backlog.
TG = (os.environ.get("BOARD_TG") or "off").strip().lower() == "on"


def tg(text):
    """One-line push to @sharp_fills_bot. A local sender on purpose: the three existing
    tg_mirror() twins live in sharp_monitor, liquidity_monitor and px_live, which all do
    live-trading setup at import time, and this is a small paper-lane script. Silent on failure,
    nothing sensitive in the public log."""
    tok = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not (TG and tok and chat):
        return False
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     data=json.dumps({"chat_id": chat, "text": text[:3500]}).encode(),
                                     method="POST", headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except Exception:
        print("board telegram failed")
        return False


def one_line(r, x, dropped=False):
    """The chat one-liner. Price is the board's own best after-fee quote where it has one."""
    am = x.get("best_price_american") or x.get("price_american")
    bk = x.get("best_price_book") or x.get("book") or r.get("book") or ""
    side, ln = r.get("side") or x.get("side_label") or "", x.get("line")
    bet = f"{side} {ln:g}" if isinstance(ln, (int, float)) else str(side)
    px = f" {am:+d}" if isinstance(am, int) else ""
    if dropped:
        return (f"\u26aa BOARD PLAY DROPPED  {r.get('league','')} {r.get('game','')}  {bet}"
                f"  -  {(r.get('why') or 'no longer on the board')[:70]}")
    return (f"\U0001F7E2 BOARD PLAY  {r.get('league','')} {r.get('game','')}  {bet}{px} {bk}"
            f"  {bb.money(r.get('new') or 0)} new  -  paper signal, check the price")


def when_of(v):
    """A record is either the new dict or a pre-Nov-6 bare timestamp string."""
    return (v.get("when") or "") if isinstance(v, dict) else (v or "")


def record(when, r, x):
    """Everything needed to read the call back without a lookup. Values come from the alert the
    board scored, so nothing here is derived or estimated."""
    mid = None
    try:                                    # the book's own id, out of the feed's key json
        mid = json.loads((x.get("key") or "|").split("|", 1)[1])
        mid = mid.get("market_ticker") or mid.get("pm_market_id") or mid.get("px_market") or None
    except Exception:
        mid = None
    return {"when": when, "tag": r.get("tag"),
            "game": x.get("game") or r.get("game"), "league": x.get("league") or r.get("league"),
            "market": x.get("market") or r.get("mk"),
            "side": x.get("side_label") or x.get("side") or r.get("side"),
            "line": x.get("line"), "price": x.get("price"), "price_american": x.get("price_american"),
            "best_price": x.get("best_price"), "best_price_american": x.get("best_price_american"),
            "best_price_book": x.get("best_price_book"), "book": x.get("book") or r.get("book"),
            "alerted_utc": x.get("alerted_utc"), "start_utc": x.get("start_utc"), "market_id": mid}


def migrate(sent, rows):
    """Fill in pre-Nov-6 records, but ONLY on an identity match. The record key is
    "tag|<feed key>|<alerted_utc>", so re-finding that exact pair in this run's rows is the same
    row and not a near-match; anything else is left exactly as it was."""
    by = {}
    for r in rows:
        x = r["x"]
        if x.get("key") and x.get("alerted_utc"):
            by[(x["key"], x["alerted_utc"])] = (r, x)
    n = 0
    for k, v in list(sent.items()):
        if isinstance(v, dict):
            continue
        p = k.split("|")
        if len(p) < 3:
            continue
        hit = by.get(("|".join(p[1:-1]), p[-1]))
        if not hit:
            sent[k] = {"when": v}          # keep the timestamp, invent nothing
            continue
        r, x = hit
        rec = record(v, r, x)               # the original send time stands
        rec["tag"] = p[0]                   # the tag it was recorded under, not today's
        rec["reconstructed"] = True
        sent[k] = rec
        n += 1
    return n


def restatus(sent, rows, now):
    """Nov 6 (Peter): the historical PLAY event is preserved, but its CURRENT status is not.

    The page said "every call is written down when it posts and never rewritten, so a PLAY whose
    money is pulled afterwards still grades as the PLAY it was" - good for grading fidelity, wrong
    for reading the file, because 14 of the first 17 records had their money pulled before tip and
    still read as PLAY. Both can hold: 'tag' is what it was called when it posted and never changes,
    while status_now / tag_now track the board today and flipped_at records WHEN it stopped being
    actionable. A record whose row is no longer on the board is left alone rather than guessed at.
    """
    by = {}
    for r in rows:
        x = r["x"]
        if x.get("key") and x.get("alerted_utc"):
            by[(x["key"], x["alerted_utc"])] = r
    n, flips = 0, []
    for k, v in sent.items():
        if not isinstance(v, dict):
            continue
        p = k.split("|")
        r = by.get(("|".join(p[1:-1]), p[-1])) if len(p) >= 3 else None
        if r is None:
            continue                      # not on the board this run: say nothing new about it
        st, tg = r.get("status"), r.get("tag")
        v["status_now"], v["tag_now"], v["checked_at"] = st, tg, now.isoformat()
        gone = st != "still there" or tg != v.get("tag")
        if gone and not v.get("flipped_at"):
            v["flipped_at"] = now.isoformat()
            v["flip_reason"] = (r.get("why") or "")[:160] or f"status {st}, tag {tg}"
            n += 1
            if v.get("tag") == "PLAY":
                flips.append((v, r))        # the caller decides whether it is pre-start
    return n, flips


def main():
    now, rows, _ = bb.build()
    try:
        st = json.load(open(FILE))
    except Exception:
        st = {"sent": {}}
    sent = st.setdefault("sent", {})
    new = pushed = dropped_sent = 0
    for r in rows:
        if r.get("tag") not in TAGS or r["status"] != "still there":
            continue
        x = r["x"]
        k = f"{r['tag']}|{x.get('key') or (r['game'] + '|' + str(r['mk']) + '|' + str(r['sd']))}|{x.get('alerted_utc')}"
        if k in sent:
            continue
        title = f"Bets Board {r['tag']}: {r['side']}"
        body = (f"{r['league']} {r['game']} | {r['mk']} | {bb.money(r['new'])} new money | {r['book']}\n"
                f"{r.get('why') or ''}\nPaper signal - check the price before betting. faros4life.github.io/sharp-monitor")
        if TOPIC and PUSH:
            try:
                req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
                                             headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high",
                                                      "Tags": "green_circle" if r["tag"] == "PLAY" else "yellow_circle",
                                                      "Click": "https://faros4life.github.io/sharp-monitor/"})
                urllib.request.urlopen(req, timeout=15).read()
            except Exception:
                continue   # not marked sent: retried next run
        sent[k] = record(now.isoformat(), r, x)
        new += 1
        if r["tag"] == "PLAY" and tg(one_line(r, x)):
            pushed += 1
    migrated = migrate(sent, rows)
    flipped, flips = restatus(sent, rows, now)
    # a PLAY that dies BEFORE tip is actionable - Peter can stand down. After tip it is history.
    for v, r in flips:
        # Nov 11: this used to bind `st`, which is the STATE dict a few lines below - so the first pre-start drop
        # of any day turned st into a string and the run died on st["sent"] before the state was ever written.
        start = v.get("start_utc") or (r["x"].get("start_utc") if isinstance(r.get("x"), dict) else None)
        try:
            pre = bool(start) and now < datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        except Exception:
            pre = False
        if pre and tg(one_line(r, r["x"], dropped=True)):
            pushed += 1
            dropped_sent += 1
    cut = (now - timedelta(days=3)).isoformat()
    st["sent"] = {k: v for k, v in sent.items() if when_of(v) >= cut}
    os.makedirs("lanes", exist_ok=True)
    json.dump(st, open(FILE, "w"), indent=1)
    print(f"board alerts: {new} sent, {migrated} migrated, {flipped} newly flipped from PLAY "
          f"({', '.join(TAGS)}); telegram {pushed} pushed ({dropped_sent} pre-start drops), "
          f"BOARD_TG={'on' if TG else 'off'}, BOARD_PUSH={'on' if PUSH else 'off'}")   # counts only


if __name__ == "__main__":
    main()

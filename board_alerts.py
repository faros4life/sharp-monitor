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

import board_build as bb

FILE = "lanes/board_alerts.json"
TOPIC = (os.environ.get("NTFY_TOPIC") or "").strip()
TAGS = [t.strip().upper() for t in (os.environ.get("BOARD_ALERT_TAGS") or "PLAY").split(",") if t.strip()]
# Nov 4 (Peter via Muse, 7:42 AM): board PLAY pushes OFF - Lane 3 is off, so every board call is paper. Rows are still
# recorded as sent (so turning it back on never floods old calls). BOARD_PUSH=on brings the push back.
PUSH = (os.environ.get("BOARD_PUSH") or "off").strip().lower() == "on"


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
            "alerted_utc": x.get("alerted_utc"), "market_id": mid}


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


def main():
    now, rows, _ = bb.build()
    try:
        st = json.load(open(FILE))
    except Exception:
        st = {"sent": {}}
    sent = st.setdefault("sent", {})
    new = 0
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
    migrated = migrate(sent, rows)
    cut = (now - timedelta(days=3)).isoformat()
    st["sent"] = {k: v for k, v in sent.items() if when_of(v) >= cut}
    os.makedirs("lanes", exist_ok=True)
    json.dump(st, open(FILE, "w"), indent=1)
    print(f"board alerts: {new} sent ({', '.join(TAGS)})")   # counts only


if __name__ == "__main__":
    main()

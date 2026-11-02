#!/usr/bin/env python3
"""
BETS BOARD PHONE ALERTS (Nov 2, 2026; Peter 18:35: "yes" to a phone alert when a new PLAY call shows on the board).
Runs inside the bets-board job, right after each rebuild's inputs land. Sends one ntfy push the first time a row is called
PLAY while its money is still there (same rules as the board: board_build.score). Already-sent rows are remembered in
lanes/board_alerts.json (public: game, side and time only - the board itself is public). Paper signal; check the price.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import board_build as bb

FILE = "lanes/board_alerts.json"
TOPIC = (os.environ.get("NTFY_TOPIC") or "").strip()
TAGS = [t.strip().upper() for t in (os.environ.get("BOARD_ALERT_TAGS") or "PLAY").split(",") if t.strip()]


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
        if TOPIC:
            try:
                req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
                                             headers={"Title": title.encode("ascii", "ignore").decode(), "Priority": "high",
                                                      "Tags": "green_circle" if r["tag"] == "PLAY" else "yellow_circle",
                                                      "Click": "https://faros4life.github.io/sharp-monitor/"})
                urllib.request.urlopen(req, timeout=15).read()
            except Exception:
                continue   # not marked sent: retried next run
        sent[k] = now.isoformat()
        new += 1
    cut = (now - timedelta(days=3)).isoformat()
    st["sent"] = {k: v for k, v in sent.items() if v >= cut}
    os.makedirs("lanes", exist_ok=True)
    json.dump(st, open(FILE, "w"), indent=1)
    print(f"board alerts: {new} sent ({', '.join(TAGS)})")   # counts only


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""One-shot read-only probe: does nba_novig_forward parse Novig's live public catalog? Prints parsed fields for up to 3 NBA games
(public exchange prices only; no OddsPapi, no key, no order). Not part of any job."""
import re
from datetime import datetime, timezone
import nba_novig_forward as n

now = datetime.now(timezone.utc)
ev, mk = n._catalog(now)
print(f"NBA events {len(ev)}; markets on them {len(mk)}")
print("market types:", sorted({m.get('marketType') for m in mk}))
if ev:
    print("event keys:", sorted(ev[0].keys()))
    print("sample descriptions:", [e.get('description') for e in ev[:3]])
done = 0
for e in sorted(ev, key=lambda e: e.get("startsTs") or 0):
    desc = e.get("description") or ""
    parts = re.split(r"\s+(?:@|at|vs\.?)\s+", desc)
    tots = [m for m in mk if m.get("eventId") == e["eventId"] and (m.get("marketType") or "").upper() == "TOTAL" and m.get("status") == "OPEN"]
    if len(parts) != 2 or not tots:
        print(f"skip '{desc}': parts {len(parts)} totals {len(tots)}")
        continue
    away, home = parts
    for m in tots[:2]:
        for side in ("Over", "Under"):
            q = n.novig_quote(home, away, float(m["strike"]), side, now)
            print(f"{desc} | strike {m['strike']} {side}: {q}")
    done += 1
    if done >= 3:
        break
print(f"games probed {done}")

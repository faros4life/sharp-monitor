#!/usr/bin/env python3
"""Read-only probe: which TOTAL strikes/status does Novig's public catalog list per NBA event? (public data only)"""
from datetime import datetime, timezone
import nba_novig_forward as n

now = datetime.now(timezone.utc)
ev, mk = n._catalog(now)
print(f"NBA events {len(ev)}; markets {len(mk)}")
for e in sorted(ev, key=lambda e: e.get("startsTs") or 0):
    ts = [m for m in mk if m.get("eventId") == e["eventId"] and (m.get("marketType") or "").upper() == "TOTAL"]
    print(f"{e.get('description')} | status {e.get('status')} | TOTAL markets {len(ts)} | strikes/status: "
          + ", ".join(sorted(f"{m.get('strike')}:{m.get('status')}" for m in ts)))
    print("   other total-like types:", sorted({m.get('marketType') for m in mk if m.get('eventId') == e['eventId'] and 'TOTAL' in (m.get('marketType') or '')}))

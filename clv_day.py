#!/usr/bin/env python3
"""READ-ONLY per-play CLV lookup for Nov 12 plays (Peter, Nov 13). No IMAP/ESPN/OddsPapi, writes nothing."""
import json
import clv_ledger as cl
import tracker_build as tb
st = tb.dec(json.load(open(cl.STATE)))
bets = st.get("bets") or {}
names = ("louisiana", "dallas", "charlotte", "toronto")
n = 0
for k, r in bets.items():
    s = json.dumps(r, default=str)
    if "2026-11-12" not in s and "2026-11-13" not in s:
        continue
    if not any(x in s.lower() for x in names):
        continue
    n += 1
    keep = {a: v for a, v in r.items() if a != "snap"}
    keep["id"] = k[:40]
    keep["snap"] = {a: v for a, v in (r.get("snap") or {}).items() if not isinstance(v, (dict, list))}
    print(json.dumps(keep, default=str)[:1200])
print("rows matched", n, "of", len(bets))

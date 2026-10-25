#!/usr/bin/env python3
"""Manual check: can every book's open positions be read? Prints counts and market types only (public log: no amounts)."""
import executor as ex
import positions

pos = ex.novig_positions()
print("Novig: " + (f"checked, {len(pos)} open position(s)" if pos is not None else f"unavailable ({ex._NVERR.get('why')})")
      + (f" | subaccount: {ex._NVERR['sub']}" if ex._NVERR.get("sub") else " | main + auto-place subaccount read"))
held = positions.all_positions()
for b, v in held.items():
    if v is None:
        print(f"{ex.BOOK_NAME[b]}: unavailable ({positions.WHY.get(b, '?')})")
    else:
        kinds = {}
        for h in v:
            kinds[h["mtype"]] = kinds.get(h["mtype"], 0) + 1
        matched = sum(1 for h in v if h.get("game"))
        print(f"{ex.BOOK_NAME[b]}: checked, {len(v)} open side(s) {kinds or ''}, {matched} with a readable game name")
print(positions.status_line(held))
print("ProphetX trade check (no amounts):", positions.STATS.get("prophetx"))

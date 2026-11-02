#!/usr/bin/env python3
"""
One-off ProphetX read (Nov 2, 2026; Muse T3 chase, Peter approved): every ProphetX trade on Fri Oct 23, 2026
(UTC 12:00 Oct 23 - 06:00 Oct 24), flagging Timberwolves/Magic and totals near 235.5. Also tries the open/closed
orders list for the resting remainder. READ-ONLY: no order is placed or changed. Private email; log prints counts only.
"""
import json
from datetime import datetime, timezone

import executor as ex
import px_live

LO, HI = datetime(2026, 10, 23, 12, tzinfo=timezone.utc), datetime(2026, 10, 24, 6, tzinfo=timezone.utc)
WORDS = ("timberwolves", "minnesota", "magic", "orlando", "235.5", "235")
KEEP = ("id", "order_id", "created_at", "updated_at", "matched_at", "settled_at", "event_name", "line_name", "selection",
        "market_name", "price", "quantity", "status", "winning_status", "profit", "strike_id", "side")


def t(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def hit(o):
    s = json.dumps(o).lower()
    return any(w in s for w in WORDS)


def main():
    if not px_live.login():
        ex.send("Bets PX LOOKUP: Timberwolves @ Magic Oct 23", "ProphetX login failed - nothing read.")
        print("login failed")
        return
    tr = px_live.trades()
    day = [x for x in tr if (lambda d: d is not None and LO <= d < HI)(t(x.get("created_at")))]
    lines = [f"ProphetX trades returned: {len(tr)} total; {len(day)} created Oct 23 12:00 UTC - Oct 24 06:00 UTC.",
             "Matches (team names or 235/235.5 anywhere in the record) are marked >>.", ""]
    for x in sorted(day, key=lambda x: str(x.get("created_at"))):
        rec = {k: x.get(k) for k in KEEP if x.get(k) is not None}
        rec["stake_usd"] = round(px_live.stake_of(x), 2)
        lines.append((">> " if hit(x) else "   ") + json.dumps(rec))
    found = [x for x in tr if hit(x)]
    lines += ["", f"Trades on ANY date matching the words: {len(found)}"]
    for x in found:
        rec = {k: x.get(k) for k in KEEP if x.get(k) is not None}
        rec["stake_usd"] = round(px_live.stake_of(x), 2)
        lines.append("   " + json.dumps(rec))
    lines += ["", "Orders (resting remainder):"]
    for path in ("/v4/mm/get_orders", "/v4/mm/orders", "/v4/mm/get_open_orders"):
        try:
            d = px_live._call(path)
            data = d.get("data") or {}
            orders = data.get("orders") or data.get("items") or (data if isinstance(data, list) else [])
            m = [o for o in orders if hit(o)]
            lines.append(f"  {path}: {len(orders)} orders returned, {len(m)} matching")
            for o in m:
                lines.append("    " + json.dumps(o)[:1500])
        except Exception as e:
            lines.append(f"  {path}: not available ({type(e).__name__})")
    lines += ["", "Game: MIN 115 - ORL 93 (total 208), so any filled Over 235.5 stake lost."]
    ex.send("Bets PX LOOKUP: Timberwolves @ Magic Oct 23", "\n".join(lines))
    print(f"PX lookup emailed: {len(day)} trades that day, {len(found)} word matches")   # counts only


if __name__ == "__main__":
    main()

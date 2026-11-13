#!/usr/bin/env python3
"""LIVE BOT PLAYS for the Last 50 page, by lane (Peter, Nov 13). READ-ONLY.

Decrypts tracker/state.enc, keeps source == "bot" rows (same grouping as bot_record.py), splits them by
lane (PHASE 1 = Lane 1, BOARD V3, R1, LANE 2) and writes tracker/bot_live.enc, encrypted with the same
TRACKER_PASSPHRASE scheme as state.enc. The plaintext never reaches the repo or the log.

NO DOLLARS: units are profit / stake per play (flat 1u risked, the same convention as the last-50 report),
plus the logged price, result and scoreboard. Stakes and balances are not exported.
The log prints counts only.
"""
import copy
import json
import sys
from datetime import datetime, timezone

import tracker_build as tb

FIRST_MULTI_LANE_DAY = "2026-11-11"   # R1 and Board v3 were approved on Nov 11; before it only Lane 1 (PHASE 1) could place

OUT = "tracker/bot_live.enc"
LANES = {"PHASE 1": "Lane 1", "BOARD V3": "Bets Board v3", "R1": "R1", "LANE 2": "Lane 2"}


def play(b):
    st = b.get("stake") or 0
    res = b.get("result")
    units = round((b.get("profit") or 0) / st, 2) if res in ("W", "L", "P") and st else None
    t = b.get("teams") or []
    return {"game": b.get("game") or "", "bet": b.get("bet") or "", "book": b.get("book") or "",
            "price": b.get("price"), "result": res, "open": bool(b.get("open") and not res), "units": units,
            "start": b.get("game_start") or "", "settled": b.get("settled") or "",
            "seen": b.get("first_seen") or "",
            "state": b.get("g_state") or "", "detail": b.get("g_detail") or "",
            "teams": [{"n": x.get("name"), "s": x.get("score")} for x in t] if len(t) == 2 else None,
            "final": bool(b.get("teams_final"))}


def registry_lanes():
    """key -> lane name from the bot's PRIVATE GitHub registry (the source of truth; Gmail is only the backup).
    The store keeps about 4 days, so it cannot label older plays. Returns {} when unreadable."""
    out = {}
    try:
        import executor as ex
        import registry as reg
        for row in reg.rows() or []:
            if not row.get("key"):
                continue
            d = lambda x: x if isinstance(x, dict) else {}   # some rows carry False/None here
            more = row.get("live_more")
            los = ([d(row.get("live_order")), d(row.get("live_rest"))]
                   + [d(x) for x in (more if isinstance(more, list) else [])])
            if any(lo.get("status") == "placed" and lo.get("order_id") and not lo.get("intent")
                   and not lo.get("voided") for lo in los):
                out[row["key"]] = ex.LANE_NAME.get(ex.lane_of(row), "PHASE 1")
    except Exception as e:
        print(f"registry unreadable ({type(e).__name__}: {str(e)[:90]}); lanes fall back to the tracker own tags")
    return out


def main():
    st = tb.dec(json.load(open(tb.STATE)))
    raw = copy.deepcopy(st.get("bets") or {})
    tb.mark_manual_dups(raw)
    rows = tb.group_fills([b for b in raw.values() if not b.get("dup_of")])
    out = {k: [] for k in LANES.values()}
    out["Unattributed"] = []
    keylane = registry_lanes()
    how = {"tracker tag": 0, "registry": 0, "before R1/Board (inferred Lane 1)": 0, "none": 0}
    for b in rows:
        if (b.get("source") or "") != "bot":
            continue
        lane, src = b.get("lane"), "tracker tag"
        if not lane:
            lane = next((v for k, v in keylane.items() if tb.bot_match(b, {k})), None)
            src = "registry"
        if not lane:
            day = (b.get("game_start") or b.get("settled") or b.get("first_seen") or "")[:10]
            if day and day < FIRST_MULTI_LANE_DAY:
                lane, src = "PHASE 1", "before R1/Board (inferred Lane 1)"
        if not lane:
            src = "none"
        how[src] += 1
        pl = play(b)
        pl["how"] = src
        out[LANES.get(lane, "Unattributed")].append(pl)
    for k in out:
        out[k].sort(key=lambda p: p["start"] or p["seen"], reverse=True)
        out[k] = out[k][:80]
    doc = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "lanes": out}
    json.dump(tb.enc(doc), open(OUT, "w"))
    print("lane source:", how)
    print("exported plays per lane:", {k: len(v) for k, v in out.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())

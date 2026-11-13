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


def main():
    st = tb.dec(json.load(open(tb.STATE)))
    raw = copy.deepcopy(st.get("bets") or {})
    tb.mark_manual_dups(raw)
    rows = tb.group_fills([b for b in raw.values() if not b.get("dup_of")])
    out = {k: [] for k in LANES.values()}
    out["Unattributed"] = []
    for b in rows:
        if (b.get("source") or "") != "bot":
            continue
        out[LANES.get(b.get("lane"), "Unattributed")].append(play(b))
    for k in out:
        out[k].sort(key=lambda p: p["start"] or p["seen"], reverse=True)
        out[k] = out[k][:80]
    doc = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "lanes": out}
    json.dump(tb.enc(doc), open(OUT, "w"))
    print("exported plays per lane:", {k: len(v) for k, v in out.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())

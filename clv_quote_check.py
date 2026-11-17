#!/usr/bin/env python3
"""READ-ONLY check of the stalest certified NCAAB close (Peter, Nov 16 19:09). FREE history path only.

For the reopened NCAAB bot row with the oldest certified quote, reports - minutes and flags only,
never a price - whether the bet's own Pinnacle line was still ACTIVE at its last pregame tick, and
how fresh Pinnacle's other total lines (including the main line) were at the start. Writes nothing.
"""
import json
import sys

import clv_ledger as cl
import hist_cache as hc
import tracker_build as tb


def main():
    st = tb.dec(json.load(open(cl.STATE)))
    mk = (json.load(open(cl.MKFILE)) or {}).get("m") or {}
    rows = [r for r in st["bets"].values() if r.get("ncaab_reopened") and r.get("clv") is not None]
    print(f"certified reopened NCAAB rows: {len(rows)}")
    if not rows:
        return 1
    r = max(rows, key=lambda x: x.get("age_min") or 0)
    s, fid = r["snap"], r.get("fixture")
    fx = json.load(open("oddspapi/fixtures_ncaab.json"))["fixtures"].get(fid) or {}
    start = cl.tp(fx.get("start"))
    pz = cl.parsed(s)
    print(f"row: market {pz[0]} | how {r.get('how')} | stored quote age {r.get('age_min')} min | fixture found {bool(fx)}")
    h = hc.get_hist(fid, ["pinnacle"], start)
    if isinstance(h, dict) and h.get("_error"):
        h = cl.api("/historical-odds", False, fixtureId=fid, bookmakers="pinnacle")
    pm = cl.book_markets(h, "pinnacle")
    lines = []
    for mid, (sid, typ, hcap, outs) in mk.items():
        if sid != 11 or typ != "totals" or mid not in pm:
            continue
        info = {"own": abs(hcap - pz[2]) < 1e-9, "diff": round(hcap - pz[2], 1)}
        for oid, o in (pm[mid].get("outcomes") or {}).items():
            ticks = (o.get("players") or {}).get("0") or []
            pre = [t for t in ticks if cl.tp(t.get("createdAt")) and cl.tp(t["createdAt"]) <= start]
            post = [t for t in ticks if cl.tp(t.get("createdAt")) and cl.tp(t["createdAt"]) > start]
            if not pre:
                continue
            last = max(pre, key=lambda t: cl.tp(t["createdAt"]))
            age = round((start - cl.tp(last["createdAt"])).total_seconds() / 60)
            info.setdefault("ages", []).append(age)
            info.setdefault("active", []).append(last.get("active"))
            info.setdefault("limit", []).append(last.get("limit"))
            info["any_inactive_pre"] = info.get("any_inactive_pre", False) or any(t.get("active") is False for t in pre)
            info["post_ticks"] = info.get("post_ticks", 0) + len(post)
        if info.get("ages"):
            lines.append(info)
    main_ = max(lines, key=lambda x: min(x.get("limit") or [0])) if lines else None
    for x in sorted(lines, key=lambda x: x["diff"]):
        tag = "OWN " if x["own"] else ("MAIN" if x is main_ else "    ")
        print(f"{tag} line diff {x['diff']:+.1f} | last pregame tick ages (min) {x['ages']} | active flag at last tick {x['active']} "
              f"| any inactive tick pregame {x['any_inactive_pre']} | limit rank {'top' if x is main_ else '-'} | ticks after start {x['post_ticks']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

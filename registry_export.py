#!/usr/bin/env python3
"""Export the registered strategy list for Muse's scorecard build.

Muse asked for "the strategy registry (his 56)". There is no list of 56 on this side: SCORECARD.md,
"master list of everything we have run", holds 34 numbered entries, of which 25 are betting lanes
and 9 are lenses or research that are not strategies. This export says so rather than inventing
cuts to reach a number - which Muse itself called mining.

NO MONEY: entries carry status and already-published percentages, units and counts; any dollar
figure in the source is redacted on the way out. Read-only; nothing here touches a live path.
"""
import json
import re
import sys

LANES = {"rules": "PHASE 1", "board": "BOARD V3", "r1": "R1", "lane2": "LANE 2 (paper)"}


def clean(x):
    return re.sub(r"\$[\d,]+(?:\.\d+)?", "[redacted]", re.sub(r"\*\*", "", x)).strip()


def entries(path="SCORECARD.md"):
    sec, out = None, []
    for ln in open(path):
        h = re.match(r"^#{2,3}\s+(.*)", ln)
        if h:
            sec = h.group(1).strip()
            continue
        if not sec or not ln.strip().startswith("|"):
            continue
        c = [clean(x) for x in ln.strip().strip("|").split("|")]
        if not c or not re.match(r"^\d+$", re.sub(r"\D", "", c[0]) or "x"):
            continue
        if not re.match(r"^\*{0,2}\d+\*{0,2}$", ln.strip().strip("|").split("|")[0].strip()):
            continue
        out.append({"entry_no": int(re.sub(r"\D", "", c[0])), "section": sec.split("—")[0].strip(),
                    "name": c[1] if len(c) > 1 else "",
                    "latest_numbers": c[2] if len(c) > 2 else "",
                    "status": c[-1] if len(c) > 2 else "",
                    "is_betting_lane": not sec.upper().startswith(("LENSES", "RESEARCH"))})
    return sorted(out, key=lambda r: r["entry_no"])


def main(argv):
    e = entries()
    dupes = sorted({r["entry_no"] for r in e
                    if sum(1 for x in e if x["entry_no"] == r["entry_no"]) > 1})
    out = {
        "export": "claude registered strategy list",
        "source": "SCORECARD.md (master list) + REGISTRY.md (THE ONE LIST)",
        "count_total": len(e),
        "count_betting_lanes": sum(1 for r in e if r["is_betting_lane"]),
        "count_not_strategies": sum(1 for r in e if not r["is_betting_lane"]),
        "live_strategy_keys": sorted({f"{k}|" for k in LANES}),
        "lane_map": LANES,
        "duplicate_entry_numbers": dupes,
        "entries": e,
        "gaps": [
            "There is no list of 56. The master list has %d numbered entries; %d are betting lanes "
            "and %d are lenses or research that are not strategies. No cuts were invented to reach "
            "another number." % (len(e), sum(1 for r in e if r["is_betting_lane"]),
                                 sum(1 for r in e if not r["is_betting_lane"])),
            "Entry numbers %s are each used by two different entries, so any join on entry number "
            "collides on them." % (dupes or "none"),
            "alert_price is NOT stored on tracker rows. The scorecard is graded at alert price, so "
            "this is the binding gap: only line_value_replay carries alert_price_after_fee, for a "
            "different population.",
            "No stable play_id spans bot, hand-placed and paper rows. executor.play_id() covers bot "
            "plays only, so a join would fall back to fuzzy matching.",
            "strategy_key is set only on bot orders matched to the registry by order id; "
            "hand-placed and paper rows carry none.",
            "order_type (taker vs resting) is recoverable from the registry, not from the tracker.",
        ],
    }
    path = argv[1] if len(argv) > 1 else "claude_registry.json"
    json.dump(out, open(path, "w"), indent=1)
    print(f"registry export: {out['count_total']} entries "
          f"({out['count_betting_lanes']} betting lanes, {out['count_not_strategies']} not), "
          f"duplicate numbers {dupes or 'none'}, {len(out['gaps'])} gaps -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""READ-ONLY diagnostic: time the four position readers without touching production state.

Peter, Nov 12: "If no qualifying play appears, use a safe read-only diagnostic to exercise the
position readers without placing orders or changing production state."

WHY THIS EXISTS. "positions read (first attempt)" measured 378.6s as one number - 73% of a
599-second executor run - while every per-call venue counter came back under a second. The executor
only performs that read when it has a play to evaluate (a `new: 0` run takes an early return and
skips it), so waiting for the measurement means waiting for an alert. This exercises the same four
readers on demand.

WHAT IT DOES NOT DO. It does not place, cancel, modify or price any order. It does not read
alerts.json, evaluate a play, touch the daily stop, the write-ahead journal or any STOP/GO state.
It calls the same four read-only position functions the executor calls and prints their timings.

ONE WRITE, and it is the same write the executor already makes on every such read:
positions.px_positions() stores resolved strike IDENTITIES in the registry cache (put_strikes). A
strike_id names one selection in one market and never changes meaning, so that cache is entity data
- it never records what is held or what it is worth. Running this therefore warms exactly the cache
a normal run warms, and nothing else. Reusing the executor's own _timed_pos() rather than a second
copy, so what is measured here is what runs in production.
"""
import sys

import executor as ex
import positions


def main():
    readers = (("novig", ex.novig_positions),
               ("kalshi", positions.kalshi_positions),
               ("prophetx", positions.px_positions),
               ("polymarket_us", positions.pmus_positions))

    print("READ-ONLY position probe. No order is placed, cancelled, modified or priced.")
    print("Running the four readers SEQUENTIALLY, so each duration is its own and not masked by")
    print("the parallel block's slowest member.\n")

    out = {}
    for name, fn in readers:
        try:
            v = ex._timed_pos(name, fn)()
            # None is the fail-closed answer: "this venue could not be verified". Never zero.
            out[name] = "unreadable (fail-closed)" if v is None else f"{len(v)} position group(s)"
        except Exception as e_:
            out[name] = f"raised {type(e_).__name__}: {str(e_)[:60]}"

    print("DURATIONS (whole function: waits, retries, cache access, network)")
    for name, secs in sorted(ex.POSW.items(), key=lambda kv: -kv[1]):
        print(f"  {secs:7.1f}s  {name:<14} -> {out.get(name)}")
    total = sum(ex.POSW.values())
    print(f"  {total:7.1f}s  TOTAL (sequential; the executor runs these four in parallel,")
    print(f"           so its bracket is about the SLOWEST one, not this sum)\n")

    print("PROPHETX SUB-TIMINGS AND STRIKE CACHE")
    if positions.WHY.get("prophetx_timing"):
        print(f"  sub-steps:   {positions.WHY['prophetx_timing']}")
    else:
        print("  sub-steps:   not recorded (px_positions returned before the walk)")
    if positions.WHY.get("prophetx_walk_s"):
        print(f"  walk:        {positions.WHY['prophetx_walk_s']}")
    st = positions.STATS.get("prophetx") or {}
    if st:
        print(f"  counts:      {st}")
        want, got = st.get("open_strikes") or 0, st.get("matched_strikes") or 0
        print(f"  cache:       {got}/{want} strikes resolved"
              + (f"; {want - got} unresolved" if want > got else "; all resolved"))
    for k in ("prophetx", "prophetx_cache", "prophetx_cache_write"):
        if positions.WHY.get(k):
            print(f"  note {k}: {str(positions.WHY[k])[:90]}")

    print("\nNothing was placed, cancelled or modified. Counts and seconds only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

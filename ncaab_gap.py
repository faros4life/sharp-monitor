#!/usr/bin/env python3
"""NCAAB OPENERS - GAP DISTRIBUTION (read-only; Peter approved Nov 5).

Answers one question: how far apart are our frozen number and Pinnacle's open, across every
graded game - not just the two that cleared the 3.0 band? Counting sightings throws away the
near-misses, and with 2 of 22 there is nothing to forecast from. The full distribution says
whether 60 sightings is reachable at all, or whether the model simply agrees with the market.

Reads ONLY what the grader already stored: rec["diff"] = our number - Pinnacle's open, set for
every posted game with a number, before the band test. Nothing is recomputed from odds, so this
makes NO OddsPapi calls of any kind - free or billable - and writes no file.

Splits the gap against freeze eligibility, because a gap only becomes a sighting if we froze
BEFORE Pinnacle opened. That separates "the model does not disagree" from "the model disagrees
but we were too late to count it" - two very different verdicts on the lane.

OddsPapi data is never republished: the report goes to the private address, the Actions log gets
counts only, exactly as the grader does.
"""
import json
import os
import statistics as s
import sys
from collections import Counter

import executor as ex
import tracker_build as tb

DIR = os.environ.get("NCAAB_DIR", "") or "ncaab-openers"
FROZEN = os.path.join(DIR, "ncaab_openers.json")
GRADES = os.path.join(DIR, "ncaab_grades.enc")
BAND = 3.0
FIRST_READ = 60


def main():
    try:
        games = (json.load(open(FROZEN)) or {}).get("games") or {}
    except Exception as e:
        print(f"no frozen file ({type(e).__name__})")
        return 1
    try:
        st = tb.dec(json.load(open(GRADES)))
    except Exception as e:
        print(f"no grades file ({type(e).__name__})")
        return 1
    graded = (st or {}).get("graded") or {}

    rows = []
    for gid, r in graded.items():
        if not isinstance(r, dict) or not r.get("posted") or r.get("diff") is None:
            continue
        g = games.get(gid) or {}
        lag = r.get("freeze_lag_min")
        rows.append({"diff": float(r["diff"]), "lag": lag,
                     "early": (lag is not None and lag > 0),
                     "late": r.get("not_sighting") == "frozen after Pinnacle's open",
                     "on_time": bool(g.get("on_time")),
                     "final": g.get("final"), "num": g.get("number"),
                     "open": r.get("open_line")})
    if not rows:
        print("no graded games with a stored gap yet")
        return 0

    a = [abs(x["diff"]) for x in rows]
    L = [f"NCAAB OPENERS - GAP DISTRIBUTION (read-only; no OddsPapi calls; n {len(rows)} graded games)",
         "",
         "THE QUESTION: is 60 sightings reachable, or does our number just agree with Pinnacle?",
         f"A sighting needs |gap| >= {BAND} AND a freeze before Pinnacle's open.",
         ""]

    L.append(f"|gap| distribution (our number vs Pinnacle's open)")
    L.append(f"  mean {s.mean(a):.2f} | median {s.median(a):.2f} | "
             f"stdev {s.pstdev(a) if len(a) > 1 else 0:.2f} | max {max(a):.2f}")
    b = Counter()
    for x in a:
        b["0.0-0.9" if x < 1 else "1.0-1.9" if x < 2 else "2.0-2.9" if x < 3
          else "3.0-3.9" if x < 4 else "4.0+"] += 1
    for k in ["0.0-0.9", "1.0-1.9", "2.0-2.9", "3.0-3.9", "4.0+"]:
        bar = "#" * round(b[k] / len(a) * 40)
        L.append(f"    {k:8s} {b[k]:4d}  {b[k]/len(a)*100:5.1f}%  {bar}")
    over = b["3.0-3.9"] + b["4.0+"]
    L.append(f"  clears the {BAND} band: {over}/{len(a)} = {over/len(a)*100:.1f}%")
    L.append("")

    # the part that matters: how much of the band-clearing population we are throwing away
    cl = [x for x in rows if abs(x["diff"]) >= BAND]
    cl_e = [x for x in cl if not x["late"]]
    L.append("OF THE GAMES THAT CLEAR THE BAND, how many actually counted?")
    L.append(f"  cleared the band            {len(cl)}")
    L.append(f"  ...and froze before the open {len(cl_e)}   <- these are the sightings")
    L.append(f"  ...and froze after  the open {len(cl)-len(cl_e)}   <- discarded (correctly)")
    if cl:
        L.append(f"  eligibility rate among band-clearers: {len(cl_e)/len(cl)*100:.1f}%")
    L.append("")

    lags = [x["lag"] for x in rows if x["lag"] is not None]
    if lags:
        e = sum(1 for x in lags if x > 0)
        L.append(f"FREEZE vs OPEN across all {len(lags)} graded games (positive = we froze first)")
        L.append(f"  median lag {s.median(lags)/60:+.1f} h | froze first {e}/{len(lags)} = {e/len(lags)*100:.1f}%")
        L.append("")

    # forecast, stated with its own caveat
    rate = over / len(a)
    elig = (len(cl_e) / len(cl)) if cl else 0.0
    L.append("WHAT THIS IMPLIES FOR THE FIRST READ")
    L.append(f"  band-clear rate {rate*100:.1f}% x eligibility {elig*100:.1f}% = "
             f"{rate*elig*100:.1f}% of graded games become sightings")
    if rate * elig > 0:
        need = FIRST_READ - len(cl_e)
        L.append(f"  {need} more sightings needs about {round(need/(rate*elig)):,} more graded games")
    else:
        L.append(f"  no sightings yet at this rate - cannot project")
    L.append(f"  at AHEAD_DAYS=3 the eligibility term should approach 100%, so the ceiling on the")
    L.append(f"  rate is the band-clear rate of {rate*100:.1f}% - that is the number that decides the lane.")
    L.append(f"  CAVEAT: n={len(rows)}. Every figure here is one small sample, and the band-clear")
    L.append(f"  rate is the one to watch rather than to act on yet.")
    L.append("")

    mae = [(abs(x["num"] - x["final"]), abs(x["open"] - x["final"])) for x in rows
           if x["num"] is not None and x["final"] is not None and x["open"] is not None]
    if mae:
        o = s.mean([m for m, _ in mae])
        p = s.mean([q for _, q in mae])
        L.append(f"MAE vs final (n {len(mae)}): ours {o:.2f} | Pinnacle open {p:.2f} | ours minus open {o-p:+.2f}")
        L.append(f"  (the registered stop is ours more than 1.0 worse, read at {FIRST_READ} sightings)")

    body = "\n".join(L)
    print(f"gap distribution: n {len(rows)} | band-clear {over} | sightings {len(cl_e)} | "
          f"discarded-late {len(cl)-len(cl_e)}")   # Actions log: counts only
    try:
        ex.send("NCAAB GAP DISTRIBUTION (read-only)", body)
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

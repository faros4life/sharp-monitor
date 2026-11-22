#!/usr/bin/env python3
"""Board non-conversion histogram (Peter, Nov 22 2026) - counts-only instrumentation.

The three that must hold: it cannot trade or write, UNKNOWN is never imputed, and nothing
identifying ever reaches a public log.
"""
import inspect
import sys

import executor as ex

FAILED = []
RAN = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


def row(why=None, go=False, rest=None, source="board"):
    live = {"go": go, "lane": "board"}
    if why is not None:
        live["why"] = why
    if rest:
        live["rest"] = rest
    return {"play": {"source": source}, "live": live}


H = ex.board_refusal_histogram


def counts(out):
    d = {}
    for ln in out:
        s = ln.strip()
        if s.startswith(("BOARD", "candidates", "secondary", "HISTORICAL", "do not sum")):
            continue
        if ": " in s and s.split(": ")[-1].isdigit():
            d[s.rsplit(": ", 1)[0]] = int(s.rsplit(": ", 1)[1])
    return d


# --- it cannot trade or write -----------------------------------------------------------------
src = inspect.getsource(H)
for bad, what in (("live_order", "place an order"), ("place(", "call place"), ("rest_bid", "rest a bid"),
                  ("open(", "open a file"), ("json.dump", "write json"), ("= True", "set a flag"),
                  ("tg(", "send a message"), ("push(", "push")):
    ok(f"histogram cannot {what}", bad not in src)
ok("it only reads results", "results" in src and "def board_refusal_histogram(results)" in src)

before = [row(["board lane not switched on (EXEC_BOARD_LIVE)"])]
snapshot = repr(before)
H(before)
ok("calling it does not mutate the rows it reads", repr(before) == snapshot)

# --- categories are mutually exclusive: one row counted exactly once ----------------------------
out = H([row(["board lane not switched on (EXEC_BOARD_LIVE)"])])
c = counts(out)
ok("a single row lands in exactly one primary category", sum(c.values()) == 1, str(c))
ok("lane-off is recognised", c.get("lane/route OFF") == 1, str(c))

for why, want in (
        (["board play cap: 10 already submitted or resting today (ET), cap 10"], "per-lane/global cap"),
        (["board daily risk limit: $2,000.00 already at risk today (ET)"], "per-lane/global cap"),
        (["a live order or resting bid was already sent for this bet (another lane)"], "position/claim stacking"),
        (["CONFLICT: the other side of this game was already bet (first side stays)"], "position/claim stacking"),
        (["no live book has the alert number or better"], "no venue/book at alert line"),
        (["Board V4: confirmation not verified - V3 signal logged, not bet"], "V4 confirmation not met")):
    ok(f"categorised: {want}", counts(H([row(why)])).get(want) == 1, str(counts(H([row(why)]))))

# --- UNKNOWN is never imputed -------------------------------------------------------------------
ok("an unrecognised reason is UNKNOWN, not guessed",
   counts(H([row(["some reason nobody has seen before"])])).get("UNKNOWN / NOT OBSERVED") == 1)
ok("a row with no reason at all is UNKNOWN",
   counts(H([row(None)])).get("UNKNOWN / NOT OBSERVED") == 1)
ok("UNKNOWN is never silently folded into another category",
   "UNKNOWN / NOT OBSERVED" in "\n".join(H([row(["unmatched"])])))

# --- resting is never called expired without terminal evidence -----------------------------------
out = H([row(["x"], rest={"status": "placed"})])
ok("a posted resting order is counted as resting, not refused", "resting placed: 1" in "\n".join(out))
ok("no 'expired' category exists at all", "expired" not in "\n".join(H([row(["x"])])).lower())

# --- attempts vs distinct calls, and the historical gap -------------------------------------------
txt = "\n".join(H([row(["no live book has the alert number or better"])]))
ok("output says these are decision attempts, not distinct calls", "decision attempts" in txt)
ok("output warns against summing across runs", "do not sum across runs" in txt)
ok("output states the historical 43 remain unknown", "HISTORICAL REASONS UNKNOWN" in txt)
ok("output refuses to infer a split for them", "no split is inferred" in txt)

# --- secondary reasons are labelled non-additive --------------------------------------------------
multi = H([row(["no live book has the alert number or better",
                "board play cap: 10 already submitted or resting today (ET), cap 10"])])
t = "\n".join(multi)
ok("secondary reasons are labelled NON-ADDITIVE", "NON-ADDITIVE" in t)
ok("the row still has exactly one primary", counts(multi).get("no venue/book at alert line") == 1)

# --- counts only: nothing identifying can reach the log --------------------------------------------
rich = [row(["no live book has the alert number or better"])]
rich[0]["play"].update({"game": "Lakers @ Celtics", "bet": "Under 225.5 (-110)"})
rich[0]["live"].update({"risk": 220.0, "am": -110, "book": "novig"})
t = "\n".join(H(rich))
for leak in ("Lakers", "Celtics", "225.5", "220", "-110", "novig"):
    ok(f"no leak of {leak!r}", leak not in t)

# --- only board rows are counted --------------------------------------------------------------------
ok("other lanes are not counted", H([row(["x"], source="r1")]) == [])
ok("no board rows means no output at all", H([]) == [])

esrc = open(__file__.replace("test_board_histogram.py", "executor.py"), encoding="utf-8").read()
ok("the histogram is wired into the run output", "board_refusal_histogram(results)" in esrc)
ok("and into the public log", "LOG.extend(_bh)" in esrc)


# --- V4 sub-reason breakdown (Peter, Nov 22, approved) --------------------------------------------
S = ex.board_v4_subreason
ok("V4: missing second-book confirmation",
   S("no second-book confirmation at alert time (status missing)") == "missing second-book confirmation")
ok("V4: evidence missing", S("second-book evidence missing") == "second-book evidence missing or unreadable")
ok("V4: evidence unreadable",
   S("second book failed verification (novig: evidence unreadable)") == "second-book evidence missing or unreadable")
ok("V4: not an independent book",
   S("second book failed verification (kalshi: not an independent known book)")
   == "second book not independent or not a known book")
ok("V4: insufficient depth is decided on the NUMBER",
   S("second book failed verification (novig: size 5000, heavier True, same line True)") == "insufficient depth")
ok("V4: a passing size is NOT called a depth failure",
   S("second book failed verification (novig: size 50000, heavier False, same line True)") != "insufficient depth")
ok("V4: not the heavier side",
   S("second book failed verification (novig: size 50000, heavier False, same line True)") == "not the heavier side")
ok("V4: different line",
   S("second book failed verification (novig: size 50000, heavier True, same line False)")
   == "second book on a different line")
ok("V4: an unrecognised failure returns None (never imputed)", S("something new") is None)
ok("V4: empty returns None", S(None) is None)

def v4row(why, ok_=False):
    r = row(["Board V4: x - V3 signal logged, not bet"])
    r["play"]["board_v4"] = {"ok": ok_, "why": why}
    return r

out = H([v4row("no second-book confirmation at alert time (status missing)")])
t = "\n".join(out)
ok("V4 sub-breakdown is emitted", "V4 failures by sub-reason" in t)
ok("V4 sub-breakdown names the failure", "missing second-book confirmation: 1" in t)
ok("V4 sub-breakdown says the sets are not the same", "NOT the same set" in t)
ok("V4 sub-breakdown warns price is not separable", "never to depth" in t)
ok("an unmatched V4 reason is counted UNKNOWN in the sub-breakdown",
   "UNKNOWN / NOT OBSERVED: 1" in "\n".join(H([v4row("brand new failure text")])))
ok("a V4 PASS contributes nothing to the sub-breakdown",
   "V4 failures by sub-reason" not in "\n".join(H([v4row(None, ok_=True)])))
leaky = v4row("second book failed verification (novig: size 5000, heavier True, same line True)")
t2 = "\n".join(H([leaky]))
for leak in ("novig", "5000", "size 5"):
    ok(f"V4 sub-breakdown does not leak {leak!r}", leak not in t2)

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)

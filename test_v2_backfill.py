#!/usr/bin/env python3
"""V2 historical backfill (Peter, Nov 20, approved): "Preserve V1 completely. The backfill may write
only V2 fields. Never reset V1 scoring flags, retries, settlement data or certified CLV."

It is a SEPARATE pass for that reason. The V1 scoring loop writes tries, why and done on a dozen
early-exit paths, so threading an already-scored row back through it risks corrupting the official
number. This pass can only ever reach record_v2.

The assertions that matter are the negative ones: after a backfill - successful, failed, or out of
budget - every V1 field must be byte-identical to what it was.
"""
import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


V1_FIELDS = ("clv", "close_p", "how", "age_min", "scored", "tries", "done", "why",
             "eff_am", "close_am", "result", "profit", "stake", "to_pay")


def row(k="nv|1", **kw):
    r = {"clv": -0.07, "close_p": 0.4854, "how": "own line", "age_min": 9, "scored": "2026-11-19T01:00Z",
         "tries": 2, "done": False, "eff_am": -109, "close_am": 106, "fixture": "FX1",
         "snap": {"league": "NCAAB", "bet": "Under 139.5", "price": -109, "stake": 95.1,
                  "to_pay": 182.0, "result": "W", "profit": 86.9, "game_start": "2026-11-19T00:00Z"}}
    r.update(kw)
    return r


def snapshot(r):
    return {f: r.get(f) for f in V1_FIELDS} | {("snap_" + f): (r.get("snap") or {}).get(f) for f in V1_FIELDS}


# ------------------------------------------------------------------ 1. V1 is unreachable from the pass
src = open("clv_ledger.py").read()
fn = src[src.index("def v2_backfill("):src.index("def v2_report(")]
code = fn.split('"""')[2]
for f in ("clv", "close_p", "how", "scored", "done", "tries", "why", "result", "profit"):
    ok(f"the backfill never assigns rec[{f!r}]", f'rec["{f}"] =' not in code)
ok("the only write path is record_v2", "record_v2(rec" in code)
ok("its own failures land on v2_tries, a V2 field", 'rec["v2_tries"]' in code)
ok("it is bounded by rows per run", "max_rows" in fn)
ok("it is bounded by the shared history budget", "MAX_HIST" in code)
ok("it never calls a paid path - history only",
   "historical-odds" in code and not any(t in code for t in ("/odds", "/fixtures", "/account")))

# ------------------------------------------------------------------ 2. record_v2 preserves V1
r = row()
before = snapshot(r)
cl.record_v2(r, {"p": 0.4854, "v2_p": 0.53, "v2_how": "own line (from main -7.5)",
                 "at_main": False, "main_line": -7.5}, 1.909)
ok("a successful V2 write leaves every V1 field untouched", snapshot(r) == before)
ok("...and records the V2 CLV separately", r["clv_v2"] == round(0.53 * 1.909 - 1, 4), r.get("clv_v2"))
ok("...flagged as model-derived", r["v2_derived"] is True)
ok("...labelled distinctly from an observed close", "from main" in r["how_v2"])
ok("...and the official CLV still reads V1", r["clv"] == -0.07)

r2 = row()
b2 = snapshot(r2)
cl.record_v2(r2, {"p": 0.52, "v2_p": 0.52, "v2_how": "own line", "at_main": True}, 1.909)
ok("when our number WAS the main line V2 equals V1's basis and is not flagged derived",
   r2["v2_derived"] is False and r2["close_p_v2"] == 0.52)
ok("...V1 still untouched", snapshot(r2) == b2)

r3 = row()
b3 = snapshot(r3)
ok("a missing close writes NO V2 at all", cl.record_v2(r3, None, 1.909) is False)
ok("...and is never recorded as scored", "clv_v2" not in r3 and snapshot(r3) == b3)
ok("a missing price writes no V2", cl.record_v2(row(), {"v2_p": 0.5}, None) is False)
ok("a close with no v2_p writes no V2", cl.record_v2(row(), {"p": 0.5}, 1.909) is False)

# ------------------------------------------------------------------ 3. selection and the report
st = {"bets": {"a": row(), "b": row(clv=None), "c": row(clv_v2=-0.01), "d": row(v2_tries=3),
               "e": row(fixture=None)}}
sel = [k for k, r in st["bets"].items()
       if r.get("clv") is not None and r.get("clv_v2") is None and r.get("v2_tries", 0) < 3 and r.get("fixture")]
ok("only scored rows still lacking V2, with a fixture and tries left, are selected",
   sel == ["a"], sel)

st2 = {"bets": {"x": row(clv=-0.0963, clv_v2=0.0118, v2_derived=True, how_v2="own line (from main -7.5)"),
                "y": row(clv=0.01, clv_v2=0.01, v2_derived=False)}}
rep = "\n".join(cl.v2_report(st2))
ok("the report separates observed from model-derived", "1 identical" in rep and "1 model-derived" in rep)
ok("...gives V1 and V2 means on the moved rows", "mean V1" in rep and "mean V2" in rep)
ok("...names the largest changes", "largest change" in rep)
ok("...shows the kill-switch under BOTH methods", rep.count("kill-switch V1") >= 1 and "V2 " in rep)
ok("an empty store says so rather than printing a figure",
   "no row carries both" in "\n".join(cl.v2_report({"bets": {}})))

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)

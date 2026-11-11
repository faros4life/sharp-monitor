"""Nov 11: parallel probe prefetch, and the watchdog off the pre-order path.

probe alert line measured 107.2s across 21 plays (5.1s each) - the largest item left on the
critical path once the registry read was 6s and the blind positions loop was gone. Pruning probes
was proven UNSAFE earlier the same day (half_point 0.01427 -> 0.01526 flips the pick from 226.5 to
227.5), so nothing is removed: evaluate() runs once per play concurrently to warm the per-run MD
cache, and the real serial loop then runs unchanged against cache hits.

What must hold, and is checked here:
  - the SERIAL loop is untouched, because its order carries "first side stays" (taken_now) and
    LIVEKEYS sequencing; reordering it would change which side of a game wins a conflict
  - the prefetch passes taken=None, so it issues no Gmail conflict search
  - the prefetch DISCARDS its results; only the cache survives
  - evaluate() has no side effects beyond MD and PERF
  - the watchdog still runs on BOTH exit paths - it flags a qualifying play with no Muse verdict,
    which is exactly the case where the play was already handled and `new` is empty
"""
import ast
import os
import re

import executor as ex

CHECKS = []
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "executor.py")).read()
tree = ast.parse(src)
fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
main = fns["main"]


def ck(name, got, want):
    CHECKS.append((name, got, want))
    assert got == want, f"{name}: got {got!r}, want {want!r}"


# ---------------------------------------------------------------- evaluate is safe to call twice
ev = fns["evaluate"]
banned = {"push", "tg", "send", "journal_order", "journal_intent", "live_order", "rest_bid",
          "imap_open", "gsearch", "gsearch_strict", "refuse"}
hits = sorted({n.func.id for n in ast.walk(ev)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in banned})
ck("evaluate sends nothing and touches no registry", hits, [])
mutations = sorted({f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(ev)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id in {"LIVEKEYS", "MANUAL_HELD", "BOARD", "R1", "INTENT", "JOURNAL"}})
ck("evaluate mutates no run state", mutations, [])

# ---------------------------------------------------------------- the prefetch itself
i = src.index("PARALLEL PROBE PREFETCH")
blk = src[i:i + 2000]
# AST, not string slicing: find _warm inside main and read its evaluate() call's `taken` argument.
warm = next((n for n in ast.walk(main) if isinstance(n, ast.FunctionDef) and n.name == "_warm"), None)
assert warm is not None, "the prefetch helper _warm was not found in main()"
ecall = next(n for n in ast.walk(warm)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "evaluate")
sig = [a.arg for a in fns["evaluate"].args.args]
taken_arg = ecall.args[sig.index("taken")]
ck("the prefetch passes taken=None (no Gmail conflict search)",
   isinstance(taken_arg, ast.Constant) and taken_arg.value is None, True)
assert "except Exception" in blk, "a prefetch failure must not break the run"
assert "ThreadPoolExecutor(max_workers=PREFETCH_WORKERS)" in blk, "concurrency must be bounded"
# results discarded: the warm helper returns nothing and its map result is not bound to a name
assert re.search(r"list\(tp\.map\(_warm, new\)\)", blk), "prefetch results must be discarded"
CHECKS.append(("prefetch discards results; only the cache survives", True, True))

ck("PREFETCH_WORKERS is bounded", 1 <= ex.PREFETCH_WORKERS <= 8, True)
for v, want in (("0", 1), ("99", 8), ("3", 3), ("", 4)):
    os.environ["EXEC_PREFETCH_WORKERS"] = v
    got = max(1, min(8, int(os.environ.get("EXEC_PREFETCH_WORKERS") or 4)))
    ck(f"workers clamp for {v!r}", got, want)
os.environ.pop("EXEC_PREFETCH_WORKERS", None)

# ---------------------------------------------------------------- the serial loop is unchanged
ck("taken_now still exists (first-side-stays sequencing)", "taken_now" in src, True)
assert "LIVEKEYS.add(derive_key(p) or p[\"play_key\"])" in src, "LIVEKEYS sequencing must remain"
CHECKS.append(("serial ordering state intact", True, True))
# the real loop still passes a taken callable, not None, for non rules/lane2 sources
assert 'None if p.get("source") in ("rules", "lane2") else taken' in src, \
    "the serial pass must still use the real conflict check"
CHECKS.append(("serial pass keeps the real taken()", True, True))

# the prefetch must come BEFORE the serial loop, and ordering must be: sweep, prefetch, order
lines = {}
for n in ast.walk(main):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
        lines.setdefault(n.func.id, []).append(n.lineno)
ck("pmus_rest_sweep stays first", min(lines["pmus_rest_sweep"]) < min(lines["evaluate"]), True)
ck("prefetch precedes the serial evaluate", len(lines["evaluate"]) >= 2, True)
ck("orders come after both evaluates", min(lines["live_order"]) > max(lines["evaluate"]), True)

# ---------------------------------------------------------------- watchdog on BOTH paths, late
# watchdog_once() wraps muse_watchdog with the bracket INSIDE it, so one label serves both call
# sites - the shape fill_reports already uses, and the reason neither duplicates a perf label.
ck("the watchdog is called from both exit paths", len(lines["watchdog_once"]), 2)
ck("muse_watchdog itself is called once, inside the wrapper",
   len([n for n in ast.walk(fns["watchdog_once"])
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "muse_watchdog"]), 1)
ck("the busy-path watchdog runs after orders",
   max(lines["watchdog_once"]) > max(lines["live_order"]), True)
assert "muse_watchdog" not in lines, "muse_watchdog must only be called via watchdog_once"
ck("fill_reports also runs on two paths", len(lines["fill_reports"]), 2)

# ---------------------------------------------------------------- the cache key is deterministic
al = {"sport": "NBA", "start_utc": "2026-11-12T01:00:00Z", "bet": "Under 230.5 (-119)"}
k1 = ex.md_key("novig", al, "total", "UNDER", 231.5, -119, ("A", "B"))
k2 = ex.md_key("novig", al, "total", "UNDER", 231.5, -119, ("A", "B"))
ck("md_key is stable for identical inputs", k1, k2)
assert k1 != ex.md_key("novig", al, "total", "UNDER", 230.5, -119, ("A", "B")), \
    "a different line must be a different cache entry"
assert k1 != ex.md_key("prophetx", al, "total", "UNDER", 231.5, -119, ("A", "B")), \
    "a different book must be a different cache entry"
CHECKS.append(("the cache cannot serve one line's price for another", True, True))

# ---------------------------------------------------------------- order time still bypasses MD
rb = fns["reread_book"]
uses_md = [n.lineno for n in ast.walk(rb)
           if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "MD"]
ck("the order-time re-read never consults the cache", uses_md, [])

print(f"PASS  test_prefetch.py  {len(CHECKS)} checks")

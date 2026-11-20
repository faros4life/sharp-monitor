#!/usr/bin/env python3
"""our_line restore + the regression guard (Peter, Nov 20, approved item 6).

How the field went missing: three commits shipped in sequence while a scheduled ledger run was in
flight. Run 44711290833 (09:30 UTC) carried the V2 backfill but predated the our_line commit by
about forty seconds of push ordering, and backfilled 79 rows without it. Those rows hold clv_v2, so
the backfill skips them forever - the field could never arrive on its own.

Two failures to prevent, and this file guards both:
  1. a V2 return path that omits our_line, at_main or main_line - the structural cause;
  2. restoring the field from anything other than the row's OWN recorded bet text.

The edits that added our_line were applied with str.replace and NO assertion that they matched.
They happened to land, but a silent no-op was one whitespace away, which is the same class of error
CLAUDE.md already records: a test that passes by not running.
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


# ------------------------------------------------------------------ 1. THE REGRESSION GUARD
src = open("clv_ledger.py").read()
cf = src[src.index("def close_for("):src.index("MAX_NEW_MAIL")]
paths = [ln for ln in cf.splitlines() if '"v2_p"' in ln]
ok("exactly two return paths carry a V2 fair", len(paths) == 2, len(paths))
for field in ("our_line", "at_main", "main_line"):
    n = cf.count(f'"{field}"')
    ok(f"every V2 return path also carries {field}", n == 2, f"{field} appears {n}x, expected 2")
ok("a V2 fair is never returned without the number it was computed for",
   all('"our_line"' in blk for blk in cf.split('"v2_p"')[:-1][1:] or ['"our_line"']))

# ------------------------------------------------------------------ 2. restore from the bet text only
def row(bet, **kw):
    r = {"clv": -0.07, "close_p": 0.48, "clv_v2": -0.02, "close_p_v2": 0.52,
         "snap": {"bet": bet, "flip": False, "league": "NFL"}}
    r.update(kw)
    return r


st = {"bets": {"a": row("IND -2.5"), "b": row("TCU -10"), "c": row("Browns +2 (-110)"),
               "d": row("Under 139.5"), "e": row("Over 225.5")}}
fixed, failed = cl.restore_our_line(st)
ok("every affected row is restored", (fixed, failed) == (5, 0), (fixed, failed))
ok("a negative spread restores its own number", st["bets"]["a"]["our_line"] == -2.5)
ok("a whole-number spread restores", st["bets"]["b"]["our_line"] == -10.0)
ok("a positive spread restores", st["bets"]["c"]["our_line"] == 2.0)
ok("an under restores its total", st["bets"]["d"]["our_line"] == 139.5)
ok("an over restores its total", st["bets"]["e"]["our_line"] == 225.5)

# ------------------------------------------------------------------ 3. it touches nothing else
before = {k: dict(v) for k, v in {"x": row("IND -2.5")}.items()}
st2 = {"bets": {"x": row("IND -2.5")}}
cl.restore_our_line(st2)
r = st2["bets"]["x"]
ok("V1 clv is untouched", r["clv"] == before["x"]["clv"])
ok("V1 close_p is untouched", r["close_p"] == before["x"]["close_p"])
ok("the V2 CLV itself is untouched", r["clv_v2"] == before["x"]["clv_v2"])
ok("only our_line was added", set(r) - set(before["x"]) == {"our_line"}, set(r) - set(before["x"]))

# ------------------------------------------------------------------ 4. it refuses what it cannot verify
st3 = {"bets": {"n": row("Yankees ML"), "m": row(""), "k": row("IND -2.5", our_line=-2.5),
                "j": {"clv": -0.01, "snap": {"bet": "IND -2.5"}}}}
f3, x3 = cl.restore_our_line(st3)
ok("a bet with no line is counted as unrecoverable, never guessed", x3 >= 1, (f3, x3))
ok("...and is left with no our_line", st3["bets"]["n"].get("our_line") is None)
ok("a row that already has our_line is not rewritten", st3["bets"]["k"]["our_line"] == -2.5)
ok("a row with no V2 at all is skipped", "our_line" not in st3["bets"]["j"])

# ------------------------------------------------------------------ 5. validation excludes, never invents
st4 = {"bets": {"p": {"v2_derived": True, "close_p": 0.50, "close_p_v2": 0.54,
                      "our_line": -2.5, "main_line": -5.5, "snap": {"league": "NFL"}},
                "q": {"v2_derived": True, "close_p": 0.50, "close_p_v2": 0.52,
                      "snap": {"league": "NBA"}}}}
rep = "\n".join(cl.v2_validation(st4))
ok("the validation measures derived minus OBSERVED", "derived minus observed" in rep)
ok("a derived row with no our_line is named as unsupported, not silently dropped",
   "UNSUPPORTED" in rep and "excluded" in rep)
ok("thin football data refuses a key-number conclusion", "NOT ENOUGH FOOTBALL" in rep)
ok("an empty set says so rather than printing a figure",
   "no model-derived row" in "\n".join(cl.v2_validation({"bets": {}})))

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)

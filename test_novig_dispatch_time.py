"""Nov 27 (Peter): a Novig order records when the executor handed it to the runner (dispatched_utc); the runner stamps
submitted_utc itself only when it actually sends to Novig. Log fields only - no order logic depends on them."""
import re
src = open("executor.py").read()
fails = 0
def ok(c, m):
    global fails
    print(("  ok   " if c else "  FAIL ") + m); fails += 0 if c else 1
seg = src[src.index('elif book == "novig":'):src.index('res = dict(res, book=book, answered_utc')]
ok("_disp_t = datetime.now(timezone.utc)" in seg and "res = dict(res, dispatched_utc=_disp_t)" in seg,
   "the Novig branch stamps dispatched_utc after the hand-off")
ok("novig_place(ids[\"outcome_id\"], limit_cost, count * 100, label, None, derive_key(p) or \"\")" in seg,
   "the dispatch call itself is unchanged")
ok('"dispatched_utc": lo.get("dispatched_utc")' in src, "the order record carries dispatched_utc")
print("FAILED" if fails else "all passed"); raise SystemExit(1 if fails else 0)

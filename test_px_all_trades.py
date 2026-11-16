"""Synthetic test: tracker_build.px_all_trades follows ProphetX's cursor. No network, no secrets."""
import os, sys
os.environ.setdefault("TRACKER_PASSPHRASE", "synthetic-test-only")
import tracker_build as tb
fails = []
def check(l, c, x=""):
    print(("  ok   " if c else "  FAIL ") + l + (f"  {x}" if x else ""))
    if not c: fails.append(l)
P = {None: {"data": {"trades": [{"id": i} for i in range(100)], "next_cursor": "c1"}},
     "c1": {"data": {"trades": [{"id": i} for i in range(100, 150)], "next_cursor": ""}}}
calls = []
def fake(path):
    calls.append(path)
    cur = path.split("next_cursor=")[1] if "next_cursor=" in path else None
    return P[cur]
tr, pages, done = tb.px_all_trades(fake)
check("both pages read; the old single read stopped at 100", len(tr) == 150 and pages == 2 and done, (len(tr), pages, done))
check("every call is a GET of get_trades", all(c.startswith("/v4/mm/get_trades") for c in calls))
P2 = {None: {"data": {"trades": [{"id": 1}, {"id": 2}], "next_cursor": "c1"}},
      "c1": {"data": {"trades": [{"id": 2}, {"id": 3}], "next_cursor": "c1"}}}
tr, pages, done = tb.px_all_trades(lambda p: P2["c1" if "next_cursor=" in p else None])
check("a repeated trade is kept once and a repeating cursor stops the loop", [t["id"] for t in tr] == [1, 2, 3] and pages == 2)
check("a loop that stops on a repeating cursor is NOT reported complete", done is False)
_n = [0]
def endless(p):
    _n[0] += 1
    return {"data": {"trades": [{"id": _n[0]}], "next_cursor": f"c{_n[0]}"}}
tr, pages, done = tb.px_all_trades(endless, max_pages=3)
check("hitting the page cap is reported TRUNCATED", pages == 3 and done is False)
src = open("tracker_build.py").read()
check("px_live.trades() itself is untouched (execution uses it)", "def trades():" in open("px_live.py").read() and
      '_call("/v4/mm/get_trades")' in open("px_live.py").read())
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_px_all_trades: all passed")

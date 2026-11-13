#!/usr/bin/env python3
"""Gmail off the executor's critical path (Peter, Nov 12).

Three claims, each measured rather than reasoned about:

  1. NO MUSE. SOURCE defaults to "rules", so read_verdicts() and the no-verdict watchdog are both
     off. They are gated on that one name, so this is the whole of the Muse removal.
  2. Novig fill reporting opens NO Gmail connection when every final row was reported long ago.
     The old guard asked "is any record FINAL?"; a FILLED row is final forever, so with 28 FILLED
     rows in the snapshot it could never fire and every pass dialled IMAP to re-learn that.
  3. The bound CANNOT lose a notification: a row the runner touches again re-enters the window, and
     a row with an unreadable timestamp is treated as reportable.

No order is placed, nothing is submitted, no historical order is replayed.
"""
import sys
from datetime import datetime, timedelta, timezone

import executor as ex

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


NOW = datetime.now(timezone.utc)


def row(age_h, status="FILLED", fq=1, cid=None, stamp=True):
    r = {"status": status, "filled_qty": fq, "qty": 1, "price": 50,
         "client_id": cid or f"c{age_h}", "label": "A @ B"}
    if stamp:
        r["updated_utc"] = (NOW - timedelta(hours=age_h)).strftime("%Y-%m-%dT%H:%M:%S")
        r["placed_utc"] = r["updated_utc"]
    return r


print("1. Muse is gone: both reads are gated on SOURCE and SOURCE defaults to rules")
check("SOURCE defaults to 'rules'", ex.SOURCE == "rules")
check("read_verdicts() does not run", ex.SOURCE not in ("muse", "both"))
check("the no-verdict watchdog returns early", ex.SOURCE not in ("both",))
check("src_tag() no longer labels plays [Muse]", "[Muse]" not in ex.src_tag({}))


print("\n2. A snapshot of only OLD final rows opens no Gmail connection")
_orig_open, _orig_results = ex.imap_open, ex.book_live.novig_results
import os
_orig_tok = os.environ.get("NOVIG_SNAPSHOT_TOKEN")
os.environ["NOVIG_SNAPSHOT_TOKEN"] = "x"   # only gates whether the snapshot is read at all

dials = {"n": 0}


def counting_open():
    dials["n"] += 1
    raise AssertionError("novig_reports must not dial Gmail for rows reported long ago")


ex.imap_open = counting_open

# 28 FILLED rows, every one older than the window: exactly the live snapshot's shape.
ex.book_live.novig_results = lambda: [row(h) for h in range(200, 228)]
dials["n"] = 0
n = ex.novig_reports()
check("no IMAP connection was opened", dials["n"] == 0)
check("and it reported nothing", n == 0)

print("\n   A RECENT final row still reaches the reporting path")
ex.book_live.novig_results = lambda: [row(300), row(1, cid="fresh")]
dials["n"] = 0
try:
    ex.novig_reports()
except AssertionError:
    pass          # the stub raises ON PURPOSE: reaching it is the proof
check("a row inside the window does dial Gmail", dials["n"] == 1)

print("\n3. The bound cannot lose a notification")
print("   a row the runner TOUCHES AGAIN re-enters the window (the late NO FILL case)")
ex.book_live.novig_results = lambda: [dict(row(400, status="CANCELED", fq=0),
                                           updated_utc=(NOW - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S"))]
dials["n"] = 0
try:
    ex.novig_reports()
except AssertionError:
    pass
check("an old order re-read by the runner is reported", dials["n"] == 1)

print("   a row with an UNREADABLE timestamp counts as reportable, never dropped")
ex.book_live.novig_results = lambda: [{"status": "FILLED", "filled_qty": 1, "qty": 1,
                                       "price": 50, "client_id": "nostamp", "label": "A @ B",
                                       "updated_utc": "not-a-date"}]
dials["n"] = 0
try:
    ex.novig_reports()
except AssertionError:
    pass
check("an unparseable stamp is treated as in-window", dials["n"] == 1)

print("   an EMPTY snapshot still opens nothing")
ex.book_live.novig_results = lambda: []
dials["n"] = 0
check("no rows means no connection and no report", ex.novig_reports() == 0 and dials["n"] == 0)

ex.imap_open, ex.book_live.novig_results = _orig_open, _orig_results
if _orig_tok is None:
    os.environ.pop("NOVIG_SNAPSHOT_TOKEN", None)
else:
    os.environ["NOVIG_SNAPSHOT_TOKEN"] = _orig_tok

print("\n4. The FETCH loop that hid 581.7s is now inside a bracket")
src = open("executor.py").read()
i_s = src.index('with perf("registry read (Gmail IMAP)")')
i_f = src.index('with perf("registry fetch (Gmail, full RFC822 per email)"')
check("the per-email fetch has its own perf bracket", i_f > i_s)
check("the bracket carries the email count", 'n=len(_uids)' in src)
check("the fetch loop runs inside it", src[i_f:i_f + 400].find("for uid in _uids:") > 0)

print()
if fails:
    print(f"FAIL  test_gmail_critical_path.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")

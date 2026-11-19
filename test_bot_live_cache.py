#!/usr/bin/env python3
"""bot Novig order retrieval (Peter, Nov 19): "The ledger spends 807 seconds in bot Novig orders.
Identify the exact blocking operation and eliminate unnecessary waiting, retries or repeated
retrieval. Preserve complete order and fill evidence. Never treat timeout or missing data as zero
fills."

Measured on run 44557449390: the stage marker printed at 15:42:54.79 and the next line at
15:56:21.15 - 806.4 s with no output, 95% of a 850 s run. The blocking operation is this function:
it searched 45 days of "Bets LIVE:" mail and FETCHed every match IN FULL, every run. The executor
sends one of those per pass, so the same thousands of messages were re-downloaded serially each
time, and the read aborted part-way.

An IMAP message is immutable once delivered, so a UID parsed once never needs fetching again.

The assertion that matters most is the negative one: a dropped connection must NOT turn into an
empty order list. Missing data is not evidence of zero fills - that mistake would silently
undercount the daily stop.
"""
import json

import clv_ledger as cl

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


ROW = [{"key": "NBA|Heat @ Celtics|total|under", "decided_utc": "2026-11-18T23:00:00Z",
        "live_px_line": 220.5, "live_px_price_after_fee": -110,
        "live_order": {"status": "placed", "order_id": "o%s", "book": "novig"},
        "books_at_decision": {"novig": {"p": 0.5}}}]


def raw_for(uid, subject="Bets LIVE: order"):
    return ("Subject: " + subject + "\r\n\r\nbody").encode()


def body_for(uid):
    return "LEDGER (machine-readable)\n" + json.dumps(
        [dict(r, live_order=dict(r["live_order"], order_id=f"o{uid}")) for r in ROW])


class FakeM:
    def __init__(self, uids, fail_on=None, uidvalidity=b"777"):
        self.uids, self.fail_on, self.uidvalidity = uids, fail_on, uidvalidity
        self.fetched = []
        self.closed = False

    def response(self, key):
        return (key, [self.uidvalidity])

    def uid(self, cmd, uid, spec):
        k = uid.decode() if isinstance(uid, bytes) else str(uid)
        self.fetched.append(k)
        if self.fail_on == k:
            raise OSError("connection reset by peer")
        return ("OK", [(b"hdr", raw_for(k))])


def run(uids, cache, fail_on=None, uidvalidity=b"777", subject="Bets LIVE: order", max_new=None):
    M = FakeM(uids, fail_on, uidvalidity)
    real = (cl.ex.imap_open, cl.ex.gsearch, cl.ex.imap_close, cl.ex.body_text)
    cl.ex.imap_open = lambda: M
    cl.ex.gsearch = lambda _M, _q: list(uids)
    cl.ex.imap_close = lambda _M: setattr(M, "closed", True)
    cl.ex.body_text = lambda raw: body_for(
        raw.decode().split("\r\n\r\n")[0].replace("Subject: ", "")) if False else body_for("x")
    # body_text keyed off the uid actually fetched:
    cl.ex.body_text = lambda raw, _M=M: body_for(_M.fetched[-1])
    if subject != "Bets LIVE: order":
        cl.ex.imap_open = lambda: M
        M_raw = raw_for("1", subject)
        M.uid = lambda cmd, uid, spec, _r=M_raw, _M=M: (_M.fetched.append(
            uid.decode() if isinstance(uid, bytes) else str(uid)), ("OK", [(b"h", _r)]))[1]
    try:
        return cl.bot_novig_orders(cache=cache, max_new=max_new), M
    finally:
        cl.ex.imap_open, cl.ex.gsearch, cl.ex.imap_close, cl.ex.body_text = real


# ------------------------------------------------------------------ 1. fetch once, ever
cache = {}
(out, note), M = run([b"1", b"2", b"3"], cache)
ok("a first run fetches every message", M.fetched == ["1", "2", "3"], M.fetched)
ok("a first run returns an order per message", len(out) == 3, len(out))
ok("a clean read carries no note", note is None, note)
ok("the parsed rows are cached by UID", sorted(cache["uids"]) == ["1", "2", "3"], sorted(cache["uids"]))

(out2, note2), M2 = run([b"1", b"2", b"3"], cache)
ok("a second run fetches NOTHING - this is the 807 seconds", M2.fetched == [], M2.fetched)
ok("...and still returns every order", len(out2) == 3, len(out2))
ok("the counters report the saving", cache["seen_last_run"] == 3 and cache["fetched_last_run"] == 0,
   (cache.get("seen_last_run"), cache.get("fetched_last_run")))

(out3, _), M3 = run([b"1", b"2", b"3", b"4"], cache)
ok("only the new message is fetched on a later run", M3.fetched == ["4"], M3.fetched)
ok("...and the full set is returned", len(out3) == 4, len(out3))

# ------------------------------------------------------------------ 2. a failed read is never zero
(out4, note4), M4 = run([b"1", b"2", b"3", b"4", b"5"], cache, fail_on="5")
ok("a dropped connection does NOT empty the result", len(out4) == 4, len(out4))
ok("...and says the read was partial", note4 and "partial read" in note4, note4)
ok("...naming the failure type", note4 and "OSError" in note4, note4)
ok("the failed UID is not cached as empty", "5" not in cache["uids"], sorted(cache["uids"]))
(out5, note5), _ = run([b"1", b"2", b"3", b"4", b"5"], cache)
ok("the failed UID is retried on the next run and recovers", len(out5) == 5 and note5 is None, (len(out5), note5))

cold = {}
(out6, note6), _ = run([b"1"], cold, fail_on="1")
ok("a cold cache that fails returns empty WITH a note, never a silent zero",
   out6 == [] and note6 is not None, (out6, note6))

# ------------------------------------------------------------------ 3. UIDVALIDITY and pruning
reused = dict(cache)
(out7, _), M7 = run([b"1", b"2"], reused, uidvalidity=b"999")
ok("a UIDVALIDITY change drops the whole cache - UIDs are only unique within one",
   M7.fetched == ["1", "2"], M7.fetched)
ok("...and the new validity is recorded", reused["uidvalidity"] == "999", reused.get("uidvalidity"))

pruned = {}
run([b"1", b"2", b"3"], pruned)
run([b"2", b"3"], pruned)
ok("UIDs that fall outside the search window are pruned, so the cache is bounded",
   sorted(pruned["uids"]) == ["2", "3"], sorted(pruned["uids"]))

# ------------------------------------------------------------------ 4. the substring trap still guarded
src = open("clv_ledger.py").read()
fn = src[src.index("def _bot_live_rows("):src.index("def order_as_bet(")]
ok("the real Subject header prefix is still re-checked (IMAP SUBJECT search is a substring match)",
   'startswith("Bets LIVE:")' in fn)
ok("the ledger JSON is still found with rfind + raw_decode, not a second invented way",
   'rfind("LEDGER (machine-readable")' in fn and "raw_decode" in fn)
ok("only placed orders with an order_id are collected",
   'lo.get("status") != "placed" or not lo.get("order_id")' in fn)

caller = src[src.index("_stage(\"bot novig orders\")"):src.index('_stage("league fixture list")')]
ok("the caller says plainly that a failed read is not zero fills",
   "NOT evidence of zero fills" in caller and "NOT read as zero fills" in caller)
ok("the caller still records the error for the ledger's error tail",
   'novig orders:' in caller and "errors" in caller)

# ------------------------------------------------------------------ 5. the per-run fetch cap
# Peter, Nov 19: "Limit uncached email fetches per run so a timeout cannot repeatedly restart a full
# 1,902-message download. Save cache progress between batches so completed work survives."
capped = {}
(outc, notec), Mc = run([b"1", b"2", b"3", b"4", b"5"], capped, max_new=2)
ok("a cold cache fetches only the capped number", Mc.fetched == ["1", "2"], Mc.fetched)
ok("...and says the read is capped, not clean", notec and "capped at 2" in notec, notec)
ok("...naming how many are still uncached", notec and "3 still uncached" in notec, notec)
ok("a deferred UID is NOT cached as empty - it is simply not yet read",
   sorted(capped["uids"]) == ["1", "2"], sorted(capped["uids"]))
ok("the capped run still returns the orders it did parse", len(outc) == 2, len(outc))

(outc2, _), Mc2 = run([b"1", b"2", b"3", b"4", b"5"], capped, max_new=2)
ok("the next run resumes where it stopped - progress survived", Mc2.fetched == ["3", "4"], Mc2.fetched)
ok("...and never re-fetches what is already cached", "1" not in Mc2.fetched and "2" not in Mc2.fetched)
(outc3, notec3), Mc3 = run([b"1", b"2", b"3", b"4", b"5"], capped, max_new=2)
ok("a cold cache converges to complete over successive runs",
   Mc3.fetched == ["5"] and len(outc3) == 5 and notec3 is None, (Mc3.fetched, len(outc3), notec3))
(outc4, _), Mc4 = run([b"1", b"2", b"3", b"4", b"5"], capped, max_new=2)
ok("once full, a run fetches nothing at all", Mc4.fetched == [], Mc4.fetched)

ok("the cap defaults to a bounded constant, not unlimited",
   isinstance(cl.MAX_NEW_MAIL, int) and 0 < cl.MAX_NEW_MAIL < 2000, cl.MAX_NEW_MAIL)
ok("the cap is small enough to finish well inside the 60-minute timeout at ~0.73 s a message",
   cl.MAX_NEW_MAIL * 0.73 < 1800, cl.MAX_NEW_MAIL * 0.73)

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)

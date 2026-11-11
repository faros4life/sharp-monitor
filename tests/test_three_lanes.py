"""The complete three-lane live system: Phase 1 + Board v3 + R1 (Peter, Nov 11).

Each lane has its OWN unit, play cap and daily risk limit, and all three sit UNDER one global
$2,250 stop and one $415 per-order guard. These tests pin that the lanes are independent where
they must be and shared where they must be.

R1's qualification rules are NOT touched here: its negative provisional CLV is unverified and
Peter instructed that it must not change the rules.
"""
import inspect
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import agree_rules  # noqa: E402
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


# ---------------------------------------------------------------- the three lanes exist, separately
ck("R1 has its own money switch, default off", ex.R1_LIVE is False)
ck("Board v3 has its own money switch, default off", ex.BOARD_LIVE is False)
ck("the switches are distinct env vars",
   "EXEC_R1_LIVE" in inspect.getsource(ex) and "EXEC_BOARD_LIVE" in inspect.getsource(ex))
ck("R1 unit is $200", ex.R1_UNIT == 200.0)
ck("Board v3 unit is $200", ex.BOARD_UNIT == 200.0)
ck("Phase 1 unit is still $300", ex.LIVE_UNIT == 300.0)
ck("R1 cap is 10 plays/day", ex.R1_MAX_PLAYS == 10)
ck("R1 daily risk limit is $1,500", ex.R1_DAILY_RISK == 1500.0)
ck("Board v3 cap and limit unchanged", ex.BOARD_MAX_PLAYS == 10 and ex.BOARD_DAILY_RISK == 1500.0)
ck("the lanes keep SEPARATE exposure stores", ex.R1 is not ex.BOARD)
for store, nm in ((ex.R1, "R1"), (ex.BOARD, "Board v3")):
    ck(f"{nm} store has risk/keys/known", set(store) == {"risk", "keys", "known"}, str(set(store)))

# ---------------------------------------------------------------- sizing is per lane
ck("unit_for routes r1 to $200", ex.unit_for("r1") == 200.0)
ck("unit_for routes board to $200", ex.unit_for("board") == 200.0)
ck("unit_for routes everything else to $300", ex.unit_for(None) == 300.0 and ex.unit_for("rules") == 300.0)
ck("R1 $200-to-win at -110 risks $220", ex.live_stake(-110, ex.R1_UNIT) == (220.0, 200.0))
ck("R1 risks $200 at +140", ex.live_stake(140, ex.R1_UNIT) == (200.0, 280.0))
ck("Phase 1 sizing is untouched by the new lane", ex.live_stake(-110, ex.LIVE_UNIT) == (330.0, 300.0))

# ---------------------------------------------------------------- each lane's own gate fails closed
ex.R1.update(risk=0.0, keys=set(), known=False)
ck("R1 gate refuses when exposure is unknown", ex.r1_gate(100.0, "k")[0] is False)
ck("  and says so", "unknown" in ex.r1_gate(100.0, "k")[1].lower())
ex.R1.update(known=True)
ck("R1 gate allows a first play", ex.r1_gate(220.0, "k1")[0] is True)
ex.R1.update(risk=1400.0, keys={f"k{i}" for i in range(3)}, known=True)
ck("R1 refuses a play that would breach $1,500", ex.r1_gate(220.0, "new")[0] is False)
ck("  and names the daily limit", "daily risk" in ex.r1_gate(220.0, "new")[1].lower())
ex.R1.update(risk=0.0, keys={f"k{i}" for i in range(10)}, known=True)
ck("R1 refuses an 11th play", ex.r1_gate(220.0, "new")[0] is False)
ck("  but a retry of an EXISTING key does not count as an 11th", ex.r1_gate(220.0, "k3")[0] is True)
ex.R1.update(risk=0.0, keys=set(), known=False)

# the two lanes do not consume each other's budget
ex.R1.update(risk=1499.0, keys=set(), known=True)
ex.BOARD.update(risk=0.0, keys=set(), known=True)
ck("R1 near its limit does NOT block Board v3", ex.board_gate(220.0, "b1")[0] is True)
ex.BOARD.update(risk=1499.0, keys=set(), known=True)
ex.R1.update(risk=0.0, keys=set(), known=True)
ck("Board v3 near its limit does NOT block R1", ex.r1_gate(220.0, "r1a")[0] is True)
ex.R1.update(risk=0.0, keys=set(), known=False)
ex.BOARD.update(risk=0.0, keys=set(), known=False)

# ---------------------------------------------------------------- one GLOBAL stop over all three
ck("the global stop is $2,250", ex.px_live.DAILY_STOP == 2250.0)
ck("the per-order guard is $415", ex.px_live.MAX_ORDER == 415.0)
pf = inspect.getsource(ex.px_live.preflight)
ck("every order passes the global stop", "DAILY_STOP" in pf)
ck("the global stop counts non-ProphetX lanes too", "OTHER" in pf or "other" in pf)
ck("an unreadable registry refuses globally (returns False)",
   "registry unknown" in pf and "return False" in pf)
pl = inspect.getsource(ex.px_live.place)
ck("the per-order guard is enforced inside place()", "MAX_ORDER" in pl)
ck("place() runs preflight on EVERY order, whatever the lane", "preflight()" in pl)
bl = inspect.getsource(ex.book_live.preflight)
ck("the exchange lanes share the same global preflight", "px_live.preflight()" in bl)
# the stop is not per lane: three lanes at their own limits still answer to one number
ck("three lanes' own limits can exceed the global stop, so the stop must bind",
   ex.R1_DAILY_RISK + ex.BOARD_DAILY_RISK > ex.px_live.DAILY_STOP,
   f"{ex.R1_DAILY_RISK}+{ex.BOARD_DAILY_RISK} vs {ex.px_live.DAILY_STOP}")

# ---------------------------------------------------------------- shared safety applies to R1
mb = inspect.getsource(ex.main)
r1_blk = mb[mb.index('elif p.get("source") == "r1"'):]
r1_blk = r1_blk[:r1_blk.index("elif ent and")]
ck("R1 is off unless its switch is on", "R1_LIVE" in r1_blk)
ck("R1 blocks a bet already live in another lane", "LIVEKEYS" in r1_blk and "same_bet(lk, k)" in r1_blk)
ck("R1 blocks the opposite side across lanes", "opp_bet(lk, k)" in r1_blk)
ck("R1 respects Peter's manual positions", "MANUAL_HELD" in r1_blk)
ck("R1 sizes on its own unit", "R1_UNIT" in r1_blk)
ck("R1 passes its own gate", "r1_gate(" in r1_blk)
ck("R1 marks its lane", '"lane": "r1"' in r1_blk)

ev = inspect.getsource(ex.evaluate)
ck("R1 gets the alert-line floor (original line or strictly better)",
   '"r1"' in ev and "floor = line" in ev)
lo = inspect.getsource(ex.live_order)
for need, what in (("journal_latch_why()", "journal latch"), ("revalidate(r", "venue revalidation"),
                   ("journal_intent(", "write-ahead record"), ("live_guards()", "registry + intents")):
    ck(f"R1 inherits {what} (lane-agnostic in live_order)", need in lo)
ck("the order dispatch is lane-agnostic, so R1 cannot bypass it",
   'r["live"]["order"] = live_order(r)' in mb)
ck("R1 orders are journalled with their lane",
   '"source": p.get("source")' in inspect.getsource(ex.journal_intent))
ck("the ledger separates R1 rows", '"source": p.get("source")' in inspect.getsource(ex.ledger_row))
ck("R1 exposure is rebuilt from the ledger each run",
   'row.get("source") == "r1"' in inspect.getsource(ex.bot_orders))
ck("R1 best-exchange routing uses the shared ranking (no tolerance in the key)",
   "tol" not in [l for l in ev.splitlines() if l.strip().startswith("c_eq =")][0])
ck("R1 uses the same 2c tolerance venues", ex.TOL_BOOKS == ("prophetx", "novig"))
ck("R1 respects the -130 cap", ex.CAP_LINE == -130)

# ---------------------------------------------------------------- notifications and reporting
ck("phone alerts name the lane", ex.lane_tag({"live": {"lane": "r1"}}) == "[R1] "
   and ex.lane_tag({"live": {"lane": "board"}}) == "[Board v3] "
   and ex.lane_tag({"live": {}}) == "")
for fn, nm in ((ex.live_order, "live_order"), (ex.live_order_other, "live_order_other")):
    s = inspect.getsource(fn)
    ck(f"{nm} tags fills with the lane", "lane_tag(r)}FILLED" in s)
    ck(f"{nm} tags errors with the lane", "lane_tag(r)}LIVE ORDER ERROR" in s)
    ck(f"{nm} tags no-fills with the lane", "lane_tag(r)}NO FILL" in s)
ex.R1.update(risk=220.0, keys={"k1"}, known=True)
ex.BOARD.update(risk=0.0, keys=set(), known=True)
rep = ex.lane_report([{"play": {"source": "r1"}, "live": {"lane": "r1", "order": {"status": "placed"}}}])
ck("the run report has a per-lane section", "LANES" in rep)
ck("  naming all three lanes", all(n in rep for n in ("Phase 1", "Board v3", "R1")))
ck("  with each lane's own cap and limit", "/10 plays" in rep and "1,500" in rep)
ck("  and the global stop stated separately", "2,250" in rep and "ON TOP" in rep)
ck("  marking a lane LIVE or OFF", "OFF" in rep)
ex.R1.update(risk=0.0, keys=set(), known=False)
ex.BOARD.update(risk=0.0, keys=set(), known=False)
ck("the report is wired into the email body", "lane_report(results)" in mb)

# ---------------------------------------------------------------- the switch actually reaches the code
wf = open(os.path.join(ROOT, ".github/workflows/executor-dry-run.yml")).read()
for v in ("EXEC_R1_LIVE", "EXEC_R1_DAILY_RISK", "EXEC_R1_MAX_PLAYS"):
    ck(f"the workflow passes {v} (a variable the code never sees is a silent no-op)",
       re.search(rf"{v}:\s*\$\{{\{{\s*vars\.{v}", wf) is not None)
ck("EXEC_R1_LIVE defaults to off in the workflow", "vars.EXEC_R1_LIVE || 'off'" in wf)

# ---------------------------------------------------------------- R1 qualification rules untouched
ck("R1 qualification lives in agree_rules.r1", hasattr(agree_rules, "r1"))
r1src = inspect.getsource(agree_rules.r1)
ck("  it is ProphetX-priced", "prophetx" in r1src.lower())
ck("  non-Top-25", "top25" in r1src.lower())
ck("  has a lead-time requirement", "lead" in r1src.lower() or "hours" in r1src.lower())
ck("  has an after-fee price bar", "price_after_fee" in r1src or "119" in r1src)
ck("r1_plays takes the FIRST alert per game+market+side only",
   "seen" in inspect.getsource(ex.r1_plays))

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)

"""Three-lane Telegram labelling and no-duplicate rule (Peter, Nov 11).

Every notification must say which lane fired - [PHASE 1], [BOARD V3], [R1] - and carry the game,
bet, line, execution odds AFTER FEES, exchange, stake, fill status and order id. Partial fills,
cancellations, rejections and errors are labelled too. Exactly one Telegram message per event.
"""
import inspect
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


def play(lane, src, bk="novig", am=-117, risk=234.0, win=200.0):
    return {"play": {"sport": "NCAAF", "game": "Army @ Navy", "bet": "Under 44.5 (-115)", "source": src},
            "live": {"lane": lane, "book": bk, "line": 44.5, "am": am, "risk": risk, "to_win": win}}


def placed(bk="novig", am=-117, asked=234.0, filled=234.0, oid="NV-7781"):
    return {"status": "placed", "order_id": oid, "book": bk, "asked_stake": asked,
            "filled_stake": filled, "avg_price": am}


# ---------------------------------------------------------------- the three labels, exactly
ck("R1 label", ex.lane_tag(play("r1", "r1")) == "[R1] ")
ck("Board v3 label is UPPERCASE", ex.lane_tag(play("board", "board")) == "[BOARD V3] ")
ck("Phase 1 is LABELLED, not blank", ex.lane_tag(play(None, "rules")) == "[PHASE 1] ")
ck("a play with no lane and no source still labels as Phase 1",
   ex.lane_tag({"play": {}, "live": {}}) == "[PHASE 1] ")
ck("an unknown lane falls back to Phase 1 rather than printing nothing",
   ex.lane_tag({"play": {"source": "weird"}, "live": {"lane": "weird"}}) == "[PHASE 1] ")
ck("the lane comes from live.lane first, then the play source",
   ex.lane_of({"play": {"source": "r1"}, "live": {}}) == "r1"
   and ex.lane_of({"play": {"source": "rules"}, "live": {"lane": "board"}}) == "board")

# ---------------------------------------------------------------- every required field
n = ex.lane_note(play("r1", "r1"), "FILLED", placed(), "novig", -117)
for needle, what in (("[R1]", "lane"), ("Army @ Navy", "game"), ("Under 44.5", "bet"),
                     ("44.5", "line"), ("-117 after fees", "execution odds after fees"),
                     ("Novig", "exchange"), ("$234.00", "stake"), ("fill: FULL", "fill status"),
                     ("NV-7781", "order id")):
    ck(f"notification carries the {what}", needle in n, n)
ck("it also states what the stake wins", "to win $200.00" in n, n)
ck("and the line actually taken", "took:" in n, n)

# ---------------------------------------------------------------- every state, labelled
for lane, src, tag in (("r1", "r1", "[R1]"), ("board", "board", "[BOARD V3]"), (None, "rules", "[PHASE 1]")):
    r = play(lane, src)
    full = ex.lane_note(r, "FILLED", placed(), "novig", -117)
    part = ex.lane_note(r, "FILLED", placed(filled=90.0), "novig", -117)
    none = ex.lane_note(r, "NO FILL", placed(filled=0), "novig", -117)
    unk = ex.lane_note(r, "FILLED", placed(filled=None), "novig", -117)
    ref = ex.lane_note(r, "ORDER REFUSED", {"status": "refused", "reason": "daily stop hit"}, "novig", -117,
                       extra="daily stop hit")
    err = ex.lane_note(r, "ORDER ERROR", {"status": "error", "reason": "HTTP 500"}, "novig", -117,
                       extra="HTTP 500")
    for txt, what in ((full, "full fill"), (part, "partial fill"), (none, "no fill"),
                      (unk, "unknown fill"), (ref, "refusal"), (err, "error")):
        ck(f"{tag} {what} is lane-labelled", txt.startswith(tag), txt.splitlines()[0])
    ck(f"{tag} partial fill is LABELLED PARTIAL", "fill: PARTIAL $90.00 of $234.00" in part, part)
    ck(f"{tag} no fill says NONE", "fill: NONE" in none, none)
    ck(f"{tag} unknown fill is counted in full, not assumed", "UNKNOWN" in unk, unk)
    ck(f"{tag} refusal carries the reason", "daily stop hit" in ref, ref)
    ck(f"{tag} error carries the reason", "HTTP 500" in err, err)
    ck(f"{tag} a refusal does not claim an order id", "order id: none" in ref, ref)

# ---------------------------------------------------------------- wired at every order site
for fn, nm in ((ex.live_order, "live_order"), (ex.live_order_other, "live_order_other")):
    s = inspect.getsource(fn)
    for state in ("FILLED", "NO FILL", "ORDER ERROR"):
        ck(f"{nm} sends a lane note on {state}", f'lane_note(r, "{state}"' in s)
    ck(f"{nm} sends no bare tg() f-string for an order state",
       not re.search(r'tg\(f"\{lane_tag\(r\)\}(FILLED|NO FILL|LIVE ORDER ERROR)', s))
ck("a REFUSAL is notified too", 'lane_note(r, "ORDER REFUSED"' in inspect.getsource(ex.live_order))
rb = inspect.getsource(ex.rest_bid)
ck("resting bids are lane-labelled", "lane_tag(r)}RESTING BID" in rb)
ck("resting errors are lane-labelled", "lane_tag(r)}RESTING BID ERROR" in rb)

# cancellations: the lane is recorded at write time and read back
pr = inspect.getsource(ex.pmus_rest_note)
ck("a resting record stores its lane", "lane" in pr and "PMUSREST {order_id} {slug}" in pr)
sw = inspect.getsource(ex.pmus_rest_sweep)
ck("the cancel path parses the lane back", "rest_lane" in sw)
ck("  tolerating records written before lanes existed", 'm.group(4) or ""' in sw)
ck("  and labels the cancellation",
   "CANCELLED' if ok else 'CANCEL FAILED'" in sw and "rest_lane" in sw)
ck("the resting record is written with the play's lane", "lane_of(r)" in rb)

# ---------------------------------------------------------------- no duplicate notifications
src = inspect.getsource(ex)
pushes = re.findall(r"push\((?:\"|')([^\"']{0,40})[^)]*?\)", src)
ck("push() mirrors to Telegram by default", "def push(title, body, mirror=True)" in src)
for fn, nm in ((ex.live_order, "live_order"), (ex.live_order_other, "live_order_other")):
    s = inspect.getsource(fn)
    for m in re.finditer(r"push\(", s):
        seg = s[m.start():m.start() + 400]
        ck(f"{nm}: every push alongside a lane note is mirror=False (no double Telegram)",
           "mirror=False" in seg, seg.splitlines()[0])
ck("the cancel path's push is non-mirrored (its tg already said it)",
   'push("PM US cancel FAILED"' in src and "mirror=False" in src)

# ---------------------------------------------------------------- three-lane exposure, together
ck("global stop is shared at $3,000", ex.px_live.DAILY_STOP == 3000.0)
ck("per-order guard is shared at $415", ex.px_live.MAX_ORDER == 415.0)
ck("Board v3 and R1 each allow $2,000", ex.BOARD_DAILY_RISK == 2000.0 and ex.R1_DAILY_RISK == 2000.0)
ck("so the two new lanes together could ask for more than the global stop allows",
   ex.BOARD_DAILY_RISK + ex.R1_DAILY_RISK > ex.px_live.DAILY_STOP)
ck("every lane's order runs the one global preflight",
   "preflight()" in inspect.getsource(ex.px_live.place)
   and "px_live.preflight()" in inspect.getsource(ex.book_live.preflight))
ck("the global stop refuses on an unreadable registry",
   "registry unknown" in inspect.getsource(ex.px_live.preflight))
for store, gate, nm in ((ex.BOARD, ex.board_gate, "Board v3"), (ex.R1, ex.r1_gate, "R1")):
    store.update(risk=0.0, keys=set(), known=False)
    ck(f"{nm} refuses when its own exposure is unknown", gate(100.0, "k")[0] is False)
    store.update(risk=1500.0, keys=set(), known=True)
    ck(f"{nm} refuses at its own limit", gate(1.0, "k")[0] is False)
    store.update(risk=0.0, keys=set(), known=False)
ck("units: Phase 1 $300, Board v3 $200, R1 $200",
   (ex.LIVE_UNIT, ex.BOARD_UNIT, ex.R1_UNIT) == (300.0, 200.0, 200.0))
ck("caps: 10 plays each for the new lanes", ex.BOARD_MAX_PLAYS == 10 and ex.R1_MAX_PLAYS == 10)
ck("both new lanes default OFF", ex.BOARD_LIVE is False and ex.R1_LIVE is False)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)

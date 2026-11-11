"""Write-ahead order record: durable ProphetX attribution and cross-run reconciliation.

MEASURED (px_live, Nov 10, 100 real trades): a ProphetX trade carries fee, id, matched_at,
order_id, price, profit, quantity, status, strike, strike_id, winning_status. external_id is NOT
among them, so no venue-recoverable bot identifier exists. The record therefore becomes a
PRECONDITION of the order instead of a consequence: write first, submit only if the write stored.

Peter's five confirmations are the five sections below.
"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import executor as ex  # noqa: E402

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


SENT = []


def stub(send=None, readable=True):
    ex.send = send or (lambda s, b: SENT.append((s, b)))
    ex.tg = lambda *a, **k: None
    ex.intent_readable = lambda cid, **k: readable   # read-back stubbed; its own suite covers it


def rowof(body):
    i = body.rfind("LEDGER (machine-readable")
    return json.JSONDecoder().raw_decode(body[body.index("[", i):])[0][0]


_send, _tg, _rb = ex.send, ex.tg, ex.intent_readable

# ---------------------------------------------------------------- the intent row itself
SENT.clear(); stub()
ok, cid = ex.journal_intent({"play": {"play_key": "K1", "source": "board"}}, "prophetx", 390.0)
ck("intent is written", ok and bool(cid))
ck("one email", len(SENT) == 1)
subj, body = SENT[0]
ck("subject is readable by bot_orders ('Bets LIVE:')", subj.startswith("Bets LIVE:"), subj)
row = rowof(body)
lo = row["live_order"]
ck("row is marked as an intent", row["intent"] is True and lo["intent"] is True)
ck("row carries a client_id", row["client_id"] == cid and lo["client_id"] == cid)
ck("row carries the play key (duplicate blocking)", row["key"] == "K1")
ck("row carries the asked stake (the daily stop counts it)", lo["asked_stake"] == 390.0)
ck("status is 'placed' so bot_orders COUNTS it (conservative)", lo["status"] == "placed")
ck("filled_stake is unknown, not assumed", lo["filled_stake"] is None)
ck("order_id is unique and marked", lo["order_id"] == "intent-" + cid)
# This assertion previously REQUIRED the clearing token in the intent's own body - which was
# the self-clearing bug. The body must NOT be able to clear the intent it describes.
ck("the body cannot clear the intent it describes",
   (ex.INTENT_CLEAR_PREFIX + " " + cid) not in body and "intentdone" not in body)
ck("two intents get different client ids",
   ex.journal_intent({"play": {}}, "prophetx", 1.0)[1] != cid)

# ---------------------------------------------------------------- 1. a lost order cannot exceed limits
# bot_orders' own accounting, replayed: an intent with no confirmation still consumes risk and a play slot.
def account(rows):
    seen, risk, keys, intents, confirmed = set(), 0.0, set(), {}, {}
    for r_ in rows:
        for is_rest, lo_ in ((False, r_.get("live_order") or {}), (True, r_.get("live_rest") or {})):
            if lo_.get("status") != "placed" or not lo_.get("order_id"):
                continue
            c = lo_.get("client_id")
            if c:
                (intents if lo_.get("intent") else confirmed)[str(c)] = r_
            k = str(c or lo_["order_id"])
            if k in seen:
                continue
            seen.add(k)
            if r_.get("key"):
                keys.add(r_["key"])
            fs = lo_.get("filled_stake")
            risk += max(float(fs or 0), float(lo_.get("asked_stake") or 0)) if (is_rest or fs is None) else float(fs)
    return risk, keys, {k: v for k, v in intents.items() if k not in confirmed}


intent_row = {"key": "K1", "source": "board",
              "live_order": {"status": "placed", "order_id": "intent-C1", "book": "prophetx",
                             "asked_stake": 390.0, "filled_stake": None, "client_id": "C1", "intent": True}}
conf_row = {"key": "K1", "source": "board",
            "live_order": {"status": "placed", "order_id": "PX-9", "book": "prophetx",
                           "asked_stake": 390.0, "filled_stake": 390.0, "client_id": "C1", "intent": False}}

risk, keys, open_i = account([intent_row])
ck("1. an unconfirmed intent still counts its risk", abs(risk - 390.0) < 1e-9, str(risk))
ck("1. an unconfirmed intent still consumes a play slot", keys == {"K1"}, str(keys))
ck("1. an unconfirmed intent is reported open", list(open_i) == ["C1"], str(open_i))

risk2, _, open2 = account([intent_row, conf_row])
ck("1. intent + confirmation count the money ONCE", abs(risk2 - 390.0) < 1e-9, str(risk2))
ck("1. a confirmation resolves its intent", open2 == {}, str(open2))
risk3, _, open3 = account([conf_row, intent_row])   # IMAP order is not chronological
ck("1. resolution is order-independent", abs(risk3 - 390.0) < 1e-9 and open3 == {}, f"{risk3} {open3}")

bo = inspect.getsource(ex.bot_orders)
ck("1. money identity prefers the client_id", 'str(cid or oid)' in bo)
ck("1. ids still carry the venue order_id (trade attribution)", "ids[oid]" in bo)
ck("1. intents are resolved after the loop, not inside it", bo.index("_intents[") < bo.index('INTENT["open"] = {}')
   if "_intents[" in bo else 'INTENT["open"] = {}' in bo)

# ---------------------------------------------------------------- 2. retries cannot duplicate
lg = inspect.getsource(ex.live_guards)
ck("2. an open intent makes live_guards REFUSE", 'INTENT["open"]' in lg)
ck("2. the refusal names the client id and the SUBJECT-based clearance",
   "INTENT_CLEAR_PREFIX" in lg and "asked" in lg)
ck("2. an unconfirmed intent puts its play key in LIVEKEYS",
   "LIVEKEYS.add" in bo and bo.index("LIVEKEYS.add") < bo.index("if str(cid or oid) in seen_oids"))
_io, _ic, _bo, _sbo, _sx = ex.imap_open, ex.imap_close, ex.bot_orders, ex.px_live.set_bot_orders, ex.book_live.set_exposure
ex.imap_open, ex.imap_close = (lambda: object()), (lambda M: None)
ex.px_live.set_bot_orders, ex.book_live.set_exposure = (lambda x: None), (lambda x: None)
ex.bot_orders = lambda M: {}          # registry readable, but an intent is open
ex.INTENT["open"] = {"C9": {"live_order": {"book": "prophetx", "asked_stake": 390.0},
                            "decided_utc": "2026-11-11T18:00:00Z"}}
ex.GUARD.update(ok=None, why="")
g_ok, g_why = ex.live_guards()
ex.imap_open, ex.imap_close, ex.bot_orders = _io, _ic, _bo
ex.px_live.set_bot_orders, ex.book_live.set_exposure = _sbo, _sx
ck("2. live_guards refuses while an intent is open", g_ok is False, str(g_why)[:120])
ck("2.   and says no live order will be placed", "fail closed" in (g_why or ""), str(g_why)[:160])
ck("2.   and tells Peter how to clear it",
   (ex.INTENT_CLEAR_PREFIX + " C9") in (g_why or ""), str(g_why)[:220])
ex.INTENT["open"] = {}
ex.GUARD.update(ok=None, why="")

# ---------------------------------------------------------------- 3. reconciled before new submissions
lo_src = inspect.getsource(ex.live_order)
ck("3. live_guards (registry + intents) runs before any order",
   lo_src.index("live_guards()") < lo_src.index("journal_intent("))
ck("3. the write-ahead runs BEFORE the book dispatch",
   lo_src.index("journal_intent(") < lo_src.index("live_order_other(r)"))
ck("3. a failed write-ahead submits NOTHING",
   "could not store the pre-order record" in lo_src and "nothing was submitted" in lo_src)
ck("3. resting bids also pass live_guards", "live_guards()" in inspect.getsource(ex.rest_bid))
ck("3. partial fills are recorded as filled_stake, not assumed full",
   '"filled_stake": lo.get("filled_stake")' in inspect.getsource(ex.journal_order))
ck("3. an unknown ProphetX fill counts everything asked",
   'res["filled_stake"] = None' in inspect.getsource(ex.live_order_other))

# a write-ahead failure refuses the order outright
SENT.clear(); stub(send=lambda s, b: (_ for _ in ()).throw(RuntimeError("smtp down")))
ok2, cid2 = ex.journal_intent({"play": {}}, "prophetx", 390.0)
ck("3. a failed write-ahead returns not-ok", ok2 is False and cid2 is None)
r_min = {"play": {"sport": "NBA", "game": "A vs B", "bet": "Under 225.5 (-110)"},
         "live": {"book": "prophetx", "line": 225.5, "risk": 390.0, "px": {"thr": -112}},
         "entry": {"price_after_fee": -110}}
ck("3. journal_intent never submits an order",
   not any(w in inspect.getsource(ex.journal_intent) for w in ("px_live.place", "_place(", "submit_order")))

# ---------------------------------------------------------------- 4. both lanes share it
ck("4. the write-ahead sits in live_order, which BOTH lanes use", "journal_intent(" in lo_src)
ck("4. the board lane routes through live_order",
   "live_order(" in inspect.getsource(ex.main))
ck("4. the write-ahead is not lane-conditional",
   not any(w in [l for l in lo_src.splitlines() if "journal_intent(" in l][0]
           for w in ("board", "rules", "lane2", "source")))
ck("4. the intent records which lane it came from (board accounting stays separable)",
   '"source": p.get("source")' in inspect.getsource(ex.journal_intent))

# ---------------------------------------------------------------- 5. no paid credits
ji = inspect.getsource(ex.journal_intent)
# Judge the CODE, not its prose: the docstring says "Zero paid credits", which a naive
# substring check reads as a credit call. Strip the docstring and comments first.
import ast as _ast  # noqa: E402
_t = _ast.parse(_ast.unparse(_ast.parse(ji)))
for _n in _ast.walk(_t):
    if isinstance(_n, (_ast.FunctionDef, _ast.Module)) and _ast.get_docstring(_n):
        _n.body = _n.body[1:]
ji_code = _ast.unparse(_t)
for bad in ("the-odds-api", "oddspapi", "ODDSPAPI", "credit", "historical-odds"):
    ck(f"5. the write-ahead makes no {bad} call", bad not in ji_code)
ck("5. the write-ahead uses Gmail SMTP only", "send(" in ji)
ck("5. the intent resolution uses a subject-only IMAP search, not a paid API",
   "intent_cleared(M, k)" in bo and "SUBJECT" in inspect.getsource(ex.subject_hits))

# ---------------------------------------------------------------- unchanged rules and sizing
ex.send, ex.tg, ex.intent_readable = _send, _tg, _rb
ck("unit still $200 board / $300 lane 1", ex.BOARD_UNIT == 200.0 and ex.LIVE_UNIT == 300.0)
ck("10 plays, $1,500, 15 min", ex.BOARD_MAX_PLAYS == 10 and ex.BOARD_DAILY_RISK == 1500.0
   and ex.BOARD_CONFIRM_MIN == 15)
ck("prophetx+novig 2c", ex.TOL_BOOKS == ("prophetx", "novig") and ex.PX_TOL_CENTS == 2)
ck("-130 cap, $2,250 stop, $415 guard",
   ex.CAP_LINE == -130 and ex.px_live.DAILY_STOP == 2250.0 and ex.px_live.MAX_ORDER == 415.0)
ck("board lane still off", ex.BOARD_LIVE is False)
ck("ProphetX never rests, so resting is unaffected by this fix",
   "polymarket_us" not in ex.REST_BOOKS and "prophetx" not in ex.REST_BOOKS, str(ex.REST_BOOKS))
ck("px_live untouched: EXT_PREFIX still defaults empty", ex.px_live.EXT_PREFIX == "")

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)

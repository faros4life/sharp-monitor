"""Crash-safe order logging and one-order-counted-once (Peter, Nov 11).

The bot-order registry is the LEDGER block in the run's 'Bets LIVE:' email, sent when the run
ENDS. An order placed at minute 8 of a 30-minute run that is then killed never reaches it, so the
daily stop undercounts and the next run can repeat the bet. journal_order() writes one durable row
the instant an order is placed, in the format bot_orders() already parses; bot_orders() now counts
each order id once so the journal row and the end-of-run row cannot double-count.
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


def fake_send(subject, body):
    SENT.append((subject, body))


def journal(lo, is_rest=False, play=None, send=fake_send):
    SENT.clear()
    old_send, old_tg = ex.send, ex.tg
    ex.send, ex.tg = send, lambda *a, **k: None
    try:
        return ex.journal_order({"play": play or {"play_key": "K1", "source": "board"}}, lo, is_rest)
    finally:
        ex.send, ex.tg = old_send, old_tg


PLACED = {"status": "placed", "order_id": "ORD-1", "book": "kalshi",
          "asked_stake": 220.0, "filled_stake": 220.0, "avg_price": -110, "limit": -110}

# ---------------------------------------------------------------- the row is written, and parseable
ok = journal(PLACED)
ck("a placed order is journalled", ok)
ck("exactly one email is sent", len(SENT) == 1, str(len(SENT)))
subj, body = SENT[0]
ck("subject starts with 'Bets LIVE:' (bot_orders only reads those)", subj.startswith("Bets LIVE:"), subj)
ck("subject names the venue and order id", "kalshi" in subj and "ORD-1" in subj, subj)
ck("body carries the ledger marker", "LEDGER (machine-readable" in body)

i = body.rfind("LEDGER (machine-readable")
rows, _ = json.JSONDecoder().raw_decode(body[body.index("[", i):])   # the EXACT bot_orders extraction
ck("the ledger parses with bot_orders' own rfind + raw_decode", isinstance(rows, list) and len(rows) == 1)
row = rows[0]
ck("row carries the play key (LIVEKEYS / duplicate blocking)", row.get("key") == "K1", str(row))
ck("row carries the lane (board accounting is separable)", row.get("source") == "board")
ck("row carries decided_utc (ET day attribution)", bool(row.get("decided_utc")))
ck("row is marked as a journal row", row.get("journal") is True)
lo = row.get("live_order") or {}
ck("immediate order lands under live_order", lo.get("status") == "placed" and lo.get("order_id") == "ORD-1")
ck("row carries the book", lo.get("book") == "kalshi")
ck("row carries asked_stake (the daily stop reads it)", lo.get("asked_stake") == 220.0)
ck("row carries filled_stake", lo.get("filled_stake") == 220.0)

ok = journal(dict(PLACED, order_id="ORD-R"), is_rest=True)
ck("a resting bid is journalled", ok)
i = SENT[0][1].rfind("LEDGER (machine-readable")
rrow = json.JSONDecoder().raw_decode(SENT[0][1][SENT[0][1].index("[", i):])[0][0]
ck("a resting order lands under live_rest", (rrow.get("live_rest") or {}).get("order_id") == "ORD-R")
ck("resting rows carry no live_order key", "live_order" not in rrow)
ck("resting rows are flagged resting", (rrow.get("live_rest") or {}).get("resting") is True)

# asked_stake falls back to 'asked' (novig_place returns that name)
journal({"status": "placed", "order_id": "N1", "book": "novig", "asked": 180.0})
i = SENT[0][1].rfind("LEDGER")
nrow = json.JSONDecoder().raw_decode(SENT[0][1][SENT[0][1].index("[", i):])[0][0]
ck("novig's 'asked' is mapped to asked_stake", (nrow.get("live_order") or {}).get("asked_stake") == 180.0)

# ---------------------------------------------------------------- failure is loud, never fatal
shouted = []


def boom_send(subject, body):
    raise RuntimeError("smtp down")


old_send, old_tg = ex.send, ex.tg
ex.send, ex.tg = boom_send, lambda m, *a, **k: shouted.append(m)
try:
    res = ex.journal_order({"play": {"play_key": "K2"}}, PLACED)
finally:
    ex.send, ex.tg = old_send, old_tg
ck("a send failure returns False rather than raising", res is False)
ck("a send failure SHOUTS on telegram", len(shouted) == 1, str(shouted))
ck("  and the shout says the order IS placed", shouted and "PLACED" in shouted[0].upper(), str(shouted))
ck("  and names the consequence (undercount / repeat)",
   shouted and ("undercount" in shouted[0] or "repeat" in shouted[0]), str(shouted))

# a telegram failure on top of a send failure must still not raise
ex.send, ex.tg = boom_send, boom_send
try:
    res2 = ex.journal_order({"play": {}}, PLACED)
finally:
    ex.send, ex.tg = old_send, old_tg
ck("send AND telegram both failing still does not raise", res2 is False)

src = inspect.getsource(ex.journal_order)
ck("journal_order never places or cancels anything",
   not any(w in src for w in ("_place(", "place(", "submit_order", "cancel")))
ck("journal_order swallows every exception (an existing order is never undone by logging)",
   "except Exception" in src)

# ---------------------------------------------------------------- wired at every order site
for fn, label in ((ex.live_order, "live_order (ProphetX)"),
                  (ex.live_order_other, "live_order_other (Kalshi/PM US/Novig)"),
                  (ex.rest_bid, "rest_bid (resting)")):
    s = inspect.getsource(fn)
    ck(f"{label} journals a placed order", "journal_order(" in s)
    ck(f"{label} journals ONLY when placed", 'status") == "placed"' in s or 'status"] == "placed"' in s)
ck("rest_bid journals as a resting row", "is_rest=True" in inspect.getsource(ex.rest_bid))

# ---------------------------------------------------------------- one order is counted once
bo = inspect.getsource(ex.bot_orders)
ck("bot_orders tracks order ids it has already counted", "seen_oids" in bo)
ck("the dedupe skips the MONEY sums", bo.index("seen_oids.add") < bo.index('NONPX["today"] +='))
ck("ids are recorded BEFORE the dedupe (duplicate blocking never weakened)",
   bo.index("ids[oid]") < bo.index("in seen_oids"))
ck("LIVEKEYS is populated BEFORE the dedupe",
   bo.index("LIVEKEYS.add") < bo.index("in seen_oids"))
ck("board keys still dedupe by play key", 'BOARD["keys"].add' in bo)

# arithmetic: the same order seen twice must add its money once
rows2 = [{"key": "K1", "source": "board", "decided_utc": "2026-11-11T18:00:00Z",
          "live_order": {"status": "placed", "order_id": "SAME", "book": "kalshi", "asked_stake": 220.0,
                         "filled_stake": 220.0}}] * 2
seen, risk = set(), 0.0
for r_ in rows2:
    lo_ = r_["live_order"]
    oid_ = str(lo_["order_id"])
    if oid_ in seen:
        continue
    seen.add(oid_)
    risk += float(lo_["asked_stake"])
ck("the same order id counted twice adds its stake once", abs(risk - 220.0) < 1e-9, str(risk))

# ---------------------------------------------------------------- nothing else moved
ck("TOL_BOOKS unchanged", ex.TOL_BOOKS == ("prophetx", "novig"))
ck("cap unchanged", ex.CAP_LINE == -130)
ck("board unit / caps unchanged",
   ex.BOARD_UNIT == 200.0 and ex.BOARD_MAX_PLAYS == 10 and ex.BOARD_DAILY_RISK == 1500.0)
ck("Lane 1 unit unchanged", ex.LIVE_UNIT == 300.0)
ck("global daily stop unchanged", ex.px_live.DAILY_STOP == 2250.0)

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)

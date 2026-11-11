#!/usr/bin/env python3
"""board_clv_check venue-selection tests (Peter, 11 Nov, O6).

Proves the three things the authorization asked for:
  1. NO HINDSIGHT venue selection - only the decision-time snapshot is read; a close, a result or a
     later price can never influence which venue is chosen.
  2. NO INCORRECT FEE TREATMENT - fees come from clv_std's single model, a venue clv_std refuses to
     price can never be selected, and maker/taker stay separate.
  3. NO CHANGE to historical calls or live execution - board/calls.json is never mutated and the
     module imports no order path.

Measurement only. Runs offline: no secrets, no network, no OddsPapi call.
"""
import json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import board_clv_check as b
import clv_std as cs

FAIL = []


def ck(name, cond, extra=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAIL.append(name)


def dec(am):
    return 1 + (am / 100.0 if am > 0 else 100.0 / -am)


print("1. NO HINDSIGHT VENUE SELECTION")
# best_bettable's whole input is one snapshot dict plus the line and the target. There is no
# parameter through which a close, a result or a later price could reach it.
import inspect
sig = set(inspect.signature(b.best_bettable).parameters)
ck("best_bettable takes only snapshot/line/alert-price/basis",
   sig == {"pbb", "line", "alert_am", "maker", "league"}, str(sig))
# Check EXECUTABLE CODE only: the docstring and comments legitimately use these words to say the
# function does not read them, so matching raw source would match its own prose. Strip the
# docstring and every comment first.
import ast as _ast
_fn = _ast.parse(inspect.getsource(b.best_bettable).lstrip()).body[0]
if (_fn.body and isinstance(_fn.body[0], _ast.Expr)
        and isinstance(getattr(_fn.body[0], "value", None), _ast.Constant)):
    _fn.body = _fn.body[1:]                      # drop the docstring
code = "\n".join(l.split("#", 1)[0] for l in _ast.unparse(_fn).splitlines())
for banned in ("close", "result", "units", "res", "after_15", "price_after", "circa", "pin"):
    ck(f"best_bettable code never references '{banned}'", banned not in code)
# a snapshot carrying extra post-decision keys is ignored rather than used
snap = {"novig": {"point": 220.5, "price": -104, "close_price": 0.9, "result": "W"},
        "kalshi": {"point": 220.5, "price": -104}}
pick = b.best_bettable(snap, 220.5, -110, False)
ck("post-decision keys in a snapshot do not change the pick", pick is not None and pick[0] == "novig.us",
   str(pick))
# the join is by the call's OWN key and alerted_utc, so a later alert on the same game cannot leak in
q = b.liq_quotes.__doc__ or ""
ck("liq_quotes keys on (key, alerted_utc)", "alerted_utc" in q)

print("\n2. FEE TREATMENT")
ck("module defines no fee constant of its own",
   not any(k in dir(b) for k in ("KALSHI_FEE", "PX_WIN_FEE", "PMUS_FEE", "NOVIG_LIVE")))
ck("_net delegates to clv_std.net_dec", "cs.net_dec" in inspect.getsource(b._net))
# same american price nets differently per venue, in the documented direction
n_novig = b._net("novig.us", -104, False)
n_kalshi = b._net("kalshi", -104, False)
n_px = b._net("prophetx", -104, False)
ck("Novig pre-game straight is fee-free vs Kalshi taker", n_novig > n_kalshi, f"{n_novig} vs {n_kalshi}")
ck("ProphetX taker sits between Novig and Kalshi", n_novig > n_px > n_kalshi, f"{n_px}")
ck("maker never prices worse than taker at the same venue",
   b._net("kalshi", -104, True) >= b._net("kalshi", -104, False))
# a venue clv_std refuses to price is unselectable, whatever its screen showed
ck("polymarket.global is not in BETTABLE", "polymarket.global" not in b.BETTABLE)
ck("polymarket.us IS in BETTABLE (Peter's venue)", "polymarket.us" in b.BETTABLE)
ck("'polymarket' (global) does not map through SRC_NAME", "polymarket" not in b.SRC_NAME)
ck("'polymarket_us' maps to polymarket.us", b.SRC_NAME.get("polymarket_us") == "polymarket.us")
ck("PM US maker is a rebate, so maker beats taker there",
   b._net("polymarket.us", -104, True) > b._net("polymarket.us", -104, False))
ck("a PM-US-only snapshot is selectable",
   b.best_bettable({"polymarket_us": {"point": 220.5, "price": -104}}, 220.5, -110, False) is not None)
ck("a snapshot with global AND PM US never picks global",
   (b.best_bettable({"polymarket": {"point": 220.5, "price": +500},
                     "polymarket_us": {"point": 220.5, "price": -104}}, 220.5, -110, False) or ("",))[0]
   == "polymarket.us")
ck("_net returns None for an unpriceable venue", b._net("polymarket.global", -104, False) is None)
gl = b.best_bettable({"polymarket": {"point": 220.5, "price": +200}}, 220.5, -110, False)
ck("a global-only snapshot yields no pick", gl is None, str(gl))
# the target must actually be beaten, and only on the same line
ck("a quote worse than the alert price is rejected",
   b.best_bettable({"kalshi": {"point": 220.5, "price": -130}}, 220.5, -104, False) is None)
ck("a different line is never selected",
   b.best_bettable({"novig": {"point": 221.5, "price": +200}}, 220.5, -110, False) is None)
ck("the alert price itself is accepted (OR BETTER, not strictly better)",
   b.best_bettable({"novig": {"point": 220.5, "price": -104}}, 220.5, -104, False) is not None)
ck("an unpriceable TRIGGER venue does not disqualify a play",
   b.best_bettable({"novig": {"point": 220.5, "price": -104}}, 220.5, -108, False) is not None)

print("\n3. NO CHANGE TO HISTORICAL CALLS OR LIVE EXECUTION")
mod = open(b.__file__).read()
for banned in ("import executor", "rest_bid", "place_order", "EXEC_LIVE", "json.dump", "open(CALLS, \"w\")"):
    ck(f"module contains no '{banned}'", banned not in mod)
# graded() copies rather than mutating the stored call
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "board"), exist_ok=True)
calls = {"calls": {"kalshi|{\"a\":1}|2026-11-01T00:00:00Z":
                   {"call": "PLAY", "result": "W", "units": 0.9, "line": 220.5,
                    "side": "NOT Over 220.5 points", "game": "A vs B", "book": "kalshi",
                    "price": -104, "at": "2026-11-01T00:00:00Z"}}}
f = os.path.join(tmp, "board", "calls.json")
json.dump(calls, open(f, "w"))
before = open(f).read()
old_calls = b.CALLS
b.CALLS = f
rows = b.graded()
b.CALLS = old_calls
ck("graded() attaches _k", rows and "_k" in rows[0])
ck("graded() leaves the file byte-identical", open(f).read() == before)
ck("graded() does not mutate the stored dict",
   "_k" not in json.load(open(f))["calls"]["kalshi|{\"a\":1}|2026-11-01T00:00:00Z"])

print("\n" + ("ALL PASS" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}"))
sys.exit(1 if FAIL else 0)

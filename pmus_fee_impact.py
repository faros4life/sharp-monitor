#!/usr/bin/env python3
"""BEFORE/AFTER for the Polymarket US fee correction. READ-ONLY: no network, no paid calls, no writes.

Peter, Nov 18: "Show the before/after execution eligibility and price impact." Two separate questions,
reported separately because they have different answers and different remedies:

  PRICE    - pure arithmetic on the model. Moves immediately and by a known amount.
  ELIGIBILITY - measured against the REAL alert population on disk (alerts.json), not a synthetic grid.

Counts only. No stakes, balances or dollar figures.
"""
import json

import clv_std as cs
import exchange_lag as el
import pmus_fee as pf

DEC = lambda am: 1 + (100 / abs(am) if am < 0 else am / 100)
AM = lambda d: round(-100 / (d - 1), 1) if d < 2 else round((d - 1) * 100, 1)


def under(model, fn):
    """pmus_fee.MODEL is the only model switch; exchange_lag deliberately exposes no alias."""
    was = pf.MODEL
    try:
        pf.MODEL = model
        return fn()
    finally:
        pf.MODEL = was


print("=" * 96)
print("POLYMARKET US FEE CORRECTION - BEFORE / AFTER   (model built, NOT activated: default is legacy)")
print("=" * 96)
print(f"active model this run: PMUS_FEE_MODEL={pf.MODEL!r}")
print(f"legacy taker coef {pf.LEGACY_TAKER}  legacy maker coef {pf.LEGACY_MAKER}")
print(f"schedule taker (tier unverified) {pf.taker(model='schedule')}   schedule maker (unverified) "
      f"{pf.maker(model='schedule')}   gate {pf.gate_coef(model='schedule')}")

# ---------------------------------------------------------------- 1. PRICE IMPACT
print("\n" + "-" * 96)
print("1. PRICE IMPACT - what $1 staked pays back, and the screen price it equals")
print("-" * 96)
print(f"{'screen':>8} | {'LEGACY taker':>22} | {'SCHEDULE taker':>22} | {'move':>8} | "
      f"{'LEGACY maker':>14} | {'SCHED maker':>12}")
for am in (-300, -200, -150, -130, -110, 100, 130, 150, 200, 300):
    d = DEC(am)
    lt = under("legacy", lambda: el.eff("polymarket.us", d))
    st = under("schedule", lambda: el.eff("polymarket.us", d))
    lm = under("legacy", lambda: el.eff("polymarket.us", d, maker=True))
    sm = under("schedule", lambda: el.eff("polymarket.us", d, maker=True))
    print(f"{am:>+8} | {lt:>9.4f} ({AM(lt):>+8}) | {st:>9.4f} ({AM(st):>+8}) | {100*(st/lt-1):>+7.2f}% | "
          f"{AM(lm):>+13} | {AM(sm):>+11}")
print("\nmaker under the schedule equals the screen price exactly: free, not a rebate.")

# ---------------------------------------------------------------- 2. THE PRICE BAR MOVES
print("\n" + "-" * 96)
print("2. PRICE REQUIREMENT - raw price PMUS must SHOW to net a target (raw_for inverts the model)")
print("-" * 96)
print(f"{'net target':>11} | {'LEGACY raw':>11} | {'SCHEDULE raw':>13} | {'extra cents of price needed':>28}")
for net_am in (-150, -130, -110, 100, 130):
    nd = DEC(net_am)
    lr = under("legacy", lambda: el.raw_for("polymarket.us", nd))
    sr = under("schedule", lambda: el.raw_for("polymarket.us", nd))
    print(f"{net_am:>+11} | {AM(lr):>+11} | {AM(sr):>+13} | {100*(1/lr - 1/sr):>+27.2f}")
print("\npositive = PMUS must quote a BETTER screen price than before to clear the same net bar.")

# ---------------------------------------------------------------- 3. ELIGIBILITY on the real population
print("\n" + "-" * 96)
print("3. EXECUTION ELIGIBILITY - measured on the alert rows on disk, not a synthetic grid")
print("-" * 96)
rows = json.load(open("alerts.json"))["alerts"]
quoted = [r for r in rows if (r.get("prices_at_alert") or {})]
freq = {}
for r in quoted:
    for b in r["prices_at_alert"]:
        freq[b] = freq.get(b, 0) + 1
print(f"alert rows on disk: {len(rows)}   rows carrying per-book quotes: {len(quoted)}")
print(f"quote frequency by book: {dict(sorted(freq.items(), key=lambda kv: -kv[1]))}")

pm = [r for r in quoted if "polymarket_us" in r["prices_at_alert"]]
print(f"rows carrying a Polymarket US quote: {len(pm)}")

changed = 0
for r in pm:
    q = {}
    for b, v in r["prices_at_alert"].items():
        p = v.get("price")
        if p is None:
            continue
        try:
            cs.canon(b)
        except Exception:
            continue
        q[b] = DEC(p)
    if not q:
        continue
    a = under("legacy", lambda: cs.best_net(q, scope="auto"))
    b_ = under("schedule", lambda: cs.best_net(q, scope="auto"))
    if a and b_ and a[0] != b_[0]:
        changed += 1
print(f"rows where the winning venue CHANGES under the correction: {changed}")

print("\nREAD THIS CAREFULLY - the two zeros mean different things:")
if not pm:
    print("  Polymarket US appears in ZERO of these rows. It is therefore not losing venue selection on")
    print("  price; it is never entering the comparison at all. A fee coefficient cannot explain a venue")
    print("  that is absent from the quote set, so the fee correction changes execution eligibility by")
    print("  NOTHING today and matters only once PMUS quotes actually appear on alert rows.")
    print("  That makes the missing executions an upstream quote-capture / market-matching question,")
    print("  which is what executor.VSTAT was deployed to measure. It is NOT settled by this commit.")
else:
    print(f"  {len(pm)} rows carry a PMUS quote and {changed} of them change hands under the correction.")
print("\nScope limit: alerts.json is the live file, not full history, and only rows that recorded")
print("per-book quotes can be tested. This measures the population on disk, nothing wider.")

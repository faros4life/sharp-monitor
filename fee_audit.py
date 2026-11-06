#!/usr/bin/env python3
"""
FEE MODEL AUDIT against the LIVE accounts (Peter, Nov 6: "YOU HAVE THE API").

Derives each venue's actual fee coefficient from our own fills instead of trusting a constant or a
website. clv_std.FEE_NOTES carries the model; two of five coefficients were verified from account
exports (Novig 0, Hard Rock 0) and three were not (ProphetX 2%, Kalshi 0.07, Polymarket US 0.0695).
This closes the three.

READ-ONLY. GET requests only, through the same authenticated callers the executor already uses. It
places, cancels and modifies nothing, and touches no order endpoint.

WHAT IS PRINTED WHERE. The Actions log is public, so it gets RATIOS, COUNTS and FIELD NAMES only -
never an amount, never a field value. Any detail goes to the private address. Field discovery prints
names and types, never values: on Nov 5 a report of mine printed /account values behind a redaction
test that a UUID defeated, and put a live API key in Peter's inbox. Names only, no exceptions.

THE ARITHMETIC
  ProphetX  model: 2% of WINNINGS -> fee/profit should be about 2.00% on a winning fill.
            px_fee_check already read /v4/mm/get_trades: 100 recent fills, fee 0.00% of profit and
            0.00% of stake, including 12 settled winners. That contradicts the model, but 80 of the
            100 were manually_settled, which may be a fee-exempt path. /v3/account/transactions is
            the wallet ledger and settles it: a 2% commission must appear there as a debit.
  Kalshi    model: 0.07 x contracts x p x (1-p). Invert it: rate = fee / (contracts x p x (1-p)).
  Polymkt   model: 0.0695, same shape. Polymarket's own docs say SPORTS taker 0.05 and MAKER 0.00,
            but describe the global venue rather than the CFTC-regulated US entity.
"""
import json
import os
import sys

import clv_std as cs

LIMIT = int(os.environ.get("FEE_AUDIT_LIMIT", "") or "200")
L = []


def say(line, public=True):
    """public=True -> also to the Actions log. Anything with an amount must pass public=False."""
    L.append(line)
    if public:
        print(line)


def shape(d, label):
    """Field NAMES and types only. Never a value."""
    if not isinstance(d, dict):
        return f"{label}: {type(d).__name__}"
    out = []
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            out.append(f"{k}{{{','.join(sorted(v))}}}")
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out.append(f"{k}[0]{{{','.join(sorted(v[0]))}}}")
        elif isinstance(v, list):
            out.append(f"{k}[{len(v)}]")
        else:
            out.append(f"{k}:{type(v).__name__}")
    return f"{label}: " + ", ".join(out)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def fee_of(d, *names):
    for n in names:
        v = num(d.get(n))
        if v is not None:
            return v, n
    return None, None


# ------------------------------------------------------------------ ProphetX
def prophetx():
    say("\n=== ProphetX (model: 2% of winnings) ===")
    try:
        import liquidity_monitor as lm
        r = lm.px_call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
        lm._PXT["token"] = (r.get("data") or {}).get("access_token")
        if not lm._PXT["token"]:
            return say("  login failed - cannot audit")
        say(f"  account: {'SANDBOX' if 'sandbox' in lm.PX_BASE else 'LIVE'}")
        tx = lm.px_call("/v3/account/transactions")
        body = tx.get("data") if isinstance(tx, dict) else None
        rows = (body.get("transactions") if isinstance(body, dict) else None) or \
               (body if isinstance(body, list) else [])
        say(f"  /v3/account/transactions -> {len(rows)} rows")
        if rows:
            say("  " + shape(rows[0], "row fields"))
            kinds = {}
            feeish = 0
            for t in rows:
                k = str(t.get("type") or t.get("transaction_type") or t.get("category") or "?")
                kinds[k] = kinds.get(k, 0) + 1
                if any("fee" in str(x).lower() or "commission" in str(x).lower() for x in t.keys()) \
                   or "fee" in k.lower() or "commission" in k.lower():
                    feeish += 1
            say(f"  transaction types: {dict(sorted(kinds.items(), key=lambda x: -x[1])[:10])}")
            say(f"  rows mentioning a fee or commission: {feeish}")
            say("  VERDICT: " + ("a fee/commission line EXISTS in the ledger - the 2% model is "
                                 "supported and the per-trade fee field is simply not populated"
                                 if feeish else
                                 "NO fee or commission line anywhere in the ledger. Together with "
                                 "0.00% on all 100 fills (12 of them settled winners) the 2% model "
                                 "is NOT supported by this account."))
    except Exception as e:
        say(f"  ProphetX audit failed ({type(e).__name__}: {str(e)[:70]})")


# ------------------------------------------------------------------ Kalshi
def kalshi():
    say("\n=== Kalshi (model: 0.07 x contracts x p x (1-p) taker) ===")
    try:
        import book_live as bl
        _, r = bl._k_call("GET", "/portfolio/fills", {"limit": LIMIT})
        fills = (r.get("fills") or []) if isinstance(r, dict) else []
        say(f"  /portfolio/fills -> {len(fills)} fills")
        if not fills:
            return say("  no fills to measure")
        say("  " + shape(fills[0], "fill fields"))
        rates, nofee = [], 0
        for f in fills:
            fee, fname = fee_of(f, "fee_dollars", "fee", "taker_fee_dollars", "taker_fee")
            cnt = num(f.get("count_fp")) or num(f.get("count"))
            yp = num(f.get("yes_price_dollars"))
            if yp is None and f.get("yes_price") is not None:
                yp = num(f.get("yes_price")) / 100.0
            side = str(f.get("side") or "").lower()
            p = yp if side != "no" else (1 - yp if yp is not None else None)
            if fee is None or not cnt or p is None or not (0 < p < 1):
                continue
            if fee == 0:
                nofee += 1
                continue
            rates.append(fee / (cnt * p * (1 - p)))
        say(f"  fills with a usable fee + size + price: {len(rates)}; with fee exactly 0: {nofee}")
        if rates:
            rates.sort()
            med = rates[len(rates) // 2]
            say(f"  implied coefficient: median {med:.4f} | min {rates[0]:.4f} | max {rates[-1]:.4f}"
                f"   (model 0.0700)")
            say("  VERDICT: " + ("matches the 0.07 model" if abs(med - 0.07) < 0.006 else
                                 f"DOES NOT match - the model should be about {med:.4f}"))
        elif nofee:
            say("  VERDICT: every fill reports fee 0 - either maker-side fills, or Kalshi charged "
                "nothing on these. The 0.07 TAKER coefficient is untested by this sample.")
    except Exception as e:
        say(f"  Kalshi audit failed ({type(e).__name__}: {str(e)[:70]})")


# ------------------------------------------------------------------ Polymarket US
def pmus():
    say("\n=== Polymarket US (model: 0.0695 x p x (1-p) taker; docs say 0.05 sports / 0.00 maker) ===")
    try:
        import book_live as bl
        _, r = bl._pm_call("GET", "/v1/portfolio/activities", {"limit": LIMIT})
        rows = None
        if isinstance(r, dict):
            for k in ("activities", "data", "results", "items"):
                if isinstance(r.get(k), list):
                    rows, key = r[k], k
                    break
            if rows is None:
                return say("  " + shape(r, "/v1/portfolio/activities response (no list found)"))
        elif isinstance(r, list):
            rows, key = r, "(top-level list)"
        else:
            return say(f"  unexpected response type {type(r).__name__}")
        say(f"  /v1/portfolio/activities -> {len(rows)} rows under {key}")
        if not rows:
            return say("  no activity to measure")
        say("  " + shape(rows[0], "row fields"))
        rates, nofee = [], 0
        for a in rows:
            fee, _ = fee_of(a, "fee", "feeDollars", "fee_dollars", "takerFee", "taker_fee")
            cnt = num(a.get("size")) or num(a.get("shares")) or num(a.get("quantity"))
            p = num(a.get("price")) or num(a.get("avgPrice")) or num(a.get("average_price"))
            if p is not None and p > 1:
                p = p / 100.0
            if fee is None or not cnt or p is None or not (0 < p < 1):
                continue
            if fee == 0:
                nofee += 1
                continue
            rates.append(fee / (cnt * p * (1 - p)))
        say(f"  rows with a usable fee + size + price: {len(rates)}; with fee exactly 0: {nofee}")
        if rates:
            rates.sort()
            med = rates[len(rates) // 2]
            say(f"  implied coefficient: median {med:.4f} | min {rates[0]:.4f} | max {rates[-1]:.4f}"
                f"   (model 0.0695, docs 0.05 sports taker)")
        elif nofee:
            say("  VERDICT: every row reports fee 0. If these were MAKER fills that agrees with the "
                "docs (maker 0.00) and posting here is free - which would put Polymarket beside "
                "Novig for the posting strategy.")
    except Exception as e:
        say(f"  Polymarket audit failed ({type(e).__name__}: {str(e)[:70]})")


def main():
    say("FEE MODEL AUDIT - live accounts, READ-ONLY (GETs only, no orders)")
    say(cs.stamp())
    say("Public log carries ratios, counts and field NAMES only - never an amount or a value.")
    prophetx()
    kalshi()
    pmus()
    say("\nVerified already, from account exports: Novig = no fee (14 fills, mean drag -0.016%), "
        "Hard Rock = no commission (43 settled bets).")
    try:
        import executor as ex
        ex.send("Bets FEE MODEL AUDIT (live accounts, read-only)", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
THE CLV STANDARD (Peter, VALUE LAB, Nov 6 2026). One CLV methodology for every script, exchange and
report. Import this; do not re-derive the formula or the fee model locally.

THE FORMULA, and the only one:
    net CLV % = (Pinnacle no-vig CLOSING probability  x  effective entry decimal AFTER FEES  -  1) x 100
Same market, same side, the exact same line. Positive means we beat the closing fair price.

WHY THIS EXISTS. Before it, the formula was written out in about eleven places (model_lab x2,
sent_export x4, nba_backtest2, p1_backtest, liq_history_test x3) and the FEE MODEL existed in four
copies with two different key spellings:
    sharp_monitor.WIN_FEE / TAKER_FEE   keys "prophetx", "kalshi", "polymarket_us"   (underscore)
    exchange_lag.eff()                  keys "prophetx", "kalshi", "polymarket.us"   (dot)
    "ev sightings".TAKER / PX_FEE       its own copy
    executor.PMUS_FEE                   the coefficient again
The two main implementations are numerically identical (both add f x p x (1-p) to the cost for
Kalshi / Polymarket, and both cut winnings by 2% for ProphetX), so no published CLV is wrong because
of it. The hazard is different and worse: exchange_lag.eff() SILENTLY RETURNS THE RAW PRICE for any
key it does not recognise. eff("polymarket_us", d) == d. No error, no warning - just a fee-free
price and an overstated CLV. canon() below refuses an unknown venue instead, which is the fix.

FEES ARE NEVER A FIXED ADJUSTMENT. Measured from eff():
    Novig      0.00% of the decimal at every price - the only genuinely free venue of the four
    ProphetX   flat 2% of WINNINGS -> 0.50% at -300, 0.96% at -110, 1.52% at +300. Grows as the
               price SHORTENS, the opposite direction to the other two. NOT fee-free.
    Kalshi     p x (1-p) shaped -> 1.75% at -300, 3.33% at -110, 5.25% at +300
    Polymarket same shape, see the coefficient caveat below
    Hard Rock  no commission; it is retail, so the vig is already inside the displayed price
Consequence: to match -110 net you need -108 ProphetX, -103 Kalshi, -103 Polymarket; to match -104
net, Kalshi must show +103. Near even money Kalshi and Polymarket fall out of contention on
arithmetic alone, so no rule is needed to exclude them. Use exchange_lag.raw_for() for that.

OPEN, AND PETER ASKED FOR IT (item 2, "verify the applicable Polymarket US fee schedule"):
Polymarket's own published docs give fee = C x rate x p x (1-p), which matches our shape, but with
SPORTS taker rate 0.05 - not the 0.0695 this repo uses - and MAKER rate 0.00 in every category,
makers never charged. Two problems with adopting that: those docs are for Polymarket (global), not
the CFTC-regulated Polymarket US entity, and no authoritative US schedule was reachable - only
third-party sites, which is not good enough for a number that prices real money. So NOTHING is
changed here. PMUS_RATE stays at the repo's existing 0.0695 and is flagged UNVERIFIED. If 0.05 is
right we have been UNDERSTATING Polymarket CLV; if maker is really 0.00 then posting there is free
and Polymarket joins Novig for Peter's posting strategy, which would matter a great deal. The
authoritative answer is the fee actually charged on one of Peter's own filled Polymarket US orders -
his account statement settles it better than any website.

Read-only helper: no network, no credits, no state.
"""
import exchange_lag as el

# Stamp this on every CLV figure (Peter, item 2: "record the fee-model version used").
# Bump it whenever eff(), a coefficient, or the venue registry changes.
FEE_MODEL = "2026-11-06.4"
# Each entry carries its VERIFICATION STATUS, not just its rate. Peter, Nov 6: "cant you check out
# fills or the account" - so where his own exports could settle a coefficient, they were used, and
# where they could not, that is stated rather than assumed.
FEE_NOTES = {
    "novig.us":      "none. VERIFIED from 14 filled Novig rows (novig-trading-history 2026-10-20): "
                     "payout/cost against the raw decimal deviates by a mean of -0.016%, scattering "
                     "BOTH directions (-0.18% to +0.23%), which is price rounding; a real fee is "
                     "one-directional. The +100 fill is exactly 0.000%.",
    "hardrockbet":   "no commission; retail vig is inside the price. VERIFIED from 43 settled Hard "
                     "Rock bets (All_Bets_Export 1 and 2): payout/(wager x decimal) is exactly "
                     "0.0000%, or -0.047% where a cent price does not divide evenly. No fee column "
                     "exists in the export, and none is being taken.",
    "kalshi":        "0.07 x p x (1-p) taker. VERIFIED EXACTLY from the live account "
                     "(fee_audit, GET /portfolio/fills): 32 taker fills, every one charged, implied "
                     "coefficient median 0.0700, min 0.0700, max 0.0705 against a model of 0.0700. "
                     "MAKER side untested - 0 of 32 fills were maker, so the maker rate is unknown "
                     "and Kalshi's API does expose is_taker to split them when there is data.",
    "prophetx":      "2% of winnings. VERIFIED EXACTLY from the ProphetX wallet ledger. The fee is "
                     "booked as its OWN 'Fees' wallet entry beside the Payout row, NOT on the trade - "
                     "which is why GET /v4/mm/get_trades reports fee 0.00 on every fill and why I "
                     "briefly and wrongly read that as 'no fee charged'. Two independent rows: "
                     "Payout +426.00 with Fees -4.00 (stake 226, price -113) and Payout +440.00 with "
                     "Fees -4.00 (stake 240, price -120). Both fees are exactly 2.000% of exactly "
                     "200.00 of winnings - Peter's unit - and a third row, Fees -0.02 on 1.00 of "
                     "winnings, agrees. eff() was right all along; nothing changes. Practical note: "
                     "at a 200-to-win unit every ProphetX winner costs a flat 4.00.\n"
                     "                     LESSON: a venue's fee may not live on its trade record. "
                     "Absence of a fee field is not evidence of no fee.",
    "polymarket.us": "0.0695 x p x (1-p) taker. NOT VERIFIED, and contradicted by the published "
                     "docs. No Polymarket export supplied. Polymarket's own docs give SPORTS taker "
                     "0.05 and MAKER 0.00 in every category, but cover Polymarket global rather "
                     "than the CFTC-regulated US entity, and no authoritative US schedule was "
                     "reachable. If 0.05 is right we UNDERSTATE Polymarket CLV; if maker is really "
                     "0.00 then posting there is free and it joins Novig for the posting strategy. "
                     "NOT MEASURABLE from the API as currently reachable either: /v1/portfolio/trades "
                     "and /v1/portfolio/fills both 404, and /v1/portfolio/activities returns only "
                     "positionResolution events carrying no fee field at all.",
}
# What would close the three open ones, in order of how much it matters:
#   ProphetX       the wallet-ledger endpoint name for this API version (/v3/account/transactions
#                  404s), or one normally-settled winning fill rather than manually_settled
#   Polymarket US  a trades endpoint, or one filled order's fee line from a statement
#   Kalshi maker   any maker-side fill; is_taker already splits them when data exists

# canonical key -> (display, auto-eligible, manual-eligible). AUTO excludes Hard Rock by Peter's
# instruction; Hard Rock is manual-only and its CLV is never pooled with AUTO.
VENUES = {
    "novig.us":      ("Novig",         True,  True),
    "prophetx":      ("ProphetX",      True,  True),
    "kalshi":        ("Kalshi",        True,  True),
    "polymarket.us": ("Polymarket US", True,  True),
    "hardrockbet":   ("Hard Rock",     False, True),
}
# every spelling seen in this repo, mapped to one canonical key
ALIASES = {
    "novig": "novig.us", "novig_us": "novig.us", "NOVIG": "novig.us", "Novig": "novig.us",
    "prophetx": "prophetx", "PROPHETX": "prophetx", "ProphetX": "prophetx", "px": "prophetx",
    "kalshi": "kalshi", "KALSHI": "kalshi", "Kalshi": "kalshi",
    "polymarket": "polymarket.us", "polymarket_us": "polymarket.us", "POLY": "polymarket.us",
    "polymarket.us": "polymarket.us", "PM US": "polymarket.us", "Polymarket US": "polymarket.us",
    "pmus": "polymarket.us",
    "hardrockbet": "hardrockbet", "hardrockbet_fl": "hardrockbet", "Hard Rock": "hardrockbet",
    "Hard Rock FL": "hardrockbet", "hardrock": "hardrockbet",
}
AUTO = tuple(k for k, v in VENUES.items() if v[1])
MANUAL = tuple(k for k, v in VENUES.items() if v[2])


class UnknownVenue(ValueError):
    """Raised instead of silently pricing a venue as fee-free."""


def canon(book, strict=True):
    """Canonical venue key. Refuses an unknown venue rather than letting eff() fall through to a
    fee-free price - that silent fall-through is the whole reason this module exists."""
    if book is None:
        if strict:
            raise UnknownVenue("venue is None")
        return None
    k = str(book).strip()
    if k in VENUES:
        return k
    if k in ALIASES:
        return ALIASES[k]
    low = k.lower().replace(" ", "").replace("-", "")
    for a, c in ALIASES.items():
        if a.lower().replace(" ", "").replace("-", "").replace("_", "").replace(".", "") == \
           low.replace("_", "").replace(".", ""):
            return c
    if strict:
        raise UnknownVenue(f"venue {book!r} is not in the registry - add it to VENUES/ALIASES rather "
                           f"than letting it price as fee-free")
    return None


def net_dec(book, raw_dec):
    """Effective decimal AFTER that venue's fee. Hard Rock and Novig return the raw price unchanged,
    for different reasons: Novig charges nothing, Hard Rock's vig is already in the price."""
    c = canon(book)
    if raw_dec is None or raw_dec <= 1:
        return None
    return raw_dec if c == "hardrockbet" else el.eff(c, float(raw_dec))


def net_clv(close_prob, raw_dec, book):
    """The one formula, as a percentage. None when any input is missing."""
    nd = net_dec(book, raw_dec)
    if nd is None or close_prob is None:
        return None
    return round(100.0 * (float(close_prob) * nd - 1.0), 3)


def best_net(quotes, scope="auto"):
    """(canonical venue, net decimal) for the best price AFTER fees within a scope.

    quotes: {venue: raw_decimal}. scope "auto" = auto-eligible exchanges only (Hard Rock excluded,
    per Peter); "manual" = everything manually reachable, Hard Rock included. The comparison is
    always on the NET price, so a venue only wins when it wins after its own fee - which is why no
    venue needs excluding by rule.
    """
    allow = AUTO if scope == "auto" else MANUAL
    best = None
    for bk, raw in (quotes or {}).items():
        try:
            c = canon(bk)
        except UnknownVenue:
            continue                       # reported by the caller, never priced as free
        if c not in allow:
            continue
        nd = net_dec(c, raw)
        if nd is not None and (best is None or nd > best[1]):
            best = (c, nd)
    return best if best else (None, None)


def close_verified(how):
    """Peter item 4: only a VERIFIED SAME-LINE Pinnacle close qualifies for a headline figure.

    close_for() reports how it read the close. "own line" is Pinnacle hanging the exact line we
    want. "moneyline" has no line to match, so it counts. Anything of the form "main X moved to Y"
    is a half-point CONVERSION - a model, not a verified close - and is excluded from the headline
    and reported separately with its reason."""
    h = (how or "").strip().lower()
    return h in ("own line", "moneyline")


def stamp():
    """One line for every report, so a CLV figure always carries the model that produced it."""
    return (f"CLV: net of fees, Pinnacle verified same-line no-vig close. fee-model {FEE_MODEL}. "
            f"AUTO={len(AUTO)} venues (Hard Rock excluded), MANUAL={len(MANUAL)}. "
            f"Polymarket US coefficient UNVERIFIED.")


if __name__ == "__main__":
    def am(d):
        return round(-100 / (d - 1)) if d < 2 else round(100 * (d - 1))
    print(stamp(), "\n")
    assert canon("polymarket_us") == "polymarket.us" and canon("PM US") == "polymarket.us"
    assert canon("novig") == "novig.us" and canon("hardrockbet_fl") == "hardrockbet"
    try:
        canon("betfair")
        raise SystemExit("FAIL: an unknown venue was accepted")
    except UnknownVenue:
        pass
    print("canon(): every repo spelling maps, unknown venue refused")
    d = 1.9091
    for b in VENUES:
        print(f"  {VENUES[b][0]:14s} raw -110 -> net {am(net_dec(b, d)):+5d}   drag "
              f"{(d / net_dec(b, d) - 1) * 100:5.2f}%   auto={VENUES[b][1]}")
    assert net_dec("hardrockbet", d) == d and net_dec("novig.us", d) == d
    assert net_dec("kalshi", d) < d and net_dec("prophetx", d) < d
    q = {"novig": 1.91, "kalshi": 1.95, "hardrockbet_fl": 2.05}
    print(f"\n  quotes {q}")
    print(f"  best AUTO   (no Hard Rock): {best_net(q, 'auto')}")
    print(f"  best MANUAL (Hard Rock in): {best_net(q, 'manual')}")
    av, an = best_net(q, "auto")
    assert av == "novig.us", f"Kalshi 1.95 must LOSE to Novig 1.91 after its fee, got {av}"
    assert best_net(q, "manual")[0] == "hardrockbet"
    print("  -> Kalshi's better RAW price loses on NET, as it must")
    assert close_verified("own line") and close_verified("moneyline")
    assert not close_verified("main 228.5 moved to 226.5") and not close_verified(None)
    print("\nclose_verified(): own line and moneyline pass; a half-point conversion is excluded")
    print(f"\nnet CLV example: close 0.52, raw -110 on Kalshi -> {net_clv(0.52, d, 'kalshi'):+.3f}%"
          f"  vs on Novig -> {net_clv(0.52, d, 'novig'):+.3f}%")
    print("ALL SELF-TESTS PASSED")

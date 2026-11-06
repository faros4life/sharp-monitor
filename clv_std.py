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
FEE_MODEL = "2026-11-06.9"
# Each entry carries its VERIFICATION STATUS, not just its rate. Peter, Nov 6: "cant you check out
# fills or the account" - so where his own exports could settle a coefficient, they were used, and
# where they could not, that is stated rather than assumed.
FEE_NOTES = {
    "novig.us": "PRE-GAME straights: ZERO both sides, and that is where Lane 1 trades - verified "
                "from 14 fills, mean drag -0.016%. But Novig is NOT flat zero, which is how this repo "
                "has carried it. Their schedule (Peter, Nov 6): TAKING a live in-game or futures "
                "straight costs 0.06 x C x p x (1-p), i.e. 2.78% of the decimal at -110, which we have "
                "been booking at zero. MAKER is $0 across every trade type, stated outright - so "
                "posting on Novig is free, confirmed, not assumed. Their own page contradicts itself on "
                "the live coefficient (table and Example 1 say 0.06; the closing VWAP note says 0.03); "
                "we take the worse until a live fill settles it. Parlays 0.10, inside the quote, not traded.",
    "hardrockbet":   "no commission; retail vig is inside the price. VERIFIED from 43 settled Hard "
                     "Rock bets (All_Bets_Export 1 and 2): payout/(wager x decimal) is exactly "
                     "0.0000%, or -0.047% where a cent price does not divide evenly. No fee column "
                     "exists in the export, and none is being taken.",
    "kalshi": "TAKER 0.07 x C x p x (1-p), verified TWICE: 32 live fills with median exactly "
              "0.0700, and now Kalshi's own schedule dated Jul 7 2026. No settlement fee, no membership "
              "fee. MAKER is the one coefficient still open repo-wide. The formula is 0.0175 x M with "
              "'M = the multiplier for each contract (default is 0 unless otherwise indicated)', and the "
              "indicated multipliers sit in a Non-Standard Fees table that names KXNFLGAME, KXNCAAFGAME, "
              "KXMLBGAME, KXWNBAGAME, KXUCLGAME, KXWCGAME - and not one SPREAD or TOTAL series, which "
              "are 96.5% of our Kalshi market records. Read literally, posting on the markets we "
              "actually trade is FREE. I cannot tell from the document whether unlisted truly means M=0 "
              "or the table just does not enumerate spreads and totals, so eff() carries the "
              "CONSERVATIVE 0.0175 and the first maker fill decides it: fee_audit.py already buckets on "
              "the API's is_taker flag.",
    "prophetx": "TWO models, split by LEAGUE (their schedule, Nov 6). Everything except NHL: 2% "
                "commission on NET GAINS PER MARKET - VERIFIED EXACTLY from 8 wallet Fees rows "
                "(-4.00 on 200.00 twice, -0.02 on a 1.00 net gain), all NBA/NFL, so schedule and "
                "ledger agree to three decimals. Note it is per MARKET, so wins and losses in one "
                "market net before the 2%; we bet one side per market, and where that breaks the "
                "model overcharges, which is the safe direction. NHL ALONE is an ordinary maker/taker "
                "scale, F(p) = a x (1-p) per traded dollar, a = 0.035 taker and 0.01 maker - the same "
                "p(1-p) shape as every other venue. Reproduces their worked example to the cent. We "
                "carried 2% across all leagues, which understated NHL takes (0.96% booked, 1.64% real) "
                "and overstated NHL posts (0.96% booked, 0.47% real). 3 ProphetX NHL rows so far.",
    "polymarket.us": "TAKER 0.0695 x C x p x (1-p) - FILL-VERIFIED, and reverted here on Nov 6. I "
                     "had changed it to 0.06 on text Peter pasted; he then applied the test it "
                     "should have faced first - official schedule, effective date, and one recent "
                     "fill reconciling at the new rate - and it fails all three. His Oct 25 "
                     "Grizzlies/Kings fill is effective 0.5374 exactly: a raw 0.52 gives 0.537347 "
                     "under 0.0695 and 0.5350 under 0.06. The fill fits the old rate. Four sources "
                     "disagree, and the CFTC filing for QCX LLC (Mar 2026) is a different STRUCTURE "
                     "entirely - 0.10% of total contract premium, ~30x smaller than any p(1-p) "
                     "reading. UNRESOLVED; the fill wins until it is not. The MAKER REBATE is not "
                     "modelled at all: Peter requires it be its own separate change, never bundled, "
                     "so maker falls back to taker and posting is costed too high, not too low.",
}
# What would close the open ones, in order of how much it matters:
#   Polymarket US  the Nov 2 Pistons fill's contract count and price (Peter has it), which pins the
#                  rate from a second independent fill; or an issuer-dated PM US schedule
#   ProphetX       the wallet-ledger endpoint name for this API version (/v3/account/transactions
#                  404s), or one normally-settled winning fill rather than manually_settled
#   Kalshi maker   any maker-side fill; is_taker already splits them when data exists

VENUES = {
    "novig.us":      ("Novig",         True,  True),
    "prophetx":      ("ProphetX",      True,  True),
    "kalshi":        ("Kalshi",        True,  True),
    "polymarket.us": ("Polymarket US", True,  True),
    "hardrockbet":   ("Hard Rock",     False, True),
    # NOT the same venue as polymarket.us. The global exchange is not CFTC-regulated and Peter
    # cannot trade it, so it is ineligible for BOTH scopes and has no fee model. It is in the
    # registry only so that canon() names it instead of refusing it - a refusal would read as a
    # data error, when in fact the quote is real and simply not ours to take.
    "polymarket.global": ("Polymarket Global", False, False),
}
# every spelling seen in this repo, mapped to one canonical key
ALIASES = {
    "novig": "novig.us", "novig_us": "novig.us", "NOVIG": "novig.us", "Novig": "novig.us",
    "prophetx": "prophetx", "PROPHETX": "prophetx", "ProphetX": "prophetx", "px": "prophetx",
    "kalshi": "kalshi", "KALSHI": "kalshi", "Kalshi": "kalshi",
    # Nov 6: "polymarket" was mapped to polymarket.us. It is the GLOBAL book. 633 alert rows carry
    # both keys and 167 of the first 400 quote DIFFERENT prices, so the collapse let an untradeable
    # quote win best-AUTO and inflate opportunity CLV. They are now separate venues.
    "polymarket": "polymarket.global", "polymarket_global": "polymarket.global",
    "polymarket_us": "polymarket.us", "POLY": "polymarket.us",
    "polymarket.us": "polymarket.us", "PM US": "polymarket.us", "Polymarket US": "polymarket.us",
    "pmus": "polymarket.us",
    "hardrockbet": "hardrockbet", "hardrockbet_fl": "hardrockbet", "Hard Rock": "hardrockbet",
    "Hard Rock FL": "hardrockbet", "hardrock": "hardrockbet",
}
AUTO = tuple(k for k, v in VENUES.items() if v[1])
MANUAL = tuple(k for k, v in VENUES.items() if v[2])


class UnknownVenue(ValueError):
    """Raised instead of silently pricing a venue as fee-free."""


class NotTradeable(ValueError):
    """A real venue whose quotes we can see but cannot take (global Polymarket). Raised rather than
    priced, so such a quote can never reach a CLV figure by accident."""


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


def net_dec(book, raw_dec, maker=False):
    """Effective decimal AFTER that venue's fee. Hard Rock and Novig return the raw price unchanged,
    for different reasons: Novig charges nothing, Hard Rock's vig is already in the price.

    maker=True prices us as the resting side. It is not merely cheaper: on Polymarket US the maker
    side is a REBATE, so net_dec can exceed the raw price. Peter's strategy is to post, so this is
    the side that matters - but it defaults to False, because every fill in our history is taker."""
    c = canon(book)
    if c not in AUTO and c not in MANUAL:
        raise NotTradeable(f"{VENUES[c][0]} quotes are visible but not tradeable - no fee model, "
                           f"and it must not enter AUTO or MANUAL opportunity")
    if raw_dec is None or raw_dec <= 1:
        return None
    return raw_dec if c == "hardrockbet" else el.eff(c, float(raw_dec), maker)


def net_clv(close_prob, raw_dec, book, maker=False):
    """The one formula, as a percentage. None when any input is missing."""
    nd = net_dec(book, raw_dec, maker)
    if nd is None or close_prob is None:
        return None
    return round(100.0 * (float(close_prob) * nd - 1.0), 3)


def best_net(quotes, scope="auto", maker=False):
    """(canonical venue, net decimal, SOURCE venue key as the row spelled it) for the best price
    AFTER fees within a scope.

    The third element is Peter's requirement, Nov 6: the original source-venue ID is preserved on
    every row, so a canonical key can always be traced back to the spelling the data used. That is
    what makes the polymarket / polymarket.us split auditable after the fact.

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
        nd = net_dec(c, raw, maker)
        if nd is not None and (best is None or nd > best[1]):
            best = (c, nd, bk)
    return best if best else (None, None, None)


def close_verified(how):
    """Peter item 4: only a VERIFIED SAME-LINE Pinnacle close qualifies for a headline figure.

    close_for() reports how it read the close. "own line" is Pinnacle hanging the exact line we
    want. "moneyline" has no line to match, so it counts. Anything of the form "main X moved to Y"
    is a half-point CONVERSION - a model, not a verified close - and is excluded from the headline
    and reported separately with its reason."""
    h = (how or "").strip().lower()
    return h in ("own line", "moneyline")


# LIVE-CODE FLAG, needs Peter's explicit yes (no live-betting change without it):
# executor.PMUS_FEE is still 0.0695 and is used in LIVE Polymarket order pricing, not just grading.
# It is now known to be 0.06 taker. The error direction is conservative - it demands a better price
# than necessary, so it under-bets rather than over-bets - but it is wrong, and it knows nothing of
# the maker rebate, so a posted Polymarket order is priced as if we paid a fee we would instead be
# PAID. Not touched here.


def stamp():
    """One line for every report, so a CLV figure always carries the model that produced it."""
    return (f"CLV: net of fees, Pinnacle verified same-line no-vig close. fee-model {FEE_MODEL}. "
            f"AUTO={len(AUTO)} venues (Hard Rock excluded), MANUAL={len(MANUAL)}. "
            f"PM-US 0.0695 fill-verified (0.06 rejected 0/3, rebate NOT modelled); Novig free "
            f"pre-game and all maker; Kalshi maker UNVERIFIED at 0.0175; ProphetX NHL 0.035/0.01.")


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
        if b not in AUTO and b not in MANUAL:
            print(f"  {VENUES[b][0]:18s} NOT TRADEABLE - net_dec() refuses it, excluded from both scopes")
            continue
        print(f"  {VENUES[b][0]:18s} raw -110 -> net {am(net_dec(b, d)):+5d}   drag "
              f"{(d / net_dec(b, d) - 1) * 100:5.2f}%   auto={VENUES[b][1]}")
    assert net_dec("hardrockbet", d) == d and net_dec("novig.us", d) == d
    assert net_dec("kalshi", d) < d and net_dec("prophetx", d) < d
    q = {"novig": 1.91, "kalshi": 1.95, "hardrockbet_fl": 2.05}
    print(f"\n  quotes {q}")
    print(f"  best AUTO   (no Hard Rock): {best_net(q, 'auto')}")
    print(f"  best MANUAL (Hard Rock in): {best_net(q, 'manual')}")
    av, an, asrc = best_net(q, "auto")
    assert av == "novig.us", f"Kalshi 1.95 must LOSE to Novig 1.91 after its fee, got {av}"
    assert best_net(q, "manual")[0] == "hardrockbet"
    assert asrc == "novig", "the SOURCE spelling must survive beside the canonical key"
    print("  -> Kalshi's better RAW price loses on NET, as it must")
    # the Nov 6 split: a global Polymarket quote must never win, or even price
    gq = {"novig": 1.91, "polymarket": 2.60}
    assert best_net(gq, "auto")[0] == "novig.us", "global Polymarket must not win best-AUTO"
    assert best_net(gq, "manual")[0] == "novig.us", "nor best-MANUAL"
    try:
        net_dec("polymarket", 2.60)
        raise AssertionError("net_dec must REFUSE an untradeable venue, not price it")
    except NotTradeable:
        pass
    assert canon("polymarket") == "polymarket.global" and canon("polymarket_us") == "polymarket.us"
    print("  -> global Polymarket: priced by nothing, wins nothing, and canon() keeps it distinct")
    assert close_verified("own line") and close_verified("moneyline")
    assert not close_verified("main 228.5 moved to 226.5") and not close_verified(None)
    print("\nclose_verified(): own line and moneyline pass; a half-point conversion is excluded")
    print(f"\nnet CLV example: close 0.52, raw -110 on Kalshi -> {net_clv(0.52, d, 'kalshi'):+.3f}%"
          f"  vs on Novig -> {net_clv(0.52, d, 'novig'):+.3f}%")
    print("ALL SELF-TESTS PASSED")

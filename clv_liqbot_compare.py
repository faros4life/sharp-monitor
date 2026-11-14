#!/usr/bin/env python3
"""
LIQ-BOT RECONCILED COMPARISON (Peter, Nov 14 2026: "Add a clearly labelled reconciled LIQ-BOT
comparison alongside the original +23.81u alert-price result. Do not overwrite the published
result.")

NOTHING PUBLISHED IS CHANGED. SCORECARD.md and REGISTRY.md are not opened for writing by this
module. It writes audit/liqbot_reconciled.md, which sits beside them and is versioned by
clv_basis.BASIS_VERSION, so the two bases can be read side by side and the published figure stays
exactly as it was ratified on 11 Nov.

THE POPULATION IS THE POINT, AND IT IS WHERE THIS COULD MOST EASILY GO WRONG. The published
+23.81u is the REGISTRY-9 DEFINITION: NBA total, lead >= 240 min, n=151 as frozen on 11 Nov. The
-3.29% / n=1,369 recompute from the observation audit is the WHOLE liquidity board, which is a
different and much larger population. Putting those two numbers in one sentence would compare a
4h+ NBA-totals lane against every NHL moneyline the board ever logged. Both comparisons are
reported here, each against its OWN published counterpart:

    registry 9      NBA total, lead >= 240 min   vs  n=151, +23.81u (alert price, 11 Nov)
    whole board     every graded liquidity row   vs  2,665 graded, -29.04u, -1.1% (11 Nov)

THE POPULATION ALSO DRIFTED. Re-running the registry-9 selection today gives n=174, because 23
more rows have been logged and graded since the 11 Nov freeze. The frozen figure is therefore
shown as frozen, and today's same-definition alert-price figure is computed and shown next to it,
so the basis change is not confused with the population change. Two causes, two columns.

SELECTION AND UNIT MATH ARE IMPORTED, NOT REWRITTEN. nba_totals_master owns the registry-9
selector (nba_totals + lead_min >= 240), the unit arithmetic (units_of, which already carries the
scar of being read as American odds once) and the halves split. clv_obs_audit owns the
new-basis waterfall, and clv_basis owns the CLV formula. A second copy of any of them here would
be a second answer to the same question.
"""
import collections
import json
import os
import statistics as stx
import sys
from datetime import datetime, timezone

import clv_basis as cb
import clv_ledger as cl
import clv_obs_audit as oa
import fixture_match as fxm
import nba_totals_master as ntm
import tracker_build as tb

ET = cl.ET
OUT = "audit/liqbot_reconciled.md"
# Frozen, as ratified 11 Nov. Read, never recomputed, never overwritten.
PUBLISHED = {
    "registry9": {"n": 151, "units": 23.81, "roi_pct": None, "fees": False,
                  "basis": "recorded ALERT price, BEFORE fees (NOT executable)",
                  "source": "SCORECARD.md entry 9, ratified 11 Nov 2026",
                  "note": "liq_history_test measured 3.42% fee drag between this basis and the "
                          "executable one, which is the whole sign difference"},
    # SCORECARD.md B2, the table's own header: "Units are 1u flat AFTER FEES at the alert price."
    # The two published figures are therefore on DIFFERENT bases, and a middle column that applies
    # fees to one and not the other would invent a discrepancy out of my own bookkeeping.
    "board": {"n": 2665, "units": -29.04, "roi_pct": -1.1, "fees": True,
              "basis": "alert price, AFTER fees (SCORECARD.md B2 header)",
              "source": "SCORECARD.md B2, 11 Nov 2026",
              "note": "the published row records Pinnacle CLV as 'none of any kind - only the "
                      "trigger exchange's own close', so the CLV column here is new evidence "
                      "rather than a revision of an existing number"},
}
# The fee model is ONE model. clv_std.net_dec delegates to exchange_lag.eff, which is what
# liq_history_test used for the published after-fee column, so "our executable after-fee entry"
# and "the alert price after fees" are the SAME number computed by the same code. What changes
# between the published figures and the new ones is therefore the BENCHMARK (trigger venue's own
# close -> Pinnacle no-vig close), and for registry 9 also the fees, which its figure omits.
# Saying it plainly matters: a reader who assumed the entry price also moved would credit the new
# column with an execution improvement that did not happen.
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def ci(xs):
    """(lo, hi) 95% CI of the mean, or None when the sample cannot support one.

    CLAUDE.md: bound a claim, do not assert it. A mean with no spread is an overcall, and a null
    result at small n means a difference was not DETECTED, never that none exists.
    """
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    se = stx.stdev(xs) / len(xs) ** 0.5
    m = stx.mean(xs)
    return (m - 1.96 * se, m + 1.96 * se)


def fmt_ci(c, scale=100, unit="%"):
    return "-" if not c else f"[{c[0] * scale:+.2f}, {c[1] * scale:+.2f}]{unit}"


def new_basis(rows, fxs, alt, allfx, mkmap):
    """Verified Pinnacle CLV per row, through the SAME waterfall the observation audit uses.

    Returns (verified, by_class). verified rows carry 'clv' and keep their alert row, so units,
    halves and ROI can be computed on exactly the rows that have a new-basis figure - never on a
    mixture of certified and modelled numbers, which is the pooling bias SCORECARD.md already
    recorded as real and one-directional.
    """
    verified, by_class = [], collections.Counter()
    for a in rows:
        cls, detail = oa.classify(a, "liquidity", fxs, alt, allfx, mkmap)
        by_class[cls] += 1
        if cls == "VERIFIED_PINNACLE" and isinstance(detail, dict) and detail.get("clv") is not None:
            verified.append({"row": a, "clv": detail["clv"], "fid": detail.get("fid"),
                             "entry": detail.get("entry"), "how": detail.get("how")})
    return verified, by_class


def block(title, rows, pub, fxs, alt, allfx, mkmap, defn):
    say("")
    say(f"### {title}")
    say("")
    say(f"Definition: {defn}")
    say("")
    verified, by_class = new_basis(rows, fxs, alt, allfx, mkmap)
    pre_u, pre_n = ntm.units_of(rows)                 # alert price, BEFORE fees
    af_u, af_n = units_alert_af(rows)                 # alert price, AFTER fees - same rows
    same_u, same_n = (af_u, af_n) if pub["fees"] else (pre_u, pre_n)
    cov_af_u, cov_af_n = units_exec(verified)         # after fees, CLV-covered rows only
    clvs = [v["clv"] for v in verified]
    say("| | PUBLISHED (frozen) | TODAY, the SAME basis | TODAY, after fees | NEW Pinnacle CLV |")
    say("|---|---|---|---|---|")
    say(f"| basis | {pub['basis']} | same selection, same basis | alert price after fees "
        f"(the executable entry) | Pinnacle no-vig close vs that same after-fee entry |")
    say(f"| version | 11 Nov 2026 | {pub['source'].split(',')[0]} | clv_std fee model | "
        f"clv_basis {cb.BASIS_VERSION} |")
    say(f"| n | {pub['n']} | {same_n} | {af_n} | {len(verified)} |")
    say(f"| units | {pub['units']:+.2f}u | {same_u:+.2f}u | {af_u:+.2f}u | "
        + (f"{cov_af_u:+.2f}u on the {cov_af_n} covered rows |" if verified else "- |"))
    roi = pub.get("roi_pct")
    say(f"| ROI (1u flat) | {'-' if roi is None else f'{roi:+.1f}%'} | "
        f"{(same_u / max(1, same_n) * 100):+.2f}% | {(af_u / max(1, af_n) * 100):+.2f}% | "
        + (f"{(cov_af_u / max(1, cov_af_n) * 100):+.2f}% |" if verified else "- |"))
    say(f"| mean CLV | not measured on this basis | not measured | not measured | "
        + (f"**{stx.mean(clvs) * 100:+.2f}%** |" if clvs else "- |"))
    say(f"| CLV 95% CI | - | - | - | {fmt_ci(ci(clvs))} |")
    say(f"| beat close | - | - | - | "
        + (f"{sum(1 for c in clvs if c > 0)}/{len(clvs)} "
           f"({sum(1 for c in clvs if c > 0) / len(clvs) * 100:.0f}%) |" if clvs else "- |"))
    unprice = by_class.get("VENUE_NOT_PRICEABLE", 0)
    priceable = max(1, len(rows) - unprice)
    say(f"| coverage, whole population | - | - | - | {len(verified)}/{len(rows)} "
        f"({len(verified) / max(1, len(rows)) * 100:.1f}%) |")
    say(f"| coverage, PRICEABLE rows only | - | - | - | {len(verified)}/{priceable} "
        f"({len(verified) / priceable * 100:.1f}%) - excludes {unprice} rows on a venue not "
        f"bettable from the US |")
    say("")
    say(f"The entry price does NOT differ between the last two columns: {af_n} rows are priced at "
        f"the alert cost through the one fee model, and the CLV column re-benchmarks that same "
        f"entry against Pinnacle instead of the trigger venue's own close. Only the benchmark "
        f"moved, so none of the change below is an execution improvement.")
    say("")
    # Reconciliation of the middle column against the frozen figure. A near-miss is reported as a
    # near-miss: CLAUDE.md, do not explain a surprising number with the world before the reader.
    like_for_like = True
    if pub["n"] != same_n:
        drift = same_n - pub["n"]
        note = (f"**Population difference, stated before anything is compared.** The frozen figure "
                f"is n={pub['n']}; the same definition today selects n={same_n} ({drift:+d}). ")
        if drift > 0:
            note += "Rows have been logged and graded since the 11 Nov freeze."
        elif pub["fees"] and abs(drift) >= unprice > 0:
            # Found by reading my own output: the after-fee column can only price rows the fee
            # model handles, so it drops every Polymarket-global row. That is a documented venue
            # exclusion, not a lost row, and leaving it unexplained would have handed over a
            # figure that looked like it contradicted the published one.
            note += (f"The after-fee basis can only price rows the fee model handles, so it "
                     f"excludes the {unprice} rows on a venue not bettable from the US, which the "
                     f"published row counted. {abs(drift)} of the difference is that exclusion - "
                     f"so the two columns are NOT like for like and their units must not be "
                     f"subtracted from each other.")
            like_for_like = False
        else:
            note += ("The count went DOWN, which logging alone cannot do - rows graded on 11 Nov "
                     "are no longer selected, so either a grade was revised or the stored "
                     "selection fields moved. That is NOT explained here.")
            like_for_like = False
        say(note + " The separate columns exist so a basis change is never read as a population "
                   "change or the reverse.")
        say("")
    gap = abs(same_u - pub["units"])
    if gap > 2.0 and like_for_like:
        say(f"**UNRECONCILED: {gap:.2f}u.** The middle column should reproduce the frozen figure on "
            f"the same selection and the same basis, and it does not. Until that gap is explained "
            f"the frozen figure stands as published and the new CLV column is the only number here "
            f"offered as evidence.")
        say("")

    say("Why the rest of the population has no new-basis figure:")
    say("")
    for c, n in by_class.most_common():
        if c == "VERIFIED_PINNACLE":
            continue
        say(f"- {n} {c} - {oa.CATEGORY.get(c, '?')}")
    say("")

    # halves, on the rows that HAVE a new figure
    h1, h2 = ntm.halves([v["row"] for v in verified], "alerted_utc")
    s1 = {id(r) for r in h1}
    a1 = [v for v in verified if id(v["row"]) in s1]
    a2 = [v for v in verified if id(v["row"]) not in s1]
    say("Chronological halves, new basis (the registered rule needs BOTH positive):")
    say("")
    say("| half | n | units (after fees) | CLV | CLV 95% CI | beat close |")
    say("|---|---|---|---|---|---|")
    for nm, g in (("H1", a1), ("H2", a2)):
        if not g:
            say(f"| {nm} | 0 | - | - | - | - |")
            continue
        cs_ = [v["clv"] for v in g]
        say(f"| {nm} | {len(g)} | {units_exec(g)[0]:+.2f}u | {stx.mean(cs_) * 100:+.2f}% | "
            f"{fmt_ci(ci(cs_))} | {sum(1 for c in cs_ if c > 0)}/{len(cs_)} |")
    say("")
    say(verdict(a1, a2, verified, rows, unprice))
    say("")
    return {"n_pop": len(rows), "n_verified": len(verified),
            "prefee_units": pre_u, "prefee_n": pre_n,
            "same_basis_units": same_u, "same_basis_n": same_n,
            "new_units_after_fee": cov_af_u if verified else None,
            "alert_units_after_fee": af_u, "alert_af_n": af_n,
            "mean_clv": stx.mean(clvs) if clvs else None,
            "ci": ci(clvs), "beat": sum(1 for c in clvs if c > 0),
            "classes": dict(by_class)}


def units_exec(verified):
    """(units, n) at the EXECUTABLE after-fee entry price, 1u risked per row.

    Nov 14, caught reading my own first output: the new-basis column originally printed units from
    ntm.units_of, which pays the ALERT price. So the cell said "NEW verified Pinnacle basis" above
    a number that was still the non-executable basis - the exact thing Peter ruled out ("do not
    present historical alert prices as actual executable prices"), and worse for being under the
    right heading. Units here come from clv_basis's after-fee decimal: a win pays (dec - 1), a
    loss is -1, a push is 0. The W/L itself is the feed's own grade and is never re-graded.
    """
    u, n = 0.0, 0
    for v in verified:
        res, dec = v["row"].get("result"), v.get("entry")
        if res not in ("W", "L", "P") or not dec or dec <= 1:
            continue
        n += 1
        if res == "P":
            continue
        u += (dec - 1) if res == "W" else -1.0
    return round(u, 2), n


def units_alert_af(rows):
    """(units, n) at the alert price AFTER fees - the published B2 basis, reproduced.

    This is the executable entry for every row the fee model can price, whether or not a Pinnacle
    close was found: units need a result and a price, CLV needs a close. Keeping the two separate
    stops a coverage gap in the CLOSE from quietly shrinking the UNITS population as well.
    """
    u, n = 0.0, 0
    for a in rows:
        res = a.get("result")
        if res not in ("W", "L", "P"):
            continue
        dec, _why = cb.after_fee_from_cost(a.get("price"), a.get("book_key") or a.get("book"),
                                           league=a.get("league") or a.get("sport"))
        if not dec or dec <= 1:
            continue
        n += 1
        if res == "P":
            continue
        u += (dec - 1) if res == "W" else -1.0
    return round(u, 2), n


def verdict(a1, a2, verified, rows, unprice=0):
    """SCORECARD.md's registered rules, applied and nothing more.

    POTENTIAL PASS needs ALL of: realized-unit CI excluding zero on the positive side WITH ACTUAL
    FILLS, certified CLV >= 0 and precise and representative, both chronological halves positive,
    multiplicity survived, rule pre-registered. CLEAR FAIL needs a realized-unit CI excluding zero
    on the negative side, or a precise and representative certified-CLV CI doing so.

    Two conditions this population cannot meet at all are stated rather than quietly skipped:
    there are NO FILLS anywhere in it (the lane is shadow-logged, approved as a bot and HELD OFF),
    and coverage is not representative while a large share of the population has no new-basis
    figure. So the outcome is bounded below by ignorance, not by profit.
    """
    if not verified:
        return ("**INSUFFICIENT EVIDENCE.** No row in this population has a verified new-basis "
                "figure, so nothing here supports or vetoes anything.")
    clvs = [v["clv"] for v in verified]
    c = ci(clvs)
    cov = len(verified) / max(1, len(rows))
    cov_p = len(verified) / max(1, len(rows) - unprice)
    bits = []
    if c and c[1] < 0:
        bits.append(f"the certified CLV CI {fmt_ci(c)} excludes zero on the NEGATIVE side")
    elif c and c[0] > 0:
        bits.append(f"the certified CLV CI {fmt_ci(c)} excludes zero on the positive side")
    else:
        bits.append(f"the certified CLV CI {fmt_ci(c)} straddles zero")
    h1ok = bool(a1) and stx.mean([v["clv"] for v in a1]) > 0
    h2ok = bool(a2) and stx.mean([v["clv"] for v in a2]) > 0
    bits.append(f"halves {'both positive' if (h1ok and h2ok) else 'NOT both positive'}")
    bits.append("no fills anywhere in this population (shadow logging only)")
    bits.append(f"coverage {cov * 100:.0f}% of all rows, {cov_p * 100:.0f}% of the PRICEABLE rows")
    # The verdict turns on which denominator "representative" uses, and that is a definition
    # question about the registered rule - not something to settle by picking the reading that
    # produces a verdict. Both are stated; neither is applied as if it were decided.
    rep_all, rep_p = cov >= 0.8, cov_p >= 0.8
    neg = bool(c and c[1] < 0)
    if neg and rep_all:
        head, tail = "**CLEAR FAIL on the executable basis**", ""
    elif neg and rep_p:
        head = "**CLEAR FAIL on the executable basis IF coverage is judged on the priceable rows**"
        tail = (f" On the whole population, coverage is {cov * 100:.0f}% and the registered rule's "
                f"representativeness test is unmet, which leaves CONTINUE TESTING. The {unprice} "
                f"uncovered rows are all on a venue that is not bettable from the US, so they "
                f"could never have been executed at any price - whether they belong in the "
                f"denominator is a DEFINITION question about this lane, and this report does not "
                f"settle it. The CLV sign and interval are the same either way; only the label "
                f"moves.")
    else:
        head = "**CONTINUE TESTING**"
        tail = (" - a statement about ignorance, not profit: it authorises more observation and "
                "nothing else.")
    return (f"{head} under the registered rules: " + "; ".join(bits) + "."
            + tail
            + " POTENTIAL PASS is unreachable here regardless of the CLV sign, because it "
              "requires a realized-unit CI from ACTUAL FILLS and this lane has none. Nothing is "
              "promoted, demoted or re-staked by this report.")


def main():
    now = datetime.now(timezone.utc)
    say(f"# LIQ-BOT: published vs reconciled")
    say("")
    say(f"Generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET. Basis version **{cb.BASIS_VERSION}**. "
        f"Read-only: SCORECARD.md and REGISTRY.md are not modified by this report, and the "
        f"published figures below are quoted from them as frozen.")
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say("")
        say(f"**FATAL**: clv/state.enc unreadable ({type(e).__name__}) - the close join cannot run, "
            f"so the new-basis column would be MISSING, not negative. No comparison written.")
        os.makedirs("audit", exist_ok=True)
        open(OUT, "w").write("\n".join(L) + "\n")
        return 1
    try:
        mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"**FATAL**: {oa.MKFILE} unreadable ({type(e).__name__})")
        return 1
    fxs = st.get("fixtures") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    allfx = dict(alt, **fxs)
    say("")
    say(f"Fixtures on hand {len(allfx)}; hcache files "
        f"{len(os.listdir(oa.HC)) if os.path.isdir(oa.HC) else 0}. No OddsPapi call is made by "
        f"this report - every close comes from cache.")

    A = ntm.nba_totals(ntm.alerts())
    r9 = [a for a in A if (ntm.lead_min(a) or 0) >= 240]
    res = {}
    res["registry9"] = block(
        "Registry 9 / LIQ-BOT - the population the published +23.81u measures",
        r9, PUBLISHED["registry9"], fxs, alt, allfx, mkmap,
        "NBA total, lead >= 240 min (nba_totals_master.lead_min, the same selector the published "
        "figure used). This is the apples-to-apples comparison.")

    board = [a for a in (ntm.alerts() or []) if a.get("result") in ("W", "L", "P")]
    res["board"] = block(
        "Whole liquidity board - a DIFFERENT and much larger population",
        board, PUBLISHED["board"], fxs, alt, allfx, mkmap,
        "every graded liquidity row, all leagues and markets. Reported separately because it is "
        "NOT registry 9: it is where the -3.29% whole-board recompute comes from, and reading it "
        "as the LIQ-BOT lane's figure would compare a 4h+ NBA-totals lane against every NHL "
        "moneyline the board ever logged.")

    say("")
    say("### Coverage limitations that bound every figure above")
    say("")
    say("- **No fills.** This lane was approved as a bot and HELD OFF; the record is shadow "
        "logging. Every unit figure on any basis is hypothetical, so the registered POTENTIAL "
        "PASS, which requires a realized-unit CI from actual fills, cannot be reached from this "
        "population at all.")
    say("- **Missingness is not random.** Rows lacking a new-basis figure concentrate by venue "
        "and league rather than spreading evenly, so the verified subset is not a random sample "
        "of the population. Nothing here says whether the uncovered rows were better or worse - "
        "no direction is inferred, because none is supported.")
    pm = sum(1 for a in r9 if str(a.get("book") or "").lower().startswith("polymarket"))
    if pm:
        say(f"- **{pm} of the {len(r9)} registry-9 rows were triggered on Polymarket global**, "
            f"which is not bettable from the US and which clv_std refuses to price at all. "
            f"Whether those rows belong in the lane's population, or should be re-priced against "
            f"a US venue's quote, is a DEFINITION question about the lane and not something this "
            f"report decides.")
    say("- **The alert price was never executable.** That is the published entry's own wording, "
        "and liq_history_test put 3.42% of fee drag between the two bases. The new column is not "
        "a correction of an arithmetic error; it is a different and executable question.")
    say("")
    say("### What is NOT changed by this report")
    say("")
    say("SCORECARD.md entry 9 and its +23.81u stand as published. No strategy is promoted, "
        "demoted, re-staked or switched on or off. No execution, routing, sizing, price-tolerance "
        "or eligibility behaviour is touched. NCAAB and MLB remain on hold.")

    os.makedirs("audit", exist_ok=True)
    open(OUT, "w").write("\n".join(L) + "\n")
    json.dump({"generated": cl.iso(now), "basis": cb.BASIS_VERSION,
               "published": PUBLISHED, "reconciled": res},
              open("audit/liqbot_reconciled.json", "w"), indent=1, default=str)
    print(f"\nwrote {OUT} and audit/liqbot_reconciled.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

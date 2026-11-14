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
    "registry9": {"n": 151, "units": 23.81, "basis": "recorded ALERT price (NOT executable)",
                  "source": "SCORECARD.md entry 9, ratified 11 Nov 2026",
                  "note": "liq_history_test measured 3.42% fee drag between this basis and the "
                          "executable one, which is the whole sign difference"},
    "board": {"n": 2665, "units": -29.04, "roi_pct": -1.1, "basis": "board grading",
              "source": "SCORECARD.md closing section, 11 Nov 2026"},
}
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
                             "how": detail.get("how")})
    return verified, by_class


def block(title, rows, pub, fxs, alt, allfx, mkmap, defn):
    say("")
    say(f"### {title}")
    say("")
    say(f"Definition: {defn}")
    say("")
    verified, by_class = new_basis(rows, fxs, alt, allfx, mkmap)
    old_u, old_n = ntm.units_of(rows)
    say("| | PUBLISHED (frozen) | TODAY, same old basis | NEW verified Pinnacle basis |")
    say("|---|---|---|---|")
    say(f"| basis | {pub['basis']} | same | Pinnacle no-vig close vs our executable after-fee entry |")
    say(f"| version | ratified 11 Nov 2026 | {pub['source'].split(',')[0]} | clv_basis {cb.BASIS_VERSION} |")
    say(f"| n | {pub['n']} | {old_n} | {len(verified)} |")
    say(f"| units | {pub['units']:+.2f}u | {old_u:+.2f}u | "
        + (f"{units_new(verified):+.2f}u |" if verified else "- |"))
    roi = pub.get("roi_pct")
    say(f"| ROI | {'-' if roi is None else f'{roi:+.1f}%'} | "
        f"{(old_u / old_n * 100):+.2f}% | "
        + (f"{(units_new(verified) / len(verified) * 100):+.2f}% |" if verified else "- |"))
    clvs = [v["clv"] for v in verified]
    say(f"| mean CLV | not measured on this basis | not measured on this basis | "
        + (f"{stx.mean(clvs) * 100:+.2f}% |" if clvs else "- |"))
    say(f"| CLV 95% CI | - | - | {fmt_ci(ci(clvs))} |")
    say(f"| beat close | - | - | "
        + (f"{sum(1 for c in clvs if c > 0)}/{len(clvs)} "
           f"({sum(1 for c in clvs if c > 0) / len(clvs) * 100:.0f}%) |" if clvs else "- |"))
    say(f"| coverage | - | - | {len(verified)}/{len(rows)} "
        f"({len(verified) / max(1, len(rows)) * 100:.1f}%) of the population |")
    say("")
    if pub["n"] != old_n:
        say(f"**The population moved as well as the basis.** The frozen figure is n={pub['n']}; the "
            f"same definition today selects n={old_n} ({old_n - pub['n']:+d}), because more rows "
            f"have been logged and graded since 11 Nov. The middle column exists so the basis "
            f"change is not read as the population change or the reverse.")
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
    say("| half | n | units | CLV | CLV 95% CI | beat close |")
    say("|---|---|---|---|---|---|")
    for nm, g in (("H1", a1), ("H2", a2)):
        if not g:
            say(f"| {nm} | 0 | - | - | - | - |")
            continue
        cs_ = [v["clv"] for v in g]
        say(f"| {nm} | {len(g)} | {units_new(g):+.2f}u | {stx.mean(cs_) * 100:+.2f}% | "
            f"{fmt_ci(ci(cs_))} | {sum(1 for c in cs_ if c > 0)}/{len(cs_)} |")
    say("")
    say(verdict(a1, a2, verified, rows))
    say("")
    return {"n_pop": len(rows), "n_verified": len(verified),
            "old_units": old_u, "old_n": old_n,
            "new_units": units_new(verified) if verified else None,
            "mean_clv": stx.mean(clvs) if clvs else None,
            "ci": ci(clvs), "beat": sum(1 for c in clvs if c > 0),
            "classes": dict(by_class)}


def units_new(verified):
    """Units on exactly the rows that carry a verified new-basis CLV, using the published unit
    arithmetic. This is NOT a re-grading: result comes from the feed's own W/L as before."""
    u, _n = ntm.units_of([v["row"] for v in verified])
    return u


def verdict(a1, a2, verified, rows):
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
    bits.append(f"coverage {cov * 100:.0f}%" + (" - not representative" if cov < 0.8 else ""))
    head = ("**CLEAR FAIL on the executable basis**" if (c and c[1] < 0 and cov >= 0.8)
            else "**CONTINUE TESTING**")
    tail = ("" if (c and c[1] < 0 and cov >= 0.8) else
            " - a statement about ignorance, not profit: it authorises more observation and "
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

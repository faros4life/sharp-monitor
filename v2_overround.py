"""Pinnacle alt-line overround and V2 model-vs-market calibration screen.

Registered spec: v2_validation_spec.md (pre-registered 2026-11-20, before any result).

Both quantities compared here are ESTIMATES of the fair probability at our number:
  MARKET - de-vig of Pinnacle's OBSERVED two-sided quote at our alt line.
  MODEL  - Pinnacle's MAIN-line fair walked to our number via line_value's registered MASS.
Neither is independent ground truth. This is a calibration screen, not a proof of accuracy.

Why two market estimates are reported, not one: de-vigging is a CHOICE of how the book's
margin is split between the sides, and the choice changes the answer on a deep alt.
  proportional (what clv_ledger.novig_p does): 1/a - fair = fair * overround, so the margin
      is loaded in proportion to probability and the favourite carries most of it.
  even: each side carries overround/2.
If the model agrees with one convention and not the other, the disagreement is located in the
DE-VIG, not in the mass tables - which is a different defect with a different fix.

Prices here are DECIMAL, matching clv_ledger.two_way.
"""

KEYS_FOOTBALL = (3.0, 7.0, 10.0, 14.0)
FOOTBALL = ("NFL", "NCAAF")
# Leagues whose line_value MASS rows are published estimates rather than measured here.
ESTIMATED_MASS = ("NCAAB", "NCAAF")
PP = 100.0          # probability points
MIN_N_OVERALL = 30
MIN_N_SUBGROUP = 20
GAP_SIGNED_MAX = 1.0
GAP_ABS_MAX = 2.0
GAP_OUTLIER = 3.0
TS_TIGHT = 15.0     # minutes: the four prices count as near-simultaneous within this spread


def overround(da, db):
    """Book margin on a two-way market, as a fraction. 0.04 = a 4% hold."""
    if not da or not db or da <= 1 or db <= 1:
        raise ValueError("decimal prices must exceed 1")
    return 1.0 / da + 1.0 / db - 1.0


def devig_proportional(da, db):
    """Side A's fair chance, margin split in proportion to probability. == novig_p."""
    ia, ib = 1.0 / da, 1.0 / db
    return ia / (ia + ib)


def devig_even(da, db):
    """Side A's fair chance, each side carrying half the margin."""
    return 1.0 / da - overround(da, db) / 2.0


def margin_share_a(da, db):
    """Fraction of the total margin that side A carries under the OBSERVED prices.

    Reported, never assumed: under proportional de-vig this equals A's fair chance by
    construction, so a value far from that is evidence the book is not pricing alts
    proportionally.
    """
    o = overround(da, db)
    if o <= 0:
        return None
    return (1.0 / da - devig_proportional(da, db)) / o


def ts_spread(ts_ages):
    """Minutes between the OLDEST and NEWEST of the four prices, or None if not recorded.

    The four quotes are independent last-ticks at or before kick, NOT one simultaneous reading.
    A wide spread is a confound on the overround comparison: a stale alt quote widens the alt
    overround and is indistinguishable, in the number alone, from genuine alt vig.
    """
    if not ts_ages or len(ts_ages) != 4 or any(x is None for x in ts_ages):
        return None
    return max(ts_ages) - min(ts_ages)


def crosses_key(our_line, main_line, league):
    """Does the move between the two numbers cross a football key number?"""
    if league not in FOOTBALL:
        return False
    lo, hi = sorted((abs(float(our_line)), abs(float(main_line))))
    return any(lo < k < hi for k in KEYS_FOOTBALL)


def distance_bucket(our_line, main_line):
    d = abs(abs(float(our_line)) - abs(float(main_line)))
    if d <= 0.5:
        return "<=0.5"
    if d <= 1.0:
        return "0.5-1"
    if d <= 2.0:
        return "1-2"
    if d <= 3.0:
        return "2-3"
    return ">3"


def summarize(gaps):
    """n, mean, sd, standard error, 95% CI, mean absolute, and the share beyond 3pp.

    Gaps are passed as fractions and reported in probability POINTS. The CI is what the
    sample can support: at small n a mean inside a threshold proves nothing on its own.
    """
    n = len(gaps)
    if not n:
        return {"n": 0}
    g = [x * PP for x in gaps]
    mean = sum(g) / n
    if n > 1:
        var = sum((x - mean) ** 2 for x in g) / (n - 1)
        sd = var ** 0.5
        se = sd / (n ** 0.5)
    else:
        sd = se = float("nan")
    half = 1.96 * se if n > 1 else float("nan")
    return {"n": n, "mean": mean, "sd": sd, "se": se,
            "ci_lo": mean - half, "ci_hi": mean + half,
            "mean_abs": sum(abs(x) for x in g) / n,
            "share_over_3": sum(1 for x in g if abs(x) > GAP_OUTLIER) / n}


def verdict(st, min_n=MIN_N_OVERALL):
    """PASS / FAIL / INCONCLUSIVE against the PRE-REGISTERED thresholds, plus the reason.

    Thin coverage is never a PASS, and point estimates inside the thresholds with a 95% CI
    that escapes them are INCONCLUSIVE: the sample cannot separate the hypotheses.
    """
    n = st.get("n", 0)
    if n < min_n:
        return "INCONCLUSIVE", f"n {n} below the registered minimum {min_n}"
    if abs(st["mean"]) > GAP_SIGNED_MAX:
        return "FAIL", f"mean signed gap {st['mean']:+.2f}pp outside +/-{GAP_SIGNED_MAX}pp"
    if st["mean_abs"] > GAP_ABS_MAX:
        return "FAIL", f"mean absolute gap {st['mean_abs']:.2f}pp above {GAP_ABS_MAX}pp"
    if not (st["ci_lo"] >= -GAP_SIGNED_MAX and st["ci_hi"] <= GAP_SIGNED_MAX):
        return "INCONCLUSIVE", (f"point estimates pass but the 95% CI "
                                f"[{st['ci_lo']:+.2f}, {st['ci_hi']:+.2f}]pp "
                                f"escapes +/-{GAP_SIGNED_MAX}pp")
    return "PASS", (f"mean {st['mean']:+.2f}pp, 95% CI "
                    f"[{st['ci_lo']:+.2f}, {st['ci_hi']:+.2f}]pp, mean abs "
                    f"{st['mean_abs']:.2f}pp on n {n} - SCREEN ONLY, not authorization")


def analyze(rows):
    """rows: dicts with league, our_line, main_line, v2_p, alt_a, alt_b, main_a, main_b,
    better (bool: did the move favour the side we hold).

    alt_* / main_* are the OBSERVED two-sided decimal prices at the same closing tick, with
    side A being the side we hold. A row missing either pair is UNRECOVERABLE: it is counted
    and reported, never estimated and never counted as agreement.
    """
    out = {"gap_prop": [], "gap_even": [], "or_main": [], "or_alt": [], "or_diff": [],
           "margin_share_a": [], "unrecoverable": 0, "by": {}, "rows": [],
           "ts_spread": [], "gap_prop_tight": [], "or_diff_tight": [], "ts_missing": 0}
    for r in rows:
        if not all(r.get(k) for k in ("alt_a", "alt_b", "main_a", "main_b")) or r.get("v2_p") is None:
            out["unrecoverable"] += 1
            continue
        try:
            or_m = overround(r["main_a"], r["main_b"])
            or_a = overround(r["alt_a"], r["alt_b"])
            mkt_prop = devig_proportional(r["alt_a"], r["alt_b"])
            mkt_even = devig_even(r["alt_a"], r["alt_b"])
            share = margin_share_a(r["alt_a"], r["alt_b"])
        except (ValueError, ZeroDivisionError):
            out["unrecoverable"] += 1
            continue
        gp, ge = r["v2_p"] - mkt_prop, r["v2_p"] - mkt_even
        out["gap_prop"].append(gp)
        out["gap_even"].append(ge)
        out["or_main"].append(or_m)
        out["or_alt"].append(or_a)
        out["or_diff"].append(or_a - or_m)
        if share is not None:
            out["margin_share_a"].append(share)
        lg = r.get("league") or "?"
        for b in (f"league {lg}",
                  "move favourable" if r.get("better") else "move unfavourable",
                  f"distance {distance_bucket(r['our_line'], r['main_line'])}",
                  ("football crosses a key number" if crosses_key(r["our_line"], r["main_line"], lg)
                   else ("football, no key number crossed" if lg in FOOTBALL else None))):
            if b:
                out["by"].setdefault(b, []).append(gp)
        sp = ts_spread(r.get("ts_ages"))
        if sp is None:
            out["ts_missing"] += 1
        else:
            out["ts_spread"].append(sp)
            if sp <= TS_TIGHT:
                out["gap_prop_tight"].append(gp)
                out["or_diff_tight"].append(or_a - or_m)
        out["rows"].append(dict(r, gap_prop=gp, gap_even=ge, or_alt=or_a, or_main=or_m,
                                mkt_prop=mkt_prop, mkt_even=mkt_even, margin_share_a=share,
                                ts_spread=sp))
    return out


def report(res):
    """Lines for the ledger log. Counts, points and percentages only - no money, ever."""
    L = []
    st = summarize(res["gap_prop"])
    ste = summarize(res["gap_even"])
    if not st.get("n"):
        L.append(f"V2 CALIBRATION: no recoverable moved-line rows yet "
                 f"(unrecoverable {res['unrecoverable']}) - INCONCLUSIVE")
        return L
    v, why = verdict(st)
    L.append(f"V2 CALIBRATION VERDICT: {v} - {why}")
    L.append(f"  model vs market (PROPORTIONAL de-vig, what V1 uses): n {st['n']}, "
             f"mean {st['mean']:+.2f}pp, 95% CI [{st['ci_lo']:+.2f}, {st['ci_hi']:+.2f}]pp, "
             f"mean abs {st['mean_abs']:.2f}pp, beyond {GAP_OUTLIER}pp {st['share_over_3']:.0%}")
    L.append(f"  model vs market (EVEN margin split): n {ste['n']}, mean {ste['mean']:+.2f}pp, "
             f"95% CI [{ste['ci_lo']:+.2f}, {ste['ci_hi']:+.2f}]pp, mean abs {ste['mean_abs']:.2f}pp")
    L.append("  (if the model agrees with one convention and not the other, the defect is in the "
             "DE-VIG allocation, not in the mass tables)")
    if res["or_main"]:
        n = len(res["or_main"])
        am, aa = sum(res["or_main"]) / n, sum(res["or_alt"]) / n
        ad = sum(res["or_diff"]) / n
        L.append(f"  overround: main {am:.2%}, alt {aa:.2%}, alt-minus-main {ad:+.2%} on n {n}")
        if res["margin_share_a"]:
            ms = sum(res["margin_share_a"]) / len(res["margin_share_a"])
            L.append(f"  margin carried by the side we hold: {ms:.0%} of the alt margin "
                     f"(proportional de-vig forces this to equal that side's fair chance)")
        L.append("  a higher alt overround alone does NOT prove V2 is right - it shows alts carry "
                 "more margin, not that V2's size or allocation of the correction is correct")
    if res.get("ts_spread"):
        sp = sorted(res["ts_spread"])
        n = len(sp)
        med = sp[n // 2] if n % 2 else (sp[n // 2 - 1] + sp[n // 2]) / 2
        tight = sum(1 for x in sp if x <= TS_TIGHT)
        L.append(f"  TIMESTAMP SPREAD of the four prices (independent last-ticks, NOT one quote): "
                 f"median {med:.0f} min, mean {sum(sp) / n:.0f} min, max {sp[-1]:.0f} min; "
                 f"within {TS_TIGHT:.0f} min {tight}/{n}")
        ts = summarize(res["gap_prop_tight"])
        if ts.get("n"):
            tv, twhy = verdict(ts)
            od = res["or_diff_tight"]
            L.append(f"  SENSITIVITY on near-simultaneous rows only (spread <= {TS_TIGHT:.0f} min): "
                     f"n {ts['n']}, mean {ts['mean']:+.2f}pp, 95% CI "
                     f"[{ts['ci_lo']:+.2f}, {ts['ci_hi']:+.2f}]pp -> {tv}"
                     + (f" ({twhy})" if tv != "PASS" else "")
                     + (f"; alt-minus-main overround {sum(od) / len(od):+.2%}" if od else ""))
            L.append("  if the full-sample and near-simultaneous results disagree, the overround gap "
                     "is contaminated by STALENESS, not evidence of alt vig")
        else:
            L.append(f"  SENSITIVITY: no row has all four prices within {TS_TIGHT:.0f} min - the "
                     f"overround comparison cannot be separated from staleness on this sample")
    if res.get("ts_missing"):
        L.append(f"  rows with no timestamps recorded (scored before the capture landed): {res['ts_missing']}")
    L.append(f"  unrecoverable rows (no two-sided quote held, never estimated): {res['unrecoverable']}")
    for b in sorted(res["by"]):
        s = summarize(res["by"][b])
        bv, bwhy = verdict(s, MIN_N_SUBGROUP)
        tag = " [MASS = published estimate]" if any(e in b for e in ESTIMATED_MASS) else ""
        L.append(f"  {b}{tag}: n {s['n']}, mean {s['mean']:+.2f}pp"
                 + (f", 95% CI [{s['ci_lo']:+.2f}, {s['ci_hi']:+.2f}]pp" if s["n"] > 1 else "")
                 + f" -> {bv}" + ("" if bv == "PASS" else f" ({bwhy})"))
    L.append("  DISTANCE CANNOT separate alt-line vig from conversion-model error - both grow with "
             "distance. No causal claim is made from the distance buckets.")
    L.append("  SCREEN ONLY: a numerical PASS does not authorize promotion. V1 official, V2 shadow.")
    return L

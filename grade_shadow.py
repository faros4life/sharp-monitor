#!/usr/bin/env python3
"""SHADOW GRADING LADDER - report only. Nothing here promotes, kills, resizes or switches anything.

Peter, Nov 22 2026: "I agree CLV should not be the biggest data point that makes us make a play.
Let's revisit how we grade." Approved as a REPORT-ONLY shadow with safeguards (issue #5):

  - CLV_STANDARD.md is untouched. That document governs how CLV is CALCULATED; this governs how a
    bucket is GRADED. Separate questions, separate files.
  - splits.py keeps its production ladder and its kill semantics. This module reads; it writes
    nothing back and imports nothing from the live decision path.
  - PROMOTE is labelled "ELIGIBLE FOR HUMAN REVIEW - NO AUTO DEPLOY". There is no auto-deploy.

WHY THE LADDER NEEDS CHANGING. The production bar is a POINT ESTIMATE: >= 30 forward resulted and
>= +0.10u/play. Three buckets cleared that on Nov 22 with 95% intervals running through zero. And
CLV had no defined role at all, which is how a lane with +2.38c closing-line value and +0.006u/play
of measured profit came within one decision of being switched on.

THE DIVERGENCE THIS IS BUILT AROUND. Measured Nov 22 on the same rows, three times independently:
the slice with the BEST closing-line value had the WORST outcomes.
    NBA totals, lead 12h+     CLV +4.43c   outcomes +0.038u/play
    NCAAB spreads, lead 4h+   CLV +2.41c   outcomes +0.065u/play
    NCAAB spreads, under 4h   CLV +0.75c   outcomes +0.168u/play
Plausibly because an alert twelve hours out beats a close the market then moves several more times.
Whatever the cause, a single pooled CLV number hides it, so every bucket is reported BY LEAD BAND,
and CLV can never promote on its own.

THE FOUR GATES (pre-specified here, before any bucket was graded with them; no post-hoc tuning):
  1. SAMPLE     n >= 30 forward resulted. Below that: NO VERDICT, full stop.
  2. OUTCOME    95% CI LOWER bound on units/play > 0. Not the point estimate.
  3. STABILITY  both DISJOINT halves positive. Halves, not the rolling windows - see below.
  4. PRICE      CLV CI lower bound > 0 on the SAME matched rows, at >= MIN_COVERAGE coverage.
                Necessary to promote. NEVER sufficient.
Any gate that cannot be evaluated - no CLV, no lead minutes, n < 2 for an interval - returns
INSUFFICIENT EVIDENCE. It never returns a pass.

OVERLAPPING WINDOWS. Week, fortnight and month are NESTED: the month contains the fortnight contains
the week. Three agreeing windows is ONE observation looked at three ways, not three replications,
and reporting them as confirmation would overstate the evidence threefold. They are printed for
shape only and labelled overlapping. Gate 3 uses two DISJOINT halves of the sample instead, which
is the only split here that is genuinely two looks at different data.

CLV SOURCES ARE NOT POOLED. Board/liquidity rows carry `clv_cents` - cents against the board's own
close. The ledger carries Pinnacle no-vig percent under CLV_STANDARD.md. Different instruments on
different scales; this module reports the cents basis and labels it, and never mixes the two into
one figure.

THE KILL RULE IS NOT CHANGED HERE. Peter, Nov 22: a sticky permanent close on a point estimate is a
LOWER evidential bar than promotion, for the more irreversible action, and ordinary variance can
trip it. He is right. But changing kill semantics mid-shadow would be the silent replacement the
safeguards forbid, so production kill logic is untouched and this module only REPORTS what a
symmetric CI-based kill would have said, as a pre-registration for separate approval.
"""
import json
import math
import os
import statistics as st

# ---- pre-specified thresholds. Set before grading; not tuned against results. ----------------
MIN_N = 30             # gate 1
MIN_COVERAGE = 0.80    # gate 4: share of resulted rows carrying a CLV value
Z = 1.96               # normal 95%. Promotion requires n >= 30, where normal and t agree closely;
                       # intervals printed for smaller n are labelled approximate.
LEAD_BANDS = (("under 4h", 0, 240), ("4-12h", 240, 720), ("12h+", 720, 10 ** 9))

PROMOTE = "ELIGIBLE FOR HUMAN REVIEW - NO AUTO DEPLOY"
WATCH = "WATCH"
INSUFFICIENT = "INSUFFICIENT EVIDENCE"
NO_VERDICT = "NO VERDICT (n < 30)"


def ci(values):
    """(n, mean, se, lo, hi) or None. A single observation has no interval - that is INSUFFICIENT,
    never a pass."""
    v = [float(x) for x in values if x is not None]
    if len(v) < 2:
        return None
    n = len(v)
    m = sum(v) / n
    se = st.stdev(v) / math.sqrt(n)
    return n, m, se, m - Z * se, m + Z * se


def resulted(rows):
    return [r for r in rows if r.get("result") in ("W", "L", "P") and r.get("units_flat") is not None]


def halves(rows, key="first_seen_utc"):
    """Two DISJOINT halves by time. Gate 3 needs two looks at different data; the rolling windows
    are nested and cannot provide that."""
    rs = sorted(rows, key=lambda r: str(r.get(key) or r.get("alerted_utc") or ""))
    h = len(rs) // 2
    return rs[:h], rs[h:]


def outcome(rows):
    return ci([r["units_flat"] for r in resulted(rows)])


def clv(rows):
    """(interval, coverage) on the SAME resulted rows the outcome is measured on, so a lead-filtered
    CLV figure and a lead-filtered outcome figure are never different populations."""
    rs = resulted(rows)
    if not rs:
        return None, 0.0
    vals = [r.get("clv_cents") for r in rs]
    have = [v for v in vals if v is not None]
    return ci(have), (len(have) / len(rs))


def old_verdict(rows):
    """splits.py as it stands today: a POINT estimate both ways. Reported for comparison only - this
    function is a read of the production rule, not a copy that production uses."""
    o = outcome(rows)
    if o is None:
        return NO_VERDICT, "no resulted rows"
    n, m, _se, _lo, _hi = o
    if n < MIN_N:
        return NO_VERDICT, f"n={n}"
    if m <= -0.10:
        return "CLOSED (sticky)", f"{m:+.3f}/play on n={n}"
    if m >= 0.10:
        return "ELIGIBLE", f"{m:+.3f}/play on n={n}"
    return "OPEN", f"{m:+.3f}/play on n={n}"


def new_verdict(rows, need_lead=True):
    """The four gates. Returns (verdict, per-gate detail). Never promotes on price alone."""
    g = {}
    o = outcome(rows)
    if o is None:
        return INSUFFICIENT, {"sample": "no interval possible (n < 2)"}
    n, m, _se, lo, hi = o
    g["sample"] = f"n={n}" + ("" if n >= MIN_N else f" (< {MIN_N})")
    if n < MIN_N:
        return NO_VERDICT, g

    if need_lead and not any(r.get("lead_min") is not None for r in resulted(rows)):
        g["lead"] = "no lead minutes on these rows"
        return INSUFFICIENT, g

    g["outcome"] = f"{m:+.3f}/play, 95% [{lo:+.3f},{hi:+.3f}]"
    gate_outcome = lo > 0

    a, b = halves(rows)
    oa, ob = outcome(a), outcome(b)
    if oa is None or ob is None:
        g["stability"] = "a half has no interval"
        return INSUFFICIENT, g
    g["stability"] = f"halves {oa[1]:+.3f} / {ob[1]:+.3f} (disjoint, n={oa[0]}/{ob[0]})"
    gate_stab = oa[1] > 0 and ob[1] > 0

    c, cov = clv(rows)
    if c is None:
        g["price"] = f"no usable CLV (coverage {cov:.0%})"
        return INSUFFICIENT, g
    g["price"] = f"{c[1]:+.2f}c, 95% [{c[3]:+.2f},{c[4]:+.2f}], coverage {cov:.0%}"
    if cov < MIN_COVERAGE:
        return INSUFFICIENT, g
    gate_price = c[3] > 0

    if gate_outcome and gate_stab and gate_price:
        return PROMOTE, g
    return WATCH, g


def kill_preregistration(rows):
    """NOT APPLIED. What a SYMMETRIC, interval-based kill would say, recorded so a future revision is
    pre-registered rather than fitted later. Production kill semantics are unchanged by this module.

    Symmetry with gate 2: promotion needs the CI lower bound above zero, so a close needs the CI
    UPPER bound below zero. And a close under it would be SUSPENDED (reversible) rather than sticky,
    because the asymmetry Peter identified is between the strength of evidence and the permanence of
    the action, not between the two directions."""
    o = outcome(rows)
    if o is None or o[0] < MIN_N:
        return "no call"
    n, m, _se, _lo, hi = o
    return f"SUSPEND (reversible): CI upper {hi:+.3f} < 0" if hi < 0 else f"keep: CI upper {hi:+.3f}"


def load_feed(root="."):
    rows = []
    for p in ("liquidity/alerts.json", "liquidity-extra/alerts.json"):
        try:
            d = json.load(open(os.path.join(root, p), encoding="utf-8"))
        except Exception:
            continue
        r = d.get("alerts") if isinstance(d, dict) else d
        rows += list(r.values()) if isinstance(r, dict) else (r or [])
    return rows


def size_of(r):
    return float(r.get("new_money") or r.get("base_depth") or 0)


def report(root="."):
    rows = load_feed(root)
    nba = [r for r in rows if r.get("league") == "NBA" and r.get("market") == "total"]
    ncs = [r for r in rows if r.get("league") == "NCAAB" and r.get("market") == "spread"
           and (r.get("book") or "").lower() == "kalshi"]
    buckets = [("NBA totals - whole lane", nba),
               ("NBA totals - $25-50k prints", [r for r in nba if 25000 <= size_of(r) <= 50000]),
               ("NBA totals - over $50k", [r for r in nba if size_of(r) > 50000]),
               ("NCAAB spreads (NCS) - all", ncs)]
    for lab, src in (("NBA totals", nba), ("NCAAB spreads (NCS)", ncs)):
        for name, lo, hi in LEAD_BANDS:
            buckets.append((f"{lab} - lead {name}",
                            [r for r in src if lo <= (r.get("lead_min") or 0) < hi]))
    out = ["SHADOW GRADING LADDER - REPORT ONLY. Nothing is promoted, killed, resized or switched.",
           "CLV here is CENTS vs the board close. It is NOT the Pinnacle no-vig percent of",
           "CLV_STANDARD.md, and the two are never pooled.",
           "Rolling week/fortnight/month windows are NESTED and are not independent replications;",
           f"stability is therefore measured on two DISJOINT halves. Gates: n>={MIN_N}, outcome CI",
           f"lower >0, both halves >0, CLV CI lower >0 at >={MIN_COVERAGE:.0%} coverage.", ""]
    for name, rs in buckets:
        ov, od = old_verdict(rs)
        nv, g = new_verdict(rs)
        out.append(f"{name}")
        out.append(f"   OLD (production, point estimate): {ov}   [{od}]")
        out.append(f"   NEW (four gates):                 {nv}")
        for k in ("sample", "outcome", "stability", "price", "lead"):
            if k in g:
                out.append(f"       {k:9s} {g[k]}")
        out.append(f"       kill (PRE-REGISTERED, NOT APPLIED): {kill_preregistration(rs)}")
        out.append(f"       {'DISAGREE' if (ov == 'ELIGIBLE') != (nv == PROMOTE) else 'agree'}")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    print(report(os.path.dirname(os.path.abspath(__file__)) or "."))

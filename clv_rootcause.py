#!/usr/bin/env python3
"""PRIORITY 6 ROOT-CAUSE AUDIT - why do profitable groups carry negative CLV? (Peter, 9 Nov)

READ-ONLY. No bet, no rule, no threshold, no file written. Zero OddsPapi credits.

WHY THIS SCRIPT EXISTS RATHER THAN A SLICE OF clv_scorecard. The liquidity population's stored
close_price is the TRIGGER VENUE'S OWN last pregame price - liquidity_monitor says so in its own
export note: "close_price = last pregame price; clv_cents = close_price - price". That is EXCHANGE
SELF-CLOSE PRICE MOVEMENT, and CLV_STANDARD.md section 4 is explicit: it "stays separate, is never
labelled Pinnacle CLV, and is never used as a CLV gate."

My first scorecard labelled those figures CLV. They were not. This script recomputes the same
groups against PINNACLE VERIFIED SAME-LINE closes - clv_ledger.find_fixture + close_for, the same
path clv_report uses - so the question is answered on the standard's basis and the two quantities
can be compared side by side instead of confused.

THAT COMPARISON IS ITSELF THE FIRST CANDIDATE ROOT CAUSE. If a group looks profitable on its own
venue's close but negative against Pinnacle's, the group is not beating the market; it is being
measured against a price that moved with it.

PRESPECIFIED ONLY. Peter: "Identify any prespecified subsets that remain positive in both halves,
but don't optimize rules retrospectively." Every slice below is a REGISTERED one (registry 9
LIQ-BOT 4h+, registry 13 LIQ-SMALL $25-50k, the NBA UNDER signal) or a plain descriptive
dimension he named (market, league, timing, liquidity, new money). No threshold is searched, no
cut is chosen by looking at the result, and nothing here becomes a rule.

WHAT CANNOT BE DONE HERE, stated rather than fudged:
  * P-LIMIT LOW. The liquidity population carries NO Pinnacle-limit field - 0 of 2,245 rows. The
    P-limit dimension and the P-limit LOW candidate cannot be audited from this data at all. It
    needs Item 56's own records. Reported as a gap, not approximated.
  * Rows with no verified same-line Pinnacle close are EXCLUDED and counted. No modelled or
    converted close is substituted, per the standard.

COST: cache-only. An uncached fixture is excluded, never bought, and clv/markets.json is read off
disk rather than through load_markets(), which BILLS once that file is 7 days old.
"""
import json
import os
import re
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
LIQ = os.environ.get("RC_LIQ", "") or "liquidity/alerts.json"
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL", "NCAAB")
L = []


def say(t=""):
    L.append(t)
    print(t)


def tp(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def toks(s):
    return set(re.findall(r"[a-z]{3,}", str(s or "").lower()))


def units(rows):
    t = 0.0
    for r in rows:
        am, res = r["am"], r["res"]
        if am is None or res == "P":
            continue
        t += (am / 100 if am > 0 else 100 / abs(am)) if res == "W" else -1.0
    return t


def ngames(rows):
    return len({(r["day"], frozenset(toks(r["game"]))) for r in rows})


def block(label, rows, key=None, indent=4):
    """One line per slice. 'pin' is Pinnacle verified same-line CLV; 'self' is the venue's own
    close movement, shown beside it so the two are never mistaken for each other again."""
    pad = " " * indent
    use = [r for r in rows if r["pin"] is not None]
    if not use:
        say(f"{pad}{label:34s} n 0 verified of {len(rows)}")
        return
    u = units(use)
    risk = sum(1.0 for r in use if r["res"] in ("W", "L"))
    pin = st.mean(r["pin"] for r in use)
    beat = sum(1 for r in use if r["pin"] > 0)
    selfv = [r["self"] for r in use if r["self"] is not None]
    sm = (f"{st.mean(selfv):+6.2f}c" if selfv else "     -")
    say(f"{pad}{label:34s} n {len(use):4d} | g {ngames(use):4d} | {u:+7.2f}u | "
        f"ROI {(100 * u / risk if risk else 0):+6.1f}% | PIN CLV {pin:+6.2f}% | "
        f"beat {beat:4d}/{len(use):<4d} {100 * beat / len(use):4.1f}% | self {sm}")


def halves(label, rows):
    """Peter's first-versus-second-half test, and the both-halves-positive verdict."""
    use = sorted([r for r in rows if r["pin"] is not None], key=lambda r: r["day"])
    if len(use) < 4:
        say(f"    {label:34s} too few verified rows to split ({len(use)})")
        return None
    h = len(use) // 2
    a, b = use[:h], use[h:]
    ca, cb = st.mean(r["pin"] for r in a), st.mean(r["pin"] for r in b)
    ua, ub = units(a), units(b)
    say(f"    {label}")
    block("H1", a, indent=6)
    block("H2", b, indent=6)
    both = ca > 0 and cb > 0
    say(f"      both halves positive on PINNACLE CLV: {'YES' if both else 'NO'}"
        f"  (H1 {ca:+.2f}%, H2 {cb:+.2f}%; units {ua:+.2f}u / {ub:+.2f}u)")
    return both


def main():
    now = datetime.now(timezone.utc)
    say("PRIORITY 6 - ROOT-CAUSE AUDIT OF NEGATIVE CLV (read-only, zero credits)")
    say(cs.stamp())
    say("")
    say("TWO DIFFERENT QUANTITIES, kept apart from here on:")
    say("  PIN CLV  (Pinnacle no-vig VERIFIED SAME-LINE close x net entry decimal after fees - 1)")
    say("           - the standard's basis, and the only thing called CLV below.")
    say("  self     the TRIGGER VENUE'S own last pregame price minus entry, in probability cents.")
    say("           liquidity_monitor's stored clv_cents. Exchange Self-Close Price Movement.")
    say("           CLV_STANDARD.md s4: never labelled Pinnacle CLV, never a CLV gate.")
    say("")
    say(f"NET OF FEES, explicitly: every entry price goes through clv_std.net_dec() under fee model")
    say(f"  {cs.FEE_MODEL} before any CLV is taken - Kalshi 0.07 taker, Polymarket US 0.06,")
    say("  Novig 0 pre-game, ProphetX 2% of net gains (NHL 0.035). A raw screen price is never used.")

    # ---------------------------------------------------------------- population
    try:
        Q = json.load(open(LIQ))
        Q = Q if isinstance(Q, list) else (Q.get("alerts") or [])
    except Exception as e:
        say(f"\n{LIQ} unreadable ({type(e).__name__})")
        return 1

    st_ = {"fixtures": {}, "fx_last": {}}
    try:
        prev = tb.dec(json.load(open(cl.STATE)))
        st_["fixtures"] = dict(prev.get("fixtures") or {})
        say(f"\nfixture cache: {len(st_['fixtures'])} fixtures read from disk - nothing purchased")
    except Exception as e:
        say(f"\nfixture cache unavailable ({type(e).__name__}) - cannot verify closes, stopping")
        return 1
    try:
        _mk = json.load(open(cl.MKFILE))
        mkmap = _mk.get("m") or {}
        age = (now - cl.tp(_mk["fetched"])).days
        say(f"market map: {len(mkmap)} entries, {age}d old, read off disk - load_markets() not called"
            + ("  (it BILLS past 7d, which is why)" if age >= 6 else ""))
    except Exception as e:
        mkmap = {}
        say(f"market map unavailable ({type(e).__name__}) - closes needing a market id will be excluded")

    rows, exc = [], Counter()
    for x in Q:
        if x.get("result") not in ("W", "L", "P") or x.get("artifact") or x.get("close_suspect"):
            continue
        lg = x.get("league") or x.get("sport")
        if lg not in LEAGUES:
            exc["league out of scope"] += 1
            continue
        b = {"bet": x.get("bet") or f"{x.get('side')} {x.get('line') or ''}".strip(),
             "league": lg, "game": x.get("game"),
             "game_start": x.get("start_utc"), "book": x.get("book")}
        am = x.get("price_american")
        rec = {"day": str(x.get("alerted_utc") or "")[:10], "game": x.get("game"), "lg": lg,
               "mk": x.get("market"), "side": x.get("side"), "book": x.get("book"),
               "am": am, "res": x.get("result"),
               "lead": x.get("lead_min"), "depth": x.get("base_depth"),
               "new_money": x.get("new_money"), "rule_met": x.get("rule_met"),
               "self": x.get("clv_cents"), "pin": None, "circa": None, "ps3838": None}
        fid = cl.find_fixture(st_, b)
        if not fid:
            exc["no fixture matched"] += 1
            rows.append(rec)
            continue
        f = st_["fixtures"][fid]
        start = cl.tp(f.get("start")) or cl.tp(x.get("start_utc"))
        if not start or now - start < hc.FINAL_AFTER:
            exc["game not final"] += 1
            rows.append(rec)
            continue
        if not os.path.exists(hc._path(fid, "pinnacle")):
            exc["Pinnacle close not in cache (not bought)"] += 1
            rows.append(rec)
            continue
        h = hc.get_hist(fid, ["pinnacle"], start)
        if isinstance(h, dict) and h.get("_error"):
            exc["history error"] += 1
            rows.append(rec)
            continue
        c, why = cl.close_for(b, f, cl.book_markets(h, "pinnacle"), mkmap, start, lg)
        if not c:
            exc[f"no verified same-line close"] += 1
            rows.append(rec)
            continue
        if am is None or not rec["book"]:
            exc["no entry price / venue"] += 1
            rows.append(rec)
            continue
        try:
            nd = cs.net_dec(cs.canon(rec["book"]), cl.am_to_dec(am))
        except Exception:
            exc["venue not tradeable for us"] += 1
            rows.append(rec)
            continue
        rec["pin"] = 100 * (c["p"] * nd - 1)
        # Peter, 9 Nov: "look at circa net fees compare". Same net entry decimal, a DIFFERENT
        # closing anchor - so this isolates the anchor, which is the whole point. Circa and ps3838
        # carry their vig in the price and take no commission, so there is no fee on the CLOSE;
        # the fee is on OUR entry, and it is already in nd.
        for bk2, fld in (("circasports", "circa"), ("ps3838", "ps3838")):
            if not os.path.exists(hc._path(fid, bk2)):
                continue
            h2 = hc.get_hist(fid, [bk2], start)
            if isinstance(h2, dict) and h2.get("_error"):
                continue
            c2, _ = cl.close_for(b, f, cl.book_markets(h2, bk2), mkmap, start, lg)
            if c2:
                rec[fld] = 100 * (c2["p"] * nd - 1)
        rows.append(rec)

    ver = [r for r in rows if r["pin"] is not None]
    say("")
    say("=" * 118)
    say("GUARD 2 - population and exclusions")
    say("=" * 118)
    say(f"  graded liquidity alerts in scope        {len(rows)}")
    for k, n in exc.most_common():
        say(f"    excluded, {k:44s} {n:5d}")
    say(f"  with a VERIFIED same-line Pinnacle close {len(ver)}"
        + (f"  ({100 * len(ver) / len(rows):.1f}% coverage)" if rows else ""))
    if not ver:
        say("\n  No verified close available - no CLV verdict can be given. That is the finding.")
        _send()
        return 0

    # ---------------------------------------------------------------- the headline contrast
    say("")
    say("=" * 118)
    say("ROOT CAUSE 1 - WHICH CLOSE IS THE PROFIT MEASURED AGAINST?")
    say("=" * 118)
    sv = [r for r in ver if r["self"] is not None]
    if sv:
        pin = st.mean(r["pin"] for r in sv)
        slf = st.mean(r["self"] for r in sv)
        bp = sum(1 for r in sv if r["pin"] > 0)
        bs = sum(1 for r in sv if r["self"] > 0)
        say(f"  on the SAME {len(sv)} rows:")
        say(f"    Pinnacle verified same-line CLV   {pin:+.2f}%   beat {bp}/{len(sv)} = {100 * bp / len(sv):.1f}%")
        say(f"    trigger venue's own close move    {slf:+.2f}c   'beat' {bs}/{len(sv)} = {100 * bs / len(sv):.1f}%")
        say("  If the venue's own close flatters these groups and Pinnacle's does not, the groups are")
        say("  not beating the market - they are being graded against a price that moved with them.")

    # ---------------------------------------------------------------- registered candidates
    say("")
    say("=" * 118)
    say("REGISTERED CANDIDATES - pass/fail on the standard's basis")
    say("=" * 118)
    nbat = [r for r in ver if r["lg"] == "NBA" and r["mk"] == "total"]
    cands = [
        ("LIQ-BOT: NBA totals, 4h+ lead (registry 9)",
         [r for r in nbat if r["lead"] is not None and r["lead"] >= 240]),
        ("LIQ-SMALL: NBA totals $25-50k prints (registry 13)",
         [r for r in nbat if r["new_money"] is not None and 25000 <= r["new_money"] <= 50000]),
        ("NBA UNDER signal",
         [r for r in nbat if r["side"] == "UNDER"]),
    ]
    verdicts = {}
    for nm, rs in cands:
        say("")
        block(nm, rs, indent=2)
        verdicts[nm] = halves("by half:", rs)

    # ---------------------------------------------------------------- the dimensions he asked for
    say("")
    say("=" * 118)
    say("DESCRIPTIVE BREAKDOWNS - dimensions Peter named. Descriptive only; no cut is a rule.")
    say("=" * 118)
    say("\n  by MARKET")
    for m in sorted({r["mk"] for r in ver if r["mk"]}):
        block(m, [r for r in ver if r["mk"] == m])
    say("\n  by LEAGUE")
    for g in sorted({r["lg"] for r in ver if r["lg"]}):
        block(g, [r for r in ver if r["lg"] == g])
    say("\n  by ENTRY TIMING (lead time to tip)")
    for lbl, lo, hi in (("under 1h", 0, 60), ("1-4h", 60, 240), ("4-12h", 240, 720), ("12h+", 720, 10 ** 9)):
        block(lbl, [r for r in ver if r["lead"] is not None and lo <= r["lead"] < hi])
    say("\n  by LIQUIDITY (base depth, quartiles of the verified sample)")
    dv = sorted(r["depth"] for r in ver if r["depth"] is not None)
    if len(dv) >= 8:
        q = [dv[len(dv) // 4], dv[len(dv) // 2], dv[3 * len(dv) // 4]]
        bands = [("Q1 lowest", 0, q[0]), ("Q2", q[0], q[1]), ("Q3", q[1], q[2]), ("Q4 highest", q[2], 10 ** 18)]
        for lbl, lo, hi in bands:
            block(f"{lbl} (<= {hi:,.0f})" if hi < 10 ** 18 else f"{lbl} (> {lo:,.0f})",
                  [r for r in ver if r["depth"] is not None and lo <= r["depth"] < hi])
    say("\n  by NEW MONEY (quartiles of the verified sample)")
    nv = sorted(r["new_money"] for r in ver if r["new_money"] is not None)
    if len(nv) >= 8:
        q = [nv[len(nv) // 4], nv[len(nv) // 2], nv[3 * len(nv) // 4]]
        for lbl, lo, hi in (("Q1 lowest", 0, q[0]), ("Q2", q[0], q[1]), ("Q3", q[1], q[2]), ("Q4 highest", q[2], 10 ** 18)):
            block(f"{lbl} (<= {hi:,.0f})" if hi < 10 ** 18 else f"{lbl} (> {lo:,.0f})",
                  [r for r in ver if r["new_money"] is not None and lo <= r["new_money"] < hi])

    say("\n  by PINNACLE LIMIT")
    say("    NOT AVAILABLE. The liquidity population carries no Pinnacle-limit field - 0 of 2,245")
    say("    rows. This dimension, and the P-LIMIT LOW candidate itself, cannot be audited from")
    say("    this data. It needs Item 56's own records. Reported as a gap, not approximated.")

    # ---------------------------------------------------------------- Circa as a second anchor
    say("")
    say("=" * 118)
    say("ROOT CAUSE 2 - IS PINNACLE'S CLOSE ITSELF THE RIGHT ANCHOR? (Circa / ps3838, net of fees)")
    say("=" * 118)
    say("  Every CLV in this system rests on Pinnacle's close with nothing checking it. These rows")
    say("  have a SECOND sharp close cached, so the entry and the fee are held constant and only")
    say("  the anchor changes. Circa is a genuinely separate shop; ps3838 is Pinnacle's own")
    say("  Asia-facing book, so it is a near-sibling and NOT an independent check - labelled so.")
    for fld, nm in (("circa", "Circa"), ("ps3838", "ps3838 (Pinnacle sibling)")):
        both = [r for r in ver if r.get(fld) is not None]
        if not both:
            say(f"\n  {nm}: no overlapping cached closes yet - the capture started 9 Nov and runs")
            say(f"     25 games a night, so this fills in over the coming days.")
            continue
        p = st.mean(r["pin"] for r in both)
        q = st.mean(r[fld] for r in both)
        bp = sum(1 for r in both if r["pin"] > 0)
        bq = sum(1 for r in both if r[fld] > 0)
        agree = sum(1 for r in both if (r["pin"] > 0) == (r[fld] > 0))
        say(f"\n  {nm}: {len(both)} rows with BOTH closes cached, same net entry price")
        say(f"    vs Pinnacle close  CLV {p:+6.2f}%   beat {bp}/{len(both)} = {100 * bp / len(both):.1f}%")
        say(f"    vs {nm[:22]:22s} CLV {q:+6.2f}%   beat {bq}/{len(both)} = {100 * bq / len(both):.1f}%")
        say(f"    the two anchors AGREE on the sign for {agree}/{len(both)} = {100 * agree / len(both):.1f}% of rows")
        if abs(p - q) > 0.5:
            say(f"    -> the anchors differ by {abs(p - q):.2f} pct pts. A CLV verdict that flips with the")
            say(f"       anchor is not a fact about the bet; it is a fact about which book you grade on.")
        else:
            say(f"    -> the anchors agree to within {abs(p - q):.2f} pct pts, so Pinnacle's close is")
            say(f"       corroborated on this sample and the negative CLV is not an artifact of it.")

    # ---------------------------------------------------------------- verdicts
    say("")
    say("=" * 118)
    say("VERDICTS")
    say("=" * 118)
    for nm, both in verdicts.items():
        v = ("INSUFFICIENT DATA" if both is None else ("PASS both halves" if both else "FAIL"))
        say(f"  {nm:52s} {v}")
    say("")
    say("  A FAIL here means the candidate does not hold positive Pinnacle CLV in both halves. It")
    say("  is not a statement about its units, and it does not retire the test - the registry owns")
    say("  that, and only Peter changes it.")
    say("")
    say("  Nothing above was chosen by looking at the result. No rule was fitted, no threshold")
    say("  searched, and no registered criterion changed.")
    _send()
    return 0


def _send():
    try:
        import executor as ex
        ex.send("Bets PRIORITY 6 - root-cause audit of negative CLV", "\n".join(L))
    except Exception as e:
        print(f"email failed ({type(e).__name__})")


if __name__ == "__main__":
    sys.exit(main())

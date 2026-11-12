"""Independent probability reference from Pinnacle (Nov 12, 2026). Pure: no network, no I/O.

WHY PINNACLE AND NOT THE EXECUTION VENUE. A buy-side quote from the venue we are about to trade on is not an
independent valuation of that venue's price. The reference must come from a separate book, two-sided, at a known
line, with a timestamp. The caller (executor, shadow only) normalises the feed and does the team matching; this module
validates everything else and returns either a line_value.Reference or a labelled reason there is none.

What a reference must match before it is used (each failure is its own labelled reason, never a guess):
  game      the caller matched both teams; commence time must be within START_TOL_MIN of the alert's start
  market    spreads or totals only, full game; the two outcomes must be the same market (same total, or mirrored handicaps)
  line      read from the quote itself (it may differ from the alert line; line_value shifts mass across the gap)
  period    full game only (the feed's spreads/totals markets); anything else is refused
  two-sided both prices present and plausible (each side > 0, overround within bounds)
  fresh     read time within MAX_AGE_S of now, and the quote's own last_update recorded alongside it
  settlement a whole-number reference line needs the reference book's refund rule: REFERENCE_SETTLEMENT below
"""
from datetime import datetime

import line_value as lv

CALC = "line_value_ref/v1"
MAX_AGE_S = 300          # same freshness the executor's existing Pinnacle guard uses (PIN_MAX_AGE_S)
START_TOL_MIN = 180      # feed commence time vs the alert's start time
OVERROUND = (1.005, 1.12)

# Reference-book push rules. Spreads: pinnacle.com states the stake is returned on an exact handicap.
# Totals: only third-party/affiliate wording found, so totals stay OFF until a primary Pinnacle rule is read.
REFERENCE_SETTLEMENT = {("pinnacle", "spread"): "refund"}
REFERENCE_SETTLEMENT_SOURCE = {
    ("pinnacle", "spread"): "https://www.pinnacle.com/en/future/bets-sports-offered (stake returned on the exact handicap)",
    ("pinnacle", "total"): "NOT VERIFIED: only pinnacleoddsdropper.com blog wording seen",
}


def _t(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def pinnacle_reference(inp, mtype, side, alert_start_utc, now, sport):
    """inp: {market:{outcomes:[{name,point,price}x2], last_update}, mine:<our outcome name>, read_utc, commence_utc,
    book:'pinnacle', why?}. Returns (Reference | None, record). The record is always returned and says what was used
    or why nothing was. Never raises."""
    rec = {"calc": CALC, "source": "pinnacle (the-odds-api)", "status": "none", "why": None}
    try:
        if not inp or inp.get("why") or not inp.get("market"):
            rec["why"] = (inp or {}).get("why") or "pinnacle_not_read"
            return None, rec
        mk, mine_name = inp["market"], inp.get("mine")
        oc = mk.get("outcomes") or []
        if mtype not in ("spread", "total"):
            rec["why"] = "market_not_spread_or_total"
            return None, rec
        if len(oc) != 2:
            rec["why"] = "not_two_sided"
            return None, rec
        mine = next((o for o in oc if o.get("name") == mine_name), None)
        other = next((o for o in oc if o is not mine), None)
        if mine is None or other is None or mine.get("point") is None or other.get("point") is None:
            rec["why"] = "our_side_not_identified"
            return None, rec
        pm, po = float(mine["point"]), float(other["point"])
        if mtype == "total" and pm != po:
            rec["why"] = "totals_points_differ"
            return None, rec
        if mtype == "spread" and abs(pm + po) > 1e-9:
            rec["why"] = "handicaps_not_mirrored"
            return None, rec
        am, ao = int(mine["price"]), int(other["price"])
        pa, pb = lv.am_to_prob(am), lv.am_to_prob(ao)
        if not (OVERROUND[0] <= pa + pb <= OVERROUND[1]):
            rec["why"] = f"implausible_overround:{pa + pb:.3f}"
            return None, rec
        rd, st, cm = _t(inp.get("read_utc")), _t(alert_start_utc), _t(inp.get("commence_utc"))
        if rd is None:
            rec["why"] = "no_read_time"
            return None, rec
        age = (now - rd).total_seconds()
        rec.update({"line": pm, "am_mine": am, "am_other": ao, "last_update": mk.get("last_update"),
                    "read_utc": inp.get("read_utc"), "age_s": round(age), "commence_utc": inp.get("commence_utc"),
                    "period": "full_game", "devig": "proportional"})
        if age > MAX_AGE_S or age < -5:
            rec["why"] = f"stale_read:{round(age)}s"
            return None, rec
        if st is None or cm is None:
            rec["why"] = "game_time_unverifiable"
            return None, rec
        gap = abs((cm - st).total_seconds()) / 60
        rec["start_gap_min"] = round(gap)
        if gap > START_TOL_MIN:
            rec["why"] = f"different_game_start:{round(gap)}min"
            return None, rec
        if lv.is_whole(lv.cover_threshold(mtype, side, pm)):
            rule = REFERENCE_SETTLEMENT.get((inp.get("book") or "pinnacle", mtype))
            rec["settlement"] = rule or "unverified"
            if rule != "refund":
                rec["why"] = "reference_settlement_unverified_on_whole_line"
                return None, rec
        q = lv.devig_two_sided(am, ao)
        rec.update({"status": "ok", "q": round(q, 6)})
        return lv.Reference(mtype, side, pm, q, mk.get("last_update") or inp.get("read_utc"), "pinnacle"), rec
    except Exception as ex:
        rec["why"] = f"error:{type(ex).__name__}"
        return None, rec

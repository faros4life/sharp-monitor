#!/usr/bin/env python3
"""AUDITABLE CLOSE DETAIL (CLV forensic audit, 10 Nov 2026). Pure functions over the same structures
clv_ledger.close_for reads. Read-only, no network.

close_for() returns only {p, how, age_min}. For an audit that is not enough: we need WHICH Pinnacle market and
outcomes, BOTH odds behind the no-vig probability, BOTH tick times, and the limit. This re-derives that from the
same history and ASSERTS that the probability recomputed from the two odds equals close_for's own p. A mismatch
is reported as "detail mismatch", never papered over: it would mean this file disagrees with the standard.
"""
import clv_ledger as cl


def _outcomes(mkmap, mid):
    return {v: k for k, v in mkmap.get(mid, [0, 0, 0, {}])[3].items()}


def close_detail(q, f, pm, mkmap, at, lg, c):
    """Detail dict for the close (or entry-time read) `c` that close_for produced at read-time `at`.
    Keys: pin_market_id, pin_outcome_held, pin_outcome_other, pin_dec_held, pin_dec_other,
    tick_held_utc, tick_other_utc, age_held_min, age_other_min, limit_held, limit_other, pin_line_t1,
    detail_check ('ok' | 'detail mismatch' | 'not reconstructed: ...')."""
    pz = cl.parsed(q)
    if not pz or not c:
        return {"detail_check": "not reconstructed: no parse or no close"}
    sid = cl.SPORT[lg]

    def pack(mid, oid_held, oid_other, tw, p_held_expected):
        h, o = tw[oid_held], tw[oid_other]
        p = cl.novig_p(h[0], o[0])        # P(held side) from its own and the other side's decimal
        ok = abs(p - p_held_expected) < 1e-9
        return {"pin_market_id": mid, "pin_outcome_held": oid_held, "pin_outcome_other": oid_other,
                "pin_dec_held": h[0], "pin_dec_other": o[0],
                "tick_held_utc": h[1].isoformat(), "tick_other_utc": o[1].isoformat(),
                "age_held_min": round((at - h[1]).total_seconds() / 60, 1),
                "age_other_min": round((at - o[1]).total_seconds() / 60, 1),
                "limit_held": h[2], "limit_other": o[2],
                "detail_check": "ok" if ok else "detail mismatch"}

    if pz[0] == "ml":
        side = cl.which_team(f, pz[1])
        if not side:
            return {"detail_check": "not reconstructed: team not matched"}
        if pz[3]:
            side = "2" if side == "1" else "1"
        mid = cl.ML_MARKET[sid]
        oc = _outcomes(mkmap, mid) or {"1": str(mid), "2": str(int(mid) + 1)}
        tw = cl.two_way(pm, mid, at)
        o1, o2 = oc.get("1"), oc.get("2")
        if o1 not in tw or o2 not in tw:
            return {"detail_check": "not reconstructed: market not in history"}
        held, other = (o1, o2) if side == "1" else (o2, o1)
        return pack(mid, held, other, tw, c["p"])

    typ = "spreads" if pz[0] == "spread" else "totals"
    cands = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in pm:
            continue
        tw = cl.two_way(pm, mid, at)
        nm = {v: k for k, v in outs.items()}
        a_id, b_id = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
        if a_id not in tw or b_id not in tw:
            continue
        age = (at - min(tw[a_id][1], tw[b_id][1])).total_seconds() / 60
        if age > cl.FRESH_MIN:
            continue
        cands.append((hcap, mid, a_id, b_id, tw, min(tw[a_id][2], tw[b_id][2])))
    if not cands:
        return {"detail_check": "not reconstructed: no market in history"}
    modelled = not cl_is_own(c)
    if typ == "totals":
        want, over = pz[2], pz[1] == "OVER"
        pick = next((x for x in cands if abs(x[0] - want) < 1e-9), None) if not modelled else \
            max(cands, key=lambda x: (x[5], -abs(cl.novig_p(x[4][x[2]][0], x[4][x[3]][0]) - .5)))
        if not pick:
            return {"detail_check": "not reconstructed: line not found"}
        hcap, mid, a_id, b_id, tw, _ = pick
        held, other = (a_id, b_id) if over else (b_id, a_id)
        d = pack(mid, held, other, tw, c["p"] if not modelled else cl.novig_p(tw[held][0], tw[other][0]))
    else:
        side = cl.which_team(f, pz[1])
        if not side:
            return {"detail_check": "not reconstructed: team not matched"}
        want = pz[2]
        if pz[3]:
            side, want = ("2" if side == "1" else "1"), -want
        t1_line = want if side == "1" else -want
        pick = next((x for x in cands if abs(x[0] - t1_line) < 1e-9), None) if not modelled else \
            max(cands, key=lambda x: (x[5], -abs(cl.novig_p(x[4][x[2]][0], x[4][x[3]][0]) - .5)))
        if not pick:
            return {"detail_check": "not reconstructed: line not found"}
        hcap, mid, a_id, b_id, tw, _ = pick
        held, other = (a_id, b_id) if side == "1" else (b_id, a_id)
        d = pack(mid, held, other, tw, c["p"] if not modelled else cl.novig_p(tw[held][0], tw[other][0]))
    d["pin_line_t1"] = hcap
    if modelled:
        d["detail_check"] = "modelled: market shown is Pinnacle's MAIN line, not the line bet"
    return d


def cl_is_own(c):
    import clv_std as cs
    return cs.close_verified(c.get("how"))

"""REVIEW ONLY: pure unit-cap calculation, not wired to live executor."""
import math

class ExposureUnknown(ValueError):
    pass

def _num(v, label):
    if isinstance(v, bool):
        raise ExposureUnknown(label)
    try:
        x=float(v)
    except (TypeError, ValueError):
        raise ExposureUnknown(label) from None
    if not math.isfinite(x) or x < 0:
        raise ExposureUnknown(label)
    return x

def fraction(stake, american, unit):
    """Current rule: minus odds use GROSS potential win, plus odds use stake at risk."""
    s=_num(stake, "stake")
    a=float(american)
    u=_num(unit, "unit")
    if not math.isfinite(a) or a == 0 or (-100 < a < 100) or not u:
        raise ExposureUnknown("price/unit")
    return (s*100/abs(a) if a < 0 else s)/u

def remaining(legs, unit, key):
    """Conservatively count each identified order's worst recorded exposure.

    Open/unknown/partial orders reserve full asked stake. Terminal states release
    unfilled portions ONLY on explicit verified terminal status and fill amount.
    This pure function DOES NOT provide atomic locking or authorize a new order.
    """
    if not key:
        raise ExposureUnknown("missing canonical key")
    by_order={}
    for leg in legs:
        if leg.get("key") != key:
            continue
        status=str(leg.get("status") or "").lower()
        if status in ("refused", "void", "dry"):
            continue
        if status not in ("open", "placed", "partially_filled", "filled", "settled", "canceled", "cancelled", "expired"):
            raise ExposureUnknown("unknown order state")
        order_id=leg.get("order_id") or leg.get("client_id")
        if not order_id:
            raise ExposureUnknown("missing order identity")
        ask=_num(leg.get("asked_stake"), "asked")
        raw=leg.get("filled_stake")
        filled=_num(raw, "filled") if raw is not None else None
        if filled is not None and filled > ask+0.011:
            raise ExposureUnknown("fill above ask")
        terminal=status in ("filled", "settled", "canceled", "cancelled", "expired")
        committed=filled if terminal and leg.get("terminal_verified") is True and filled is not None else ask
        used=fraction(committed, leg.get("american"), unit)
        oid=str(order_id)
        by_order[oid]=max(used, by_order.get(oid,0.0))
    return max(0.0,1.0-sum(by_order.values()))

def maximum_stake(available_units, american, unit):
    """Round DOWN to cents. Only safe AFTER an atomic per-play reservation."""
    r=_num(available_units,"available")
    if r > 1+1e-9:
        raise ExposureUnknown("remaining >1")
    a=float(american)
    u=_num(unit,"unit")
    if not math.isfinite(a) or a == 0 or (-100 < a < 100):
        raise ExposureUnknown("invalid odds")
    return math.floor((r*u*(abs(a)/100 if a < 0 else 1)+1e-10)*100)/100

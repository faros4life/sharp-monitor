"""Synthetic tests for clv_ledger.registry_side. No network, no secrets, no real data."""
import os, sys
os.environ.setdefault("TRACKER_PASSPHRASE", "synthetic-test-only")
import clv_ledger as cl
fails = []
def check(l, c, x=""):
    print(("  ok   " if c else "  FAIL ") + l + (f"  {x}" if x else ""))
    if not c: fails.append(l)
RID = "pm|Stanford vs Virginia Tech [cfb-stan-vt-2026-11-14]|-15.50|settled"
SNAP = {"league": "NCAAF", "game": "Stanford vs Virginia Tech", "bet": "-15.50"}
LINKS = {"o1": "cfb-stan-vt-2026-11-14"}
ORD = [{"key": "r1|NCAAF|stanford+virginia_tech|side|stanford", "fill_line": -15.5, "decided_utc": "2026-11-14T15:00:00Z",
        "live_order": {"order_id": "o1", "status": "placed"}}]
R = cl.registry_side
v, why = R(RID, SNAP, LINKS, ORD)
check("exact chain -> a full spread bet with the claim's side", v == "stanford -15.5", (v, why))
check("parsed as a SPREAD, never a moneyline", cl.parsed({"bet": v}) == ("spread", "stanford", -15.5, None), cl.parsed({"bet": v}))
check("two venue orders on the market -> refused", R(RID, SNAP, dict(LINKS, o2="cfb-stan-vt-2026-11-14"), ORD)[0] is None)
check("no venue-confirmed order -> refused", R(RID, SNAP, {}, ORD)[0] is None)
check("two registry orders with the id -> refused",
      R(RID, SNAP, LINKS, ORD + [dict(ORD[0], decided_utc="2026-11-14T16:00:00Z")])[0] is None)
check("league mismatch -> refused", R(RID, dict(SNAP, league="NCAAB"), LINKS, ORD)[0] is None)
check("a totals claim -> refused", R(RID, SNAP, LINKS, [dict(ORD[0], key="r1|NCAAF|stanford+virginia_tech|total|OVER")])[0] is None)
check("teams that do not match the row -> refused", R(RID, dict(SNAP, game="Duke vs Wake Forest"), LINKS, ORD)[0] is None)
check("order line differs from the row line -> refused", R(RID, SNAP, LINKS, [dict(ORD[0], fill_line=-14.5)])[0] is None)
check("opposite sign is a different bet -> refused", R(RID, SNAP, LINKS, [dict(ORD[0], fill_line=15.5)])[0] is None)
check("a short contract -> refused", R(RID, dict(SNAP, flip=True), LINKS, ORD)[0] is None)
check("bet text that is not a bare line -> refused", R(RID, dict(SNAP, bet="Stanford -15.5"), LINKS, ORD)[0] is None)
check("non-Polymarket rows are never touched", R("px|123", SNAP, LINKS, ORD)[0] is None)
check("alert_line used when no fill_line", R(RID, SNAP, LINKS, [dict(ORD[0], fill_line=None, alert_line=-15.5)])[0] == "stanford -15.5")
if fails:
    print("FAILED", fails); sys.exit(1)
print("test_registry_side: all passed")

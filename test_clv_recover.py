#!/usr/bin/env python3
"""clv_recover: the budget ceiling, the dedup rule and the tier definitions (Nov 14).

Peter set a hard ceiling of 39 billable credits. A ceiling that is only an intention is not a
ceiling, so the enforcement is tested here rather than trusted: the stage must stop ON the cap,
not one call past it, and a dry run must bill nothing by construction.
"""
import clv_recover as cr
import tracker_build as tb

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


print("1. dedup: one unique game AND market is one unit")
a = {"league": "NBA", "game": "Toronto Raptors @ Philadelphia 76ers", "market": "total", "line": 223.5}
b = {"league": "NBA", "game": "Philadelphia 76ers vs Toronto Raptors", "market": "total", "line": 223.5}
c = {"league": "NBA", "game": "Toronto Raptors @ Philadelphia 76ers", "market": "total", "line": 224.5}
d = {"league": "NBA", "game": "Toronto Raptors @ Philadelphia 76ers", "market": "moneyline", "line": None}
e = {"league": "NHL", "game": "Toronto Raptors @ Philadelphia 76ers", "market": "total", "line": 223.5}
check("the same game written either way is ONE unit", cr.unit_key(a) == cr.unit_key(b),
      f"{cr.unit_key(a)} vs {cr.unit_key(b)}")
check("a different LINE is a different unit", cr.unit_key(a) != cr.unit_key(c))
check("a different MARKET is a different unit", cr.unit_key(a) != cr.unit_key(d))
check("a different LEAGUE is a different unit", cr.unit_key(a) != cr.unit_key(e))

print("2. tiers come from the REGISTERED definitions and are not widened")
t, why = cr.tier_of({"league": "NBA", "market": "total"}, None)
check("NBA totals -> tier 2 (LIQ-BOT / LIQ-SMALL)", t == 2, f"{t} {why}")
for lg, mkt in (("NHL", "total"), ("NBA", "moneyline"), ("NCAAF", "spread"), ("NFL", "total")):
    t, why = cr.tier_of({"league": lg, "market": mkt}, None)
    check(f"{lg} {mkt} is NOT claimed as a registered candidate", t == 3, f"tier {t}")
t, _ = cr.tier_of({"league": "NBA", "market": "total", "order_id": "x"}, None)
check("a live-lane order id -> tier 1", t == 1)

print("3. the budget ceiling is enforced before the call, not after")
calls = []


def fake_refresh(st, now, lg, lo, hi):
    calls.append((lg, str(lo)))
    cr.RECOVERED[f"f{len(calls)}"] = {"lg": lg, "start": "2026-11-01T00:00:00Z",
                                      "p1": "A", "p2": "B"}
    return True


def fake_reclassify(u, *a, **k):
    u["cls"] = "MISSING_HISTORY"      # fixture found, history still needed: NOT resolved
    u["needs_fixture"] = False
    return u["cls"]


orig = (cr.refresh_into_recovered, cr.reclassify, cr.APPLY, cr.BUDGET, cr.MIN_FIX_RATE,
        cr.cl.tournament, cr.cl.can_bill)
cr.refresh_into_recovered, cr.reclassify = fake_refresh, fake_reclassify
cr.APPLY, cr.BUDGET, cr.MIN_FIX_RATE = True, 3, 0.0     # floor off: isolate the ceiling
cr.cl.tournament = lambda st, now, lg: 1
cr.cl.can_bill = lambda st, now, n=1: True
cr.SPENT["billable"] = 0
units = [{"key": f"k{i}", "row": {}, "tier": 2, "twhy": "", "lg": "NBA",
          "day": f"2026-11-{i + 1:02d}", "cls": "FIXTURE_OR_IDENTITY",
          "detail": "no unique fixture", "needs_fixture": True, "n_obs": 1,
          "clv": None, "fid": None, "stage": ""} for i in range(10)]
r = cr.stage_fixtures(units, {}, cr.datetime.now(cr.timezone.utc), {}, {}, {}, {}, 2)
check("stops ON the ceiling, never past it", cr.SPENT["billable"] == 3,
      f"spent {cr.SPENT['billable']} with ceiling 3")
check("the calls made match the credits counted", len(calls) == 3, len(calls))
check("the abort reason says it was the ceiling", "ceiling" in str(r.get("aborted")), r.get("aborted"))
check("10 windows were available, only 3 bought", r["windows_available"] == 10, r)

print("4. a tier that resolves nothing stops instead of spending the rest")
calls.clear()
cr.RECOVERED.clear()
cr.BUDGET, cr.MIN_FIX_RATE = 39, 0.15
cr.SPENT["billable"] = 0
units = [{"key": f"k{i}", "row": {}, "tier": 2, "twhy": "", "lg": "NBA",
          "day": f"2026-11-{i + 1:02d}", "cls": "FIXTURE_OR_IDENTITY",
          "detail": "no unique fixture", "needs_fixture": True, "n_obs": 1,
          "clv": None, "fid": None, "stage": ""} for i in range(20)]
r = cr.stage_fixtures(units, {}, cr.datetime.now(cr.timezone.utc), {}, {}, {}, {}, 2)
check("stopped well under the 39 ceiling", cr.SPENT["billable"] <= 6, cr.SPENT["billable"])
check("and said why", "poor recovery" in str(r.get("aborted")), r.get("aborted"))

print("5. a dry run bills nothing by construction")
calls.clear()
cr.APPLY = False
cr.SPENT["billable"] = 0
units = [{"key": "k", "row": {}, "tier": 2, "twhy": "", "lg": "NBA", "day": "2026-11-01",
          "cls": "FIXTURE_OR_IDENTITY", "detail": "no unique fixture", "needs_fixture": True,
          "n_obs": 1, "clv": None, "fid": None, "stage": ""}]
r = cr.stage_fixtures(units, {}, cr.datetime.now(cr.timezone.utc), {}, {}, {}, {}, 2)
check("no credit spent", cr.SPENT["billable"] == 0)
check("no call made", not calls)
check("the unit records what WOULD have been called", "would call" in units[0]["stage"],
      units[0]["stage"])

(cr.refresh_into_recovered, cr.reclassify, cr.APPLY, cr.BUDGET, cr.MIN_FIX_RATE,
 cr.cl.tournament, cr.cl.can_bill) = orig
cr.SPENT["billable"] = 0
cr.RECOVERED.clear()

print("6. only /fixtures bills - history and account are free paths")
import credit_gate as cg
check("/historical-odds is free", cg.is_free("/historical-odds"))
check("/account is free", cg.is_free("/account"))
check("/fixtures is NOT free", not cg.is_free("/fixtures"))

print("7. the job never names the production state as a write target")
src = open("clv_recover.py").read()
for bad in ('open(cl.STATE, "w")', "open(cl.STATE,'w')", "refresh_fixtures("):
    check(f"does not {bad}", bad not in src)
check("writes only its own fixture cache and the audit file",
      'open(FXOUT, "w")' in src and 'open(OUT, "w")' in src)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_clv_recover: all passed")

"""95% CI on units/play, per trigger, in the nightly export. Peter's ruling, Nov 25 2026.

"Maybe confidence interval is better yardstick" -> CIs next to every trigger's all-time and
last-20 units/play. Display and judging frame only: no grading, no kill/promote bar, no execution
change.

The whole point of the ruling is that a mean with no spread is an overcall, so these checks are
mostly about the interval being HONEST - right denominator, right sample, and no interval invented
where the data cannot support one."""
import bot_live_export as B

FAILED = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    if not cond:
        FAILED.append(name)


def plays(units, start="2026-11-20T00:00:00Z"):
    return [{"units": u, "start": f"2026-11-{10 + i:02d}T00:00:00Z", "seen": None}
            for i, u in enumerate(units)]


# --- the interval is real arithmetic, not decoration -------------------------------------------
c = B.units_ci(plays([1.0, -1.0, 1.0, -1.0]))
ok("mean of a symmetric set is 0", abs(c["mean"]) < 1e-9, c["mean"])
ok("sample SD uses n-1", abs(c["sd"] - 1.1547) < 1e-3, c["sd"])
ok("a set centred on 0 is unproven", c["verdict"] == "unproven", c["verdict"])
ok("interval straddles the mean", c["lo"] < c["mean"] < c["hi"])

# a strongly positive, tight set clears zero
c = B.units_ci(plays([0.9, 1.0, 1.1, 0.95, 1.05] * 4))
ok("a tight positive set is proven", c["verdict"] == "proven" and c["lo"] > 0, c)

# a strongly negative, tight set is kill territory
c = B.units_ci(plays([-0.9, -1.0, -1.1, -0.95, -1.05] * 4))
ok("a tight negative set is kill territory", c["verdict"] == "kill territory" and c["hi"] < 0, c)

# --- a positive mean that cannot be told from zero must NOT read as proven ---------------------
# This is the case the ruling exists for: Lane 1 all-time was +0.205 with the CI crossing 0.
wide = plays([1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, 1.0])     # mean +0.25, big spread
c = B.units_ci(wide)
ok("a positive mean with a wide interval stays unproven", c["mean"] > 0 and c["verdict"] == "unproven", c)

# --- no spread means no interval, not a fabricated one -----------------------------------------
for n, s in ((0, []), (1, [0.9])):
    c = B.units_ci(plays(s))
    ok(f"n={n}: no interval invented", c["lo"] is None and c["hi"] is None, c)
    ok(f"n={n}: verdict is not proven", "proven" not in c["verdict"] or "unproven" in c["verdict"], c)
ok("n=0 reports no mean", B.units_ci([])["mean"] is None)

# --- only RESULTED plays count; open plays carry units=None ------------------------------------
mixed = plays([1.0, -1.0, 1.0, -1.0]) + [{"units": None, "start": "2026-11-30T00:00:00Z", "seen": None}]
ok("open plays are excluded from n", B.units_ci(mixed)["n"] == 4, B.units_ci(mixed)["n"])

# --- last-20 means the twenty MOST RECENT, not the first twenty listed -------------------------
old_losers = plays([-1.0] * 30)                                    # Nov 10 onward
recent = [{"units": 1.0, "start": f"2026-12-{i:02d}T00:00:00Z", "seen": None} for i in range(1, 21)]
c20 = B.units_ci(old_losers + recent, last=20)
ok("last-20 takes the most recent by start time", c20["n"] == 20 and c20["mean"] == 1.0, c20)
ok("all-time still sees everything", B.units_ci(old_losers + recent)["n"] == 50)
ok("last-20 is capped at 20 even with more", B.units_ci(plays([0.5] * 40), last=20)["n"] == 20)
ok("last-20 of a short set is just the set", B.units_ci(plays([0.5, -0.5]), last=20)["n"] == 2)

# a play with no start falls back to seen rather than crashing the sort
ok("a play with no start does not break the ordering",
   B.units_ci([{"units": 1.0, "start": None, "seen": "2026-11-01T00:00:00Z"},
               {"units": -1.0, "start": None, "seen": None}])["n"] == 2)

# --- the frame and the caveat travel with the numbers ------------------------------------------
ok("frame states all three verdicts",
   all(w in B.CI_FRAME for w in ("proven", "kill territory", "unproven")))
ok("frame names the basis, so it is not compared against a to-win denominator",
   "profit/stake" in B.CI_FRAME and "fill price" in B.CI_FRAME)
ok("caveat records that a nightly rolling window is not a 95% test",
   "not a 95% test" in B.CI_CAVEAT.replace("NOT", "not"))
ok("caveat records the promote/kill asymmetry", "asymmetric" in B.CI_CAVEAT)

# --- the export carries them, and the log stays counts-only ------------------------------------
src = open("bot_live_export.py", encoding="utf-8").read()
ok("export doc carries the per-trigger CIs", '"trigger_ci": trig_ci' in src)
ok("export doc carries the frame and the caveat", '"ci_frame": CI_FRAME' in src and '"ci_caveat": CI_CAVEAT' in src)
ok("both windows are computed for every trigger",
   '"all_time": units_ci(v)' in src and '"last_20": units_ci(v, last=20)' in src)
ok("the Actions log prints sample sizes only, no units",
   "trigger CI sample sizes (counts only)" in src and 'c["all_time"]["n"]' in src)
ok("no dollar figure is printed anywhere in this change", "$" not in B.CI_FRAME + B.CI_CAVEAT)

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)

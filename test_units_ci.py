#!/usr/bin/env python3
"""95% units/play intervals, for all-time / last-50 / last-20.

Peter, 27 Nov: "Add 95% units/play confidence intervals for all-time, last-50 and last-20 performance.
CLV confidence intervals alone are insufficient."

His 25 Nov yardstick judges a lane on units/play with its 95% interval - fully above 0 proven, fully below
kill territory, crossing 0 unproven - and says the ALL-TIME interval governs qualification while last-20 is
supporting evidence only. Before this the table printed an interval for CLV and none for units/play, and its
"ALL" row was silently a 50-play window, so the interval his rule names did not exist anywhere.
"""
import statistics
import live_ledger as ll


def play(t, res, am_net=-110.0, clv=None):
    p = {"t": t, "res": res, "am_net": am_net, "lane": "TESTLANE"}
    if clv is not None:
        p["clv"] = clv
    return p


def check(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    return bool(cond)


def main():
    ok = True

    # ---- 1. the interval is the mean of per-play units +/- 1.96 se, not something else
    plays = [play(f"2026-11-{d:02d}", r) for d, r in zip(range(1, 9), "WLWLWLWW")]
    x = ll.lane_stats(plays)
    u = [ll.units(p["am_net"], p["res"]) for p in plays]
    exp_m = statistics.mean(u)
    exp_se = statistics.stdev(u) / len(u) ** 0.5
    ok &= check("u/play equals the mean of per-play units", abs(x["upp"] - exp_m) < 1e-9, x["upp"])
    ok &= check("the interval is mean +/- 1.96 se",
                abs(x["uci"][0] - (exp_m - 1.96 * exp_se)) < 1e-9
                and abs(x["uci"][1] - (exp_m + 1.96 * exp_se)) < 1e-9, x["uci"])
    ok &= check("u/play is ROI/100, so the two columns cannot disagree",
                abs(x["upp"] * 100 - x["roi"]) < 1e-9, (x["upp"], x["roi"]))

    # ---- 2. a single play gets NO interval. A zero-width interval would read as certainty from one bet.
    x1 = ll.lane_stats([play("2026-11-01", "W")])
    ok &= check("n=1 has a u/play figure", x1["upp"] is not None)
    ok &= check("n=1 claims no interval", x1["uci"] is None, x1["uci"])

    # ---- 3. the sign of the interval is what his yardstick reads, so pin all three verdicts
    allw = ll.lane_stats([play(f"2026-11-{d:02d}", "W") for d in range(1, 13)])
    ok &= check("an all-winning lane's interval sits fully above 0 (proven)", allw["uci"][0] > 0, allw["uci"])
    alll = ll.lane_stats([play(f"2026-11-{d:02d}", "L") for d in range(1, 13)])
    ok &= check("an all-losing lane's interval sits fully below 0 (kill)", alll["uci"][1] < 0, alll["uci"])
    mixed = ll.lane_stats([play(f"2026-11-{d:02d}", r) for d, r in zip(range(1, 13), "WLWLWLWLWLWL")])
    ok &= check("a coin-flip lane's interval crosses 0 (unproven)",
                mixed["uci"][0] < 0 < mixed["uci"][1], mixed["uci"])

    # ---- 4. the windows. 60 plays so ALL, L50 and L20 are genuinely different row sets.
    many = [play(f"2026-{9 + d // 30:02d}-{d % 30 + 1:02d}", "W" if d % 3 else "L", clv=0.5)
            for d in range(60)]
    lines = ll.lane_summary({"plays": many})
    tags = [l.split()[1] for l in lines if l.strip().startswith("TESTLANE")]
    for want in ("ALL", "L50", "L20", "H1", "H2"):
        ok &= check(f"the table carries a {want} row", want in tags, tags)
    ok &= check("every window row carries a u/play interval",
                all("u/play" in l and "95% [" in l for l in lines if l.strip().startswith("TESTLANE")))

    def n_of(tag):
        return int([l for l in lines if l.strip().startswith("TESTLANE") and l.split()[1] == tag][0]
                   .split("n")[1].split()[0])

    ok &= check("ALL is all-time, not a 50-play window", n_of("ALL") == 60, n_of("ALL"))
    ok &= check("L50 is the last 50", n_of("L50") == 50, n_of("L50"))
    ok &= check("L20 is the last 20", n_of("L20") == 20, n_of("L20"))
    ok &= check("H1 and H2 halve ALL, not the window", n_of("H1") + n_of("H2") == 60,
                (n_of("H1"), n_of("H2")))

    # ---- 5. with fewer plays than a window, that window is not repeated as a duplicate ALL row
    few = ll.lane_summary({"plays": [play(f"2026-11-{d:02d}", "W", clv=0.4) for d in range(1, 9)]})
    ftags = [l.split()[1] for l in few if l.strip().startswith("TESTLANE")]
    ok &= check("8 plays: no duplicate L50 row", "L50" not in ftags, ftags)
    ok &= check("8 plays: no duplicate L20 row", "L20" not in ftags, ftags)
    ok &= check("8 plays: ALL is still there", "ALL" in ftags, ftags)

    # ---- 6. the CLV interval is still reported, and is a DIFFERENT number from the units one
    ok &= check("CLV keeps its own interval", any("CLV" in l and "95% [" in l.split("CLV")[1]
                                                  for l in lines if l.strip().startswith("TESTLANE")))

    print("\nALL PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""toa_peak_analyze on a synthetic 15 s series: move counting, after-fee edge, opportunity windows and sampler loss."""
import toa_peak_analyze as pa

fails = 0
def ok(c, m):
    global fails
    print(("  ok   " if c else "  FAIL ") + m); fails += 0 if c else 1

T = [1000 + 15 * i for i in range(40)]
S = {("basketball_nba", "e1", "pinnacle", "totals", "Over"): [(i, T[i], (220.5, -110 if i < 10 else -120)) for i in range(40)],
     ("basketball_nba", "e1", "pinnacle", "totals", "Under"): [(i, T[i], (220.5, -110 if i < 10 else +100)) for i in range(40)],
     # Novig Under +125 for polls 12..13 only (30 s), else -115
     ("basketball_nba", "e1", "novig", "totals", "Under"): [(i, T[i], (220.5, 125 if 12 <= i <= 13 else -115)) for i in range(40)]}
start = {"e1": T[0] + 7200}
tot, cau, dl = pa.pin_moves(S, start, {r: s // 15 for r, s in pa.RATES.items()})
ok(tot[("price-only", ">60 min", "15s")] == 2, "two Pinnacle price-only moves (one per side) at 15 s")
ok(cau[("price-only", ">60 min", "5min")] == 2 and dl[("price-only", ">60 min", "5min")][0] > 0, "5 min sees them, later")
P = pa.by_poll(S)
e = pa.edge(P, "NBA", "e1", "totals", "Under", "novig", 12)
ok(e is not None and e > 0.01, "Novig +125 vs a Pinnacle fair near 48% is actionable after fees")
ok(pa.edge(P, "NBA", "e1", "totals", "Under", "novig", 20) < 0, "Novig -115 is not")
O = pa.opportunities(S, P, start, {"e1": "basketball_nba"}, T, 15)
A = [w for w in O if w["lvl"] == "actionable"]
ok(len(A) == 1 and A[0]["dur"] == 30, "one actionable window lasting 30 s")
ok(A[0]["seen"]["15s"] == 0 and A[0]["seen"]["5min"] is None, "15 s catches it, 5 min loses it")
print("FAILED" if fails else "all passed"); raise SystemExit(1 if fails else 0)

"""Nov 12: the alternate-line benchmark matches game/side/time, classifies moves, and never estimates a missing cell."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pin_alt_measure as pa  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


START = datetime(2026, 11, 8, 18, 0, tzinfo=timezone.utc)
iso = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ticks(dec, at):
    return [{"createdAt": iso(at), "price": dec, "limit": 1000}]


def market(mid, hcap, typ, p1, p2, at):
    outs = {f"{mid}a": "1", f"{mid}b": "2"} if typ == "spreads" else {f"{mid}a": "Over", f"{mid}b": "Under"}
    mk = {"outcomes": {f"{mid}a": {"players": {"0": ticks(p1, at)}}, f"{mid}b": {"players": {"0": ticks(p2, at)}}}}
    return mid, [14, typ, hcap, outs], mk


# spreads: team1 -3.5 (1.909 / 1.952), -3.0 (2.05 / 1.80), -2.5 (2.20 / 1.70); totals 44.5 / 45.5
at = START - timedelta(minutes=10)
rows = [market("m35", -3.5, "spreads", 1.909, 1.952, at), market("m30", -3.0, "spreads", 1.80, 2.05, at),
        market("m25", -2.5, "spreads", 1.70, 2.20, at), market("t445", 44.5, "totals", 1.80, 2.05, at),
        market("t455", 45.5, "totals", 1.909, 1.909, at),
        market("stale", -4.5, "spreads", 2.5, 1.5, START - timedelta(hours=5))]   # stale at T=start
mkmap = {mid: v for mid, v, _ in rows}
pm = {mid: mk for mid, _, mk in rows}
pa.SAMPLE_H = (0,)
obs = pa.observe("F1", "NFL", pm, mkmap, START)
hh = [o for o in obs if o["cls"] == "half_half" and o["typ"] == "spreads" and o["side"] == "team1"]
ck("team1 -3.5 -> -2.5 is one half_half observation across 3", len(hh) == 1 and hh[0]["k"] == 3 and hh[0]["move"] == 1.0, str(hh))
ck("its diff is cents(better) - cents(worse): -143 vs -110 -> 32.9 cents paid (negative diff)", abs(hh[0]["diff"] + 32.9) < 0.11 and hh[0]["am_better"] == -143, str(hh[0]))
hw = [o for o in obs if o["cls"] == "half_whole" and o["side"] == "team1"]
ck("team1 gets two half_whole moves (-3.5->-3 and -3->-2.5), both tagged integer 3", len(hw) == 2 and all(o["k"] == 3 for o in hw), str(hw))
t2 = [o for o in obs if o["side"] == "team2" and o["cls"] == "half_half"]
ck("team2's better line is +3.5 (from +2.5): direction follows the SIDE, not the number", len(t2) == 1 and t2[0]["line_better"] == -3.5 and t2[0]["line_worse"] == -2.5, str(t2))
ck("stale line (-4.5, tick 5h old) is excluded", not any(o["line_worse"] == -4.5 or o["line_better"] == -4.5 for o in obs))
ov = [o for o in obs if o["typ"] == "totals" and o["side"] == "over"]
ck("over: 44.5 is the better line vs 45.5, class half_half across 45", len(ov) == 1 and ov[0]["line_better"] == 44.5 and ov[0]["k"] == 45, str(ov))
un = [o for o in obs if o["typ"] == "totals" and o["side"] == "under"]
ck("under: 45.5 is the better line vs 44.5", len(un) == 1 and un[0]["line_better"] == 45.5, str(un))
# sync: ticks 45 min apart are not contemporaneous
rows2 = [market("a", -3.5, "spreads", 1.909, 1.952, at), market("b", -2.5, "spreads", 2.2, 1.7, at - timedelta(minutes=45))]
o2 = pa.observe("F2", "NFL", {m: k for m, _, k in rows2}, {m: v for m, v, _ in rows2}, START)
ck("ticks more than SYNC_MIN apart give no pair", not o2)
s = pa.summarize(obs)
cell = s[("NFL", "spreads", "half_half", 1.0, 3)]
ck("summary counts observations and fixtures separately", cell["n_obs"] == 2 and cell["n_fixtures"] == 1, str(cell))
ck("summary reports mean, median, sd, se, p10, p90", all(k in cell for k in ("mean", "median", "sd", "se", "p10", "p90")))
txt = pa.render(s, {"NFL"}, 1, 1)
ck("MLB is reported as not in cache, never estimated", "MLB: NOT IN CACHE" in txt and "MLB spreads (league not in cache)" in txt)
ck("se is labelled as one standard error", "ONE standard error" in txt)
ck("empty leagues are listed as missing cells", "NBA spreads (league not in cache)" in txt)
src = open(pa.__file__).read()
ck("no executor import, no email, no network write", "import executor" not in src and "smtplib" not in src and "urlopen" not in src)
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)

#!/usr/bin/env python3
"""NOVIG-ONLY vs PROPHETX-QUALIFIED executable-basis CLV, Oct 28 - Nov 10 2026 (research, read-only, 0 credits).
Reads alerts.json + cached Pinnacle history (hcache) only. Same method as rest_depth_report.audit():
exact alert line, entry = alert price after fees, verified same-line Pinnacle close (clv_std), UNKNOWN when any leg is missing.
Never reads a paid endpoint: markets come from clv/markets.json on disk."""
import json, os, sys, collections, math
from datetime import datetime, timezone, timedelta
import clv_ledger as cl, clv_std as cs, hist_cache as hc, nba_names as nn, tracker_build as tb, agree_rules as ar

W0, W1 = "2026-10-28", "2026-11-10"
# Novig-only plays whose exact-line fill at the alert price had depth >= order size (executor ledger emails, Nov 10 audit)
EXEC = {"2026-10-28T12:30:17Z", "2026-10-28T12:50:13Z", "2026-10-28T20:20:14Z",
        "2026-11-04T14:25:13Z", "2026-11-07T21:40:15Z", "2026-11-09T13:40:17Z"}

def etday(s):
    d = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (d - timedelta(hours=4 if d < datetime(2026, 11, 1, 6, tzinfo=timezone.utc) else 5)).date().isoformat()

ent = [x for x in json.load(open("alerts.json"))["alerts"] if W0 <= etday(x["alert_utc"]) <= W1]
for x in ent:
    x["_ok"], x["_why"] = ar.phase1(x, ar.decide(x)["verdict"] == "AGREE")
nov = [x for x in ent if x.get("book_key") == "novig" and all(w.startswith("priced on") for w in x["_why"])]
px = [x for x in ent if x.get("book_key") == "prophetx" and x["_ok"]]
nex = [x for x in nov if x["alert_utc"] in EXEC]

st = {"fixtures": dict(tb.dec(json.load(open(cl.STATE))).get("fixtures") or {})}
mkmap = json.load(open(cl.MKFILE))["m"]
print(f"fixtures {len(st['fixtures'])}  novig-only {len(nov)}  executable {len(nex)}  px-qualified {len(px)}")

def score(x):
    if x.get("kind") != "tot" or x.get("point") is None or x.get("price_after_fee") is None:
        return None, "not an exact-line total"
    lg = x["sport"].upper(); side = "Under" if "under" in x["bet"].lower() else "Over"
    bet = f"{side} {float(x['point']):g}"
    try:
        fid = cl.find_fixture(st, {"bet": bet, "league": lg, "game": x["game"], "teams": nn.teams_of({"league": lg, "teams": None}), "game_start": x["start_utc"]})
    except Exception:
        fid = None
    if not fid: return None, "no fixture matched"
    if not os.path.exists(hc._path(fid, "pinnacle")): return None, "no cached Pinnacle history"
    f = st["fixtures"][fid]; start = cl.tp(f.get("start"))
    try:
        h = hc.get_hist(fid, ["pinnacle"], start)
        c, why = cl.close_for({"bet": bet, "league": lg, "market": "total"}, f, cl.book_markets(h, "pinnacle"), mkmap, start, lg)
    except Exception as e:
        return None, f"close read error {type(e).__name__}"
    if not c or not cs.close_verified(c.get("how")): return None, f"close not verified ({why or (c or {}).get('how')})"
    am = x["price_after_fee"]; dec = 1 + (am / 100.0 if am > 0 else 100.0 / abs(am))
    try:
        return cs.net_clv(c["p"], dec, cs.canon(x["book"].lower().replace(" ", "_")), maker=False, league=lg), None
    except Exception as e:
        return None, f"net_clv error {type(e).__name__}"

def wil(w, n, z=1.96):
    if not n: return "n/a"
    p = w / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; hh = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"[{100*(c-hh):.0f}%,{100*(c+hh):.0f}%]"

def block(name, rs):
    rs = sorted(rs, key=lambda x: x["alert_utc"]); res = []; unk = collections.Counter()
    for x in rs:
        v, why = score(x); res.append(v)
        if v is None: unk[why] += 1
    ok = [v for v in res if v is not None]; beat = sum(v > 0 for v in ok)
    print(f"\n{name}: n={len(rs)} scored={len(ok)} UNKNOWN={len(rs)-len(ok)} {dict(unk)}")
    if ok:
        m = sum(ok) / len(ok); sd = (sum((v - m) ** 2 for v in ok) / (len(ok) - 1)) ** .5 if len(ok) > 1 else float("nan")
        print(f"  mean net CLV {m:+.2f}%  se {sd/len(ok)**.5:.2f}  beat close {beat}/{len(ok)} {wil(beat, len(ok))}")
        h = len(res) // 2
        for lab, part in (("H1", res[:h]), ("H2", res[h:])):
            p = [v for v in part if v is not None]
            print(f"  {lab}: scored {len(p)}/{len(part)}  mean {(sum(p)/len(p)) if p else float('nan'):+.2f}%")
    return res

block("NOVIG-ONLY executable (depth-verified)", nex)
block("NOVIG-ONLY all 14 (alert price)", nov)
block("PROPHETX-qualified (alert price)", px)

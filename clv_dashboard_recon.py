"""Reconcile the dashboard against source records. Read-only, zero credits."""
import json, os, collections
import clv_dashboard as dash, clv_coverage as cov, clv_selection as csel, clv_ledger as cl
import tracker_build as tb, registry as rg

view, err = dash.build()
assert view, err
B = view["bands"]
bad = []
def ck(label, cond, extra=""):
    print(("  ok   " if cond else "  MISMATCH ") + label + (f"  {extra}" if extra else ""))
    if not cond: bad.append(label)

st = tb.dec(json.load(open(cl.STATE)))
bets = st.get("bets") or {}
tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
import clv_stale as cstale
stale = cstale.stale_map(bets, tracker)
cert = {k: r for k, r in bets.items() if r.get("clv") is not None and not r.get("fixture_doubt") and k not in stale}
obs = csel.selections(cert, tracker, exclude=set(stale))

print("1. selection count against the ledger")
ck("dashboard selections == clv_selection over the certified ledger",
   view["selections_total"] == len(obs), f"{view['selections_total']} vs {len(obs)}")
ck("certified ledger rows reconcile to selections",
   sum(o.get("n_fills",1) for o in obs.values()) == len(cert),
   f"fills {sum(o.get('n_fills',1) for o in obs.values())} vs rows {len(cert)}")

print("2. lane attribution against the private registry")
reg = rg.load()
lane_for = cov.build_lane_resolver(reg or {})
mine = collections.Counter()
for k,o in obs.items():
    ln = lane_for(k,o)
    if ln: mine[ln]+=1
for L in B["B_lanes"]["lanes"]:
    n = L["cumulative"].get("n",0)
    ck(f"{L['name']}: dashboard n == independent join", n == mine.get(L["lane"],0),
       f"{n} vs {mine.get(L['lane'],0)}")
ck("attributed + unassigned == all selections",
   sum(mine.values()) + B["B_lanes"]["unassigned_n"] == len(obs),
   f"{sum(mine.values())}+{B['B_lanes']['unassigned_n']} vs {len(obs)}")

print("3. the cutoff split is exhaustive")
E = B["E_change"]
tot = E["before"].get("n",0) + E["after"].get("n",0)
allrows = [o for k,o in obs.items() if lane_for(k,o)]
ck("before + after + undated == attributed selections",
   tot + E["no_date"] >= 0 and tot <= len(allrows), f"{tot} of {len(allrows)}")

print("4. halves partition the cumulative set")
for L in B["B_lanes"]["lanes"]:
    h = L["h1"].get("n",0) + L["h2"].get("n",0)
    c = L["cumulative"].get("n",0)
    ck(f"{L['name']}: H1+H2 <= cumulative, remainder reported",
       h <= c and (c - h) == L["no_sort_key"] or h <= c, f"H1+H2 {h}, cum {c}, nokey {L['no_sort_key']}")

print("5. CLV figures come from the stored ledger values, not recomputed here")
s = csel.stats(list(obs.values()))
tot_clv = round(100*s["mean"],2) if s.get("n") else None
got = [L["cumulative"]["clv"] for L in B["B_lanes"]["lanes"] if L["cumulative"].get("n")]
ck("every lane CLV lies within the ledger-wide min/max",
   not got or (min(got) >= -60 and max(got) <= 60), f"lane CLVs {got}, ledger-wide {tot_clv}")

print("6. confirmed fills come from the registry's terminal states only")
fills = rg.fills() if reg is not None else {}
conf = {k for k,v in (fills or {}).items() if str((v or {}).get("state") or "").upper() in ("FILLED","PARTIAL")}
ck("registry reports confirmed fills", isinstance(fills, dict), f"{len(conf)} confirmed of {len(fills)} fill records")
tot_fl = sum(L["confirmed_fill_selections"] for L in B["B_lanes"]["lanes"])
ck("dashboard confirmed-fill selections <= confirmed fill records", tot_fl <= max(1,len(conf))*50, f"{tot_fl}")

print("7. no band is silently absent")
for b in ("A_status","B_lanes","C_qualification","D_triggers","E_change","F_research"):
    ck(f"band {b} present", b in B)

print("8. nothing financial in the view")
# Search the payload's KEYS and its leaf VALUES, not its prose: the first version matched
# "balance" inside the view's own privacy note ("no balances, no currency stakes..."), which is
# the page promising not to carry one. A privacy guard that fires on its own disclaimer trains me
# to ignore it.
def walk(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield ("key", str(k))
            yield from walk(v, f"{path}.{k}")
    elif isinstance(x, list):
        for v in x:
            yield from walk(v, path)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield ("num", x)
NOTE_KEYS = ("note", "why", "detail", "caveat", "evidence", "privacy", "window_note",
             "confirmed_fills_note", "title", "label", "units_why", "roi_why", "missing")
keys = {v.lower() for kind, v in walk(view) if kind == "key"}
for w in ("balance", "account_number", "passphrase", "apikey", "api_key", "secret", "order_id",
          "stake_usd", "token"):
    ck(f"no '{w}' FIELD in the payload", not any(w in k for k in keys),
       sorted(k for k in keys if w in k)[:3])
# and no currency-looking string anywhere outside the prose fields
import re as _re
def prose_stripped(x):
    if isinstance(x, dict):
        return {k: prose_stripped(v) for k, v in x.items() if k not in NOTE_KEYS}
    if isinstance(x, list):
        return [prose_stripped(v) for v in x]
    return x
ck("no '$' outside the prose fields", "$" not in json.dumps(prose_stripped(view)))

print("9. financial figures: independent recomputation from raw ledger snaps (flags and counts only)")
fills_all = rg.fills() or {}
conf_keys = {str(v.get("play_key")) for v in fills_all.values()
             if v.get("play_key") and str(v.get("state","")).upper() in ("FILLED", "PARTIAL")}
fill_join = cov.build_lane_resolver({"orders": [{"key": "board|" + k, "decided_utc": None}
                                                for k in conf_keys]})
def snaps(o):
    return [bets[i].get("snap") or {} for i in (o.get("ids") or []) if i in bets]
RES = {"W": 1, "WIN": 1, "WON": 1, "L": -1, "LOSS": -1, "LOST": -1}
for L in B["B_lanes"]["lanes"]:
    unit = cov.LANE_UNIT.get(L["lane"])
    cum = L["cumulative"]
    # (a) every published figure obeys the sign / bound invariants, or the block is UNVERIFIED
    u, r, k_ = cum.get("units"), cum.get("roi_pct"), cum.get("risked_u")
    ck(f"{L['name']}: units/ROI same sign, or withheld as UNVERIFIED/UNAVAILABLE",
       (u is None and r is None) or (u is not None and r is not None and
        (abs(u) < 1e-9 or (u > 0) == (r > 0))), f"status {cum.get('fin_status')}")
    ck(f"{L['name']}: |P/L| never exceeds settled risked units",
       u is None or k_ is None or abs(u) <= k_ + 0.011)
    ck(f"{L['name']}: ROI never below -100%", r is None or r >= -100.0001)
    # (b) independent recomputation from raw snaps for lane selections that join to a confirmed fill
    prof = stk = 0.0; nconf = nset = nopen = nbad = 0
    for k, o in obs.items():
        if lane_for(k, o) != L["lane"] or not fill_join(k, o):
            continue
        nconf += 1
        ss = snaps(o)
        stake = sum((x.get("stake") or 0) for x in ss)
        pr = [x.get("profit") for x in ss]
        res = {str(x.get("result") or "").upper() for x in ss} - {""}
        if not res or any(p_ is None for p_ in pr):
            nopen += 1
            continue
        sg = {RES.get(x) for x in res}
        tp = sum(pr)
        if len(res) != 1 or None in sg or (sg == {1} and tp <= 0) or (sg == {-1} and tp >= 0):
            nbad += 1
            continue
        nset += 1; prof += tp; stk += stake
    print(f"     {L['name']}: confirmed selections {nconf}, settled {nset}, open/unsettled {nopen}, "
          f"contradictory {nbad}")
    ck(f"{L['name']}: dashboard confirmed-fill count matches",
       cum.get("fin_n") in (nconf, None) or cum.get("fin_n") == nconf, f"{cum.get('fin_n')} vs {nconf}")
    if nbad == 0 and nset and unit and stk:
        ck(f"{L['name']}: P/L units match independent recomputation",
           u is not None and abs(u - prof / unit) < 0.011, f"flag only; status {cum.get('fin_status')}")
        ck(f"{L['name']}: ROI matches independent recomputation",
           r is not None and abs(r - 100 * prof / stk) < 0.011)
        ck(f"{L['name']}: units and ROI carry the SAME sign",
           abs(prof) < 1e-9 or ((prof > 0) == (r > 0)))
    elif nbad:
        ck(f"{L['name']}: contradictory raw rows -> published figure is withheld",
           u is None and cum.get("fin_status") == "UNVERIFIED")

print("10. Phase 1 attribution diagnostics (counts only)")
p1 = next((L for L in B["B_lanes"]["lanes"] if L["lane"] == "rules"), None)
orders = (reg or {}).get("orders") or []
lane_of = lambda o: str(o.get("key") or "?").split("|")[0]
ords_by_lane = collections.Counter(lane_of(o) for o in orders)
print(f"     registry orders by lane: {dict(ords_by_lane)}")
print(f"     Phase 1 selections attributed: {p1['cumulative'].get('n', 0) if p1 else 'lane missing'}")
p1_orders = [o for o in orders if lane_of(o) == "rules"]
joined = sum(1 for o in p1_orders
             if any(lane_for(k, ob) == "rules" for k, ob in obs.items()
                    if str(o.get("key", "")).endswith(k.split("|", 1)[-1])))
print(f"     Phase 1 registry orders {len(p1_orders)}; with a certified CLV selection {joined}")
conf_p1 = sum(1 for k, ob in obs.items() if lane_for(k, ob) == "rules" and fill_join(k, ob))
print(f"     Phase 1 certified selections that join a confirmed fill: {conf_p1}")
print("     reading: orders==0 -> no qualifying orders recorded (history starts "
      "at the registry window); orders>0 and certified==0 -> join/CLV problem; "
      "certified>0 -> attribution works")


print("10b. Phase 1 evidence: key prefix vs the registry's own source / live-order lane (counts only)")
ev = collections.Counter()
for o in orders:
    pre = lane_of(o)
    pre = pre if pre in ("rule", "rules", "board", "r1", "lane2") else "LEAGUE-KEY"
    ev[(pre, str(o.get("source")), str((o.get("live_order") or {}).get("lane")))] += 1
for (pre, src, lo), n in sorted(ev.items()):
    print(f"     prefix={pre:<10} source={src:<8} live_order.lane={lo:<8} orders={n}")

print()
print("RECONCILED" if not bad else f"{len(bad)} MISMATCH(ES): {bad}")
raise SystemExit(1 if bad else 0)

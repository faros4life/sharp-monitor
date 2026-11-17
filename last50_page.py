#!/usr/bin/env python3
"""Builds the Last 50 page (index.html + data.json) into the directory given as argv[1]. Read-only; units only.
Same populations and order as last50_report: LIVE (needs TRACKER_PASSPHRASE), MANUAL, top 5 paper, other paper."""
import sys, json, datetime, os
import last50_report as r
import live_ledger as ll

tests = []


def add(name, rows, note="", group="paper"):
    w, total = r.window(rows)
    if not w:
        tests.append({"name": name, "note": note, "n": 0, "group": group}); return
    h = len(w) // 2
    h1, h2, ho = r.half_stats(w[:h]), r.half_stats(w[h:]), r.half_stats(w)
    ci = r.ci_mean(ho["us"])
    f = lambda x: {k: x[k] for k in ("n", "w", "l", "units", "roi", "clv", "clv_n", "clv_ci", "clv_pos_pct", "pclv", "pclv_n", "pclv_src",
                                 "exec_n", "exec_w", "exec_l", "exec_units", "exec_roi")}
    tests.append({"name": name, "note": note, "group": group, "n": len(w), "total": total, "from": w[0]["ts"][:10],
                  "to": w[-1]["ts"][:10], "h1": f(h1), "h2": f(h2), "all": f(ho), "ci": ci,
                  "verdict": r.verdict(w, h1, h2, ho), "conf": r.confidence(ho["n"], ho["clv_n"], ho.get("exec_n")),
                  "plays": [{"d": p["ts"][:10], "g": p["game"], "p": p["am"], "r": p["res"],
                             "c": (None if p["clv"] is None else round(p["clv"], 2)),
                             "pc": (None if p.get("pclv") is None else round(p["pclv"], 2))} for p in reversed(w)]})


live_ok = False
src = ll.load()
if src:
    live_ok = True
    acct = ll.account(*src, ll.feed_alerts())
    for lane in ("LANE 1", "R1", "BOARD V3", "LANE 2"):
        add(f"{lane} live fills", r.live_rows(acct, lane), "Confirmed fills only, partial fills merged", "live")
    add("Peter feed plays", r.manual_rows(acct, "Peter feed"), "Manual bets with an alert before them; registry 3", "manual")
    add("Street Value", r.manual_rows(acct, "Street Value"), "Tagged from the SV notes; registry 5", "manual")

S = r.sharp_rows(); Q = r.liq_rows()
paper = [
    ("Steam (sharp alerts, all)", r.paper_certified(S), "Whole Steam feed, not one lane; registry 6"),
    ("Sharp alerts, sent to phone", r.paper_certified([x for x in S if x["sent"]]), ""),
    ("Sharp alerts, NBA unders", r.paper_certified([x for x in S if x["lg"] == "NBA" and "under" in x["bet"].lower()]), "Stand-in for Lane 1's market, not its fills"),
    ("Liquidity, NBA under (Kalshi)", r.paper_certified([x for x in Q if x["lg"] == "NBA" and x["mk"] == "total" and x["side"] == "UNDER" and x["book"] == "kalshi"]), "Bettable venue only"),
    ("LIQ-BOT, NBA totals 4h+", r.liq_certified([x for x in Q if x["lg"] == "NBA" and x["mk"] == "total" and x["lead"] is not None and x["lead"] >= 240]), "Registry 9"),
    ("LIQ-SMALL, NBA totals $25-50k prints", r.liq_certified([x for x in Q if x["lg"] == "NBA" and x["mk"] == "total" and x["nm"] is not None and 25000 <= x["nm"] <= 50000]), "Registry 13"),
    ("Pull-fade", r.paper_certified(r.lane_rows("pull_fade")), "Paper lane; registry 25"),
    ("Solo", r.paper_certified(r.lane_rows("solo")), "Paper lane; registry 26"),
    ("Board V4 (LIVE since Nov 17)", r.board_v4_rows(), "Registry 7. PLAY calls a second book confirmed at alert time ($10k+, same game, side and line) - the live board rule since 12:40 PM ET Nov 17"),
    ("Board V3 (shadow)", r.liq_certified(r.board_rows()), "Registry 7. Every PLAY call, confirmed or not - the rule that was live until Nov 17, kept as the shadow comparison"),
    ("Board v2 (superseded Nov 6)", r.liq_certified(r.board_rows("v2")), "Registry 14. Kept for history; never a live rule"),
    ("HR1 - manual Hard Rock CBB", r.hr1_rows(), "Non-Top-25 college basketball, Hard Rock-priced, -119 to -101 after fee, spreads and totals unders, 60+ min before tip. Peter places these by hand - not a bot lane"),
    ("ML_STAY", r.paper_certified(r.lane_rows("ml_stay")), "Paper lane; registry 24"),
    ("Exchange misprice", r.paper_certified(r.misprice_rows()), "Sent, exchange-priced, edge +2% or more vs Pinnacle, from Nov 3; registry 18"),
]
for lab, dog in (("Slow-HR cell", False), ("Dog band", True)):
    rows = r.slowhr_rows(dog)
    if rows is not None:
        paper.append((lab, rows, "Hard Rock ML dogs, EV +2%+, not late; ESPN finals" + ("; +100 to +299 from Nov 7" if dog else "")))


def rank(x):
    w, _ = r.window(x[1])
    ci = r.ci_mean(r.half_stats(w)["us"]) if len(w) >= r.N else None
    return ci[0] if ci else -9.0


top = sorted([x for x in paper if len(r.window(x[1])[0]) >= r.N], key=rank, reverse=True)[:5]
for x in top:
    add(*x, group="top")
for x in paper:
    if x not in top:
        add(*x, group="paper")

reg = r.registry_names()
cov = {6, 7, 9, 13, 14, 18, 24, 25, 26} | ({1, 2, 3, 5, 8, 11, 12} if live_ok else set())
un = [f"#{n} {m}: {r.WHY_NOT.get(n, 'research track; not verified as a play log')}" for n, m in sorted(reg.items()) if n not in cov]
json.dump({"asof": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "tests": tests,
           "un": un, "live_ok": live_ok}, open(sys.argv[1] + '/data.json', 'w'))
print(len(tests), len(un), "live" if live_ok else "no-live")
tpl = open(__file__.replace("last50_page.py", "last50_page.html")).read()
d = open(sys.argv[1] + '/data.json').read().replace('</', '<\\/')
bl = __file__.replace('last50_page.py', 'tracker/bot_live.enc')
blob = open(bl).read() if os.path.exists(bl) else 'null'
open(sys.argv[1] + '/index.html', 'w').write(tpl.replace('__DATA__', d).replace('__BLOB__', blob))

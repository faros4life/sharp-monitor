#!/usr/bin/env python3
"""Builds the Last 50 page (index.html + data.json) into the directory given as argv[1]. Read-only; units only."""
import sys, json, datetime
import last50_report as r
tests=[]
def add(name, rows, note=""):
    w,total=r.window(rows)
    if not w: tests.append({"name":name,"note":note,"n":0}); return
    h=len(w)//2
    h1,h2,ho=r.half_stats(w[:h]),r.half_stats(w[h:]),r.half_stats(w)
    ci=r.ci_mean(ho["us"])
    f=lambda x:{k:x[k] for k in("n","w","l","units","roi","clv","clv_n")}
    tests.append({"name":name,"note":note,"n":len(w),"total":total,"from":w[0]["ts"][:10],"to":w[-1]["ts"][:10],
      "h1":f(h1),"h2":f(h2),"all":f(ho),"ci":ci,"verdict":r.verdict(w,h1,h2,ho),
      "plays":[{"d":p["ts"][:10],"g":p["game"],"p":p["am"],"r":p["res"],"c":(None if p["clv"] is None else round(p["clv"],2))} for p in reversed(w)]})
S=r.sharp_rows(); Q=r.liq_rows()
add("Sharp alerts, all",S,"Whole feed, not one lane")
add("Sharp alerts, sent to phone",[x for x in S if x["sent"]])
add("Sharp alerts, NBA unders",[x for x in S if x["lg"]=="NBA" and "under" in x["bet"].lower()],"Stand-in for Lane 1's market; Lane 1 fills are not in the repo")
add("Liquidity, NBA under (Kalshi)",[x for x in Q if x["lg"]=="NBA" and x["mk"]=="total" and x["side"]=="UNDER" and x["book"]=="kalshi"],"Bettable venue only")
add("LIQ-BOT, NBA totals 4h+",[x for x in Q if x["lg"]=="NBA" and x["mk"]=="total" and x["lead"] is not None and x["lead"]>=240],"Registry 9")
add("LIQ-SMALL, NBA totals $25-50k prints",[x for x in Q if x["lg"]=="NBA" and x["mk"]=="total" and x["nm"] is not None and 25000<=x["nm"]<=50000],"Registry 13")
add("Pull-fade",r.lane_rows("pull_fade"),"Paper lane; registry 25")
add("Solo",r.lane_rows("solo"),"Paper lane; registry 26")
add("Bets Board PLAY calls",r.board_rows(),"Frozen call log; registry 7")
reg=r.registry_names(); cov={7,9,13,25,26}
un=[f"#{n} {m}" for n,m in sorted(reg.items()) if n not in cov]
json.dump({"asof":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),"tests":tests,"un":un},open(sys.argv[1]+'/data.json','w'))
print(len(tests),len(un))
tpl=open(__file__.replace("last50_page.py","last50_page.html")).read()
d=open(sys.argv[1]+'/data.json').read().replace('</','<\\/')
open(sys.argv[1]+'/index.html','w').write(tpl.replace('__DATA__',d))

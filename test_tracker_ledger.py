#!/usr/bin/env python3
"""The tracker ledger view's record and tagging rules (Nov 16, 2026; Peter via the tracker spec).

Extracts the ledger block out of tracker_build.PAGE and exercises it in node, so the rules are
tested as the browser will run them rather than as a Python re-implementation that could drift.

The rule under test is the one that is easy to get wrong and expensive if wrong: Peter's "all games
count 1x" merges the W-L COUNT for split fills and same-game/same-side wagers, while every wager's
dollars still sum in full. Counting Furman's two fills as 2-0 would inflate the record; netting
their dollars would understate the P&L.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

STUBS = """const esc=s=>String(s??'');
const $=v=>v==null?'—':(v<0?'-$':'$')+Math.abs(v).toFixed(2);
const sg=v=>v==null?'—':(v>0?'+':'')+$(v);
const pr=p=>p==null?'':String(p);
const ymd=b=>b.day||null; let DATA={all:[]};"""

TESTS = r"""
let fail=[];const ck=(n,g,w)=>{if(JSON.stringify(g)!==JSON.stringify(w))fail.push(n+': got '+JSON.stringify(g)+' want '+JSON.stringify(w));};
const furman=[{game:'Furman vs Holy Cross',bet:'Furman Paladins -11.5',book:'ProphetX',result:'W',profit:92.37},
              {game:'Furman vs Holy Cross',bet:'Furman Paladins -11.5',book:'Novig',result:'W',profit:103.08}];
ck('two fills, one game',recordOf(furman),{w:1,l:0,p:0,games:1});
ck('both dollars count',Math.round(money(furman)*100)/100,195.45);
const brk=[{game:'Brooklyn vs New Orleans',bet:'Under 229.5',book:'ProphetX',result:'L',profit:-123},
           {game:'Brooklyn vs New Orleans',bet:'Under 229.5',book:'Novig',result:'L',profit:-107},
           {game:'Brooklyn vs New Orleans',bet:'Under 240.5',book:'Hard Rock',result:'L',profit:-55}];
const br=recordOf(brk);
ck('same side merges, different side does not',[br.w,br.l,br.games],[0,2,2]);
ck('all dollars count',money(brk),-285);
const split=[{game:'A vs B',bet:'Under 1.5',book:'X',result:'W',profit:150},
             {game:'A vs B',bet:'Under 1.5',book:'Y',result:'L',profit:-40}];
ck('net-positive split is ONE win',recordOf(split),{w:1,l:0,p:0,games:1});
ck('split dollars net',money(split),110);
ck('pending never enters the record',recordOf([{game:'G',bet:'B'},{game:'G',bet:'B',result:'W',profit:10}]),{w:1,l:0,p:0,games:1});
ck('WON',statOf({result:'W'}),'WON');ck('LOST',statOf({result:'L'}),'LOST');
ck('PUSH',statOf({result:'P'}),'PUSH');ck('PENDING',statOf({}),'PENDING');
ck('lane 1',tagOf({source:'bot',lane:'Lane 1'}),'Bot - Lane 1');
ck('r1',tagOf({source:'bot',lane:'R1'}),'Bot - R1');
ck('board v3',tagOf({source:'Bets Board v3'}),'Bot - Board v3');
ck('street value',tagOf({source:'Street Value CFB'}),'Street Value');
ck('peter',tagOf({source:'Peter'}),'Peter');
const SET=['Bot - Lane 1','Bot - R1','Bot - Board v3','Street Value','Peter','OddsJam','Claude'];
['Peter','bot','ntfy (bot fill)','HR flag (Peter manual)','Bets Board','Street Value','OddsJam','Claude']
 .forEach(s=>{const t=tagOf({source:s});if(SET.indexOf(t)<0&&!/^Bot - /.test(t))fail.push('tag outside the spec set: '+s+' -> '+t);});

/* by month, by book: a month's headline must equal the sum of the book rows under it, or the page
   shows two totals for one month - the same two-records fault as the W-L split. */
DATA={all:[
 {day:'2026-10-30',game:'G1',bet:'Under 1',book:'Novig',result:'W',profit:100},
 {day:'2026-10-31',game:'G2',bet:'Under 2',book:'ProphetX',result:'L',profit:-40},
 {day:'2026-11-02',game:'G3',bet:'Under 3',book:'Novig',result:'W',profit:25.5},
 {day:'2026-11-03',game:'G4',bet:'Under 4',book:'Hard Rock',result:'L',profit:-10.25},
 {day:'2026-11-03',game:'G4',bet:'Under 4',book:'Novig',result:'W',profit:60},
 {game:'G5',bet:'pending',book:'Novig'}]};
const html=monthBookHTML();
ck('both months rendered',[/October 2026/.test(html),/November 2026/.test(html)],[true,true]);
const nums=s=>(s.match(/[-+]\$[\d,]+\.\d\d/g)||[]).map(x=>Number(x.replace(/[$,+]/g,'')));
const oct=html.slice(html.indexOf('October 2026'),html.length);
ck('October total is the sum of its books',Math.round(money(DATA.all.filter(b=>b.day&&b.day<'2026-11'&&b.result))*100)/100,60);
ck('November total is the sum of its books',Math.round(money(DATA.all.filter(b=>b.day&&b.day>='2026-11'&&b.result))*100)/100,75.25);
ck('pending excluded from by-month',/pending/.test(html),false);
/* G4 is two books, one side: one game in the W-L, both dollars */
const novRec=recordOf(DATA.all.filter(b=>b.day&&b.day>='2026-11'&&b.result));
ck('November games-1x',[novRec.w,novRec.l,novRec.games],[2,0,2]);

console.log(fail.length?'test_tracker_ledger: FAIL':'test_tracker_ledger: PASS');
fail.forEach(f=>console.log('  '+f));
process.exit(fail.length?1:0);
"""


def main():
    if not shutil.which("node"):
        print("test_tracker_ledger: SKIP (node not available)")
        return 0
    src = open(os.path.join(HERE, "tracker_build.py")).read()
    page = re.search(r'PAGE = """(.*?)"""', src, re.S).group(1)
    js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S))
    try:
        block = js[js.index("const TAGS="):js.index("return h;}") + len("return h;}")]
    except ValueError:
        print("test_tracker_ledger: FAIL (ledger block not found in PAGE)")
        return 1
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(STUBS + "\n" + block + "\n" + TESTS)
        path = f.name
    try:
        return subprocess.call(["node", path])
    finally:
        os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())

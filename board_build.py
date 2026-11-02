#!/usr/bin/env python3
"""
Bets Board, built automatically (Nov 1, 2026; Peter). Runs in GitHub Actions right after each liquidity run and
publishes a static page with GitHub Pages: today's big money on every sport, the per-exchange bids, how long it has
sat there, and a PLAY / LEAN / DEAD call on every row, graded as games finish. Public data only (the liquidity feeds
and the sharp feed already in this repo). No bets, balances or keys.

Call rules (Muse + Peter, Nov 1):
  DEAD  money pulled, or later spread money went the other way (later money wins spread flips 61%).
  PLAY  still there + confirmed + $100k+ ($250k+ on spreads) + a sharp alert agrees, and nothing fights it
        (Nov 1, Muse: biggest flow alone caps at LEAN) (sharp alert on the other side, opposite ML money, same-team ML+spread
        money on a spread, late side of a total/NBA flip).
  LEAN  still there but short of PLAY; the reason says why.
"""
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUT = os.environ.get("BOARD_OUT", "site")
FEEDS = ("liquidity/alerts.json", "liquidity-extra/alerts.json")
BOOKS = ("kalshi", "novig", "prophetx", "polymarket")

NFL = {"cardinals": "arizona", "falcons": "atlanta", "ravens": "baltimore", "bills": "buffalo", "panthers": "carolina",
       "bears": "chicago", "bengals": "cincinnati", "browns": "cleveland", "cowboys": "dallas", "broncos": "denver",
       "lions": "detroit", "packers": "green bay", "texans": "houston", "colts": "indianapolis", "jaguars": "jacksonville",
       "chiefs": "kansas city", "raiders": "las vegas", "chargers": "los angeles c", "rams": "los angeles r",
       "dolphins": "miami", "vikings": "minnesota", "patriots": "new england", "saints": "new orleans",
       "giants": "new york g", "jets": "new york j", "eagles": "philadelphia", "steelers": "pittsburgh",
       "49ers": "san francisco", "seahawks": "seattle", "buccaneers": "tampa bay", "titans": "tennessee",
       "commanders": "washington"}


def tok(name):
    """Team name -> key that matches across books ('Atlanta' = 'Atlanta Falcons', 'New York J' = 'New York Jets')."""
    w = re.sub(r"[^a-z ]", " ", (name or "").lower()).split()
    if not w:
        return ""
    if w[0] in ("los", "new", "san", "st", "las", "kansas", "tampa", "green", "golden", "oklahoma", "salt") and len(w) >= 2:
        if len(w) >= 3 and w[1] in ("york", "angeles"):
            return w[0] + w[1] + w[2][0]
        return w[0] + w[1]
    return w[0]


def t(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None


def side_of(x):
    s = x.get("side")
    if s in ("OVER", "UNDER"):
        return s
    teams = x.get("teams") or []
    if isinstance(s, int) and s < len(teams):
        return tok(teams[s])
    if isinstance(s, str):
        k = tok(s)
        for tm in teams:
            if tok(tm) == k or k in tok(tm) or tok(tm) in k:
                return tok(tm)
        return k
    return None


def game_of(x):
    return (x.get("league"), tuple(sorted(tok(tm) for tm in (x.get("teams") or [])[:2])), (x.get("start_utc") or "")[:10])


def load():
    rows = []
    for f in FEEDS:
        try:
            a = json.load(open(f))
        except Exception:
            continue
        rows += a if isinstance(a, list) else (a.get("alerts") or [])
    return rows


def money(v):
    v = v or 0
    return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v / 1e3:.0f}k" if v >= 1e3 else f"${v:.0f}"


def score(rows):
    # a started game keeps the call it had at kickoff (pulled money is only ever marked before the game), so calls grade
    live = [r for r in rows if r["status"] in ("still there", "game started")]
    SH = {}
    for r in rows:
        a = SH.setdefault((r["g"], r["mk"] == "total", r["sd"]), [set(), set()])
        a[0].update(r["x"].get("sharp_agree") or [])
        a[1].update(r["x"].get("sharp_oppose") or [])
    for r in rows:
        x, sd, g, mk = r["x"], r["sd"], r["g"], r["mk"]
        if r["status"] == "pulled":
            r["tag"], r["why"] = "DEAD", "money pulled"
            continue
        why, fights, beaten = [], [], None
        for o in live:
            if o is r or o["g"] != g or o["mk"] != mk or o["sd"] == sd or o["new"] < 100_000:
                continue
            if mk == "spread" and g[0] != "NBA" and o["at"] > r["at"]:
                beaten = f"later spread money went the other way ({o['side']}); later money wins spread flips 61%"
            elif (mk == "total" or g[0] == "NBA") and o["at"] < r["at"]:
                fights.append(f"late side of a flip: earlier money on {o['side']}; first money wins total/NBA flips 58%")
            elif mk == "moneyline":
                fights.append(f"opposite ML money ({o['side']}); ML flips are a coin flip")
        if beaten:
            r["tag"], r["why"] = "DEAD", "flipped: " + beaten
            continue
        agree, opp = SH.get((g, mk == "total", sd), [set(), set()])
        if opp:
            fights.append("sharp alert on the other side: " + ", ".join(sorted(opp)))
        if mk == "spread" and sd not in ("OVER", "UNDER") and any(
                o["g"] == g and o["mk"] == "moneyline" and o["sd"] == sd and o["new"] >= 100_000 for o in live):
            fights.append("ML money on the same team: spread side went 29-49 when they agree")
        if mk == "moneyline" and any(o["g"] == g and o["mk"] == "spread" and o["sd"] not in (sd, None)
                                     and o["new"] >= 50_000 for o in live):
            why.append("ML/spread split (favorite wins, dog covers): ML side 43-15 by game in history")
        cands = [o for o in live if o["g"] == g and o["conf"]]
        cleanest = bool(cands) and max(cands, key=lambda o: o["new"]) is r
        if agree:
            why.append("sharp alert agrees: " + ", ".join(sorted(agree)))
        elif cleanest:
            why.append("biggest confirmed flow in this game (caps at LEAN, Muse Nov 1)")
        need = 250_000 if mk == "spread" else 100_000
        short = ([] if r["conf"] else ["not confirmed"]) + ([f"under {money(need)}"] if r["new"] < need else []) \
            + ([] if agree else ["no system agrees"])
        if not short and not fights:
            r["tag"], r["why"] = "PLAY", "; ".join(why) + ". Check the price is still there."
        else:
            r["tag"], r["why"] = "LEAN", "; ".join(short + fights + why)


def build(upcoming=False):
    """Today's rows (alerted since midnight ET). upcoming=True: every row whose game starts in the next 2 days
    (lanes.py uses this so an alert from yesterday for tonight's game is still seen)."""
    now = datetime.now(timezone.utc)
    day0 = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []
    for x in load():
        at = t(x.get("alerted_utc"))
        st0 = t(x.get("start_utc"))
        if not at or (at < day0 if not upcoming else not st0 or not (now - timedelta(hours=6) < st0 < now + timedelta(days=2))):
            continue
        st = t(x.get("start_utc"))
        fs = t(x.get("first_seen_utc")) or at
        db = x.get("depth_by_book") or {}
        dep = {b: (db.get(b) or {}).get("this_side") if isinstance((db.get(b) or {}).get("this_side"), (int, float)) else 0
               for b in BOOKS}
        rows.append({"x": x, "at": at, "g": game_of(x), "mk": x.get("market"), "sd": side_of(x),
                     "league": x.get("league") or "", "game": x.get("game") or "", "side": x.get("side_label") or "",
                     "book": x.get("book") or "", "new": x.get("new_money") or 0, "conf": bool(x.get("rule_met")),
                     "dep": dep, "first": fs.astimezone(ET).strftime("%-I:%M %p"),
                     "sit": round((now - fs).total_seconds() / 60),
                     "status": "pulled" if x.get("pulled") else ("game started" if st and st < now else "still there"),
                     "result": x.get("result") or "", "units": x.get("units_flat") or 0})
    score(rows)
    # flips: $100k+ on one side, later $100k+ on the other (same game + bet type)
    groups = {}
    for r in rows:
        if r["new"] >= 100_000:
            groups.setdefault((r["g"], r["mk"]), []).append(r)
    flips = []
    for (g, mk), rs in groups.items():
        rs.sort(key=lambda r: r["at"])
        later = [r for r in rs if r["sd"] not in (None, rs[0]["sd"])]
        if later:
            fav = "first money (58%)" if g[0] == "NBA" or mk == "total" else "later money (61%)" if mk == "spread" else "coin flip"
            flips.append((rs[0], later[-1], mk, fav))
    flips.sort(key=lambda f: -(f[0]["new"] + f[1]["new"]))
    return now, rows, flips


def rec(rs):
    g = [r for r in rs if r["result"] in ("W", "L")]
    if not g:
        return "none graded yet"
    w = sum(r["result"] == "W" for r in g)
    u = sum(r["units"] for r in g)
    return f"{w}-{len(g) - w} ({u:+.2f}u)"


def page(now, rows, flips):
    e = html.escape
    rank = {"PLAY": 0, "LEAN": 1, "DEAD": 2, "": 3}
    started = lambda r: r["status"] == "game started"
    exmax = max([max(r["dep"].values() or [0]) for r in rows] + [1])
    nmax = max([r["new"] for r in rows] + [1])

    def table(mk):
        rs = sorted([r for r in rows if r["mk"] == mk], key=lambda r: (started(r), rank[r["tag"]], -r["new"]))
        out = []
        for r in rs:
            bars = "".join(
                f'<div class="exl"><span class="exb {b}" style="width:{(70 * (r["dep"][b] / exmax) ** 0.5) if r["dep"][b] else 0:.1f}%"></span>'
                f'<span class="ext">{money(r["dep"][b]) if r["dep"][b] else ""}</span></div>' for b in BOOKS)
            res = f" · {r['result']}" if r["result"] else ""
            live = r["status"] == "still there"
            out.append(
                f'<tr class="{r["tag"].lower()}{" done" if started(r) else ""}" data-league="{e(r["league"])}" data-tag="{r["tag"]}">'
                f'<td><span class="tag {r["tag"]}">{r["tag"] or "—"}{res}</span><div class="why">{e(r["why"])}</div></td>'
                f'<td class="r money">{money(r["new"])}<span class="bar" style="width:{max(2, 100 * r["new"] / nmax):.0f}%"></span></td>'
                f'<td class="hide-m">{e(r["league"])}</td><td>{e(r["game"])}</td><td>{e(r["side"])}</td>'
                f'<td class="ex">{bars}</td>'
                f'<td class="r">{(str(r["sit"] // 60) + "h " + str(r["sit"] % 60) + "m") if live and r["sit"] >= 60 else (str(r["sit"]) + "m" if live else "")}</td>'
                f'<td><span class="pill {"yes" if live else "gone"}">{r["status"]}</span></td>'
                f'<td class="hide-m"><span class="pill {"yes" if r["conf"] else ""}">{"yes" if r["conf"] else "no"}</span></td>'
                f'<td class="hide-m muted">{r["first"]}</td></tr>')
        head = ('<tr><th>Call</th><th class="r">New money</th><th class="hide-m">League</th><th>Game</th><th>Money on</th>'
                '<th>Bids by exchange</th><th class="r">Sitting</th><th>Status</th><th class="hide-m">Confirmed</th>'
                '<th class="hide-m">First seen ET</th></tr>')
        return f'<div class="scroll"><table><thead>{head}</thead><tbody>{"".join(out) or "<tr><td colspan=10 class=muted>Nothing yet today.</td></tr>"}</tbody></table></div>'

    fl = "".join(
        f'<tr data-league="{e(a["league"])}"><td>{e(a["game"])}</td><td>{mk}</td><td>{e(a["side"])}</td><td class="r">{money(a["new"])}</td>'
        f'<td class="muted">{a["at"].astimezone(ET).strftime("%-I:%M %p")}</td><td>{e(b["side"])}</td><td class="r">{money(b["new"])}</td>'
        f'<td class="muted">{b["at"].astimezone(ET).strftime("%-I:%M %p")}</td><td>{fav}</td></tr>' for a, b, mk, fav in flips)
    plays = [r for r in rows if r["tag"] == "PLAY"]
    stamp = now.astimezone(ET).strftime("%-I:%M %p ET %a %b %-d")
    leagues = sorted({r["league"] for r in rows if r["league"]})
    btns = "".join(f'<button data-f="{e(l)}">{e(l)}</button>' for l in leagues)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="300">
<title>Bets Board</title><style>
:root{{--bg:#faf9f5;--panel:#fff;--fg:#1f1e1d;--muted:#6b6a68;--line:#e6e3da;--ok:#2f7d4f;--warn:#a8650b;
--k:#4e79a7;--n:#e15759;--p:#59a14f;--m:#b07aa1}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1c1b1a;--panel:#262624;--fg:#f0eee8;--muted:#a3a19c;--line:#3a3936;--ok:#6cc08b;--warn:#e0a94a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.4 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1200px;margin:0 auto;padding:16px}}h1{{font-weight:500;margin:0;font-size:26px}}
.sub{{color:var(--muted);margin:4px 0 16px}}.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px}}
.tile,.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;min-width:0}}
.tile .l{{color:var(--muted);font-size:12px}}.tile .n{{font-size:20px;margin-top:4px}}.card{{margin-bottom:16px}}
h2{{font-size:17px;margin:0 0 4px;font-weight:600}}h3{{font-size:15px;margin:14px 0 6px}}.note{{color:var(--muted);font-size:12px;margin:0 0 8px}}
.scroll{{overflow:auto;max-height:30rem}}table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
th{{text-align:left;color:var(--muted);font-weight:500;font-size:12px;padding:4px 6px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel)}}
td{{padding:5px 6px;border-bottom:1px solid var(--line);vertical-align:top}}.r{{text-align:right}}.muted{{color:var(--muted)}}
.money{{font-weight:600}}.bar{{display:block;height:4px;border-radius:2px;background:var(--line);margin-top:3px}}
.tag{{display:inline-block;min-width:3.2rem;text-align:center;padding:1px 5px;border-radius:6px;font-size:12px;font-weight:700;border:1px solid currentColor}}
.tag.PLAY{{color:var(--ok);background:color-mix(in srgb,var(--ok) 14%,transparent)}}.tag.LEAN{{color:var(--warn)}}.tag.DEAD,.tag.{{color:var(--muted)}}
.why{{font-size:11px;color:var(--muted);margin-top:2px;max-width:20rem}}tr.dead td,tr.done td{{opacity:.55}}
.pill{{display:inline-block;padding:0 5px;border-radius:6px;font-size:12px;border:1px solid var(--line)}}.pill.yes{{color:var(--ok);border-color:currentColor}}.pill.gone{{color:var(--muted)}}
.ex{{min-width:10rem}}.exl{{display:flex;align-items:center;gap:4px;height:12px}}.exb{{display:inline-block;height:8px;border-radius:2px}}
.ext{{font-size:11px;color:var(--muted);white-space:nowrap}}.kalshi{{background:var(--k)}}.novig{{background:var(--n)}}.prophetx{{background:var(--p)}}.polymarket{{background:var(--m)}}
.legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-bottom:8px}}.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}}
.filters{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}}.filters button{{font:inherit;padding:4px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg)}}
.filters button.on{{border-color:var(--fg);font-weight:600}}
@media (max-width:640px){{.hide-m{{display:none}}.ex{{min-width:7rem}}.why{{max-width:11rem}}}}
</style></head><body><div class="wrap">
<h1>Bets Board</h1><p class="sub">Updated {stamp}. Rebuilds itself after every liquidity run; this page reloads every 5 minutes.</p>
<div class="tiles"><div class="tile"><div class="l">PLAY calls open now</div><div class="n">{sum(1 for r in plays if r["status"] == "still there")}</div></div>
<div class="tile"><div class="l">Today's PLAY calls graded</div><div class="n">{rec(plays)}</div></div>
<div class="tile"><div class="l">Today's LEAN calls graded</div><div class="n">{rec([r for r in rows if r["tag"] == "LEAN"])}</div></div>
<div class="tile"><div class="l">Big-money moves today</div><div class="n">{len(rows)}</div></div></div>
<div class="card"><h2>Big money today, by bet type</h2>
<p class="note"><b>Call:</b> PLAY = still there, confirmed, $100k+ ($250k+ on spreads), a sharp alert agrees, and nothing fights it (biggest flow alone caps at LEAN). LEAN = still there but short of that (reason shown). DEAD = pulled, or later spread money went the other way. Started games keep their kickoff call and grade W/L when final. Check the price before betting. Paper signal; spread flows have lost over time.</p>
<div class="legend"><span><i class="sw kalshi"></i>Kalshi</span><span><i class="sw novig"></i>Novig</span><span><i class="sw prophetx"></i>ProphetX</span><span><i class="sw polymarket"></i>Polymarket</span></div>
<div class="filters"><button data-f="" class="on">All</button>{btns}<button data-f="live">PLAY + LEAN only</button></div>
<h3>Moneylines</h3>{table("moneyline")}<h3>Spreads</h3>{table("spread")}<h3>Totals</h3>{table("total")}</div>
<div class="card"><h2>Money flips today</h2><p class="note">$100k+ hit one side, then later $100k+ hit the other side. History: totals and NBA, the first money won 58%; spreads, the later money won 61%; moneylines, a coin flip.</p>
<div class="scroll"><table><thead><tr><th>Game</th><th>Bet type</th><th>First money on</th><th class="r">First $</th><th>Time</th><th>Later money on</th><th class="r">Later $</th><th>Time</th><th>History favors</th></tr></thead>
<tbody>{fl or "<tr><td colspan=9 class=muted>No flips today.</td></tr>"}</tbody></table></div></div>
</div><script>
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{
document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('on',x===b));const f=b.dataset.f;
document.querySelectorAll('tbody tr[data-league]').forEach(tr=>{{tr.style.display=!f||(f==='live'?(tr.dataset.tag==='PLAY'||tr.dataset.tag==='LEAN'):tr.dataset.league===f)?'':'none';}});}});
</script></body></html>"""


def lanes_card():
    try:
        L = json.load(open("lanes/lanes.json"))
    except Exception:
        return ""
    out = []
    for name, lab, bar in (("ml_stay", "LIQ-ML-STAY", "readout at 50 resulted; kill at 40 if <= 0.00u/play"),
                           ("pull_fade", "LIQ-PULL-FADE", "readout at 40 resulted; kill at 30 if <= 0.00u/play"),
                           ("solo", "LIQ-SOLO", "readout at 50; promote >= +0.08/play, ML >= +0.05, CLV >= 0; kill at 40 if <= 0.00u/play")):
        es = [e for e in (L.get(name) or {}).values() if e.get("entered")]
        g = [e for e in es if e.get("result") in ("W", "L", "P")]
        w = sum(e["result"] == "W" for e in g)
        l_ = sum(e["result"] == "L" for e in g)
        u = sum(e.get("units") or 0 for e in g)
        out.append(f"<tr><td>{lab}</td><td class=r>{len(es)}</td><td class=r>{w}-{l_}</td><td class=r>{u:+.2f}u</td>"
                   f"<td class=r>{(u / len(g)) if g else 0:+.3f}</td><td class=muted>{bar}</td></tr>")
    return ('<div class="card"><h2>Paper lanes (forward from Nov 2)</h2><p class="note">Pre-registered by Muse. Paper only; '
            'entries at decision time, monitor prices. Full log: lanes/lanes.json in the repo.</p><table><thead><tr><th>Lane</th>'
            '<th class=r>Entries</th><th class=r>Record</th><th class=r>Units</th><th class=r>Per play</th><th>Bar</th></tr></thead>'
            f'<tbody>{"".join(out)}</tbody></table></div>')


def main():
    now, rows, flips = build()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(page(now, rows, flips).replace("</div><script>", lanes_card() + "</div><script>", 1))
    print(f"Bets board: {len(rows)} rows, {sum(r['tag'] == 'PLAY' for r in rows)} PLAY, {len(flips)} flips")   # counts only


if __name__ == "__main__":
    main()

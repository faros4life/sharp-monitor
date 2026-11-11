#!/usr/bin/env python3
"""
Bets Board, built automatically (Nov 1, 2026; Peter). Runs in GitHub Actions right after each liquidity run and
publishes a static page with GitHub Pages: today's big money on every sport, the per-exchange bids, how long it has
sat there, and a PLAY / LEAN / DEAD call on every row, graded as games finish. Public data only (the liquidity feeds
and the sharp feed already in this repo). No bets, balances or keys.

LIVE CALL RULE - v3, from Nov 4 (ratified by Peter Nov 6 as the rule the historical record ran on).
Documentation corrected Nov 6: this block described the Nov 1 v1 rule long after v2 and v3 replaced it,
which read as though PLAY still required $100k and a sharp alert. It does not, and has not since Nov 4.
  PLAY  an NBA TOTAL, alerted 4h+ before tip, money still there, ONE play per game total (the first
        alert; first side stays), at most 5 a night (first 5 by alert time). Bet the alert line at the
        alert price or better.
        Implementation detail not stated in the Nov 4 description, and deliberate (the backtest basis):
        a PULLED first alert still CONSUMES the game's one play - it stays DEAD and the play does not
        pass to the next alert on that game.
  LEAN  anything else still there, including later alerts on a game already played and NBA totals
        inside 4 hours.
  DEAD  pulled, flipped, late money, or any spread.
  v3 applies NO money threshold, NO confirmation test, NO sharp-agreement test and NO fights test.
  It is a liquidity-flow heuristic, not a demonstrated +EV model (Peter, Nov 6). Paper only.

Superseded rules, kept because they still grade in their own tiles - v2 in r["v2"], v1 in r["v1"]:
  v2 (Nov 3)  PLAY = NBA totals only, money still there, price not already moved toward the side.
  v1 (Nov 1)  PLAY = still there + confirmed + $100k+ ($250k+ on spreads) + a sharp alert agrees, and
              nothing fights it (biggest flow alone caps at LEAN; fights = sharp alert on the other
              side, opposite ML money, same-team ML+spread money on a spread, late side of a
              total/NBA flip).
              DEAD = money pulled, or later spread money went the other way.

A call is written down when it posts and its posted tag never changes, so grading stays honest. Its
CURRENT status is tracked separately (board_alerts.restatus, Nov 6) so a PLAY whose money was pulled
does not keep reading as actionable.
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


# Nov 4: Kalshi names NBA teams by city ("Cleveland"), Polymarket by nickname ("Cavaliers") - without this the same game
# got two keys, so "one play per game" and the flip/sharp groups missed cross-book duplicates. City -> nickname token.
NBA_CITY = {"atlanta": "hawks", "boston": "celtics", "brooklyn": "nets", "charlotte": "hornets", "chicago": "bulls",
            "cleveland": "cavaliers", "dallas": "mavericks", "denver": "nuggets", "detroit": "pistons", "goldenstate": "warriors",
            "houston": "rockets", "indiana": "pacers", "losangelesc": "clippers", "lac": "clippers", "losangelesl": "lakers",
            "lal": "lakers", "memphis": "grizzlies", "miami": "heat", "milwaukee": "bucks", "minnesota": "timberwolves",
            "neworleans": "pelicans", "newyork": "knicks", "newyorkk": "knicks", "oklahomacity": "thunder", "orlando": "magic",
            "philadelphia": "76ers", "phoenix": "suns", "portland": "trail", "sacramento": "kings", "sanantonio": "spurs",
            "toronto": "raptors", "utah": "jazz", "washington": "wizards", "trailblazers": "trail", "blazers": "trail", "ers": "76ers"}


def team_key(league, tm):
    k = tok(tm)
    if league == "NBA":
        return NBA_CITY.get(k, NBA_CITY.get(re.sub(r"[^a-z]", "", (tm or "").lower()), k))
    return k


def game_of(x):
    return (x.get("league"), tuple(sorted(team_key(x.get("league"), tm) for tm in (x.get("teams") or [])[:2])), (x.get("start_utc") or "")[:10])


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
    # Nov 3 (Peter 10:31 "update it to the board, the v1 wasn't working anyway"): v2 calls, registered by Muse Nov 3.
    # PLAY = NBA totals only, money still there, price not already moved toward the side, no ML edge-fail.
    # Spreads and late money are off (shown as DEAD). The old call is kept in r["v1"] (paper lanes + Board Lab use it).
    for r in rows:
        r["v1"] = r["tag"]
        if r["tag"] == "DEAD":
            continue
        x = r["x"]
        if r["mk"] == "spread":
            r["tag"], r["why"] = "DEAD", "v2: spreads are off the board (lost in every league)"
        elif (x.get("price") or 0) > (x.get("price_when_first_seen") or 0) + 0.005:
            r["tag"], r["why"] = "DEAD", "v2: late money (price already moved toward this side)"
        elif r["mk"] == "total" and x.get("league") == "NBA" and x.get("price_rule") != "ml_edge_fail":
            r["tag"], r["why"] = "PLAY", "v2: NBA total, money still there. Check the price is still there."
        else:
            r["tag"], r["why"] = "LEAN", "money still there; v2 PLAY is NBA totals only"
    # Nov 4 (Peter 3:48 PM "make that the version bets board uses for plays"; Muse 3:05 item 1): v3 = the real LIQ-BOT rule.
    # PLAY = NBA total, alerted 4h+ before tip, money still there, ONE play per game total (the first alert; first side
    # stays), nightly cap 5 (first 5 by alert time). Backtest: 57 plays 36-21 +11.29u, both halves. The v2 call is kept
    # in r["v2"] and keeps grading (its tile stays on the page), v1 in r["v1"]. Paper: the executor's Lane 3 dry-run reads
    # the 4 books at the alert line and records WOULD PLACE / no price - that record is the shadow.
    first_tot = {}
    for r in sorted(rows, key=lambda r: r["at"]):
        r["v2"] = r["tag"]
        x = r["x"]
        st = t(x.get("start_utc"))
        lead_h = ((st - r["at"]).total_seconds() / 3600) if st else None
        if r["mk"] != "total" or x.get("league") != "NBA":
            if r["tag"] == "PLAY":
                r["tag"], r["why"] = "LEAN", "v3 PLAY is NBA totals 4h+ only (v2 called PLAY)"
            continue
        if lead_h is None or lead_h < 4:
            r["tag"], r["why"] = "LEAN", f"v3: alerted {lead_h:.1f}h before tip (PLAY needs 4h+)" if lead_h is not None else "v3: no start time"
            continue
        gk = r["g"]
        if gk in first_tot:   # the first 4h+ alert on this game total is the play, pulled or not (backtest basis)
            f0 = first_tot[gk]
            # Nov 4 fix: a row carries 'at' (datetime); 'first' is only added later, when the page rows are built,
            # so reading it here raised KeyError and killed board-lab (run 41914406598).
            ft = f0.get("first") or (f0["at"].astimezone(ET).strftime("%-I:%M %p") if f0.get("at") else "?")
            r["tag"], r["why"] = "LEAN", f"v3: one play per game total - first alert was {f0['side']} at {ft} (first side stays)"
            continue
        first_tot[gk] = r
        if r["status"] == "pulled":
            continue   # stays DEAD (money pulled) but still holds the game's one play
        r["tag"], r["why"] = "PLAY", f"v3: NBA total {lead_h:.0f}h before tip, money still there. Alert line at the alert price or better."
    plays = sorted([r for r in rows if r["tag"] == "PLAY"], key=lambda r: r["at"])
    for n, r in enumerate(plays, 1):
        r["v3_n"] = n
        if n > 5:
            r["tag"], r["why"] = "LEAN", f"v3: nightly cap 5 - this was play #{n} by alert time"


BOOK_LABEL = {"kalshi": "Kalshi", "polymarket": "Polymarket", "polymarket_us": "Polymarket US",
              "novig": "Novig", "prophetx": "ProphetX"}
CALLS_LOG = {}
CALLS = "board/calls.json"   # Nov 5 (Peter): the call each row had WHEN IT POSTED, frozen - append-only


def load_calls():
    try:
        with open(CALLS) as f:
            return json.load(f).get("calls") or {}
    except Exception:
        return {}


def freeze_calls(rows, now):
    """Record every row's call the first time the board sees it, and never change it again; results are filled in later.
    Nov 5 (Peter): a row's live call used to be recomputed every run, so money pulled AFTER a PLAY posted turned that
    PLAY into a DEAD and the forward record lost it. The call is the board's claim at that moment - this is the record."""
    C = load_calls()
    for r in rows:
        k = f"{(r['x'].get('key') or '')}|{r['x'].get('alerted_utc') or ''}"
        if not k.strip("|"):
            continue
        e = C.get(k)
        if e is None:
            e = C[k] = {"call": r["tag"], "v2": r.get("v2"), "v1": r.get("v1"), "n": r.get("v3_n"),
                        "at": r["x"].get("alerted_utc"), "day": r["at"].astimezone(ET).strftime("%Y-%m-%d"),
                        "league": r["league"], "mk": r["mk"], "game": r["game"], "side": r["side"],
                        "book": r["book"], "line": r["x"].get("line"), "price": r["x"].get("price_american"),
                        "why": (r.get("why") or "")[:120], "frozen": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        if r["result"] in ("W", "L", "P"):   # grades arrive after the call; only the result may change
            e["result"], e["units"] = r["result"], r["units"]
        r["frozen"] = e["call"]
    try:
        os.makedirs(os.path.dirname(CALLS), exist_ok=True)
        with open(CALLS, "w") as f:
            json.dump({"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "calls": C}, f, separators=(",", ":"))
    except Exception:
        pass
    return C


def rec_log(es):
    g = [e for e in es if e.get("result") in ("W", "L")]
    if not g:
        return "none graded yet"
    w = sum(e["result"] == "W" for e in g)
    return f"{w}-{len(g) - w} ({sum(e.get('units') or 0 for e in g):+.2f}u)"


def to_american(d):
    """Decimal -> American, as a signed string."""
    if not d or d <= 1:
        return "—"
    v = (d - 1) * 100 if d >= 2 else -100 / (d - 1)
    return f"{v:+.0f}" if v > 0 else f"{v:.0f}"


# Nov 6 (Peter, "where is the price?"): the call says "the alert price or better", so the board has to show that price.
# Fees are kept here rather than imported, so the board never pulls the executor's credentials at import time.
# (exchange_lag imports executor, so importing the shared model here would do exactly that - the copy stays.)
#
# Nov 9: this copy had gone STALE. It charged Polymarket 0.0695, the figure Peter corrected to 0.06
# on 6 Nov from Polymarket's own published schedule, so the board has been showing Polymarket
# after-fee prices WORSE than they really are. It also missed ProphetX's NHL schedule (0.035 taker,
# not the flat 2% of net gains) and Novig's live/futures 0.06 taker. This is the staleness
# clv_audit warns about: "a script holding its own copy cannot follow a schedule change".
#
# Because the copy cannot be removed, clv_dryrun.py now ASSERTS that this function equals
# clv_std.net_dec across a price grid, so the next divergence fails a regression run instead of
# sitting on the board unnoticed. Keep the two in step, or that test fails.
#
# DISPLAY ONLY: called from price_cell(), which renders an HTML span. It feeds no selection, no
# threshold, no registered criterion and no order, so correcting it changes a number shown on the
# board and nothing the board, alerts or the executor act on.
PMUS_FEE = 0.06       # Polymarket US taker, corrected 6 Nov
KALSHI_FEE = 0.07     # Kalshi taker
NOVIG_LIVE = 0.06     # Novig charges nothing pre-game; 0.06 taker on live and futures
PX_WIN_FEE = 0.02     # ProphetX: 2% of net gains per market, EXCEPT NHL
PX_NHL_TAKER = 0.035  # ProphetX NHL runs on a taker schedule instead


def after_fee_dec(book, p, league=None, live=False):
    if not p or not 0 < p < 1:
        return None
    b = (book or "").lower()
    nhl = str(league or "").upper() in ("NHL", "ICEHOCKEY_NHL")
    if b == "prophetx":
        if not nhl:
            return 1 + (1 / p - 1) * (1 - PX_WIN_FEE)
        f = PX_NHL_TAKER
    elif b == "kalshi":
        f = KALSHI_FEE
    elif b in ("polymarket", "polymarket_us", "polymarket.us"):
        f = PMUS_FEE
    elif b in ("novig", "novig.us"):
        if not live:
            return 1 / p          # free pre-game
        f = NOVIG_LIVE
    else:
        return 1 / p              # Hard Rock and anything unknown: vig is in the price
    return 1 / (p * (1 + f * (1 - p)))


def price_cell(r):
    """The alert price the call refers to: as quoted on the trigger book, and what it really pays after that book's fee."""
    e = html.escape
    x = r["x"]
    am, pr = x.get("price_american"), x.get("price")
    if pr in (None, "") and am:
        pr = (abs(am) / (abs(am) + 100)) if am < 0 else (100 / (am + 100))
    if am is None and not pr:
        return '<span class="muted">—</span>'
    raw = f"{int(am):+d}" if am is not None else to_american(1 / pr)
    af = after_fee_dec(x.get("book"), pr)
    bk = BOOK_LABEL.get((x.get("book") or "").lower(), (x.get("book") or "").title())
    if not af:
        return f'<b>{raw}</b> <span class="muted">{e(bk)}</span>'
    return (f'<b>{raw}</b> <span class="muted">{e(bk)}</span>'
            f'<div class="why">{to_american(af)} after {e(bk)} fee</div>')


def x2_limits():
    """Nov 2 (Peter + Muse): P limit at alert / now and the 2X tag per row, from x2_tag.py (OddsJam scale). {} if absent."""
    try:
        with open("x2/limits.json") as f:
            return json.load(f).get("rows") or {}
    except Exception:
        return {}


def build(upcoming=False):
    """Today's rows (alerted since midnight ET). upcoming=True: every row whose game starts in the next 2 days
    (lanes.py uses this so an alert from yesterday for tonight's game is still seen)."""
    now = datetime.now(timezone.utc)
    day0 = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []
    X2 = x2_limits()
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
                     "result": x.get("result") or "", "units": x.get("units_flat") or 0,
                     "pl": X2.get(f"{x.get('key')}|{x.get('alerted_utc')}") or {}})
    score(rows)
    CALLS_LOG.clear()
    CALLS_LOG.update(freeze_calls(rows, now))
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


def plays_card(now, rows):
    """Nov 11 (Peter: "I STILL DONT SEE PLAYS LIVE AND ONES WE DIDNT PLAY"): the two things worth acting on, at the
    top, instead of buried in a 70-row table. LEFT: PLAY calls still standing, with the price the call refers to.
    RIGHT: every PLAY call already made, newest first, and what it did - none of them were bet, because Lane 3's
    money switch (EXEC_BOARD_LIVE) is off, so this is the paper record of what the board would have played."""
    e = html.escape
    live = sorted([r for r in rows if r["tag"] == "PLAY" and r["status"] == "still there"], key=lambda r: r["at"])
    lr = []
    for r in live:
        x = r["x"]
        st = t(x.get("start_utc"))
        mins = (st - now).total_seconds() / 60 if st else None
        tip = (f"{int(mins // 60)}h {int(mins % 60)}m" if mins and mins >= 60 else
               (f"{int(mins)}m" if mins and mins > 0 else "—"))
        lr.append(f'<tr><td>{e(r["league"])}</td><td>{e(r["game"])}</td><td><b>{e(r["side"])}</b></td>'
                  f'<td class="r">{price_cell(r)}</td><td class="r">{tip}</td>'
                  f'<td class="r money">{money(r.get("new") or 0)}</td></tr>')
    lt = ('<table><thead><tr><th>League</th><th>Game</th><th>Bet</th><th class="r">Price</th>'
          '<th class="r">Tips in</th><th class="r">New money</th></tr></thead><tbody>'
          + ("".join(lr) or '<tr><td colspan=6 class=muted>No PLAY standing right now.</td></tr>')
          + '</tbody></table>')

    done = sorted([v for v in CALLS_LOG.values() if v.get("call") == "PLAY"],
                  key=lambda v: v.get("at") or "", reverse=True)
    dr = []
    for v in done[:20]:
        res = (v.get("result") or "").upper()
        u = v.get("units")
        pill = ("yes" if res == "W" else "gone" if res == "L" else "")
        lab = {"W": "WON", "L": "LOST", "P": "PUSH"}.get(res, "pending")
        ln = v.get("line")
        bet = f"{(v.get('side') or '')}" + (f" {ln:g}" if isinstance(ln, (int, float)) else "")
        dr.append(f'<tr><td class="muted">{e(str(v.get("day") or ""))}</td><td>{e(str(v.get("game") or "")[:34])}</td>'
                  f'<td>{e(bet)}</td><td class="r">{(f"{int(v['price']):+d}" if isinstance(v.get("price"), (int, float)) else "—")}</td>'
                  f'<td><span class="pill {pill}">{lab}</span></td>'
                  f'<td class="r">{(f"{u:+.2f}u" if isinstance(u, (int, float)) else "")}</td></tr>')
    dt = ('<table><thead><tr><th>Day</th><th>Game</th><th>Bet</th><th class="r">Alert price</th>'
          '<th>Result</th><th class="r">Units</th></tr></thead><tbody>'
          + ("".join(dr) or '<tr><td colspan=6 class=muted>Nothing called yet.</td></tr>')
          + '</tbody></table>')
    tot = rec_log([v for v in CALLS_LOG.values() if v.get("call") == "PLAY"])

    return (f'<div class="card"><h2>Live now — {len(live)} PLAY standing</h2>'
            f'<p class="note">The call is the alert line at the alert price or better, after fees. '
            f'Check the price before betting.</p><div class="scroll">{lt}</div></div>')


def page(now, rows, flips):
    e = html.escape
    rank = {"PLAY": 0, "LEAN": 1, "DEAD": 2, "": 3}
    started = lambda r: r["status"] == "game started"
    exmax = max([max(r["dep"].values() or [0]) for r in rows] + [1])
    nmax = max([r["new"] for r in rows] + [1])

    def plim(r):
        p = r.get("pl") or {}
        if not p.get("p_alert"):
            return '<span class="muted">—</span>'
        s = money(p["p_alert"])
        if p.get("p_now") and abs(p["p_now"] - p["p_alert"]) >= 0.05 * p["p_alert"]:
            s += f' <span class="muted">now {money(p["p_now"])}</span>'
        if p.get("x2"):
            s += ' <span class="pill yes" title="Exchange money on this side is at least 2x the P limit (2 of Novig/ProphetX/Kalshi at $5k+, $25k+ total)">2X</span>'
        return s

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
                f'<td class="r"><b>{e(str(r["x"].get("line")) if r["x"].get("line") not in (None, "") else "—")}</b></td>'
                f'<td class="r">{price_cell(r)}</td>'
                f'<td class="ex">{bars}</td>'
                f'<td class="r">{plim(r)}</td>'
                f'<td class="r">{(str(r["sit"] // 60) + "h " + str(r["sit"] % 60) + "m") if live and r["sit"] >= 60 else (str(r["sit"]) + "m" if live else "")}</td>'
                f'<td><span class="pill {"yes" if live else "gone"}">{r["status"]}</span></td>'
                f'<td class="hide-m"><span class="pill {"yes" if r["conf"] else ""}">{"yes" if r["conf"] else "no"}</span></td>'
                f'<td class="hide-m muted">{r["first"]}</td></tr>')
        head = ('<tr><th>Call</th><th class="r">New money</th><th class="hide-m">League</th><th>Game</th><th>Money on</th><th class="r" title="The alert line on the trigger book">Line</th>'
                '<th class="r" title="The alert price on the trigger book, and what it pays after that book\'s fee">Price</th><th>Bids by exchange</th><th class="r" title="Pinnacle limit on OddsJam scale: at the alert, and now">P limit</th><th class="r">Sitting</th><th>Status</th><th class="hide-m">Confirmed</th>'
                '<th class="hide-m">First seen ET</th></tr>')
        return f'<div class="scroll"><table><thead>{head}</thead><tbody>{"".join(out) or "<tr><td colspan=13 class=muted>Nothing yet today.</td></tr>"}</tbody></table></div>'

    fl = "".join(
        f'<tr data-league="{e(a["league"])}"><td>{e(a["game"])}</td><td>{mk}</td><td>{e(a["side"])}</td><td class="r">{money(a["new"])}</td>'
        f'<td class="muted">{a["at"].astimezone(ET).strftime("%-I:%M %p")}</td><td>{e(b["side"])}</td><td class="r">{money(b["new"])}</td>'
        f'<td class="muted">{b["at"].astimezone(ET).strftime("%-I:%M %p")}</td><td>{fav}</td></tr>' for a, b, mk, fav in flips)
    plays = [r for r in rows if r["tag"] == "PLAY"]
    # Nov 5: the graded record comes from the frozen call log, not from today's recomputed tags
    today = now.astimezone(ET).strftime("%Y-%m-%d")
    all_log = [e for e in CALLS_LOG.values() if e.get("call") == "PLAY"]
    today_log = [e for e in all_log if e.get("day") == today]
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
<h1>Bets Board</h1><p class="sub"><b>Last updated {stamp}</b> <span id="ago" data-t="{now.isoformat()}"></span> · <span id="ld"></span>. Rebuilds itself after every liquidity run; this page reloads every 5 minutes.</p>
<div class="tiles"><div class="tile"><div class="l">PLAY calls open now</div><div class="n">{sum(1 for r in plays if r["status"] == "still there")}</div></div>
<div class="tile"><div class="l">Big-money moves today</div><div class="n">{len(rows)}</div></div></div>
{plays_card(now, rows)}\n{live_plays_card()}
<div class="card"><h2>Big money today, by bet type</h2>
<p class="note"><b>Call (v3, from Nov 4):</b> PLAY = an NBA total alerted 4 hours or more before tip, money still there, one play per game total (the first alert; first side stays), at most 5 a night (first 5 by alert time). Bet the alert line at the alert price or better. LEAN = anything else still there, including later alerts on a game already played and NBA totals inside 4 hours. DEAD = pulled, flipped, late money, or any spread. Started games keep their kickoff call and grade W/L when final. The v2 call (NBA total, money still there, price not moved) keeps grading in its own tile. Paper signal. Every call is written down when it posts and never rewritten, so a PLAY whose money is pulled afterwards still grades as the PLAY it was.</p>
<div class="legend"><span><i class="sw kalshi"></i>Kalshi</span><span><i class="sw novig"></i>Novig</span><span><i class="sw prophetx"></i>ProphetX</span><span><i class="sw polymarket"></i>Polymarket</span></div>
<div class="filters"><button data-f="" class="on">All</button>{btns}<button data-f="live">PLAY + LEAN only</button></div>
<h3>Moneylines</h3>{table("moneyline")}<h3>Spreads</h3>{table("spread")}<h3>Totals</h3>{table("total")}</div>
<div class="card"><h2>Money flips today</h2><p class="note">$100k+ hit one side, then later $100k+ hit the other side. History: totals and NBA, the first money won 58%; spreads, the later money won 61%; moneylines, a coin flip.</p>
<div class="scroll"><table><thead><tr><th>Game</th><th>Bet type</th><th>First money on</th><th class="r">First $</th><th>Time</th><th>Later money on</th><th class="r">Later $</th><th>Time</th><th>History favors</th></tr></thead>
<tbody>{fl or "<tr><td colspan=9 class=muted>No flips today.</td></tr>"}</tbody></table></div></div>
</div><script>
(()=>{{const a=document.getElementById('ago'),l=document.getElementById('ld'),t=new Date(a.dataset.t),f=x=>x.toLocaleTimeString('en-US',{{hour:'numeric',minute:'2-digit'}});
l.textContent='page loaded '+f(new Date());const u=()=>{{const m=Math.round((Date.now()-t)/60000);a.textContent='('+(m<1?'just now':m+' min ago')+')';}};u();setInterval(u,30000);}})();
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{
document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('on',x===b));const f=b.dataset.f;
document.querySelectorAll('tbody tr[data-league]').forEach(tr=>{{tr.style.display=!f||(f==='live'?(tr.dataset.tag==='PLAY'||tr.dataset.tag==='LEAN'):tr.dataset.league===f)?'':'none';}});}});
</script></body></html>"""


def live_plays_card():
    """The bot's OWN board-lane plays, with the reason each one did or did not get placed.

    Peter, Nov 11: the board shows its PLAY calls, but not what the bot actually did with them -
    so a live play and a refused one looked identical from here. This reads the executor's own
    ledger rows (its "Bets LIVE" emails, source == "board") and shows the outcome and the WHY.

    The reason text is the executor's own, verbatim. It is not re-worded or summarised: when a play
    is refused, the exact sentence that refused it is the useful thing, and a paraphrase of it is
    how a reader comes to believe something slightly different from what happened.

    Degrades to a stated message rather than an empty card: no Gmail credentials, an IMAP failure
    or simply no board plays yet each print their own line, because a blank table and "nothing was
    placed" look the same and mean very different things.
    """
    import datetime as _d
    rows, err = [], None
    try:
        import executor as _ex
        import rest_depth_report as _rd
        since = (_d.datetime.now(_d.timezone.utc) - _d.timedelta(days=2)).strftime("%d-%b-%Y")
        M = _ex.imap_open()
        try:
            for subj in ('"Bets LIVE:"',):   # Nov 11 (Peter): live only, no paper (dry-run) rows
                got, _n = _rd.ledger_rows(M, subj, since)
                rows += got
        finally:
            try:
                M.logout()
            except Exception:
                pass
    except SystemExit as ex:
        # executor.gmail() raises SystemExit("Email not configured.") when the credentials are
        # missing, and `except Exception` does NOT catch that - so without this the whole board
        # build would exit here and the page would stop being rebuilt. A display card must never
        # be able to take down the board. Caught locally, with no credentials, before shipping.
        err = f"credentials: {str(ex)[:70]}"
    except BaseException as ex:            # IMAP can also raise KeyboardInterrupt-like socket aborts
        err = f"{type(ex).__name__}: {str(ex)[:70]}"

    _today = _d.datetime.now(ET).strftime("%Y-%m-%d")
    def _is_today(r):
        try:
            return _d.datetime.fromisoformat(str(r.get("decided_utc")).replace("Z", "+00:00")).astimezone(ET).strftime("%Y-%m-%d") == _today
        except Exception:
            return False
    board = [r for r in rows if _is_today(r)]   # Nov 11 (Peter): today's plays, every lane
    # one row per play, keeping the one that records a PLACEMENT over one that does not
    def _placed(r):
        los = [r.get("live_order") or {}, r.get("live_rest") or {}]
        los += [x or {} for x in (r.get("live_more") or [])]
        return any(l.get("status") == "placed" and l.get("order_id") for l in los)
    seen = {}
    for r in sorted(board, key=lambda r: str(r.get("decided_utc") or "")):
        k = r.get("key") or r.get("play_key")
        if not k:
            continue
        if k not in seen or (_placed(r) and not _placed(seen[k])):
            seen[k] = r
    board = sorted(seen.values(), key=lambda r: str(r.get("decided_utc") or ""), reverse=True)

    out = []
    for r in board[:40]:
        # Peter, Nov 11: a play that CAME and was not taken matters as much as one that was, so the
        # ways of not taking it are kept apart instead of collapsing into one label.
        #   PLACED   an order went in
        #   REFUSED  a safety gate fired at order time, after the play qualified
        #   SKIPPED  the executor never reached an order - usually the price was gone
        #   BLOCKED  it qualified but a lane or rule switch stopped it
        lo = r.get("live_order") or {}
        raw = str(lo.get("status") or "")
        if raw in ("placed", "refused"):
            st = raw
        elif str(r.get("verdict") or "").upper() == "SKIP":
            st = "skipped"
        elif r.get("live"):
            st = "would place"
        else:
            st = "blocked"
        why = (lo.get("reason")
               or "; ".join(str(x) for x in (r.get("live_why_not") or []))
               or r.get("reason") or "")
        cls = {"placed": "ok", "refused": "bad", "skipped": "muted",
               "blocked": "bad", "would place": "muted"}.get(st, "muted")
        key = str(r.get("key") or "").split("|")
        game = key[1] if len(key) > 3 else str(r.get("key") or "")
        side = f"{key[3]} {r.get('fill_line') if r.get('fill_line') is not None else ''}" if len(key) > 3 else ""
        px = r.get("fill_price_after_fee")
        try:
            t = _d.datetime.fromisoformat(str(r.get("decided_utc")).replace("Z", "+00:00")).astimezone(ET).strftime("%-I:%M %p")
        except Exception:
            t = str(r.get("decided_utc") or "")[11:16]
        try:
            lane = _ex.LANE_NAME.get(_ex.lane_of(r), str(r.get("source") or "").upper())
        except Exception:
            lane = str(r.get("source") or "").upper()
        out.append(
            f'<tr><td class=muted>{t}</td><td>{lane}</td><td>{game}</td><td>{side}</td>'
            f'<td>{r.get("fill_book") or ""}</td>'
            f'<td class=r>{(f"{px:+d}" if isinstance(px, int) else "")}</td>'
            f'<td class="{cls}">{st.upper()}</td><td class=muted>{why}</td></tr>')

    if err:
        body = f'<tr><td colspan=8 class=muted>Ledger unreadable ({err}) - this card cannot say what the bot did.</td></tr>'
    elif not board:
        body = '<tr><td colspan=8 class=muted>No bot plays today yet.</td></tr>'
    else:
        body = "".join(out)
    return ('<div class="card"><h2>Today&#39;s plays - what the bot did</h2>'
            '<p class="note">Every lane (Phase 1, Board v3, R1), today ET, newest first, from the executor ledger. Live orders only, no paper. '
            'PLACED = an order went in. REFUSED = a gate fired at order time. SKIPPED = never reached an '
            'order, usually the price was gone. BLOCKED = qualified but a switch stopped it. Every reason is '
            'the executor\'s own words, not a summary. A quote is not a fill.</p>'
            '<div class="scroll"><table><thead><tr><th>ET</th><th>Lane</th><th>Game</th><th>Bet</th><th>Book</th>'
            '<th class=r>Price</th><th>Outcome</th><th>Why</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div></div>')


def main():
    now, rows, flips = build()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(page(now, rows, flips))
    print(f"Bets board: {len(rows)} rows, {sum(r['tag'] == 'PLAY' for r in rows)} PLAY, {len(flips)} flips; "
          f"frozen calls {len(CALLS_LOG)}, frozen PLAY {sum(1 for e in CALLS_LOG.values() if e.get('call') == 'PLAY')}")   # counts only


if __name__ == "__main__":
    main()

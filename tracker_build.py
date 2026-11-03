#!/usr/bin/env python3
"""
Bet Tracker, PRIVATE (Nov 1, 2026; Peter: "I want it private"). Built in GitHub Actions next to the Bets Board and
published at faros4life.github.io/sharp-monitor/tracker/, but EVERYTHING on the page is encrypted (AES-GCM, key from
PBKDF2 of the TRACKER_PASSPHRASE secret). The browser decrypts it after Peter types the passphrase once; anyone else
sees a locked box. The persisted bet history (tracker/state.enc) is encrypted the same way. Public log: counts only.

What it shows (Muse's spec, VALUE LAB Nov 1):
  tiles: settled profit Today / This week (Mon-Sun) / This month, ET, from the books' own settled numbers
         (ProphetX trades, Kalshi settlements, Polymarket US settlement activities); Novig settled = graded from finals
         until the home runner sends Novig's own numbers (marked "graded").
  LIVE: open bets on started games with score, period, clock and a COVERING / BEHIND / HOLDING read.
  UPCOMING: open bets on games not started.  SETTLED: this week's settled bets with signed profit.
Every bet: book, bet, stake, to pay, source (bot when it matches the executor's own ledger, else Peter).
Not on the page: balances, bankroll, Street Value card, pool picks, executor internals.
"""
import base64
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STATE = "tracker/state.enc"
OUT = os.environ.get("TRACKER_OUT", "site/tracker")
PASS = (os.environ.get("TRACKER_PASSPHRASE") or "").encode()
ITER = 250_000
LOG = {}   # source -> "ok n" / "failed" (counts only)


# ------------------------------------------------------------------ crypto (same format as the page's WebCrypto)
def _key(salt):
    return hashlib.pbkdf2_hmac("sha256", PASS, salt, ITER, 32)


def enc(obj):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(salt)).encrypt(iv, json.dumps(obj, separators=(",", ":")).encode(), None)
    return {"s": base64.b64encode(salt).decode(), "i": base64.b64encode(iv).decode(), "c": base64.b64encode(ct).decode(), "n": ITER}


def dec(blob):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv, ct = (base64.b64decode(blob[k]) for k in ("s", "i", "c"))
    return json.loads(AESGCM(_key(salt)).decrypt(iv, ct, None))


# ------------------------------------------------------------------ helpers
def num(x):
    if isinstance(x, dict):
        x = x.get("value")
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def tparse(t):
    if t in (None, ""):
        return None
    try:
        if isinstance(t, (int, float)) or str(t).isdigit():
            t = float(t)
            return datetime.fromtimestamp(t / 1000 if t > 1e11 else t, timezone.utc)
        return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except Exception:
        return None


def american_to_p(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def p_to_american(p):
    if not p or not 0 < p < 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


WORDS = re.compile(r"[a-z0-9]+")
STOP = {"at", "vs", "v", "the", "fc", "game", "points", "point", "goals", "wins", "by", "over", "under", "not", "total",
        "full", "scored", "spread", "moneyline", "ml", "and", "of"}


def toks(s):
    return {w for w in WORDS.findall((s or "").lower()) if w not in STOP and not w.replace(".", "").isdigit() and len(w) > 1}


# ------------------------------------------------------------------ bet text -> what has to happen
def parse_bet(text, flip=False):
    """('total', 'OVER'|'UNDER', line) | ('spread', team_text, line) | ('ml', team_text, None) | None.
    Handles book wording: 'Under 43.5', 'Celtics -5.5 (-130)', 'Boston wins by over 5.5 points', 'NOT Over 42.5 points',
    'Phoenix wins', 'Celtics ML'. flip=True means the held side is the NO / short side."""
    s = re.sub(r"\(\s*[+-]?\d+\s*\)", "", text or "").strip()
    neg = flip
    if s.upper().startswith("NOT "):
        neg, s = not neg, s[4:]
    m = re.search(r"\b(over|under)\s+(\d+(?:\.\d+)?)", s, re.I)
    if m and not re.search(r"wins by", s, re.I):
        side = m.group(1).upper()
        if neg:
            side = "UNDER" if side == "OVER" else "OVER"
        return ("total", side, float(m.group(2)))
    m = re.search(r"^(.*?)\s+wins by (?:over|more than)\s+(\d+(?:\.\d+)?)", s, re.I)
    if m:   # Kalshi spread: YES = team covers -line; NO = the other team +line
        return ("spread", m.group(1).strip(), -float(m.group(2)), neg)
    m = re.search(r"^(.*?)\s+([+-]\d+(?:\.\d+)?)\s*$", s)
    if m:
        return ("spread", m.group(1).strip(), float(m.group(2)), neg)
    m = re.search(r"^(.*?)(?:\s+wins|\s+ml|\s+moneyline)?\s*$", s, re.I)
    if m and m.group(1).strip():
        return ("ml", m.group(1).strip(), None, neg)
    return None


# ------------------------------------------------------------------ ESPN scores
LEAGUES = {"NFL": "football/nfl", "NCAAF": "football/college-football", "NBA": "basketball/nba", "NHL": "hockey/nhl",
           "MLB": "baseball/mlb", "NCAAB": "basketball/mens-college-basketball", "WNBA": "basketball/wnba"}


def _espn_get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def espn_games(days):
    from concurrent.futures import ThreadPoolExecutor
    jobs = []
    for lg, path in LEAGUES.items():
        for d in days:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={d.strftime('%Y%m%d')}&limit=400"
            if lg == "NCAAF":
                url += "&groups=80"
            jobs.append((lg, url))
    with ThreadPoolExecutor(max_workers=8) as pool:   # Nov 2 (Peter: tracker too slow): fetch the scoreboards in parallel
        got = list(pool.map(lambda j: _espn_get(j[1]), jobs))
    games = []
    for (lg, url), data in zip(jobs, got):
        if True:
            if data is None:
                continue
            for ev in data.get("events") or []:
                comp = (ev.get("competitions") or [{}])[0]
                teams = []
                for c in comp.get("competitors") or []:
                    t = c.get("team") or {}
                    names = " ".join(str(t.get(k) or "") for k in ("displayName", "shortDisplayName", "name", "location", "abbreviation"))
                    teams.append({"home": c.get("homeAway") == "home", "names": names, "toks": toks(names),
                                  "abbr": (t.get("abbreviation") or "").lower(), "score": num(c.get("score")) or 0,
                                  "short": t.get("shortDisplayName") or t.get("displayName") or "",
                                  "full": t.get("displayName") or t.get("shortDisplayName") or ""})
                st = (ev.get("status") or {}).get("type") or {}
                games.append({"league": lg, "id": ev.get("id"), "start": ev.get("date"), "teams": teams,
                              "state": st.get("state"), "detail": st.get("shortDetail") or st.get("detail") or "",
                              "final": bool(st.get("completed")), "period": (ev.get("status") or {}).get("period"),
                              "clock": (ev.get("status") or {}).get("displayClock")})
    LOG["espn"] = f"ok {len(games)}"
    return games


def match_game(bet, games, near=None):
    """near: a datetime the game must start within 36 h of (settled bets: their settle time), so an old bet is never
    pinned to this week's game between the same teams."""
    bt = toks(bet.get("game")) | toks(bet.get("bet"))
    best, score = None, 0
    for g in games:
        if bet.get("league") and bet["league"] != g["league"]:
            continue
        if near is not None:
            gs = tparse(g.get("start"))
            if not gs or abs((gs - near).total_seconds()) > 36 * 3600:
                continue
        hits = sum(1 for t in g["teams"] if (t["toks"] & bt) or (t["abbr"] and t["abbr"] in bt))
        if hits > score or (hits == score and best and g["start"] and bet.get("date") and g["start"][:10] == bet["date"]):
            best, score = g, hits
    return best if score >= 2 or (score == 1 and bet.get("league")) else None


def team_of(text, g):
    tt = toks(text)
    for t in g["teams"]:
        if t["toks"] & tt or (t["abbr"] and t["abbr"] in tt):
            return t
    return None


def read_status(bet, g):
    """(status text, outcome if final: W/L/P/None)."""
    pb = parse_bet(bet.get("bet"), bet.get("flip"))
    if not g or not pb or len(g["teams"]) != 2:
        return ("", None)
    a, b = g["teams"]
    tot = a["score"] + b["score"]
    if pb[0] == "total":
        side, line = pb[1], pb[2]
        if g["final"]:
            return (f"final {int(tot)}", "P" if tot == line else ("W" if (tot > line) == (side == "OVER") else "L"))
        proj = None
        frac = elapsed(g)
        if frac and frac > 0.05:
            proj = tot / frac
        hold = None if proj is None else ((proj > line) == (side == "OVER"))
        txt = f"{int(tot)} now" + (f", pace {proj:.0f} vs {line:g}" if proj else "")
        return (txt + ("" if hold is None else (" HOLDING" if hold else " NOT HOLDING")), None)
    t = team_of(pb[1], g)
    if not t:
        return ("", None)
    o = b if t is a else a
    neg = pb[3]
    if pb[0] == "spread":
        line = pb[2]
        if neg:   # NO on "team -x" = the other team +x
            t, o, line = o, t, -line
        cushion = t["score"] + line - o["score"]
        if g["final"]:
            return (f"final {int(t['score'])}-{int(o['score'])}", "P" if cushion == 0 else ("W" if cushion > 0 else "L"))
        return (f"{'COVERING' if cushion > 0 else 'BEHIND' if cushion < 0 else 'PUSH'} by {abs(cushion):g}", None)
    if neg:
        t, o = o, t
    lead = t["score"] - o["score"]
    if g["final"]:
        return (f"final {int(t['score'])}-{int(o['score'])}", "P" if lead == 0 else ("W" if lead > 0 else "L"))
    return (("WINNING" if lead > 0 else "LOSING" if lead < 0 else "TIED") + (f" by {abs(lead):g}" if lead else ""), None)


def elapsed(g):
    """Share of regulation played (for total pace)."""
    per = {"NFL": (4, 15), "NCAAF": (4, 15), "NBA": (4, 12), "WNBA": (4, 10), "NCAAB": (2, 20), "NHL": (3, 20), "MLB": (9, None)}
    n, mins = per.get(g["league"], (4, 12))
    p = g.get("period") or 0
    if not p or g["state"] != "in":
        return None
    if mins is None:
        return min(1.0, (p - 0.5) / n)
    c = str(g.get("clock") or "").strip()   # Nov 2: ESPN shows "0.0" at breaks and "45.3" in the last minute
    m = re.match(r"(\d+):(\d+(?:\.\d+)?)$", c)
    if m:
        left = int(m.group(1)) + float(m.group(2)) / 60
    elif re.match(r"\d+(?:\.\d+)?$", c):
        left = float(c) / 60
    else:
        left = mins / 2
    if re.match(r"(halftime|end of|end )", str(g.get("detail") or "").strip(), re.I):
        left = 0   # quarter / period break: the period is fully played
    left = max(0.0, min(float(mins), left))
    return min(1.0, ((min(p, n) - 1) * mins + (mins - left)) / (n * mins))


def attach(b, g):
    """Scoreboard fields for the card: league, both teams (away first) with scores, game state and clock."""
    if not g or len(g["teams"]) != 2:
        return
    a, h = sorted(g["teams"], key=lambda t: t["home"])
    b["league"] = b.get("league") or g["league"]
    b["teams"] = [{"name": a["full"], "score": int(a["score"])}, {"name": h["full"], "score": int(h["score"])}]
    b["g_state"], b["g_detail"] = g["state"], g["detail"]
    b["game_start"] = b.get("game_start") or g["start"]
    if g["final"]:
        b["teams_final"] = True


def score_line(g):
    if not g or len(g["teams"]) != 2:
        return ""
    a, b = sorted(g["teams"], key=lambda t: t["home"])
    sc = f"{a['short']} {int(a['score'])}, {b['short']} {int(b['score'])}"
    return sc + (f" · {g['detail']}" if g["state"] in ("in", "post") else "")


# ------------------------------------------------------------------ book reads (read-only)
def read_prophetx():
    """(open bets, settled bets) from ProphetX trades (trading key)."""
    import px_live
    import positions as ps
    if not px_live.login():
        LOG["prophetx"] = "failed (login)"
        return [], []
    names = {}
    try:
        for h in ps.px_positions() or []:
            names[str(h.get("strike_id") or "")] = h
    except Exception:
        pass
    op, se = [], []
    for t in px_live.trades():
        st = str(t.get("winning_status") or "").lower()
        stake = px_live.stake_of(t)
        pr = int(t.get("price") or 0)
        win = stake * 100 / abs(pr) if pr < 0 else stake * pr / 100
        h = names.get(str(t.get("strike_id")))
        title = str(t.get("line_name") or t.get("selection") or "")
        b = {"id": f"px|{t.get('id')}", "book": "ProphetX", "game": (h or {}).get("game") or str(t.get("event_name") or ""),
             "bet": (h or {}).get("label") or title, "price": pr, "stake": round(stake, 2),
             "to_pay": round(stake + win * 0.98, 2), "date": (h or {}).get("date"), "placed": str(t.get("created_at") or "")}
        when = None
        for k in ("settled_at", "settle_time", "settled_time", "updated_at", "update_time", "matched_at", "created_at"):
            when = tparse(t.get(k))
            if when:
                break
        if st in ("profit", "win", "won"):
            se.append({**b, "result": "W", "profit": round(abs(float(t.get("profit") or 0)) * 0.98, 2), "settled": iso(when), "site": True})
        elif st in ("loss", "lose", "lost"):
            se.append({**b, "result": "L", "profit": -round(stake, 2), "settled": iso(when), "site": True})
        elif st in ("push", "void", "refund", "cancel", "cancelled"):
            se.append({**b, "result": "P", "profit": 0.0, "settled": iso(when), "site": True})
        else:
            op.append(b)
    LOG["prophetx"] = f"ok {len(op)} open {len(se)} settled"
    return op, se


def k_name(tk):
    """KXNBAGAME-26OCT30DENPHX-PHX -> 'NBA DEN @ PHX (Oct 30)'."""
    m = re.match(r"KX([A-Z]+?)(GAME|SPREAD|TOTAL)-(\d\d)([A-Z]{3})(\d\d)([A-Z]+?)-", tk or "")
    if not m:
        return tk or ""
    teams = m.group(6)
    a, b = (teams[:len(teams) // 2], teams[len(teams) // 2:]) if len(teams) in (4, 6) else (teams, "")
    return f"{m.group(1)} {a} @ {b} ({m.group(4).title()} {int(m.group(5))})".replace(" @ ", " @ " if b else "")


def k_bet(tk, res):
    m = re.match(r"KX[A-Z]+?(GAME|SPREAD|TOTAL)-[^-]+-(.+)$", tk or "")
    if not m:
        return tk or ""
    kind, tail = m.group(1), m.group(2)
    if kind == "TOTAL":
        return f"Total {tail}"
    if kind == "SPREAD":
        mm = re.match(r"([A-Z]+)(\d+)", tail)
        return f"{mm.group(1)} -{int(mm.group(2)) - 0.5:g}" if mm else tail
    return f"{tail} ML"


def lg_of(text):
    t = (text or "").upper()
    for k, v in (("NCAAF", "NCAAF"), ("NCAAMB", "NCAAB"), ("NCAAB", "NCAAB"), ("WNBA", "WNBA"), ("NBA", "NBA"), ("NFL", "NFL"),
                 ("NHL", "NHL"), ("MLB", "MLB"), ("CFB", "NCAAF")):
        if k in t:
            return v
    return None


def iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def read_kalshi(since):
    import positions as ps
    op, se = [], []
    cur = None
    for _ in range(5):
        d = ps._kalshi_get("/portfolio/positions", {"limit": 200, "count_filter": "position", **({"cursor": cur} if cur else {})})
        for p in d.get("market_positions") or []:
            q = num(p.get("position_fp")) if p.get("position_fp") is not None else num(p.get("position"))
            if not q:
                continue
            tk = p.get("ticker") or ""
            cost = num(p.get("market_exposure_dollars"))
            if cost is None:
                cost = (num(p.get("market_exposure")) or 0) / 100
            mk = (ps.lm.get(f"{ps.K_API}/markets/{tk}") or {}).get("market") or {}
            et = mk.get("event_ticker") or tk.rsplit("-", 1)[0]
            try:
                title = ((ps.lm.get(f"{ps.K_API}/events/{et}") or {}).get("event") or {}).get("title") or ""
            except Exception:
                title = ""
            label = mk.get("yes_sub_title") or mk.get("subtitle") or mk.get("title") or tk
            pr = (cost / abs(q)) if q else None
            op.append({"id": f"ks|{tk}|{'no' if q < 0 else 'yes'}", "book": "Kalshi", "game": title, "league": lg_of(tk),
                       "bet": ("NOT " if q < 0 else "") + label, "flip": False, "stake": round(cost, 2),
                       "to_pay": round(abs(q), 2), "price": p_to_american(pr), "date": ps._date(tk), "ticker": tk})
        cur = d.get("cursor")
        if not cur:
            break
    items, cur = [], None
    for _ in range(20):
        prm = {"limit": 200, "min_ts": int(since.timestamp())}
        if cur:
            prm["cursor"] = cur
        d = ps._kalshi_get("/portfolio/settlements", prm)
        items += d.get("settlements") or []
        cur = d.get("cursor")
        if not cur:
            break
    for s in items:
        def dollars(k):
            v = num(s.get(k + "_dollars"))
            if v is not None:
                return v
            v = num(s.get(k))
            return v / 100 if v is not None else 0.0
        rev, cost, fee = dollars("revenue"), dollars("yes_total_cost") + dollars("no_total_cost"), num(s.get("fee_cost")) or 0.0
        p = rev - cost - fee
        se.append({"id": f"ks|{s.get('ticker')}|settled", "book": "Kalshi", "game": k_name(s.get("ticker")),
                   "bet": k_bet(s.get("ticker"), s.get("market_result")),
                   "stake": round(cost, 2), "to_pay": round(rev, 2), "result": "W" if p > 0 else "L" if p < 0 else "P",
                   "profit": round(p, 2), "settled": iso(tparse(s.get("settled_time"))), "site": True, "ticker": s.get("ticker")})
    LOG["kalshi"] = f"ok {len(op)} open {len(se)} settled"
    return op, se


def read_pmus(since):
    import pmus_activity as pa
    import positions as ps
    op, se = [], []
    d = pa.signed_get("/v1/portfolio/positions")
    items = []

    def walk(x, slug=None):
        if isinstance(x, dict):
            if isinstance(x.get("marketMetadata"), dict):
                items.append((x, slug))
                return
            for k, v in x.items():
                walk(v, k if isinstance(v, dict) else slug)
        elif isinstance(x, list):
            for v in x:
                walk(v, slug)
    walk(d)
    for p, slug in items:
        md = p["marketMetadata"]
        q = None
        for k in ("netPosition", "netPositionDecimal", "position", "qtyDecimal", "qty", "quantity"):
            if num(p.get(k)) is not None:
                q = num(p.get(k))
                break
        if not q:
            continue
        cost = num(p.get("cost")) or (abs(q) * (num(p.get("avgPx")) or 0))
        op.append({"id": f"pm|{md.get('slug') or slug}|{md.get('outcome')}", "book": "Polymarket US", "game": md.get("title") or "",
                   "league": lg_of((md.get("eventSlug") or md.get("slug") or slug or "").split("-")[0]),
                   "bet": md.get("outcome") or "", "flip": q < 0, "stake": round(cost, 2), "to_pay": round(abs(q), 2),
                   "price": p_to_american(cost / abs(q)) if cost else None, "date": ps._date(md.get("eventSlug") or md.get("slug") or slug)})
    acts, params = [], {"limit": 100}
    for _ in range(30):
        dd = pa.signed_get("/v1/portfolio/activities", params)
        got = pa.items_of(dd)
        acts += got
        nc = pa.next_cursor(dd)
        oldest = min((pa.when(a) for a in got if pa.when(a)), default=None)
        if not got or not nc or (oldest and oldest < since):
            break
        params = {"limit": 100, nc[0] if nc[0] != "next" else "cursor": nc[1]}
    for a in acts:
        r = pa.row(a)
        if r["type"] != "SETTLEMENT" or r["pnl"] is None or not r["time_et"]:
            continue
        t = datetime.strptime(r["time_et"], "%Y-%m-%d %H:%M").replace(tzinfo=ET)
        if t < since:
            continue
        se.append({"id": f"pm|{r['market']}|{r['outcome']}|settled", "book": "Polymarket US", "game": r["market"].split(" [")[0],
                   "bet": r["outcome"], "stake": round(r["cost"] or 0, 2), "to_pay": round(r["amount"] or 0, 2),
                   "result": "W" if r["pnl"] > 0 else "L" if r["pnl"] < 0 else "P", "profit": r["pnl"],
                   "settled": iso(t), "site": True})
    LOG["polymarket_us"] = f"ok {len(op)} open {len(se)} settled"
    return op, se


def read_novig():
    import executor as ex
    import liquidity_monitor as lm
    import book_check as bc
    tok = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
    snap, age = ex._snap_read(tok)
    if age > 12:   # Nov 2: GitHub runs the home PC's 5-min schedule hours late -> ask for a fresh snapshot now (read-only)
        try:
            ex._snap_refresh(tok)   # not waited on: the next board run (minutes away) reads the fresh one
        except Exception:
            pass
    op = []
    pos = snap.get("positions") or []
    ev_by, mk_by = {}, {}
    if pos:
        try:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            evs, mks = bc.novig_catalog(now_ms - 12 * 3600 * 1000, now_ms + 9 * 86400 * 1000)
            ev_by = {e.get("eventId"): e for e in evs}
            mk_by = {m.get("marketId"): m for m in mks}
        except Exception:
            pass
    for p in pos:
        qty = (num(p.get("qty")) or 0) / 100   # Novig qty = payout in cents (qty 40000 = $400 to pay)
        cost = num(p.get("cost")) or 0
        game, side, league, start = "", "", None, None
        try:
            mk = mk_by.get(p.get("marketId")) or lm.get(f"{lm.NOVIG}/v3/public/catalog/markets/{p.get('marketId')}")
            side = next((o.get("name") for o in mk.get("outcomes") or [] if o.get("outcomeId") == p.get("outcomeId")), "") or ""
            ev = ev_by.get(mk.get("eventId")) or {}
            game = ev.get("description") or mk.get("description") or mk.get("title") or ""
            league = lm.N_LEAGUE.get((ev.get("league") or "").upper().strip())
            start = ev.get("startTime") or ev.get("start_time") or ev.get("scheduledStart")
            mt = bc.N_MKT.get((mk.get("marketType") or "").upper())
            if mt == "total" and side and not re.search(r"\d", side):
                strike = num(mk.get("strike"))
                side = f"{side} {strike:g}" if strike is not None else side
            elif mt == "spread" and side and not re.search(r"[+-]\d", side):
                strike = num(mk.get("strike"))
                idx = next((i for i, o in enumerate(mk.get("outcomes") or []) if o.get("outcomeId") == p.get("outcomeId")), 0)
                if strike is not None:
                    side = f"{side} {(strike if idx == 1 else -strike):+g}"
        except Exception:
            pass
        op.append({"id": f"nv|{p.get('marketId')}|{p.get('outcomeId')}", "book": "Novig", "game": game, "bet": side,
                   "league": league, "source": "bot" if p.get("wallet") == "sub" else None,
                   "stake": round(cost, 2), "to_pay": round(qty, 2), "price": p_to_american(cost / qty) if qty and cost else None})
    se = []
    for r in snap.get("settled") or []:   # Nov 1: Novig's own settled numbers, written by the home PC
        res = {"WIN": "W", "LOSS": "L", "PUSH": "P"}.get(r.get("result"))
        if not res:
            continue
        cost, pay = num(r.get("cost")) or 0, num(r.get("payout")) or 0
        qty = (num(r.get("qty")) or 0) / 100   # Nov 2: Novig qty = payout in cents if it won (known for losses too)
        tp_ = pay if res != "L" else (qty or None)
        st = r.get("start")
        if isinstance(st, (int, float)) or str(st or "").isdigit():
            st = iso(tparse(st))
        se.append({"id": f"nv|{r.get('marketId')}|{r.get('outcomeId')}", "book": "Novig", "game": r.get("game") or "",
                   "bet": r.get("label") or "", "league": lm.N_LEAGUE.get(str(r.get("league") or "").upper().strip()),
                   "source": "bot" if r.get("wallet") == "sub" else None,   # main wallet: the bot ledger decides
                   "stake": round(cost, 2), "to_pay": round(tp_, 2) if tp_ else None,
                   "price": p_to_american(cost / tp_) if tp_ and cost and res in ("W", "L") else None, "result": res,
                   "profit": round(num(r.get("pnl")) if num(r.get("pnl")) is not None else pay - cost, 2),
                   "settled": iso(tparse(r.get("settledTs"))), "game_start": st, "site": True})
    LOG["novig"] = f"ok {len(op)} open {len(se)} settled (snapshot {age:.0f} min old)"
    return op, se


IMAP_CACHE = {"v": None, "b": {}, "m": {}}   # Nov 2: parsed emails by Gmail UID, kept in the encrypted state (fetch each once)
IMAP_T = {}   # seconds per IMAP step (log only)


def _uidvalidity(M):
    try:
        r = M.response("UIDVALIDITY")[1]
        return r[0].decode() if r and r[0] else None
    except Exception:
        return None


def bot_keys(M, days=2):
    """The bot's own bet keys (rows with a placed order) from its 'Bets LIVE:' emails - for tagging sources only.
    Uses Gmail's indexed search (X-GM-RAW); the executor's IMAP SUBJECT scan of All Mail took ~6 minutes per build."""
    import email
    import email.header
    import executor as ex
    import time as _t
    keys = set()
    t0 = _t.time()
    uids = ex.gsearch(M, f'subject:(Bets LIVE) newer_than:{days}d')
    IMAP_T["bot search"] = round(_t.time() - t0)
    t0, n = _t.time(), 0
    for uid in uids:
        u = uid.decode() if isinstance(uid, bytes) else str(uid)
        if u in IMAP_CACHE["b"]:
            keys |= set(IMAP_CACHE["b"][u])
            continue
        n += 1
        got = set()
        typ, d = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not d or not d[0]:
            continue
        raw = d[0][1]
        subj = str(email.header.make_header(email.header.decode_header(email.message_from_bytes(raw).get("Subject") or "")))
        if not subj.startswith("Bets LIVE:"):
            continue
        txt = ex.body_text(raw)
        i = txt.rfind("LEDGER (machine-readable")
        if i >= 0:
            try:
                rows, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
            except Exception:
                rows = None
            if rows is None:
                continue   # unreadable ledger: not cached, retried next build
            for row in rows:
                los = [row.get("live_order") or {}, row.get("live_rest") or {}] + [x or {} for x in (row.get("live_more") or [])]
                if row.get("key") and any(lo.get("status") == "placed" and lo.get("order_id") for lo in los):
                    got.add(row["key"])
        IMAP_CACHE["b"][u] = sorted(got)
        keys |= got
    IMAP_T[f"bot fetch ({n} new of {len(uids)})"] = round(_t.time() - t0)
    return keys


def read_manual_and_bot():
    """Peter's 'Bets manual' notes (Hard Rock etc.) + the bot's own live keys (to tag sources)."""
    import executor as ex
    import time as _t
    man, keys = [], set()
    t0 = _t.time()
    M = ex.imap_open()
    IMAP_T["login+select"] = round(_t.time() - t0)
    v = _uidvalidity(M)
    if v and IMAP_CACHE.get("v") != v:   # mailbox UIDs renumbered: drop the cache
        IMAP_CACHE.update({"v": v, "b": {}, "m": {}})
    try:
        keys = bot_keys(M, days=2)   # Nov 2 (Peter: tracker too slow): indexed Gmail search, not a 6-minute IMAP scan;
        # older bot bets keep their stored 'bot' tag (see prev source below)
        t0 = _t.time()
        for uid in ex.gsearch(M, 'subject:"Bets manual" newer_than:10d'):
            u = uid.decode() if isinstance(uid, bytes) else str(uid)
            if u not in IMAP_CACHE["m"]:
                typ, data = M.uid("FETCH", uid, "(RFC822)")
                if typ != "OK" or not data or not data[0]:
                    continue
                IMAP_CACHE["m"][u] = [ln for ln in ex.body_text(data[0][1]).splitlines() if "MANUAL:" in ln]
            for line in IMAP_CACHE["m"][u]:
                m = re.match(r"\s*MANUAL:\s*(\{.*\})\s*$", line)
                if not m:
                    continue
                try:
                    d = json.loads(m.group(1))
                except Exception:
                    continue
                mp = re.search(r"\(([+-]\d+)\)", d.get("bet") or "")
                pr = int(mp.group(1)) if mp else None
                stake = num(d.get("stake"))
                est = False
                if not stake and pr:   # Peter's sizing (Oct 20): minus price risks to win $200, plus price risks $200
                    stake, est = (round(200 * abs(pr) / 100, 2) if pr < 0 else 200.0), True
                win = (stake * 100 / abs(pr) if pr and pr < 0 else stake * pr / 100 if pr else None) if stake else None
                man.append({"id": "mn|" + hashlib.sha1(line.strip().encode()).hexdigest()[:12], "book": d.get("book") or "manual",
                            "game": d.get("game") or "", "bet": d.get("bet") or "", "league": (d.get("sport") or "").upper() or None,
                            "price": pr, "stake": stake, "to_pay": round(stake + win, 2) if win else None,
                            "source": "Peter (Hard Rock note" + (", est. stake)" if est else ")")})
        IMAP_T["manual"] = round(_t.time() - t0)
    finally:
        M.logout()
    LOG["manual"] = f"ok {len(man)}"
    LOG["bot_keys"] = f"ok {len(keys)}"
    return man, keys


# Peter, Nov 2 (via Muse): ntfy alerts he played by hand while testing them count in the ntfy stream, not his own record.
RECLASS = [("2026-10-25", {"bengals", "cincinnati"}), ("2026-10-23", {"mavericks", "pacers", "mavs"}),
           ("2026-10-23", {"clippers"}, "Hard Rock"), ("2026-10-24", {"heat"}), ("2026-10-28", {"rays", "tb"}),
           ("2026-10-28", {"magic", "orlando"}, "Hard Rock")]   # the Clippers and Magic items are Hard Rock add-ons only


def reclass(b):
    t0 = tparse(b.get("game_start")) or tparse(b.get("settled"))
    if not t0:
        return False
    d = t0.astimezone(ET).strftime("%Y-%m-%d")
    words = set(WORDS.findall(f"{b.get('game')} {b.get('bet')}".lower()))
    return any(d == r[0] and (r[1] & words) and (len(r) < 3 or b.get("book") == r[2]) for r in RECLASS)


def bot_match(b, keys):
    pb = parse_bet(b.get("bet"), b.get("flip"))
    bw = (b.get("bet") or "").strip().upper()
    if not pb and bw in ("UNDER", "OVER", "NOT UNDER", "NOT OVER"):   # PM US labels a total side without its number
        side = bw.split()[-1]
        if bw.startswith("NOT "):
            side = "UNDER" if side == "OVER" else "OVER"
        pb = ("total", side, None)
    bt = toks(b.get("game"))
    bare = bool(re.fullmatch(r"\s*[+-]\d+(?:\.\d+)?\s*", b.get("bet") or ""))   # Nov 2: PM US labels a spread by its number only ("-3.50")
    for k in keys:
        sp, game, market, side = (k.split("|") + [None] * 4)[:4]
        if not game or len(toks(game) & bt) < 2 and not (toks(game) & toks(b.get("bet"))):
            continue
        if bare and market == "side" and len(toks(game) & bt) >= 2:
            return True
        if pb and pb[0] == "total" and market == "total" and side == pb[1]:
            return True
        if pb and pb[0] in ("spread", "ml") and market == "side" and (toks(side) & toks(pb[1])):
            return True
    return False


# ------------------------------------------------------------------ page
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#121614"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>Bet Tracker</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0f1311;--card:#171c1a;--line:#2a312e;--fg:#eef1ef;--muted:#8b958f;--win:#4ade80;--loss:#f87171;--winbg:#14301f;--lossbg:#3a1a1a;--live:#f87171}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 Inter,-apple-system,system-ui,sans-serif}
.wrap{max-width:560px;margin:0 auto;padding:16px 16px 40px}.cond{font-family:Oswald,Impact,sans-serif;text-transform:uppercase;letter-spacing:.02em}
h1{font:600 26px Oswald,sans-serif;margin:4px 0 2px;text-transform:uppercase}.sub{color:var(--muted);font-size:12px;margin:0 0 14px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:18px}.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;min-width:0}
.tile .l{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}.tile .n{font:600 clamp(16px,5vw,24px) Oswald,sans-serif;margin-top:2px;white-space:nowrap}
h2{font:600 22px Oswald,sans-serif;text-transform:uppercase;margin:22px 0 10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px 16px;margin-bottom:12px}
.card.win{border-color:var(--win);box-shadow:inset 5px 0 0 var(--win)}.card.loss{border-color:var(--loss);box-shadow:inset 5px 0 0 var(--loss)}
.hdr{display:flex;justify-content:space-between;gap:8px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
.hdr .s.win{color:var(--win)}.hdr .s.loss{color:var(--loss)}.hdr .s.live{color:var(--live)}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--live);margin-right:5px;vertical-align:1px}
.banner{display:flex;justify-content:space-between;align-items:center;border-radius:10px;padding:8px 12px;margin-top:10px;font:600 22px Oswald,sans-serif;text-transform:uppercase}
.banner.win{background:var(--winbg);color:var(--win)}.banner.loss{background:var(--lossbg);color:var(--loss)}.banner.push{background:#222;color:var(--muted)}
.banner .c{display:inline-block;width:14px;height:14px;border-radius:50%;background:currentColor;margin-right:8px}
.team{display:flex;justify-content:space-between;align-items:baseline;margin-top:8px;font:500 20px Oswald,sans-serif;text-transform:uppercase}
.team b{font:600 28px Oswald,sans-serif}.team.lead{color:var(--fg)}.team.trail{color:#cfd6d2}
hr{border:0;border-top:1px solid var(--line);margin:12px 0 10px}
.betl{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}.betl .b{font:600 24px Oswald,sans-serif;text-transform:uppercase}
.betl .p{font:500 18px Oswald,sans-serif}.betl .m{color:var(--muted)}.betl .bk{color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:600}
.pill{display:inline-block;margin-top:8px;border-radius:8px;padding:4px 10px;font:600 15px Oswald,sans-serif;text-transform:uppercase;letter-spacing:.04em}
.pill.win{background:var(--winbg);color:var(--win)}.pill.loss{background:var(--lossbg);color:var(--loss)}.pill.neu{background:#232a27;color:var(--muted)}
.note{color:var(--muted);font-size:13px;margin-top:8px}
.lock{max-width:340px;margin:22vh auto;text-align:center}.lock input{font:inherit;padding:12px;width:100%;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg)}
.lock button{margin-top:10px;font:600 16px Oswald,sans-serif;text-transform:uppercase;padding:12px;border-radius:10px;border:0;background:var(--win);color:#08210f;width:100%}
.err{color:var(--loss);font-size:13px;margin-top:8px;min-height:1em}
.top1{display:flex;justify-content:space-between;align-items:center;gap:10px}
.rf{font:600 14px Oswald,sans-serif;text-transform:uppercase;letter-spacing:.04em;padding:9px 14px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
.rf:active{opacity:.6}.rf.busy{opacity:.5}
/* compact (Nov 1, Peter: less scrolling) */
.wrap{padding:12px 12px 32px}h1{font-size:22px}.sub{margin-bottom:10px}.rf{padding:6px 10px;font-size:13px}
.tiles{margin-bottom:12px;gap:6px}.tile{padding:7px 9px;border-radius:12px}.tile .n{font-size:clamp(15px,4.6vw,20px)}.tile .r{color:var(--muted);font-size:11px}
h2{font-size:17px;margin:14px 0 6px}.card{padding:10px 12px;border-radius:14px;margin-bottom:8px}
.team{margin-top:3px;font-size:16px}.team b{font-size:19px}hr{margin:7px 0 6px}
.betl{gap:2px 10px}.betl .b{font-size:18px}.betl .p{font-size:15px}.betl .m{font-size:13px}.pill{margin-top:6px;font-size:13px;padding:3px 8px}.note{font-size:12px;margin-top:5px}
.day{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin:10px 2px 4px}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:7px 10px;margin-bottom:5px}
.row.win{box-shadow:inset 4px 0 0 var(--win)}.row.loss{box-shadow:inset 4px 0 0 var(--loss)}
.row .l1{font:600 15px Oswald,sans-serif;text-transform:uppercase}.row .l1 span{color:var(--muted);font:500 13px Inter,sans-serif;text-transform:none}
.row .l2{color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.row>div:first-child{min-width:0}
.row .amt{font:600 17px Oswald,sans-serif;white-space:nowrap}.row.win .amt{color:var(--win)}.row.loss .amt{color:var(--loss)}
.box{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;margin-bottom:10px}
.seg{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{font:500 14px Inter,sans-serif;padding:8px 0;background:none;border:0;color:var(--muted)}.seg button.on{background:#222a27;color:var(--fg);font-weight:600}
.sum{color:var(--muted);font-size:13px;margin:8px 2px}.sum b{color:var(--fg)}
.kpi{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;gap:6px}.kpi .v{font:600 20px Oswald,sans-serif}.kpi .k{color:var(--muted);font-size:12px}
.calh{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}.calh button{background:none;border:0;color:var(--fg);font-size:20px;padding:2px 10px}
.calh .mo{font:600 17px Oswald,sans-serif}.calh .mp{font:600 15px Oswald,sans-serif}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;text-align:center}.cal .dn{color:var(--muted);font-size:11px;padding:2px 0}
.cal .c{border-radius:8px;padding:4px 0;min-height:40px;border:1px solid transparent;cursor:pointer}.cal .c .n{font-size:13px}.cal .c .p{font:600 11px Oswald,sans-serif}
.cal .c.pos{background:var(--winbg)}.cal .c.neg{background:var(--lossbg)}.cal .c.sel{border-color:#60a5fa}.cal .c.today .n{font-weight:700;text-decoration:underline}
.cal .c .p.pos{color:var(--win)}.cal .c .p.neg{color:var(--loss)}.cal .c .p.open{color:#60a5fa}
/* Nov 3 (Peter): look more like OddsJam - solid calendar tiles, Settled/Live/Upcoming tabs, bet rows with result badge */
.calh .mo{font:600 22px Oswald,sans-serif;margin:0 6px}.calh .mp{font:600 20px Oswald,sans-serif}.calh .mp small{color:var(--muted);font:500 13px Inter,sans-serif;margin-left:4px}
.cal{gap:5px}.cal .dn{font-size:12px;font-weight:600;padding:4px 0}
.cal .c{min-height:50px;border-radius:9px;padding:5px 0;border:1px solid transparent;background:none}
.cal .c .n{font:500 14px Inter,sans-serif}.cal .c .p{font:700 13px Inter,sans-serif;letter-spacing:-.02em}
.cal .c.pos{background:#3f6b2a;border-color:#5f9a3e}.cal .c.neg{background:#7a1c1c;border-color:#a83232}
.cal .c.pos .n,.cal .c.neg .n,.cal .c.pos .p,.cal .c.neg .p{color:#fff}.cal .c.open{border-color:#60a5fa}
.cal .c.sel{outline:2px solid #60a5fa;outline-offset:1px}.cal .c.empty{background:none;border-color:transparent}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-bottom:10px}
.tabs button{font:500 15px Inter,sans-serif;padding:9px 0;background:none;border:0;color:var(--muted)}.tabs button.on{background:#222a27;color:var(--fg);font-weight:600}
.tk{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;margin:4px 0 10px}.tk .v{font:600 26px Oswald,sans-serif}.tk .k{color:var(--muted);font-size:13px}
.bl{border-top:1px solid var(--line);padding:12px 2px}.bl:first-of-type{border-top:0}
.bl .t1{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.bl .nm{font:600 16px Inter,sans-serif}.bl .ty{color:var(--muted);font-size:14px;margin-top:1px}
.bl .pf{text-align:right;white-space:nowrap}.bl .pf .k{color:var(--muted);font-size:13px}.bl .pf .v{font:700 19px Inter,sans-serif}
.bl .mk{font:600 15px Inter,sans-serif;margin-top:10px}.bl .gm{color:#cfd6d2;font-size:13px}
.bl .t3{display:flex;justify-content:space-between;align-items:center;margin-top:6px}.bl .sc{font:500 15px Inter,sans-serif}
.badge{display:inline-block;margin-left:8px;padding:1px 7px;border-radius:5px;font:700 13px Inter,sans-serif;letter-spacing:.03em;border:1px solid}
.badge.win{color:#86efac;background:#14301f;border-color:#2f6b45}.badge.loss{color:#fca5a5;background:#3a1a1a;border-color:#7a2a2a}.badge.push{color:var(--muted);border-color:var(--line)}
.bl .od{font:500 14px Inter,sans-serif;color:#cfd6d2;display:flex;align-items:center;gap:6px}.bk1{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:#eef1ef;color:#0f1311;font:700 12px Inter,sans-serif}
.bar{position:relative;height:8px;border-radius:4px;background:#2a312e;margin:12px 34px 4px 0}.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:4px}.bar i.win{background:var(--win)}.bar i.loss{background:#e5483b}
.bar b{position:absolute;top:50%;transform:translate(-50%,-50%);font:600 12px Inter,sans-serif;background:var(--card);border:2px solid currentColor;border-radius:10px;padding:1px 6px}.bar u{position:absolute;top:-3px;bottom:-3px;width:2px;background:#cfd6d2}
</style></head><body><div class="wrap" id="app"><div class="lock"><h1>Bet Tracker</h1><p class="sub">Private. Enter your passphrase.</p>
<form id="f"><input id="p" type="password" autocomplete="current-password" placeholder="Passphrase"><button>Unlock</button></form><div class="err" id="e"></div></div></div>
<script>
let BLOB=__BLOB__;let PASS=null;
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function unlock(pass){const k=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveKey']);
const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64(BLOB.s),iterations:BLOB.n,hash:'SHA-256'},k,{name:'AES-GCM',length:256},false,['decrypt']);
const pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64(BLOB.i)},key,b64(BLOB.c));return JSON.parse(new TextDecoder().decode(pt));}
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const $=v=>v==null?'—':(v<0?'-$':'$')+Math.abs(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const sg=v=>v==null?'—':(v>0?'+':v<0?'':'')+$(v);const pr=p=>p==null?'':(p>0?'+'+p:String(p));
const src=b=>b.source==='bot'?'Bot fill':(b.source==='ntfy (Peter manual)'?'ntfy (manual)':'Peter');
function teams(b){if(b.teams&&b.teams.length===2){const [a,h]=b.teams;const live=b.g_state==='in'||b.g_state==='post';
return b.teams.map((t,i)=>{const o=b.teams[1-i];const cl=live?(t.score>=o.score?'lead':'trail'):'';return `<div class="team ${cl}"><span>${esc(t.name)}</span><b>${live?t.score:'—'}</b></div>`}).join('');}
const g=String(b.game||'').split(/\\s+(?:@|at|vs\\.?)\\s+/i);return g.length===2?g.map(n=>`<div class="team"><span>${esc(n)}</span><b>—</b></div>`).join(''):`<div class="team"><span>${esc(b.game||'')}</span></div>`;}
function card(b,kind){const res=b.result;const cls=res==='W'?'win':res==='L'?'loss':'';
let st;if(kind==='settled')st=`<span class="s ${cls}">Final · ${res==='W'?'Won':res==='L'?'Lost':'Push'}</span>`;
else if(kind==='live')st=`<span class="s live"><i class="dot"></i>Live · ${esc(b.g_detail||'')}</span>`;else st=`<span class="s">${esc(b.when||'')}</span>`;
const banner=kind==='settled'?`<div class="banner ${res==='W'?'win':res==='L'?'loss':'push'}"><span><i class="c"></i>${res==='W'?'Won':res==='L'?'Lost':'Push'}</span><span>${sg(b.profit)}</span></div>`:'';
const s=b.status||'';const good=/COVERING|HOLDING$|WINNING/.test(s),bad=/BEHIND|NOT HOLDING|LOSING/.test(s);
const pill=kind==='settled'?`<span class="pill ${cls||'neu'}">${res==='W'?'Won':res==='L'?'Lost':'Push'} ${sg(b.profit)}</span>`:(s?`<span class="pill ${bad?'loss':good?'win':'neu'}">${esc(s)}</span>`:'');
const notes=[b.site===false?'graded from the final score':'',/est\\./.test(b.source||'')?'stake estimated (log it to make it exact)':''].filter(Boolean).join(' · ');
return `<div class="card ${kind==='settled'?cls:''}"><div class="hdr"><span>${esc(b.league||'')}${b.league?' · ':''}${esc(src(b))}</span>${st}</div>${banner}${teams(b)}<hr>
<div class="betl"><span class="b">${esc(b.bet)}</span><span class="p">${pr(b.price)}</span><span class="m">${$(b.stake)} → ${b.to_pay?$(b.to_pay):'—'}</span><span class="bk">${esc(b.book)}</span></div>
${pill}${notes?`<div class="note">${esc(notes)}</div>`:''}</div>`;}
let DATA=null;function render(d){DATA=d;const t=d.tiles;const tile=(l,v,r)=>`<div class="tile"><div class="l">${l}</div><div class="n" style="color:${v>0?'var(--win)':v<0?'var(--loss)':'var(--fg)'}">${sg(v)}</div>${r?`<div class="r">${r}</div>`:''}</div>`;
const sec=(h,a,k)=>a.length?`<h2>${h}</h2>`+a.map(b=>card(b,k)).join(''):'';
const mkOf=b=>{const t=String(b.bet||'');return /^(over|under|not over|not under)/i.test(t)?'Total Points':(/\\bml\\b|moneyline|to win/i.test(t)?'Moneyline':(/[+-]\\d/.test(t)?'Point Spread':''));};
const k1=v=>{const a=Math.abs(v);return (v<0?'-$':'$')+(a>=1000?(a/1000).toFixed(1).replace(/\\.0$/,'')+'k':Math.round(a).toLocaleString());};
const rowOf=b=>{const r=b.result,c=r==='W'?'win':r==='L'?'loss':'push';const tm=b.teams&&b.teams.length===2?b.teams:null;
const gm=tm?`${tm[0].name} vs ${tm[1].name}`:(b.game||'');const sc=tm?`${tm[0].score}-${tm[1].score}`:'';
let bar='';const mk=mkOf(b);const lm=String(b.bet||'').match(/(\\d+(?:\\.\\d+)?)/);
if(mk==='Total Points'&&tm&&lm){const tot=tm[0].score+tm[1].score,ln=parseFloat(lm[1]),mx=Math.max(tot,ln)*1.15||1;
bar=`<div class="bar" style="color:${r==='W'?'var(--win)':'#e5483b'}"><i class="${c}" style="width:${Math.min(100,tot/mx*100)}%"></i><u style="left:${ln/mx*100}%"></u><b style="left:${Math.min(100,tot/mx*100)}%">${tot}</b></div>`;}
return `<div class="bl"><div class="t1"><div><div class="nm">${esc(b.bet)}</div><div class="ty">${esc(src(b))}</div></div>
<div class="pf"><div class="k">Profit</div><div class="v" style="color:${r==='W'?'var(--win)':r==='L'?'var(--loss)':'var(--fg)'}">${$(Math.abs(b.profit||0))}</div></div></div>
${mk?`<div class="mk">${mk}</div>`:''}<div class="gm">${esc(gm)}</div>
<div class="t3"><div class="sc">${esc(sc)}<span class="badge ${c}">${r==='W'?'WON':r==='L'?'LOST':'PUSH'}</span></div>
<div class="od">${pr(b.price)}<span class="bk1" title="${esc(b.book)}">${esc(String(b.book||'?').charAt(0))}</span></div></div>${bar}</div>`;};
const dkey=b=>{const x=new Date(b.game_start||b.settled||0);return isNaN(x)?'Earlier':x.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:'America/New_York'});};
const settledHTML=a=>{if(!a.length)return '';const g={};a.forEach(b=>{(g[dkey(b)]=g[dkey(b)]||[]).push(b)});
return '<h2>Settled</h2>'+Object.entries(g).map(([k,l])=>{const tot=l.reduce((s,b)=>s+(b.profit||0),0);const w=l.filter(b=>b.result==='W').length,lo=l.filter(b=>b.result==='L').length;
return `<div class="day"><span>${esc(k)} · ${w}-${lo}</span><span style="color:${tot>0?'var(--win)':tot<0?'var(--loss)':'var(--muted)'}">${sg(Math.round(tot*100)/100)}</span></div>`+l.map(rowOf).join('')}).join('');};
const wl=a=>{const w=a.filter(b=>b.result==='W').length,l=a.filter(b=>b.result==='L').length;return w+l?`${w}-${l}`:'';};
const today=new Date().toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',timeZone:'America/New_York'});
const ymd=x=>{const s=x.game_start||x.settled||x.first_seen;if(!s)return null;return new Date(s).toLocaleDateString('en-CA',{timeZone:'America/New_York'});};
const ALL=(d.all||[]);const byDay={};ALL.forEach(b=>{const k=ymd(b);if(k)(byDay[k]=byDay[k]||[]).push(b)});const tk=b=>b.game_start||b.placed||b.settled||'';Object.values(byDay).forEach(l=>l.sort((x,y)=>tk(x).localeCompare(tk(y))));
const todayK=new Date().toLocaleDateString('en-CA',{timeZone:'America/New_York'});
window.SEL=window.SEL||todayK;window.CALM=window.CALM||todayK.slice(0,7);
const shift=(k,n)=>{const x=new Date(k+'T12:00:00');x.setDate(x.getDate()+n);return x.toLocaleDateString('en-CA');};
const dayStats=k=>{const l=byDay[k]||[];const s=l.filter(b=>b.result),o=l.filter(b=>!b.result&&b.open);
return {l,s,o,live:o.filter(b=>b.g_state==='in').length,up:o.filter(b=>b.g_state!=='in').length,
pnl:s.reduce((a,b)=>a+(b.profit||0),0),risk:o.reduce((a,b)=>a+(b.stake||0),0),max:o.reduce((a,b)=>a+((b.to_pay||0)-(b.stake||0)),0)};};
const fmt0=v=>(v<0?'-$':'$')+Math.abs(Math.round(v)).toLocaleString();
const dayBox=()=>{const k=window.SEL,st=dayStats(k);const lab=new Date(k+'T12:00:00').toLocaleDateString('en-US',{weekday:'long',month:'short',day:'numeric'});
const segb=(n,txt)=>`<button class="${shift(todayK,n)===k?'on':''}" onclick="SEL='${shift(todayK,n)}';CALM=SEL.slice(0,7);render(DATA)">${txt}</button>`;
return `<div class="box"><div class="seg">${segb(-1,'Yesterday')}${segb(0,'Today')}${segb(1,'Tomorrow')}</div>
<div class="sum">${esc(lab)}: <b>${st.s.length}</b> settled, <b>${st.live}</b> live, <b>${st.up}</b> upcoming</div>
<div class="kpi"><div><div class="v" style="color:${st.pnl>0?'var(--win)':st.pnl<0?'var(--loss)':'var(--fg)'}">${sg(Math.round(st.pnl*100)/100)}</div><div class="k">Settled</div></div>
<div><div class="v">${$(st.risk)}</div><div class="k">At risk</div></div><div><div class="v">${$(st.max)}</div><div class="k">Max profit</div></div></div></div>`;};
const calBox=()=>{const [Y,M]=window.CALM.split('-').map(Number);const first=new Date(Y,M-1,1),days=new Date(Y,M,0).getDate();
let mp=0;Object.entries(byDay).forEach(([k,l])=>{if(k.startsWith(window.CALM))mp+=l.reduce((a,b)=>a+(b.result?(b.profit||0):0),0)});
let cells='';for(let i=0;i<first.getDay();i++)cells+='<div class="c empty"></div>';
for(let dd=1;dd<=days;dd++){const k=`${window.CALM}-${String(dd).padStart(2,'0')}`;const st=dayStats(k);let p='',cl='';
if(st.s.length){cl=st.pnl>0?'pos':st.pnl<0?'neg':'';p=`<div class="p">${k1(Math.abs(st.pnl))}</div>`;}else if(st.o.length){cl='open';p=`<div class="p open">${k1(st.risk)}</div>`;}
cells+=`<div class="c ${cl} ${k===window.SEL?'sel':''} ${k===todayK?'today':''}" onclick="SEL='${k}';render(DATA)"><div class="n">${dd}</div>${p}</div>`;}
const mv=n=>{const x=new Date(Y,M-1+n,1);return `${x.getFullYear()}-${String(x.getMonth()+1).padStart(2,'0')}`;};
return `<div class="box"><div class="calh"><div><button onclick="CALM='${mv(-1)}';render(DATA)">‹</button><span class="mo">${first.toLocaleDateString('en-US',{month:'short',year:'numeric'})}</span><button onclick="CALM='${mv(1)}';render(DATA)">›</button></div>
<div class="mp" style="color:${mp>0?'var(--win)':mp<0?'var(--loss)':'var(--fg)'}">${sg(Math.round(mp*100)/100)}<small>Profit</small></div></div>
<div class="cal">${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(x=>`<div class="dn">${x}</div>`).join('')}${cells}</div></div>`;};
const dayList=()=>{const st=dayStats(window.SEL);const live=st.o.filter(b=>b.g_state==='in'),up=st.o.filter(b=>b.g_state!=='in');
if(!st.l.length)return '<p class="sub">No bets this day.</p>';
let T=window.TAB;if(!T||(T==='live'&&!live.length&&(st.s.length||up.length))||(T==='settled'&&!st.s.length)||(T==='up'&&!up.length))T=live.length?'live':(st.s.length?'settled':'up');window.TAB=T;
const tb=(k,n,txt)=>`<button class="${T===k?'on':''}" onclick="TAB='${k}';render(DATA)">${n} ${txt}</button>`;
const list=T==='settled'?st.s:(T==='live'?live:up);const risk=list.filter(b=>!b.result).reduce((a,b)=>a+(b.stake||0),0);
const pnl=T==='settled'?st.pnl:list.reduce((a,b)=>a+((b.to_pay||0)-(b.stake||0)),0);
return `<div class="box"><div class="tabs">${tb('settled',st.s.length,'Settled')}${tb('live',live.length,'Live')}${tb('up',up.length,'Upcoming')}</div>
<div class="tk"><div><div class="v">${list.length}</div><div class="k">Bets</div></div><div><div class="v">${$(risk)}</div><div class="k">At Risk</div></div>
<div><div class="v" style="color:${T!=='settled'?'var(--fg)':pnl>0?'var(--win)':pnl<0?'var(--loss)':'var(--fg)'}">${sg(Math.round(pnl*100)/100)}</div><div class="k">${T==='settled'?'Profit':'Max Profit'}</div></div></div>
${T==='settled'?list.map(rowOf).join(''):'</div>'+list.map(b=>card(b,T==='live'?'live':'up')).join('')+'<div>'}</div>`;};
document.getElementById('app').innerHTML=`<div class="top1"><h1>Bet Tracker</h1><button class="rf" id="rf" onclick="refresh()">↻ Refresh</button></div><p class="sub">Updated ${esc(d.updated)} · settled profit from the books' own numbers</p>
<div class="tiles">${tile('Today',t.today,wl(d.settled.filter(b=>dkey(b)===today)))}${tile('This week',t.week,wl(d.settled))}${tile('This month',t.month,'')}</div>
${dayBox()}${calBox()}${dayList()}${sec('Other open bets',d.unmatched||[],'up')}
<p class="sub">Reads: ${esc(d.reads)}</p>`;
clearTimeout(window._rt);window._rt=setTimeout(refresh,d.live.length?60000:300000);}
async function refresh(){const btn=document.getElementById('rf');if(btn){btn.classList.add('busy');btn.textContent='Refreshing…';}
try{const h=await (await fetch(location.pathname+'?t='+Date.now(),{cache:'no-store'})).text();const m=h.match(/let BLOB=(\\{[^;]*\\});/);
if(m)BLOB=JSON.parse(m[1]);if(PASS)render(await unlock(PASS));}catch(e){if(btn)btn.textContent='↻ Refresh';}}
async function go(pass,save){try{const d=await unlock(pass);PASS=pass;try{if(save)localStorage.setItem('btp',pass)}catch(e){}render(d);}catch(e){const el=document.getElementById('e');if(el)el.textContent='Wrong passphrase.';try{localStorage.removeItem('btp')}catch(_){}}}
document.getElementById('f').onsubmit=e=>{e.preventDefault();go(document.getElementById('p').value,true);};
try{const s=localStorage.getItem('btp');if(s)go(s,false);}catch(e){}
</script></body></html>"""


def main():
    if not PASS:
        print("Tracker: TRACKER_PASSPHRASE not set; skipped")
        return
    now = datetime.now(timezone.utc)
    d = now.astimezone(ET)
    day0 = d.replace(hour=0, minute=0, second=0, microsecond=0)
    week0 = day0 - timedelta(days=day0.weekday())
    month0 = day0.replace(day=1)
    since = min(week0, month0)
    try:
        state = dec(json.load(open(STATE)))
    except Exception:
        state = {"bets": {}}
    before = json.dumps(state, sort_keys=True)
    bets = state["bets"]

    import time as _t
    T = {}   # seconds per read (log only), to find what slows the tracker
    opened, settled = [], []
    for name, fn in (("prophetx", read_prophetx), ("kalshi", lambda: read_kalshi(since)), ("polymarket_us", lambda: read_pmus(since)),
                     ("novig", read_novig)):
        t0 = _t.time()
        try:
            o, s = fn()
            opened += o
            settled += s
        except (Exception, SystemExit) as e:
            LOG[name] = f"failed ({type(e).__name__})"
        T[name] = round(_t.time() - t0)
    t0 = _t.time()
    IMAP_CACHE.update(state.get("imap_cache") or {})
    try:
        man, keys = read_manual_and_bot()
    except (Exception, SystemExit) as e:
        man, keys = [], set()
        LOG["manual"] = f"failed ({type(e).__name__})"
    T["manual+bot"] = round(_t.time() - t0)
    T.update(IMAP_T)
    IMAP_CACHE["b"] = dict(list(IMAP_CACHE["b"].items())[-400:])
    IMAP_CACHE["m"] = dict(list(IMAP_CACHE["m"].items())[-200:])
    state["imap_cache"] = IMAP_CACHE
    t0 = _t.time()
    games = espn_games([d - timedelta(days=1), d, d + timedelta(days=1)])
    T["espn"] = round(_t.time() - t0)

    open_ids = set()
    for b in opened + man:
        open_ids.add(b["id"])
        prev = bets.get(b["id"]) or {}
        if prev.get("result"):
            if b["id"].startswith("mn|") and b.get("stake") and prev.get("stake") != b["stake"]:   # stake added later
                r = prev["result"]
                prev.update(stake=b["stake"], to_pay=b.get("to_pay"), source=b.get("source"),
                            profit=round((b["to_pay"] - b["stake"]) if r == "W" and b.get("to_pay") else (-b["stake"] if r == "L" else 0.0), 2))
            continue
        b["source"] = b.get("source") or ("bot" if bot_match(b, keys) or prev.get("source") == "bot" else "Peter")
        b["first_seen"] = prev.get("first_seen") or iso(now)
        bets[b["id"]] = {**prev, **b, "open": True}
    # Kalshi settlements carry only a ticker: join them to the open row we saw before (game + bet text)
    for s in settled:
        if s["book"] == "Kalshi":
            prev = next((v for v in bets.values() if v.get("ticker") == s.get("ticker") and v.get("game")), None)
            if prev:
                s = {**prev, **{k: v for k, v in s.items() if k not in ("game", "bet")}}
                bets.pop(prev["id"], None)
        elif s["book"] == "ProphetX":
            pass
        s["open"] = False
        prev_src = (bets.get(s["id"]) or {}).get("source")
        s["source"] = s.get("source") or ("bot" if bot_match(s, keys) or prev_src == "bot" else None) or \
            (prev_src if prev_src and prev_src != "Peter" else None) or "Peter"
        bets[s["id"]] = {**(bets.get(s["id"]) or {}), **{k: v for k, v in s.items() if v is not None}}   # Nov 2: a settlement row
        # without price / payout (Novig losses) no longer wipes the price the open row already had
    # settled bets from earlier days this week need their own ESPN dates (scores shown on every card)
    have = {g["start"][:10] for g in games if g.get("start")}
    extra = set()
    for b in bets.values():
        if b.get("teams_final"):
            continue
        t0 = tparse(b.get("game_start")) or tparse(b.get("settled"))
        if t0 and t0 >= week0 - timedelta(days=1):
            for dd in (t0.astimezone(ET), t0.astimezone(ET) - timedelta(days=1)):
                if dd.date() < (d - timedelta(days=1)).date():
                    extra.add(dd.replace(hour=12))
    if extra:
        games += espn_games(sorted(extra)[:8])
    for b in bets.values():
        # undo an earlier bad pin: a game more than 2 days from when the bet settled is not its game
        gs, ss = tparse(b.get("game_start")), tparse(b.get("settled"))
        if gs and ss and abs((gs - ss).total_seconds()) > 48 * 3600 and b.get("book") != "Novig":
            for f in ("game_start", "teams", "teams_final", "g_state", "g_detail"):
                b.pop(f, None)
        if not b.get("result") or b.get("teams_final"):
            continue
        near = tparse(b.get("game_start")) or tparse(b.get("settled"))
        if not near:
            continue
        g = match_game(b, games, near)
        if g:
            attach(b, g)
    # bets that left the open list without a site settlement (Novig, manual): grade from the final score
    nm = [0, 0]
    for k, b in list(bets.items()):
        if b.get("result"):
            continue
        g = match_game(b, games)
        nm[0 if g else 1] += 1
        if g:
            b["game_start"] = g["start"]
            st, outc = read_status(b, g) if g["state"] in ("in", "post") else ("", None)
            b["status"], b["score"] = st, score_line(g)
            attach(b, g)
            if outc and (k not in open_ids or b["book"] in ("Novig", "Hard Rock", "manual")) and b["book"] not in ("ProphetX", "Kalshi", "Polymarket US"):
                b["result"] = outc
                b["profit"] = round((b["to_pay"] - b["stake"]) if outc == "W" and b.get("to_pay") and b.get("stake") else
                                    (-(b.get("stake") or 0) if outc == "L" else 0.0), 2)
                b["settled"], b["site"], b["open"] = iso(now), False, False
        elif k not in open_ids and b["book"] in ("ProphetX", "Kalshi", "Polymarket US") and not b.get("result"):
            b["open"] = False   # left the book's open list; its site settlement will arrive in a later read

    for b in bets.values():
        if b.get("source") == "Peter" and reclass(b):
            b["source"] = "ntfy (Peter manual)"

    def et_date(s):
        t = tparse(s)
        return t.astimezone(ET) if t else None

    def gdate(b):
        return et_date(b.get("game_start")) or et_date(b.get("settled"))

    sett = [b for b in bets.values() if b.get("result") in ("W", "L", "P")]
    tile = lambda t0: round(sum(b.get("profit") or 0 for b in sett if gdate(b) and gdate(b) >= t0), 2)
    live, up, unm = [], [], []
    for b in bets.values():
        if b.get("result") or not b.get("open"):
            continue
        st = et_date(b.get("game_start"))
        b["when"] = st.strftime("%a %-I:%M %p") if st else ""
        if not b.get("game_start"):
            unm.append(b)
        elif st and st <= d:
            live.append(b)
        else:
            up.append(b)
    up.sort(key=lambda b: b.get("game_start") or "")
    week_settled = sorted([b for b in sett if gdate(b) and gdate(b) >= week0], key=lambda b: b.get("settled") or "", reverse=True)
    # keep 45 days of history in the state
    cut = iso(now - timedelta(days=45))
    state["bets"] = {k: v for k, v in bets.items() if not v.get("result") or (v.get("settled") or "") >= cut}
    view = {"updated": d.strftime("%a %b %-d, %-I:%M %p ET"),
            "tiles": {"today": tile(day0), "week": tile(week0), "month": tile(month0)},
            "live": live, "upcoming": up, "settled": week_settled, "unmatched": unm,
            "all": [{k: b.get(k) for k in ("bet", "price", "stake", "to_pay", "book", "source", "result", "profit", "teams",
                                           "game", "league", "g_state", "g_detail", "status", "game_start", "settled",
                                           "first_seen", "open", "site", "when")}
                    for b in state["bets"].values() if b.get("result") or b.get("open")],
            "graded_note": "Novig and manual bets graded from final scores" if any(b.get("site") is False for b in sett) else "",
            "reads": ", ".join(f"{k} {'ok' if str(v).startswith('ok') else 'failed'}" for k, v in LOG.items())}
    if json.dumps(state, sort_keys=True) != before:   # re-encrypt (new IV) only when the bets changed: fewer commits
        os.makedirs("tracker", exist_ok=True)
        with open(STATE, "w") as f:
            json.dump(enc(state), f)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(PAGE.replace("__BLOB__", json.dumps(enc(view))))
    print("Tracker:", "; ".join(f"{k} {v}" for k, v in LOG.items()), f"| games matched {nm[0]}, not matched {nm[1]}",
          f"| open {len(live) + len(up) + len(unm)}, settled this week {len(week_settled)}",
          "| seconds: " + ", ".join(f"{k} {v}" for k, v in T.items()))   # counts only


if __name__ == "__main__":
    main()

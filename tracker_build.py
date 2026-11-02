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


def espn_games(days):
    games = []
    for lg, path in LEAGUES.items():
        for d in days:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={d.strftime('%Y%m%d')}&limit=400"
            if lg == "NCAAF":
                url += "&groups=80"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
                    data = json.loads(r.read().decode())
            except Exception:
                continue
            for ev in data.get("events") or []:
                comp = (ev.get("competitions") or [{}])[0]
                teams = []
                for c in comp.get("competitors") or []:
                    t = c.get("team") or {}
                    names = " ".join(str(t.get(k) or "") for k in ("displayName", "shortDisplayName", "name", "location", "abbreviation"))
                    teams.append({"home": c.get("homeAway") == "home", "names": names, "toks": toks(names),
                                  "abbr": (t.get("abbreviation") or "").lower(), "score": num(c.get("score")) or 0,
                                  "short": t.get("shortDisplayName") or t.get("displayName") or ""})
                st = (ev.get("status") or {}).get("type") or {}
                games.append({"league": lg, "id": ev.get("id"), "start": ev.get("date"), "teams": teams,
                              "state": st.get("state"), "detail": st.get("shortDetail") or st.get("detail") or "",
                              "final": bool(st.get("completed")), "period": (ev.get("status") or {}).get("period"),
                              "clock": (ev.get("status") or {}).get("displayClock")})
    LOG["espn"] = f"ok {len(games)}"
    return games


def match_game(bet, games):
    bt = toks(bet.get("game")) | toks(bet.get("bet"))
    best, score = None, 0
    for g in games:
        if bet.get("league") and bet["league"] != g["league"]:
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
    m = re.match(r"(\d+):(\d+)", str(g.get("clock") or ""))
    left = (int(m.group(1)) + int(m.group(2)) / 60) if m else mins / 2
    return min(1.0, ((min(p, n) - 1) * mins + (mins - left)) / (n * mins))


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
        for k in ("settled_at", "settle_time", "settled_time", "updated_at", "update_time"):
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
            op.append({"id": f"ks|{tk}|{'no' if q < 0 else 'yes'}", "book": "Kalshi", "game": title,
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
        se.append({"id": f"ks|{s.get('ticker')}|settled", "book": "Kalshi", "game": "", "bet": s.get("ticker") or "",
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
    snap, age = ex._snap_read((os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip())
    op = []
    for p in snap.get("positions") or []:
        qty = num(p.get("qty")) or 0
        cost = num(p.get("cost")) or 0
        game, side = "", ""
        try:
            mk = lm.get(f"{lm.NOVIG}/v3/public/catalog/markets/{p.get('marketId')}")
            side = next((o.get("name") for o in mk.get("outcomes") or [] if o.get("outcomeId") == p.get("outcomeId")), "") or ""
            game = mk.get("description") or mk.get("title") or ""
            ev = mk.get("event") or {}
            game = ev.get("description") or game
        except Exception:
            pass
        op.append({"id": f"nv|{p.get('marketId')}|{p.get('outcomeId')}", "book": "Novig", "game": game, "bet": side,
                   "stake": round(cost, 2), "to_pay": round(qty, 2), "price": p_to_american(cost / qty) if qty and cost else None})
    LOG["novig"] = f"ok {len(op)} open (snapshot {age:.0f} min old)"
    return op


def read_manual_and_bot():
    """Peter's 'Bets manual' notes (Hard Rock etc.) + the bot's own live keys (to tag sources)."""
    import executor as ex
    man, keys = [], set()
    M = ex.imap_open()
    try:
        ex.bot_orders(M, days=10)
        keys = set(ex.LIVEKEYS)
        for uid in ex.gsearch(M, 'subject:"Bets manual" newer_than:10d'):
            typ, data = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not data or not data[0]:
                continue
            for line in ex.body_text(data[0][1]).splitlines():
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
                win = (stake * 100 / abs(pr) if pr and pr < 0 else stake * pr / 100 if pr else None) if stake else None
                man.append({"id": "mn|" + hashlib.sha1(line.strip().encode()).hexdigest()[:12], "book": d.get("book") or "manual",
                            "game": d.get("game") or "", "bet": d.get("bet") or "", "league": (d.get("sport") or "").upper() or None,
                            "price": pr, "stake": stake, "to_pay": round(stake + win, 2) if win else None, "source": "Peter (note)"})
    finally:
        M.logout()
    LOG["manual"] = f"ok {len(man)}"
    LOG["bot_keys"] = f"ok {len(keys)}"
    return man, keys


def bot_match(b, keys):
    pb = parse_bet(b.get("bet"), b.get("flip"))
    bt = toks(b.get("game"))
    for k in keys:
        sp, game, market, side = (k.split("|") + [None] * 4)[:4]
        if not game or len(toks(game) & bt) < 2 and not (toks(game) & toks(b.get("bet"))):
            continue
        if pb and pb[0] == "total" and market == "total" and side == pb[1]:
            return True
        if pb and pb[0] in ("spread", "ml") and market == "side" and (toks(side) & toks(pb[1])):
            return True
    return False


# ------------------------------------------------------------------ page
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bet Tracker</title><meta name="robots" content="noindex"><style>
:root{--bg:#faf9f5;--panel:#fff;--fg:#1f1e1d;--muted:#6b6a68;--line:#e6e3da;--ok:#2f7d4f;--bad:#b3261e;--warn:#a8650b}
@media (prefers-color-scheme:dark){:root{--bg:#1c1b1a;--panel:#262624;--fg:#f0eee8;--muted:#a3a19c;--line:#3a3936;--ok:#6cc08b;--bad:#ff8a80;--warn:#e0a94a}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:16px}h1{font-weight:500;margin:0;font-size:26px}.sub{color:var(--muted);margin:4px 0 14px;font-size:13px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px}
.tile .l{color:var(--muted);font-size:12px}.tile .n{font-size:22px;margin-top:2px;font-variant-numeric:tabular-nums}
h2{font-size:16px;margin:16px 0 6px}.bet{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px}
.top{display:flex;justify-content:space-between;gap:8px}.b{font-weight:600}.m{color:var(--muted);font-size:13px}.r{text-align:right;white-space:nowrap}
.st{font-weight:700;font-size:13px}.good{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.lock{max-width:340px;margin:20vh auto;text-align:center}.lock input{font:inherit;padding:10px;width:100%;box-sizing:border-box;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--fg)}
.lock button{margin-top:10px;font:inherit;padding:10px 16px;border-radius:8px;border:1px solid var(--fg);background:var(--fg);color:var(--bg);width:100%}
.err{color:var(--bad);font-size:13px;margin-top:8px;min-height:1em}
</style></head><body><div class="wrap" id="app"><div class="lock"><h1>Bet Tracker</h1><p class="sub">Private. Enter your passphrase.</p>
<form id="f"><input id="p" type="password" autocomplete="current-password" placeholder="Passphrase"><button>Unlock</button></form><div class="err" id="e"></div></div></div>
<script>
const BLOB=__BLOB__;
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function open(pass){const k=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveKey']);
const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64(BLOB.s),iterations:BLOB.n,hash:'SHA-256'},k,{name:'AES-GCM',length:256},false,['decrypt']);
const pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64(BLOB.i)},key,b64(BLOB.c));return JSON.parse(new TextDecoder().decode(pt));}
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const $=v=>v==null?'—':(v<0?'-$':'$')+Math.abs(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const sg=v=>v==null?'—':(v>0?'+':'')+$(v);const pr=p=>p==null?'':(p>0?'+'+p:p);
function card(b,kind){const cls=b.result==='W'?'good':b.result==='L'?'bad':(/COVERING|HOLDING$|WINNING/.test(b.status||'')?'good':/BEHIND|NOT HOLDING|LOSING/.test(b.status||'')?'bad':'warn');
const right=kind==='settled'?`<div class="st ${cls}">${b.result==='W'?'Won':b.result==='L'?'Lost':'Push'} ${sg(b.profit)}</div>`:`<div class="st ${cls}">${esc(b.status||'')}</div>`;
return `<div class="bet"><div class="top"><div><div class="b">${esc(b.bet)} ${pr(b.price)}</div><div class="m">${esc(b.game)}${b.when?' · '+esc(b.when):''}</div>
<div class="m">${esc(b.book)} · stake ${$(b.stake)} · to pay ${$(b.to_pay)} · ${esc(b.source||'')}${b.site===false?' · graded':''}</div>${b.score?`<div class="m">${esc(b.score)}</div>`:''}</div><div class="r">${right}</div></div></div>`;}
function render(d){const t=d.tiles;const tile=(l,v)=>`<div class="tile"><div class="l">${l}</div><div class="n ${v>0?'good':v<0?'bad':''}">${sg(v)}</div></div>`;
const sec=(h,a,k)=>a.length?`<h2>${h} (${a.length})</h2>`+a.map(b=>card(b,k)).join(''):'';
document.getElementById('app').innerHTML=`<h1>Bet Tracker</h1><p class="sub">Updated ${esc(d.updated)}. Settled profit from the books' own numbers${d.graded_note?'; '+esc(d.graded_note):''}.</p>
<div class="tiles">${tile('Today',t.today)}${tile('This week',t.week)}${tile('This month',t.month)}</div>
${sec('Live',d.live,'live')}${sec('Upcoming',d.upcoming,'up')}${sec('Settled this week',d.settled,'settled')}
${d.unmatched&&d.unmatched.length?`<h2>Open, game not matched (${d.unmatched.length})</h2>`+d.unmatched.map(b=>card(b,'up')).join(''):''}
<p class="sub">Reads: ${esc(d.reads)}</p>`;
if(d.live.length)setTimeout(()=>location.reload(),60000);else setTimeout(()=>location.reload(),300000);}
async function go(pass,save){try{const d=await open(pass);try{if(save)localStorage.setItem('btp',pass)}catch(e){}render(d);}catch(e){document.getElementById('e').textContent='Wrong passphrase.';try{localStorage.removeItem('btp')}catch(_){}}}
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

    opened, settled = [], []
    for name, fn in (("prophetx", read_prophetx), ("kalshi", lambda: read_kalshi(since)), ("polymarket_us", lambda: read_pmus(since)),
                     ("novig", lambda: (read_novig(), []))):
        try:
            o, s = fn()
            opened += o
            settled += s
        except (Exception, SystemExit) as e:
            LOG[name] = f"failed ({type(e).__name__})"
    try:
        man, keys = read_manual_and_bot()
    except (Exception, SystemExit) as e:
        man, keys = [], set()
        LOG["manual"] = f"failed ({type(e).__name__})"
    games = espn_games([d - timedelta(days=1), d, d + timedelta(days=1)])

    open_ids = set()
    for b in opened + man:
        open_ids.add(b["id"])
        prev = bets.get(b["id"]) or {}
        if prev.get("result"):
            continue
        b["source"] = b.get("source") or ("bot" if bot_match(b, keys) else "Peter")
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
        s["source"] = (bets.get(s["id"]) or {}).get("source") or ("bot" if bot_match(s, keys) else "Peter")
        bets[s["id"]] = {**(bets.get(s["id"]) or {}), **s}
    # bets that left the open list without a site settlement (Novig, manual): grade from the final score
    for k, b in list(bets.items()):
        if b.get("result"):
            continue
        g = match_game(b, games)
        if g:
            b["game_start"] = g["start"]
            st, outc = read_status(b, g)
            b["status"], b["score"] = st, score_line(g)
            if outc and (k not in open_ids or b["book"] in ("Novig", "Hard Rock", "manual")) and b["book"] not in ("ProphetX", "Kalshi", "Polymarket US"):
                b["result"] = outc
                b["profit"] = round((b["to_pay"] - b["stake"]) if outc == "W" and b.get("to_pay") and b.get("stake") else
                                    (-(b.get("stake") or 0) if outc == "L" else 0.0), 2)
                b["settled"], b["site"], b["open"] = iso(now), False, False
        elif k not in open_ids and b["book"] in ("ProphetX", "Kalshi", "Polymarket US") and not b.get("result"):
            b["open"] = False   # left the book's open list; its site settlement will arrive in a later read

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
            "graded_note": "Novig and manual bets graded from final scores" if any(b.get("site") is False for b in sett) else "",
            "reads": ", ".join(f"{k} {'ok' if str(v).startswith('ok') else 'failed'}" for k, v in LOG.items())}
    if json.dumps(state, sort_keys=True) != before:   # re-encrypt (new IV) only when the bets changed: fewer commits
        os.makedirs("tracker", exist_ok=True)
        with open(STATE, "w") as f:
            json.dump(enc(state), f)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(PAGE.replace("__BLOB__", json.dumps(enc(view))))
    print("Tracker:", "; ".join(f"{k} {v}" for k, v in LOG.items()),
          f"| open {len(live) + len(up) + len(unm)}, settled this week {len(week_settled)}")   # counts only


if __name__ == "__main__":
    main()

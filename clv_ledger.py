#!/usr/bin/env python3
"""
LIVE CLV LEDGER (Nov 2, 2026; Peter: "the best and most accurate and most efficient").
Every real bet (bot and Peter, every book) scored against PINNACLE'S TRUE CLOSE: the last Pinnacle tick before the
game's start, from OddsPapi's free /v4/historical-odds, no-vig, at the bet's OWN line when Pinnacle hung that line
(else Pinnacle's main line moved to the bet's number with the half-point table in sharp_monitor).
CLV = close fair win chance x the bet's after-fee decimal price - 1 (what the bet was worth at the close).

Also (Peter, Nov 2 "stale reads and calls"): NOVIG STALE CHECK - for each bot Novig order, Novig's own price in
OddsPapi's history at the bot's decision time vs the price the bot used, and how old that Novig quote was.

Read-only. Bets come from the encrypted tracker state (tracker/state.enc); this script keeps its own encrypted state
(clv/state.enc) and a public market-id map (clv/markets.json, OddsPapi ids only). Billable OddsPapi calls: /fixtures
(one per league, at most every 6 h, only when a bet needs it), /markets (once a week), /tournaments (NCAAF id, once).
Hard cap CLV_MONTH_CAP billable calls per month. Private email; the Actions log prints counts only.
Kill-switch (Muse registration, alert-only until Peter decides): rolling 50 scored bot bets, average CLV < 0 -> ALERT.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import executor as ex
import sharp_monitor as sm
import tracker_build as tb

BASE = "https://api.oddspapi.io/v4"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
STATE = "clv/state.enc"
MKFILE = "clv/markets.json"
ET = tb.ET
CAP = int(os.environ.get("CLV_MONTH_CAP", "") or "150")
SPORT = {"NBA": 11, "NFL": 14, "NCAAF": 14, "NHL": 15}
TOURN = {"NBA": 132, "NFL": 31, "NHL": 234}           # NCAAF looked up once (the probe's 850 was wrong)
ML_MARKET = {11: "111", 14: "141", 15: "151"}         # Winner incl. overtime (hockey: incl. OT and penalties)
FRESH_MIN = 24 * 60  # history stores CHANGES: a line's last pre-start tick is its price at the start unless it is a day old
SCORE_AFTER_MIN = 10  # score a bet this long after its listed start
MAX_TRIES = 8
MAX_HIST = 60        # free history calls per run
CALLS = []
STATS = {"billable": 0, "free": 0}


# ------------------------------------------------------------------ OddsPapi
def api(path, billable, **params):
    params["apiKey"] = KEY
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"Accept": "application/json", "User-Agent": "sharp-monitor-clv"})
    time.sleep(8.0 if path == "/historical-odds" else 1.1)   # history throttles (429 seen at ~1 s spacing)
    STATS["billable" if billable else "free"] += 1
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                CALLS.append((path, r.status))
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(20)
                continue
            CALLS.append((path, e.code))
            return {"_error": e.code, "_body": e.read().decode()[:200]}
        except Exception as e:
            CALLS.append((path, type(e).__name__))
            return {"_error": type(e).__name__, "_body": str(e)[:200]}


def month_key(now):
    return now.strftime("%Y-%m")


def can_bill(st, now, n=1):
    used = st.setdefault("billable", {}).get(month_key(now), 0)
    return used + n <= CAP


def bill(st, now, n=1):
    st["billable"][month_key(now)] = st["billable"].get(month_key(now), 0) + n


# ------------------------------------------------------------------ helpers
def tp(x):
    return tb.tparse(x)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def am_to_dec(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def dec_to_am(d):
    d = float(d)
    if d <= 1:
        return None
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def eff_dec(b):
    """The bet's after-fee decimal price: what it pays back per $1 staked."""
    st, pay = tb.num(b.get("stake")), tb.num(b.get("to_pay"))
    if st and pay and pay > st:
        return pay / st
    if b.get("price") not in (None, ""):
        d = am_to_dec(b["price"])
        return 1 + (d - 1) * 0.98 if b.get("book") == "ProphetX" else d   # ProphetX: 2% fee on winnings
    return None


def parsed(b):
    """(kind 'ml'|'spread'|'total', team_text or OVER/UNDER, line or None) for the side actually held."""
    pb = tb.parse_bet(b.get("bet"), b.get("flip"))
    if not pb:
        return None
    if pb[0] == "total":
        return ("total", pb[1], pb[2])
    kind, team, line, neg = pb[0], pb[1], pb[2], pb[3]
    return (kind, team, line, neg)


# ------------------------------------------------------------------ market map (public ids only)
def load_markets(st, now):
    try:
        mk = json.load(open(MKFILE))
        if (now - tp(mk["fetched"])).days < 7:
            return mk["m"]
    except Exception:
        mk = None
    if not can_bill(st, now):
        return (mk or {}).get("m") or {}
    d = api("/markets", True)
    bill(st, now)
    if not isinstance(d, list):
        return (mk or {}).get("m") or {}
    m = {}
    for x in d:
        if x.get("sportId") in (11, 14, 15) and str(x.get("period")) == "result" and x.get("marketType") in ("moneyline", "spreads", "totals") \
                and not x.get("playerProp"):
            m[str(x["marketId"])] = [x["sportId"], x["marketType"], float(x.get("handicap") or 0),
                                     {str(o["outcomeId"]): o.get("outcomeName") for o in x.get("outcomes") or []}]
    os.makedirs("clv", exist_ok=True)
    json.dump({"fetched": iso(now), "note": "OddsPapi market ids (full game incl. overtime): public reference data",
               "m": m}, open(MKFILE, "w"), separators=(",", ":"))
    return m


# ------------------------------------------------------------------ fixtures
def tournament(st, now, lg):
    if lg in TOURN:
        return TOURN[lg]
    if lg != "NCAAF":
        return None
    if st.get("ncaaf_tid"):
        return st["ncaaf_tid"]
    if not can_bill(st, now):
        return None
    ts = api("/tournaments", True, sportId=14)
    bill(st, now)
    best = None
    for t in ts if isinstance(ts, list) else []:
        nm = (t.get("tournamentName") or "").lower()
        if ("ncaa" in nm or "college" in nm) and "usa" in (t.get("categorySlug") or "").lower():
            n = (t.get("upcomingFixtures") or 0) + (t.get("futureFixtures") or 0)
            if not best or n > best[0]:
                best = (n, t.get("tournamentId"), t.get("tournamentName"))
    if best and best[0] > 0:
        st["ncaaf_tid"] = best[1]
        st["ncaaf_name"] = best[2]
        return best[1]
    return None


def refresh_fixtures(st, now, lg, lo, hi):
    """One billable /fixtures call for a league over [lo, hi] (dates), at most every 6 h per league."""
    last = tp((st.get("fx_last") or {}).get(lg))
    if last and now - last < timedelta(hours=6):
        return
    tid = tournament(st, now, lg)
    if not tid or not can_bill(st, now):
        return
    d = api("/fixtures", True, tournamentId=tid, **{"from": lo.strftime("%Y-%m-%d"), "to": hi.strftime("%Y-%m-%d")})
    bill(st, now)
    st.setdefault("fx_last", {})[lg] = iso(now)
    if isinstance(d, dict) and d.get("_error"):
        st.setdefault("errors", []).append(f"{iso(now)} fixtures {lg}: {d['_error']} {d['_body'][:120]}")
        return
    fx = st.setdefault("fixtures", {})
    for f in d if isinstance(d, list) else []:
        if not f.get("fixtureId"):
            continue
        fx[f["fixtureId"]] = {"lg": lg, "start": f.get("startTime"), "status": f.get("statusId"),
                              "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                              "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                              "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}


def find_fixture(st, b):
    lg, gs = b.get("league"), tp(b.get("game_start"))
    words = tb.toks(" ".join(t.get("name", "") for t in b.get("teams") or [])) or tb.toks(b.get("game"))
    best, sc = None, 0
    for fid, f in (st.get("fixtures") or {}).items():
        if f["lg"] != lg:
            continue
        fs = tp(f["start"])
        if gs and fs and abs((fs - gs).total_seconds()) > 36 * 3600:
            continue
        hits = (1 if tb.toks(f["p1"]) & words else 0) + (1 if tb.toks(f["p2"]) & words else 0)
        if hits > sc:
            best, sc = fid, hits
    return best if sc == 2 else None


def which_team(f, team_text):
    w = tb.toks(team_text)
    a, c = len(tb.toks(f["p1"]) & w), len(tb.toks(f["p2"]) & w)
    if a == c:
        abbr = (team_text or "").strip().lower()
        a += abbr in (f["p1"].lower().split()[-1:] or [""])
        c += abbr in (f["p2"].lower().split()[-1:] or [""])
    return "1" if a > c else "2" if c > a else None


# ------------------------------------------------------------------ history
def last_tick(ticks, before):
    best = None
    for t in ticks or []:
        ct = tp(t.get("createdAt"))
        if ct and ct <= before and (best is None or ct > best[0]):
            best = (ct, t)
    return best


def book_markets(h, bk):
    return ((((h or {}).get("bookmakers") or {}).get(bk) or {}).get("markets") or {}) if isinstance(h, dict) else {}


def two_way(pm, mid, before):
    """{outcome_name: (decimal, tick_time)} for a two-way market, last ticks at or before the given time."""
    m = pm.get(str(mid)) or {}
    out = {}
    for oid, o in (m.get("outcomes") or {}).items():
        lt = last_tick((o.get("players") or {}).get("0"), before)
        if lt and tb.num(lt[1].get("price")):
            out[oid] = (float(lt[1]["price"]), lt[0], tb.num(lt[1].get("limit")) or 0.0)
    return out


def novig_p(a, b):
    ia, ib = 1 / a, 1 / b
    return ia / (ia + ib)


def close_for(b, f, pm, mkmap, start, lg):
    """Pinnacle close fair win chance for the held side, plus how it was read."""
    pz = parsed(b)
    if not pz:
        return None, "bet text not parsed"
    sid = SPORT[lg]
    lab = lg
    if pz[0] == "ml":
        side = which_team(f, pz[1])
        if not side:
            return None, "team not matched"
        if pz[3]:
            side = "2" if side == "1" else "1"
        mid = ML_MARKET[sid]
        oc = {v: k for k, v in mkmap.get(mid, [0, 0, 0, {}])[3].items()} or {"1": str(mid), "2": str(int(mid) + 1)}
        tw = two_way(pm, mid, start)
        o1, o2 = oc.get("1"), oc.get("2")
        if o1 not in tw or o2 not in tw:
            return None, "no Pinnacle moneyline close"
        age = (start - min(tw[o1][1], tw[o2][1])).total_seconds() / 60
        p = novig_p(tw[o1][0], tw[o2][0])
        return {"p": p if side == "1" else 1 - p, "how": "moneyline", "age_min": round(age)}, None
    # spreads / totals: every Pinnacle line of that type for this fixture
    typ = "spreads" if pz[0] == "spread" else "totals"
    cands = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in pm:
            continue
        tw = two_way(pm, mid, start)
        nm = {v: k for k, v in outs.items()}
        a_id, b_id = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
        if a_id not in tw or b_id not in tw:
            continue
        age = (start - min(tw[a_id][1], tw[b_id][1])).total_seconds() / 60
        if age > FRESH_MIN:
            continue
        pa = novig_p(tw[a_id][0], tw[b_id][0])   # P(team 1 covers hcap) or P(over hcap)
        cands.append((hcap, pa, age, min(tw[a_id][2], tw[b_id][2])))
    if not cands:
        return None, f"no Pinnacle {typ} close"
    # Pinnacle's main line carries its biggest limit (alt lines are capped lower); ties: the most even price
    main = max(cands, key=lambda c: (c[3], -abs(c[1] - 0.5)))
    if typ == "totals":
        want, over = pz[2], pz[1] == "OVER"
        exact = next((c for c in cands if abs(c[0] - want) < 1e-9), None)
        if exact:
            return {"p": exact[1] if over else 1 - exact[1], "how": "own line", "age_min": round(exact[2])}, None
        ppt, po = main[0], main[1]
        p = po if over else 1 - po
        v = sm.half_point_value(lab, "tot", ppt, want, ppt)
        better = (want < ppt) if over else (want > ppt)
        return {"p": min(max(p + (v if better else -v), .01), .99), "how": f"main {ppt:g} moved to {want:g}",
                "age_min": round(main[2])}, None
    side = which_team(f, pz[1])
    if not side:
        return None, "team not matched"
    want = pz[2]
    if pz[3]:   # NO / short side of a 'Team -x' contract: the other team at +x
        side, want = ("2" if side == "1" else "1"), -want
    t1_line = want if side == "1" else -want          # the same bet stated as team 1's handicap
    exact = next((c for c in cands if abs(c[0] - t1_line) < 1e-9), None)
    if exact:
        p1 = exact[1]
        return {"p": p1 if side == "1" else 1 - p1, "how": "own line", "age_min": round(exact[2])}, None
    if lg == "NHL":
        return None, "puck line at a different number: not comparable"
    hp, p1 = main[0], main[1]
    my_pin_line = hp if side == "1" else -hp           # Pinnacle's main number from the bet team's side
    p = p1 if side == "1" else 1 - p1
    v = sm.half_point_value(lab, "spr", my_pin_line, want, my_pin_line)
    p += v if want > my_pin_line else -v
    return {"p": min(max(p, .01), .99), "how": f"main {my_pin_line:+g} moved to {want:+g}", "age_min": round(main[2])}, None


# ------------------------------------------------------------------ bot Novig orders (stale check)
def bot_novig_orders(days=10):
    """Bot Novig orders from its own 'Bets LIVE:' ledger rows: decision time, price used, line."""
    import email as em
    out = []
    M = ex.imap_open()
    try:
        for uid in ex.gsearch(M, f'subject:"Bets LIVE:" newer_than:{days}d'):
            typ, d = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not d or not d[0]:
                continue
            raw = d[0][1]
            subj = str(em.header.make_header(em.header.decode_header(em.message_from_bytes(raw).get("Subject") or "")))
            if not subj.startswith("Bets LIVE:"):
                continue
            txt = ex.body_text(raw)
            i = txt.rfind("LEDGER (machine-readable")
            if i < 0:
                continue
            try:
                rows, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
            except Exception:
                continue
            for r in rows:
                for lo in [r.get("live_order") or {}, r.get("live_rest") or {}] + [x or {} for x in r.get("live_more") or []]:
                    if lo.get("status") != "placed" or (lo.get("book") or "") != "novig" or not lo.get("order_id"):
                        continue
                    out.append({"order_id": str(lo["order_id"]), "key": r.get("key"), "decided_utc": r.get("decided_utc"),
                                "line": r.get("live_px_line"), "price": r.get("live_px_price_after_fee"),
                                "nv_at_decision": ((r.get("books_at_decision") or {}).get("novig") or {})})
    finally:
        M.logout()
    return out


def order_as_bet(o):
    sp, game, market, side = (str(o.get("key") or "").split("|") + [None] * 4)[:4]
    if not game or not market:
        return None
    if market == "total":
        if o.get("line") is None:
            return None
        bet = f"{side.title()} {float(o['line']):g}"
    elif o.get("line") is not None:
        bet = f"{side} {float(o['line']):+g}"
    else:
        bet = f"{side} ML"
    return {"id": "nvo|" + o["order_id"], "league": sp, "game": game, "bet": bet, "price": o.get("price"),
            "decided_utc": o.get("decided_utc")}


def novig_at(b, f, nm_pm, mkmap, when, lg):
    """Novig's own price (decimal) for the held side at that time, and its age in seconds; None if not found."""
    pz = parsed(b)
    if not pz:
        return None
    sid = SPORT[lg]
    if pz[0] == "ml":
        side = which_team(f, pz[1])
        if not side:
            return None
        tw = two_way(nm_pm, ML_MARKET[sid], when)
        oid = {v: k for k, v in mkmap.get(ML_MARKET[sid], [0, 0, 0, {}])[3].items()}.get(side)
        return (tw[oid][0], (when - tw[oid][1]).total_seconds()) if oid in tw else None
    typ = "spreads" if pz[0] == "spread" else "totals"
    if typ == "totals":
        want, name = pz[2], ("Over" if pz[1] == "OVER" else "Under")
    else:
        side = which_team(f, pz[1])
        if not side:
            return None
        want, name = (pz[2] if side == "1" else -pz[2]), side
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s == sid and t == typ and abs(hcap - want) < 1e-9 and mid in nm_pm:
            oid = {v: k for k, v in outs.items()}.get(name)
            m = (nm_pm.get(mid) or {}).get("outcomes", {}).get(oid) or {}
            lt = last_tick((m.get("players") or {}).get("0"), when)
            if lt:
                return float(lt[1]["price"]), (when - lt[0]).total_seconds()
    return None


# ------------------------------------------------------------------ ESPN fill
def espn_fill(st, now, max_days=12):
    """Settled tracker rows the tracker never pinned to a game: match them on ESPN (free) within 36 h of the settle
    or placed time, and take league, start and teams from there. At most max_days scoreboard dates per run."""
    todo = []
    for k, rec in st["bets"].items():
        s = rec["snap"]
        if s.get("game_start") or rec.get("espn_tries", 0) >= 3:
            continue
        t0 = tp(s.get("settled")) or tp(s.get("placed")) or tp(rec.get("first_seen"))
        if t0 and t0 > now - timedelta(days=45):
            todo.append((k, rec, t0))
    if not todo:
        return
    days = sorted({(t0 - timedelta(days=dd)).astimezone(ET).replace(hour=12, minute=0, second=0, microsecond=0)
                   for _, _, t0 in todo for dd in (0, 1)}, reverse=True)[:max_days]
    games = tb.espn_games(days)
    for k, rec, t0 in todo:
        s = rec["snap"]
        g = tb.match_game(s, games, t0)
        if g and len(g["teams"]) == 2:
            a, h = sorted(g["teams"], key=lambda t: t["home"])
            s["league"] = s.get("league") or g["league"]
            s["game_start"] = g["start"]
            s["teams"] = [{"name": a["full"]}, {"name": h["full"]}]
            s["espn_filled"] = True
        else:
            rec["espn_tries"] = rec.get("espn_tries", 0) + 1


# ------------------------------------------------------------------ main
def lane_stats(rows):
    n = len(rows)
    if not n:
        return "-"
    avg = sum(r["clv"] for r in rows) / n
    beat = sum(1 for r in rows if r["clv"] > 0)
    return f"n {n}, avg CLV {100 * avg:+.2f}%, beat close {beat}/{n}"


def main():
    now = datetime.now(timezone.utc)
    if not KEY or not tb.PASS:
        print("CLV ledger: ODDSPAPI_KEY or TRACKER_PASSPHRASE not set; skipped")
        return
    try:
        st = tb.dec(json.load(open(STATE)))
    except Exception:
        st = {}
    st.setdefault("bets", {})
    st.setdefault("billable", {})
    try:
        tracker = tb.dec(json.load(open(tb.STATE))).get("bets") or {}
    except Exception:
        tracker = {}
    # 1) capture: keep each bet's first-seen price/stake/payout (a later settlement row can drop them for losses)
    for k, b in tracker.items():
        rec = st["bets"].setdefault(k, {"first_seen": iso(now)})
        snap = rec.setdefault("snap", {})
        for f in ("book", "game", "bet", "flip", "league", "source", "teams", "game_start", "placed", "settled"):
            if b.get(f) not in (None, "", []):
                snap[f] = b[f]
        for f in ("price", "stake", "to_pay"):
            if b.get(f) not in (None, "") and snap.get(f) in (None, ""):
                snap[f] = b[f]
        if b.get("result"):
            snap["result"] = b["result"]
    # 1b) tracker rows with no game attached (older settled rows): find the game on ESPN (free) near when it settled
    try:
        espn_fill(st, now)
    except Exception as e:
        st.setdefault("errors", []).append(f"{iso(now)} espn fill: {type(e).__name__}")
    # 2) bot Novig orders for the stale check
    nvo = []
    try:
        nvo = [x for x in (order_as_bet(o) for o in bot_novig_orders()) if x]
    except Exception as e:
        st.setdefault("errors", []).append(f"{iso(now)} novig orders: {type(e).__name__}")
    for o in nvo:
        st.setdefault("novig_checks", {}).setdefault(o["id"], {"snap": o})
    mkmap = load_markets(st, now)
    if not st.get("rescored_v2"):   # v1 freshness rule could pick an alt line as main: score everything again once
        for rec in st["bets"].values():
            for f in ("clv", "close_p", "eff_am", "close_am", "how", "age_min", "scored", "done", "tries", "why", "fixture"):
                rec.pop(f, None)
        st["rescored_v2"] = iso(now)
    # 3) which leagues need fixtures
    pend = []
    for k, rec in st["bets"].items():
        s = rec["snap"]
        if rec.get("clv") is not None or rec.get("done"):
            continue
        gs = tp(s.get("game_start"))
        if not gs or now < gs + timedelta(minutes=SCORE_AFTER_MIN):
            continue
        pend.append((k, rec))
    for k, rec in (st.get("novig_checks") or {}).items():
        if rec.get("done"):
            continue
        pend.append((k, rec))
    need = {}
    for k, rec in pend:
        s = rec["snap"]
        lg = s.get("league")
        if lg not in SPORT:
            continue
        if rec.get("fixture") or find_fixture(st, s):
            continue
        d0 = max(tp(s.get("game_start") or s.get("decided_utc")) or now, now - timedelta(days=14))   # keep the call small
        lo, hi = need.get(lg, (d0, d0))
        need[lg] = (min(lo, d0), max(hi, d0))
    for lg, (lo, hi) in need.items():
        refresh_fixtures(st, now, lg, (lo - timedelta(days=1)).astimezone(ET), (hi + timedelta(days=1)).astimezone(ET))
    # 4) score: free history calls, one per fixture and book
    hist = {}
    new_scored = 0
    for k, rec in pend:
        s = rec["snap"]
        lg = s.get("league")
        if lg not in SPORT:
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = f"league {lg or 'unknown'} not covered"
            if lg or rec["tries"] >= MAX_TRIES:
                rec["done"] = True
            continue
        fid = rec.get("fixture") or find_fixture(st, s)
        if not fid:
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = "no OddsPapi fixture matched"
            if rec["tries"] >= MAX_TRIES:
                rec["done"] = True
            continue
        f = (st.get("fixtures") or {}).get(fid)
        if not f:
            rec.pop("fixture", None)
            continue
        rec["fixture"] = fid
        start = tp(f["start"]) or tp(s.get("game_start"))
        is_nv = k.startswith("nvo|")
        if not is_nv and now < start + timedelta(minutes=SCORE_AFTER_MIN):
            continue
        bk = "novig" if is_nv else "pinnacle"   # one book per call: a bad slug never costs the Pinnacle read
        if (fid, bk) not in hist and len(hist) >= MAX_HIST:
            continue   # backfill spreads over runs (history throttles at ~8 s a call)
        if (fid, bk) not in hist:
            hist[(fid, bk)] = api("/historical-odds", False, fixtureId=fid, bookmakers=bk)
        h = hist[(fid, bk)]
        if isinstance(h, dict) and h.get("_error"):
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = f"history HTTP {h['_error']}"
            continue
        if is_nv:
            when = tp(s.get("decided_utc"))
            got = novig_at(s, f, book_markets(h, "novig"), mkmap, when, lg) if when else None
            if got:
                rec["novig_price_then"] = dec_to_am(got[0])
                rec["quote_age_s"] = round(got[1])
                rec["bot_price"] = s.get("price")
                rec["done"] = True
            else:
                rec["tries"] = rec.get("tries", 0) + 1
                rec["why"] = "no Novig tick found at that line"
                if rec["tries"] >= MAX_TRIES:
                    rec["done"] = True
            continue
        pl = tp(s.get("placed"))
        if pl and pl > start:
            rec["done"], rec["why"] = True, "placed after start (in-play): not scored"
            continue
        c, why = close_for(s, f, book_markets(h, "pinnacle"), mkmap, start, lg)
        d = eff_dec(s)
        if c and d:
            rec["clv"] = round(c["p"] * d - 1, 4)
            rec["close_p"] = round(c["p"], 4)
            rec["eff_am"] = dec_to_am(d)
            rec["close_am"] = tb.p_to_american(c["p"])
            rec["how"], rec["age_min"], rec["scored"] = c["how"], c["age_min"], iso(now)
            rec.pop("why", None)
            new_scored += 1
        else:
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = why or "no price on the bet"
            if rec["tries"] >= MAX_TRIES or (why and ("not parsed" in why or "not comparable" in why)) or not d:
                rec["done"] = True
    # 5) report
    scored = sorted([dict(r, id=k) for k, r in st["bets"].items() if r.get("clv") is not None], key=lambda r: r.get("scored") or "")
    bot = [r for r in scored if (r["snap"].get("source") or "") == "bot"]
    man = [r for r in scored if (r["snap"].get("source") or "") != "bot"]
    alert = len(bot) >= 50 and sum(r["clv"] for r in bot[-50:]) / 50 < 0
    today = now.astimezone(ET).strftime("%Y-%m-%d")
    want_email = os.environ.get("EMAIL_NOW") == "1" or (now.astimezone(ET).hour >= 9 and st.get("emailed") != today) \
        or (alert and st.get("alerted") != today)
    if want_email:
        L = ["LIVE CLV LEDGER - your real bets vs Pinnacle's true close (OddsPapi history: last tick before start, no-vig,",
             "at the bet's own line when Pinnacle had it). CLV = close win chance x your after-fee payout - 1.", ""]
        if alert:
            L += ["*** KILL-SWITCH ALERT: last 50 scored bot bets average CLV below 0 (alert only; no pause - Peter decides) ***", ""]
        L.append(f"ALL scored: {lane_stats(scored)}")
        L.append(f"  bot: {lane_stats(bot)} | rolling 50: {lane_stats(bot[-50:])}")
        L.append(f"  Peter/other: {lane_stats(man)} | rolling 50: {lane_stats(man[-50:])}")
        for lab, keyf in (("by book", lambda r: r["snap"].get("book")), ("by sport", lambda r: r["snap"].get("league")),
                          ("by source tag", lambda r: r["snap"].get("source"))):
            g = {}
            for r in scored:
                g.setdefault(keyf(r) or "?", []).append(r)
            L.append(f"  {lab}: " + "; ".join(f"{k2} {lane_stats(v)}" for k2, v in sorted(g.items())))
        how = {}
        for r in scored:
            how["own line" if r["how"] in ("own line", "moneyline") else "moved to your number"] = \
                how.get("own line" if r["how"] in ("own line", "moneyline") else "moved to your number", 0) + 1
        L.append(f"  close read: {how}")
        L += ["", "LAST 30 SCORED (newest first):"]
        for r in scored[::-1][:30]:
            s = r["snap"]
            L.append(f"  {(s.get('game_start') or '')[:10]} {s.get('league')} {s.get('book')} [{s.get('source')}] "
                     f"{s.get('bet')} | you {r['eff_am']:+d} after fee, close fair {r['close_am']:+d} ({r['how']}, "
                     f"tick {r['age_min']} min pre-start) -> CLV {100 * r['clv']:+.1f}%" if r.get("eff_am") and r.get("close_am") else
                     f"  {s.get('bet')}: CLV {100 * r['clv']:+.1f}%")
        un = [(k, r) for k, r in st["bets"].items() if r.get("done") and r.get("clv") is None]
        L += ["", f"NOT SCORED (counted, never dropped): {len(un)}"]
        reasons = {}
        for k, r in un:
            reasons[r.get("why") or "?"] = reasons.get(r.get("why") or "?", 0) + 1
        L += [f"  {v} x {k2}" for k2, v in sorted(reasons.items(), key=lambda x: -x[1])]
        waiting = sum(1 for k, r in st["bets"].items() if not r.get("done") and r.get("clv") is None)
        L.append(f"  still waiting (game not started yet or retrying): {waiting}")
        wr = {}
        for k, r in st["bets"].items():
            if not r.get("done") and r.get("clv") is None:
                w = r.get("why") or ("no game found for the tracker row (ESPN)" if not r["snap"].get("game_start") else
                                     "game not started" if tp(r["snap"]["game_start"]) > now - timedelta(minutes=SCORE_AFTER_MIN) else "queued")
                wr[w] = wr.get(w, 0) + 1
        L += [f"    {v} x {k2}" for k2, v in sorted(wr.items(), key=lambda x: -x[1])]
        nc = [r for r in (st.get("novig_checks") or {}).values() if r.get("novig_price_then") is not None]
        L += ["", f"NOVIG STALE CHECK (bot Novig orders: the price the bot used vs Novig's own price in OddsPapi history at that "
                  f"moment): {len(nc)} checked"]
        for r in nc[-20:]:
            s = r["snap"]
            bp = r.get("bot_price")
            gap = (tb.american_to_p(r["novig_price_then"]) - tb.american_to_p(bp)) * 100 if bp not in (None, "") else None
            L.append(f"  {(s.get('decided_utc') or '')[:16]} {s.get('league')} {s.get('bet')}: bot used {bp}, Novig then "
                     f"{r['novig_price_then']:+d} (quote {r['quote_age_s'] // 60} min old)"
                     + (f", gap {gap:+.1f}c" if gap is not None else ""))
        nnc = [r for r in (st.get("novig_checks") or {}).values() if r.get("done") and r.get("novig_price_then") is None]
        if nnc:
            L.append(f"  not found: {len(nnc)}")
        L += ["", f"OddsPapi calls this run: billable {STATS['billable']}, free {STATS['free']}; billable this month "
                  f"{st['billable'].get(month_key(now), 0)} of cap {CAP} (plan 250)."]
        if st.get("errors"):
            L.append("Errors (last 5): " + " | ".join(st["errors"][-5:]))
        ex.send(("Bets CLV LEDGER ALERT" if alert else "Bets CLV LEDGER") + f" {today}", "\n".join(L))
        st["emailed"] = today
        if alert:
            st["alerted"] = today
    # 6) save (encrypted), trim
    cut = iso(now - timedelta(days=60))
    st["bets"] = {k: v for k, v in st["bets"].items() if (v.get("first_seen") or "") >= cut}
    st["novig_checks"] = {k: v for k, v in (st.get("novig_checks") or {}).items() if (v["snap"].get("decided_utc") or "") >= cut}
    st["fixtures"] = {k: v for k, v in (st.get("fixtures") or {}).items() if (v.get("start") or "") >= iso(now - timedelta(days=12))}
    st["errors"] = (st.get("errors") or [])[-20:]
    os.makedirs("clv", exist_ok=True)
    json.dump(tb.enc(st), open(STATE, "w"))
    print(f"CLV ledger: bets {len(st['bets'])}, scored {len(scored)} (+{new_scored}), "
          f"calls billable {STATS['billable']} free {STATS['free']}")   # counts only


if __name__ == "__main__":
    main()

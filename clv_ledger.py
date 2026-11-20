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
import collections
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import clv_stale as cstale     # leaf module, tracker_build only - safe to import here
import fixture_match as fxm   # leaf module, tracker_build only - the SHARED fixture matcher
import credit_gate as cg       # leaf module, stdlib only - safe to import here
SIDE_EV = ({}, [])
SIDE_LOG = collections.Counter()
import executor as ex
import sharp_monitor as sm
import tracker_build as tb

BASE = "https://api.oddspapi.io/v4"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
FREE_KEY = (os.environ.get("ODDSPAPI_FREE_KEY") or "").strip()   # Nov 3: free-account key, history only
STATE = "clv/state.enc"
MKFILE = "clv/markets.json"
ET = tb.ET
CAP = int(os.environ.get("CLV_MONTH_CAP", "") or "1000")   # Nov 4: paid plan has 5,000 a month (was 150 for the 250 free plan)
# Nov 5 (Peter, approved): these two WERE independent constants - the fixture cache pruned at 12 days while the fixture
# FETCH window floored at 14. 12 inside 14 meant the cache deleted fixtures the fetcher still considered in range, so a
# bet older than ~12 days could neither find a cached fixture nor fetch one (the max() below moves the window off the
# game date rather than shrinking it). Bets are kept 60 days, so the ledger retained bets five times longer than any
# means of scoring them. Derived now, so the two can never drift apart again: the cache must OUTLIVE the window.
FETCH_DAYS = 45                  # Nov 5 (Peter, explicit release): was 14. The /fixtures request is built as
                                 #   d0 = max(game_start, now - FETCH_DAYS)
                                 # so at 14 the window CLAMPED to now-14d and never asked for an older game's
                                 # own date - those fixtures could not be fetched at any price. 45 centres the
                                 # window on the game date across the classified scope (earliest 2026-10-04)
                                 # while staying bounded, so one stale row cannot widen it without limit.
FX_KEEP_DAYS = FETCH_DAYS + 14   # fixture cache retention - always longer than the window, never inside it
SPORT = {"NBA": 11, "NFL": 14, "NCAAF": 14, "NHL": 15}
TOURN = {"NBA": 132, "NFL": 31, "NHL": 234}           # NCAAF looked up once (the probe's 850 was wrong)
ML_MARKET = {11: "111", 14: "141", 15: "151"}         # Winner incl. overtime (hockey: incl. OT and penalties)
# Nov 16 (Peter, approved): NCAAB is SCORED with the same certified close as every other league.
# SPORT itself is unchanged so no other job's league list moves. NCAAB fixtures are CACHE-ONLY:
# a fixture lookup for NCAAB is a paid call and is not approved, so this ledger never asks for one;
# a row whose game is in no cached store waits with that reason and burns no retry.
SCORE_SPORT = dict(SPORT, NCAAB=11)
CACHE_ONLY_FX = frozenset({"NCAAB"})
# Nov 17 (Peter, "We need to fix it"): NCAAB gets ONE capped paid /fixtures call per ET day, only when an NCAAB row is
# actually waiting for a fixture that no store holds, always on the verified tournament (no tournament search), inside
# the monthly cap. Everything else about the cache-only rule is unchanged.
NCAAB_DAILY_FX_CAP = 1
# Nov 17 (Peter, OK): a SECOND daily NCAAB lookup, basketball-wide (sportId 11), only for a waiting NCAAB row whose game
# day IS in the regular-season list but whose game is not (OddsPapi files some early-season events separately).
# One call per ET day, never the same game date twice. Professional and women's competitions are not stored.
NCAAB_WIDE_DAILY_CAP = 1
NOT_MENS_COLLEGE_TIDS = frozenset({132, 486, 875, 1329, 1580, 2382, 14458, 15822, 23881, 34992, 38949, 40401, 41126,
                                   45587, 46736, 53592, 21384, 33946, 33948, 34006, 34008, 40443})
NCAAB_REOPEN_START_ET = "2026-11-12"   # report_sections.START_ET: the four settled bot rows Peter named
NCAAB_REOPEN_EXPECT = 4
# Peter, Nov 16 16:07: the NCAAB tournament must be verified as NCAA Division I men's basketball from
# authoritative metadata BEFORE any paid fixture call. tournament()'s "most upcoming NCAA" pick is not
# verification, and it returned no id on both prior attempts (ncaab-probe, Nov 14). Until a verified id
# is recorded here, the one-time fixture recovery is BLOCKED and spends nothing.
NCAAB_VERIFIED_TID = 648   # Peter, Nov 16 16:22: "NCAA, Regular Season" (slug ncaa-regular-season, USA) - his explicit pick
FRESH_MIN = 24 * 60  # history stores CHANGES: a line's last pre-start tick is its price at the start unless it is a day old
SCORE_AFTER_MIN = 10  # score a bet this long after its listed start
MAX_TRIES = 8
# Stage 2 flag (Peter, Nov 13): OFF by default. On, the email gains a selection-level section
# beside the per-fill headline; it never replaces it, so the switch is reversible by env alone
# and no stored figure changes either way.
SELECTION_MODE = (os.environ.get("CLV_SELECTION_MODE", "") or "off").strip().lower() == "on"
MAX_HIST = 60        # free history calls per run
BACKLOG_AFTER_DAYS = 3   # Nov 19: older than this is historical recovery, not today's grading
BACKLOG_MAX = 40         # historical rows offered per run - bounded so recovery cannot starve new fills
CALLS = []
STATS = {"billable": 0, "free": 0}


# ------------------------------------------------------------------ OddsPapi
HIST_GAP = [float(os.environ.get("HIST_GAP", "") or "5.2")]   # Nov 2 (Peter: "run faster"): adaptive history spacing
RL_TRIES = int(os.environ.get("RL_TRIES", "") or "12")   # Nov 3: rate-limit retries per call (about 4-12 min at most)
HIST_MIN = float(os.environ.get("HIST_GAP_MIN", "") or "5.2")   # Nov 2: spacing eases back down, never below OddsPapi's documented
# 5,000 ms cooldown on /historical-odds (docs: get-historical-odds; a 304 counts too)


_KEY_LOCKS, _GAPS = {}, {}   # Nov 4: history spacing is per key (each key has its own OddsPapi cooldown)


class GateRefused(RuntimeError):
    """The shared credit gate refused a paid request. Distinct from a network or provider error so
    callers can tell 'we chose not to spend' from 'the provider failed'."""


def api(path, billable, apikey=None, **params):
    # Nov 3 21:30: the paid plan answers 403 RESTRICTED_ACCESS "Restricted bookmakers: pinnacle" on /historical-odds (it sells
    # "Pinnacle +30 sec", a different product), so ALL history goes through the free-account key when it is set; the paid
    # key keeps every billable call. The free key never makes a billable call, so its 250 can never run out.
    # Nov 4 (Wenzel, OddsPapi): the paid plan's Pinnacle history slug is "pinnacle+30"; hist_cache sends Pinnacle / Hard Rock
    # history on the paid key with that slug (apikey=KEY passed explicitly), so the two keys run side by side.
    if apikey is None and path == "/historical-odds" and FREE_KEY:
        apikey = FREE_KEY
    k = apikey or KEY
    # THE CREDIT GATE. One chokepoint: every paid OddsPapi request in the system arrives here with
    # billable=True, and free ones (/account, /historical-odds) bypass it untouched. In shadow mode
    # take() always returns True and only records what it would have refused, so this blocks
    # nothing until ODDSPAPI_GATE=enforce. Fail closed: a False is a refusal, not a retry.
    if billable and not cg.take(1, purpose=path.lstrip("/"), path=path):
        raise GateRefused(f"credit gate refused {path}: no budget left this period")
    if path != "/historical-odds":
        return _api(path, billable, k, params)
    import threading
    lk = _KEY_LOCKS.setdefault(k, threading.Lock())
    with lk:   # one history call at a time per key, spaced by that key's own gap
        return _api(path, billable, k, params)


def _api(path, billable, k, params):
    params["apiKey"] = k
    q = urllib.parse.urlencode({x: v for x, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"Accept": "application/json", "User-Agent": "sharp-monitor-clv"})
    hist = path == "/historical-odds"
    if hist:
        _GAPS.setdefault(k, HIST_GAP[0])
    # history throttles (429 seen at ~1 s spacing): start at HIST_GAP s, back off 1.5x on every 429 (max 15 s)
    time.sleep(_GAPS[k] if hist else 1.1)
    STATS["billable" if billable else "free"] += 1
    # Nov 3 20:30 (Peter: build the one-downloader guard, "as long as it doesnt stop the download"): jobs sharing the key
    # no longer lose games to RATE_LIMITED. A rate-limit 429 waits (Retry-After, at least 20 s, at most 60 s) and retries
    # up to RL_TRIES times while the history spacing widens, so two jobs settle at the key's shared rate instead of
    # dropping data. A quota 429 (REQUEST_LIMIT_EXCEEDED) is never retried. Counts only in the log.
    for attempt in range(RL_TRIES):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                CALLS.append((path, r.status))
                if hist:   # a clean call eases the spacing back toward HIST_MIN (it only grew before)
                    _GAPS[k] = max(HIST_MIN, _GAPS[k] * 0.95)
                    if k == (FREE_KEY or KEY):
                        HIST_GAP[0] = _GAPS[k]   # the logged spacing = the free key's
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code == 429 and "REQUEST_LIMIT" not in body and attempt < RL_TRIES - 1:
                STATS["rate_waits"] = STATS.get("rate_waits", 0) + 1
                if hist:
                    _GAPS[k] = min(_GAPS[k] * 1.5, 15.0)
                    if k == (FREE_KEY or KEY):
                        HIST_GAP[0] = _GAPS[k]
                try:
                    ra = float(e.headers.get("Retry-After") or 0)
                except Exception:
                    ra = 0.0
                time.sleep(min(60.0, max(20.0, ra)))
                continue
            CALLS.append((path, e.code))
            return {"_error": e.code, "_body": body}
        except Exception as e:
            CALLS.append((path, type(e).__name__))
            return {"_error": type(e).__name__, "_body": str(e)[:200]}


PERIOD_DAY = int(os.environ.get("ODDSPAPI_PERIOD_DAY", "") or "3")


def month_key(now):
    """The PROVIDER'S SUBSCRIPTION PERIOD, not the calendar month (Peter, item 3, 9 Nov).

    The OddsPapi period runs the 3rd to the 3rd - Nov 3 to Dec 3 - so the provider's usage resets
    on the 3rd while every counter here used to reset on the 1st. credits.py has documented that
    mismatch since 5 Nov: for two days each period a fresh local counter read zero against usage
    the provider was still counting, and the last two days of a period were charged to the next
    one. Keyed by the period's START date so local and provider figures line up directly."""
    y, m = now.year, now.month
    if now.day < PERIOD_DAY:
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return f"{y:04d}-{m:02d}-{PERIOD_DAY:02d}"


def used_this_period(st, now):
    """Recorded usage for the current period, carrying the LEGACY calendar-month figure forward.

    Without this fallback, changing the key would make every existing counter read zero and
    silently RESET month-to-date usage - exactly what Peter said not to do. The legacy value is
    read, never deleted or rewritten."""
    b = st.setdefault("billable", {})
    k = month_key(now)
    if k in b:
        return b[k]
    legacy = b.get(now.strftime("%Y-%m"))
    return legacy if legacy is not None else 0


def can_bill(st, now, n=1):
    return used_this_period(st, now) + n <= CAP


def bill(st, now, n=1):
    """Counts into the PERIOD key, seeded once from the legacy calendar-month figure so the
    carried-forward usage is preserved rather than restarting at n."""
    b = st.setdefault("billable", {})
    k = month_key(now)
    if k not in b:
        b[k] = b.get(now.strftime("%Y-%m"), 0)
    b[k] = b[k] + n


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


def eff_dec_src(b):
    """(after-fee decimal, which input produced it, fee model). Mirrors eff_dec branch for branch - eff_dec is
    unchanged. Phase 1 / P1-B (Peter, Nov 14: "Approves"): recorded at scoring so the entry price is auditable."""
    book = b.get("book")
    st, pay = tb.num(b.get("stake")), tb.num(b.get("to_pay"))
    if st and pay and pay > st:
        src = "stake_to_pay"
    elif b.get("price_af") not in (None, ""):
        src = "price_af"
    elif b.get("price") not in (None, ""):
        src = "price_px_fee" if book == "ProphetX" else "price"
    else:
        return None, None, None
    if book == "Kalshi":
        fee = "kalshi_unresolved"            # executed_clv: whether Kalshi's cost is gross or net of fee is NOT settled
    elif book == "ProphetX":
        fee = "px_settle_2pct"               # 2% of net winnings at settlement, applied in to_pay or here
    elif src == "price_af":
        fee = "bot_fill_after_fee"
    elif book in ("Novig", "Polymarket US") and src == "stake_to_pay":
        fee = "fee_inclusive_cost_payout"
    else:
        fee = "book_payout_as_recorded"
    return eff_dec(b), src, fee


def eff_dec(b):
    """The bet's after-fee decimal price: what it pays back per $1 staked."""
    st, pay = tb.num(b.get("stake")), tb.num(b.get("to_pay"))
    if st and pay and pay > st:
        return pay / st
    if b.get("price_af") not in (None, ""):   # Nov 2 (Peter): after-fee price from the bot's own fill record
        return am_to_dec(b["price_af"])
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



# ------------------------------------------------------------------ verified side from the registry (Peter, 16 Nov)
def registry_side(row_id, snap, pm_links, orders):
    """(side_text, why). A Polymarket US settled row records only the line ("-15.50"), so its side was never known.
    The side is taken from the bot's own registry claim ONLY through an exact chain, failing closed at every step:
      row market slug -> exactly ONE venue-confirmed order id (pm_links, written by pmus-activity's read-back)
      -> exactly ONE registry order with that id -> its claim: same league, a spread/side market, teams that match the
      row's game, and an order line EQUAL to the row's line. Pure: pm_links {order_id: slug}, orders [registry rows]."""
    m = re.search(r"\[([^\]]+)\]", str(row_id or ""))
    if not str(row_id or "").startswith("pm|") or not m:
        return None, "not a Polymarket row with a market slug"
    oids = [o for o, sl in (pm_links or {}).items() if "#" not in o and sl == m.group(1)]
    if len(oids) != 1:
        return None, f"{len(oids)} venue-confirmed orders on this market (need exactly 1)"
    def _lo(o):
        x = o.get("live_order")
        return x if isinstance(x, dict) else {}
    hits = {(o.get("key"), o.get("decided_utc") or o.get("et_day")): o for o in orders or []
            if str(_lo(o).get("order_id") or "") == oids[0]}
    if len(hits) != 1:
        return None, f"{len(hits)} registry orders carry this order id (need exactly 1)"
    o = next(iter(hits.values()))
    parts = [p for p in str(o.get("key") or "").split("|") if p]
    if parts and parts[0] in ("rule", "rules", "board", "r1", "lane2"):
        parts = parts[1:]
    if len(parts) < 4:
        return None, "registry claim key is incomplete"
    lg, teams, mkt, side = parts[0], parts[1], parts[2].lower(), parts[3]
    if lg.upper() != str(snap.get("league") or "").upper():
        return None, "registry league differs from the row's league"
    if mkt not in ("side", "spread"):
        return None, f"registry market '{mkt}' is not a spread"
    if side.lower() in ("over", "under") or not any(c.isalpha() for c in side):
        return None, "registry side is not a team"
    rt = {t for t in re.split(r"[+_\s]+", teams.lower()) if t}
    gt = tb.toks(snap.get("game")) - tb.WEAK
    if not rt or not (rt <= gt or gt <= rt or len(rt & gt) >= 2):
        return None, "registry teams do not match the row's game"
    # The row's bet text is a bare signed line ("-15.50"); anything else is not this case.
    bt = str(snap.get("bet") or "").strip()
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", bt):
        return None, "the row's bet text is not a bare line"
    oline = o.get("fill_line") if o.get("fill_line") is not None else o.get("alert_line")
    # LONG the "-x" contract holds that line; SHORT it holds the other team at +x. The claim (the bot's own team and
    # line) must say exactly that: equal to the row's line when long, its exact negation when short. Anything else is
    # a contradiction and is refused. The bet scored is the CLAIM's team at the CLAIM's line - nothing inferred.
    team = side.replace("_", " ")
    mdef = (pm_links or {}).get(oids[0] + "#market")
    vdir0 = (pm_links or {}).get(oids[0] + "#intent")
    if isinstance(mdef, dict) and isinstance(mdef.get("market"), dict):
        # 16 Nov (Peter): with the venue's market definition on file, the held side is a FACT: the side whose long flag
        # matches the venue's own BUY_LONG/BUY_SHORT. It must be the claim's team (and the other side must not be),
        # its own signed line must equal the claim's line, and the market must be a spread.
        hb, hw = held_from_market(mdef["market"], vdir0, team, oline)
        # the tracker's settlement row must be the same market: its bare line is one side's label (same magnitude)
        if hb and abs(abs(float(bt)) - abs(float(hb.rsplit(" ", 1)[1]))) > 1e-9:
            return None, "the settlement row's line is not this market's line"
        return hb, hw
    # Direction: the VENUE's own order record (BUY_LONG / BUY_SHORT, saved by pmus-activity's read-back) decides.
    # Settled Polymarket rows carry no direction from the venue, so the tracker's flag is used only when the venue's
    # is absent - and then any disagreement with the claim fails closed below.
    vdir = (pm_links or {}).get(oids[0] + "#intent")
    short = (vdir == "SHORT") if vdir in ("LONG", "SHORT") else bool(snap.get("flip"))
    try:
        want = -float(bt) if short else float(bt)
        if oline is None or abs(float(oline) - want) > 1e-9:
            return None, ("the order's line is not the negation of the row's line (short)" if short
                          else "the order's line does not equal the row's line")
    except (TypeError, ValueError):
        return None, "line unreadable"
    team = side.replace("_", " ")
    return f"{team} {float(oline):+g}", "registry claim via Polymarket order read-back"



def _side_text(sd):
    t = sd.get("team")
    parts = [str(v) for v in (t.values() if isinstance(t, dict) else [t]) if isinstance(v, str)]
    return " ".join(parts + [str(sd.get("description") or ""), str(sd.get("identifier") or "")])


def held_from_market(mk, vdir, claim_team, claim_line):
    """(bet_text, why) from the venue's market definition. Pure. Fails closed on any ambiguity or contradiction."""
    if vdir not in ("LONG", "SHORT"):
        return None, "venue direction unknown"
    mtype = " ".join(str(mk.get(k) or "") for k in ("sportsMarketType", "marketType", "type")).lower()
    if "spread" not in mtype:
        return None, f"market is not a spread ({mtype.strip() or 'type absent'})"
    sides = [x for x in mk.get("marketSides") or [] if isinstance(x, dict)]
    if len(sides) != 2:
        return None, f"market has {len(sides)} sides (need 2)"
    held = [x for x in sides if bool(x.get("long", True)) == (vdir == "LONG")]
    if len(held) != 1:
        return None, "the venue direction does not single out one side"
    held, other = held[0], next(x for x in sides if x is not held[0])
    ct = tb.toks(claim_team) - tb.WEAK
    ht, ot = tb.toks(_side_text(held)) - tb.WEAK, tb.toks(_side_text(other)) - tb.WEAK
    if not ct or not (ct <= ht):
        return None, "the held side is not the claim's team"
    if ct <= ot:
        return None, "the claim's team names both sides (ambiguous)"
    mm = re.search(r"([+-]\d+(?:\.\d+)?)", str(held.get("description") or ""))
    hl = float(mm.group(1)) if mm else None
    if hl is None:
        ln = mk.get("line")
        try:
            hl = (float(ln) if held.get("long", True) else -float(ln)) if ln is not None else None
        except (TypeError, ValueError):
            hl = None
    try:
        if hl is None or claim_line is None or abs(hl - float(claim_line)) > 1e-9:
            rel = ("held line unreadable" if hl is None else "claim line absent" if claim_line is None else
                   "same size, opposite sign" if abs(abs(hl) - abs(float(claim_line))) < 1e-9 else "different size")
            src = "from the side's label" if mm else "from the market line"
            return None, f"the held side's line does not equal the claim's line ({rel}; held line {src})"
    except (TypeError, ValueError):
        return None, "line unreadable"
    return f"{claim_team} {hl:+g}", "venue market definition + venue direction + registry claim agree"

def load_side_evidence():
    """(pm_links, orders) from the encrypted reporting files. ({}, []) if either is absent - then nothing changes."""
    try:
        links = tb.dec(json.load(open("reporting/pm_links.enc"))) or {}
        import reporting_ledger as rl
        cur = rl.latest(rl.load_ledger())
        orders = [d for (k, _i), (_f, d) in cur.items() if k == "order"]
        return links, orders
    except Exception as e:
        SIDE_LOG[f"evidence unreadable ({type(e).__name__})"] += 1
        return {}, []

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
    try:
        d = api("/markets", True)
    except GateRefused:
        return (mk or {}).get("m") or {}      # same fallback as "cannot bill": the stale list

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
    if lg == "NCAAB":   # Nov 6 (history cache + model lab only; NCAAB stays out of SPORT so no other job changes)
        if st.get("ncaab_tid"):
            return st["ncaab_tid"]
        if not can_bill(st, now):
            return None
        try:
            ts = api("/tournaments", True, sportId=11)
        except GateRefused:
            return None                       # same as "cannot bill": no tournament id this run
        bill(st, now)
        best = None
        for t in ts if isinstance(ts, list) else []:
            nm = (t.get("tournamentName") or "").lower()
            if "ncaa" in nm and "women" not in nm and "usa" in (t.get("categorySlug") or "").lower():
                n = (t.get("upcomingFixtures") or 0) + (t.get("futureFixtures") or 0)
                if not best or n > best[0]:
                    best = (n, t.get("tournamentId"), t.get("tournamentName"))
        if best and best[0] > 0:
            st["ncaab_tid"] = best[1]
            return best[1]
        return None
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


FX_LOG = []        # one line per league per run: what was called, what was refused, and why
ALT_FX = {}        # fixtures from the stores other jobs maintain; filled once per run in main()
ALT_SRC = {}       # fixture id -> which store it came from, for the audit trail


def refresh_fixtures(st, now, lg, lo, hi, allow_extra=False):
    """One billable /fixtures call for a league over [lo, hi] (dates), at most every 6 h per league.

    Returns True only when a FRESH lookup actually reached OddsPapi, so the caller can tell the
    difference between "we looked and the game is not there" and "we never looked". Nov 5 (Peter):
    a run that made no lookup must not burn a retry - see the tries accounting in main().

    Stage 4 (Peter, Nov 13): "Allow one additional fixture refresh per league per evening when
    unresolved games fall beyond the existing cache." allow_extra permits exactly one override of
    the 6 h cooldown per league per ET DAY, and only when the caller has established that a
    pending game starts later than anything the cache holds for that league - which is the Nov 12
    failure: three selections sat unscored with "no fixture yet - no fresh lookup this run (6 h
    cooldown), retry not counted" while NBA's newest cached fixture started an hour before the
    games in question and the league had been fetched 2 h earlier.

    NOTE ON THE WINDOW, corrected from my own earlier claim: the window is NOT too narrow. hi
    comes from the pending rows themselves and main() adds a day to it, so a row whose game starts
    tonight already widens the window to cover tonight. The cooldown alone was the blocker, so the
    cooldown alone is overridden here. If an extra call still does not return the fixture, the
    cause is OddsPapi's own coverage of that window and FX_LOG will say so rather than imply a
    window bug that the dates do not support.

    COST CONTROL. The allowance is consumed only when a call is actually about to bill, so a
    credit-gate refusal or a missing tournament id does not waste it; it is recorded per league per
    ET day in st["fx_extra"]; and every decision - called, refused, overridden - is appended to
    FX_LOG, which main() prints. Fixtures already downloaded are kept and reused: this only ever
    adds to st["fixtures"].
    """
    last = tp((st.get("fx_last") or {}).get(lg))
    day = now.astimezone(ET).strftime("%Y-%m-%d")
    extra = False
    if last and now - last < timedelta(hours=6):
        if not allow_extra:
            FX_LOG.append(f"{lg}: no call - 6h cooldown ({(now - last).total_seconds() / 3600:.1f}h ago), "
                          f"no pending game past the cache")
            return False
        if (st.get("fx_extra") or {}).get(lg) == day:
            FX_LOG.append(f"{lg}: no call - 6h cooldown and the one extra refresh for {day} is spent")
            return False
        extra = True
    tid = tournament(st, now, lg)
    if not tid or not can_bill(st, now):
        FX_LOG.append(f"{lg}: no call - {'no tournament id' if not tid else 'credit gate would refuse'}")
        return False
    try:
        d = api("/fixtures", True, tournamentId=tid, **{"from": lo.strftime("%Y-%m-%d"), "to": hi.strftime("%Y-%m-%d")})
    except GateRefused as e:
        # A gate refusal is exactly the existing "we never looked" case, so it takes the same
        # return. This matters for the seven contents: read research jobs: under enforcement they
        # cannot take a reservation, so every paid call is refused - the intended state - and they
        # must still complete their FREE historical work instead of aborting on the first refusal.
        st.setdefault("errors", []).append(f"{iso(now)} fixtures {lg}: {e}")
        return False
    bill(st, now)
    st.setdefault("fx_last", {})[lg] = iso(now)
    if extra:   # consumed only now, when the call has actually billed
        st.setdefault("fx_extra", {})[lg] = day
    FX_LOG.append(f"{lg}: 1 billable /fixtures {lo:%Y-%m-%d}..{hi:%Y-%m-%d}"
                  + ("  (EXTRA - cooldown overridden, pending game past the cache)" if extra else ""))
    if isinstance(d, dict) and d.get("_error"):
        st.setdefault("errors", []).append(f"{iso(now)} fixtures {lg}: {d['_error']} {d['_body'][:120]}")
        return False   # the call failed, so the cache is unchanged - that is not the bet's fault
    fx = st.setdefault("fixtures", {})
    for f in d if isinstance(d, list) else []:
        if not f.get("fixtureId"):
            continue
        fx[f["fixtureId"]] = {"lg": lg, "start": f.get("startTime"), "status": f.get("statusId"),
                              "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                              "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                              "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}
    return True


def find_fixture(st, b):
    """Nov 5 (Peter, approval of the targeted recovery): BOTH participants must match on a DISTINCTIVE
    token, neither side may be carried by a word the other also matched, AT LEAST ONE side must match
    on TWO or more distinctive tokens, and the winner must be unique.
    tb.WEAK is stripped here because match_game already strips it, and without that a "New Orleans ..."
    bet reached sc==2 against a "New York ..." fixture purely on the shared word "new" - a wrong
    fixture, and so a confidently wrong CLV, which is worse than no CLV. "Bay" (Tampa Bay / Green Bay)
    and "Cougars" (Houston / Misericordia) fail the same way; both were seen in the Nov 5 inspection.
    The two-token floor (Peter, Nov 5) stops a single coincidental token per side from carrying a
    match: "Penn State Nittany Lions / Purdue" otherwise matched "Pennsylvania Quakers / Columbia
    Lions" on "penn" and "lions" alone. It also UNBLOCKS real matches, because the junk low-division
    fixture in an NCAAF collision drops out and leaves the true game unique.
    Several qualifying fixtures, or none, returns None and the bet is left UNSCORED rather than
    mis-scored. This only tightens: it never invalidates a fixture already stored on a row, and a
    scored row is skipped before this is reached."""
    lg, gs = b.get("league"), tp(b.get("game_start"))
    # Nov 12: UNION, not `or`. The `or` short-circuited: if `teams` yielded any token at all the
    # game text was never consulted - and a row whose `teams` holds only ONE side could then never
    # match, because _qualifies requires BOTH p1 and p2 to intersect `words`. Measured: 46 of 54
    # unscored rows failed on "one side matched nothing", including rows whose closest fixture was
    # literally the right game ("Atlanta Hawks @ Orlando Magic" vs fixture "Orlando Magic ORL v
    # Atlanta Hawks ATL", p1 hit []) - Orlando is in the row's own game text, which `or` skipped.
    # fill_for() at line ~628 in this same file already unions the two; this makes the matcher and
    # its validator agree with it. No guard is relaxed: both sides must still intersect, each still
    # needs a distinctive token the other lacks, the two-token floor still applies, and the winner
    # must still be unique - so this admits the RIGHT fixture without admitting a wrong one.
    words = (tb.toks(" ".join(t.get("name", "") for t in b.get("teams") or []))
             | tb.toks(b.get("game"))) - tb.WEAK
    if not words:
        return None
    # the per-fixture test lives in _qualifies so this and fixture_check() can never diverge - two
    # standards for the same question is exactly how the first version of the exclusion went wrong.
    hit = [fid for fid, f in (st.get("fixtures") or {}).items() if _qualifies(f, lg, gs, words)]
    return hit[0] if len(hit) == 1 else None


def _qualifies(f, lg, gs, words):
    """The matcher's own test for ONE fixture, so find_fixture and the validation cannot drift."""
    if f.get("lg") != lg:
        return False
    fs = tp(f.get("start"))
    if gs and fs and abs((fs - gs).total_seconds()) > 36 * 3600:
        return False
    a = (tb.toks(f.get("p1") or "") - tb.WEAK) & words
    c = (tb.toks(f.get("p2") or "") - tb.WEAK) & words
    return bool(a and c and (a - c) and (c - a) and max(len(a), len(c)) >= 2)


def fixture_check(st, rec):
    """('ok' | 'doubt' | 'unvalidatable', reason) for a scored row's STORED fixture.

    Nov 5 (Peter, closing two holes in the first version):
      - the stored fixture must be the UNIQUELY correct one, not merely pass the token rule. A
        fixture that qualifies while others also qualify is not established, it is ambiguous.
      - a fixture that has left the cache is 'unvalidatable', NOT 'ok'. The first version returned
        not-suspect in that case, so cache expiry would have quietly restored a doubtful row to the
        headline with no independent re-check - exactly what must not happen.
    Pairs with the sticky fixture_doubt marker set in main(): once a row is found doubtful it stays
    out until someone establishes its real game and its CLV is recalculated. Nothing here clears it."""
    fid = rec.get("fixture")
    if not fid:
        return "ok", ""                     # scored without a fixture id - nothing to validate here
    s = rec.get("snap") or {}
    # Nov 12: union, matching find_fixture above. The comment there explains why `or` was wrong;
    # the reason this one must change with it is that _qualifies is deliberately shared so the
    # matcher and the validator "can never diverge". Leaving the validator on `or` would make it
    # judge a stored fixture by a narrower word set than the one that chose it, and start calling
    # correctly-matched rows doubtful.
    words = (tb.toks(" ".join(t.get("name", "") for t in s.get("teams") or []))
             | tb.toks(s.get("game"))) - tb.WEAK
    if not words:
        return "unvalidatable", "no distinctive team words on the row"
    fx = st.get("fixtures") or {}
    if fid not in fx:
        return "unvalidatable", "stored fixture is no longer in the cache"
    lg, gs = s.get("league"), tp(s.get("game_start"))
    q = [k for k, f in fx.items() if _qualifies(f, lg, gs, words)]
    if q == [fid]:
        return "ok", ""
    if fid in q:
        return "doubt", f"stored fixture qualifies but so do {len(q) - 1} other(s) - not established"
    return "doubt", f"stored fixture does not pass the matcher ({len(q)} other(s) qualify)"


def identity_check(rec):
    """Was the row's GAME identity established, or inherited from a one-team ESPN match?

    Nov 5 (Peter): "validate the original game identity, not just the fixture assigned by the
    tracker." tracker_build.match_game returns a game on score==1 when the league is known:
        return best if score >= 2 or (score == 1 and bet.get("league")) else None
    espn_fill then OVERWRITES s["teams"] with that game's two teams. find_fixture afterwards matches
    a fixture against those teams and passes the two-token floor and the uniqueness test - because it
    is checking against the data the upstream error wrote. The downstream matcher therefore cannot
    catch this class of mistake at all; it can only confirm it.
    s["bet"] and s["game"] are never overwritten, so the bet's ORIGINAL text is an independent
    witness: it must support BOTH assigned teams, and any tracker date must agree with the game."""
    s = rec.get("snap") or {}
    if not s.get("espn_filled"):
        return "ok", ""                  # the tracker supplied the game - nothing was inherited
    tms = [(t.get("name") or "").strip() for t in (s.get("teams") or []) if (t.get("name") or "").strip()]
    if len(tms) < 2:
        return "doubt", "ESPN-filled row without two named teams"
    own = (tb.toks(s.get("bet")) | tb.toks(s.get("game"))) - tb.WEAK
    if not own:
        return "doubt", "ESPN-filled and the bet's own text names no team - identity unverifiable"
    hits = sum(1 for t in tms if (tb.toks(t) - tb.WEAK) & own)
    if hits < 2:
        return "doubt", f"ESPN-filled: the bet's own text supports {hits} of the 2 assigned teams"
    d, gs = tp((s.get("date") or "") + "T12:00:00Z") if s.get("date") else None, tp(s.get("game_start"))
    if d and gs and abs((gs - d).total_seconds()) > 36 * 3600:
        return "doubt", "ESPN-filled: assigned game date disagrees with the tracker's own date"
    return "ok", ""


def release_covers(rec, why_now):
    """Did Peter's manual release already cover EXACTLY this doubt, on THIS fixture?

    Stage 1 (Peter, Nov 13). clv_release_verified clears fixture_doubt correctly, but step 5
    re-ran identity_check on every pass and re-raised the flag whenever it was merely absent.
    identity_check reads espn_filled, teams and bet text - none of which a release changes - so
    all 25 released rows came back held out with the identical reason string on the very next
    run, and clv_readout's own check has been printing "released rows still carrying
    fixture_doubt: 25 (must be 0)" ever since. The release was a no-op that looked like success.

    The guard is deliberately narrow on BOTH axes:
      * the reason string must match exactly. A row that later develops a DIFFERENT doubt - a
        new ambiguity, a fixture that stops passing the matcher - is flagged normally. A release
        forgives the doubt Peter looked at, never doubt in general.
      * the fixture must match. If a row's fixture changes, whatever was validated no longer
        describes it.
    The legacy case: released_from written before this change stored only {since, why}, so it
    carries no fixture. Those are honoured once (the fixture on the row is the one the Nov 12
    audit recorded against it) and the caller then pins the fixture into the record, after which
    the strict test applies. No row is released that Peter did not already release by hand.
    """
    prev = rec.get("released_from") or {}
    if not prev or prev.get("why") != why_now:
        return False
    fx = prev.get("fixture")
    return fx is None or fx == rec.get("fixture")


def apply_doubt(st, rec, now):
    """Step 5's per-row decision. Extracted from main() so it is testable without a full run.

    Behaviour is unchanged except for the release_covers() guard: a doubt that a prior release
    already covered no longer re-excludes the row. Nothing else is written - no CLV, no price,
    no fixture, no result.
    """
    fv, fw = fixture_check(st, rec)
    iv, iw = identity_check(rec)
    doubt = (fv == "doubt" or iv == "doubt")
    why_now = fw if fv == "doubt" else iw
    if doubt and release_covers(rec, why_now):
        # Pin a legacy release to the fixture it is covering, once, so later passes use the
        # strict fixture+reason test instead of the permissive legacy one. This adds a field
        # to released_from and changes no CLV, price, fixture or result.
        if not (rec.get("released_from") or {}).get("fixture") and rec.get("fixture"):
            rec["released_from"]["fixture"] = rec["fixture"]
        if rec.get("fixture_doubt"):
            # The flag is ALREADY set, put there by the pre-Stage-1 step 5 on one of the many runs
            # since Nov 12. Guarding the re-raise alone was not enough: it stops the next flag but
            # leaves the existing one in place, so the 25 rows stayed held out and the first real
            # ledger run after Stage 1 moved none of them. A release that the row still satisfies
            # has to actually clear the flag, which is what the release did in the first place.
            # Narrow by the same test as everything else here - fixture AND reason - and
            # idempotent: released_from keeps the original record, so re-running changes nothing.
            rec.pop("fixture_doubt")
            return "re-released"
        return "released"
    if doubt and not rec.get("fixture_doubt"):
        rec["fixture_doubt"] = {"since": iso(now), "why": why_now}
        return "flagged"
    if fv == "ok" and iv == "ok":
        # Durable record of an independent validation, keyed to the fixture it validated. Keeps
        # the FIRST date, so a row checked while its fixture was cached is not punished later when
        # the cache rolls - that is the "durable record of prior validation" Peter asked for.
        if (rec.get("fixture_ok") or {}).get("fixture") != rec.get("fixture"):
            rec["fixture_ok"] = {"at": iso(now), "fixture": rec.get("fixture")}
        return "ok"
    return "unchanged"


LG_LOG = []


def recover_leagues(st, now, max_rows=400):
    """Fill snap['league'] on rows that have none, from AUTHORITATIVE evidence only.

    Peter, Nov 13: "Recover leagues from authoritative order/fixture metadata, never guess from
    an ambiguous description." 103 of the 166 rows with no CLV carry no league at all - almost
    all ProphetX - and a row with no league can never match a fixture, because _qualifies
    requires f['lg'] == lg. It is the single largest cause of missing CLV and it is our own data
    gap, not a limit of what the market published: read_prophetx builds its rows without a league
    key, and espn_fill only fills rows that have no GAME, so a ProphetX row with a game and no
    league was never touched by either.

    THREE SOURCES, ALL AUTHORITATIVE, IN ORDER:
      1 the fixture already stored on the row - the fixture IS the game, so its league is a fact
      2 the ESPN scoreboard for the row's own date - a scoreboard is the authority on which
        league a game belongs to, and tracker_build.match_game already encodes the two-team
        anti-ambiguity rules. A match must be UNIQUE across leagues or it is refused.
      3 nothing else. No inference from the bet text, the book, or a tournament-sounding word.

    Every fill records league_src, so any recovered league can be traced to the evidence that
    produced it. Rows that cannot be resolved are left exactly as they are and counted.
    """
    noleague = [(k, r) for k, r in (st.get("bets") or {}).items()
                if not (r.get("snap") or {}).get("league")]
    filled = collections.Counter()
    # Many rows with no league ALSO have no game text - read_prophetx writes
    # game = strike-lookup or event_name, and when the strike walk failed at the time both came
    # out empty. The registry's strike map is the authoritative record of what a strike IS
    # (book, game, date, mtype, label), so a row whose tracker entry carries a strike id can
    # have its game restored from there. That is venue metadata, not a guess from a description.
    nogame = [(k, r) for k, r in noleague if not (r.get("snap") or {}).get("game")]
    if nogame:
        # Nov 18 (Peter): states with different remedies must not share one silent outcome. Until
        # today clv-ledger was not passed REGISTRY_TOKEN, so enabled() was False, smap was {} and
        # 349 rows restored 0 games with NO message at all - an empty map is not an exception, so
        # nothing was logged and the run looked like it had simply found nothing to recover. Each
        # case below now says which one it is.
        smap, _smap_why = {}, ""
        try:
            import registry as _reg
            if not _reg.enabled():
                _smap_why = "REGISTRY_TOKEN not set for this job - strike-map recovery did not run"
            else:
                smap = _reg.strike_map() or {}
                if not smap:
                    _smap_why = "registry reachable but its strike map is EMPTY - nothing cached to recover from"
        except Exception as e_:
            _smap_why = f"registry strike map unavailable ({type(e_).__name__})"
        if _smap_why:
            LG_LOG.append(_smap_why)
        trk = {}
        try:
            trk = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
        except Exception:
            pass
        for k, r in nogame:
            sid = str((trk.get(k) or {}).get("strike") or "")
            ent = smap.get(sid) if sid else None
            if ent and ent.get("game"):
                r["snap"]["game"] = ent["game"]
                r["snap"]["game_src"] = {"from": "registry strike map", "strike": sid, "at": iso(now)}
                filled["game_from_strike"] += 1
        # Nov 18 (Peter): say WHY the misses missed, split by cause - "no strike id on the row" and
        # "strike id present but absent from the map" need opposite fixes, and one number cannot
        # tell them apart. This is what verifies whether the registry actually holds these rows.
        _no_sid = _no_hit = 0
        for k, r in nogame:
            if r["snap"].get("game"):
                continue
            if not str((trk.get(k) or {}).get("strike") or ""):
                _no_sid += 1
            else:
                _no_hit += 1
        LG_LOG.append(f"rows with no league AND no game: {len(nogame)}; "
                      f"games restored from the registry strike map: {filled['game_from_strike']}; "
                      f"strike map entries: {len(smap)}; misses: {_no_sid} with no strike id on the row, "
                      f"{_no_hit} whose strike id is not in the map")
        # Nov 18 (Peter, minimum-viable recovery): split the missing rows by SOURCE on a VERIFIED
        # identifier before anyone spends effort recovering them. The execution studies (Q1, Q4) need
        # BOT fills; a manual row restored moves neither. The bot order registry keys each order by
        # play_key - league|game|market|side - so a row whose order_ref matches a registry order id
        # has its identity available without a single venue call. READ-ONLY: this counts, it writes
        # nothing, and no row is changed on the strength of it.
        _reg_keys, _src, _joinable = {}, collections.Counter(), 0
        try:
            import registry as _reg2
            for _row in (_reg2.rows() or []):
                _k = _row.get("key")
                if not _k:
                    continue
                _legs = [_row.get("live_order") or {}, _row.get("live_rest") or {}]
                _legs += [x or {} for x in (_row.get("live_more") or [])]
                for _lo in _legs:
                    for _i in (_lo.get("order_id"), _lo.get("client_id")):
                        if _i:
                            _reg_keys[str(_i)] = _k
        except Exception as _je:
            LG_LOG.append(f"bot order registry join unavailable ({type(_je).__name__})")
        for k, r in nogame:
            _t = trk.get(k) or {}
            _ref = str(_t.get("order_ref") or "")
            _s = str((r.get("snap") or {}).get("source") or _t.get("source") or "")
            if _ref and _ref in _reg_keys:
                _src["BOT (registry order id matched)"] += 1
                _joinable += 1
            elif _s.lower().startswith("bot"):
                _src["BOT (source tag, no registry match)"] += 1
            elif _s:
                _src[f"MANUAL ({_s[:16]})"] += 1
            else:
                _src["UNKNOWN (no source, no registry match)"] += 1
        LG_LOG.append(f"missing-row sources: {dict(_src)}; registry orders indexed: {len(_reg_keys)}; "
                      f"identities recoverable by order-id join: {_joinable}")
    need = [(k, r) for k, r in noleague if (r.get("snap") or {}).get("game")]
    LG_LOG.append(f"rows with no league: {len(noleague)}; of those with a game text: {len(need)}")
    if not need:
        return 0
    # 1) the row's own fixture
    for k, r in need:
        fid = r.get("fixture")
        f = ((st.get("fixtures") or {}).get(fid) or ALT_FX.get(fid)) if fid else None
        if f and f.get("lg"):
            r["snap"]["league"] = f["lg"]
            r["snap"]["league_src"] = {"from": "stored fixture", "fixture": fid, "at": iso(now)}
            filled["fixture"] += 1
    need = [(k, r) for k, r in need if not r["snap"].get("league")][:max_rows]
    if not need:
        LG_LOG.append(f"leagues recovered from stored fixtures: {filled['fixture']}")
        return sum(filled.values())
    # 2) the ESPN scoreboard for each row's own date, across every league the tracker reads
    days = sorted({(tp(r["snap"].get("game_start")) or tp(r["snap"].get("placed"))
                    or tp(r.get("first_seen"))).astimezone(ET).date()
                   for _k, r in need
                   if (tp(r["snap"].get("game_start")) or tp(r["snap"].get("placed"))
                       or tp(r.get("first_seen")))})
    games = []
    for d in days[-14:]:          # bounded: a free ESPN read per date, newest 14 dates
        try:
            games += tb.espn_games([datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc).astimezone(ET)])
        except Exception as e_:
            LG_LOG.append(f"espn scoreboard {d}: {type(e_).__name__}")
    for k, r in need:
        s = r["snap"]
        g = None
        try:
            g = tb.match_game({"game": s.get("game"), "bet": s.get("bet")}, games)
        except Exception:
            g = None
        if g and g.get("league"):
            # UNIQUE across leagues, or refused: match_game returns one game, but a game text
            # that plausibly matches two leagues' scoreboards must not be resolved by whichever
            # was read first.
            others = {x.get("league") for x in games
                      if x is not g and tb.match_game({"game": s.get("game"), "bet": s.get("bet")}, [x])}
            if others - {g["league"]}:
                filled["ambiguous"] += 1
                continue
            s["league"] = g["league"]
            s["league_src"] = {"from": "ESPN scoreboard", "game": g.get("id"), "at": iso(now)}
            filled["espn"] += 1
            for fld in ("done", "tries", "why"):
                r.pop(fld, None)      # it was never given a fair attempt without a league
        else:
            filled["unresolved"] += 1
    LG_LOG.append(f"leagues recovered: {dict(filled)} (from {len(days[-14:])} scoreboard date(s))")
    return filled["fixture"] + filled["espn"]


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



PROV = collections.Counter()   # P1-B provenance outcomes this run (counts only; printed in the run summary)
QUOTE_TS_BASIS = "derived: start minus close_for age_min (age of the OLDER side's last tick, rounded to 1 min)"


def stamp_entry(rec, s, c, start, now):
    """P1-B. WRITE-ONCE scoring-time entry provenance. Returns the status written to entry_prov_status.

    The first scoring stores entry_dec / entry_src / fee_model / basis_version / entry_scored_at and a DERIVED
    quote time. A later re-score that sees a different entry decimal records the current value beside it and
    never replaces the original; the drift evidence is STICKY (review R3): once seen it keeps first-seen,
    count and largest |drift| even after the entry returns to the original. The CLV figure is computed
    exactly as before - this only records how."""
    d, src, fee = eff_dec_src(s)
    if d is None:
        rec["entry_prov_status"] = "no_entry_price"
        return "no_entry_price"
    try:
        import clv_basis as _cb
        bv = _cb.BASIS_VERSION
    except Exception:
        bv = None
    if rec.get("entry_dec") is None:
        rec["entry_dec"], rec["entry_src"], rec["fee_model"] = round(d, 6), src, fee
        rec["basis_version"], rec["entry_scored_at"] = bv, iso(now)
        am = c.get("age_min")
        # NOT an observed timestamp: close_for reports only minutes before start, rounded (review: quote_ts)
        rec["quote_ts_derived"] = iso(start - timedelta(minutes=am)) if (start and am is not None) else None
        rec["quote_ts_basis"] = QUOTE_TS_BASIS if rec["quote_ts_derived"] else "unavailable: no start or no age_min"
        rec["entry_prov_status"] = "ok"
        return "ok"
    drift = 1e4 * (d - rec["entry_dec"]) / rec["entry_dec"] if rec["entry_dec"] else None
    if drift is not None and abs(drift) >= 0.5:
        rec["entry_dec_now"], rec["entry_src_now"] = round(d, 6), src
        rec["entry_drift_bp"], rec["entry_drift_seen"] = round(drift, 1), iso(now)
        rec.setdefault("entry_drift_first_seen", iso(now))
        rec["entry_drift_count"] = rec.get("entry_drift_count", 0) + 1
        rec["entry_drift_max_bp"] = max(abs(round(drift, 1)), rec.get("entry_drift_max_bp") or 0)
        rec["entry_prov_status"] = "ok_drift"
        return "ok_drift"
    for x in ("entry_dec_now", "entry_src_now", "entry_drift_bp", "entry_drift_seen"):   # CURRENT drift only;
        rec.pop(x, None)                                                                  # the sticky record stays
    rec["entry_prov_status"] = "ok"
    return "ok"


PHASE1_SNAP = ("order_ref", "lane", "lane_src", "strategy_key")
LANE_RANK = {"none": 0, "manual-source": 1, "fuzzy-join": 1, "registry-order-id": 2}


def copy_phase1(snap, b, now_iso):
    """Carry the tracker's Phase 1 identity onto a ledger snap WITHOUT relabelling history (review R4).

    * A tracker row with no lane_src is legacy: nothing is copied.
    * A snap that has never held a lane_src takes the four fields once.
    * After that the lane can only be UPGRADED to an exact registry-order-id match, and every change is
      appended to snap['lane_history'] with the old and new values. A downgrade or a sideways change is
      never written. ingest_* first-observation fields are copied once and never overwritten."""
    if not b.get("lane_src"):
        return "legacy"
    if "lane_src" not in snap:
        for f in PHASE1_SNAP:
            if b.get(f) not in (None, "", []):
                snap[f] = b[f]
        out = "first"
    elif LANE_RANK.get(b["lane_src"], 0) > LANE_RANK.get(snap.get("lane_src"), 0) and b["lane_src"] == "registry-order-id":
        snap.setdefault("lane_history", []).append({"from": {f: snap.get(f) for f in PHASE1_SNAP},
                                                    "to": {f: b.get(f) for f in PHASE1_SNAP}, "at": now_iso})
        for f in PHASE1_SNAP:
            if b.get(f) not in (None, "", []):
                snap[f] = b[f]
        out = "upgraded"
    else:
        out = "kept"
    for f in ("ingest_missing_first", "ingest_checked"):
        if f in b and f not in snap:
            snap[f] = b[f]
    return out


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


def record_v2(rec, c, d):
    """Store the SHADOW V2 close alongside V1, never over it (Peter, Nov 19: "Keep V1 as the official
    CLV. Run V2 alongside it - shadow only").

    V1 reads the no-vig fair off whatever quote sits at our number. Once the line moves, that quote
    is a deep ALT, and Pinnacle's alt juice is heavier and uneven while novig_p strips vig assuming
    it is even - which biases the fair against the side holding the better number. V2 derives the
    fair at our number from the MAIN line instead. They are IDENTICAL whenever our number was the
    main line, so V2 differs only on rows where the line actually moved.

    v2_derived marks a MODEL-DERIVED fair. It is not a directly observed same-line close and must
    never be reported as certified same-line CLV.
    """
    if not c or d is None or c.get("v2_p") is None:
        return False
    rec["clv_v2"] = round(c["v2_p"] * d - 1, 4)
    rec["close_p_v2"] = round(c["v2_p"], 4)
    rec["how_v2"] = c.get("v2_how")
    rec["v2_derived"] = not c.get("at_main", True)
    if c.get("main_line") is not None:
        rec["main_line"] = c["main_line"]
    return True


def fair_from_main(p_main, main_line, want, better, lab, kind):
    """The fair win chance AT OUR NUMBER, derived from Pinnacle's MAIN line.

    Nov 19 (Peter): "The line moved my way, it should get CLV credit. The CLV is not at my number."
    It was read at the number - but off the ALT quote that survives there once the line moves.
    Pinnacle prices alts with heavier and uneven juice, and novig_p strips vig assuming it is even,
    so an alt's fair understates the side holding the better number. That biases exactly the plays
    that moved our way: seven plays on Nov 19 all beat the closing number and all scored negative,
    which no market verdict explains.

    The main line is the liquid, properly priced quote, so the fair at our number is the main line's
    fair moved across the intervening numbers by the half-point model - the same model already used
    when Pinnacle has no quote at our number at all. `better` is True when our number is the easier
    side of the main line; the value is added then and subtracted otherwise, so a favourable move
    can only ever increase our fair chance.
    """
    v = sm.half_point_value(lab, kind, min(main_line, want), max(main_line, want), main_line)
    return min(max(p_main + (v if better else -v), .01), .99)


def close_for(b, f, pm, mkmap, start, lg):
    """Pinnacle close fair win chance for the held side, plus how it was read."""
    # Nov 14 (Peter, priority 1): the same guards the shared basis applies. A politics market is
    # not a sports bet - ks|SENATEMI-26-R reached scoring with league NCAAF after being
    # ESPN-filled onto Eastern Michigan v Central Michigan on the shared word "Michigan".
    try:
        if tb.is_politics({"game": b.get("game"), "bet": b.get("bet")}):
            return None, "politics market, not a sports bet - never scored against a game close"
    except Exception:
        pass
    pz = parsed(dict(b, bet=b["side_verified"], flip=None) if b.get("side_verified") else b)
    if not pz:
        return None, "bet text not parsed"
    sid = SCORE_SPORT[lg]
    lab = lg
    if pz[0] == "ml":
        side, _swhy = fxm.resolve_side(f, pz[1], lg, which_team)
        if not side:
            return None, _swhy
        if pz[3]:
            side = "2" if side == "1" else "1"
        mid = ML_MARKET[sid]
        oc = {v: k for k, v in mkmap.get(mid, [0, 0, 0, {}])[3].items()} or {"1": str(mid), "2": str(int(mid) + 1)}
        tw = two_way(pm, mid, start)
        o1, o2 = oc.get("1"), oc.get("2")
        if o1 not in tw or o2 not in tw:
            return None, "no Pinnacle moneyline close"
        age = (start - min(tw[o1][1], tw[o2][1])).total_seconds() / 60
        # Nov 6 (Peter, code review): the spreads/totals branch below drops a candidate whose last
        # tick is older than FRESH_MIN, and this branch computed the same age and then ignored it.
        # A moneyline close could therefore be a day-plus stale and still be reported as verified.
        # The registered freshness rule now applies to BOTH paths, as it always should have.
        if age > FRESH_MIN:
            return None, "Pinnacle moneyline close older than the freshness limit"
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
            # V1 stays OFFICIAL (Peter, Nov 19): the fair is read off the quote at our number, as it
            # always was. V2 is computed alongside as a SHADOW and never replaces it here. They
            # differ only when our number is an ALT - i.e. only when the line moved.
            _p1v = exact[1] if over else 1 - exact[1]
            _at_main = abs(exact[0] - main[0]) < 1e-9
            _ppt, _po = main[0], main[1]
            _p2v = _p1v if _at_main else fair_from_main(
                _po if over else 1 - _po, _ppt, want, (want < _ppt) if over else (want > _ppt), lab, "tot")
            return {"p": _p1v, "how": "own line", "age_min": round(exact[2]),
                    "at_main": _at_main, "main_line": _ppt,
                    "v2_p": _p2v, "v2_how": "own line" if _at_main else f"own line (from main {_ppt:g})"}, None
        ppt, po = main[0], main[1]
        if abs(want - ppt) > max(1.5, 0.03 * ppt):   # Nov 2: 'Over 5.5' scored on an NBA total = wrong league/market
            return None, "bet line far from Pinnacle's main line (wrong league or market?)"
        p = po if over else 1 - po
        v = sm.half_point_value(lab, "tot", ppt, want, ppt)
        better = (want < ppt) if over else (want > ppt)
        return {"p": min(max(p + (v if better else -v), .01), .99), "how": f"main {ppt:g} moved to {want:g}",
                "age_min": round(main[2])}, None
    side, _swhy = fxm.resolve_side(f, pz[1], lg, which_team)
    if not side:
        return None, _swhy
    want = pz[2]
    if pz[3]:   # NO / short side of a 'Team -x' contract: the other team at +x
        side, want = ("2" if side == "1" else "1"), -want
    t1_line = want if side == "1" else -want          # the same bet stated as team 1's handicap
    exact = next((c for c in cands if abs(c[0] - t1_line) < 1e-9), None)
    if exact:
        # V1 official, V2 shadow - see the totals branch above.
        _p1v = exact[1] if side == "1" else 1 - exact[1]
        _at_main = abs(exact[0] - main[0]) < 1e-9
        _hp, _pm1 = main[0], main[1]
        _mine = _hp if side == "1" else -_hp
        _p2v = _p1v if _at_main else fair_from_main(
            _pm1 if side == "1" else 1 - _pm1, _mine, want, want > _mine, lab, "spr")
        return {"p": _p1v, "how": "own line", "age_min": round(exact[2]),
                "at_main": _at_main, "main_line": _mine,
                "v2_p": _p2v, "v2_how": "own line" if _at_main else f"own line (from main {_mine:+g})"}, None
    if lg == "NHL":
        return None, "puck line at a different number: not comparable"
    hp, p1 = main[0], main[1]
    my_pin_line = hp if side == "1" else -hp           # Pinnacle's main number from the bet team's side
    if abs(want - my_pin_line) > 4.5:
        return None, "bet line far from Pinnacle's main line (wrong league or market?)"
    p = p1 if side == "1" else 1 - p1
    v = sm.half_point_value(lab, "spr", my_pin_line, want, my_pin_line)
    p += v if want > my_pin_line else -v
    return {"p": min(max(p, .01), .99), "how": f"main {my_pin_line:+g} moved to {want:+g}", "age_min": round(main[2])}, None


# ------------------------------------------------------------------ bot Novig orders (stale check)
MAX_NEW_MAIL = 600   # Nov 19: uncached "Bets LIVE:" fetches per run (~0.73 s each, so ~7 min)


def bot_novig_orders(days=45, cache=None, max_new=None):
    """Bot Novig orders from its own 'Bets LIVE:' ledger rows: decision time, price used, line.

    Returns (orders, note) - note is None on a clean read, else why the read is PARTIAL.

    Nov 19 (Peter: the ledger spent 807 s here; eliminate repeated retrieval). This searched 45 days
    of "Bets LIVE:" mail and FETCHed every match in full, every run - the executor sends one of those
    per pass, so the same thousands of messages were re-downloaded serially each time. That was 95%
    of the ledger's runtime and it is what aborted mid-read.

    An IMAP message is immutable once delivered, so a UID parsed once never needs fetching again.
    Only UIDs absent from the cache are fetched. The cache is keyed inside UIDVALIDITY and dropped
    whole if the server changes it, because UIDs are only unique within one UIDVALIDITY.

    A failed read NEVER yields an empty result: whatever the cache holds is returned with a note
    saying the read was partial. Missing data is not evidence of zero fills.
    """
    import email as em
    out, note = [], None
    cache = cache if cache is not None else {}
    M = ex.imap_open()
    try:
        try:
            uv = (M.response("UIDVALIDITY")[1] or [b""])[0].decode() or ""
        except Exception:
            uv = ""
        if uv and cache.get("uidvalidity") not in (None, uv):
            cache.clear()          # UIDs are only unique within a UIDVALIDITY - a change invalidates every key
        cache.setdefault("uidvalidity", uv)
        rows_by_uid = cache.setdefault("uids", {})
        uids = ex.gsearch(M, f'subject:"Bets LIVE:" newer_than:{days}d')
        cap = MAX_NEW_MAIL if max_new is None else max_new
        fetched, deferred = 0, 0
        for uid in uids:
            key = uid.decode() if isinstance(uid, bytes) else str(uid)
            if key in rows_by_uid:                       # parsed on an earlier run; the message cannot have changed
                out.extend(rows_by_uid[key])
                continue
            if fetched >= cap:
                # Nov 19 (Peter: a timeout must not repeatedly restart a full 1,902-message
                # download). Each run fetches a bounded slice and then stops, so the run always
                # reaches its save stage and the messages it DID parse persist. The rest are taken
                # on later runs; a cold cache fills over a few runs instead of risking a kill that
                # saves nothing and starts over.
                deferred += 1
                continue
            try:
                parsed = _bot_live_rows(M, uid, em)
            except Exception as e:                       # a dropped connection stops the sweep, it does not empty it
                note = f"partial read after {fetched} new message(s): {type(e).__name__}"
                break
            fetched += 1
            rows_by_uid[key] = parsed
            out.extend(parsed)
        live = {u.decode() if isinstance(u, bytes) else str(u) for u in uids}
        for gone in [k for k in rows_by_uid if k not in live]:
            del rows_by_uid[gone]      # outside the 45-day window: bounded, not unbounded growth
        cache["fetched_last_run"] = fetched
        cache["seen_last_run"] = len(uids)
        cache["deferred_last_run"] = deferred
        if deferred and not note:
            note = f"capped at {fetched} new message(s) this run; {deferred} still uncached"
    finally:
        ex.imap_close(M)
    return out, note


def _bot_live_rows(M, uid, em):
    """The orders carried by ONE 'Bets LIVE:' message. The parsing is unchanged; it is lifted out of
    bot_novig_orders so the caller can cache the result per UID and never fetch that message again.
    Each former `continue` (skip this message) becomes an empty return for this message."""
    out = []
    typ, d = M.uid("FETCH", uid, "(RFC822)")
    if typ != "OK" or not d or not d[0]:
        return out
    raw = d[0][1]
    subj = str(em.header.make_header(em.header.decode_header(em.message_from_bytes(raw).get("Subject") or "")))
    if not subj.startswith("Bets LIVE:"):
        return out          # IMAP SUBJECT search is a SUBSTRING match - re-check the real header prefix
    txt = ex.body_text(raw)
    i = txt.rfind("LEDGER (machine-readable")
    if i < 0:
        return out
    try:
        rows, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
    except Exception:
        return out
    for r in rows:
        for lo in [r.get("live_order") or {}, r.get("live_rest") or {}] + [x or {} for x in r.get("live_more") or []]:
            if lo.get("status") != "placed" or not lo.get("order_id"):
                continue
            out.append({"order_id": str(lo["order_id"]), "book": lo.get("book") or "prophetx", "key": r.get("key"),
                        "decided_utc": r.get("decided_utc"),
                        "line": r.get("live_px_line"), "price": r.get("live_px_price_after_fee"),
                        "nv_at_decision": ((r.get("books_at_decision") or {}).get("novig") or {})})
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
            "decided_utc": o.get("decided_utc"), "book": o.get("book")}


def fill_for(s, fills):
    """The bot's own fill record (after-fee price) for a tracker bet that lost its price, or None."""
    gs = tp(s.get("game_start"))
    words = tb.toks(" ".join(t.get("name", "") for t in s.get("teams") or [])) | tb.toks(s.get("game"))
    sz = parsed(s)
    if not sz or not words:
        return None
    for b in fills:
        if b.get("price") in (None, "") or (s.get("league") and b.get("league") != s.get("league")):
            continue
        if len(tb.toks(b.get("game")) & words) < 2:
            continue
        dt = tp(b.get("decided_utc"))
        if gs and dt and not (gs - timedelta(days=4) <= dt <= gs + timedelta(hours=1)):
            continue
        bz = parsed(b)
        if not bz or bz[0] != sz[0]:
            continue
        if sz[0] == "total":
            if bz[1] == sz[1] and abs((bz[2] or 0) - (sz[2] or 0)) < 0.01:
                return b
        elif tb.toks(str(bz[1])) & tb.toks(str(sz[1])) and (sz[0] == "ml" or abs((bz[2] or 0) - (sz[2] or 0)) < 0.01):
            return b
    return None


def novig_at(b, f, nm_pm, mkmap, when, lg):
    """Novig's own price (decimal) for the held side at that time, and its age in seconds; None if not found."""
    pz = parsed(b)
    if not pz:
        return None
    sid = SCORE_SPORT[lg]
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


def grading_queue(pend, now):
    """Nov 19 (Peter: separate new fills from historical recovery, and process new fills first).

    st["bets"] iterates in FIRST-SEEN order, so the OLDEST rows were served first and spent the
    MAX_HIST free history calls (~8 s each) before today's fills were ever reached. The Nov 18
    game_start recovery made 353 old rows scorable at once, so a fill placed tonight could wait days
    for a call. That is starvation, not slowness: the run can finish on time and still not grade
    today.

    Returns (ordered pend, one log line). This changes ORDER and BATCH SIZE only. No row is dropped
    from the store, no row is marked done, no CLV is estimated, and nothing here touches a trading
    rule - a deferred row is simply offered again next run.
    """
    old = datetime.min.replace(tzinfo=timezone.utc)

    def row_t(kr):
        sn = kr[1].get("snap") or {}
        return tp(sn.get("game_start")) or tp(sn.get("placed")) or tp(kr[1].get("first_seen"))

    fresh, backlog = [], []
    for kr in pend:
        t = row_t(kr)
        (fresh if t and t > now - timedelta(days=BACKLOG_AFTER_DAYS) else backlog).append(kr)
    fresh.sort(key=lambda kr: row_t(kr) or old, reverse=True)
    # Least-tried, then least-recently-tried: the backlog ROTATES. Sorting by date alone would
    # re-offer the same head every run and never reach the tail - the rows most in need of a retry
    # are exactly the ones that have had fewest.
    backlog.sort(key=lambda kr: (kr[1].get("tries", 0), tp(kr[1].get("last_try")) or old))
    served = backlog[:BACKLOG_MAX]
    return fresh + served, (f"grading queue: {len(fresh)} new (<={BACKLOG_AFTER_DAYS}d), "
                            f"{len(backlog)} backlog, {len(served)} served this run, "
                            f"{len(backlog) - len(served)} deferred to a later run")


# ------------------------------------------------------------------ ESPN fill
def _espn_days(t0):
    """The scoreboard dates a bet at t0 could sit on: its own ET date and the one before - a late game
    settles after midnight ET."""
    return {(t0 - timedelta(days=dd)).astimezone(ET).replace(hour=12, minute=0, second=0, microsecond=0) for dd in (0, 1)}


def apply_settled_amounts(snap, b):
    """Prefer a SETTLED row's own stake and payout over the frozen first-seen pair. Returns the
    fields replaced, for counting.

    Nov 19 (Peter, proved against Novig's own settlement record on two R1 selections): the ledger
    freezes the first-seen stake/to_pay, which come from the OPEN row and can be a PARTIAL fill,
    while profit is refreshed from the settled row's pnl. One row, two bases. Novig held
    cost 1.079u / payout 2.075u / pnl 0.996u - payout minus cost equal to pnl to the cent - while
    the ledger held 0.616u / 1.185u / 0.996u. The units were RIGHT and the ROI denominator was
    understated, so R1's ROI read high and the payout ceiling read low.

    A settled row's own stake and payout are final, so they win when present. The guard matters:
    a settlement row DROPS the stake for losses, which is why the first-seen value is kept as the
    fallback and is never deleted - it is preserved under <field>_first_seen so the original record
    survives and the substitution is auditable. Nothing here touches sizing, pricing, risk controls
    or any live-betting path; it corrects what a settled row REPORTS, not what was bet.
    """
    done = []
    if not (b.get("result") and b.get("settled")):
        return done                      # not settled: the first-seen pair stands
    for f in ("stake", "to_pay"):
        v = b.get(f)
        if v in (None, "") or snap.get(f) == v:
            continue                     # missing on the settled row -> keep first-seen
        snap.setdefault(f + "_first_seen", snap.get(f))
        snap[f] = v
        snap[f + "_src"] = "settled row"
        done.append(f)
    return done


def espn_fill(st, now, max_days=50):   # Nov 4: was 12 - older bets' dates were never fetched, so they used up their tries
    """Settled tracker rows the tracker never pinned to a game: match them on ESPN (free) within 36 h of the settle
    or placed time, and take league, start and teams from there. At most max_days scoreboard dates per run.

    Nov 19 (Peter: the same historical data was being looked up every run). A row carries espn_done - the dates it has
    already been matched against a VERIFIED COMPLETE slate (every league read, all games terminal, date in the past).
    Such a date can never produce a new game, so re-reading it for that row is pure waste; the row's remaining dates
    are all that gets fetched, and a row with none left is skipped. A date that came back incomplete, empty across
    every league, or failed is never marked done, so unresolved rows stay eligible for retry - which is the whole
    point of the recovery path."""
    todo, skipped = [], 0
    # Nov 19 (Peter: report the 349 stuck rows by exclusion reason - exhausted tries, outside the
    # date window, missing usable dates, or other). Counting only: no counter is reset, no lookup is
    # started, nothing about the guards below changes. The run that printed "0 to try" gave no reason.
    why = collections.Counter()
    for k, rec in st["bets"].items():
        s = rec["snap"]
        if s.get("game_start"):
            continue                      # already pinned to a game; not part of the stuck set
        if rec.get("espn_tries", 0) >= 6:   # Nov 4: 3 more tries for rows stuck under the old 12-day window
            why["tries exhausted (>=6)"] += 1
            continue
        t0 = tp(s.get("settled")) or tp(s.get("placed")) or tp(rec.get("first_seen"))
        if not t0:
            why["no usable date (no settled, placed or first_seen)"] += 1
            continue
        if t0 <= now - timedelta(days=45):
            why["outside the 45-day window"] += 1
            continue
        done = set(rec.get("espn_done") or [])
        want = {d for d in _espn_days(t0) if d.strftime("%Y%m%d") not in done}
        if not want:          # every date this row could sit on is settled and did not match it
            why["already checked against settled dates"] += 1
            skipped += 1
            continue
        why["queued for a lookup"] += 1
        todo.append((k, rec, t0, want))
    LG_LOG.append("stuck rows (no game_start) by exclusion reason: "
                  + (", ".join(f"{k} {v}" for k, v in sorted(why.items())) or "none"))
    print("CLV ledger stuck rows by reason (counts only): "
          + (", ".join(f"{k} {v}" for k, v in sorted(why.items())) or "none"), flush=True)
    if not todo:
        LG_LOG.append(f"espn fill: 0 to try, {skipped} skipped as already checked")
        return
    days = sorted(set().union(*(w for _, _, _, w in todo)), reverse=True)[:max_days]
    complete = set()
    games = tb.espn_games(days, complete=complete)
    got, filled, marked = set(days), 0, 0
    for k, rec, t0, want in todo:
        s = rec["snap"]
        if not want <= got:   # Nov 4: this bet's dates weren't fetched this run - don't count it as a failed try
            continue
        g = tb.match_game(s, games, t0)
        if g and len(g["teams"]) == 2:
            a, h = sorted(g["teams"], key=lambda t: t["home"])
            s["league"] = s.get("league") or g["league"]
            s["game_start"] = g["start"]
            s["teams"] = [{"name": a["full"]}, {"name": h["full"]}]
            s["espn_filled"] = True
            filled += 1
        else:
            rec["espn_tries"] = rec.get("espn_tries", 0) + 1
            shut = sorted({d.strftime("%Y%m%d") for d in want} & complete)
            if shut:          # checked against a slate that can never change again - never re-read it for this row
                rec["espn_done"] = sorted(set(rec.get("espn_done") or []) | set(shut))
                marked += 1
    LG_LOG.append(f"espn fill: {len(todo)} rows, {len(days)} dates read, {len(complete)} settled, "
                  f"{filled} filled, {marked} closed out, {skipped} skipped as already checked")


# ------------------------------------------------------------------ lanes (Nov 2, Peter: ntfy trades and Street Value separate)
def sv_registry(days=150):
    """Street Value picks from private 'Bets SV' notes: lines 'SV: {\"game\": ..., \"bet\": ..., \"date\": \"YYYY-MM-DD\"}'."""
    out = []
    M = ex.imap_open()
    try:
        for uid in ex.gsearch(M, f'subject:"Bets SV" newer_than:{days}d'):
            typ, d = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not d or not d[0]:
                continue
            for ln in ex.body_text(d[0][1]).splitlines():
                ln = ln.strip()
                if ln.startswith("SV:"):
                    try:
                        out.append(json.loads(ln[3:].strip()))
                    except Exception:
                        pass
    finally:
        ex.imap_close(M)
    return out


def lane_of(s, sv):
    src = s.get("source") or ""
    if src == "bot":
        return "bot"
    if src.startswith("ntfy"):
        return "ntfy (alerts you played)"
    gs = tp(s.get("game_start"))
    bt = tb.toks(s.get("bet")) | tb.toks(s.get("game"))
    for p in sv:
        d = tp((p.get("date") or "") + "T12:00:00Z") if p.get("date") else None
        if d and gs and abs((gs - d).total_seconds()) > 4 * 86400:
            continue
        pz = parsed({"bet": p.get("bet")})
        sz = parsed(s)
        if not pz or not sz or pz[0] != sz[0]:
            continue
        if tb.toks(p.get("game")) & bt and (pz[0] == "total" and pz[1] == sz[1] or tb.toks(str(pz[1])) & tb.toks(str(sz[1]))):
            return "Street Value"
    return "Peter other"


def ncaab_reopen(st, now):
    """Reopen ONCE the settled bot NCAAB rows closed only because NCAAB was not scored (Peter, Nov 16).

    Exactly NCAAB_REOPEN_EXPECT rows must qualify: bot source, NCAAB, done with no CLV, why exactly
    'league NCAAB not covered', game on/after NCAAB_REOPEN_START_ET (ET), never reopened before.
    Any other count reopens NOTHING (fail closed), so no unintended row is ever rescored."""
    if st.get("ncaab_reopen_v1"):
        return "already applied"
    hit = []
    for k, rec in (st.get("bets") or {}).items():
        s_ = rec.get("snap") or {}
        gs = tp(s_.get("game_start"))
        if (s_.get("source") == "bot" and s_.get("league") == "NCAAB" and rec.get("done") and rec.get("clv") is None
                and rec.get("why") == "league NCAAB not covered" and not rec.get("ncaab_reopened")
                and gs and gs.astimezone(ET).strftime("%Y-%m-%d") >= NCAAB_REOPEN_START_ET):
            hit.append(rec)
    if len(hit) != NCAAB_REOPEN_EXPECT:
        return f"refused: {len(hit)} qualifying rows (need exactly {NCAAB_REOPEN_EXPECT})"
    for rec in hit:
        rec["done"], rec["tries"], rec["ncaab_reopened"] = False, 0, iso(now)
    st["ncaab_reopen_v1"] = iso(now)
    return f"reopened {len(hit)}"


def day_listed(lg, gs, st):
    """True when a stored fixture list already covers this league within 12 h of the game start."""
    if not gs:
        return False
    for f in list((st.get("fixtures") or {}).values()) + list(ALT_FX.values()):
        t = tp(f.get("start"))
        if f.get("lg") == lg and t and abs((t - gs).total_seconds()) <= 12 * 3600:
            return True
    return False


def wide_searched_days(st):
    """ET game dates already searched basketball-wide (ledger record + the one-off Nov 17 search store)."""
    days = set((st.get("ncaab_wide_days") or {}).keys())
    try:
        tag = (json.load(open("oddspapi/fixtures_ncaab.json")).get("sportsearch_2026_11_17") or {}).get("window") or []
    except Exception:
        tag = []
    if len(tag) == 2:
        d0, d1 = tag
        x = datetime.strptime(d0, "%Y-%m-%d")
        while x.strftime("%Y-%m-%d") <= d1:
            days.add(x.strftime("%Y-%m-%d"))
            x += timedelta(days=1)
    return days


def ncaab_wide_daily(st, now, game_days, fetched):
    """At most NCAAB_WIDE_DAILY_CAP basketball-wide /fixtures calls per ET day; the OLDEST unsearched game date first,
    window that date + 1 day (under the 48 h limit); never a date already searched; monthly cap respected. Stores
    only fixtures outside the professional/women's competitions, labelled NCAAB; never overwrites a stored fixture."""
    day = now.astimezone(ET).strftime("%Y-%m-%d")
    used = (st.get("ncaab_wide_daily") or {}).get(day, 0)
    if used >= NCAAB_WIDE_DAILY_CAP:
        return f"daily cap reached ({used}/{NCAAB_WIDE_DAILY_CAP}) - no call"
    todo = sorted(set(game_days) - wide_searched_days(st))
    if not todo:
        return "every waiting game date already searched - no call"
    if not can_bill(st, now, 1):
        return "refused: monthly cap - no call"
    d0 = todo[0]
    d1 = (datetime.strptime(d0, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        d = api("/fixtures", True, sportId=11, **{"from": d0, "to": d1})
    except GateRefused:
        return "refused by the credit gate - no call"
    bill(st, now)
    st.setdefault("ncaab_wide_daily", {})[day] = used + 1
    if isinstance(d, dict) and d.get("_error"):
        return f"call failed ({d['_error']}) - date not marked searched"
    st.setdefault("ncaab_wide_days", {})[d0] = iso(now)
    fx, added = st.setdefault("fixtures", {}), 0
    for f in d if isinstance(d, list) else []:
        if not f.get("fixtureId") or f["fixtureId"] in fx or f.get("tournamentId") in NOT_MENS_COLLEGE_TIDS:
            continue
        fx[f["fixtureId"]] = {"lg": "NCAAB", "start": f.get("startTime"), "status": f.get("statusId"),
                              "p1": " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")),
                              "p2": " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")),
                              "n1": f.get("participant1Name"), "n2": f.get("participant2Name"), "wide": True}
        added += 1
    fetched.add("NCAAB")
    return f"billable 1 (date {d0}), fixtures added {added} ({used + 1}/{NCAAB_WIDE_DAILY_CAP} today)"


def ncaab_fx_daily(st, now, lg, lo, hi, fetched):
    """At most NCAAB_DAILY_FX_CAP billable /fixtures calls per ET day, on the verified tournament only, and only when
    the month's cap has room. The day is consumed only when a call actually billed (refresh_fixtures also keeps its
    own 6 h cooldown). -> counts-only status line."""
    if not NCAAB_VERIFIED_TID:
        return "blocked: no verified tournament id - no call"
    if st.get("ncaab_tid") not in (None, NCAAB_VERIFIED_TID):
        return "blocked: stored NCAAB tournament id differs from the verified id - no call"
    day = now.astimezone(ET).strftime("%Y-%m-%d")
    used = (st.get("ncaab_fx_daily") or {}).get(day, 0)
    if used >= NCAAB_DAILY_FX_CAP:
        return f"daily cap reached ({used}/{NCAAB_DAILY_FX_CAP}) - no call"
    if not can_bill(st, now, 1):
        return "refused: monthly cap - no call"
    st["ncaab_tid"] = NCAAB_VERIFIED_TID
    u0 = used_this_period(st, now)
    ok = refresh_fixtures(st, now, lg, (lo - timedelta(days=1)).astimezone(ET), (hi + timedelta(days=1)).astimezone(ET))
    spent = used_this_period(st, now) - u0
    if spent:
        st.setdefault("ncaab_fx_daily", {})[day] = used + spent
        st["ncaab_fx_daily"] = {d: n for d, n in st["ncaab_fx_daily"].items() if d >= (now - timedelta(days=14)).astimezone(ET).strftime("%Y-%m-%d")}
    if ok:
        fetched.add(lg)
    return f"billable {spent}, fixtures call {'ok' if ok else 'not made/failed'} ({used + spent}/{NCAAB_DAILY_FX_CAP} today)"


def ncaab_fx_once(st, now, lg, lo, hi, fetched):
    """Peter, Nov 16 14:08: at most TWO billable calls, ONCE, to recover fixtures for the four
    reopened NCAAB bot rows - a tournament lookup only if no id is stored, plus one /fixtures.
    Refuses without spending unless the month's credit gate has room for every call it may make.
    The once-flag is set as soon as any call has billed, so no later run can repeat it."""
    if st.get("ncaab_fx_once"):
        return "already used"
    if os.path.exists("oddspapi/fixtures_ncaab.json"):   # the isolated ncaab-fx job spent the one call
        return "already used (isolated recovery store present)"
    if not NCAAB_VERIFIED_TID:
        return "blocked: no verified NCAA Division I men's tournament id - no paid call made"
    if st.get("ncaab_tid") not in (None, NCAAB_VERIFIED_TID):
        return "blocked: stored NCAAB tournament id differs from the verified id - no paid call made"
    st["ncaab_tid"] = NCAAB_VERIFIED_TID
    n = 1
    used0 = used_this_period(st, now)
    if not can_bill(st, now, n):
        return f"refused: budget would not cover {n} call(s) (used {used0} of {CAP})"
    ok = refresh_fixtures(st, now, lg, (lo - timedelta(days=1)).astimezone(ET), (hi + timedelta(days=1)).astimezone(ET))
    spent = used_this_period(st, now) - used0
    if spent:
        st["ncaab_fx_once"] = {"at": iso(now), "billable": spent, "fixtures_ok": bool(ok)}
    if ok:
        fetched.add(lg)
    n_fx = sum(1 for f in (st.get("fixtures") or {}).values() if f.get("lg") == lg)
    return f"billable {spent} (tid {'stored' if n == 1 else 'looked up'}), fixtures call {'ok' if ok else 'not made/failed'}, {lg} fixtures cached {n_fx}"


# ------------------------------------------------------------------ main
# Nov 4 (Peter 14:56 "yes"): Pinnacle's LIMIT at the bet's placed time, on every scored fill (read-only, from the same history
# the close comes from). LOW = at or below the P-limit test's frozen FIT median for that league x market (Item 56, Nov 4);
# markets without a frozen cut fall back to the board lab's league median. A split, never a filter.
PLIM_CUT = {("NBA", "spread"): 4464, ("NBA", "total"): 1808, ("NCAAF", "spread"): 10992, ("NCAAF", "total"): 3101,
            ("NFL", "total"): 16892, ("NHL", "total"): 2324}
PLIM_LEAGUE = {"NBA": 4578, "NCAAF": 10586, "NFL": 19206, "NHL": 3536}


def plimit_tag(s, f, pin, mkmap, lg, when):
    """{limit, cut, grp} or None: Pinnacle's raw limit on the held side at `when` (last tick within 60 min)."""
    try:
        import plimit_level as pl   # lazy: plimit_level imports this module
        if when.tzinfo is None:   # Nov 4: a naive 'placed' stamp (Novig created_at) raised against aware ticks -> no read
            when = when.replace(tzinfo=timezone.utc)
        lim, how = pl.pin_limit_at(s, f, pin, mkmap, when, lg)
    except Exception as e_:
        return {"why": f"{type(e_).__name__}: {str(e_)[:60]}"}
    if not lim:
        return {"why": "no Pinnacle tick within 60 min of placed time"}
    pz = parsed(s)
    mk = {"ml": "moneyline", "spread": "spread", "total": "total"}.get(pz[0] if pz else "", "")
    cut = PLIM_CUT.get((lg, mk)) or PLIM_LEAGUE.get(lg)
    out = {"limit": round(lim), "how": how, "cut": cut,
           "grp": (None if not cut else ("LOW" if lim <= cut else "HIGH"))}
    if not cut:
        # Nov 18: a limit WAS read but no frozen Item 56 cut exists for this league x market, so the row
        # cannot be grouped. Without a reason it fell into plim_stats' bucket as "not tried", which is
        # false - it was tried and it worked. No cut is invented here: freezing an NCAAB median is a
        # decision and a FIT window, not a side effect of a report.
        out["why"] = f"limit read, but no frozen Item 56 cut for {lg} x {mk or '?'} - not grouped"
    return out


def units_of(r):
    """Flat 1u result for a scored bet from its tracker result and after-fee price; None if unknown."""
    res = (r["snap"].get("result") or "").upper()
    d = eff_dec(r["snap"])
    if not d or res not in ("W", "L", "P", "WIN", "LOSS", "PUSH"):
        return None
    return (d - 1) if res in ("W", "WIN") else (-1.0 if res in ("L", "LOSS") else 0.0)


def plim_stats(rows):
    g = [r for r in rows if r.get("plimit", {}).get("grp")]
    out = []
    for grp in ("LOW", "HIGH"):
        xs = [r for r in g if r["plimit"]["grp"] == grp]
        u = [units_of(r) for r in xs]
        u = [x for x in u if x is not None]
        out.append(f"{grp} {lane_stats(xs)}" + (f", units {sum(u):+.2f}u on {len(u)}" if u else ""))
    miss = [r.get("plimit", {}).get("why") or "not tried" for r in rows if not r.get("plimit", {}).get("grp")]
    top = ""
    if miss:
        from collections import Counter
        top = " (" + "; ".join(f"{k} x{v}" for k, v in Counter(miss).most_common(2)) + ")"
    return " || ".join(out) + f" | no limit read: {len(miss)}{top}"


def lane_stats(rows):
    n = len(rows)
    if not n:
        return "-"
    avg = sum(r["clv"] for r in rows) / n
    beat = sum(1 for r in rows if r["clv"] > 0)
    return f"n {n}, avg CLV {100 * avg:+.2f}%, beat close {beat}/{n}"


V2STAT = collections.Counter()   # Nov 19: shadow-V2 coverage, counts only
_T0 = [None]


def _stage(name):
    """Seconds since the run began, printed at each stage boundary. Nov 19 (Peter): six consecutive
    runs were killed at the 40-minute timeout and left NO trace of where the time went - this script
    prints nothing until it finishes, so even the successful runs were a 32-minute black box. Timing
    only: no counts of money, no bet text. Without this the next growth is diagnosed by guessing,
    which is exactly how the liquidity-extra league list went wrong."""
    import time as _t
    if _T0[0] is None:
        _T0[0] = _t.time()
    print(f"  [stage] {name:<34} t+{_t.time() - _T0[0]:6.1f}s", flush=True)


def main():
    _stage("start")
    global SIDE_EV
    SIDE_EV = load_side_evidence()   # 16 Nov: registry-verified sides for line-only Polymarket rows (read-only)
    SIDE_LOG[f"evidence: venue links {len(SIDE_EV[0])}, ledger orders {len(SIDE_EV[1])}"] += 1
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
    _stage("capture tracker rows")
    # 1) capture: keep each bet's first-seen price/stake/payout (a later settlement row can drop them for losses)
    for k, b in tracker.items():
        rec = st["bets"].setdefault(k, {"first_seen": iso(now)})
        snap = rec.setdefault("snap", {})
        for f in ("book", "game", "bet", "flip", "league", "source", "teams", "game_start", "placed", "settled", "first_seen"):
            if b.get(f) not in (None, "", []):
                snap[f] = b[f]
        if not snap.get("side_verified") and str(k).startswith("pm|"):
            _sv, _svw = registry_side(k, snap, *SIDE_EV)
            if not _sv:
                SIDE_LOG["refused: " + re.sub(r"\d+", "N", _svw)] += 1
            if _sv:
                snap["side_verified"], snap["side_src"] = _sv, _svw   # a full spread bet: "<team> <line>"
                SIDE_LOG["side recovered"] += 1
        try:
            PROV["snap_" + copy_phase1(snap, b, iso(now))] += 1   # P1-A/C: gated, never relabels history
        except Exception as _ce:
            PROV["snap_failed"] += 1
        for f in ("price", "stake", "to_pay"):
            if b.get(f) not in (None, "") and snap.get(f) in (None, ""):
                snap[f] = b[f]
        if b.get("result"):
            snap["result"] = b["result"]
        for _f in apply_settled_amounts(snap, b):
            PROV["settled_amount_" + _f] += 1
        # Stage 3 (Peter, Nov 13): capture profit so ROI is computable at all. The snapshot has
        # always taken stake and to_pay but never profit, so profit summed to zero across the
        # whole ledger and any ROI figure built from it was a fabricated +0.00% - which is how the
        # first Stage 2 report printed one for every source. Additive: a new field, no existing
        # value altered, and it arrives at settlement like result, so it is refreshed not frozen.
        if b.get("profit") is not None:
            snap["profit"] = b["profit"]
    # 1b) tracker rows with no game attached (older settled rows): find the game on ESPN (free) near when it settled
    try:
        espn_fill(st, now)
    except Exception as e:
        st.setdefault("errors", []).append(f"{iso(now)} espn fill: {type(e).__name__}")
    _stage("bot novig orders")
    # 2) bot Novig orders for the stale check
    nvo, fills = [], []
    _uid_cache = st.setdefault("bot_live_uids", {})
    try:
        _orders, _note = bot_novig_orders(cache=_uid_cache)
        fills = [x for x in (order_as_bet(o) for o in _orders) if x]
        nvo = [x for x in fills if x.get("book") == "novig" and (tp(x.get("decided_utc")) or now) > now - timedelta(days=10)]
        if _note:
            # Peter, Nov 19: never treat a timeout or a missing read as zero fills. The cached
            # evidence still stands; say the read was partial and carry on with what we hold.
            st.setdefault("errors", []).append(f"{iso(now)} novig orders: {_note}")
            print(f"bot Novig orders: PARTIAL READ - {_note}. Cached evidence retained, NOT read as zero fills.", flush=True)
    except Exception as e:
        st.setdefault("errors", []).append(f"{iso(now)} novig orders: {type(e).__name__}")
        print(f"bot Novig orders: READ FAILED ({type(e).__name__}). No fill evidence added this run; "
              f"this is NOT evidence of zero fills.", flush=True)
    print(f"bot Novig orders: {len(fills)} order(s) from {_uid_cache.get('seen_last_run', 0)} message(s); "
          f"{_uid_cache.get('fetched_last_run', 0)} newly fetched, "
          f"{max(_uid_cache.get('seen_last_run', 0) - _uid_cache.get('fetched_last_run', 0), 0)} served from cache", flush=True)
    # Nov 2 (Peter, "you have bot fills"): a bet whose price the tracker lost (Novig losses) takes the bot's own fill price
    for k, rec in st["bets"].items():
        s = rec["snap"]
        if s.get("price_af") is None and not (s.get("stake") and s.get("to_pay")) and s.get("price") in (None, ""):
            f = fill_for(s, fills)
            if f:
                s["price_af"], s["price_from"] = f["price"], "bot fill record"
                if rec.get("why") == "no price on the bet":
                    for x in ("done", "tries", "why"):
                        rec.pop(x, None)
    # Nov 4: bot rows carry no placed time (positions have none) - take the executor's decision time from its own fill record
    for k, rec in st["bets"].items():
        s = rec["snap"]
        if not s.get("placed_bot") and (s.get("source") or "").lower().startswith("bot") and not tp(s.get("placed")):
            try:
                f = fill_for({**s, "price": None}, fills)   # price-blind match: game + league + bet
            except Exception:
                f = None
            if f and f.get("decided_utc"):
                s["placed_bot"] = f["decided_utc"]
                if (rec.get("plimit") or {}).get("why"):   # a failed read on a stale time: read it again
                    for fld in ("clv", "close_p", "eff_am", "close_am", "how", "age_min", "scored", "plimit"):
                        rec.pop(fld, None)
    for k, rec in st["bets"].items():   # Nov 2 (Peter "do it"): Novig losses now carry their price from the tracker - retry them
        if rec.get("why") == "no price on the bet" and eff_dec(rec["snap"]):
            for x in ("done", "tries", "why"):
                rec.pop(x, None)
    for o in nvo:
        st.setdefault("novig_checks", {}).setdefault(o["id"], {"snap": o})
    # The fixture stores other jobs in this repo maintain. Loaded once per run and used ONLY
    # when the ledger's own matcher has already failed, so nothing about the existing path
    # changes. Peter, Nov 13: "Make the live scorer read the same fixture and historical-odds
    # caches as the scorecard, using the verified fallback."
    global ALT_FX, ALT_SRC
    _alt = fxm.alt_fixtures()
    ALT_FX = {fid: f for fid, (f, _src) in _alt.items() if fid not in (st.get("fixtures") or {})}
    ALT_SRC = {fid: src for fid, (_f, src) in _alt.items()}
    print(f"fixtures: {len(ALT_FX)} additional fixture(s) available from "
          f"{sorted(set(ALT_SRC.values()))}", flush=True)
    # Peter, Nov 13, priority 2: fill the missing leagues BEFORE anything tries to match a
    # fixture, since a row with no league can never match one.
    try:
        _n_lg = recover_leagues(st, now)
    except Exception as _lg_ex:
        _n_lg = 0
        LG_LOG.append(f"league recovery skipped ({type(_lg_ex).__name__}) - no row was changed")
    for _ln in LG_LOG:
        print(f"leagues: {_ln}", flush=True)
    mkmap = load_markets(st, now)
    if st.get("rescored_v3") is None:   # v3 (Nov 2): line-distance guard; score everything again once
        st.pop("rescored_v2", None)
        st["rescored_v3"] = iso(now)
    if not st.get("plimit_v4"):   # Nov 4: read Pinnacle's limit at placed time on every already-scored bet, once (v4: dense history)
        for rec in st["bets"].values():
            if rec.get("clv") is not None and not (rec.get("plimit") or {}).get("grp"):
                for fld in ("clv", "close_p", "eff_am", "close_am", "how", "age_min", "scored", "plimit"):
                    rec.pop(fld, None)
        st["plimit_v1"] = st["plimit_v2"] = st["plimit_v3"] = st["plimit_v4"] = iso(now)
    if not st.get("rescored_v2"):   # v1 freshness rule could pick an alt line as main: score everything again once
        for rec in st["bets"].values():
            for f in ("clv", "close_p", "eff_am", "close_am", "how", "age_min", "scored", "done", "tries", "why", "fixture"):
                rec.pop(f, None)
        st["rescored_v2"] = iso(now)
    # Reopen ONCE a row that gave up only because its side was unknown and now has a registry-verified side.
    for k, rec in st["bets"].items():
        s_ = rec.get("snap") or {}
        if (rec.get("done") and rec.get("clv") is None and s_.get("side_verified") and not rec.get("side_reopened")
                and str(rec.get("why") or "").startswith("the bet text is")):
            rec["done"], rec["tries"], rec["side_reopened"] = False, 0, iso(now)
            SIDE_LOG["reopened"] += 1
    print(f"CLV ledger verified-side recovery (counts only): {dict(SIDE_LOG) or 'none'}", flush=True)
    print(f"CLV ledger NCAAB reopen (counts only): {ncaab_reopen(st, now)}", flush=True)
    _stage("league fixture list")
    # 3) which leagues need fixtures
    pend = []
    for k, rec in st["bets"].items():
        s = rec["snap"]
        if rec.get("clv") is not None or rec.get("done"):
            continue
        gs = tp(s.get("game_start"))
        # Nov 12: a row with no game_start used to fall out here silently - no attempt, no try
        # counted, and no reason stored on the record, which is why four graded ProphetX losses
        # read "clv None, tries None" with nothing to say why. The skip itself is correct (a
        # closing line cannot be read without knowing when the game started); what was wrong is
        # that it left no trace. Recording the reason changes no decision and no stored CLV - it
        # only makes the row say why it is waiting.
        if not gs:
            rec["why"] = "no game_start on the row - never attempted, not failed"
            continue
        if now < gs + timedelta(minutes=SCORE_AFTER_MIN):
            rec["why"] = "game not started"
            continue
        pend.append((k, rec))
    for k, rec in (st.get("novig_checks") or {}).items():
        if rec.get("done"):
            continue
        pend.append((k, rec))
    pend, _q = grading_queue(pend, now)
    LG_LOG.append(_q)

    need = {}
    # Stage 4 (Peter, Nov 13): the newest fixture the cache holds per league. A pending game that
    # starts after it was never offered to the matcher at all, which is a FETCH question and the
    # one case allowed to override the 6 h cooldown - once per league per ET day.
    newest = {}
    for f in (st.get("fixtures") or {}).values():
        d = tp(f.get("start"))
        lgf = f.get("lg")
        if d and lgf and (lgf not in newest or d > newest[lgf]):
            newest[lgf] = d
    beyond = {}
    wide_days = set()      # NCAAB game dates needing a basketball-wide search (Nov 17)
    for k, rec in pend:
        s = rec["snap"]
        lg = s.get("league")
        if lg not in SCORE_SPORT:
            continue
        if rec.get("fixture") or find_fixture(st, s):
            continue
        if lg in CACHE_ONLY_FX and fxm.ordered_match(s, ALT_FX, tp)[0]:
            continue          # already held by an alternate store: never pay for it again
        if lg in CACHE_ONLY_FX and day_listed(lg, tp(s.get("game_start")), st):
            # The regular-season list for that day is on file and the game is not in it: a basketball-wide search
            # (filed under another competition) is the only lookup that could help - never the same list again.
            _gd = tp(s.get("game_start")).astimezone(ET).strftime("%Y-%m-%d")
            wide_days.add(_gd)
            continue
        d0 = max(tp(s.get("game_start") or s.get("decided_utc")) or now, now - timedelta(days=FETCH_DAYS))   # keep the call small
        lo, hi = need.get(lg, (d0, d0))
        need[lg] = (min(lo, d0), max(hi, d0))
        gs = tp(s.get("game_start"))
        if gs and (lg not in newest or gs > newest[lg]):
            beyond[lg] = beyond.get(lg, 0) + 1
    fetched = set()        # leagues whose fixtures were ACTUALLY re-read from OddsPapi this run
    if wide_days:
        print(f"CLV ledger NCAAB basketball-wide lookup (counts only): {ncaab_wide_daily(st, now, wide_days, fetched)}",
              flush=True)
    for lg, (lo, hi) in need.items():
        if lg in CACHE_ONLY_FX:
            print(f"CLV ledger NCAAB daily fixture lookup (counts only): {ncaab_fx_daily(st, now, lg, lo, hi, fetched)}",
                  flush=True)
            continue
        if lg in beyond:
            FX_LOG.append(f"{lg}: {beyond[lg]} pending game(s) start after the newest cached fixture "
                          f"({newest.get(lg) and newest[lg].astimezone(ET).strftime('%Y-%m-%d %H:%M') or 'none cached'})")
        if refresh_fixtures(st, now, lg, (lo - timedelta(days=1)).astimezone(ET),
                            (hi + timedelta(days=1)).astimezone(ET), allow_extra=(lg in beyond)):
            fetched.add(lg)
    for _ln in FX_LOG:
        print(f"fixtures: {_ln}", flush=True)
    _stage("SCORE (history calls)")
    # 4) score: free history calls, one per fixture and book
    hist = {}
    new_scored = 0
    for k, rec in pend:
        rec["last_try"] = iso(now)   # Nov 19: what rotates the backlog. Stamped on every row REACHED,
        s = rec["snap"]              # including ones that fall out below, so the queue cannot stall
        lg = s.get("league")         # on a head that is skipped for the same reason every run.
        if lg not in SCORE_SPORT:
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = f"league {lg or 'unknown'} not covered"
            if lg or rec["tries"] >= MAX_TRIES:
                rec["done"] = True
            continue
        fid = rec.get("fixture") or find_fixture(st, s)
        if not fid:
            # Stage 3 of Peter's Nov 13 list: the live scorer now reads the SAME fixture stores
            # the scorecard reads, through the SAME matcher, instead of only its own cache. The
            # Nov 12 Louisiana row sat unscored for a day while the fixture for that exact game
            # was already on disk in oddspapi/fixtures.json - two caches, one of which the scorer
            # had never been told about. ALT is loaded once per run, above.
            _fid, _note = fxm.ordered_match(s, ALT_FX, tp)
            if _fid:
                fid = _fid
                rec["fixture_src"] = {"from": ALT_SRC.get(_fid, "alt cache"), "how": _note,
                                      "at": iso(now)}       # audit trail: where this came from
                # Copy the fixture into our own cache. Without this the row scores but is then
                # UNVALIDATABLE - fixture_check reports "stored fixture is no longer in the
                # cache" and the Nov 5 fail-closed rule drops it from the headline, so the row
                # would carry a CLV that no figure ever counts. The Louisiana row did exactly
                # that on the first run of this change. Fixtures are public reference data and
                # this only ever ADDS: an id already in st["fixtures"] is never overwritten.
                if _fid not in (st.get("fixtures") or {}):
                    st.setdefault("fixtures", {})[_fid] = ALT_FX[_fid]
                FX_LOG.append(f"recovered fixture for {k[:28]}: {_fid} from "
                              f"{ALT_SRC.get(_fid, '?')} ({_note})")
        if not fid:
            # Nov 5 (Peter): only a run that actually looked fixtures up for this league may burn a
            # retry. The ledger runs every 2 h but refresh_fixtures has a 6 h cooldown, so roughly two
            # runs in three would otherwise exhaust MAX_TRIES against an UNCHANGED cache in about 16
            # hours - which is how the 70 rows recovered on Nov 5 died in the first place. espn_fill
            # already guards the same way ("this bet's dates weren't fetched this run").
            if lg in fetched:
                rec["tries"] = rec.get("tries", 0) + 1
                rec["why"] = "no OddsPapi fixture matched"
                if rec["tries"] >= MAX_TRIES:
                    rec["done"] = True
            elif lg in CACHE_ONLY_FX:
                # Nov 17: this said "not in any cached store; waiting for the capped daily lookup" even AFTER that
                # lookup had run and the game simply did not match - so a genuinely UNMATCHED row (Central Arkansas)
                # was filed in the trend log as "fixture not yet fetched", which reads as "more data will fix it".
                # day_listed answers which state we are in: a stored list already covering this game's day means the
                # lookup happened, so the row is unmatched and the try counts toward done.
                if day_listed(lg, tp(s.get("game_start")), st):   # THIS row's start; gs above belongs to another loop
                    rec["tries"] = rec.get("tries", 0) + 1
                    rec["why"] = f"no OddsPapi fixture matched ({lg} list for this date is already cached)"
                    if rec["tries"] >= MAX_TRIES:
                        rec["done"] = True
                else:
                    rec["why"] = (f"{lg} fixture not in any cached store; waiting for the capped daily {lg} lookup "
                                  "(1 paid call per ET day) - retry not counted")
            else:
                rec["why"] = "no fixture yet - no fresh lookup this run (6 h cooldown), retry not counted"
            continue
        f = (st.get("fixtures") or {}).get(fid) or ALT_FX.get(fid)
        if not f:
            rec.pop("fixture", None)
            continue
        rec["fixture"] = fid
        start = tp(f["start"]) or tp(s.get("game_start"))
        is_nv = k.startswith("nvo|")
        if not is_nv and now < start + timedelta(minutes=SCORE_AFTER_MIN):
            continue
        bk = "novig.us" if is_nv else "pinnacle"   # OddsPapi slug for Novig is novig.us   # one book per call: a bad slug never costs the Pinnacle read
        if (fid, bk) not in hist and len(hist) >= MAX_HIST:
            continue   # backfill spreads over runs (history throttles at ~8 s a call)
        if (fid, bk) not in hist:
            if bk == "pinnacle":
                # Nov 4: Pinnacle history through the shared cache (paid "pinnacle+30" ticks, as Item 56 reads it). The free
                # key's "pinnacle" history is sparse away from the close, so limit-at-placed reads found no tick within 60 min.
                try:
                    import hist_cache as hc   # lazy: hist_cache imports this module
                    hist[(fid, bk)] = hc.get_hist(fid, ["pinnacle"], start)
                except Exception as e_:
                    hist[(fid, bk)] = {"_error": f"cache: {str(e_)[:40]}"}
                if isinstance(hist[(fid, bk)], dict) and hist[(fid, bk)].get("_error"):
                    hist[(fid, bk)] = api("/historical-odds", False, fixtureId=fid, bookmakers=bk)
            else:
                hist[(fid, bk)] = api("/historical-odds", False, fixtureId=fid, bookmakers=bk)
        h = hist[(fid, bk)]
        if isinstance(h, dict) and h.get("_error"):
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = f"history HTTP {h['_error']}"
            continue
        if is_nv:
            when = tp(s.get("decided_utc"))
            got = novig_at(s, f, book_markets(h, "novig.us"), mkmap, when, lg) if when else None
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
            if record_v2(rec, c, d):
                V2STAT["scored with a shadow V2"] += 1
                if rec.get("v2_derived"):
                    V2STAT["V2 differs: our number was an ALT at close"] += 1
            try:
                PROV[stamp_entry(rec, s, c, start, now)] += 1
            except Exception as _pe:   # never costs the score, but never silent either (review R1)
                rec["entry_prov_status"] = f"failed: {type(_pe).__name__}"
                PROV["failed"] += 1
            # Nov 4: bot rows carry no 'placed' (positions have no order time) -> fall back to when the tracker, then
            # this ledger, first saw the bet (<= ~2h after placement; the limit read is the last Pinnacle tick before it)
            when, basis = None, None
            for fld, nm in (("placed", "placed"), ("decided_utc", "placed"), ("placed_bot", "bot decision"), ("first_seen", "first seen (tracker)")):
                when = tp(s.get(fld))
                if when:
                    basis = nm
                    break
            if not when and tp(rec.get("first_seen")):
                when, basis = tp(rec["first_seen"]), "first seen (ledger, <=2h late)"
            if when:
                pt = plimit_tag(s, f, book_markets(h, "pinnacle"), mkmap, lg, when)
                if pt:
                    pt["basis"] = basis
                    rec["plimit"] = pt
            else:
                rec["plimit"] = {"why": "no placed / first-seen time on the row"}
        else:
            rec["tries"] = rec.get("tries", 0) + 1
            rec["why"] = why or "no price on the bet"
            if rec["tries"] >= MAX_TRIES or (why and ("not parsed" in why or "not comparable" in why or "far from" in why)) or not d:
                rec["done"] = True
    _stage("report build")
    # 5) report
    # Nov 5 (Peter): the doubt marker is STICKY. A row found doubtful is written with fixture_doubt
    # and stays out of every figure even after its fixture leaves the cache, so neither expiry nor a
    # routine refresh can restore it. Only the marker is written - never the fixture, price or clv -
    # and nothing in this file ever clears it: that needs the real game established and the CLV
    # recalculated, which is a decision, not a side effect.
    for k, rec in st["bets"].items():
        if rec.get("clv") is None:
            continue
        apply_doubt(st, rec, now)
    # Nov 10 (Peter, Option 2): EXCLUDE AT READ TIME, preserve the stored state. man_id changed on Nov 5 and
    # man_migrate retires the old key in the TRACKER, but this file only setdefault()s keys into st["bets"] and
    # prunes by age, so a retired key survived here for 60 days with the snapshot it froze with - including, in
    # some rows, the invented stake the old sizing rule guessed. Those rows were counted a SECOND time beside the
    # live row. The test is tracker presence plus man_id resolution, never game/line/price identity; an orphan that
    # does not resolve is left in and flagged. Nothing is written or deleted: st["bets"] is untouched and the rows
    # return by themselves if a tracker key ever comes back.
    stale, stale_unproven = cstale.stale_map(st["bets"], tracker), cstale.orphans_unproven(st["bets"], tracker)
    all_scored = sorted([dict(r, id=k) for k, r in st["bets"].items()
                         if r.get("clv") is not None and k not in stale],
                        key=lambda r: r.get("scored") or "")
    held = [r for r in all_scored if r.get("fixture_doubt")]        # sticky - out of every figure
    hid = {r["id"] for r in held}
    rest = [r for r in all_scored if r["id"] not in hid]

    def _unverified(r):
        """FAIL CLOSED (Peter, Nov 5): a row with no currently validated fixture AND no durable record
        of a prior validation of that same fixture is excluded, not counted. Previously these were
        counted, which let an unverifiable row sit inside the verified headline."""
        if fixture_check(st, r)[0] != "unvalidatable":
            return False
        prev = r.get("fixture_ok") or {}
        return not (prev.get("fixture") and prev["fixture"] == r.get("fixture"))
    unvalidated = [(r, fixture_check(st, r)[1]) for r in rest if _unverified(r)]
    uid = {r["id"] for r, _ in unvalidated}
    scored = [r for r in rest if r["id"] not in uid]
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
        # Stage 2 (Peter, Nov 13, "publish the new selection-level scorecard as the official
        # measurement basis; preserve the historical per-fill report for audit purposes"). With
        # CLV_SELECTION_MODE=on the selection-level figures lead and the per-fill figures follow,
        # explicitly labelled and unchanged, so nothing is lost. One strategy selection is one
        # observation however many pieces it filled in: Nov 12's Toronto Under 223.5 is one bet
        # and 13 ProphetX fills. Both halves use the SAME deduplicated basis - splitting a
        # deduplicated sample with a per-fill split would reintroduce the weighting it removes.
        if SELECTION_MODE:
            try:
                import clv_selection as csel
                _obs = list(csel.selections({r["id"]: r for r in scored}, tracker).values())
                _h1, _h2, _nod = csel.halves(_obs)

                def _fmt(tag, s_):
                    if not s_.get("n"):
                        return f"{tag}: n 0"
                    _se = f" +/-{100 * s_['se']:.2f} (1 s.e.)" if s_.get("se") is not None else ""
                    # ROI says UNAVAILABLE rather than 0.00% when no row carries a profit - a
                    # fabricated zero is worse than a blank (it printed one for every source once).
                    _roi = (f", ROI {s_['roi_pct']:+.2f}% on {s_['n_settled']} settled"
                            if s_.get("roi_pct") is not None
                            else f", ROI UNAVAILABLE ({s_.get('has_profit', 0)}/{s_['n']} rows carry profit)")
                    return (f"{tag}: n {s_['n']} from {s_['fills']} fills, mean CLV "
                            f"{100 * s_['mean']:+.2f}%{_se}, beat close {s_['pos']}/{s_['n']}{_roi}")

                L.append("OFFICIAL BASIS - SELECTION LEVEL (one bet = one observation, however many fills):")
                L.append("  " + _fmt("ALL selections", csel.stats(_obs)))
                L.append("  " + _fmt("first half ", csel.stats(_h1)))
                L.append("  " + _fmt("second half", csel.stats(_h2)))
                if _nod:
                    L.append(f"  excluded from the half split (no game start): {len(_nod)}")
                L.append("")
                L.append("PER-FILL (audit basis, retained unchanged - every fill counted separately):")
            # NOT `as ex`: this module imports executor as ex at line 29, and `except ... as ex`
            # makes ex function-local for the WHOLE of main() and then DELETES it when the block
            # ends, so the later ex.send() died with UnboundLocalError. It cost a run and two
            # billable fixture calls that were then discarded unwritten.
            except Exception as _sel_ex:
                L.append(f"SELECTION-LEVEL unavailable ({type(_sel_ex).__name__}) - "
                         f"the per-fill figures below are the basis for this run")
        L.append(f"ALL scored: {lane_stats(scored)}")
        L.append(f"  bot: {lane_stats(bot)} | rolling 50: {lane_stats(bot[-50:])}")
        L.append(f"  Peter/other: {lane_stats(man)} | rolling 50: {lane_stats(man[-50:])}")
        if stale or stale_unproven:
            L += ["", "STALE ROWS EXCLUDED AT READ TIME (Peter, Nov 10 - stored state preserved, nothing deleted):",
                  f"  {cstale.note(stale, stale_unproven)}"]
            for k, tgt in sorted(stale.items()):
                s = (st["bets"][k].get("snap") or {})
                L.append(f"  {s.get('book') or '?'} {(s.get('bet') or '')[:30]} | stale id {str(k)[:14]}.. duplicates "
                         f"live tracker id {str(tgt)[:14]}.. | its frozen stake {s.get('stake')}")
            if stale_unproven:
                L.append("  UNPROVEN orphans (absent from the tracker but nothing resolves to them): KEPT in every")
                L.append("  figure above, because an aged-out tracker row is not evidence of a duplicate.")
                for k in stale_unproven:
                    s = (st["bets"][k].get("snap") or {})
                    L.append(f"    {s.get('book') or '?'} {(s.get('bet') or '')[:30]} | id {str(k)[:18]}.. | "
                             f"first_seen {(st['bets'][k].get('first_seen') or '')[:16]}")
        if held:
            L += ["", f"HELD OUT of every figure above ({len(held)}) - the stored fixture no longer passes the",
                  "matcher, so the game assignment is doubtful. Nothing was changed: the row keeps its CLV, its",
                  "fixture and its price, and it returns to these figures by itself once the assignment is",
                  "re-established. Excluded from the rolling 50 and from the kill-switch arithmetic."]
            for r in held:
                s, fx = r["snap"], ((st.get("fixtures") or {}).get(r.get("fixture")) or {})
                d = r.get("fixture_doubt") or {}
                # Nov 18: print the row id. The UNPROVEN-orphan block above already prints one, and
                # without it a held-out row cannot be named to clv_fixture_repair, whose allowlist is
                # BY ID - so the one action that resolves these rows had no way to reference them. The
                # id is an identifier, not a dollar figure, and this email is the private channel.
                L.append(f"  {s.get('league') or '?'} {s.get('book') or '?'} {(s.get('bet') or '')[:26]} | "
                         f"CLV {100 * r['clv']:+.2f}% | id {r.get('id') or r.get('key') or '?'} | "
                         f"stored fixture points at "
                         f"{(fx.get('n1') or fx.get('p1') or '?')[:22]} vs {(fx.get('n2') or fx.get('p2') or '?')[:22]}")
                L.append(f"      flagged {(d.get('since') or '')[:16]}: {d.get('why') or '?'}")
                now_v, now_w = fixture_check(st, r)
                L.append(f"      re-checked now: {now_v}" + (f" - {now_w}" if now_w else "")
                         + ". Stays out until the real game is established and the CLV recalculated.")
        if unvalidated:
            L += ["", f"EXCLUDED AS UNVERIFIED ({len(unvalidated)}) - no currently validated fixture and no durable",
                  "record of a prior validation of that same fixture, so the assignment cannot be verified at all.",
                  "These are NOT counted above: the headline fails closed rather than carry an unverifiable row.",
                  "A row validated earlier, while its fixture was cached, keeps that validation and stays counted."]
            for r, why_ in unvalidated:
                s = r["snap"]
                L.append(f"  {s.get('league') or '?'} {s.get('book') or '?'} {(s.get('bet') or '')[:26]} | "
                         f"CLV {100 * r['clv']:+.2f}% | {why_}")
        try:
            sv = sv_registry()
        except Exception:
            sv = []
        lanes = {}
        for r in scored:
            lanes.setdefault(lane_of(r["snap"], sv), []).append(r)
        L.append(f"  LANES (Street Value picks on file: {len(sv)}):")
        for ln_ in ("bot", "ntfy (alerts you played)", "Street Value", "Peter other"):
            v = lanes.get(ln_, [])
            L.append(f"    {ln_}: {lane_stats(v)} | rolling 50: {lane_stats(v[-50:])}")
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
        L += ["", "PINNACLE LIMIT AT PLACED TIME (split, not a filter; LOW = at or below the Item 56 frozen league x market median):",
              f"  bot: {plim_stats(bot)}", f"  Peter/other: {plim_stats(man)}"]
        for ln_ in ("bot",):
            for lg_ in ("NBA", "NFL", "NCAAF", "NHL"):
                v = [r for r in lanes.get(ln_, []) if r["snap"].get("league") == lg_]
                if v:
                    L.append(f"    bot {lg_}: {plim_stats(v)}")
        L += ["", "LAST 30 SCORED (newest first):"]
        for r in scored[::-1][:30]:
            s = r["snap"]
            L.append(f"  {(s.get('game_start') or '')[:10]} {s.get('league')} {s.get('book')} [{lane_of(s, sv)}] "
                     f"{s.get('bet')} | you {r['eff_am']:+d} after fee, close fair {r['close_am']:+d} ({r['how']}, "
                     f"tick {r['age_min']} min pre-start) -> CLV {100 * r['clv']:+.1f}%"
                     + (f" | P limit {r['plimit']['limit']:,} {r['plimit']['grp'] or ''} @{r['plimit'].get('basis') or 'placed'}" if (r.get("plimit") or {}).get("limit")
                        else f" | P limit: {r['plimit']['why']}" if (r.get("plimit") or {}).get("why") else "")
                     if r.get("eff_am") and r.get("close_am") else
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
        # Nov 18 (Peter): SAMPLE VISIBILITY. The scored basis and the stuck-row count, both BY BOOK, so
        # the sample growing is visible in the report rather than history being quietly restated. A row
        # with no game_start is never attempted, and until Nov 18 the Kalshi and Polymarket US readers
        # never set that field - their settled rows are minted under a different id than the open row
        # that knew the start, so unlike Novig they inherited nothing. These two lines are how we see
        # whether the fix actually moved them; they decide nothing.
        def _bk(r):
            return str((r.get("snap") or {}).get("book") or "?")
        sc_by, st_by = {}, {}
        for k, r in st["bets"].items():
            b = _bk(r)
            if r.get("clv") is not None:
                sc_by[b] = sc_by.get(b, 0) + 1
            elif not r["snap"].get("game_start"):
                st_by[b] = st_by.get(b, 0) + 1
        L.append(f"  SCORED by book: {', '.join(f'{b} {sc_by[b]}' for b in sorted(sc_by)) or 'none'}")
        L.append(f"  STUCK (no game_start) by book: {', '.join(f'{b} {st_by[b]}' for b in sorted(st_by)) or 'none'}"
                 f" | total {sum(st_by.values())}")
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
        # Nov 2 (Peter): every open bet, all books, by game time (for the pinned Bets Board)
        ob = sorted([b for b in tracker.values() if b.get("open") and not b.get("result")], key=lambda b: b.get("game_start") or "9")
        L += ["", f"OPEN BETS (all books, by game time): {len(ob)}"]
        orows = []
        for b in ob:
            gs = tp(b.get("game_start"))
            when = gs.astimezone(ET).strftime("%a %-I:%M %p") if gs else "no game time"
            L.append(f"  {when} | {b.get('league') or '?'} | {b.get('book')} [{b.get('source')}] | {b.get('bet')} {b.get('price') or ''} | "
                     f"stake {b.get('stake')} to pay {b.get('to_pay')} | {b.get('game')}")
            orows.append({k: b.get(k) for k in ("game_start", "league", "book", "source", "bet", "price", "stake", "to_pay", "game", "status", "score")})
        L.append("OPEN_BETS_JSON " + json.dumps(orows, separators=(",", ":")))
        L += ["", f"OddsPapi calls this run: billable {STATS['billable']}, free {STATS['free']}; billable this month "
                  f"{st['billable'].get(month_key(now), 0)} of cap {CAP} (plan 250)."]
        if st.get("errors"):
            L.append("Errors (last 5): " + " | ".join(st["errors"][-5:]))
        ex.send(("Bets CLV LEDGER ALERT" if alert else "Bets CLV LEDGER") + f" {today}", "\n".join(L))
        st["emailed"] = today
        if alert:
            st["alerted"] = today
    _stage("save + trim")
    # 6) save (encrypted), trim
    cut = iso(now - timedelta(days=60))
    st["bets"] = {k: v for k, v in st["bets"].items() if (v.get("first_seen") or "") >= cut}
    st["novig_checks"] = {k: v for k, v in (st.get("novig_checks") or {}).items() if (v["snap"].get("decided_utc") or "") >= cut}
    st["fixtures"] = {k: v for k, v in (st.get("fixtures") or {}).items()
                      if (v.get("start") or "") >= iso(now - timedelta(days=FX_KEEP_DAYS))}
    st["errors"] = (st.get("errors") or [])[-20:]
    os.makedirs("clv", exist_ok=True)
    json.dump(tb.enc(st), open(STATE, "w"))
    print(f"CLV ledger: bets {len(st['bets'])}, scored {len(scored)} (+{new_scored}), "
          f"calls billable {STATS['billable']} free {STATS['free']}")   # counts only
    # Nov 19 (Peter: add runtime and backlog counters so we can prove later reports are faster).
    # history calls used against the per-run cap, and how much ungraded work is still queued.
    _ungraded = sum(1 for _r in st["bets"].values() if _r.get("clv") is None and not _r.get("done"))
    print(f"CLV ledger work: history calls {len(hist)}/{MAX_HIST}, "
          f"ungraded backlog {_ungraded}, runtime {int((time.time() - _T0[0]) if _T0[0] else 0)}s", flush=True)
    print("CLV ledger Phase 1 provenance (counts only): "
          + (", ".join(f"{k} {v}" for k, v in sorted(PROV.items())) or "none this run"), flush=True)


if __name__ == "__main__":
    main()

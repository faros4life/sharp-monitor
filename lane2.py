#!/usr/bin/env python3
"""
LANE 2 - LOW-LIMIT SHARP ALERTS. Muse registration Nov 4 3:48 PM (Peter approved, with Muse's five pins).
DRY RUN ONLY (Peter Nov 4 4:01 PM "no live play"): there is no live order path in this module or for its plays in the
executor. Every Lane 2 play is priced, logged and emailed exactly like a dry-run play; nothing is ever sent to a book.
Friday's go-live is a separate decision by Peter; until then EXEC_LANE2_LIVE does not exist on purpose.

The lane (Item 56 P-limit test, Nov 4 12:47 PM: LOW +18.77u on 116, halves +13.18 / +5.59; HIGH -13.73u on 108):
  trigger  any SENT sharp alert, spreads or totals, NBA / NCAAF / NFL (not NHL), any pricing book, not late,
           alert gates 2-6 of agree_rules.decide (late, -130 after-fee cap, Top 25, executable book), edge under 4%
  gate     Pinnacle's RAW limit on that side, read live at decision time, at or below the FROZEN league x market median
           (FIT sent alerts to Oct 28, never re-fit). No NFL spreads median exists -> NFL spreads are out of the lane.
  price    the executor's own pricing (best after-fee exchange price at the alert number or better; Lane 1 rules)
  stake    1u flat (Lane 1's unit) - reported only, never placed
  logged   on every play: LOW / HIGH / no-limit, the limit and median used, pricing book (Hard Rock-priced split),
           timing (inside / outside 6-24 h, Muse pin 2: logged, not gated), edge band (<0, 0-2, 2-4, 4+; pin 3)
  stop     -8u from peak is an ALERT to Peter, never an auto-pause (pin 4) - computed by the Friday package, not here
Limits come from OddsPapi's live odds (paid key; the Nov 2 probe confirmed Pinnacle carries a per-market limit there),
one billable /odds-by-tournaments call per league per run that has a new Lane 2 candidate, plus /fixtures only when the
odds response carries no team names. Dollar limits go to the private dry-run email; the public log prints counts only.
"""
import os
from datetime import datetime, timedelta, timezone

import agree_rules as ar
import clv_ledger as cl
import tracker_build as tb

MEDIAN = {("NBA", "totals"): 1808.0, ("NBA", "spreads"): 4464.0, ("NCAAF", "spreads"): 10992.0,
          ("NCAAF", "totals"): 3101.0, ("NFL", "totals"): 16892.0}   # frozen (Item 56 FIT medians, raw OddsPapi dollars)
# ITEM 1 (Peter, 9 Nov): PAUSE PAID LANE 2 POLLING. Default OFF, so the pause is in effect without
# a repo-variable flip; set EXEC_LANE2_PAID=on to resume.
#
# Lane 2 is registry 8 - PAPER + DRY-RUN, no live order path - and it was the only OddsPapi
# consumer running on the executor's 10-minute cadence, which made it the dominant paid consumer
# at a measured 509/day against a sustainable 70/day.
#
# WHAT IS PRESERVED: the registered strategy, every threshold, the frozen medians, all historical
# data, and the whole module. Nothing is renamed, merged or retired - the registry is untouched.
# Lane 2 still runs each pass and still reports; it simply does not BUY a live Pinnacle limit, so
# candidates needing one are counted as "no limit (paid polling paused)" instead of being bought.
#
# WHAT IS NOT TOUCHED: the executor itself, LANE 1 and RESTING BIDS. None of them use OddsPapi at
# all - sharp_monitor runs on api.the-odds-api.com and the venue clients on their own APIs - so
# this cannot affect live money.
PAID = (os.environ.get("EXEC_LANE2_PAID") or "off").strip().lower() == "on"
LEAGUES = ("NBA", "NCAAF", "NFL")
EDGE_MAX = 4.0
LOOKBACK_H = 6
_ODDS = {}      # this run: league -> {fixtureId: fixture with bookmakerOdds}
# STEP 1 (Peter, 9 Nov). This WAS a throwaway: {"billable": {}} rebuilt every run, so
# cl.can_bill() always saw zero used and the 1,000 cap could never restrain Lane 2, while
# cl.bill() wrote into a dict that was discarded - Lane 2 spent on every executor pass and
# recorded nothing. That is the best single explanation for the provider reading 3,345 against an
# internal count of ~32.
#
# The meter is now seeded by READING the shared, committed clv/state.enc counter, so the cap binds
# immediately with no workflow change. Recording is deliberately NOT done by writing a state file
# here: executor-dry-run is contents:read and runs every 10 minutes, so adding a commit step would
# race the ten other committing workflows. Lane 2's spend is instead durably recorded where this
# codebase already keeps cross-run facts - the "Bets LIVE" email, whose summary_line() carries
# "OddsPapi calls N" - and credits.py attributes it from there. Gmail is the existing durable store
# (clv_ledger and tracker_build both read from it), so this adds no new persistence mechanism.
def _seed_state():
    """Month-to-date billable, read from the SHARED committed counter. Read-only, and LAZY.

    Lazy on purpose: lane2 -> clv_ledger -> executor -> lane2 is a circular import, so cl.STATE is
    not bound while this module is still loading. Seeding on first use sidesteps that entirely.

    It does NOT reset or invent a figure. On any failure the seed is empty and _seeded is False,
    and the run SAYS the cap is not enforceable rather than silently behaving as if zero were
    spent - which is exactly the failure the throwaway meter had."""
    if _ST["_seeded"] is not None:
        return _ST
    try:
        import json as _j
        st = tb.dec(_j.load(open(cl.STATE)))
        _ST["billable"] = dict((st or {}).get("billable") or {})
        _ST["_seeded"] = True
    except Exception as e:
        _ST["billable"] = {}
        _ST["_seeded"] = False
        STATS["notes"].append(f"credit seed unavailable ({type(e).__name__}): cap NOT enforced this run")
    return _ST


_ST = {"billable": {}, "_seeded": None}   # seeded lazily by _seed_state() on the first billable door
STATS = {"calls": 0, "capped": 0, "paused": 0, "candidates": 0, "low": 0, "high": 0, "no_limit": 0, "no_fixture": 0, "notes": []}
# Nov 4: the paid plan answers 403 RESTRICTED_ACCESS "Restricted bookmakers: pinnacle" on the history endpoint and sells
# "Pinnacle +30 sec" instead, so the live odds call may need the same slug. Try the plain name, then the paid slug.
# STEP 2 (Peter, 9 Nov). The paid plan answers 403 RESTRICTED_ACCESS for plain "pinnacle" - this
# file has said so since 4 Nov - so starting the loop there spent one billable call per league per
# run on a documented failure, then succeeded on "pinnacle+30". Observed in the 9 Nov 06:10 run:
# "NBA pinnacle: HTTP 403" then a good read, "OddsPapi calls 2".
#
# NO FEED CHANGE. "pinnacle+30" is already the feed EVERY successful call has used, because the
# first slug has never once worked on this plan. Reordering removes the wasted call and leaves the
# data identical - it does not switch us onto a different feed. Plain "pinnacle" is retained as a
# fallback in case the plan ever starts serving it.
SLUGS = ("pinnacle+30", "pinnacle")
_BOOK = {"slug": None}


def markets(cl_mod, now):
    """Market ids for Lane 2 WITHOUT a billable call while paid polling is paused.

    ITEM 2 / urgent: clv_ledger.load_markets() BILLS once clv/markets.json is 7 days old, and
    executor.py calls it on EVERY run. executor-dry-run is contents:read with no commit step, so
    the refreshed file is DISCARDED each time - meaning from the moment that file goes stale this
    becomes a permanent billable call per run, 144+/day, for a file that never persists. The file
    was fetched 2 Nov, so that leak would have opened on 10 Nov.

    Paused: read the committed file off disk, which is free and good enough for market ids -
    reference data that barely changes. Resumed: the normal path, cooldown and cap intact."""
    if PAID:
        return cl_mod.load_markets(_ST, now)
    try:
        import json as _j
        return _j.load(open(cl_mod.MKFILE)).get("m") or {}
    except Exception as e:
        STATS["notes"].append(f"market ids unreadable ({type(e).__name__})")
        return {}


def _live(lg, now):
    if lg in _ODDS:
        return _ODDS[lg]
    out = {}
    if not PAID:
        STATS["paused"] += 1
        return {}      # no billable call; the strategy, medians and history are untouched
    tid = cl.tournament(_ST, now, lg) if cl.KEY else None
    if not tid:
        STATS["notes"].append(f"{lg}: no tournament id")
    for slug in (SLUGS if tid else ()):
        # STEP 1: the cap now actually gates Lane 2. A refusal skips the PAPER measurement for this
        # league and says why - it never places, changes or suppresses a bet, because Lane 2 has no
        # live order path at all (registry 8: paper + dry-run).
        _seed_state()
        if _ST.get("_seeded") and not cl.can_bill(_ST, now):
            STATS["capped"] += 1
            STATS["notes"].append(f"{lg}: SKIPPED - monthly cap {cl.CAP} reached "
                                  f"({(_ST.get('billable') or {}).get(cl.month_key(now), 0)} used); "
                                  f"paper measurement skipped, nothing placed")
            break
        d = cl.api("/odds-by-tournaments", True, tournamentIds=str(tid), bookmaker=slug, verbosity=3)
        STATS["calls"] += 1
        cl.bill(_ST, now)   # counts against the seeded shared total for the rest of THIS run
        if isinstance(d, dict) and d.get("_error"):
            STATS["notes"].append(f"{lg} {slug}: HTTP {d['_error']}")
            continue
        fx = [f for f in (d if isinstance(d, list) else []) if f.get("fixtureId")]
        if not fx:
            STATS["notes"].append(f"{lg} {slug}: 0 fixtures")
            continue
        _BOOK["slug"] = slug
        for f in fx:
            out[str(f["fixtureId"])] = f
        break
    _ODDS[lg] = out
    return out


def _names(f):
    p1 = " ".join(str(f.get(k) or "") for k in ("participant1Name", "participant1ShortName", "participant1Abbr")).strip()
    p2 = " ".join(str(f.get(k) or "") for k in ("participant2Name", "participant2ShortName", "participant2Abbr")).strip()
    return p1, p2


def _fixture(a, lg, now, live):
    """(fixtureId, fixture record) for the alert's game: names from the live response when present, else /fixtures."""
    # A PAUSED LANE 2 MUST NOT BUY FIXTURES (Nov 9, caught by the new billable-call logging).
    # The Item 1 pause makes _live() return {}, so `live` is always empty here and this fell straight
    # through to the BILLABLE refresh_fixtures below - turning an occasional paid call into a
    # guaranteed one, 4 leagues per run. executor-dry-run is contents: read, so fx_last never
    # persisted either and every run re-bought all four: ~120 credits/day, the largest single
    # consumer, and a regression introduced by the pause itself.
    # With polling paused there is no live quote to price (bo is empty whatever this returns), so the
    # lookup cannot produce anything usable. decide() already handles a None fid.
    if not PAID:
        return None, None
    b = {"bet": a.get("bet"), "league": lg, "game": a.get("game"), "game_start": a.get("start_utc")}
    fx = {}
    for fid, f in live.items():
        p1, p2 = _names(f)
        if p1 and p2:
            fx[fid] = {"lg": lg, "start": f.get("startTime"), "p1": p1, "p2": p2,
                       "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}
    if fx:
        fid = cl.find_fixture({"fixtures": fx}, b)
        if fid:
            return fid, fx[fid]
    gs = cl.tp(a.get("start_utc")) or now
    cl.refresh_fixtures(_ST, now, lg, (gs - timedelta(days=1)).astimezone(cl.ET), (gs + timedelta(days=1)).astimezone(cl.ET))
    fid = cl.find_fixture(_ST, b)
    return (fid, _ST["fixtures"][fid]) if fid else (None, None)


def _tick(o):
    """The outcome's current quote. History keys players by "0" and holds a list of ticks; the LIVE odds response keys
    players by its own id and holds one dict (Nov 4: that mismatch made every Lane 2 play read NO_LIMIT), so take "0"
    when it is there and otherwise the first player, and the newest tick when it is a list."""
    p = o.get("players")
    if isinstance(p, dict):
        p = p.get("0") if "0" in p else next(iter(p.values()), None)
    if isinstance(p, list):
        p = max(p, key=lambda x: x.get("createdAt") or "") if p else None
    return p if isinstance(p, dict) else {}


def _limit(b, lg, f, pm, mkmap):
    """(raw limit, 'own line' | 'main line') of Pinnacle's current limit for the held side (plimit_level.pin_limit_at,
    on the live shape). Spreads and totals only."""
    pz = cl.parsed(b)
    if not pz or pz[0] == "ml":
        return None, None
    sid = cl.SPORT[lg]

    def lim(mid, oid):
        m = (pm.get(str(mid)) or {}).get("outcomes", {}).get(oid) or {}
        return tb.num(_tick(m).get("limit"))
    typ = "spreads" if pz[0] == "spread" else "totals"
    if typ == "totals":
        want, name = pz[2], ("Over" if pz[1] == "OVER" else "Under")
    else:
        side = cl.which_team(f, pz[1])
        if not side:
            return None, None
        if pz[3]:
            side = "2" if side == "1" else "1"
        want, name = (pz[2] if side == "1" else -pz[2]), side
    main = None
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != sid or t != typ or mid not in pm:
            continue
        oid = {v: k for k, v in outs.items()}.get(name)
        v = lim(mid, oid) if oid else None
        if not v:
            continue
        if abs(hcap - want) < 1e-9:
            return v, "own line"
        if main is None or v > main:
            main = v
    return (main, "main line") if main else (None, None)


def _edge_band(e):
    if e is None:
        return "n/a"
    return "<0" if e < 0 else ("0-2" if e < 2 else ("2-4" if e < 4 else "4+"))


def decide(a, now, mkmap):
    """Lane 2 entry for one sent alert: label LOW / HIGH / NO_LIMIT plus every logged split. Never places anything."""
    lg, kind = a.get("sport"), a.get("kind")
    typ = "spreads" if kind == "spr" else "totals"
    med = MEDIAN.get((lg, typ))
    ld = ar.lead_min(a)
    ent = {"lane": "lane2", "league": lg, "market": typ, "median": med, "limit": None, "limit_how": None, "label": None,
           "book_key": a.get("book_key"), "hr_priced": bool(ar.hr_priced(a)), "edge_pct": a.get("edge_pct"),
           "edge_band": _edge_band(a.get("edge_pct")), "lead_min": round(ld) if ld is not None else None,
           "timing": ("inside 6-24h" if ld is not None and 360 <= ld < 1440 else "outside 6-24h"),
           "alert_utc": a.get("alert_utc"), "price_after_fee": a.get("price_after_fee"), "point": a.get("point"),
           "sport": lg, "bet": a.get("bet"), "top25": a.get("top25")}
    if med is None:
        ent["label"] = "NOT IN LANE"
        ent["why"] = f"no frozen median for {lg} {typ}"
        return ent
    live = _live(lg, now)
    fid, f = _fixture(a, lg, now, live)
    bo = ((live.get(fid) or {}).get("bookmakerOdds") or {}) if fid else {}
    # Nov 5 (Peter, urgent before the Friday package): there WAS a fallback to next(iter(bo.values())) here - if
    # neither Pinnacle slug was present it took whatever bookmaker happened to be first in the dict and compared THAT
    # book's limits against the frozen PINNACLE-derived league x market medians, producing LOW / HIGH labels from an
    # unidentified book. Verified Pinnacle only now; anything else is NO_LIMIT, never a label.
    pin = bo.get("pinnacle") or bo.get("pinnacle+30") or {}
    pm = pin.get("markets") or {}
    if not fid:
        STATS["no_fixture"] += 1
    b = {"bet": a.get("bet"), "league": lg, "game": a.get("game"), "game_start": a.get("start_utc"), "book": a.get("book")}
    limit, how = _limit(b, lg, f, pm, mkmap) if (f and pm) else (None, None)
    ent["limit"], ent["limit_how"] = limit, how
    if limit is None:
        ent["label"] = "NO_LIMIT"
        ent["why"] = "no Pinnacle limit readable for this side right now" + ("" if fid else " (fixture not matched)")
        STATS["no_limit"] += 1
    elif limit <= med:
        ent["label"] = "LOW"
        STATS["low"] += 1
    else:
        ent["label"] = "HIGH"
        STATS["high"] += 1
    return ent


def plays(now, feed, mkmap):
    """Lane 2 candidate plays from the feed (alerts.json), each with its lane2_entry. All are DRY RUN."""
    out = []
    for a in feed or []:
        try:
            t, st = cl.tp(a.get("alert_utc")), cl.tp(a.get("start_utc"))
        except Exception:
            continue
        if not t or not st or t < now - timedelta(hours=LOOKBACK_H) or st <= now:
            continue
        if not a.get("sent_to_phone") or a.get("sport") not in LEAGUES or a.get("kind") not in ("spr", "tot") or a.get("late"):
            continue
        if (a.get("edge_pct") or 0) >= EDGE_MAX:
            continue
        d = ar.decide(a)
        if d.get("verdict") != "AGREE":
            continue
        STATS["candidates"] += 1
        ent = decide(a, now, mkmap)
        if ent["label"] == "NOT IN LANE":
            continue
        out.append({"sport": a.get("sport"), "game": a.get("game"), "bet": a.get("bet"), "start_utc": a.get("start_utc"),
                    "late": False, "source": "lane2", "alert_utc": a.get("alert_utc"),
                    "rules": {"verdict": "AGREE" if ent["label"] == "LOW" else "DISAGREE", "gate": "limit",
                              "reason": f"Lane 2 {ent['label']}: Pinnacle limit {ent['limit']} vs median {ent['median']:g} ({ent['limit_how'] or '-'})"},
                    "lane2_entry": ent})
    return out


def summary_line():
    return (f"Lane 2 (dry run only): {STATS['candidates']} candidate(s); LOW {STATS['low']}, HIGH {STATS['high']}, "
            f"no limit {STATS['no_limit']} (no fixture match {STATS['no_fixture']}); OddsPapi calls {STATS['calls']}; "
            f"Pinnacle slug {_BOOK['slug'] or '-'}; "
            + ("PAID POLLING PAUSED (EXEC_LANE2_PAID=off) - no billable call; "
               f"{STATS['paused']} league(s) skipped; strategy and history intact; " if not PAID else "")
            + f"month-to-date billable {(_ST.get('billable') or {}).get(cl.month_key(datetime.now(timezone.utc)), 0)}"
            f"/{cl.CAP}{'' if _ST.get('_seeded') else ' (SEED UNAVAILABLE - cap not enforced)'}"
            + (f"; CAPPED {STATS['capped']} league(s)" if STATS.get('capped') else "") + ("; " + "; ".join(STATS["notes"][:6]) if STATS["notes"] else ""))

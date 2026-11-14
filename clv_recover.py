#!/usr/bin/env python3
"""
LIQUIDITY-BOARD PINNACLE CLV RECOVERY (Peter, Nov 14 2026: "maximum budget of 39 billable
credits ... deduplicate by unique game and market, reuse caches, and prioritize live strategies,
top five potential candidates, then the remainder. Use staged batches and stop on unexpected
costs or poor recovery.")

WHAT IS BEING RECOVERED. The liquidity board's published CLV was measured against the ALERTING
VENUE'S OWN closing price, which REGISTRY.md already flags as not executable. This job recomputes
it against Pinnacle's no-vig close at our actual after-fee entry, using clv_basis - the one
versioned calculation the ledger uses. 1,369 observations already recompute from cached data at
zero credits. This job goes after the rest.

NOTHING PUBLISHED IS TOUCHED. The job never writes clv/state.enc (the 5-minute ledger owns it and
a second writer would race it), never writes liquidity/alerts.json, and never writes the published
scorecard. It writes exactly two things:
  * hcache/            the shared free history cache every test already reads
  * oddspapi/fixtures_recovered.json   its OWN fixture cache, so it cannot contend with the
                       plimit-logger workflow's commits to oddspapi/fixtures.json
Both are reference data - fixture ids, team names, start times, public market history. No stakes,
no balances, no account data, no keys.

THE BUDGET IS ENFORCED IN CODE, NOT BY INTENTION.
  * Only /fixtures bills. /historical-odds and /account are free (credit_gate.FREE_PATHS).
  * Every billable call goes through credit_gate, and BUDGET caps this job's own reservations.
    The ceiling is checked BEFORE each call, so the cap cannot be passed by one call.
  * Stages run in order and each stage stops early on its own abort test, so a tier that is not
    paying for itself does not spend the next tier's credits.

WHY THE PRIORITY TIERS LOOK THE WAY THEY DO. REGISTRY.md defines 9/LIQ-BOT as the "NBA totals 4h+
liquidity lane" and 13/LIQ-SMALL as the "$25-50k-print NBA totals subset". Both are NBA TOTALS.
The live lanes (Phase 1, R1, Board v3) place through the ledger, not the liquidity board, so the
liquidity population holds little or nothing for them - that is reported as a number, not assumed.
Tier 2 is therefore where the registered candidates actually live, and the remainder (NHL, NCAAF,
NFL, moneylines, spreads) belongs to no registered entry yet.

POLYMARKET GLOBAL IS NOT RECOVERABLE AND IS NOT A GAP. clv_std refuses to price it (NotTradeable,
and it is not bettable from the US at all), so those observations can never produce an executable
entry price. They are excluded from the budget rather than counted as missing work.
"""
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_basis as cb
import clv_ledger as cl
import clv_obs_audit as oa
import credit_gate as cg
import fixture_match as fxm
import hist_cache as hc
import tracker_build as tb

ET = cl.ET
BUDGET = int(os.environ.get("RECOVER_BUDGET", "39"))     # billable /fixtures calls, hard ceiling
APPLY = (os.environ.get("RECOVER_APPLY") or "").strip().lower() in ("1", "yes", "on", "true")
TIERS = (os.environ.get("RECOVER_TIERS") or "1,2,3").replace(" ", "")
MAX_FREE = int(os.environ.get("RECOVER_MAX_FREE", "400"))  # free /historical-odds calls per run
# Abort tests, per stage. A tier that resolves almost nothing is not worth the next tier's money.
MIN_FIX_RATE = float(os.environ.get("RECOVER_MIN_FIX_RATE", "0.15"))
FXOUT = "oddspapi/fixtures_recovered.json"
OUT = "audit/recovery_result.json"
L = []
SPENT = {"billable": 0, "free": 0}


def say(t=""):
    L.append(t)
    print(t, flush=True)


# ---------------------------------------------------------------------- recovery units
def unit_key(x):
    """ONE recovery unit = one unique game AND market (Peter's dedup rule).

    The game is keyed on its distinctive tokens so 'UMass vs UConn' and 'UConn @ UMass' are one
    unit, and the market carries its line, because a total at 223.5 and the same game's total at
    224.5 need different closing quotes and are not interchangeable.
    """
    lg = str(x.get("league") or x.get("sport") or "?").upper()
    gt = "+".join(sorted(tb.toks(x.get("game")) - tb.WEAK)) or "?"
    mkt = str(x.get("market") or "?").lower()
    line = tb.num(x.get("line"))
    return f"{lg}|{gt}|{mkt}|{'' if line is None else format(line, 'g')}"


def tier_of(x, cls):
    """1 live lane, 2 registered candidate (LIQ-BOT / LIQ-SMALL: NBA totals), 3 remainder.

    Returns (tier, why). Read from the registered definitions in REGISTRY.md, never widened:
    an NHL moneyline is NOT a LIQ-BOT observation however much we would like more of them.
    """
    lg = str(x.get("league") or x.get("sport") or "").upper()
    mkt = str(x.get("market") or "").lower()
    if x.get("lane") or x.get("bot_order_id") or x.get("order_id"):
        return 1, "carries a live-lane order id"
    if lg == "NBA" and mkt.startswith("total"):
        return 2, "9/LIQ-BOT + 13/LIQ-SMALL: NBA totals"
    return 3, f"no registered entry covers {lg or '?'} {mkt or '?'}"


def date_window(x):
    d = str(x.get("date") or x.get("alerted_utc") or x.get("first_seen_utc") or "")[:10]
    return d if len(d) == 10 else ""


# ---------------------------------------------------------------------- stages
def stage_free_history(units, allfx, mkmap, fxs, alt):
    """Games whose fixture we already hold but whose Pinnacle history was never cached.

    /historical-odds is FREE (credit_gate.FREE_PATHS), so this stage spends no credits at all. It
    runs FIRST and unconditionally: paying for fixtures before exhausting the free history would
    be spending money to reach work that was already reachable.
    """
    got, miss, calls = 0, 0, 0
    for u in units:
        if u["cls"] != "MISSING_HISTORY" or not u.get("fid"):
            continue
        if calls >= MAX_FREE:
            u["stage"] = "free-history: run cap reached, not attempted"
            continue
        f = allfx.get(u["fid"]) or {}
        start = cl.tp(f.get("start"))
        calls += 1
        SPENT["free"] += 1
        try:
            h = hc.get_hist(u["fid"], ["pinnacle"], start=start)
        except Exception as e:
            u["stage"] = f"free-history: call failed ({type(e).__name__})"
            miss += 1
            continue
        if isinstance(h, dict) and h.get("_error"):
            u["stage"] = f"free-history: API {h.get('_error')}"
            miss += 1
            continue
        oa._PIN.pop(u["fid"], None)
        if oa.cached_pin(u["fid"]) is None:
            u["stage"] = "free-history: Pinnacle has no history for this fixture"
            miss += 1
            continue
        got += 1
        u["stage"] = "free-history: downloaded"
        reclassify(u, fxs, alt, allfx, mkmap)
    return {"calls": calls, "history_arrived": got, "no_history": miss}


def stage_fixtures(units, st, now, allfx, mkmap, fxs, alt, tier):
    """The only stage that bills. One /fixtures call covers a whole league x date WINDOW, so the
    units are grouped into windows first and the windows are spent in order of how many unique
    games each one unblocks - the most games per credit, not the first row encountered.
    """
    want = collections.defaultdict(list)
    for u in units:
        if u["tier"] != tier or u["cls"] not in ("FIXTURE_OR_IDENTITY",) or not u.get("day"):
            continue
        if not u.get("needs_fixture"):
            continue
        lg = u["lg"]
        if lg not in cl.SPORT:
            continue
        want[(lg, u["day"])].append(u)
    order = sorted(want.items(), key=lambda kv: -len(kv[1]))
    res = {"windows_available": len(order), "windows_called": 0, "credits": 0,
           "units_resolved": 0, "units_attempted": 0, "aborted": None}
    for (lg, day), us in order:
        if SPENT["billable"] >= BUDGET:
            res["aborted"] = f"budget ceiling {BUDGET} reached"
            break
        d = cl.tp(day + "T12:00:00Z")
        if not d:
            continue
        lo, hi = (d - timedelta(days=1)).date(), (d + timedelta(days=1)).date()
        before = len(st.get("fixtures") or {}) + len(RECOVERED)
        if not APPLY:
            res["units_attempted"] += len(us)
            for u in us:
                u["stage"] = f"would call /fixtures {lg} {lo}..{hi} (dry run, no credit spent)"
            continue
        SPENT["billable"] += 1
        res["credits"] += 1
        ok = refresh_into_recovered(st, now, lg, lo, hi)
        res["windows_called"] += 1
        res["units_attempted"] += len(us)
        if not ok:
            for u in us:
                u["stage"] = f"/fixtures {lg} {lo}..{hi}: call refused or failed"
            continue
        allfx.update(RECOVERED)
        for u in us:
            reclassify(u, fxs, alt, allfx, mkmap)
            if u["cls"] == "VERIFIED_PINNACLE":
                res["units_resolved"] += 1
            elif u.get("fid"):
                u["stage"] = "fixture found; Pinnacle history still needed"
        say(f"    {lg} {day}: +{len(st.get('fixtures') or {}) + len(RECOVERED) - before} fixtures, "
            f"{res['units_resolved']}/{res['units_attempted']} units resolved so far, "
            f"{SPENT['billable']}/{BUDGET} credits")
        if res["windows_called"] >= 5:
            rate = res["units_resolved"] / max(1, res["units_attempted"])
            if rate < MIN_FIX_RATE:
                res["aborted"] = (f"poor recovery: {res['units_resolved']}/{res['units_attempted']} "
                                  f"({rate:.0%}) after {res['windows_called']} windows, "
                                  f"below the {MIN_FIX_RATE:.0%} floor - stopped rather than "
                                  f"spending the rest of the budget at this rate")
                break
    return res


RECOVERED = {}


def refresh_into_recovered(st, now, lg, lo, hi):
    """One billable /fixtures call whose result lands in RECOVERED, never in clv/state.enc.

    This is deliberately NOT clv_ledger.refresh_fixtures: that one writes st["fixtures"] and
    stamps st["fx_last"], and the 5-minute ledger owns that file. Two writers to one encrypted
    state is a lost-update race, so this job keeps its own cache and the ledger picks it up
    through fixture_match.ALT_PATHS on its next run.
    """
    tid = cl.tournament(st, now, lg)
    if not tid:
        return False
    if not cl.can_bill(st, now):
        say(f"    {lg}: credit gate would refuse - not called")
        return False
    try:
        d = cl.api("/fixtures", True, tournamentId=tid,
                   **{"from": lo.strftime("%Y-%m-%d"), "to": hi.strftime("%Y-%m-%d")})
    except Exception as e:
        say(f"    {lg}: /fixtures refused ({type(e).__name__})")
        return False
    if isinstance(d, dict) and d.get("_error"):
        say(f"    {lg}: /fixtures error {d.get('_error')}")
        return False
    n = 0
    for f in d if isinstance(d, list) else []:
        if not f.get("fixtureId"):
            continue
        RECOVERED[f["fixtureId"]] = {
            "lg": lg, "start": f.get("startTime"), "status": f.get("statusId"),
            "p1": " ".join(str(f.get(k) or "") for k in
                           ("participant1Name", "participant1ShortName", "participant1Abbr")),
            "p2": " ".join(str(f.get(k) or "") for k in
                           ("participant2Name", "participant2ShortName", "participant2Abbr")),
            "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}
        n += 1
    return n > 0


def reclassify(u, fxs, alt, allfx, mkmap):
    cls, detail = oa.classify(u["row"], "liquidity", fxs, alt, allfx, mkmap)
    u["cls"], u["detail"] = cls, detail
    if isinstance(detail, dict):
        u["fid"] = detail.get("fid")
        u["clv"] = detail.get("clv")
    elif cls == "MISSING_HISTORY":
        # Nov 14, caught by the first dry run: Stage A made ZERO free calls while 84 units sat in
        # MISSING_HISTORY. classify() returns a dict only for VERIFIED_PINNACLE, so u["fid"] was
        # never set for the one class that needs it, and the stage's `if not u.get("fid")` skipped
        # every single one. A stage that silently recovers nothing is the worst failure available,
        # and the measurement was the instrument again. The fixture id is re-derived through the
        # SAME matcher classify used, so there is no second definition of a match.
        fid, _note = fxm.ordered_match(oa.snap_for(u["row"], "liquidity"), allfx, cl.tp)
        u["fid"] = fid
    u["needs_fixture"] = cls == "FIXTURE_OR_IDENTITY" and "no unique fixture" in str(detail)
    return cls


# ---------------------------------------------------------------------- main
def main():
    now = datetime.now(timezone.utc)
    say("LIQUIDITY PINNACLE CLV RECOVERY" + ("" if APPLY else "   [DRY RUN - no call bills]"))
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET   basis {cb.BASIS_VERSION}   "
        f"budget {BUDGET} billable   tiers {TIERS}")
    say("=" * 104)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    try:
        mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"FATAL: {oa.MKFILE} unreadable ({type(e).__name__})")
        return 1
    try:
        RECOVERED.update((json.load(open(FXOUT)).get("fixtures") or {}))
        say(f"  carried forward {len(RECOVERED)} fixtures recovered by earlier runs")
    except Exception:
        pass

    fxs = st.get("fixtures") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    allfx = dict(alt, **fxs)
    allfx.update(RECOVERED)
    rows = oa.load(oa.LIQ)
    say(f"  liquidity observations {len(rows)}   fixtures on hand {len(allfx)}   "
        f"hcache {len(os.listdir(oa.HC)) if os.path.isdir(oa.HC) else 0}")

    # ---- dedup to units, classify once
    units = {}
    for x in rows:
        k = unit_key(x)
        u = units.get(k)
        if u is None:
            t, twhy = tier_of(x, None)
            u = units[k] = {"key": k, "row": x, "n_obs": 0, "tier": t, "twhy": twhy,
                            "lg": str(x.get("league") or x.get("sport") or "").upper(),
                            "day": date_window(x), "stage": "", "clv": None, "fid": None}
            reclassify(u, fxs, alt, allfx, mkmap)
        u["n_obs"] += 1
    say(f"  {len(rows)} observations -> {len(units)} unique game x market units "
        f"(dedup factor {len(rows) / max(1, len(units)):.1f}x)")
    say("")

    say("TIERS - from the REGISTERED definitions, not widened")
    say("-" * 104)
    for t in (1, 2, 3):
        us = [u for u in units.values() if u["tier"] == t]
        if not us:
            say(f"  tier {t}: 0 units")
            continue
        say(f"  tier {t}: {len(us):5d} units / {sum(u['n_obs'] for u in us):5d} observations   "
            f"{us[0]['twhy']}")
        cc = collections.Counter(u["cls"] for u in us)
        for c, n in cc.most_common():
            say(f"           {n:5d}  {c}")
    say("")
    if not any(u["tier"] == 1 for u in units.values()):
        say("  TIER 1 IS EMPTY, and that is the expected shape, not a gap: the live lanes place")
        say("  through the ledger and their CLV is scored there (coverage is reported by")
        say("  clv_coverage). No liquidity observation carries a live-lane order id.")
        say("")

    want = [t for t in ("1", "2", "3") if t in TIERS.split(",")]
    say("STAGE A - free history for games whose fixture we already hold (0 credits)")
    say("-" * 104)
    pool = [u for u in units.values() if str(u["tier"]) in want]
    a = stage_free_history(pool, allfx, mkmap, fxs, alt)
    say(f"  {a['calls']} free /historical-odds calls -> history arrived for {a['history_arrived']}, "
        f"Pinnacle has none for {a['no_history']}")
    say("")

    say(f"STAGE B - billable /fixtures, ceiling {BUDGET}, by tier")
    say("-" * 104)
    bres = {}
    for t in (1, 2, 3):
        if str(t) not in want:
            continue
        r = stage_fixtures(pool, st, now, allfx, mkmap, fxs, alt, t)
        bres[t] = r
        say(f"  tier {t}: {r['windows_available']} league x date windows available, "
            f"{r['windows_called']} called, {r['credits']} credits, "
            f"{r['units_resolved']}/{r['units_attempted']} units resolved")
        if r["aborted"]:
            say(f"           STOPPED: {r['aborted']}")
            break
    say("")

    # ---- result
    say("RESULT - after recovery, by tier")
    say("=" * 104)
    final = {}
    for t in (1, 2, 3):
        us = [u for u in units.values() if u["tier"] == t]
        if not us:
            continue
        cc = collections.Counter(u["cls"] for u in us)
        ver = [u for u in us if u["cls"] == "VERIFIED_PINNACLE" and u["clv"] is not None]
        n_obs_ver = sum(u["n_obs"] for u in ver)
        mean = sum(u["clv"] for u in ver) / len(ver) if ver else None
        beat = sum(1 for u in ver if u["clv"] > 0)
        final[t] = {"units": len(us), "obs": sum(u["n_obs"] for u in us),
                    "verified_units": len(ver), "verified_obs": n_obs_ver,
                    "mean_clv": None if mean is None else round(mean, 4),
                    "beat_close": beat, "classes": dict(cc)}
        say(f"  tier {t}: {len(ver)}/{len(us)} units verified ({n_obs_ver} observations)"
            + (f"   mean CLV {mean * 100:+.2f}%   beat close {beat}/{len(ver)}" if ver else ""))
    say("")
    say(f"CREDITS SPENT BY THIS JOB: {SPENT['billable']} billable (ceiling {BUDGET}), "
        f"{SPENT['free']} free calls")
    say(f"credit_gate reservations this process: {dict(cg.SPEND)}")
    if not APPLY:
        say("DRY RUN: no /fixtures call was made, so the billable count is 0 by construction.")

    os.makedirs("audit", exist_ok=True)
    json.dump({"generated": cl.iso(now), "basis": cb.BASIS_VERSION, "apply": APPLY,
               "budget": BUDGET, "spent": SPENT, "stage_a": a, "stage_b": bres,
               "final": final,
               "units": [{k: v for k, v in u.items() if k != "row"} for u in units.values()]},
              open(OUT, "w"), indent=1, default=str)
    if APPLY and RECOVERED:
        os.makedirs("oddspapi", exist_ok=True)
        json.dump({"generated": cl.iso(now), "by": "clv_recover",
                   "note": "fixture reference data only - no stakes, accounts or keys",
                   "fixtures": RECOVERED}, open(FXOUT, "w"), indent=1)
        say(f"wrote {FXOUT}: {len(RECOVERED)} fixtures (reference data only)")
    say(f"wrote {OUT}")
    cg.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())

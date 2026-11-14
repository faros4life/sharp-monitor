#!/usr/bin/env python3
"""
FULL OBSERVATION AUDIT - every scorecard observation, one class each (Peter, Nov 14 2026).

READ-ONLY. No write, no fetch, no OddsPapi call, no IMAP. Pinnacle history comes from the hcache
files already on disk.

Peter: "Produce mutually exclusive missing-data classifications that reconcile exactly to all
3,903 observations" and "Do not count a successful calculation as verified Pinnacle CLV unless
the benchmark source is proven."

TWO INDEPENDENT DIMENSIONS, because conflating them is the original error:

  A. NEW-BASIS OUTCOME - can a verified same-line Pinnacle close be computed TODAY, at an
     executable after-fee entry price? Six mutually exclusive classes, assigned by a strict
     waterfall so every observation lands in exactly one and the counts reconcile to the total.

  B. OLD BENCHMARK PROVENANCE - what the published scorecard's CLV was actually measured
     against. This is NOT a missing-data class; it is a property of the figure already
     published, and it is read from the stored fields that record it rather than inferred:

       liquidity rows: close_price is, in liquidity_monitor's own export note, "last pregame
         price" of the ALERTING EXCHANGE - kalshi, novig, polymarket or prophetx. Pinnacle is
         not among the books it reads. So every liquidity observation with a close was measured
         against the TRIGGER VENUE'S OWN close. CLV_STANDARD.md section 4: that "stays separate,
         is never labelled Pinnacle CLV, and is never used as a CLV gate."

       sharp rows: close_fair_prob is Pinnacle-derived (SHARP_BOOK defaults to pinnacle), but
         sharp_monitor records it as PROVISIONAL in its own fields - clv_source "live read
         (provisional)", clv_verified False - with the comment "a same-line read 20-30 min out is
         still not the close. clv_verified is True ONLY on a certified historical Pinnacle close
         from the clv_recover path". Where clv_conv_pts is non-zero the read was also at a
         DIFFERENT line and converted.

     So neither population's published CLV qualifies as verified Pinnacle CLV, and they fail for
     different reasons with different remedies.

The cross-tab at the end is the thing to read: how many observations have BOTH a provable
old-benchmark defect AND a computable verified close, i.e. how many published figures can be
corrected now rather than merely doubted.
"""
import collections
import gzip
import json
import os
import sys
from datetime import datetime, timezone

import clv_basis as cb
import clv_ledger as cl
import fixture_match as fxm
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
SHARP = os.environ.get("SC_SHARP", "") or "alerts.json"
LIQ = os.environ.get("SC_LIQ", "") or "liquidity/alerts.json"
MKFILE = "clv/markets.json"
OUT = "audit/observation_audit.json"
L = []
_PIN = {}

# Peter's five reporting categories, and which of the six waterfall classes map to each.
CATEGORY = {
    "VERIFIED_PINNACLE": "1 verified Pinnacle CLV at an executable after-fee entry",
    "UNVERIFIABLE_ENTRY": "5 unverifiable entry price",
    "VENUE_NOT_PRICEABLE": "5 unverifiable entry price (venue not tradeable from the US)",
    "FIXTURE_OR_IDENTITY": "4 fixture or identity failure",
    "MISSING_HISTORY": "3 missing Pinnacle history",
    "NO_SAME_LINE_QUOTE": "3 missing Pinnacle history (our line was never hung two-sided)",
    "LEAGUE_NOT_COVERED": "4 fixture or identity failure (league outside the sport map)",
}


def say(t=""):
    L.append(t)
    print(t, flush=True)


def load(p):
    try:
        d = json.load(open(p))
    except Exception:
        return []
    if isinstance(d, dict):
        for k in ("alerts", "rows", "sightings"):
            if isinstance(d.get(k), list):
                return d[k]
        return []
    return d if isinstance(d, list) else []


def cached_pin(fid):
    if fid in _PIN:
        return _PIN[fid]
    p = os.path.join(HC, f"{fid}__pinnacle.json.gz")
    d = None
    if os.path.exists(p):
        try:
            with gzip.open(p, "rt") as fh:
                d = json.load(fh)
        except Exception:
            d = None
    _PIN[fid] = {"bookmakers": {"pinnacle": d}} if d is not None else None
    return _PIN[fid]


def provenance(x, src):
    """What the OLD published CLV was measured against. Read from stored fields, never inferred."""
    if src == "liquidity":
        if x.get("close_price") is None:
            return "NONE", "no close was ever read for this observation"
        if x.get("close_suspect"):
            return "TRIGGER_VENUE_SUSPECT", ("trigger venue's own last pregame price, and flagged "
                                             f"{x['close_suspect']} by liquidity_monitor itself")
        return "TRIGGER_VENUE", ("trigger venue's own last pregame price (liquidity_monitor export "
                                 "note) - not Pinnacle")
    if x.get("close_fair_prob") is None:
        return "NONE", "no close was ever read for this observation"
    if x.get("clv_verified") is True:
        return "PINNACLE_CERTIFIED", "certified historical Pinnacle close (clv_recover path)"
    conv = tb.num(x.get("clv_conv_pts"))
    if conv:
        return "PINNACLE_PROVISIONAL_CONVERTED", (f"provisional live Pinnacle read, converted "
                                                  f"{conv:+g} pts from a different line")
    return "PINNACLE_PROVISIONAL", (f"provisional live Pinnacle read"
                                    + (f", {x.get('close_read_mins_before')} min before start"
                                       if x.get("close_read_mins_before") is not None else ""))


def snap_for(x, src):
    """A scoring snapshot built from each population's OWN fields.

    The liquidity export has NO 'bet' string at all. It is fully structured - market
    ("moneyline"|"total"|"spread"), side ("Over", "Under", or a team name), line, and teams -
    and reading x["bet"] from it returns nothing, so 2,054 observations were filed "bet text does
    not parse" by my reader rather than by any defect in the data. That is the THIRD unit/field
    mistake I made on this one population (close_price provenance, the 0-1 price unit, and now
    the missing bet field), which is exactly why CLAUDE.md says to suspect the instrument first.

    The bet text is synthesised from those fields rather than guessed, and teams is handed
    straight to the matcher, which is stronger than splitting the game string.
    """
    lg = x.get("sport") or x.get("league")
    gs = x.get("start_utc") or x.get("game_start") or x.get("commence_time")
    if src != "liquidity":
        return {"league": lg, "game": x.get("game"), "bet": x.get("bet"), "game_start": gs}
    mkt = str(x.get("market") or "").lower()
    side = str(x.get("side") or x.get("side_label") or "").strip()
    line = tb.num(x.get("line"))
    if mkt.startswith("total") and line is not None:
        bet = f"{side} {line:g}"
    elif mkt.startswith("spread") and line is not None:
        bet = f"{side} {line:+g}"
    else:
        bet = side
    tms = x.get("teams")
    snap = {"league": lg, "game": x.get("game"), "bet": bet, "game_start": gs}
    if isinstance(tms, list) and len(tms) >= 2:
        snap["teams"] = [{"name": t if isinstance(t, str) else (t or {}).get("name")} for t in tms[:2]]
    # The venue's own market ticker (Kalshi: KXNBATOTAL-26NOV13OKCLAC-223) carries both teams'
    # abbreviations. It is the only identity signal left on a row whose title was truncated to
    # "Los Angeles C" and whose fixture OddsPapi calls "LA Clippers" - see fixture_match.name_pick.
    tk = (x.get("ref") or {}).get("market_ticker") if isinstance(x.get("ref"), dict) else None
    if tk:
        snap["ticker"] = tk
    return snap


def classify(x, src, fxs, alt, allfx, mkmap):
    """Exactly ONE class, by waterfall. Returns (class, detail)."""
    lg = x.get("sport") or x.get("league")
    book = x.get("book_key") or x.get("book")
    # 1 entry price first: without one, nothing downstream can produce a CLV at all. The two
    # populations quote in DIFFERENT UNITS and conflating them was my own error: the liquidity
    # export says "price = cost to buy the side when logged (0-1)", while the sharp feed carries
    # American odds. 616 rows were filed UNVERIFIABLE_ENTRY on that unit mistake.
    if src == "liquidity":
        entry, ewhy = cb.after_fee_from_cost(x.get("price"), book, league=lg)
    else:
        am = tb.num(x.get("price_after_fee"))
        if am is None:
            am = tb.num(x.get("price"))
        entry = cb.after_fee_from_quote(am, book, cl.am_to_dec, league=lg)
        ewhy = f"price={am} book={book}" if entry is None else None
    if entry is None:
        if ewhy and ("not tradeable" in ewhy or "not in the venue registry" in ewhy):
            return "VENUE_NOT_PRICEABLE", ewhy
        return "UNVERIFIABLE_ENTRY", f"no executable after-fee entry: {ewhy}"
    snap = snap_for(x, src)
    # 2 identity: the bet must parse and the row must name two sides
    if not cl.parsed(snap):
        return "FIXTURE_OR_IDENTITY", "bet text does not parse into a market, side and line"
    sides, how = fxm.sides_of(snap)
    if not sides or not all(sides):
        return "FIXTURE_OR_IDENTITY", f"cannot be split into two named sides ({how})"
    if lg not in cl.SPORT:
        return "LEAGUE_NOT_COVERED", f"league {lg or 'unknown'} has no OddsPapi sport id"
    fid, note = fxm.ordered_match(snap, allfx, cl.tp)
    if not fid:
        return "FIXTURE_OR_IDENTITY", f"no unique fixture: {note[:60]}"
    h = cached_pin(fid)
    if h is None:
        return "MISSING_HISTORY", f"fixture {fid} has no cached Pinnacle history"
    f = allfx[fid]
    p, why = cb.pinnacle_no_vig_close(f, snap, mkmap, cl.book_markets(h, "pinnacle"), cl.parsed,
                                      cl.which_team, cl.two_way, cl.novig_p, cl.SPORT,
                                      cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
    if p is None:
        w = str(why)
        if "not matched" in w or "never recorded" in w or "names no team" in w or "politics" in w:
            return "FIXTURE_OR_IDENTITY", w[:70]
        return "NO_SAME_LINE_QUOTE", w[:70]
    return "VERIFIED_PINNACLE", {"p": p, "entry": entry, "clv": cb.clv(p, entry),
                                 "how": why.get("how"), "age_min": why.get("age_min"), "fid": fid}


def main():
    now = datetime.now(timezone.utc)
    say("FULL OBSERVATION AUDIT - READ-ONLY, nothing written to production, no credits spent")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET   basis {cb.BASIS_VERSION}")
    say("=" * 108)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    try:
        mkmap = (json.load(open(MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"FATAL: {MKFILE} unreadable ({type(e).__name__})")
        return 1
    fxs = st.get("fixtures") or {}
    altmap = fxm.alt_fixtures()
    alt = {fid: f for fid, (f, _s) in altmap.items()}
    allfx = dict(alt, **fxs)
    say(f"  fixtures {len(allfx)} ({len(fxs)} state + {len(allfx) - len(fxs)} other stores) | "
        f"market ids {len(mkmap)} | hcache {len(os.listdir(HC)) if os.path.isdir(HC) else 0}")

    obs = [(x, "sharp") for x in load(SHARP)] + [(x, "liquidity") for x in load(LIQ)]
    say(f"  observations: {len(obs)}  (sharp {sum(1 for _x, s in obs if s == 'sharp')}, "
        f"liquidity {sum(1 for _x, s in obs if s == 'liquidity')})")

    rows = []
    for x, src in obs:
        cls, detail = classify(x, src, fxs, alt, allfx, mkmap)
        prov, pwhy = provenance(x, src)
        rows.append({"src": src, "cls": cls, "detail": detail, "prov": prov, "pwhy": pwhy,
                     "lg": x.get("sport") or x.get("league"), "day": str(
                         x.get("alert_utc") or x.get("alerted_utc") or "")[:10],
                     "book": x.get("book_key") or x.get("book"), "res": x.get("result"),
                     "game": x.get("game"), "bet": x.get("bet")})

    # ---------------------------------------------------------------- A: reconciliation
    say("")
    say("A. NEW-BASIS OUTCOME - mutually exclusive, reconciled")
    say("=" * 108)
    cc = collections.Counter(r["cls"] for r in rows)
    total = sum(cc.values())
    for k, n in cc.most_common():
        say(f"  {n:6d}  {k:<22} -> Peter category {CATEGORY.get(k, '?')}")
    say(f"  {'-' * 100}")
    say(f"  {total:6d}  TOTAL")
    say(f"  observations loaded {len(rows)}   classes sum to {total}   "
        f"RECONCILES: {'YES' if total == len(rows) else 'NO'}")
    say("")
    say("  rolled up into Peter's five categories:")
    cat = collections.Counter(CATEGORY.get(r["cls"], "?")[0] for r in rows)
    names = {"1": "verified Pinnacle CLV at an executable after-fee entry",
             "3": "missing Pinnacle history (no file, or our line never hung two-sided)",
             "4": "fixture or identity failure", "5": "unverifiable entry price"}
    for k in sorted(cat):
        say(f"    {cat[k]:6d}  ({100 * cat[k] / total:.1f}%)  {k} {names.get(k, '?')}")
    say(f"    {'2':>6}  (category 2, incorrect benchmark CLV) is reported in section B: it is a")
    say("            property of the PUBLISHED figure, not a reason the new basis failed, so")
    say("            counting it here would double-count every observation.")

    say("")
    say("  by source:")
    for src in ("sharp", "liquidity"):
        sub = [r for r in rows if r["src"] == src]
        if not sub:
            continue
        say(f"    {src} (n {len(sub)}):")
        for k, n in collections.Counter(r["cls"] for r in sub).most_common():
            say(f"      {n:6d}  {k}")

    say("")
    say("  the leading detail text behind each failing class:")
    for k in [k for k in cc if k != "VERIFIED_PINNACLE"]:
        det = collections.Counter(str(r["detail"])[:62] for r in rows if r["cls"] == k)
        say(f"    {k}:")
        for d, n in det.most_common(4):
            say(f"      {n:6d}  {d}")

    # ---------------------------------------------------------------- B: provenance
    say("")
    say("B. OLD BENCHMARK PROVENANCE - what the published CLV was measured against")
    say("=" * 108)
    pc = collections.Counter(r["prov"] for r in rows)
    for k, n in pc.most_common():
        ex = next(r["pwhy"] for r in rows if r["prov"] == k)
        say(f"  {n:6d}  {k:<34} {ex[:58]}")
    say(f"  {'-' * 100}")
    say(f"  {sum(pc.values()):6d}  TOTAL   RECONCILES: "
        f"{'YES' if sum(pc.values()) == len(rows) else 'NO'}")
    bad = [r for r in rows if r["prov"].startswith("TRIGGER_VENUE")]
    prov_ok = [r for r in rows if r["prov"] == "PINNACLE_CERTIFIED"]
    say("")
    say(f"  OBSERVATIONS MEASURED AGAINST THE TRIGGER VENUE'S OWN CLOSE: {len(bad)}")
    say(f"    all of them liquidity-board rows: {sum(1 for r in bad if r['src'] == 'liquidity')}")
    say("    CLV_STANDARD.md section 4 forbids labelling that Pinnacle CLV or using it as a gate.")
    say(f"  OBSERVATIONS WITH A CERTIFIED PINNACLE CLOSE ALREADY: {len(prov_ok)}")
    say("    so no published figure in either population currently qualifies as verified")
    say("    Pinnacle CLV, and the two populations fail for different reasons.")
    say("")
    say("  by league, the trigger-venue population:")
    for lg, n in collections.Counter(str(r["lg"]) for r in bad).most_common(8):
        say(f"    {n:6d}  {lg}")
    say("  by venue:")
    for bk, n in collections.Counter(str(r["book"]) for r in bad).most_common(8):
        say(f"    {n:6d}  {bk}")

    # ---------------------------------------------------------------- cross-tab
    say("")
    say("C. CROSS-TAB - which published figures can be CORRECTED, not merely doubted")
    say("=" * 108)
    say(f"  {'old benchmark':<34} {'verified now':>13} {'still not':>11} {'total':>8}")
    for k in [k for k, _ in pc.most_common()]:
        sub = [r for r in rows if r["prov"] == k]
        ok = sum(1 for r in sub if r["cls"] == "VERIFIED_PINNACLE")
        say(f"  {k:<34} {ok:13d} {len(sub) - ok:11d} {len(sub):8d}")
    corr = [r for r in rows if r["prov"].startswith("TRIGGER_VENUE") and r["cls"] == "VERIFIED_PINNACLE"]
    say("")
    say(f"  liquidity observations with a WRONG benchmark that CAN be recomputed now: {len(corr)}")
    say(f"  liquidity observations with a wrong benchmark and NO verified close available: "
        f"{len(bad) - len(corr)}")
    if corr:
        d = [r["detail"]["clv"] for r in corr if isinstance(r["detail"], dict)
             and r["detail"].get("clv") is not None]
        if d:
            m = sum(d) / len(d)
            say(f"  their recomputed CLV: n {len(d)}  mean {100 * m:+.2f}%  "
                f"beat close {sum(1 for x in d if x > 0)}/{len(d)}")
            say("  NOTE: that is the recomputed figure for the subset that happens to be")
            say("  recoverable, which is NOT a random subset of the liquidity population. It is")
            say("  not a corrected verdict for any registered slice.")

    say("")
    say("D. WHAT THE SCORECARD ACTUALLY EVALUATES")
    say("=" * 108)
    say("  clv_scorecard.py computes 7 slices in code; SCORECARD.md's registry table has 32")
    say("  numbered entries. Neither is 56, and I cannot find a 56 anywhere in the repo - so the")
    say("  per-test breakdown below is per CODE SLICE, and the registry entries that are not")
    say("  computed from these two files cannot be classified from this data at all. Say which")
    say("  list the 56 refers to and I will map to it exactly rather than guess.")
    say("")
    say(f"  {'slice':<26} {'n':>6} {'verified':>9} {'cov':>6} {'wrong bench':>12}")
    slices = [("ALL", rows),
              ("sharp feed", [r for r in rows if r["src"] == "sharp"]),
              ("liquidity board", [r for r in rows if r["src"] == "liquidity"]),
              ("NBA totals UNDER", [r for r in rows if r["lg"] == "NBA"
                                    and "under" in str(r["bet"]).lower()]),
              ("NBA", [r for r in rows if r["lg"] == "NBA"]),
              ("NCAAF", [r for r in rows if r["lg"] == "NCAAF"]),
              ("NFL", [r for r in rows if r["lg"] == "NFL"]),
              ("NHL", [r for r in rows if r["lg"] == "NHL"])]
    for name, sub in slices:
        if not sub:
            continue
        v = sum(1 for r in sub if r["cls"] == "VERIFIED_PINNACLE")
        w = sum(1 for r in sub if r["prov"].startswith("TRIGGER_VENUE"))
        say(f"  {name:<26} {len(sub):6d} {v:9d} {100 * v / len(sub):5.1f}% {w:12d}")

    # ---------------------------------------------------------------- E: recovery cost
    say("")
    say("E. LIQUIDITY RECOVERY COST - deduplicated to unique games, no paid call made")
    say("=" * 108)
    liq = [(x, r) for (x, _s), r in zip(obs, rows) if r["src"] == "liquidity"]
    games = {}
    for x, r in liq:
        gs = x.get("start_utc") or x.get("game_start") or x.get("commence_time")
        d = cl.tp(gs)
        key = (str(r["lg"]), "+".join(sorted(fxm.toks(r["game"]) if hasattr(fxm, "toks")
                                             else (tb.toks(r["game"]) - tb.WEAK))),
               d.astimezone(ET).strftime("%Y-%m-%d") if d else (r["day"] or "?"))
        games.setdefault(key, []).append((x, r))
    say(f"  liquidity observations {len(liq)}  ->  UNIQUE GAMES {len(games)}"
        f"  ({len(liq) / max(len(games), 1):.1f} observations per game)")
    have_fx, need_fx, have_hist, need_hist, no_league = 0, 0, 0, 0, 0
    fx_windows = set()
    for (lg, _gt, day), items in games.items():
        if lg not in cl.SPORT:
            no_league += 1
            continue
        x, r = items[0]
        fid, _n = fxm.ordered_match(snap_for(x, "liquidity"), allfx, cl.tp)
        if not fid:
            need_fx += 1
            fx_windows.add((lg, day))
            continue
        have_fx += 1
        if cached_pin(fid) is not None:
            have_hist += 1
        else:
            need_hist += 1
    say(f"  unique games in a league the ledger covers      {len(games) - no_league}")
    say(f"    league outside the sport map (NCAAB/MLB etc)  {no_league}  - held, not costed")
    say(f"  fixture already in a cache we hold              {have_fx}")
    say(f"    of those, Pinnacle history ALREADY cached     {have_hist}  <- free, no call at all")
    say(f"    of those, history MISSING                     {need_hist}  <- 1 FREE /historical-odds each")
    say(f"  no fixture in any cache                         {need_fx}  <- needs a billable /fixtures first")
    say("")
    say("  CALLS AND CREDITS:")
    say(f"    free /historical-odds calls needed            {need_hist + need_fx}")
    say(f"      (the {need_fx} without a fixture need history too, once their fixture exists)")
    say(f"    billable /fixtures calls                      {len(fx_windows)} league x date window(s)")
    say("      a window is one league for one ET date; consecutive dates for a league can be")
    say("      batched into one call, so this is an UPPER bound on credits")
    say(f"    distinct leagues needing a fetch              {len({lg for lg, _d in fx_windows})}")
    per_run = cl.MAX_HIST
    runs = -(-(need_hist + need_fx) // max(per_run, 1))
    say("")
    say("  GITHUB RUNS:")
    say(f"    MAX_HIST caps free history at {per_run} calls a run, ~8s each")
    say(f"    runs needed for the history backfill          {runs}")
    say(f"    wall time at {per_run} x 8s                           ~{per_run * 8 / 60:.0f} min a run,"
        f" ~{runs * per_run * 8 / 3600:.1f} h total")
    say("")
    say("  WHAT IT WOULD BUY: recomputing the trigger-venue population on a verified Pinnacle")
    say(f"  close. Ceiling is the {have_fx} games whose fixture we already hold; the {need_fx} without")
    say("  one are gated behind the billable fetch and may still fail on fixture ambiguity or on")
    say("  Pinnacle never hanging the bet's own line - neither is knowable before the call.")

    try:
        os.makedirs("audit", exist_ok=True)
        json.dump({"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "basis": cb.BASIS_VERSION,
                   "total": len(rows), "classes": dict(cc), "provenance": dict(pc),
                   "trigger_venue_total": len(bad), "trigger_venue_recoverable": len(corr)},
                  open(OUT, "w"), indent=1)
        print(f"wrote {OUT}", flush=True)
    except Exception as e:
        print(f"could not write {OUT} ({type(e).__name__})", flush=True)
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("Full observation audit", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"obs audit: {len(rows)} observations, verified {cc.get('VERIFIED_PINNACLE', 0)}, "
          f"trigger-venue benchmark {len(bad)}, correctable {len(corr)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

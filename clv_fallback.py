#!/usr/bin/env python3
"""
CLV FALLBACK RECOVERY (Peter, Nov 13 2026). READ-ONLY in this revision.

The games have finished, so a missing CLV should not depend on the live ledger's fixture-refresh
race. This searches every fixture cache the repo already keeps - clv/state.enc, the separate
oddspapi/fixtures.json that other jobs maintain, and any clv_backup snapshot - plus the hcache
Pinnacle history already on disk, and reports for each live selection missing CLV exactly what is
there and what is not.

IDENTITY IS STRICTER HERE THAN IN THE LIVE MATCHER, DELIBERATELY. find_fixture's job is to be
safe at scale and it refuses an ambiguous match by design (Nov 5: "a wrong fixture produces a
confidently wrong CLV, which is worse than no CLV"). A fallback that relaxed that rule to raise
coverage would be manufacturing exactly what Peter forbade. So a fixture is accepted here only
when BOTH of these hold:

  * the two fixture participants map ONE-TO-ONE onto the two sides named by the row, each on a
    token the other side does not also carry, and
  * the fixture start is within 12 hours of the row's own game start, and the league agrees.

A fixture that fails either test is reported as AMBIGUOUS with the colliding tokens printed, and
is NOT used. That is a decision for Peter, not a default.

PRICE. The CLV uses the row's ACTUAL after-fee execution price via clv_ledger.eff_dec - the same
function the scorecard uses - never a hypothetical entry. A row with no price is reported as
such.

AGREEMENT. compute_clv() is the single arithmetic path: no-vig from the two closing decimals, the
held side chosen the same way, then close x after-fee - 1. The scorecard and this fallback call it
on the same inputs, so they cannot disagree; test_clv_fallback.py asserts that against
clv_ledger.close_for on shared inputs.

WRITES NOTHING in this revision. APPLY=1 is accepted but refused with a message, because saving a
recovered CLV against a live selection changes the measured record and is Peter's call once he has
seen what would be written.
"""
import collections
import glob
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
MKFILE = "clv/markets.json"
ALT_FX = ["oddspapi/fixtures.json"]
ONLY = (os.environ.get("ONLY") or "").strip().lower()
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def am(dec):
    return round(-100 / (dec - 1)) if dec < 2 else round(100 * (dec - 1))


def load_all_fixtures():
    """Every fixture this repo already holds, with where it came from. No fetch."""
    out, src = {}, {}
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception:
        st = {}
    for fid, f in (st.get("fixtures") or {}).items():
        out[fid] = f
        src[fid] = "clv/state.enc"
    for path in ALT_FX:
        try:
            d = json.load(open(path))
        except Exception:
            continue
        for fid, f in (d.get("fixtures") or {}).items():
            if fid not in out:
                out[fid] = f
                src[fid] = path
    for path in sorted(glob.glob("clv_backup/*.enc")):
        try:
            d = tb.dec(json.load(open(path)))
        except Exception:
            continue
        for fid, f in (d.get("fixtures") or {}).items():
            if fid not in out:
                out[fid] = f
                src[fid] = path
    return st, out, src


def sides_of(s):
    """The two sides the row names, as token sets: from snap.teams when present, else game text."""
    tms = [(t.get("name") or "").strip() for t in (s.get("teams") or []) if (t.get("name") or "").strip()]
    if len(tms) >= 2:
        return [tb.toks(tms[0]) - tb.WEAK, tb.toks(tms[1]) - tb.WEAK], "snap.teams"
    txt = str(s.get("game") or "").replace(" v ", " @ ").replace(" vs ", " @ ")
    parts = [p for p in txt.split("@") if p.strip()]
    if len(parts) == 2:
        return [tb.toks(parts[0]) - tb.WEAK, tb.toks(parts[1]) - tb.WEAK], "game text"
    return None, "could not split the row into two sides"


def strict_match(s, fixtures):
    """(fid, note) for the ONE fixture that maps one-to-one onto the row, or (None, why)."""
    sides, how = sides_of(s)
    if not sides or not all(sides):
        return None, f"no two distinguishable sides on the row ({how})"
    gs = cl.tp(s.get("game_start"))
    lg = s.get("league")
    ok, amb = [], []
    for fid, f in fixtures.items():
        if f.get("lg") != lg:
            continue
        fs = cl.tp(f.get("start"))
        if gs and fs and abs((fs - gs).total_seconds()) > 12 * 3600:
            continue
        p1 = tb.toks(f.get("p1") or "") - tb.WEAK
        p2 = tb.toks(f.get("p2") or "") - tb.WEAK
        for a, b in ((p1, p2), (p2, p1)):
            ha, hb = a & sides[0], b & sides[1]
            if not (ha and hb):
                continue
            # one-to-one: each side must be carried by a token the OTHER side does not also hold
            if (ha - hb) and (hb - ha):
                ok.append((fid, f))
            else:
                amb.append((fid, f, ha & hb))
            break
    if len(ok) == 1:
        return ok[0][0], f"unique one-to-one match ({how})"
    if len(ok) > 1:
        return None, f"{len(ok)} fixtures match one-to-one - ambiguous, not used"
    if amb:
        fid, f, shared = amb[0]
        return None, (f"AMBIGUOUS: {str(f.get('p1'))[:26]} v {str(f.get('p2'))[:26]} - both sides "
                      f"share {sorted(shared)}, so neither is distinguished. Not used.")
    return None, "no fixture in any cache matches this league and date"


def cached_pin(fid):
    p = os.path.join(HC, f"{fid}__pinnacle.json.gz")
    if not os.path.exists(p):
        return None
    try:
        with gzip.open(p, "rt") as fh:
            return {"bookmakers": {"pinnacle": json.load(fh)}}
    except Exception:
        return None


def compute_clv(p_held, dec):
    """THE single arithmetic path. close win chance x after-fee decimal - 1."""
    return round(p_held * dec - 1, 4)


def close_at_line(pm, f, s, start, mkmap):
    """(p_held, evidence) at the bet's own line, or (None, why). No conversion, ever."""
    pz = cl.parsed(s)
    if not pz:
        return None, "bet text did not parse"
    sid = cl.SPORT.get(s.get("league"))
    if sid is None:
        return None, f"league {s.get('league')} has no OddsPapi sport id"
    typ = "spreads" if pz[0] == "spread" else "totals" if pz[0] == "total" else "ml"
    if typ == "ml":
        return None, "moneyline: handled by the live path, not this fallback"
    want = pz[2]
    side_is_a = (pz[1] == "OVER") if typ == "totals" else None
    if typ == "spreads":
        sd = cl.which_team(f, pz[1])
        if not sd:
            return None, "held team not matched to either side of the fixture"
        if pz[3]:
            sd, want = ("2" if sd == "1" else "1"), -want
        want = want if sd == "1" else -want
        side_is_a = (sd == "1")
    for mid, (sp, t, hcap, outs) in (mkmap or {}).items():
        if sp != sid or t != typ or mid not in pm or abs(hcap - want) > 1e-9:
            continue
        tw = cl.two_way(pm, mid, start)
        nm = {v: k for k, v in outs.items()}
        a, b = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
        if a not in tw or b not in tw:
            continue
        age = (start - min(tw[a][1], tw[b][1])).total_seconds() / 60
        if age > cl.FRESH_MIN:
            return None, f"closing tick {age / 60:.0f}h stale (limit {cl.FRESH_MIN / 60:.0f}h)"
        p_a = cl.novig_p(tw[a][0], tw[b][0])
        return (p_a if side_is_a else 1 - p_a), {
            "line": want, "dec_a": tw[a][0], "dec_b": tw[b][0],
            "tick_a": tw[a][1], "tick_b": tw[b][1],
            "limit_a": tw[a][2], "limit_b": tw[b][2], "age_min": age,
            "p_a": p_a, "names": ("team 1", "team 2") if typ == "spreads" else ("Over", "Under")}
    return None, f"Pinnacle did not hang {want:g} with two sides before start"


def main():
    now = datetime.now(timezone.utc)
    say("CLV FALLBACK RECOVERY - READ-ONLY. No fetch, no write, no CLV saved.")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("Searches clv/state.enc, oddspapi/fixtures.json and clv_backup snapshots for fixtures,")
    say("and the hcache files already on disk for Pinnacle history. Identity is STRICTER than the")
    say("live matcher: an ambiguous fixture is reported, never used.")
    say("=" * 100)
    if os.environ.get("APPLY") == "1":
        say("  APPLY=1 REFUSED: this revision writes nothing. Saving a recovered CLV changes the")
        say("  measured record, so it waits for Peter's go once he has seen what would be written.")
    st, fixtures, src = load_all_fixtures()
    try:
        mkmap = (json.load(open(MKFILE)) or {}).get("m") or {}
    except Exception as e:
        say(f"FATAL: {MKFILE} unreadable ({type(e).__name__})")
        return 1
    bets = st.get("bets") or {}
    by_src = collections.Counter(src.values())
    say(f"  ledger rows {len(bets)} | fixtures available {len(fixtures)} {dict(by_src)}")
    say(f"  hcache files {len(os.listdir(HC)) if os.path.isdir(HC) else 0}")

    live = [(k, r) for k, r in bets.items()
            if r.get("clv") is None and str((r.get("snap") or {}).get("source") or "").lower().startswith("bot")]
    allmiss = [(k, r) for k, r in bets.items() if r.get("clv") is None]
    say(f"  rows missing CLV: {len(allmiss)} total, {len(live)} from the bot (live lanes)")
    todo = [(k, r) for k, r in allmiss
            if not ONLY or ONLY in " ".join(str((r.get("snap") or {}).get(x) or "")
                                            for x in ("game", "bet", "league")).lower()]
    if ONLY:
        say(f"  filtered to ONLY='{ONLY}': {len(todo)} row(s)")

    tally = collections.Counter()
    for k, r in sorted(todo):
        s = r.get("snap") or {}
        say("")
        say(f"  ROW {k[:52]}")
        say(f"    {s.get('league')} | {str(s.get('game'))[:46]} | {s.get('bet')} | "
            f"book {s.get('book')} | source {s.get('source')}")
        say(f"    stored reason: {str(r.get('why') or '-')[:70]}   tries {r.get('tries')} "
            f"done {bool(r.get('done'))}   result {s.get('result') or 'UNSETTLED'}")
        # Some rows are retired by a DECISION, not a missing input: an in-play bet has no
        # pre-game close to beat, an unparsable bet has no side to price, a puck line at another
        # number is not comparable. A close being findable does not make those recoverable, and
        # the first run of this pass offered to "recover" mn|c6ab79076ef3 - retired "placed after
        # start (in-play): not scored" - at +2.47%. That would have been manufactured coverage on
        # a bet that has no pre-game close by definition.
        _why = str(r.get("why") or "").lower()
        if r.get("done") and any(p in _why for p in ("placed after start", "not parsed",
                                                     "not comparable", "far from")):
            say("    SKIPPED: correctly retired by policy, not a data gap - no close applies")
            tally["policy_retired"] += 1
            continue
        fid, note = strict_match(s, fixtures)
        if not fid:
            say(f"    FIXTURE: {note}")
            tally["no_fixture"] += 1
            continue
        f = fixtures[fid]
        say(f"    FIXTURE: {fid} from {src.get(fid)}  ({note})")
        say(f"      {str(f.get('p1'))[:34]} v {str(f.get('p2'))[:34]}  start {f.get('start')}")
        tally["fixture_found"] += 1
        start = cl.tp(f.get("start")) or cl.tp(s.get("game_start"))
        h = cached_pin(fid)
        if h is None:
            say(f"    HISTORY: no hcache file for {fid} - MISSING HISTORICAL MARKET DATA. A free")
            say("      /historical-odds call would be needed; this revision makes none.")
            tally["no_history"] += 1
            continue
        pm = cl.book_markets(h, "pinnacle")
        if not pm:
            say("    HISTORY: cached file holds no Pinnacle markets - MISSING MARKET DATA")
            tally["no_pinnacle"] += 1
            continue
        p_held, ev = close_at_line(pm, f, s, start, mkmap)
        if p_held is None:
            say(f"    CLOSE: {ev}")
            tally["no_close"] += 1
            continue
        dec = cl.eff_dec(s)
        na, nb = ev["names"]
        say(f"    CLOSE at our exact line {ev['line']:g}:")
        say(f"      {na:<7} {ev['dec_a']:.4f} ({am(ev['dec_a']):+d})  tick "
            f"{ev['tick_a'].astimezone(timezone.utc):%Y-%m-%dT%H:%M:%SZ}  limit {ev['limit_a']:g}")
        say(f"      {nb:<7} {ev['dec_b']:.4f} ({am(ev['dec_b']):+d})  tick "
            f"{ev['tick_b'].astimezone(timezone.utc):%Y-%m-%dT%H:%M:%SZ}  limit {ev['limit_b']:g}")
        say(f"      {ev['age_min']:.0f} min before start   no-vig P({na}) {ev['p_a']:.4f}   "
            f"P(held) {p_held:.4f}")
        if not dec:
            say("    PRICE: the row carries NO after-fee execution price - no CLV computed.")
            tally["no_price"] += 1
            continue
        say(f"    PRICE: actual after-fee {dec:.4f} ({am(dec):+d}) from the row's own stake/payout")
        say(f"    WOULD RECOVER CLV = {p_held:.4f} x {dec:.4f} - 1 = "
            f"{100 * compute_clv(p_held, dec):+.2f}%   (NOT saved)")
        tally["recoverable"] += 1

    say("")
    say("SUMMARY")
    say("=" * 100)
    say(f"  rows examined                 {len(todo)}")
    say(f"  skipped, retired by policy    {tally['policy_retired']}")
    say(f"  fixture found in a cache      {tally['fixture_found']}")
    say(f"  no fixture / ambiguous        {tally['no_fixture']}")
    say(f"  fixture but no cached history {tally['no_history'] + tally['no_pinnacle']}")
    say(f"  history but no same-line close{tally['no_close']}")
    say(f"  close but no execution price  {tally['no_price']}")
    say(f"  WOULD RECOVER                 {tally['recoverable']}")
    say("")
    say("  Nothing was fetched and nothing was saved. Every gap above names the specific missing")
    say("  data rather than being filled in.")
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("CLV fallback recovery (read-only)", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"fallback: examined {len(todo)}, fixtures {tally['fixture_found']}, "
          f"would recover {tally['recoverable']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

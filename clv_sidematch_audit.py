#!/usr/bin/env python3
"""
SIDE-MATCH AUDIT (Peter, Nov 14 2026). READ-ONLY.

Ten rows have a fixture AND cached Pinnacle history and still produce no close, because
which_team() cannot resolve the bet's team text to either participant. Peter: "Treat these as
pipeline defects until proven otherwise. Verify league, game date, both teams, orientation,
market and line against authoritative fixture metadata. Never force an ambiguous match."

So this does not fix anything. It prints, for every such row, what the bet text actually says,
what the parser made of it, what the fixture's two participants are, and which authoritative
metadata is available to resolve the side - snap.teams, the tracker row's own label/ticker, and
the registry strike record. That is the evidence needed to decide whether each one is a defect we
can repair or a row with no recoverable side.

READ-ONLY: no write, no fetch, no OddsPapi call, no IMAP.
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
MKFILE = "clv/markets.json"
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def cached_pin(fid):
    p = os.path.join(HC, f"{fid}__pinnacle.json.gz")
    if not os.path.exists(p):
        return None
    try:
        with gzip.open(p, "rt") as fh:
            return {"bookmakers": {"pinnacle": json.load(fh)}}
    except Exception:
        return None


def main():
    now = datetime.now(timezone.utc)
    say("SIDE-MATCH AUDIT - why a row with a fixture and history still has no close")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET   READ-ONLY, nothing written or fetched")
    say("=" * 104)
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
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception:
        tracker = {}
    smap = {}
    try:
        import registry as _reg
        smap = _reg.strike_map() if _reg.enabled() else {}
    except Exception:
        pass
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    fxs = st.get("fixtures") or {}

    hits, resolves, why_counter = [], [], collections.Counter()
    for k, r in (st.get("bets") or {}).items():
        if r.get("clv") is not None:
            continue
        s = r.get("snap") or {}
        fid, where, _note = cb.resolve_fixture(s, fxs, alt, cl.find_fixture, fxm.ordered_match, cl.tp)
        if not fid:
            continue
        h = cached_pin(fid)
        if h is None:
            continue
        f = fxs.get(fid) or alt.get(fid) or {}
        p, why = cb.pinnacle_no_vig_close(f, s, mkmap, cl.book_markets(h, "pinnacle"), cl.parsed,
                                          cl.which_team, cl.two_way, cl.novig_p, cl.SPORT,
                                          cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
        if p is not None:
            # It resolves NOW. If the row is retired, the pending loop will never reach it -
            # done is checked before anything else - so the fix cannot land without a reopen.
            resolves.append((k, r, f, fid, where, p, cl.eff_dec(s)))
            continue
        why_counter[str(why)[:60]] += 1
        if "held team not matched" in str(why) or "never recorded" in str(why) \
                or "names no team" in str(why) or "politics" in str(why):
            hits.append((k, r, f, fid, where, why))

    say("")
    say("ROWS WITH A FIXTURE AND CACHED HISTORY BUT NO CLOSE, by reason")
    say("=" * 104)
    for w, n in why_counter.most_common():
        say(f"  {n:5d}  {w}")
    say("")
    say(f"SIDE-MATCH FAILURES IN DETAIL: {len(hits)}")
    say("=" * 104)
    say("For each: what the bet text says, what the parser made of it, the fixture's participants,")
    say("and the authoritative metadata available to resolve the side.")
    shapes = collections.Counter()
    for k, r, f, fid, where, _why in hits:
        s = r.get("snap") or {}
        pz = cl.parsed(s)
        trk = tracker.get(k) or {}
        sid = str(trk.get("strike") or "")
        ent = smap.get(sid) or {}
        say("")
        say(f"  ROW {k[:58]}")
        say(f"    league {s.get('league')}   game_start {str(s.get('game_start'))[:19]}   "
            f"book {s.get('book')}   source {s.get('source')}")
        say(f"    game text : {str(s.get('game'))[:78]}")
        say(f"    bet text  : {str(s.get('bet'))[:78]}")
        say(f"    parsed    : {pz}")
        say(f"    fixture   : {fid} (from {where})")
        say(f"      p1 {str(f.get('p1'))[:46]}")
        say(f"      p2 {str(f.get('p2'))[:46]}")
        team_text = pz[1] if pz and pz[0] != "total" else None
        if team_text is not None:
            w = tb.toks(team_text)
            say(f"    team text tokens {sorted(w)}  vs p1 {sorted(tb.toks(f.get('p1') or '') & w)} "
                f"/ p2 {sorted(tb.toks(f.get('p2') or '') & w)}")
        say(f"    AUTHORITATIVE METADATA AVAILABLE:")
        tms = [(t.get('name') or '') for t in (s.get("teams") or [])]
        say(f"      snap.teams        : {tms or 'NONE'}")
        say(f"      tracker label     : {str(trk.get('bet') or trk.get('label') or 'NONE')[:52]}")
        say(f"      tracker ticker    : {str(trk.get('ticker') or 'NONE')[:52]}")
        say(f"      registry strike   : {str(ent.get('label') or 'NONE')[:52]}"
            f"  (game {str(ent.get('game') or 'NONE')[:32]})")
        # what SHAPE of defect is this
        if pz and pz[0] == "ml" and not tb.toks(str(pz[1])) - {"", }:
            shape = "bet text has NO team at all"
        elif pz and pz[0] == "ml" and any(ch.isdigit() for ch in str(pz[1])):
            shape = "bet text is a bare number - the side was never recorded in it"
        elif tms:
            shape = "bet text unresolvable BUT snap.teams names both sides"
        elif ent.get("label"):
            shape = "bet text unresolvable BUT the registry strike holds a label"
        else:
            shape = "no authoritative side anywhere - not recoverable"
        shapes[shape] += 1
        say(f"    -> {shape}")

    say("")
    say("ROWS THAT RESOLVE NOW BUT CANNOT BE REACHED")
    say("=" * 104)
    say("These produce a close under the current code. A row with done=True is skipped by the")
    say("pending loop before anything else, so the fix cannot land on it without a one-time")
    say("reopen - which is what clv_reopen_once.py is for, with its allowlist and APPLY gate.")
    retired = [x for x in resolves if (x[1].get("done") and x[1].get("tries") == cl.MAX_TRIES)]
    other = [x for x in resolves if x not in retired]
    say(f"  resolve now: {len(resolves)}   of those retired at tries={cl.MAX_TRIES}: {len(retired)}"
        f"   reachable without a reopen: {len(other)}")
    for k, r, f, fid, where, p, dec in resolves:
        s_ = r.get("snap") or {}
        clv_ = cb.clv(p, dec)
        say(f"    {k[:44]:<44} done={bool(r.get('done'))} tries={r.get('tries')}  "
            f"CLV would be {('%+.2f%%' % (100 * clv_)) if clv_ is not None else 'UNKNOWN (no price)'}")
        say(f"        {s_.get('league')} | {str(s_.get('game'))[:40]} | {str(s_.get('bet'))[:20]}"
            f"  stored reason: {str(r.get('why'))[:38]}")
    if retired:
        say("")
        say("  REOPEN_IDS allowlist for the retired ones (copy verbatim):")
        say("    " + ",".join(k for k, *_ in retired))
        say(f"    REOPEN_EXPECT={len(retired)}")

    say("")
    say("SHAPES")
    say("=" * 104)
    for sh, n in shapes.most_common():
        say(f"  {n:5d}  {sh}")
    say("")
    say("  A shape naming authoritative metadata is a PIPELINE DEFECT we can repair. 'no")
    say("  authoritative side anywhere' is not: forcing a side from an ambiguous description is")
    say("  exactly what must not happen on a live-money record.")
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("Side-match audit (read-only)", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"sidematch: {len(hits)} side-match failures, shapes {dict(shapes)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

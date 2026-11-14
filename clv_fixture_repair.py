#!/usr/bin/env python3
"""
STALE FIXTURE REPAIR - narrowly scoped, dry run by default (Peter, Nov 14 2026, explicit GO).

WHAT HAPPENED. Four rows retired at tries=8 with "team not matched" were reopened once, and only
ONE scored. The other three failed their single attempt for a reason the reopen could not see:
close_for prefers the row's STORED fixture id over re-resolving, and these rows carry a stale one
from an earlier wrong match. So the repaired side matcher was being asked to match "PUR" against
a different game's participants and failed again, exactly as before.

WHAT THIS DOES, and only this: for the ids on the explicit allowlist, it INDEPENDENTLY
establishes the correct fixture, and clears the stale id only when the replacement is uniquely
established. The stored CLV, price, result and tries are never touched. The original value and
the reason are written to an audit file before anything changes.

INDEPENDENT VERIFICATION - all six, per row, or the row is left alone:
  1 a UNIQUE one-to-one ordered match over every fixture we hold (state + the other stores)
  2 the fixture's league equals the row's league
  3 the fixture's start is within 12 h of the row's own game start
  4 both participants map to the row's two named sides, each on a token the other lacks
  5 the bet's side resolves against the NEW fixture (fixture_match.resolve_side)
  6 Pinnacle's cached history for the NEW fixture actually hangs the bet's OWN line with two
    sides before the start - so the repair is only made when it demonstrably produces a close
Condition 6 is what makes this a repair rather than a reshuffle: a swap that still yields no
close would be churn on a live-money record.

WHAT IT IS NOT. It does not change MAX_TRIES, the retirement logic or any global retry limit. It
does not reset tries - the reopen that follows gives each row exactly ONE attempt and the
existing guard retires it again on the next genuine failure. It never forces an ambiguous match:
two candidates means the row is left exactly as it is. It writes no CLV.

APPLY=1 is required to write. Without it this prints what it would do and changes nothing.
"""
import gzip
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import clv_basis as cb
import clv_ledger as cl
import fixture_match as fxm
import tracker_build as tb

ET = tb.ET
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
MKFILE = "clv/markets.json"
APPLY = (os.environ.get("REPAIR_APPLY") or "") == "1"
ALLOW = [x.strip() for x in (os.environ.get("REPAIR_IDS") or "").split(",") if x.strip()]
EXPECT = int(os.environ.get("REPAIR_EXPECT") or "0")
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
    say("STALE FIXTURE REPAIR - narrowly scoped" + ("  [APPLY]" if APPLY else "  [DRY RUN]"))
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("Clears a stale fixture id ONLY where the correct one is uniquely established and")
    say("demonstrably produces a close. No CLV, price, result, tries or retry limit is touched.")
    say("=" * 104)
    if not ALLOW:
        say("  REPAIR_IDS is empty - nothing to do. This script only ever acts on an explicit")
        say("  allowlist, so it cannot sweep the ledger.")
        return 0
    say(f"  allowlist: {len(ALLOW)} id(s)")
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
    bets = st.get("bets") or {}
    fxs = st.get("fixtures") or {}
    altmap = fxm.alt_fixtures()
    allfx = dict({fid: f for fid, (f, _s) in altmap.items()}, **fxs)
    say(f"  fixtures available for verification: {len(allfx)} "
        f"({len(fxs)} in state + {len(allfx) - len(fxs)} from other stores)")

    eligible, rejected = [], []
    for k in ALLOW:
        rec = bets.get(k)
        say("")
        say(f"  ROW {k[:64]}")
        if not rec:
            rejected.append((k, "id not in the ledger"))
            say("    REJECTED: id not in the ledger")
            continue
        s = rec.get("snap") or {}
        old_fid = rec.get("fixture")
        say(f"    {s.get('league')} | {str(s.get('game'))[:44]} | {str(s.get('bet'))[:22]}")
        say(f"    stored fixture: {old_fid}   stored reason: {str(rec.get('why'))[:48]}")
        if rec.get("clv") is not None:
            rejected.append((k, "already has a CLV - never overwritten"))
            say("    REJECTED: already has a CLV - never overwritten")
            continue
        if not old_fid:
            rejected.append((k, "no stored fixture - nothing stale to clear"))
            say("    REJECTED: no stored fixture - nothing stale to clear")
            continue
        oldf = allfx.get(old_fid) or {}
        say(f"      old -> {str(oldf.get('p1'))[:34]} v {str(oldf.get('p2'))[:34]} "
            f"({oldf.get('lg')}, {str(oldf.get('start'))[:19]})")
        # 1 unique one-to-one ordered match over EVERY fixture we hold
        new_fid, note = fxm.ordered_match(s, allfx, cl.tp)
        if not new_fid:
            rejected.append((k, f"not uniquely established: {note[:52]}"))
            say(f"    REJECTED: {note[:86]}")
            continue
        if new_fid == old_fid:
            rejected.append((k, "the stored fixture IS the uniquely established one - not stale"))
            say("    REJECTED: the stored fixture is the uniquely established one - not stale")
            continue
        f = allfx[new_fid]
        say(f"      new -> {str(f.get('p1'))[:34]} v {str(f.get('p2'))[:34]} "
            f"({f.get('lg')}, {str(f.get('start'))[:19]})   [{note}]")
        # 2 league, 3 date
        if f.get("lg") != s.get("league"):
            rejected.append((k, "league mismatch"))
            say("    REJECTED: league mismatch")
            continue
        gs, fsx = cl.tp(s.get("game_start")), cl.tp(f.get("start"))
        if gs and fsx and abs((fsx - gs).total_seconds()) > 12 * 3600:
            rejected.append((k, "start more than 12h from the row's own game start"))
            say("    REJECTED: start more than 12h from the row's own game start")
            continue
        say(f"      league ok, start within "
            f"{abs((fsx - gs).total_seconds()) / 3600:.1f}h of the row" if gs and fsx else
            "      league ok, no start time to compare")
        # 5 the side resolves against the NEW fixture
        pz = cl.parsed(s)
        if pz and pz[0] != "total":
            side, swhy = fxm.resolve_side(f, pz[1], s.get("league"), cl.which_team)
            if not side:
                rejected.append((k, f"side still unresolved against the new fixture: {swhy[:40]}"))
                say(f"    REJECTED: side still unresolved against the new fixture - {swhy[:60]}")
                continue
            say(f"      side resolves to participant {side} ({swhy})")
        # 6 Pinnacle actually hangs the bet's own line on the NEW fixture
        h = cached_pin(new_fid)
        if h is None:
            rejected.append((k, "no cached Pinnacle history for the new fixture"))
            say("    REJECTED: no cached Pinnacle history for the new fixture")
            continue
        p, why = cb.pinnacle_no_vig_close(f, s, mkmap, cl.book_markets(h, "pinnacle"), cl.parsed,
                                          cl.which_team, cl.two_way, cl.novig_p, cl.SPORT,
                                          cl.ML_MARKET, cl.FRESH_MIN, cl.tp)
        if p is None:
            rejected.append((k, f"new fixture yields no close: {str(why)[:44]}"))
            say(f"    REJECTED: the new fixture yields no close - {str(why)[:62]}")
            continue
        dec = cl.eff_dec(s)
        would = cb.clv(p, dec)
        say(f"      close at own line: P(held) {p:.4f}  how {why.get('how')}  "
            f"{why.get('age_min', 0):.0f} min before start")
        say(f"      after-fee entry {dec if dec else 'UNKNOWN'}   "
            f"CLV would be {('%+.2f%%' % (100 * would)) if would is not None else 'UNKNOWN'}")
        if would is None:
            rejected.append((k, "no executable after-fee price - CLV not computable"))
            say("    REJECTED: no executable after-fee price")
            continue
        say("    ELIGIBLE: all six conditions met")
        eligible.append((k, rec, old_fid, new_fid, would, note))

    say("")
    say("SUMMARY")
    say("=" * 104)
    say(f"  ELIGIBLE {len(eligible)}   REJECTED {len(rejected)}")
    for k, w in rejected:
        say(f"    {k[:46]:<46} {w}")
    if EXPECT and len(eligible) != EXPECT:
        say("")
        say(f"  STOP: REPAIR_EXPECT={EXPECT} but {len(eligible)} are eligible. Nothing written.")
        return 2
    if not eligible:
        say("  nothing to repair")
        return 0
    if not APPLY:
        say("")
        say("  DRY RUN - nothing written. Re-run with REPAIR_APPLY=1 and the same allowlist.")
        say("  REPAIR_IDS=" + ",".join(k for k, *_ in eligible))
        return 0

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=20).stdout.strip()
    except Exception:
        sha = ""
    audit = {"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "state_commit_before": sha,
             "reason": ("stale fixture assignment cleared where the correct fixture was uniquely "
                        "established and demonstrably produces a close; CLV, price, result and "
                        "tries untouched"),
             "rows": []}
    for k, rec, old_fid, new_fid, would, note in eligible:
        s = rec.get("snap") or {}
        audit["rows"].append({
            "id": k, "league": s.get("league"), "game": s.get("game"), "bet": s.get("bet"),
            "fixture_before": old_fid, "fixture_after": new_fid, "match_note": note,
            "why_before": rec.get("why"), "tries_before": rec.get("tries"),
            "done_before": bool(rec.get("done")), "projected_clv": would,
            "p1_before": (allfx.get(old_fid) or {}).get("p1"),
            "p2_before": (allfx.get(old_fid) or {}).get("p2"),
            "p1_after": allfx[new_fid].get("p1"), "p2_after": allfx[new_fid].get("p2")})
    path = f"clv/fixture_repair_{now:%Y%m%dT%H%M%S}Z.json"
    os.makedirs("clv", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(audit, fh, indent=1, sort_keys=True)
    say(f"  AUDIT written: {path} ({len(audit['rows'])} row(s)), state commit before {sha[:12]}")

    for k, rec, old_fid, new_fid, _w, _n in eligible:
        # The ONLY mutations: point the row at the established fixture and keep the old value on
        # the record. done is cleared so the ONE reopened attempt can happen; tries is left as it
        # is, so the existing guard retires the row again on the next genuine failure.
        rec["fixture_stale"] = {"was": old_fid, "why": rec.get("why"), "at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        rec["fixture"] = new_fid
        rec["done"] = False
        rec.pop("why", None)
    say(f"  repaired {len(eligible)} row(s): fixture re-pointed, done=False, tries UNCHANGED, no clv touched")
    with open(cl.STATE, "w") as fh:
        json.dump(tb.enc(st), fh)
    say(f"  state written: {cl.STATE}")
    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as _ex
            _ex.send("Stale fixture repair", "\n".join(L))
            print("report emailed", flush=True)
        except Exception as _e:
            print(f"email skipped ({type(_e).__name__})", flush=True)
    print(f"fixture repair: {'APPLIED' if APPLY else 'DRY RUN'}, eligible {len(eligible)}, "
          f"rejected {len(rejected)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

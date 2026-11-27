#!/usr/bin/env python3
"""READ-ONLY DIAGNOSTIC: why each qualifying DOGS signal did or did not become a bot order.

Peter, 27 Nov 2026: "Determine exactly why 16 qualifying signals produced zero bot orders. Show the rejection
reasons for each signal. Do not assume the 30-minute age limit is responsible."

It replays executor.dogs_select over the 5-minute tick grid the executor actually runs on, using the lane's own
functions - dogs_qualifies, dogs_bet, DOGS_MAX_AGE_MIN, the first-print rule - so the answer cannot drift from
the lane. For every qualifying print it prints the stage that rejected it, and for a print the lane WOULD have
selected it counts how many ticks it was selectable in, which is what settles the age-limit question.

What it cannot answer: the gates after selection need the venue books as they were at that tick (a venue in the
Dogs route at the alert line, alert price or better after fees, with liquidity). Only the executor's own run log
records those, and GitHub trims them, so for an older signal that stage is UNRECOVERABLE - stated, not guessed.

No network, no venue call, no order, no write. Run it with `python3 dogs_why.py` from the repo root."""
import json, sys, os
from datetime import datetime, timezone, timedelta
import executor as ex

Q = json.load(open("liquidity/alerts.json"))
rows = Q if isinstance(Q, list) else (Q.get("alerts") or [])
SINCE = "2026-11-23"

def iso(s): return ex.iso_t(s)

# the lane's own eligibility + first-print set, exactly as dogs_select builds it
elig = [x for x in rows if isinstance(x, dict) and not x.get("artifact") and not x.get("close_suspect")
        and str(x.get("book") or "").strip().lower() not in ex.DOGS_NOT_BETTABLE and iso(x.get("alerted_utc"))]
elig.sort(key=lambda x: iso(x.get("alerted_utc")))
first = {}
for x in elig:
    first.setdefault((str(x.get("game")).lower(), x.get("market"), str(x.get("side")).lower()), x)
firsts = set(id(v) for v in first.values())

cand = [x for x in rows if isinstance(x, dict) and str(x.get("alerted_utc") or "") >= SINCE and ex.dogs_qualifies(x)]
print(f"rows in feed {len(rows)} | qualifying prints since {SINCE} {len(cand)} "
      f"| of those, first print for their game+market+side {sum(1 for x in cand if id(x) in firsts)}")
print(f"DOGS_MAX_AGE_MIN={ex.DOGS_MAX_AGE_MIN} DOGS_MAX_PLAYS={ex.DOGS_MAX_PLAYS} "
      f"money {ex.DOGS_MIN_MONEY:.0f}-{ex.DOGS_MAX_MONEY:.0f} tol {ex.DOGS_TOL_CENTS}c ({ex.DOGS_GATE_VERSION})")
print()
hdr = f"{'alerted_utc':17} {'lg':6} {'market':10} {'book':9} {'px':>5} {'lead':>5}  {'selectable ticks':>16}  reason"
print(hdr); print("-" * len(hdr))

sel_rows = []
for x in sorted(cand, key=lambda z: str(z.get("alerted_utc"))):
    at, st = iso(x.get("alerted_utc")), iso(x.get("start_utc"))
    lead = "" if not (at and st) else f"{(st - at).total_seconds() / 60:.0f}"
    why, ticks = [], 0
    if id(x) not in firsts:
        f0 = first[(str(x.get("game")).lower(), x.get("market"), str(x.get("side")).lower())]
        why.append(f"NOT the first print (first was {f0.get('alerted_utc')} on {f0.get('book')})")
    if not st:
        why.append("no start_utc")
    if not ex.dogs_bet(x):
        why.append("bet string not readable (side is not one of the game string's two teams)")
    if at and st:
        # every 5-minute tick the executor could have run on
        t = at.replace(second=0, microsecond=0)
        end = min(st, at + timedelta(minutes=ex.DOGS_MAX_AGE_MIN))
        while t <= end:
            if t >= at and st > t and t - at <= timedelta(minutes=ex.DOGS_MAX_AGE_MIN):
                ticks += 1
            t += timedelta(minutes=5)
        if ticks == 0:
            why.append("no tick satisfies at<=now<start and now-at<=age limit")
    ok_sel = not why
    if ok_sel:
        sel_rows.append(x)
    print(f"{str(x.get('alerted_utc'))[:16]:17} {str(x.get('league')):6} {str(x.get('market')):10} "
          f"{str(x.get('book')):9} {str(x.get('price_american')):>5} {lead:>5}  {ticks:>16}  "
          f"{'SELECTABLE - rejection is downstream of selection' if ok_sel else ' + '.join(why)}")
print()
print(f"SELECTABLE by the lane's own rules: {len(sel_rows)} of {len(cand)}")
print("For a selectable signal the remaining gates are, in order:")
print("  MANUAL_HELD / LIVEKEYS / opp_bet  -> a manual note or another lane already holds this bet")
print("  verdict == WOULD PLACE and r['lc'] -> a venue IN THE DOGS ROUTE at the alert line, alert price")
print("     or better after fees (+" + str(ex.DOGS_TOL_CENTS) + "c), with liquidity")
print("  dogs_gate(risk, key)              -> kill bar, daily risk cap, play cap, unit ledger")
print("None of these can be evaluated from the feed alone: they need the venue books as they were at")
print("that tick. The executor's own run log is the only record of them.")

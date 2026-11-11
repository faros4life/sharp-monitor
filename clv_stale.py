#!/usr/bin/env python3
"""
STALE CLV ROW FILTER - read-time only (Peter, Nov 10 2026, Option 2: "Exclude confirmed stale/orphaned rows at
read time. Preserve the original CLV state.").

WHY THIS EXISTS. man_id changed on Nov 5 from a hash of the whole "MANUAL: {...}" note line to book+game+bet, and
tracker_build.man_migrate retires the old key IN THE TRACKER. clv_ledger only ever setdefault()s keys into its own
st["bets"] and prunes by first_seen age (60 days), so a retired key survives there carrying the snapshot and CLV it
held at the moment it was retired - including, for some rows, the INVENTED stake the old sizing rule guessed before
Peter's real stakes arrived. Measured Nov 10: 12 such rows, all Hard Rock manual, double-counted in the ledger
report, in plays_kelly's ACTUAL dollars and in bucket_report's ledger buckets.

THE TEST IS TRACKER PRESENCE PLUS ID RESOLUTION, never game/line/price identity (Peter: "Don't assume identical
games, lines, and prices are duplicate wagers"):
  the key is absent from the tracker state, AND
  man_id(book, game, bet) of its own snapshot resolves to a key that IS present in the tracker.
Both conditions, or the row is left alone. An orphan that fails the second test is UNPROVEN - it may be a real bet
whose tracker row simply aged out (the tracker keeps 10 days of notes; clv keeps 60 days) - and is reported, never
excluded.

This module writes nothing, deletes nothing and recalculates nothing. It only says which keys a reader should skip.

FAIL-SAFE BY CONSTRUCTION: both conditions are checked against the tracker dict. If the tracker is unreadable and an
empty dict is passed, every key looks absent but nothing can resolve, so the result is empty and NOTHING is
excluded. A missing tracker must never silently delete rows from a report.
"""
import tracker_build as tb


def stale_map(bets, trk):
    """{stale key: the live tracker key it resolves to} for PROVEN stale duplicates only.

    bets: the clv state's "bets" dict. trk: the tracker state's "bets" dict.
    """
    out = {}
    if not bets or not trk:
        return out
    for k, r in bets.items():
        if k in trk or not str(k).startswith("mn|"):
            continue
        s = (r or {}).get("snap") or {}
        try:
            cand = tb.man_id(s.get("book"), s.get("game"), s.get("bet"))
        except Exception:
            continue
        if cand and cand != k and cand in trk:
            out[k] = cand
    return out


def orphans_unproven(bets, trk):
    """Keys absent from the tracker that do NOT resolve. Reported and flagged, never excluded."""
    if not bets or not trk:
        return []
    bad = stale_map(bets, trk)
    return sorted(k for k in bets if k not in trk and k not in bad)


def load_tracker():
    """The tracker's bets dict, or {} when it cannot be read (which disables exclusion - see FAIL-SAFE)."""
    import json
    try:
        return (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception:
        return {}


def live_bets(bets, trk=None):
    """(filtered bets dict, stale_map, unproven orphan keys). The input dict is never mutated."""
    trk = load_tracker() if trk is None else trk
    bad = stale_map(bets or {}, trk)
    kept = {k: v for k, v in (bets or {}).items() if k not in bad}
    return kept, bad, orphans_unproven(bets or {}, trk)


def note(bad, unproven):
    """One line for a report, so an exclusion is never silent."""
    s = f"stale rows excluded at read time: {len(bad)} (proven duplicates of a live tracker row; stored state untouched)"
    if unproven:
        s += f" | unproven orphans kept and flagged: {len(unproven)}"
    return s

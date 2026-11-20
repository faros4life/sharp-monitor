#!/usr/bin/env python3
"""Export ledger fixture identity + raw close evidence for Muse's backfill.

Muse, Nov 20, two asks: (1) OddsPapi fixture id + game + start time, so its backfill can match
events by ID instead of team name - which is where the misses happen, the St Bonaventure name
problem; (2) the per-row tick timestamps and raw side prices behind V1, so any future
V1-vs-snapshot gap is attributed exactly instead of inferred.

CONTAINS NO MONEY. No stake, payout, profit, balance or account identifier - fixture identity,
lines, odds, tick ages and CLV percentages only, per the standing export rule. Read-only on
state: nothing is written back to the ledger and no live path is touched.
"""
import json
import os
import sys

import tracker_build as tb

STATE = "clv/state.enc"
MONEY = ("stake", "to_pay", "profit", "payout", "balance", "pnl", "cost")


def row(k, rec, fixtures):
    s = rec.get("snap") or {}
    fid = rec.get("fixture")
    fx = (fixtures or {}).get(fid) or {}
    out = {
        "fixture_id": fid,
        "odds_api_event_id": fx.get("id") or fid,
        "game": s.get("game"),
        "teams": [t.get("name") for t in (s.get("teams") or []) if isinstance(t, dict)],
        "league": s.get("league"),
        "book": s.get("book"),
        "bet": s.get("bet"),
        "game_start": fx.get("start") or s.get("game_start"),
        "placed": s.get("placed"),
        "settled": s.get("settled"),
        "our_line": rec.get("our_line"),
        "main_line": rec.get("main_line"),
        "close_how": rec.get("how"),
        "close_age_min": rec.get("age_min"),
        "clv_v1_pct": None if rec.get("clv") is None else round(rec["clv"] * 100, 4),
        "clv_v2_pct": None if rec.get("clv_v2") is None else round(rec["clv_v2"] * 100, 4),
        "v2_unsupported": rec.get("v2_unsupported"),
        # the raw two-sided decimals and their tick ages, held side FIRST
        "alt_px_decimal": rec.get("alt_px"),
        "main_px_decimal": rec.get("main_px"),
        "tick_ages_min_before_start": rec.get("ts_ages"),
        "not_scored_reason": rec.get("why"),
    }
    assert not any(m in out for m in MONEY), "money field leaked into the export"
    return out


def build(st):
    fixtures = st.get("fixtures") or {}
    rows = [row(k, rec, fixtures) for k, rec in (st.get("bets") or {}).items()]
    with_fid = sum(1 for r in rows if r["fixture_id"])
    with_start = sum(1 for r in rows if r["game_start"])
    with_raw = sum(1 for r in rows if r["alt_px_decimal"] and r["main_px_decimal"])
    with_ticks = sum(1 for r in rows if r["tick_ages_min_before_start"])
    return {
        "export": "claude ledger fixture + close evidence",
        "note": "No money in this file by design: fixture identity, lines, odds, tick ages and CLV "
                "percentages only. Match on fixture_id / odds_api_event_id, not on team name.",
        "rows": len(rows),
        "with_fixture_id": with_fid,
        "with_game_start": with_start,
        "with_raw_two_sided_prices": with_raw,
        "with_tick_ages": with_ticks,
        "data": rows,
    }


def main(argv):
    if not tb.PASS:
        print("fixture export: TRACKER_PASSPHRASE not set", flush=True)
        return 1
    try:
        st = tb.dec(json.load(open(STATE))) or {}
    except Exception as e:
        print(f"fixture export: state unreadable ({type(e).__name__})", flush=True)
        return 1
    out = build(st)
    path = argv[1] if len(argv) > 1 else "claude_fixtures.json"
    json.dump(out, open(path, "w"), indent=1)
    print(f"fixture export: {out['rows']} rows | fixture_id {out['with_fixture_id']}"
          f" | game_start {out['with_game_start']}"
          f" | raw two-sided prices {out['with_raw_two_sided_prices']}"
          f" | tick ages {out['with_tick_ages']} -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

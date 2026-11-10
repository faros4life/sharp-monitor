#!/usr/bin/env python3
"""
Polymarket US SLUG LOOKUP (Nov 9). Read-only: lists market slugs so a slug can be handed to
pmus_rest_order_test. NO ORDER CODE - this only performs GETs.

WHY. The resting-bid test needs a market SLUG string. Muse can pull numeric market/game IDs from the
monitor feed (tonight: 5651101 / 5651104, Flyers vs Canucks) but has no verified slug source and
rightly would not guess at the format. This closes that gap rather than anyone inventing one.

HOW. Uses the same endpoints executor._pmus_game_markets already relies on, in the same order, so
this inherits a path that is known to work rather than a new guess:
    /v1/markets?gameId=<id>&limit=100
    /v1/events/slug/<slug>  |  /v1/events?slug=  |  /v1/events?id=
For each market found it prints the slug, the title, and - where readable - the best offer, since
the test refuses to price an order without one.

Run with PMUS_GAME_ID set to one or more comma-separated ids. Counts and market metadata only; no
balances, positions or order data.
"""
import json
import os
import sys

import executor as ex
import liquidity_monitor as lm

PMUS = ex.PMUS


def say(s):
    print(s, flush=True)


def markets_for(gid):
    """Markets for one game id, trying the executor's own endpoint order."""
    tries = [("markets?gameId", f"{PMUS}/v1/markets", {"gameId": gid, "limit": 100}),
             ("events?id", f"{PMUS}/v1/events", {"id": gid}),
             ("events/slug", f"{PMUS}/v1/events/slug/{gid}", None)]
    for how, url, params in tries:
        try:
            d = lm.get(url, params)
        except Exception as e:
            say(f"    {how}: error {str(e)[:70]}")
            continue
        mks = d.get("markets") if isinstance(d, dict) else d
        if isinstance(d, dict) and not mks:
            mks = (d.get("event") or {}).get("markets")
        if isinstance(d, dict) and not mks and d.get("events"):
            mks = [m for e in d["events"] for m in (e.get("markets") or [])]
        if mks:
            say(f"    {how}: {len(mks)} market(s)")
            return [m for m in mks if isinstance(m, dict)]
        say(f"    {how}: none")
    return []


def best_offer(slug):
    try:
        md = (lm.get(f"{PMUS}/v1/markets/{slug}/book") or {}).get("marketData") or {}
    except Exception:
        return None
    for k in ("bestAsk", "best_ask", "ask", "bestOffer"):
        v = md.get(k)
        if isinstance(v, (int, float)) and 0 < float(v) < 1:
            return float(v)
        if isinstance(v, dict):
            for kk in ("value", "price"):
                try:
                    f = float(v.get(kk))
                    if 0 < f < 1:
                        return f
                except (TypeError, ValueError):
                    pass
    return None


def main():
    ids = [x.strip() for x in (os.environ.get("PMUS_GAME_ID") or "").split(",") if x.strip()]
    if not ids:
        sys.exit("Set PMUS_GAME_ID to one or more comma-separated Polymarket US game/market ids.")
    say("POLYMARKET US SLUG LOOKUP (read-only; no order code)")
    for gid in ids:
        say(f"\n=== id {gid} ===")
        mks = markets_for(gid)
        if not mks:
            say("    no markets found on any known path for this id")
            continue
        for m in mks:
            slug = m.get("slug") or m.get("marketSlug")
            if not slug:
                continue
            title = (m.get("question") or m.get("title") or m.get("name") or "")[:66]
            bo = best_offer(slug)
            flag = ""
            if bo is None:
                flag = "   [no best offer - the test would refuse to price this one]"
            say(f"    slug: {slug}")
            say(f"          {title}")
            say(f"          best offer: {('%.3f' % bo) if bo is not None else '-'}{flag}")
    say("\nPick a full-game MONEYLINE slug with a readable best offer, then run pmus-rest-order-test")
    say("with it. That test places ONE real contract 15c below the offer - Peter runs it, not Claude.")


if __name__ == "__main__":
    main()

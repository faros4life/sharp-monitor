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


def by_league(sport):
    """Every full-game market for a league, the way executor.pmus_events enumerates them.

    Added after the id lookup came back empty: the numeric ids from the monitor feed are NOT
    Polymarket ids, so there was nothing to resolve. This path needs no id at all - it lists the
    venue's own live events, which is what the executor itself does on every run."""
    evs = []
    for slug in ex.PMUS_LEAGUES.get(sport.upper(), []):
        try:
            d = lm.get(f"{PMUS}/v2/leagues/{slug}/events", {"limit": 200})
        except Exception as e:
            say(f"    leagues/{slug}/events: error {str(e)[:70]}")
            continue
        evs = (d or {}).get("events") or []
        say(f"    leagues/{slug}/events: {len(evs)} event(s)")
        if evs:
            break
    for ev in evs:
        title = ev.get("title") or ev.get("name") or ev.get("slug") or "?"
        mks = [m for m in (ev.get("markets") or []) if isinstance(m, dict)]
        if not mks:
            mks = markets_for_event(ev)
        shown = 0
        for m in mks:
            slug = m.get("slug") or m.get("marketSlug")
            if not slug:
                continue
            try:
                if not ex.pmus_type(m):
                    continue            # full-game markets only, the executor's own filter
            except Exception:
                pass
            bo = best_offer(slug)
            if bo is None:
                continue                 # no book = the test would refuse it anyway
            if not shown:
                say(f"\n  {title}")
            shown += 1
            say(f"    slug: {slug}")
            say(f"          {(m.get('question') or m.get('title') or '')[:66]}")
            say(f"          best offer: {bo:.3f}")


def markets_for_event(ev):
    for how, url, params in (("events/slug", f"{PMUS}/v1/events/slug/{ev.get('slug')}", None),
                             ("events?id", f"{PMUS}/v1/events", {"id": ev.get("id")})):
        if "None" in url:
            continue
        try:
            d = lm.get(url, params)
        except Exception:
            continue
        mks = (d or {}).get("markets") or ((d or {}).get("event") or {}).get("markets")
        if mks:
            return [m for m in mks if isinstance(m, dict)]
    return []


def main():
    sport = (os.environ.get("PMUS_SPORT") or "").strip()
    ids = [x.strip() for x in (os.environ.get("PMUS_GAME_ID") or "").split(",") if x.strip()]
    if not ids and not sport:
        sys.exit("Set PMUS_SPORT (NHL/NBA/NFL/...) to list live markets, or PMUS_GAME_ID for a specific id.")
    say("POLYMARKET US SLUG LOOKUP (read-only; no order code)")
    if sport:
        say(f"\n=== live {sport.upper()} markets ===")
        by_league(sport)
        if not ids:
            say("\nPick a full-game MONEYLINE slug above, then run pmus-rest-order-test with it.")
            say("That test places ONE real contract 15c below the offer - Peter runs it, not Claude.")
            return
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

#!/usr/bin/env python3
"""ProphetX tournament lookup (manual, read-only). Fast version: lists every basketball tournament name + ID from one
call, and checks events only for likely NCAA men's season tournaments. Login + reads only; never touches orders."""
import json
import time
import urllib.error

import liquidity_monitor as lm


def events(tid):
    try:
        evs = (lm.px_call(f"/mm/get_sport_events?tournament_id={tid}").get("data") or {}).get("sport_events") or []
        up = [e for e in evs if (e.get("status") or "not_started") == "not_started"]
        first = (up or evs or [{}])[0]
        return f"events {len(evs)} (upcoming {len(up)})" + (f" e.g. {first.get('name')} {first.get('scheduled')}" if first else "")
    except urllib.error.HTTPError as ex:
        return f"events: HTTP {ex.code}"
    except Exception as ex:
        return f"events: {str(ex)[:60]}"


def main():
    if not (lm.PX_ACCESS and lm.PX_SECRET):
        raise SystemExit("Missing PROPHETX_ACCESS_KEY / PROPHETX_SECRET_KEY")
    d = lm.px_call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
    lm._PXT["token"] = (d.get("data") or {}).get("access_token")
    tl = ((lm.px_call("/mm/get_tournaments").get("data") or {}).get("tournaments")) or []
    sports = {}
    for t in tl:
        s = json.dumps(t.get("sport"))[:60]
        sports[s] = sports.get(s, 0) + 1
    print(f"Tournaments: {len(tl)}. Sport values: {sports}\n")
    bb = [t for t in tl if "basketball" in json.dumps(t).lower() or any(
        w in (t.get("name") or "").lower() for w in ("ncaa", "college", "cbb"))]
    print(f"Basketball / college tournaments ({len(bb)}):")
    for t in sorted(bb, key=lambda x: str(x.get("name"))):
        print(f"  {t.get('id')!s:>11}  {t.get('name')}  | sport {json.dumps(t.get('sport'))[:50]} | category {json.dumps(t.get('category'))[:50]}")
    cands = [t for t in bb if any(w in (t.get("name") or "").lower() for w in ("ncaab", "ncaam", "college basketball",
             "ncaa basketball", "ncaa men")) and not any(w in (t.get("name") or "").lower() for w in (
             "future", "field of", "conference tournament", "women", "specials"))]
    print(f"\nEvent check for likely NCAA men's season tournaments ({len(cands)}):")
    for t in cands[:12]:
        print(f"  {t.get('id')!s:>11}  {t.get('name')}  | {events(t.get('id'))}")
        time.sleep(0.2)


if __name__ == "__main__":
    main()

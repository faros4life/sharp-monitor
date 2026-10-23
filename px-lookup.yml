#!/usr/bin/env python3
"""ProphetX tournament lookup (manual, read-only): baseball / college basketball / tennis names, IDs and live events.
Login + GET-style reads only; never places, changes or cancels orders. Keys are never printed."""
import json
import time
import urllib.error

import liquidity_monitor as lm

WORDS = ("mlb", "baseball", "world series", "postseason", "playoff", "ncaa", "college", "basketball", "ncaab",
         "atp", "wta", "tennis")


def main():
    if not (lm.PX_ACCESS and lm.PX_SECRET):
        raise SystemExit("Missing PROPHETX_ACCESS_KEY / PROPHETX_SECRET_KEY")
    d = lm.px_call("/auth/login", {"access_key": lm.PX_ACCESS, "secret_key": lm.PX_SECRET})
    lm._PXT["token"] = (d.get("data") or {}).get("access_token")
    tl = ((lm.px_call("/mm/get_tournaments").get("data") or {}).get("tournaments")) or []
    print(f"Tournaments listed: {len(tl)}. Fields: {sorted(tl[0].keys()) if tl else []}")
    hits = []
    for t in tl:
        blob = json.dumps(t).lower()
        if any(w in blob for w in WORDS):
            hits.append(t)
    print(f"Matching baseball / college basketball / tennis: {len(hits)}\n")
    for t in hits:
        extra = {k: v for k, v in t.items() if k not in ("id", "name") and not isinstance(v, (dict, list))}
        line = f"{t.get('id')!s:>8}  {t.get('name')!s:<45} {json.dumps(extra)[:120]}"
        try:
            evs = (lm.px_call(f"/mm/get_sport_events?tournament_id={t.get('id')}").get("data") or {}).get("sport_events") or []
            up = [e for e in evs if (e.get("status") or "not_started") == "not_started"]
            first = up[0] if up else (evs[0] if evs else {})
            line += f" | events {len(evs)} (upcoming {len(up)})" + (f" e.g. {first.get('name')} {first.get('scheduled')}" if first else "")
        except urllib.error.HTTPError as ex:
            line += f" | events: HTTP {ex.code}"
        except Exception as ex:
            line += f" | events: {str(ex)[:60]}"
        print(line)
        time.sleep(0.2)


if __name__ == "__main__":
    main()

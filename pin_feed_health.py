#!/usr/bin/env python3
"""PINNACLE FEED HEALTH for the NBA totals model (Nov 13, 2026; Peter).

READ-ONLY. Reads two files already on disk and prints. Makes no API call, spends no credit, needs
no secret, writes nothing, and cannot change a model result.

WHY IT EXISTS. nba_totals_model.pin_lines() takes Pinnacle totals from ONE place - the EV study's
pin_cache - and has no fallback. When that cache stopped updating, the model did not fail: it kept
posting games with pin_line = None, which its own code comments as "no Pinnacle reference at
posting: logged, never a sighting". A model producing zero sightings looked exactly like a model
with nothing to report. That is the failure this file makes impossible to miss.

It answers four questions, and the last one is the one that matters:
  how old is the cache, how many games does it cover, how many postings have no reference, and
  is the model still producing valid sightings at all.

Exit 1 when recent postings have lost their reference, so the run is visibly red rather than a
quiet success. It never gates, blocks or alters the model - the model has already finished by the
time this runs.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

EV = os.environ.get("EV_FILE", "") or "ev-study/ev_sightings.json"
MODEL = os.environ.get("NBA_MODEL_FILE", "") or "nba-model/nba_model.json"
# A posting dated from today onward is "live": it is the model's current output, and a missing
# reference there is a present-tense defect rather than history.
LOOK_BACK_DAYS = 7


def load(p):
    try:
        with open(p) as f:
            return json.load(f), None
    except Exception as ex:
        return None, f"{type(ex).__name__}: {str(ex)[:80]}"


def parse(s):
    """ISO or epoch seconds. The cache stores its timestamps as epoch STRINGS ('1794532069.99'),
    not ISO, so an ISO-only reader reports 'no timestamps in the cache' and the age check - the
    whole point of this file - silently never runs."""
    if s in (None, ""):
        return None
    try:
        v = float(s)
        if v > 1e9:                       # epoch seconds, not a year or a line number
            return datetime.fromtimestamp(v, tz=timezone.utc)
    except (TypeError, ValueError):
        pass
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s)[:19 if "T" in f else 10], f).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def main():
    now = datetime.now(timezone.utc)
    print("PINNACLE FEED HEALTH (read-only; no API calls, no credits)")
    print("=" * 88)
    bad = []

    ev, err = load(EV)
    if err:
        print(f"  pin_cache     UNREADABLE: {err}")
        bad.append("pin_cache unreadable")
    else:
        cache = (ev or {}).get("pin_cache") or {}
        stamps = []
        for v in cache.values():
            t = parse(((v or {}).get("totals") or {}).get("fetched") or
                      ((v or {}).get("totals") or {}).get("upd"))
            if t:
                stamps.append(t)
        newest = max(stamps) if stamps else None
        age_h = (now - newest).total_seconds() / 3600 if newest else None
        print(f"  pin_cache     {len(cache)} game(s)")
        if newest:
            print(f"  newest entry  {newest:%Y-%m-%d %H:%M}Z  (age {age_h:.1f} h)")
            if age_h > 12:
                print(f"                STALE - nothing new in {age_h:.1f} h; the writer is not running")
                bad.append(f"cache stale {age_h:.0f}h")
        else:
            print("  newest entry  unknown (no timestamps in the cache)")

    md, err = load(MODEL)
    if err:
        print(f"  nba_model     UNREADABLE: {err}")
        bad.append("model output unreadable")
        print("=" * 88)
        sys.exit(1)

    games = md.get("games") or []
    games = list(games.values()) if isinstance(games, dict) else games
    cut = (now - timedelta(days=LOOK_BACK_DAYS)).date()
    rows = {}
    for g in games:
        if not isinstance(g, dict):
            continue
        p = g.get("post") or {}
        d = parse(p.get("utc") or g.get("start"))
        if not d or d.date() < cut:
            continue
        k = d.date().isoformat()
        r = rows.setdefault(k, [0, 0, 0])
        r[0] += 1
        if p.get("pin_line") is not None:
            r[1] += 1
        if p.get("sighting"):
            r[2] += 1

    print(f"  model updated {md.get('updated_utc')}")
    print()
    print("  posted date   postings   with reference   missing   sightings")
    live_missing = live_total = 0
    today = now.date()
    for k in sorted(rows):
        n, w, s = rows[k]
        miss = n - w
        flag = ""
        if datetime.strptime(k, "%Y-%m-%d").date() >= today and miss:
            flag = "   <- LIVE, NO REFERENCE"
            live_missing += miss
            live_total += n
        print(f"    {k}     {n:>6}   {w:>14}   {miss:>7}   {s:>9}{flag}")

    print()
    if live_missing:
        print(f"  {live_missing} of {live_total} posting(s) dated today or later have NO Pinnacle reference.")
        print("  Those can never become sightings. The model is running and producing nothing usable,")
        print("  which is why this check exists rather than reading the run as a success.")
        bad.append(f"{live_missing} live postings with no reference")
    else:
        print("  Every posting dated today or later carries a Pinnacle reference.")

    print("=" * 88)
    if bad:
        print("FEED UNHEALTHY: " + "; ".join(bad))
        sys.exit(1)
    print("Feed healthy.")


if __name__ == "__main__":
    main()

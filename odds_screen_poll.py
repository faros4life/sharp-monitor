"""Nov 5 (Peter: "we need to make it faster updates"): fast refresh for the odds screen only.

Runs as a step of each sharp-monitor run (every ~5 min). At most once per 10 minutes, 9 AM-midnight ET, it pulls
Peter's books + Pinnacle for each sport on the screen and rewrites odds_screen.json. A sport the monitor polled in the
last 9 minutes is skipped (already fresh). Cost: 1 credit per market per sport (books <= 10). No alerts, no state.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import odds_screen
import sharp_monitor as sm

_M = (os.environ.get("ODDS_SCREEN_MIN", "") or "off").strip().lower()   # Nov 5: off by default (Refresh button on the page);
EVERY_S = None if _M in ("off", "0", "none") else float(_M) * 60     # set GitHub variable ODDS_SCREEN_MIN to 10 or 5 to turn on
FRESH_S = (EVERY_S or 0) - 60


def main():
    if EVERY_S is None:
        return print("odds screen poll: off (page Refresh button only)")
    n = datetime.now(timezone.utc)
    if not 9 <= n.astimezone(sm.ET).hour <= 23:
        return print("odds screen poll: outside 9 AM-midnight ET")
    try:
        old = json.load(open(odds_screen.FILE))
    except Exception:
        return print("odds screen poll: no screen file yet (the monitor writes the first one)")
    now = time.time()
    if now - old.get("fast_poll", 0) < EVERY_S - 30:
        return print("odds screen poll: not due")
    t25 = {g["id"]: g.get("t25", []) for g in old.get("games", [])}
    by_label = {cfg["label"]: key for key, cfg in sm.SPORTS.items()}
    books = ",".join(dict.fromkeys(sm.RETAIL + [sm.SHARP]))
    spent, polled, rem = 0, [], None
    for lg, last in old.get("sports", {}).items():
        key = by_label.get(lg)
        if not key or (sm.ONLY and key not in sm.ONLY) or now - last < FRESH_S:
            continue
        cfg = sm.SPORTS[key]
        try:
            events, rem = sm.http_get(f"/sports/{key}/odds", {
                "bookmakers": books, "markets": ",".join(cfg["markets"]), "oddsFormat": "american",
                "includeLinks": "true", "commenceTimeFrom": sm.iso(n),
                "commenceTimeTo": sm.iso(n + timedelta(hours=sm.LOOKAHEAD_H))})
        except Exception as x:
            print(f"odds screen poll: {lg} failed ({str(x)[:60]})")
            continue
        spent += len(cfg["markets"])
        polled.append(lg)
        for ev in events:
            ev["commence_time"] = sm.listed_start(cfg["label"], ev["commence_time"])
            odds_screen.add(lg, ev, sm.book_lines(ev), [tuple(x) for x in t25.get(ev["id"], [])], sm.RETAIL, sm.SHARP)
    odds_screen.save(sm.RETAIL, sm.SHARP, sm.NAMES, rem)
    d = json.load(open(odds_screen.FILE))
    d["fast_poll"] = round(now)
    with open(odds_screen.FILE, "w") as f:
        json.dump(d, f, separators=(",", ":"))
    print(f"odds screen poll: {polled or 'nothing due'}; ~{spent} credits; remaining {rem}")


WEEK_EVERY_S = 2 * 3600   # Nov 9: NFL + CFB through the next 7 days, every 2h (9 AM-midnight ET), ~4 credits a pull


def week():
    n = datetime.now(timezone.utc)
    if not 9 <= n.astimezone(sm.ET).hour <= 23:
        return print("odds screen week pull: outside 9 AM-midnight ET")
    try:
        old = json.load(open(odds_screen.FILE))
    except Exception:
        return print("odds screen week pull: no screen file yet")
    if time.time() - old.get("week_poll", 0) < WEEK_EVERY_S - 60:
        return print("odds screen week pull: not due")
    t25 = {g["id"]: g.get("t25", []) for g in old.get("games", [])}
    books = ",".join(dict.fromkeys(sm.RETAIL + [sm.SHARP]))
    rem, spent = None, 0
    for key in ("americanfootball_nfl", "americanfootball_ncaaf"):
        cfg = sm.SPORTS.get(key)
        if not cfg:
            continue
        try:
            events, rem = sm.http_get(f"/sports/{key}/odds", {
                "bookmakers": books, "markets": ",".join(cfg["markets"]), "oddsFormat": "american",
                "includeLinks": "true", "commenceTimeFrom": sm.iso(n), "commenceTimeTo": sm.iso(n + timedelta(days=7))})
        except Exception as x:
            print(f"odds screen week pull: {cfg['label']} failed ({str(x)[:60]})")
            continue
        spent += len(cfg["markets"])
        for ev in events:
            ev["commence_time"] = sm.listed_start(cfg["label"], ev["commence_time"])
            odds_screen.add(cfg["label"], ev, sm.book_lines(ev), [tuple(x) for x in t25.get(ev["id"], [])], sm.RETAIL, sm.SHARP)
    odds_screen.save(sm.RETAIL, sm.SHARP, sm.NAMES, rem)
    d = json.load(open(odds_screen.FILE))
    d["week_poll"] = round(time.time())
    with open(odds_screen.FILE, "w") as f:
        json.dump(d, f, separators=(",", ":"))
    print(f"odds screen week pull: ~{spent} credits; remaining {rem}")


if __name__ == "__main__":
    main()
    week()

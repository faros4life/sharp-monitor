#!/usr/bin/env python3
"""
HARD ROCK EV SCANNER - the SLOW-HR-EV forward paper lane (Peter yes Nov 4 7:12 AM; Muse terms Nov 4 7:19 AM).
Runs inside every sharp-monitor poll, on the lines that poll already fetched (0 extra credits).

Sighting: NBA / NFL / NCAAF spread or total where Hard Rock's price is >= +2% EV against Pinnacle's no-vig fair AT THE
SAME LINE (both sides of Pinnacle's market at that number). Everything is logged; nothing is ever placed.
- Recheck: the first poll >= 5 min after the sighting records whether Hard Rock still has that line at that price or
  better. Hard Rock's max bet is not in the odds feed, so it is logged as unknown (Muse amendment b: needs a source).
- Flag (Peter Nov 4 7:45 AM "those come to ntfy"): one ntfy MANUAL-BET ping on the first sighting of a bet.
  NCAAF flags only for Top-25 games (Muse amendment a: log everything, flag selectively). No flags inside T-30.
  HRSCAN_FLAG=off silences the pings; the log keeps running.
- Graded later at Pinnacle's true close, forward only (from registered_utc). Checkpoint 50, judged at 100.
hrscan.json is public like alerts.json: game, market, side, line, prices, EV, times. No stakes, no amounts.
"""
import json
import os

FILE = "hrscan.json"
MIN_EV = float(os.environ.get("HRSCAN_MIN_EV", "") or "2.0")
FLAG = (os.environ.get("HRSCAN_FLAG") or "on").strip().lower() == "on"
HR_BOOKS = ("hardrockbet_fl", "hardrockbet")
LEAGUES = ("NBA", "NFL", "NCAAF")
NO_FLAG_MIN = 30          # inside the final 30 minutes: logged, not flagged
RECHECK_S = 300
KEEP_DAYS = 30


def _p(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def _dec(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / -a)


def load():
    try:
        d = json.load(open(FILE))
        d.setdefault("sightings", [])
        return d
    except Exception:
        return {"registered_utc": None, "min_ev_pct": MIN_EV, "sightings": []}


def save(d, now_ts):
    d["sightings"] = [s for s in d["sightings"] if s["t"] > now_ts - KEEP_DAYS * 86400]
    json.dump(d, open(FILE, "w"), indent=1)


def _fmt(a):
    a = round(a)
    return f"+{a}" if a > 0 else str(a)


def scan(sm, ev, cfg, lines, is_t25, d, now):
    """Log / recheck / flag Hard Rock EV sightings for one event. Returns the number of flags sent."""
    label = cfg.get("label")
    if label not in LEAGUES:
        return 0
    pin = lines.get(sm.SHARP) or {}
    hrk = next((b for b in HR_BOOKS if b in lines), None)
    if not hrk or not pin:
        return 0
    start = sm.parse_iso(ev["commence_time"])
    lead = (start - now).total_seconds() / 60
    if lead <= 0:
        return 0
    if not d.get("registered_utc"):
        d["registered_utc"] = sm.iso(now)
    ts = now.timestamp()
    game = f"{ev['away_team']} @ {ev['home_team']}"
    flags = 0
    for mk in ("spreads", "totals"):
        P = pin.get(mk) or {}
        H = lines[hrk].get(mk) or {}
        if len(P) != 2:
            continue
        for side, (hpt, hpr) in H.items():
            if side not in P:
                continue
            ppt, ppr = P[side]
            other = next(s for s in P if s != side)
            opt, opr = P[other]
            if ppt != hpt or opt != (ppt if mk == "totals" else -ppt):
                continue
            q, r = _p(ppr), _p(opr)
            fair = q / (q + r)
            evp = 100 * (fair * _dec(hpr) - 1)
            key = f"{ev['id']}|{mk}|{side}|{hpt:g}"
            mine = [s for s in d["sightings"] if s["key"] == key]
            for s in mine:   # +5 min recheck: is the price still there?
                if s.get("recheck") is None and ts - s["t"] >= RECHECK_S:
                    s["recheck"] = {"utc": sm.iso(now), "hr": hpr, "still_there": float(hpr) >= float(s["hr"]),
                                    "evp": round(evp, 2), "max_bet": None}
            if evp < MIN_EV:
                continue
            if mine and float(mine[-1]["hr"]) == float(hpr):
                continue   # same price still standing: one sighting, not one per poll
            s = {"key": key, "ev": ev["id"], "lg": label, "game": game, "start": ev["commence_time"], "mk": mk,
                 "side": side, "pt": hpt, "book": hrk, "hr": hpr, "pin": ppr, "pin_other": opr,
                 "fair_am": round(sm.prob_to_am(fair)), "evp": round(evp, 2), "t": ts, "utc": sm.iso(now),
                 "lead": round(lead), "t25": is_t25, "recheck": None, "flag": False,
                 "repeat": bool(mine)}
            want = (not mine) and lead >= NO_FLAG_MIN and (label != "NCAAF" or is_t25 is True)
            if FLAG and want:
                bet = (f"{side} {hpt:g}" if mk == "totals" else f"{side} {hpt:+g}") + f" ({_fmt(hpr)})"
                try:
                    sm.notify(f"HR EDGE {label} {evp:+.1f}% - MANUAL BET",
                              f"HARD ROCK EDGE {evp:+.1f}% vs Pinnacle fair - MANUAL BET\n{bet} at Hard Rock\n"
                              f"Pinnacle {ppt:g}: {_fmt(ppr)} / {_fmt(opr)} -> fair {_fmt(sm.prob_to_am(fair))}\n"
                              f"{game}, starts in {sm.lead_text(lead)}\n"
                              "Bet only if this price is still there; check the max bet it allows. Paper lane - your call.",
                              extra_tags=("mag",), headline=f"{game} — {bet} @ Hard Rock")
                    s["flag"] = True
                    flags += 1
                except Exception as x:
                    print(f"hr scanner flag failed: {str(x)[:60]}")
            d["sightings"].append(s)
    return flags

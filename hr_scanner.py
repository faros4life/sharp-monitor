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
- One ping per bet (Peter Nov 4 9:09 "fix double ping"): the scanner and the alert-based HR MISPRICE ping share one
  'pinged' list, so whichever fires first is the only ping for that game / market / side.
- Max bet (Peter Nov 4 9:09 "you can tell me max bet"): Peter sends "max 500" on his ntfy topic after checking a flag;
  it is attached to his most recent flag. Dollar figures stay in the PRIVATE state (Actions cache), never in this public
  file - here only a size bucket (S < 100, M 100-499, L 500+).
- Auto grade (Peter Nov 4 9:09): every poll keeps the newest Pinnacle read for each open sighting (the last one before
  start = the close, 0 credits); 3 h after start the final score comes from ESPN. Units first: 1u flat at the Hard Rock
  price. CLV vs Pinnacle's no-vig close when Pinnacle closed on the same number. Forward only, checkpoint 50, judged 100.
hrscan.json is public like alerts.json: game, market, side, line, prices, EV, times, results. No stakes, no amounts.
"""
import json
import os
import re
import urllib.request
from datetime import timedelta

FILE = "hrscan.json"
MIN_EV = float(os.environ.get("HRSCAN_MIN_EV", "") or "2.0")
FLAG = (os.environ.get("HRSCAN_FLAG") or "on").strip().lower() == "on"
HR_BOOKS = ("hardrockbet_fl", "hardrockbet")
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL", "NCAAB", "MLB")   # Nov 4 12:29 (Peter): all six paid sports, 0 extra credits
FLAG_LEAGUES = ("NBA", "NFL", "NCAAF")   # Peter "no push to me": NHL / NCAAB / MLB are logged and graded, never pinged
NO_FLAG_MIN = 30          # inside the final 30 minutes: logged, not flagged
RECHECK_S = 300
KEEP_DAYS = 30


def _p(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def _dec(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / -a)


def _dg(d, k, n=1):
    """Nov 5 (Peter: scanner has shown 0 sightings since it registered 13:55 UTC Nov 4): the scanner had exactly one
    print statement, so a hard zero was indistinguishable from a dead feed. These counters record WHERE each candidate
    dies, every poll. Counts only - this file is public, and no counter is an alert."""
    g = d.setdefault("diag", {})
    g[k] = g.get(k, 0) + n


def load():
    try:
        d = json.load(open(FILE))
        d.setdefault("sightings", [])
        return d
    except Exception:
        return {"registered_utc": None, "min_ev_pct": MIN_EV, "sightings": []}


def save(d, now_ts):
    d["sightings"] = [s for s in d["sightings"] if s["t"] > now_ts - KEEP_DAYS * 86400]
    d["pinged"] = {k: t for k, t in (d.get("pinged") or {}).items() if t > now_ts - 3 * 86400}
    json.dump(d, open(FILE, "w"), indent=1)


def _fmt(a):
    a = round(a)
    return f"+{a}" if a > 0 else str(a)


def pinged(d, k):
    return k in (d.get("pinged") or {})


def mark(d, k, ts=None):
    import time
    d.setdefault("pinged", {})[k] = ts or time.time()


def _bucket(v):
    return "S" if v < 100 else ("M" if v < 500 else "L")


def attach_max(d, priv, topic):
    """Read 'max <n>' messages from Peter's ntfy topic (last 12 h) and attach each to the newest flag sent before it."""
    if not topic:
        return 0
    try:
        with urllib.request.urlopen(f"https://ntfy.sh/{topic}/json?poll=1&since=12h", timeout=15) as r:
            msgs = r.read().decode().splitlines()
    except Exception:
        return 0
    seen = priv.setdefault("max_msgs", [])
    got = 0
    for ln in msgs:
        try:
            m = json.loads(ln)
        except Exception:
            continue
        x = re.match(r"^\s*max\s*\$?\s*([\d,]+(?:\.\d+)?)\s*$", m.get("message") or "", re.I)
        if not x or m.get("id") in seen:
            continue
        seen.append(m.get("id"))
        v = float(x.group(1).replace(",", ""))
        fl = [s for s in d["sightings"] if s.get("flag") and s["t"] <= (m.get("time") or 0)]
        if not fl:
            continue
        s = max(fl, key=lambda z: z["t"])
        priv.setdefault("max_bet", {})[s["key"] + "|" + str(s["t"])] = v
        s["max_bet_bucket"] = _bucket(v)
        got += 1
    del seen[:-200]
    return got


def grade(sm, d, now):
    """Final score (ESPN) -> W/L/P and units for sightings whose game started 3+ h ago; CLV from the stored close."""
    n = 0
    for s in d["sightings"]:
        if s.get("res") or sm.parse_iso(s["start"]) > now - timedelta(hours=3):
            continue
        e = {"game": s["game"], "start": s["start"], "sport": s["lg"], "kind": "tot" if s["mk"] == "totals" else "spr",
             "side": s["side"], "pt": s["pt"]}
        try:
            g = sm.find_game(e)
            r = sm.settle(e, g) if g else None
        except Exception:
            r = None
        if not r:
            if sm.parse_iso(s["start"]) < now - timedelta(days=4):
                s["res"] = {"r": "NG", "why": "no final found"}   # not graded; counted, never dropped
            continue
        dec = _dec(s["hr"])
        u = (dec - 1) if r[0] == "W" else (-1.0 if r[0] == "L" else 0.0)
        s["res"] = {"r": r[0], "score": r[1], "u": round(u, 3)}
        c = s.get("close")
        if c and c.get("pt") == s["pt"]:
            q, o = _p(c["pr"]), _p(c["other"])
            fair = q / (q + o)
            s["res"]["clv"] = round(100 * (fair * dec - 1), 2)
            s["res"]["close_fair_am"] = round(sm.prob_to_am(fair))
        elif c:
            s["res"]["close_line"] = c.get("pt")   # Pinnacle closed on another number: units only, no CLV
        n += 1
    return n


def summary(d):
    def line(xs):
        g = [s for s in xs if (s.get("res") or {}).get("r") in ("W", "L", "P")]
        w = sum(1 for s in g if s["res"]["r"] == "W")
        l_ = sum(1 for s in g if s["res"]["r"] == "L")
        u = sum(s["res"]["u"] for s in g)
        c = [s["res"]["clv"] for s in g if s["res"].get("clv") is not None]
        return {"n": len(g), "w": w, "l": l_, "units": round(u, 2), "roi_pct": round(100 * u / len(g), 1) if g else None,
                "clv_n": len(c), "clv_avg": round(sum(c) / len(c), 2) if c else None,
                "beat": sum(1 for x in c if x > 0)}
    first = [s for s in d["sightings"] if not s.get("repeat")]
    out = {"all": line(first), "flagged": line([s for s in first if s.get("flag")])}
    for lg in LEAGUES:
        out[lg] = line([s for s in first if s["lg"] == lg])
    for b in ("S", "M", "L"):
        out["max_bet_" + b] = line([s for s in first if s.get("max_bet_bucket") == b])
    d["summary"] = out
    return out


def scan(sm, ev, cfg, lines, is_t25, d, now):
    """Log / recheck / flag Hard Rock EV sightings for one event. Returns the number of flags sent."""
    label = cfg.get("label")
    if label not in LEAGUES:
        return 0
    pin = lines.get(sm.SHARP) or {}
    hrk = next((b for b in HR_BOOKS if b in lines), None)
    d.setdefault("diag", {}).setdefault("diag_since_utc", sm.iso(now))
    _dg(d, "events seen")
    if not hrk or not pin:
        _dg(d, "no Hard Rock book in the poll lines" if not hrk else "no Pinnacle lines")
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
    for s in d["sightings"]:   # keep the newest Pinnacle read for this bet: the last one before start is the close
        if s["ev"] == ev["id"] and not s.get("res"):
            P = pin.get(s["mk"]) or {}
            if s["side"] in P and len(P) == 2:
                o = next(x for x in P if x != s["side"])
                s["close"] = {"pt": P[s["side"]][0], "pr": P[s["side"]][1], "other": P[o][1], "lead": round(lead)}
    for mk in ("spreads", "totals"):
        P = pin.get(mk) or {}
        H = lines[hrk].get(mk) or {}
        if len(P) != 2:
            _dg(d, f"{mk}: Pinnacle not two-sided")
            continue
        if not H:
            _dg(d, f"{mk}: no Hard Rock line")
            continue
        for side, (hpt, hpr) in H.items():
            if side not in P:
                _dg(d, f"{mk}: side not at Pinnacle")
                continue
            ppt, ppr = P[side]
            other = next(s for s in P if s != side)
            opt, opr = P[other]
            _dg(d, f"{mk}: both books have this side")
            if ppt != hpt or opt != (ppt if mk == "totals" else -ppt):
                _dg(d, f"{mk}: line mismatch, HR vs Pinnacle")
                continue
            _dg(d, f"{mk}: same line at both")
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
                _dg(d, f"{mk}: same line but EV under {MIN_EV:g}%")
                continue
            _dg(d, f"{mk}: SIGHTING")
            if mine and float(mine[-1]["hr"]) == float(hpr):
                continue   # same price still standing: one sighting, not one per poll
            s = {"key": key, "ev": ev["id"], "lg": label, "game": game, "start": ev["commence_time"], "mk": mk,
                 "side": side, "pt": hpt, "book": hrk, "hr": hpr, "pin": ppr, "pin_other": opr,
                 "fair_am": round(sm.prob_to_am(fair)), "evp": round(evp, 2), "t": ts, "utc": sm.iso(now),
                 "lead": round(lead), "t25": is_t25, "recheck": None, "flag": False,
                 "repeat": bool(mine)}
            pk = f"{ev['id']}|{mk}|{side}"
            want = ((not mine) and label in FLAG_LEAGUES and lead >= NO_FLAG_MIN and (label != "NCAAF" or is_t25 is True)
                    and not pinged(d, pk))
            if FLAG and want:
                mark(d, pk, ts)
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

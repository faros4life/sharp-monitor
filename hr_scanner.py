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
import hashlib
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
# Nov 5 ~6:54 AM (Peter, reversing the earlier restriction): "don't limit the pushes, let's see how many I get and
# adjust. Show me all HR lag." All six sports flag on both paths; the NCAAF Top-25 ping gate is lifted FOR HR FLAGS
# ONLY (ntfy rules elsewhere unchanged). Volume is COUNTED by league x conversion bucket instead of being gated, so
# any later adjustment is made on real numbers. NCAAB maxes at Hard Rock are small - noted in reporting, not gated.
# Nov 9 (Peter, 10:18 AM: "IM LIMITED CBB" / "UNLESS TOP 25"): college basketball pings only for Top-25 games.
# NCAAB stays in this list because the non-Top-25 notification gate below already does that job - it suppresses
# the push on an ESTABLISHED non-Top-25 college game while still logging, counting and grading the sighting,
# and it fails open when the AP poll cannot be read. Same gate NCAAF uses, one definition for both.
# NBA is out entirely (Peter, 10:19 AM: "NBA LIMITED ALSO") - he is limited at Hard Rock there and a push he
# cannot act on is noise. NBA sightings are still LOGGED, counted and graded exactly as before.
# Nov 9 10:21 (Peter: "IM LIMITED ALL CBB HR") - ALL college basketball is out, Top 25 included; the earlier
# "unless Top 25" line applies to NCAAF football, which keeps its gate below. NBA is out too (10:19, limited).
FLAG_LEAGUES = ("NFL", "NCAAF", "NHL", "MLB")
NO_FLAG_MIN = 30          # inside the final 30 minutes: logged, not flagged
RECHECK_S = 300
KEEP_DAYS = 30
DISTINCT_DAYS = 2   # Nov 5 (Peter, option 2): rolling retention for the seen-key SETS. The distinct COUNTS keep
                    # the full KEEP_DAYS window; only the hash sets that answer "already counted today?" are pruned.


def _p(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def _dec(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / -a)


def _uid(ev_id, mk, side):
    """Short stable id for one game x market x side. Hashed so the committed diagnostic file stays small; the
    distinct COUNTS are what gets reported, the hash set only answers 'already counted this one today?'."""
    return hashlib.sha1(f"{ev_id}|{mk}|{side}".encode()).hexdigest()[:10]


def _dd(d, day, lg, mk, cat, uid):
    """Count one game x market x side ONCE per day per category, per league and market. Opposite sides are
    different uids, so they count separately. PROSPECTIVE ONLY - no distinct count is ever inferred from
    aggregate polling totals; a day that predates this code simply has no distinct figures."""
    if not uid:
        return
    seen = d.setdefault("seen", {}).setdefault(day, {}).setdefault(cat, {})
    if uid in seen:
        return
    seen[uid] = 1
    dd = d.setdefault("distinct", {}).setdefault(day, {})
    k = f"{lg or '?'} {mk}: {cat}"
    dd[k] = dd.get(k, 0) + 1


def _convb(conv):
    """Conversion-distance bucket for push-volume reporting (Peter Nov 5: count it, do not gate on it).
    NAMED _convb, not _bucket: the pre-existing _bucket(v) below is the max-bet S/M/L sizer and, being defined
    later in the module, shadowed this one - which labelled every push S/M/L and raised TypeError on conv None
    (None < 100), i.e. it would have crashed the poll on the first run/puck-line push."""
    if conv is None:
        return "none (no line to convert)"
    try:
        c = float(conv)
    except Exception:
        return "unknown"
    return ("0" if c <= 0 else ">0-0.5" if c <= 0.5 else ">0.5-1.0" if c <= 1.0
            else ">1.0-2.0" if c <= 2.0 else ">2.0")


def count_push(d, lg, conv, now, src="alert", mk=None, ev=None, side=None):
    """Record one FIRED push, by UTC day x league x conversion bucket x source, raw AND distinct. Counts only."""
    day = now.strftime("%Y-%m-%d")
    g = d.setdefault("pushes", {}).setdefault(day, {}).setdefault(lg or "?", {})
    k = f"{_convb(conv)} [{src}]"
    g[k] = g.get(k, 0) + 1
    _dg(d, f"{lg or '?'} PUSH SENT [{src}] conv {_convb(conv)}", day=day)
    if mk and ev is not None:
        _dd(d, day, lg, mk, f"PUSH SENT [{src}]", _uid(ev, mk, side))


def _dg(d, k, n=1, day=None):
    """Nov 5 (Peter: scanner has shown 0 sightings since it registered 13:55 UTC Nov 4): the scanner had exactly one
    print statement, so a hard zero was indistinguishable from a dead feed. These counters record WHERE each candidate
    dies, every poll. Counts only - this file is public, and no counter is an alert."""
    g = d.setdefault("diag", {})
    g[k] = g.get(k, 0) + n
    if day:   # Nov 5 (Peter): the same counter, also kept per UTC day so volume is readable day by day
        dd = d.setdefault("daily", {}).setdefault(day, {})
        dd[k] = dd.get(k, 0) + n


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
    if d.get("daily"):   # keep the per-day counters to the same window as the sightings
        keep = sorted(d["daily"])[-KEEP_DAYS:]
        d["daily"] = {k: v for k, v in d["daily"].items() if k in keep}
    if d.get("distinct"):
        keep = sorted(d["distinct"])[-KEEP_DAYS:]
        d["distinct"] = {k: v for k, v in d["distinct"].items() if k in keep}
    if d.get("seen"):    # the hash SETS are bounded to 2 days; the counts above outlive them
        keep = sorted(d["seen"])[-DISTINCT_DAYS:]
        d["seen"] = {k: v for k, v in d["seen"].items() if k in keep}
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
    _day = now.strftime("%Y-%m-%d")

    def dd(mk_, side_, cat):
        """Distinct (game x market x side) counter for this event, league-aware."""
        _dd(d, _day, label, mk_, cat, _uid(ev.get("id"), mk_, side_))

    def dg(k, n=1):
        """Nov 5 (Peter): every scanner counter is split BY LEAGUE and kept per day. Spreads and totals stay
        separate because the key carries the market. Counts only; this file is public."""
        _dg(d, f"{label} {k}", n, day=_day)
    dg("events seen")
    if not hrk or not pin:
        dg("no Hard Rock book in the poll lines" if not hrk else "no Pinnacle lines")
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
            dg(f"{mk}: Pinnacle not two-sided")
            continue
        if not H:
            dg(f"{mk}: no Hard Rock line")
            continue
        for side, (hpt, hpr) in H.items():
            if side not in P:
                dg(f"{mk}: side not at Pinnacle")
                continue
            ppt, ppr = P[side]
            other = next(s for s in P if s != side)
            opt, opr = P[other]
            dg(f"{mk}: sides compared")
            dd(mk, side, "sides compared")
            if ppt != hpt or opt != (ppt if mk == "totals" else -ppt):
                dg(f"{mk}: line mismatch, HR vs Pinnacle")
                dd(mk, side, "mismatched line")
                # Nov 5: how FAR apart. A standing mismatch is only a Type L CANDIDATE (SLOW-HR Type L also needs a
                # Pinnacle move >= 0.5 inside the window plus persistence, which this scanner does not track), so these
                # are an upper bound on Type L flow, not Type L sightings. Half-point gaps are the bettable shape.
                try:
                    gap = abs(float(hpt) - float(ppt))
                    dg(f"{mk}: gap " + ("0.5" if gap <= 0.5 else "1.0" if gap <= 1.0 else
                                            "1.5-2" if gap <= 2.0 else "2.5-3" if gap <= 3.0 else "over 3"))
                except Exception:
                    pass
                continue
            dg(f"{mk}: same line at both")
            dd(mk, side, "same line")
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
                dg(f"{mk}: same line but EV under {MIN_EV:g}%")
                # Nov 5: HOW far under. Is the bar slightly wrong (HR landing at 1.9%) or is Hard Rock simply worse
                # than Pinnacle at the same number (negative EV), in which case no threshold rescues this test.
                dg(f"{mk}: EV band " + ("1 to 2%" if evp >= 1 else "0 to 1%" if evp >= 0 else
                                            "-2 to 0%" if evp >= -2 else "-5 to -2%" if evp >= -5 else "under -5%"))
                continue
            dg(f"{mk}: SIGHTING")
            dd(mk, side, "EV >= 2%")
            if mine and float(mine[-1]["hr"]) == float(hpr):
                continue   # same price still standing: one sighting, not one per poll
            s = {"key": key, "ev": ev["id"], "lg": label, "game": game, "start": ev["commence_time"], "mk": mk,
                 "side": side, "pt": hpt, "book": hrk, "hr": hpr, "pin": ppr, "pin_other": opr,
                 "fair_am": round(sm.prob_to_am(fair)), "evp": round(evp, 2), "t": ts, "utc": sm.iso(now),
                 "lead": round(lead), "t25": is_t25, "recheck": None, "flag": False,
                 "repeat": bool(mine)}
            pk = f"{ev['id']}|{mk}|{side}"
            # Nov 5 (Peter, later): NOTIFICATION-ONLY gate on non-Top-25 Hard Rock flags, superseding
            # the earlier "no Top-25 gate on HR flags". The PUSH is suppressed; the sighting is still
            # logged, counted and graded with full labels, the same way the suppressed NBA half-point
            # conversions are kept. is_t25 is None for non-college leagues and True when the poll
            # could not read the AP poll (top25_tag fails open), so only an ESTABLISHED non-Top-25
            # game is gated - an unreadable poll never silences a flag.
            # The alert path needs no equivalent: its Top-25 arm already consumes non-Top-25 alerts
            # before hr_ev is reached, so that path has never pinged a non-Top-25 college game.
            # The alert path ALSO blocks Hard Rock
            # spread underdogs via sm.hr_dog (Peter Nov 3: "8-19, -11.9u, lost every week"), and
            # this path never checked, so Wake Forest +18.5 at +100 pinged at 17:55Z on Nov 5.
            # One rule, both paths - called through sm so there is only ever one definition of it.
            # Totals are untouched: hr_dog tests only spr/rl, so a total's positive number cannot
            # be mistaken for an underdog.
            want = ((not mine) and label in FLAG_LEAGUES and lead >= NO_FLAG_MIN
                    and not pinged(d, pk)
                    and not sm.hr_dog({"book": hrk, "kind": "spr" if mk == "spreads" else "tot",
                                       "pt": hpt}))
            t25_gated = bool(want and is_t25 is False)
            if t25_gated:
                want = False
                # Nov 5: set when the push was suppressed by the non-Top-25 gate. The row is graded
                # and counted exactly as a flagged one; only the notification differs. Assigned here
                # rather than in the dict literal above, which is built before this gate is known.
                s["gated"] = "non-Top-25 (notification-only gate, Peter Nov 5)"
                dg(f"{mk}: flag GATED - non-Top-25 (notification only, Peter Nov 5)")
                dd(mk, side, "FLAG GATED non-Top-25")
                count_push(d, label, 0.0, now, "scanner-gated-non-top25",
                           mk=mk, ev=ev.get("id"), side=side)
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
                    # the scanner is same-line by construction: conv 0. Nov 5 (Peter): pass the identifiers too,
                    # or a scanner push raises the RAW total and can never raise the DISTINCT one.
                    count_push(d, label, 0.0, now, "scanner", mk=mk, ev=ev.get("id"), side=side)
                except Exception as x:
                    print(f"hr scanner flag failed: {str(x)[:60]}")
            d["sightings"].append(s)
    return flags

#!/usr/bin/env python3
"""FORWARD PAPER CANDIDATE (Peter, 10 Nov 2026): NBA own-number model, REG, T-6h post, priced at NOVIG.
PAPER ONLY. Reads Novig's PUBLIC unsigned catalog (free; no key, no OddsPapi, no order, no account). Never alerts, never bets.
Used by nba_totals_model.py inside try/except, so a failure here can never affect the registered model record.

Per sighting (|number - Pinnacle total| >= 3.0, unchanged) it logs, at post time: Novig's price for that side AT THAT LINE
(taker price = 1 - best opposing bid), the size at the best level and the dollars within 5c, and the quote time.
At the close: verified CLV = Pinnacle no-vig close at the SAME line x Novig decimal - 1 (Novig pre-game fee 0).
EXCLUDED, never modelled or estimated: no Novig quote at that line, no Pinnacle close, close line != sighting line,
close read more than 60 min before tip.
Registered bar for the candidate (house bar, unchanged): >= 100 QUALIFYING UNIQUE GAMES, CLV > 0 and beat-close >= 53%,
in BOTH halves (FIT = first half of qualifying games in start order, CHECK = second half). No retesting of history."""
import json
import os
import smtplib
import statistics as st
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

NOVIG = os.environ.get("NOVIG_API", "") or "https://api.novig.com"
FRESH_CLOSE_MIN = 60
BAR_N = 100
_cache = {"t": 0, "ev": None, "mk": None}


def _get(path, params=None):
    url = NOVIG + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": "nba-forward-paper/1.0", "Accept": "application/json"})
    for i in range(3):          # the live probe saw an isolated HTTP error on a book read: retry 429/5xx, then give up (-> excluded)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if i == 2 or e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(2 * (i + 1))


def _paged(path, params):
    out, after = [], None
    for _ in range(10):
        d = _get(path, dict(params, **({"after": after} if after else {})))
        out += d.get("items") or []
        after = d.get("next")
        if not after:
            break
    return out


def _catalog(now):
    """One events + markets read per run, shared by every game that run (two calls, not per game)."""
    if _cache["ev"] is not None and _cache["t"] == now.strftime("%Y%m%d%H%M"):
        return _cache["ev"], _cache["mk"]
    lo = int(now.timestamp() * 1000)
    hi = int((now + timedelta(hours=36)).timestamp() * 1000)
    p = {"startsAfter": lo, "startsBefore": hi, "limit": 5000}
    ev = [e for e in _paged("/v3/public/catalog/events", p) if (e.get("league") or "").upper().strip() == "NBA"]
    ids = {e["eventId"] for e in ev}
    mk = [m for m in _paged("/v3/public/catalog/markets", p) if m.get("eventId") in ids]
    _cache.update({"t": now.strftime("%Y%m%d%H%M"), "ev": ev, "mk": mk})
    return ev, mk


def _words(team):
    return {w for w in str(team).lower().replace(".", "").split() if len(w) > 2}


def novig_quote(home, away, line, side, now):
    """{'prob','dec','best_size_usd','depth5c_usd','t_utc','market_id'} or {'excluded': reason}. Never raises to the caller."""
    try:
        ev, mk = _catalog(now)
    except Exception as e:
        return {"excluded": f"novig catalog unavailable ({type(e).__name__})"}
    cand = [e for e in ev if (_words(home) & _words(e.get("description") or "")) and (_words(away) & _words(e.get("description") or ""))]
    if len(cand) != 1:
        return {"excluded": f"event match {len(cand)}"}
    eid = cand[0]["eventId"]
    ms = [m for m in mk if m.get("eventId") == eid and (m.get("marketType") or "").upper() == "TOTAL"
          and m.get("status") == "OPEN" and m.get("strike") is not None and abs(float(m["strike"]) - float(line)) < 1e-9]
    if len(ms) != 1:
        return {"excluded": f"no open Novig total at {line:g}" if not ms else "ambiguous market"}
    m = ms[0]
    outs = m.get("outcomes") or []
    mine = next((o for o in outs if side.lower() in (o.get("name") or "").lower()), None)
    other = next((o for o in outs if o is not mine), None)
    if not mine or not other:
        return {"excluded": "outcome names not recognised"}
    try:
        book = _get(f"/v3/public/catalog/markets/{m['marketId']}/book", {"depth": 20})
    except Exception as e:
        return {"excluded": f"novig book unavailable ({type(e).__name__})"}
    bids = sorted(((float(r["price"]), int(r["qty"]) / 100.0) for r in (book.get("orders") or {}).get(other["outcomeId"], [])), reverse=True)
    if not bids:
        return {"excluded": "no opposing bids (no price to take)"}
    best = bids[0][0]
    p = round(1 - best, 4)                       # cost per $1 payout of the side we want
    if not 0.05 < p < 0.95:
        return {"excluded": "price outside 5-95c"}
    size = (1 - best) * bids[0][1]               # dollars we can stake at the best level
    d5 = sum((1 - pr) * q for pr, q in bids if pr >= best - 0.05)
    return {"prob": p, "dec": round(1 / p, 4), "best_size_usd": round(size, 2), "depth5c_usd": round(d5, 2),
            "t_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "market_id": m["marketId"]}


def _p(a):
    a = float(a)
    return -a / (-a + 100) if a < 0 else 100 / (a + 100)


def grade(sg, close):
    """Verified CLV for the Novig candidate; idempotent. Writes sg['clv_v'] (percent) or sg['clv_v_excl'] (reason)."""
    if "clv_v" in sg or "clv_v_excl" in sg:
        return
    q = sg.get("novig")
    if not q:
        return                                    # logged before this candidate existed: not part of the sample
    if "excluded" in q:
        sg["clv_v_excl"] = q["excluded"]
        return
    if not close:
        return                                    # not closed yet
    if abs(float(close["line"]) - float(sg["line"])) > 1e-9:
        sg["clv_v_excl"] = "close line differs from sighting line (modelled close refused)"
        return
    if close.get("mins_before") is None or close["mins_before"] > FRESH_CLOSE_MIN:
        sg["clv_v_excl"] = f"close read {close.get('mins_before')} min before tip (> {FRESH_CLOSE_MIN})"
        return
    po, pu = _p(close["over"]), _p(close["under"])
    pc = po / (po + pu)
    pc = pc if sg["side"] == "Over" else 1 - pc
    sg["clv_v"] = round(100 * (pc / q["prob"] - 1), 3)   # Novig pre-game fee 0: decimal = 1 / prob


def evaluate(games):
    """games: [(start_iso, sighting)] -> dict with counts, halves and bar status. One sighting per game = unique games."""
    q = sorted(((s, g) for s, g in games if g.get("clv_v") is not None), key=lambda x: x[0])
    v = [g["clv_v"] for _, g in q]
    h = len(v) // 2
    F, C = v[:h], v[h:]

    def ok(x):
        return bool(x) and st.mean(x) > 0 and sum(a > 0 for a in x) / len(x) >= 0.53
    return {"n": len(v), "fit": F, "check": C, "met": len(v) >= BAR_N and ok(F) and ok(C), "all": v}


def report(state):
    gs = [(g.get("start") or "", g["post"]["sighting"]) for g in state["games"].values()
          if g.get("post") and g["post"].get("sighting") and g["post"]["sighting"].get("novig") is not None]
    ex = {}
    for _, s in gs:
        r = s.get("clv_v_excl")
        if r:
            ex[r] = ex.get(r, 0) + 1
    quoted = [s for _, s in gs if "excluded" not in s["novig"]]
    e = evaluate(gs)
    f = lambda x: (f"{st.mean(x):+.2f}% beat {100 * sum(a > 0 for a in x) / len(x):.0f}% n {len(x)}" if x else "n 0")
    L = ["FORWARD CANDIDATE: NBA REG T-6h at NOVIG (paper; verified same-line Pinnacle close; unique games)",
         f"  sightings since logging started {len(gs)} | with a Novig quote {len(quoted)} | qualifying (verified CLV) {e['n']} of {BAR_N} needed",
         f"  ALL {f(e['all'])} | FIT {f(e['fit'])} | CHECK {f(e['check'])} | bar: {'MET' if e['met'] else 'not met'}"]
    if quoted:
        sz = [s["novig"]["best_size_usd"] for s in quoted]
        d5 = [s["novig"]["depth5c_usd"] for s in quoted]
        L.append(f"  Novig size at best level median ${st.median(sz):,.0f}; within 5c median ${st.median(d5):,.0f}")
    if ex:
        L.append("  excluded: " + "; ".join(f"{n} x {k}" for k, n in sorted(ex.items(), key=lambda kv: -kv[1])))
    return L, e


def maybe_notify(state, e):
    """One email when the registered sample AND both-half requirements are met. Silent otherwise."""
    if not e["met"] or state.get("cand_notified"):
        return
    user, pw, to = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD"), os.environ.get("EMAIL_TO")
    if not (user and pw and to):
        print("candidate bar met but no email credentials in this job")
        return
    L, _ = report(state)
    m = MIMEText("\n".join(L), "plain", "utf-8")
    m["Subject"], m["From"], m["To"] = "Bets NBA REG T-6h Novig candidate: registered sample and bar MET (paper)", user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(m)
    state["cand_notified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

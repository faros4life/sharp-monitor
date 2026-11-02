#!/usr/bin/env python3
"""
PLIMIT read-path PROBE v2 (Nov 2, 2026; Peter yes; Muse PLIMIT registration: confirm the read before any logger).
OddsPapi v4 free plan (250 billable requests / month, resets on the 1st; /v4/historical-odds is free). Read-only.
About 6 billable calls: sports, tournaments x3, odds-by-tournaments (pinnacle; circasports). Plus free historical
calls for 2 fixtures to see whether the limit is in the history. Private email; the Actions log prints counts only.
"""
import json
import os
import time
import urllib.parse
import urllib.request

import executor as ex

BASE = "https://api.oddspapi.io/v4"
KEY = (os.environ.get("ODDSPAPI_KEY") or "").strip()
CALLS = []


def get(path, **params):
    params["apiKey"] = KEY
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"Accept": "application/json", "User-Agent": "sharp-monitor-probe"})
    time.sleep(8 if path == "/historical-odds" else 1.1)   # history endpoint throttles harder (429 at ~1 s)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            CALLS.append((path, r.status))
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        CALLS.append((path, e.code))
        return {"_error": e.code, "_body": e.read().decode()[:300]}


def walk(book):
    """(outcomes, with_limit, samples) over a bookmakerOdds entry."""
    n = k = 0
    s = []
    for mid, m in (book.get("markets") or {}).items():
        for oid, o in (m.get("outcomes") or {}).items():
            for pid, pl in (o.get("players") or {}).items():
                n += 1
                if pl.get("limit") is not None:
                    k += 1
                    if len(s) < 4:
                        s.append(f"market {mid} {pl.get('bookmakerOutcomeId')}: price {pl.get('price')} limit {pl.get('limit')}")
    return n, k, s


def hr_check(fid):
    """Free-only: Hard Rock + Pinnacle history for one fixture (historical-odds is unmetered)."""
    L = [f"HARD ROCK HISTORY CHECK (free calls only), fixture {fid}"]
    h = get("/historical-odds", fixtureId=fid, bookmakers="hardrockbet,pinnacle")
    for bk in ("hardrockbet", "pinnacle"):
        b = ((h.get("bookmakers") or {}).get(bk) or {}) if isinstance(h, dict) else {}
        mk = b.get("markets") or {}
        ticks = sum(len(v) for m in mk.values() for o in (m.get("outcomes") or {}).values() for v in (o.get("players") or {}).values() if isinstance(v, list))
        first = None
        for m in mk.values():
            for o in (m.get("outcomes") or {}).values():
                for v in (o.get("players") or {}).values():
                    if isinstance(v, list) and v:
                        first = v[0]
                        break
                if first: break
            if first: break
        L.append(f"  {bk}: markets {len(mk)}, ticks {ticks}, sample tick {json.dumps(first)[:300] if first else '-'}")
    if isinstance(h, dict) and h.get("_error"):
        L.append(f"  HTTP {h['_error']} {h['_body']}")
    return L


def books_check(fid, books):
    """Free-only: which books carry a limit (or exchange depth) in history for one fixture. 3 books per call."""
    L = [f"LIMIT COVERAGE BY BOOK (free history calls only), fixture {fid}"]
    for i in range(0, len(books), 3):
        grp = books[i:i + 3]
        h = get("/historical-odds", fixtureId=fid, bookmakers=",".join(grp))
        if isinstance(h, dict) and h.get("_error"):
            L.append(f"  {grp}: HTTP {h['_error']} {h['_body'][:120]}")
            continue
        for bk in grp:
            mk = ((h.get("bookmakers") or {}).get(bk) or {}).get("markets") or {}
            n = lim = ex_ = 0
            samp = None
            for m in mk.values():
                for o in (m.get("outcomes") or {}).values():
                    for v in (o.get("players") or {}).values():
                        for t in (v if isinstance(v, list) else []):
                            n += 1
                            if t.get("limit") is not None:
                                lim += 1
                                samp = samp or t
                            if t.get("exchangeMeta"):
                                ex_ += 1
                                samp = samp or t
            L.append(f"  {bk}: markets {len(mk)}, ticks {n}, with limit {lim}, with exchange depth {ex_}"
                     + (f" | sample {json.dumps(samp)[:220]}" if samp else ""))
    return L


def discover(fid):
    """Markets map (1 billable) + one fixture's participants (1 billable) + its Pinnacle markets (free history)."""
    L = ["MARKETS DISCOVERY"]
    mk = get("/markets")
    rows = [m for m in (mk if isinstance(mk, list) else []) if m.get("sportId") in (11, 14, 15) and not m.get("playerProp")]
    by = {}
    for m in rows:
        by.setdefault((m.get("sportId"), m.get("period"), m.get("marketType")), []).append(m)
    L.append(f"markets total {len(mk) if isinstance(mk, list) else mk}; basketball/football/hockey non-prop {len(rows)}")
    for k, v in sorted(by.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), str(kv[0][2]))):
        if str(k[1]) != "result" or any(w in str(k[2]) for w in ("winningmargin", "correctscore", "exactgoals", "halftime", "highestscoring")):
            continue
        ex1 = v[:3]
        L.append(f"  sport {k[0]} period {k[1]} type {k[2]}: {len(v)} markets; e.g. " + "; ".join(
            f"{m['marketId']} '{m.get('marketName')}' h={m.get('handicap')} outs={[(o['outcomeId'], o['outcomeName']) for o in (m.get('outcomes') or [])[:4]]}" for m in ex1))
    periods = sorted({str(m.get("period")) for m in rows})
    L.append("periods seen: " + ", ".join(periods))
    fx = get("/fixture", fixtureId=fid)
    L.append("fixture: " + json.dumps({k: (fx.get(k) if isinstance(fx, dict) else None) for k in ("participant1Name", "participant2Name", "startTime", "tournamentId", "statusId")}))
    L.append("fixture keys: " + (",".join(sorted(fx.keys())) if isinstance(fx, dict) else str(fx)[:200]))
    h = get("/historical-odds", fixtureId=fid, bookmakers="pinnacle")
    pm = ((h.get("bookmakers") or {}).get("pinnacle") or {}).get("markets") or {} if isinstance(h, dict) else {}
    meta = {m["marketId"]: m for m in (mk if isinstance(mk, list) else [])}
    show = 0
    for mid, m in pm.items():
        md = meta.get(int(mid)) if str(mid).isdigit() else None
        if not md or str(md.get("period")) not in ("fulltime", "result"):
            continue
        last = {}
        for oid, o in (m.get("outcomes") or {}).items():
            ticks = (o.get("players") or {}).get("0") or []
            if ticks:
                t = max(ticks, key=lambda t: t.get("createdAt") or "")
                last[oid] = (t.get("price"), t.get("limit"))
        L.append(f"  pin market {mid} {md.get('marketType')} h={md.get('handicap')} '{md.get('marketName')}' last={last}")
        show += 1
        if show >= 40:
            break
    return L


def _ticks_at(ticks, T):
    """(last tick at or before T, first tick after T) as dicts with parsed time."""
    from datetime import datetime
    def pt(x):
        try:
            return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        except Exception:
            return None
    before = after = None
    for t in ticks or []:
        ct = pt(t.get("createdAt"))
        if not ct:
            continue
        if ct <= T and (before is None or ct > before[0]):
            before = (ct, t)
        if ct > T and (after is None or ct < after[0]):
            after = (ct, t)
    return before, after


def idcheck(arg):
    """Limit-identity check vs an OddsJam read + Pinnacle player-prop limit probe (PLIMIT Q2 step 0).
    arg: 'TeamA,TeamB,ISO-time'. Billable: /fixtures NBA, /markets, /fixtures NFL (3). History is free."""
    from datetime import datetime, timedelta
    ta, tb_, ts = [x.strip() for x in arg.split(",")]
    T = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    L = [f"LIMIT-IDENTITY CHECK + PROP-LIMIT PROBE: {ta} vs {tb_}, read time {ts}"]
    d0 = T.strftime("%Y-%m-%d")
    d1 = (T + timedelta(days=1)).strftime("%Y-%m-%d")
    fx = get("/fixtures", tournamentId=132, **{"from": d0, "to": d1})
    fid, f = None, None
    for x in fx if isinstance(fx, list) else []:
        nm = f"{x.get('participant1Name')} {x.get('participant2Name')}".lower()
        if ta.lower() in nm and tb_.lower() in nm:
            fid, f = x.get("fixtureId"), x
    if not fid:
        L.append(f"fixture not found ({fx if isinstance(fx, dict) else len(fx or [])})")
        return L
    L.append(f"fixture {fid}: team 1 = {f.get('participant1Name')}, team 2 = {f.get('participant2Name')}, start {f.get('startTime')}")
    mk = get("/markets")
    meta = {str(m["marketId"]): m for m in (mk if isinstance(mk, list) else [])}
    h = get("/historical-odds", fixtureId=fid, bookmakers="pinnacle")
    pm = ((h.get("bookmakers") or {}).get("pinnacle") or {}).get("markets") or {} if isinstance(h, dict) else {}
    a_is_1 = ta.lower() in str(f.get("participant1Name")).lower()

    def show(mid, label):
        m = pm.get(str(mid)) or {}
        md = meta.get(str(mid)) or {}
        names = {str(o["outcomeId"]): o.get("outcomeName") for o in md.get("outcomes") or []}
        for oid, o in (m.get("outcomes") or {}).items():
            b, a = _ticks_at((o.get("players") or {}).get("0"), T)
            nm = names.get(oid, oid)
            who = (ta if (nm == "1") == a_is_1 else tb_) if nm in ("1", "2") else nm
            if b:
                t = b[1]
                pr = t.get("price")
                lim = t.get("limit")
                base = round(lim * (pr - 1), 1) if (lim is not None and pr) else None
                L.append(f"  {label} {who}: tick at {b[0].strftime('%H:%M:%S')}Z price {pr} (am {_am(pr)}) limit {lim} implied base {base}"
                         + (f" | next tick {a[0].strftime('%H:%M:%S')}Z price {a[1].get('price')} limit {a[1].get('limit')}" if a else ""))
            else:
                L.append(f"  {label} {who}: no tick at or before the read")

    L.append("MONEYLINE (market 111):")
    show("111", "ML")
    sp = sorted([(float(m.get("handicap") or 0), k) for k, m in meta.items() if m.get("sportId") == 11 and m.get("period") == "result"
                 and m.get("marketType") == "spreads" and k in pm])
    tt = sorted([(float(m.get("handicap") or 0), k) for k, m in meta.items() if m.get("sportId") == 11 and m.get("period") == "result"
                 and m.get("marketType") == "totals" and k in pm])
    L.append("SPREADS near the read (team 1 handicap; OddsJam: DET -5 / CHA +5):")
    for hcap, k in sp:
        if abs(abs(hcap) - 5) <= 1.0:
            show(k, f"spread h={hcap:+g}")
    L.append("TOTALS near the read (OddsJam: 210.5):")
    for hcap, k in tt:
        if abs(hcap - 210.5) <= 1.0:
            show(k, f"total {hcap:g}")

    def props(pmk, sport):
        by = {}
        samples = []
        for mid, m in pmk.items():
            md = meta.get(str(mid)) or {}
            if md.get("sportId") != sport or not (md.get("playerProp") or "player" in str(md.get("marketType"))):
                continue
            typ = md.get("marketType")
            for oid, o in (m.get("outcomes") or {}).items():
                for pid, ticks in (o.get("players") or {}).items():
                    if not isinstance(ticks, list) or not ticks:
                        continue
                    last = max(ticks, key=lambda t: str(t.get("createdAt")))
                    c = by.setdefault(typ, [0, 0])
                    c[0] += 1
                    if last.get("limit") is not None:
                        c[1] += 1
                        if len(samples) < 3 and last.get("price"):
                            samples.append(f"{typ} h={md.get('handicap')} player {pid}: price {last.get('price')} limit {last.get('limit')} "
                                           f"implied base {round(last['limit'] * (last['price'] - 1), 1)} at {last.get('createdAt')}")
        return by, samples
    by, samples = props(pm, 11)
    L.append("NBA PLAYER PROPS on this fixture (Pinnacle history, last tick per player outcome): outcomes with a limit / total")
    L += [f"  {k}: {v[1]} / {v[0]}" for k, v in sorted(by.items())] or ["  none listed"]
    L += ["  sample: " + s for s in samples]
    fx2 = get("/fixtures", tournamentId=31, **{"from": d0, "to": d1})
    nfl = [x for x in (fx2 if isinstance(fx2, list) else [])]
    if nfl:
        g = nfl[0]
        h2 = get("/historical-odds", fixtureId=g.get("fixtureId"), bookmakers="pinnacle")
        pm2 = ((h2.get("bookmakers") or {}).get("pinnacle") or {}).get("markets") or {} if isinstance(h2, dict) else {}
        by2, s2 = props(pm2, 14)
        L.append(f"NFL PLAYER PROPS ({g.get('participant1Name')} vs {g.get('participant2Name')}): outcomes with a limit / total")
        L += [f"  {k}: {v[1]} / {v[0]}" for k, v in sorted(by2.items())] or ["  none listed"]
        L += ["  sample: " + s for s in s2]
    else:
        L.append("NFL: no fixture in the window")
    return L


def _am(d):
    try:
        d = float(d)
        return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))
    except Exception:
        return None



def main():
    if os.environ.get("HR_FIXTURE") and os.environ.get("HR_BOOKS") == "IDCHECK":
        L = idcheck(os.environ["HR_FIXTURE"])
        L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS)]
        ex.send("Bets ODDSPAPI LIMIT-IDENTITY + PROP PROBE", "\n".join(L))
        print(f"idcheck emailed: {len(CALLS)} calls")
        return
    if os.environ.get("HR_FIXTURE") and os.environ.get("HR_BOOKS") == "DISCOVER":
        L = discover(os.environ["HR_FIXTURE"])
        L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS)]
        ex.send("Bets ODDSPAPI MARKETS DISCOVERY", "\n".join(L))
        print(f"discovery emailed: {len(CALLS)} calls")
        return
    if os.environ.get("HR_FIXTURE") and os.environ.get("HR_BOOKS"):
        L = books_check(os.environ["HR_FIXTURE"], [b.strip() for b in os.environ["HR_BOOKS"].split(",") if b.strip()])
        L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS) + " (historical-odds is free)"]
        ex.send("Bets LIMIT COVERAGE BY BOOK (OddsPapi)", "\n".join(L))
        print(f"coverage check emailed: {len(CALLS)} calls")
        return
    if os.environ.get("HR_FIXTURE"):
        L = hr_check(os.environ["HR_FIXTURE"])
        L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS) + " (historical-odds is free)"]
        ex.send("Bets HR HISTORY CHECK (OddsPapi)", "\n".join(L))
        print(f"HR check emailed: {len(CALLS)} calls")
        return
    L = ["PLIMIT PROBE v2 (OddsPapi v4, free plan)", ""]
    if not KEY:
        ex.send("Bets PLIMIT PROBE", "ODDSPAPI_KEY not set - nothing read.")
        return
    acct = get("/account")
    L.append("account: " + json.dumps({k: acct.get(k) for k in ("plan", "requestsUsed", "requestsLimit", "used", "limit", "_error")
                                       if isinstance(acct, dict)})[:300])
    sports = get("/sports")
    if isinstance(sports, dict) and sports.get("_error"):
        L.append(f"/sports HTTP {sports['_error']}: {sports['_body']}")
        ex.send("Bets PLIMIT PROBE v2 (OddsPapi)", "\n".join(L))
        print("probe: sports failed")
        return
    sid = {s.get("slug"): s.get("sportId") for s in sports}
    L.append("sport ids: " + json.dumps({k: sid.get(k) for k in ("basketball", "american-football", "ice-hockey")}))
    tids = {}
    for slug, wants in (("basketball", {"NBA": "nba"}), ("american-football", {"NFL": "nfl", "NCAAF": "ncaa"}),
                        ("ice-hockey", {"NHL": "nhl"})):
        if not sid.get(slug):
            continue
        ts = get("/tournaments", sportId=sid[slug])
        for t in ts if isinstance(ts, list) else []:
            nm, cat = (t.get("tournamentName") or "").lower(), (t.get("categorySlug") or "").lower()
            for lg, w in wants.items():
                if lg not in tids and (nm == w or (nm.startswith(w) and "usa" in cat) or (lg == "NCAAF" and "ncaa" in nm and "div" not in nm and "usa" in cat)):
                    tids[lg] = (t.get("tournamentId"), t.get("tournamentName"), t.get("upcomingFixtures"), t.get("futureFixtures"))
    L.append("tournaments: " + json.dumps(tids))
    ids = ",".join(str(tids[l][0]) for l in ("NBA", "NFL", "NHL") if l in tids)
    first = {}
    for bk in ("pinnacle", "circasports"):
        d = get("/odds-by-tournaments", tournamentIds=ids, bookmaker=bk, verbosity=3)
        if isinstance(d, dict) and d.get("_error"):
            L.append(f"{bk}: HTTP {d['_error']} {d['_body']}")
            continue
        fx = d if isinstance(d, list) else []
        L.append(f"{bk}: {len(fx)} fixtures (NBA/NFL/NHL)")
        tot_n = tot_k = 0
        by_t = {}
        for f in fx:
            b = (f.get("bookmakerOdds") or {}).get(bk) or {}
            n, k, s = walk(b)
            tot_n += n
            tot_k += k
            by_t.setdefault(f.get("tournamentId"), [0, 0])
            by_t[f.get("tournamentId")][0] += n
            by_t[f.get("tournamentId")][1] += k
            if s and bk not in first:
                first[bk] = f.get("fixtureId")
                L.append(f"  sample fixture {f.get('fixtureId')} start {f.get('startTime')}:")
                L += ["    " + x for x in s]
        L.append(f"  outcomes {tot_n}, with a limit {tot_k}; by tournament (outcomes, with limit): {json.dumps(by_t)}")
    for bk, fid in first.items():
        h = get("/historical-odds", fixtureId=fid, bookmakers=bk)
        txt = json.dumps(h)
        L.append(f"historical ({bk}, free): {len(txt)} chars; contains 'limit': {'limit' in txt}; head: {txt[:400]}")
    L += ["", "Calls: " + "; ".join(f"{p} {c}" for p, c in CALLS),
          "Billable: every call except /account and /historical-odds."]
    ex.send("Bets PLIMIT PROBE v2 (OddsPapi)", "\n".join(L))
    print(f"PLIMIT probe v2 emailed: {len(CALLS)} calls")   # counts only


if __name__ == "__main__":
    main()

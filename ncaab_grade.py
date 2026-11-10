#!/usr/bin/env python3
"""
NCAAB OPENERS - GRADER v1.1 (item 28; Peter go Nov 3, 4:38 PM ET via Muse). PAPER ONLY: never places orders, never
alerts. Grades the freezer's frozen numbers (ncaab_openers.py, ncaab-openers branch) against Pinnacle's history.

Registered rules (ncaab_openers.py header, unchanged):
  Pinnacle OPEN = Pinnacle's main full-game total one minute after its first totals tick (main = biggest limit).
  Sighting = |frozen number - Pinnacle open| >= 3.0, bands 3.0-3.9 / 4.0+, side toward our number. A number frozen
    after Pinnacle's open is never a sighting (it could have seen the open). Freeze time, open time and lag logged.
  PRIMARY grade = Pinnacle no-vig CLOSE at the sighting line vs Pinnacle's no-vig OPEN for that side (half points
    priced in when the close is at another number): CLV% = close fair / open fair - 1.
  SECONDARY = flat 1u at the best after-fee exchange price (Novig, ProphetX, Kalshi, Polymarket US) at the open, same
    line; graded on the final.
  MAE: our number vs the final, and Pinnacle's open vs the final, on every posted game.
  First read at 60 sightings. STOP if CLV <= 0 at 60, or our MAE more than 1.0 point worse than the open's.

OddsPapi data is never republished: the grades live in an ENCRYPTED file (ncaab_grades.enc) on the ncaab-openers
branch; the report goes by private email; the Actions log prints counts only. History calls are free; the only
billable calls are the NCAAB tournament lookup (once) and one /fixtures call a day. It waits when another OddsPapi
download job is running (one downloader at a time).
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import finals as fin
import hist_cache as hc
import sharp_monitor as sm
import tracker_build as tb

ET = tb.ET
DIR = os.environ.get("NCAAB_DIR", "") or "ncaab-openers"
FROZEN = os.path.join(DIR, "ncaab_openers.json")
OUT = os.path.join(DIR, "ncaab_grades.enc")
SID = 11                        # basketball
MAX_FIX = int(os.environ.get("NCAAB_MAX_FIX", "") or "30")   # fixtures read per run (2 free history calls each)
BAND = 3.0
FIRST_READ = 60
BOOKS1 = ["pinnacle", "novig.us", "prophetx"]
BOOKS2 = ["kalshi", "polymarket.us"]
EXCH = ["novig.us", "prophetx", "kalshi", "polymarket.us"]
DOWNLOADERS = ("exchange-lag", "slowhr-backtest", "x2-backtest", "nba-backtest2", "model-lab")
NAME = {"novig.us": "Novig", "prophetx": "ProphetX", "kalshi": "Kalshi", "polymarket.us": "Polymarket US"}


def eff(book, dec):
    """After-fee decimal (same fee model as the exchange-lag study)."""
    if book == "prophetx":
        return 1 + (dec - 1) * 0.98
    if book in ("kalshi", "polymarket.us"):
        p = 1 / dec
        # Nov 6: PM US taker default corrected per the venue's published schedule
        fee = 0.07 if book == "kalshi" else float(os.environ.get("PMUS_FEE", "") or "0.06")
        return 1 / (p * (1 + fee * (1 - p)))
    return dec


def other_downloader_running():
    repo, tok = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_TOKEN", "")
    if not repo:
        return False
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/runs?status=in_progress&per_page=50",
                                     headers={"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {tok}"} if tok else {})})
        runs = json.loads(urllib.request.urlopen(req, timeout=20).read().decode()).get("workflow_runs") or []
        return any(r.get("name") in DOWNLOADERS for r in runs)
    except Exception:
        return False


def tournament(st, now):
    if st.get("tid"):
        return st["tid"]
    if not cl.can_bill(st, now):
        return None
    ts = cl.api("/tournaments", True, sportId=SID)
    cl.bill(st, now)
    best = None
    for t in ts if isinstance(ts, list) else []:
        nm = (t.get("tournamentName") or "").lower()
        if "ncaa" in nm and "women" not in nm and "usa" in (t.get("categorySlug") or "").lower():
            n = (t.get("upcomingFixtures") or 0) + (t.get("futureFixtures") or 0)
            if not best or n > best[0]:
                best = (n, t.get("tournamentId"), t.get("tournamentName"))
    if best and best[0] > 0:
        st["tid"], st["tname"] = best[1], best[2]
    return st.get("tid")


def refresh_fixtures(st, now):
    last = cl.tp(st.get("fx_last"))
    if last and now - last < timedelta(hours=24):
        return
    tid = tournament(st, now)
    if not tid or not cl.can_bill(st, now):
        return
    lo, hi = (now - timedelta(days=3)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET)
    d = cl.api("/fixtures", True, tournamentId=tid, **{"from": lo.strftime("%Y-%m-%d"), "to": hi.strftime("%Y-%m-%d")})
    cl.bill(st, now)
    st["fx_last"] = cl.iso(now)
    if isinstance(d, dict) and d.get("_error"):
        st.setdefault("errors", []).append(f"{cl.iso(now)} fixtures: {d['_error']}")
        return
    fx = st.setdefault("fixtures", {})
    for f in d if isinstance(d, list) else []:
        if f.get("fixtureId"):
            fx[f["fixtureId"]] = {"start": f.get("startTime"), "n1": f.get("participant1Name"), "n2": f.get("participant2Name")}


def match(st, g):
    gs = cl.tp(g.get("start"))
    a, h = tb.toks(g.get("away")) - tb.WEAK, tb.toks(g.get("home")) - tb.WEAK
    best, sc = None, 0
    for fid, f in (st.get("fixtures") or {}).items():
        fs = cl.tp(f.get("start"))
        if not gs or not fs or abs((fs - gs).total_seconds()) > 6 * 3600:
            continue
        t1, t2 = tb.toks(f.get("n1")) - tb.WEAK, tb.toks(f.get("n2")) - tb.WEAK
        s = max(len(a & t1) + len(h & t2), len(a & t2) + len(h & t1)) if (a & t1 and h & t2) or (a & t2 and h & t1) else 0
        if s > sc:
            best, sc = fid, s
    return best


def totals(pm, mkmap):
    """[(line, over_mid, under_oid, over_oid)] for Pinnacle-style full-game totals markets present in the history."""
    out = []
    for mid, (s, t, hcap, outs) in mkmap.items():
        if s != SID or t != "totals" or mid not in pm:
            continue
        nm = {v: k for k, v in outs.items()}
        if nm.get("Over") and nm.get("Under"):
            out.append((hcap, mid, nm["Over"], nm["Under"]))
    return out


def first_tick(pm, mids):
    best = None
    for mid in mids:
        for o in ((pm.get(str(mid)) or {}).get("outcomes") or {}).values():
            for t in (o.get("players") or {}).get("0") or []:
                ct = cl.tp(t.get("createdAt"))
                if ct and (best is None or ct < best):
                    best = ct
    return best


def state_at(pm, tots, when):
    """[(line, p_over no-vig, limit)] for every totals line priced at the given time."""
    out = []
    for hcap, mid, ov, un in tots:
        tw = cl.two_way(pm, mid, when)
        if ov in tw and un in tw:
            out.append((hcap, cl.novig_p(tw[ov][0], tw[un][0]), min(tw[ov][2], tw[un][2])))
    return out


def fair_at_line(cands, line, over):
    """No-vig chance for the side at that line: exact line, else the main line moved with the basketball half-point value."""
    if not cands:
        return None, None
    ex = next((c for c in cands if abs(c[0] - line) < 1e-9), None)
    if ex:
        return (ex[1] if over else 1 - ex[1]), "own line"
    main = max(cands, key=lambda c: (c[2], -abs(c[1] - 0.5)))
    if abs(main[0] - line) > 6:
        return None, None
    p = main[1] if over else 1 - main[1]
    v = sm.half_point_value("NCAAB", "tot", main[0], line, main[0])
    better = (line < main[0]) if over else (line > main[0])
    return min(max(p + (v if better else -v), .01), .99), f"main {main[0]:g} moved to {line:g}"


def grade_one(g, fid, f, mkmap):
    s = cl.tp(f.get("start")) or cl.tp(g.get("start"))
    h1 = hc.get_hist(fid, BOOKS1, s)
    if isinstance(h1, dict) and h1.get("_error"):
        return None, "history error"
    pin = cl.book_markets(h1, "pinnacle")
    tots = totals(pin, mkmap)
    if not tots:
        return {"posted": False}, None
    t0 = first_tick(pin, [m for _, m, _, _ in tots])
    if not t0:
        return {"posted": False}, None
    t_open = t0 + timedelta(minutes=1)
    oc = state_at(pin, tots, t_open)
    cc = state_at(pin, tots, s)
    if not oc:
        return {"posted": False}, None
    main_o = max(oc, key=lambda c: (c[2], -abs(c[1] - 0.5)))
    rec = {"posted": True, "fid": fid, "open_line": main_o[0], "open_utc": cl.iso(t_open)}
    if cc:
        main_c = max(cc, key=lambda c: (c[2], -abs(c[1] - 0.5)))
        rec["close_line"] = main_c[0]
    num = g.get("number")
    frozen = cl.tp(g.get("frozen_utc"))
    if num is None:
        return rec, None
    diff = round(num - main_o[0], 1)
    rec["diff"] = diff
    rec["freeze_lag_min"] = round((t_open - frozen).total_seconds() / 60) if frozen else None
    if abs(diff) < BAND:
        return rec, None
    if frozen and frozen >= t_open:
        rec["not_sighting"] = "frozen after Pinnacle's open"
        return rec, None
    over = diff > 0
    line = main_o[0]
    p_open = main_o[1] if over else 1 - main_o[1]
    p_close, how = fair_at_line(cc, line, over)
    sg = {"side": "OVER" if over else "UNDER", "line": line, "band": "4.0+" if abs(diff) >= 4 else "3.0-3.9",
          "p_open": round(p_open, 4), "p_close": round(p_close, 4) if p_close is not None else None, "close_how": how,
          "clv_pct": round(100 * (p_close / p_open - 1), 2) if p_close is not None else None}
    # secondary: best after-fee exchange price at the open, same line, same side
    h2 = hc.get_hist(fid, BOOKS2, s)
    best = None
    for bk in EXCH:
        src = h1 if bk in BOOKS1 else (h2 if isinstance(h2, dict) and not h2.get("_error") else {})
        xm = cl.book_markets(src, bk)
        for hcap, mid, ov, un in totals(xm, mkmap):
            if abs(hcap - line) > 1e-9:
                continue
            tw = cl.two_way(xm, mid, t_open)
            o = tw.get(ov if over else un)
            if o and o[0] > 1:
                d = eff(bk, o[0])
                if not best or d > best[1]:
                    best = (bk, d)
    if best:
        sg["exch_book"], sg["exch_dec_af"] = best[0], round(best[1], 4)
    rec["sighting"] = sg
    return rec, None


def result(sg, final):
    if final is None or not sg:
        return None
    if final == sg["line"]:
        return "P"
    return "W" if (final > sg["line"]) == (sg["side"] == "OVER") else "L"


def report(st, games, now):
    rows = [(gid, g, st["graded"].get(gid)) for gid, g in games.items() if st["graded"].get(gid)]
    posted = [(gid, g, r) for gid, g, r in rows if r.get("posted")]
    sg = [(gid, g, r) for gid, g, r in posted if r.get("sighting")]
    L = [f"NCAAB OPENERS GRADER v1.1 (paper; frozen numbers vs Pinnacle open/close; {now.astimezone(ET).strftime('%a %b %-d %-I:%M %p ET')})",
         f"Frozen games {len(games)} | graded {len(rows)} | Pinnacle posted a total {len(posted)} | sightings {len(sg)} "
         f"(first read at {FIRST_READ}) | fixtures matched {sum(1 for g in games if st['fix'].get(g))}",
         ""]
    mae = [(abs(g["number"] - g["final"]), abs(r["open_line"] - g["final"])) for gid, g, r in posted
           if g.get("number") is not None and g.get("final") is not None]
    if mae:
        a, b = sum(x for x, _ in mae) / len(mae), sum(y for _, y in mae) / len(mae)
        L.append(f"MAE vs final (n {len(mae)}): our number {a:.2f} pts | Pinnacle open {b:.2f} pts | ours minus open {a - b:+.2f}"
                 + ("  << STOP rule: more than 1.0 worse" if a - b > 1.0 and len(mae) >= FIRST_READ else ""))
    on = [(gid, g, r) for gid, g, r in sg if g.get("on_time")]
    for name, xs in (("ALL sightings", sg), ("frozen on time (06:00 ET day before)", on),
                     ("band 3.0-3.9", [x for x in sg if x[2]["sighting"]["band"] == "3.0-3.9"]),
                     ("band 4.0+", [x for x in sg if x[2]["sighting"]["band"] == "4.0+"]),
                     ("OVER", [x for x in sg if x[2]["sighting"]["side"] == "OVER"]),
                     ("UNDER", [x for x in sg if x[2]["sighting"]["side"] == "UNDER"])):
        c = [x[2]["sighting"]["clv_pct"] for x in xs if x[2]["sighting"].get("clv_pct") is not None]
        res = [(result(x[2]["sighting"], x[1].get("final")), x[2]["sighting"].get("exch_dec_af")) for x in xs]
        u = [fin.units_wl(r, d) for r, d in res if r and d]
        w = sum(1 for r, _ in res if r == "W")
        lo = sum(1 for r, _ in res if r == "L")
        L.append(f"  {name}: n {len(xs)} | CLV {sum(c) / len(c):+.2f}% (n {len(c)}, beat close {sum(1 for v in c if v > 0)}/{len(c)})"
                 if c else f"  {name}: n {len(xs)} | CLV n/a")
        L[-1] += f" | {w}-{lo} on the final | exchange units {sum(u):+.2f}u ({len(u)} with an exchange price at the open)"
    c_all = [x[2]["sighting"]["clv_pct"] for x in sg if x[2]["sighting"].get("clv_pct") is not None]
    if len(c_all) >= FIRST_READ:
        L.append("")
        L.append(f"FIRST READ ({len(c_all)} sightings): CLV {sum(c_all) / len(c_all):+.2f}%"
                 + ("  << STOP rule: CLV <= 0" if sum(c_all) <= 0 else "  (passes the CLV > 0 bar so far)"))
    lagged = [r.get("freeze_lag_min") for gid, g, r in posted if r.get("freeze_lag_min") is not None]
    if lagged:
        L.append("")
        L.append(f"Freeze-to-open lag: median {sorted(lagged)[len(lagged) // 2]} min (positive = we froze before Pinnacle opened); "
                 f"frozen after the open (never sightings): {sum(1 for gid, g, r in posted if r.get('not_sighting'))}")
    L += ["", "SIGHTINGS (latest 40)"]
    for gid, g, r in sorted(sg, key=lambda x: x[1].get("start") or "", reverse=True)[:40]:
        s = r["sighting"]
        clv = f"{s['clv_pct']:+.2f}%" if s.get("clv_pct") is not None else "n/a"
        L.append(f"  {g['away']} @ {g['home']} ({(cl.tp(g['start']) or now).astimezone(ET).strftime('%b %-d')}): ours {g['number']:g}, "
                 f"open {r['open_line']:g} ({r['diff']:+g}) -> {s['side']} {s['line']:g} [{s['band']}] | CLV {clv}")
        L[-1] += (f" | final {g['final']:g} {result(s, g['final'])}" if g.get("final") is not None else " | not final")
        if s.get("exch_book"):
            L[-1] += f" | best exchange at open {NAME.get(s['exch_book'], s['exch_book'])} {cl.dec_to_am(s['exch_dec_af']):+d} after fees"
    L += ["", "Rules: see ncaab_grade.py header (registered Nov 2 / Nov 3). Paper only. OddsPapi history (free calls)."]
    return "\n".join(L)


MKMAP = {}


def pending_counts(st, games, now):
    """Reporting only: frozen games past the 4h mark and inside the 12-day window that have no grade yet, split by why.
    (no fixture = no OddsPapi fixture matched; history unread = fixture matched but the history was not graded.)"""
    nofix = hist = 0
    for gid, g in games.items():
        s = cl.tp(g.get("start"))
        if gid in st["graded"] or not s or now - s < timedelta(hours=4) or now - s > timedelta(days=12):
            continue
        if st["fix"].get(gid) or match(st, g):
            hist += 1
        else:
            nofix += 1
    return nofix, hist


def main():
    global MKMAP
    now = datetime.now(timezone.utc)
    if not cl.KEY or not tb.PASS:
        print("NCAAB grader: ODDSPAPI_KEY or TRACKER_PASSPHRASE not set; skipped")
        return
    try:
        games = json.load(open(FROZEN)).get("games") or {}
    except Exception:
        print("NCAAB grader: no frozen numbers yet")
        return
    try:
        st = tb.dec(json.load(open(OUT)))
    except Exception:
        st = {}
    for k in ("graded", "fix", "fixtures", "billable"):
        st.setdefault(k, {})
    busy = other_downloader_running()
    read = 0
    if not busy:
        MKMAP = cl.load_markets(st, now)
        refresh_fixtures(st, now)
        todo = []
        for gid, g in games.items():
            s = cl.tp(g.get("start"))
            if gid in st["graded"] or not s or now - s < timedelta(hours=4) or now - s > timedelta(days=12):
                continue
            todo.append((s, gid, g))
        todo.sort()
        for s, gid, g in todo[:MAX_FIX]:
            fid = st["fix"].get(gid) or match(st, g)
            if not fid:
                if now - s > timedelta(days=2):
                    st["graded"][gid] = {"posted": False, "why": "no OddsPapi fixture"}
                continue
            st["fix"][gid] = fid
            rec, err = grade_one(g, fid, st["fixtures"].get(fid) or {}, MKMAP)
            if err:
                continue
            st["graded"][gid] = rec
            read += 1
    last = cl.tp(st.get("emailed"))
    local = now.astimezone(ET)
    n_sg = sum(1 for r in st["graded"].values() if r.get("sighting"))
    due = (not last or last.astimezone(ET).date() < local.date()) and local.hour >= 9
    first = n_sg >= FIRST_READ and not st.get("first_read_sent")
    if (due or first) and st["graded"]:
        try:
            import executor as ex
            ex.send(f"Bets NCAAB OPENERS GRADER ({n_sg} sightings)", report(st, games, now))
            st["emailed"] = cl.iso(now)
            if first:
                st["first_read_sent"] = cl.iso(now)
        except Exception as e:
            print(f"NCAAB grader: email failed ({type(e).__name__})")
    json.dump(tb.enc(st), open(OUT, "w"))
    nofix, hist = pending_counts(st, games, now)
    finals = sum(1 for g in games.values() if g.get("final") is not None)
    print(f"NCAAB grader: {'waited (another OddsPapi download running)' if busy else 'ran'}; graded +{read}, "
          f"cumulative graded {len(st['graded'])}, pending {nofix + hist} (no fixture {nofix}, history unread {hist}), "
          f"sightings {n_sg}, finals {finals}, calls {len(cl.CALLS)}")   # counts only


if __name__ == "__main__":
    main()

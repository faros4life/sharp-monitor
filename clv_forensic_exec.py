#!/usr/bin/env python3
"""CLV FORENSIC - EXECUTED FILLS (audit of 10 Nov 2026). READ-ONLY, CACHE-ONLY, ZERO CREDITS.

Re-reads every graded Lane 1 bot fill from the books' own records and re-derives its Pinnacle close from
the cached history, but KEEPS what executed_clv.py throws away, so each figure can be audited:
  how the close was read (own line / moneyline / modelled), the close tick's age and timestamp, the
  line and side, the fill's net decimal, and the Pinnacle fair probability at ENTRY time (read at or
  before the entry timestamp, never after) next to the close.
Then, WITHOUT changing the registered rule:
  * headline on VERIFIED closes only, and the modelled ones separately, never mixed
  * a freshness-sensitivity table (close tick no older than 15 / 60 / 240 / 1440 min)
  * every |CLV| > 10% listed for review (classified by hand, never deleted)
  * the three-way split: entry edge, Pinnacle fair-probability movement, net CLV. They multiply, they
    are never added:   (1 + CLV) = (1 + entry_edge) * (p_close / p_entry_fair)
Does not modify executed_clv.py, any live rule, any threshold, or any stored report.
No dollars in the public log; the per-row CSV goes to the private address and carries no stakes.
"""
import os
import sys

import netguard                                   # FIRST: before any project import can open a socket
netguard.refuse_if_proxied(os.environ)
netguard.install(allow=("smtp.gmail.com",))       # the only host this job may reach: the private email

import csv
import io
import json
import smtplib
import statistics as st
from collections import Counter
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import clv_ledger as cl
import clv_std as cs
import executed_clv as xc
import executor as ex
import hist_cache as hc
import slow_hr as sh
import tracker_build as tb


class _NoNetwork(RuntimeError):
    pass


def _refuse(*a, **k):
    raise _NoNetwork("OddsPapi call refused: this audit never buys or fetches data")


# Belt and braces, four independent layers (any one of which stops a spend):
#   1 the workflow passes NO OddsPapi secret       2 CLV_MONTH_CAP=0 in the workflow
#   3 these call sites are replaced here          4 netguard blocks the connection itself
cl.api = _refuse
cl.bill = _refuse
cl.load_markets = _refuse        # it BILLS when clv/markets.json is 7+ days old; we read the file instead
hc.get_hist_orig = hc.get_hist


def _cached_only(fid, books, start=None):
    """hist_cache.get_hist, but a miss is an error instead of a fetch."""
    for b in books:
        if not os.path.exists(hc._path(fid, b)):
            raise _NoNetwork(f"not cached: {b}")
    return hc.get_hist_orig(fid, books, start)


hc.get_hist = _cached_only

COLS = ["day", "league", "game", "bet", "venue", "fill_american", "fill_net_decimal", "result",
        "close_how", "close_verified", "close_age_min", "close_tick_utc", "game_start_utc",
        "pin_close_prob", "net_clv_pct",
        "entry_time_utc", "entry_time_source", "entry_how", "entry_age_min", "pin_entry_fair_prob",
        "entry_edge_pct", "pin_movement_pct", "excluded_reason", "fee_model"]
FRESH_STEPS = (15, 60, 240, 1440)
L = []


def say(t=""):
    L.append(t)
    print(t)


def split(p_entry, p_close, net_dec):
    """(entry_edge %, movement %, net CLV %). Multiplicative: 1+CLV = (1+edge) * (p_close/p_entry)."""
    if None in (p_entry, p_close, net_dec) or p_entry <= 0:
        return None, None, None
    edge = p_entry * net_dec - 1
    mov = p_close / p_entry - 1
    clv = p_close * net_dec - 1
    return round(100 * edge, 3), round(100 * mov, 3), round(100 * clv, 3)


def summarize(rows):
    """Pure summary over dict rows with net_clv_pct; used by the self-test as well."""
    v = [r["net_clv_pct"] for r in rows if r["net_clv_pct"] is not None]
    if not v:
        return {"n": 0}
    sd = st.pstdev(v) if len(v) < 2 else st.stdev(v)
    return {"n": len(v), "mean": round(st.mean(v), 3), "median": round(st.median(v), 3),
            "beat": sum(1 for x in v if x > 0), "sd": round(sd, 3),
            "se": round(sd / len(v) ** 0.5, 3), "big": sum(1 for x in v if abs(x) > 10)}


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (c - h, c + h)


def tcrit(df):
    tab = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23,
           15: 2.13, 20: 2.09, 30: 2.04, 60: 2.00}
    for k in sorted(tab):
        if df <= k:
            return tab[k]
    return 1.98


def ci_line(label, vals):
    n = len(vals)
    if n < 2:
        return f"  {label:46s} n {n}"
    m, sd = st.mean(vals), st.stdev(vals)
    h = tcrit(n - 1) * sd / n ** 0.5
    k = sum(1 for v in vals if v > 0)
    lo, hi = wilson(k, n)
    return (f"  {label:46s} n {n:3d} | CLV {m:+.2f}% (95% CI {m - h:+.2f}..{m + h:+.2f}) | beat close {k}/{n} "
            f"= {100 * k / n:.0f}% (Wilson {100 * lo:.0f}-{100 * hi:.0f}%)")


def line(label, s):
    if not s.get("n"):
        return f"  {label:46s} n 0"
    return (f"  {label:46s} n {s['n']:3d} | mean {s['mean']:+6.2f}% (se {s['se']:.2f}) | median "
            f"{s['median']:+6.2f}% | beat {s['beat']}/{s['n']} | |CLV|>10: {s['big']}")


def send_csv(subject, body, rows, filename, cols=None, extra=()):
    user, pw, to = ex.gmail()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols or COLS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    m = MIMEMultipart()
    m["Subject"], m["From"], m["To"] = subject, user, to
    m.attach(MIMEText(body, "plain", "utf-8"))
    part = MIMEBase("text", "csv")
    part.set_payload(buf.getvalue().encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    m.attach(part)
    for (fn, c2, r2) in extra:
        b2 = io.StringIO()
        w2 = csv.DictWriter(b2, fieldnames=c2, extrasaction="ignore")
        w2.writeheader()
        for r in r2:
            w2.writerow(r)
        p2 = MIMEBase("text", "csv")
        p2.set_payload(b2.getvalue().encode("utf-8"))
        encoders.encode_base64(p2)
        p2.add_header("Content-Disposition", "attachment", filename=fn)
        m.attach(p2)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(m)


L2COLS = ["day", "league", "game", "kind", "type", "side", "team", "hr_american", "hr_decimal", "late", "mins_before",
          "stored_close_fair", "recomputed_close_fair", "close_tick_age_min", "close_verified", "clv_pct", "excluded_reason"]


def _ml_close(pin, mkmap, lg, start):
    """Independent Pinnacle MONEYLINE no-vig close at game start from the cached ticks: (p_side1, age_min) or None."""
    sid = cl.SPORT[lg]
    best = None
    for mid, (s, typ, hcap, outs) in mkmap.items():
        if s != sid or typ != "moneyline" or mid not in pin:
            continue
        names = {v: k for k, v in outs.items()}
        o1, o2 = names.get("1"), names.get("2")
        oo = pin[mid].get("outcomes") or {}
        if not o1 or not o2 or o1 not in oo or o2 not in oo:
            continue
        t1, t2 = sh.at(sh.ticks(oo[o1]), start), sh.at(sh.ticks(oo[o2]), start)
        if not t1 or not t2:
            continue
        i1, i2 = 1 / t1[1], 1 / t2[1]
        age = (start - min(t1[0], t2[0])).total_seconds() / 60
        cand = (i1 / (i1 + i2), age)
        if best is None or cand[1] < best[1]:
            best = cand
    return best


def lane2(now, mkmap):
    """Lane 2 = SLOW-HR Type P moneyline sightings. Hard Rock shows the price (no fee). Close = Pinnacle's OWN moneyline
    no-vig at game start, recomputed here from the cached ticks (never the logger's stored value, only compared to it).
    Underdog = Hard Rock American price > 0. Rows without a verified own-market close are excluded and counted."""
    say("")
    say("LANE 2 (SLOW-HR Type P moneyline) - independent recalculation")
    try:
        sstate = tb.dec(json.load(open(sh.STATE)))
    except Exception as e:
        say(f"STOP-LANE2: cannot read slowhr/state.enc ({type(e).__name__})")
        return []
    S = sstate.get("sightings") or []
    say(f"sighting record field inventory: " + ", ".join(f"{k}:{n}" for k, n in sorted(Counter(k for x in S for k in x).items())))
    say(f"sightings stored {len(S)}; by kind/type: {dict(Counter((x.get('kind'), x.get('type')) for x in S))}")
    P = [x for x in S if x.get("kind") == "P" and x.get("type") == "moneyline"]
    rows, why = [], Counter()
    for x in P:
        r = {"day": str(x.get("start"))[:10], "league": x.get("league"), "game": x.get("game"), "kind": "P",
             "type": "moneyline", "side": x.get("side"), "team": x.get("team"), "hr_american": x.get("hr_am"),
             "hr_decimal": x.get("hr_price"), "late": x.get("late"), "mins_before": x.get("mins_before"),
             "stored_close_fair": x.get("close_fair")}
        rows.append(r)
        start = cl.tp(x.get("start"))
        fid = x.get("fixture")
        try:
            if not start or not fid or not x.get("hr_price"):
                raise KeyError("missing field")
            if not os.path.exists(hc._path(fid, "pinnacle")):
                raise _NoNetwork("Pinnacle close not in cache")
            h = hc.get_hist(fid, ["pinnacle"], start)
            pin = cl.book_markets(h, "pinnacle")
            c = _ml_close(pin, mkmap, x["league"], start)
            if not c:
                raise KeyError("no own-market moneyline close")
            p1, age = c
            pc = p1 if x.get("side") == "1" else 1 - p1
            r.update({"recomputed_close_fair": round(pc, 5), "close_tick_age_min": round(age, 1), "close_verified": 1,
                      "clv_pct": round(100 * (pc * x["hr_price"] - 1), 3)})
            if x.get("close_fair") is not None and abs(x["close_fair"] - pc) > 0.01:
                r["excluded_reason"] = "stored vs recomputed close differ >1pt (kept, flagged)"
                why["close differs from logger"] += 1
        except (KeyError, _NoNetwork) as e:
            r["excluded_reason"] = str(e)[:50]
            why[str(e)[:50]] += 1
    ok = [r for r in rows if r.get("clv_pct") is not None]
    say(f"Type P moneyline sightings {len(P)}; scored with verified own close {len(ok)}; exclusions {dict(why)}")

    def block(label, xs):
        by = {}
        for r in xs:
            by.setdefault((r["league"], r["game"]), []).append(r)
        first = [sorted(v, key=lambda r: -(r.get("mins_before") or 0))[0]["clv_pct"] for v in by.values()]
        say(ci_line(f"{label}: sightings", [r["clv_pct"] for r in xs]))
        say(ci_line(f"{label}: one per game (earliest)", first))
        return first
    J = [r for r in ok if not r["late"]]
    block("ALL not-late", J)
    D = [r for r in J if (r["hr_american"] or 0) > 0]
    first = block("UNDERDOGS (HR price > +100) not-late", D)
    block("underdogs, close tick <= 60 min old", [r for r in D if r["close_tick_age_min"] <= 60])
    days = sorted({r["day"] for r in D})
    if days:
        mid = days[(len(days) - 1) // 2]
        for lab, xs in ((f"FIT (<= {mid})", [r for r in D if r["day"] <= mid]), (f"CHECK (> {mid})", [r for r in D if r["day"] > mid])):
            g = {}
            for r in xs:          # unique games only: earliest sighting per game, never repeated sightings
                k = (r["league"], r["game"])
                if k not in g or (r.get("mins_before") or 0) > (g[k].get("mins_before") or 0):
                    g[k] = r
            say(ci_line(f"underdogs {lab}: UNIQUE GAMES", [r["clv_pct"] for r in g.values()]))
    say(f"  registered bar: >=100 distinct games, CLV>0 and beat-close>=53% in both halves; distinct underdog games here: {len({(r['league'], r['game']) for r in D})}")
    return rows


def main():
    now = datetime.now(timezone.utc)
    say("CLV FORENSIC - EXECUTED FILLS (read-only, cache-only, zero credits)")
    say(cs.stamp())
    # PREFLIGHT: prove the Actions cache restored. An empty cache is a stop, never a reason to fetch.
    hdir = hc.DIR
    pin_files = [x for x in (os.listdir(hdir) if os.path.isdir(hdir) else []) if x.endswith("__pinnacle.json.gz")]
    say(f"preflight: history cache dir {hdir!r} holds {len(pin_files)} Pinnacle files; "
        f"OddsPapi key present in env: {bool(cl.KEY or cl.FREE_KEY)} (must be False)")
    if cl.KEY or cl.FREE_KEY:
        say("STOP: an OddsPapi key is present. This audit must run without one.")
        return 2
    if not pin_files:
        say("STOP: the Pinnacle history cache did not restore (0 files). Nothing computed, nothing fetched.")
        try:
            send_csv("Bets CLV FORENSIC - STOPPED, cache not restored", "\n".join(L), [], "empty.csv")
        except Exception:
            pass
        return 3
    F, total = xc.fill_rows()
    say(f"tracker rows {total}; graded bot fills {len(F)}")
    inv = Counter(k for b in F for k, v in b.items() if v not in (None, ""))
    say("fill field inventory (name: rows present): " + ", ".join(f"{k}:{n}" for k, n in sorted(inv.items())))

    stt = {"fixtures": {}, "fx_last": {}}
    prev = cl.tb.dec(json.load(open(cl.STATE)))
    stt["fixtures"] = dict(prev.get("fixtures") or {})
    stt["fx_last"] = dict(prev.get("fx_last") or {})
    mkmap = (json.load(open(cl.MKFILE)).get("m") or {})      # from disk: load_markets() can BILL

    out = []
    for b in F:
        lg = b.get("league")
        gstart = (b.get("game_start") or b.get("settled") or b.get("placed") or b.get("first_seen"))
        q = {"bet": b.get("bet"), "league": lg, "game": b.get("game"), "teams": b.get("teams"),
             "game_start": gstart, "book": b.get("book"), "_start_was_given": bool(b.get("game_start"))}
        bk = cs.canon(b.get("book")) if b.get("book") else ""
        am = xc.num(b.get("price"))
        row = {"day": str(b.get("game_start") or "")[:10], "league": lg, "game": b.get("game"),
               "bet": b.get("bet"), "venue": bk, "fill_american": am, "result": b.get("result"),
               "fee_model": cs.FEE_MODEL, "net_clv_pct": None, "close_verified": 0}

        def drop(reason, row=row):
            row["excluded_reason"] = reason
            out.append(row)

        fid = cl.find_fixture(stt, q)
        if not fid:
            drop("no fixture matched")
            continue
        f = stt["fixtures"][fid]
        start = cl.tp(f.get("start")) or cl.tp(b.get("game_start"))
        if not start:
            drop("no game start")
            continue
        row["game_start_utc"] = start.isoformat()
        if now - start < hc.FINAL_AFTER:
            drop("game not final yet")
            continue
        if not os.path.exists(hc._path(fid, "pinnacle")):     # never fall through to a paid fetch
            drop("Pinnacle close not in cache")
            continue
        try:
            h = hc.get_hist(fid, ["pinnacle"], start)
        except _NoNetwork:
            drop("Pinnacle close not in cache")
            continue
        if isinstance(h, dict) and h.get("_error"):
            drop("history error")
            continue
        pin = cl.book_markets(h, "pinnacle")
        c, why = cl.close_for(q, f, pin, mkmap, start, lg)
        if not c:
            drop(f"no close ({str(why)[:40]})")
            continue
        try:
            nd = xc.net_of(bk, cl.am_to_dec(am), lg, False)
        except cs.UnknownVenue:
            drop("venue not in the registry")
            continue
        age = c.get("age_min")
        row.update({"fill_net_decimal": round(nd, 6), "close_how": c["how"],
                    "close_verified": int(cs.close_verified(c["how"])), "close_age_min": age,
                    "close_tick_utc": ((start - timedelta(minutes=age)).isoformat() if age is not None else ""),
                    "pin_close_prob": round(c["p"], 6),
                    "net_clv_pct": round(100 * (c["p"] * nd - 1), 3)})
        # entry-time fair price: read AT OR BEFORE the entry timestamp. close_for's 5th argument is only
        # the read cutoff, so passing the entry time reuses the same side/line/sign logic (no new matcher).
        et_raw, et_src = None, ""
        for k in ("placed", "decided_utc", "first_seen"):
            if b.get(k):
                et_raw, et_src = b.get(k), k
                break
        et = cl.tp(et_raw) if et_raw else None
        if et and et < start:
            ce, _ = cl.close_for(q, f, pin, mkmap, et, lg)
            row.update({"entry_time_utc": et.isoformat(), "entry_time_source": et_src})
            if ce:
                edge, mov, _ = split(ce["p"], c["p"], nd)
                row.update({"entry_how": ce["how"], "entry_age_min": ce.get("age_min"),
                            "pin_entry_fair_prob": round(ce["p"], 6),
                            "entry_edge_pct": edge, "pin_movement_pct": mov})
        out.append(row)

    scored = [r for r in out if r["net_clv_pct"] is not None]
    ver = [r for r in scored if r["close_verified"]]
    mod = [r for r in scored if not r["close_verified"]]
    say("")
    say("EXCLUSIONS: " + str(dict(Counter(r.get("excluded_reason") for r in out if r.get("excluded_reason")))))
    say(f"close read: {dict(Counter(r['close_how'].split(' ')[0] + (' (modelled)' if not r['close_verified'] else '') for r in scored))}")
    say("")
    say("HEADLINES (never mixed)")
    say(line("VERIFIED same-line closes only", summarize(ver)))
    say(line("MODELLED closes only (diagnostic, not CLV headline)", summarize(mod)))
    say(line("as executed_clv.py reports it (all of the above)", summarize(scored)))
    # split fills: one decision (league, game, bet, venue) can be filled in several pieces; each decision counts once
    # (equal-weight mean of its fills - no stakes are read or exported)
    grp = {}
    for r in ver:
        grp.setdefault((r["league"], r["game"], r["bet"], r["venue"]), []).append(r["net_clv_pct"])
    dec = [st.mean(v) for v in grp.values()]
    games = {(k[0], k[1]) for k in grp}
    say("")
    say(f"LANE 1 CORRECTED (verified same-line closes, fees once, split fills collapsed to one decision)")
    say(f"  verified fills {len(ver)} -> decisions {len(grp)} -> unique games {len(games)}; "
        f"fills with >1 piece: {sum(1 for v in grp.values() if len(v) > 1)}")
    say(ci_line("Lane 1 decisions, verified", dec))
    say(ci_line("Lane 1 decisions, verified, close <= 60 min old",
                [st.mean(x["net_clv_pct"] for x in ver if (x["league"], x["game"], x["bet"], x["venue"]) == k and (x["close_age_min"] or 0) <= 60)
                 for k in grp if any((x["league"], x["game"], x["bet"], x["venue"]) == k and (x["close_age_min"] or 0) <= 60 for x in ver)]))
    for r in ver:
        r["decision_key"] = "|".join(str(x) for x in (r["league"], r["game"], r["bet"], r["venue"]))
    say("")
    say("FRESHNESS SENSITIVITY (verified closes; registered rule unchanged at 24h)")
    for m in FRESH_STEPS:
        say(line(f"close tick no older than {m} min", summarize([r for r in ver if (r["close_age_min"] or 0) <= m])))
    say("")
    say("THREE-WAY SPLIT where an entry-time Pinnacle price exists (multiplicative, not additive)")
    sp = [r for r in ver if r.get("entry_edge_pct") is not None]
    say(f"  rows with entry-time Pinnacle read: {len(sp)} of {len(ver)}")
    if sp:
        say(f"  A. entry edge (net fill vs Pinnacle fair at entry)     mean {st.mean(r['entry_edge_pct'] for r in sp):+.2f}%")
        say(f"  B. Pinnacle fair-probability movement entry->close      mean {st.mean(r['pin_movement_pct'] for r in sp):+.2f}%")
        say(f"  C. net CLV on the same rows                             mean {st.mean(r['net_clv_pct'] for r in sp):+.2f}%")
    l2rows = lane2(now, mkmap)
    big = [r for r in scored if abs(r["net_clv_pct"]) > 10]
    say("")
    say(f"|CLV| > 10%: {len(big)} row(s), listed in the private CSV for manual classification")
    say(f"network guard refusals: {netguard.report() or 'none'}")
    print(f"clv forensic exec: fills {len(F)}, scored {len(scored)}, verified {len(ver)}, modelled {len(mod)}")
    try:
        send_csv("Bets CLV FORENSIC - executed fills (audit)", "\n".join(L), out,
                 f"clv_forensic_exec_{now:%Y%m%d_%H%M}.csv",
                 extra=[(f"lane2_{now:%Y%m%d_%H%M}.csv", L2COLS, l2rows)])
        print(f"per-row CSV sent: {len(out)} rows")
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


def _selftest():
    e, m, c = split(0.50, 0.55, 1.90)
    assert abs((1 + c / 100) - (1 + e / 100) * (1 + m / 100)) < 1e-3, (e, m, c)
    s = summarize([{"net_clv_pct": 2.0}, {"net_clv_pct": -12.0}, {"net_clv_pct": None}])
    assert s["n"] == 2 and s["big"] == 1 and s["beat"] == 1
    print("self-test ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        raise SystemExit(0)
    raise SystemExit(main())

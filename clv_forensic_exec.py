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


def line(label, s):
    if not s.get("n"):
        return f"  {label:46s} n 0"
    return (f"  {label:46s} n {s['n']:3d} | mean {s['mean']:+6.2f}% (se {s['se']:.2f}) | median "
            f"{s['median']:+6.2f}% | beat {s['beat']}/{s['n']} | |CLV|>10: {s['big']}")


def send_csv(subject, body, rows, filename):
    user, pw, to = ex.gmail()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, extrasaction="ignore")
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
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(m)


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
    big = [r for r in scored if abs(r["net_clv_pct"]) > 10]
    say("")
    say(f"|CLV| > 10%: {len(big)} row(s), listed in the private CSV for manual classification")
    say(f"network guard refusals: {netguard.report() or 'none'}")
    print(f"clv forensic exec: fills {len(F)}, scored {len(scored)}, verified {len(ver)}, modelled {len(mod)}")
    try:
        send_csv("Bets CLV FORENSIC - executed fills (audit)", "\n".join(L), out,
                 f"clv_forensic_exec_{now:%Y%m%d_%H%M}.csv")
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

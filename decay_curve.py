#!/usr/bin/env python3
"""
Price-decay curve (Nov 2, 2026; Peter + Muse). How much of a sharp alert's price is still there by the time the bot
decides, by delay bucket. PRIVATE result by email; the Actions log prints counts only. Read-only.

Source: every executor run email ("Bets LIVE:" subject) since Oct 26: its LEDGER rows give, per play,
alert_utc, run_start_utc, decided_utc, latency_s, alert_price_after_fee, px_best_after_fee (ProphetX best after fee
at the alert line, at decision), px_gettable, fill_price_after_fee. Joined to alerts.json (same play key + alert time)
for the close (close_fair_prob = no-vig closing probability of the alert side).

Per bucket (alert -> decision: <1 min, 1-5, 5-15, 15+): plays, wake and run medians, ProphetX cents lost
(implied prob at decision minus at alert, after fee, same line), % still gettable at the alert number or better,
% of decision prices still beating the close, and the record/units of the plays in that bucket.
"""
import json
import re
import statistics as st
from datetime import datetime, timezone

import executor as ex

SINCE = "26-Oct-2026"


def t(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None


def prob(a):
    if a in (None, 0):
        return None
    a = float(a)
    return -a / (-a + 100) if a < 0 else 100 / (a + 100)


def main():
    M = ex.imap_open()
    rows, seen = [], set()
    try:
        typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", SINCE)
        uids = data[0].split() if typ == "OK" and data and data[0] else []
        for uid in uids:
            typ, d = M.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not d or not d[0]:
                continue
            txt = ex.body_text(d[0][1])
            i = txt.rfind("LEDGER (machine-readable")
            if i < 0:
                continue
            try:
                led, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
            except Exception:
                continue
            for r in led:
                k = (r.get("key"), r.get("alert_utc"))
                if k in seen or not r.get("alert_utc") or not r.get("decided_utc"):
                    continue
                seen.add(k)   # first decision per play (catch-up reruns of the same play are not new decisions)
                rows.append(r)
    finally:
        M.logout()

    feed = json.load(open("alerts.json"))
    feed = feed if isinstance(feed, list) else feed.get("alerts")
    fk = {}
    for e in feed:
        k = ex.derive_key(e)
        if k:
            fk[(k, e.get("alert_utc"))] = e

    out = []
    for r in rows:
        a, rs, dc = t(r["alert_utc"]), t(r.get("run_start_utc")), t(r["decided_utc"])
        lat = (dc - a).total_seconds()
        e = fk.get((r.get("key"), r.get("alert_utc"))) or {}
        pa, pd = prob(r.get("alert_price_after_fee")), prob(r.get("px_best_after_fee"))
        close = e.get("close_fair_prob")
        out.append({"lat": lat, "wake": (rs - a).total_seconds() if rs else None, "run": (dc - rs).total_seconds() if rs else None,
                    # same book only: ProphetX-priced alerts (otherwise the gap is book-vs-book, not time)
                    "cents": (pd - pa) * 100 if pa is not None and pd is not None and r.get("alert_book") == "prophetx" else None,
                    "gettable": bool(r.get("px_gettable")),
                    "beats_close": (pd < close) if pd is not None and isinstance(close, (int, float)) else None,
                    "alert_beats_close": (pa < close) if pa is not None and isinstance(close, (int, float)) else None,
                    "result": e.get("result"), "units": e.get("units_flat"), "live": bool(r.get("live")),
                    "verdict": r.get("verdict"), "book": r.get("alert_book"), "pd": pd, "pa": pa, "joined": bool(e),
                    "pf": prob(r.get("fill_price_after_fee")), "fbook": r.get("fill_book"), "close": close})

    def med(xs):
        xs = [x for x in xs if x is not None]
        return f"{st.median(xs):.0f}s" if xs else "-"

    def pct(xs):
        xs = [x for x in xs if x is not None]
        return f"{100 * sum(xs) / len(xs):.0f}% (n={len(xs)})" if xs else "-"

    def block(name, L):
        c = [x["cents"] for x in L if x["cents"] is not None]
        g = [x for x in L if x["result"] in ("W", "L")]
        w = sum(x["result"] == "W" for x in g)
        u = sum(x["units"] or 0 for x in g)
        return (f"{name:<14} plays {len(L):>3} | wake med {med([x['wake'] for x in L])}, run med {med([x['run'] for x in L])} | "
                f"PX cents lost avg {st.mean(c):+.1f}c med {st.median(c):+.1f}c (n={len(c)}) | " if c else
                f"{name:<14} plays {len(L):>3} | wake med {med([x['wake'] for x in L])}, run med {med([x['run'] for x in L])} | PX cents lost - | ") + \
               (f"still gettable {pct([x['gettable'] for x in L])} | decision beats close {pct([x['beats_close'] for x in L])} "
                f"(alert beat close {pct([x['alert_beats_close'] for x in L])}) | record {w}-{len(g) - w} {u:+.2f}u")

    B = [("<1 min", 0, 60), ("1-5 min", 60, 300), ("5-15 min", 300, 900), ("15+ min", 900, 10 ** 9)]
    lines = [f"PRICE-DECAY CURVE (alert -> bot decision), executor ledgers since Oct 26, built "
             f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             "Stream: sharp feed plays the executor decided on (all verdicts). Basis: ProphetX after fee, alert line.",
             "Cents lost = ProphetX implied prob at decision minus at alert (positive = price got worse); ProphetX-priced alerts only.",
             "Beats close = decision price implied prob below the no-vig closing prob of that side.", ""]
    for name, lo, hi in B:
        lines.append(block(name, [x for x in out if lo <= x["lat"] < hi]))
    lines += ["", block("ALL", out), "", "Phase-1 LIVE-eligible plays only:"]
    for name, lo, hi in B:
        lines.append(block(name, [x for x in out if x["live"] and lo <= x["lat"] < hi]))
    lines += ["", f"Joined to the feed for close/result: {sum(1 for x in out if x['result'] or x['beats_close'] is not None)} of {len(out)}."]

    # v2 checks (Nov 2, Peter: fix the cents read, matched subset, reconcile latency)
    def q(xs, f):
        xs = sorted(x for x in xs if x is not None)
        return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None
    lt = [x["lat"] for x in out]
    lines += ["", "LATENCY DISTRIBUTION (alert -> decision, first decision per play):",
              f"  n {len(lt)} | median {q(lt, .5):.0f}s | mean {st.mean(lt):.0f}s | p75 {q(lt, .75):.0f}s | p90 {q(lt, .9):.0f}s | max {max(lt):.0f}s"
              if lt else "  none"]
    m = [x for x in out if x["beats_close"] is not None and x["alert_beats_close"] is not None]
    lines += ["", "MATCHED SUBSET (same plays have alert price, ProphetX decision price and close):",
              f"  n {len(m)} | alert beats close {pct([x['alert_beats_close'] for x in m])} | decision beats close {pct([x['beats_close'] for x in m])}",
              f"  both beat {sum(x['alert_beats_close'] and x['beats_close'] for x in m)} | alert only {sum(x['alert_beats_close'] and not x['beats_close'] for x in m)}"
              f" | decision only {sum(x['beats_close'] and not x['alert_beats_close'] for x in m)} | neither {sum(not x['alert_beats_close'] and not x['beats_close'] for x in m)}"]
    for lab, cond in (("  ProphetX-priced alerts", lambda x: x["book"] == "prophetx"), ("  other-book alerts", lambda x: x["book"] != "prophetx")):
        mm = [x for x in m if cond(x)]
        lines.append(f"{lab}: n {len(mm)} | alert beats close {pct([x['alert_beats_close'] for x in mm])} | decision beats close {pct([x['beats_close'] for x in mm])}")
    c = [x["cents"] for x in out if x["cents"] is not None]
    lines += ["", "PROPHETX CENTS CHECK (ProphetX-priced alerts; decision price is a live read at decision time):",
              f"  n {len(c)} | worse {sum(v > 0.05 for v in c)} | same {sum(abs(v) <= 0.05 for v in c)} | better {sum(v < -0.05 for v in c)}"
              + (f" | min {min(c):+.1f}c max {max(c):+.1f}c" if c else "")]
    lines.append("  No ProphetX decision price: " + str(sum(1 for x in out if x["pd"] is None)) + f" of {len(out)} (book not listing the alert line at decision).")

    # v3 (Nov 2, Muse challenge): tails per bucket, gettable by alert book, unjoined by bucket, phase-1 matched, fill vs close
    lines += ["", "V3 CHECKS (Muse Nov 2 challenge):", "Tails per bucket (p90 wake / p90 alert->decision):"]
    for name, lo, hi in B:
        L = [x for x in out if lo <= x["lat"] < hi]
        w9, l9 = q([x["wake"] for x in L], .9), q([x["lat"] for x in L], .9)
        lines.append(f"  {name:<9} n {len(L):>3} | p90 wake {'-' if w9 is None else f'{w9:.0f}s'} | p90 decision {'-' if l9 is None else f'{l9:.0f}s'}"
                     f" | ProphetX-priced alerts {sum(x['book'] == 'prophetx' for x in L)} | unjoined {sum(not x['joined'] for x in L)}"
                     f" | no ProphetX price {sum(x['pd'] is None for x in L)}")
    lines.append("Still gettable by alert book (ProphetX at the alert price or better at decision):")
    for name, lo, hi in B:
        L = [x for x in out if lo <= x["lat"] < hi]
        lines.append(f"  {name:<9} ProphetX-priced {pct([x['gettable'] for x in L if x['book'] == 'prophetx'])} | "
                     f"other-book {pct([x['gettable'] for x in L if x['book'] != 'prophetx'])}")
    m1 = [x for x in m if x["live"]]
    lines.append(f"Phase-1 matched: n {len(m1)} | alert beats close {pct([x['alert_beats_close'] for x in m1])} | "
                 f"decision beats close {pct([x['beats_close'] for x in m1])}")
    f = [x for x in out if x["pf"] is not None and isinstance(x["close"], (int, float))]
    lines.append(f"Actual fills vs close (fill price after fee, any book): n {len(f)} | fill beats close {pct([x['pf'] < x['close'] for x in f])} | "
                 f"alert beat close on the same plays {pct([x['pa'] < x['close'] for x in f if x.get('pa') is not None])}")
    lines.append("  fills by book: " + ", ".join(f"{b} {sum(x['fbook'] == b for x in f)}" for b in sorted({x['fbook'] for x in f if x['fbook']})))
    ex.send("Bets DECAY CURVE (alert -> decision)", "\n".join(lines))
    print(f"Decay curve emailed: {len(out)} decisions read")   # counts only


if __name__ == "__main__":
    main()

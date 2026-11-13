#!/usr/bin/env python3
"""DAILY LAST-50 REPORT - deterministic, no model in the loop (Peter, 13 Nov).

For every test whose per-play records are readable in this repo, take the LAST 50 graded plays
(one play = game + market + side, first alert only), split 25 older / 25 newer, and report units,
ROI, standardized CLV and n for each half and overall. CLV is the ONE adopted basis only:
(Pinnacle no-vig close prob x net entry decimal AFTER FEES - 1) x 100, via clv_scorecard.std_clv
and clv_std. No stored CLV field is read. Rows without a usable close are EXCLUDED AND COUNTED,
never substituted. Where a test has no standard CLV the CLV cell says "n/a" and the test cannot
be called a pass.

Read-only: no bet, no rule, no threshold, no registry change. Flat 1u at the logged price, so
the output carries units and percentages only - no dollars, stakes or balances.
Tests whose data is not in these files are listed UNANSWERED with the reason.

Verdict ladder (policy of 11 Nov): n < 50 -> NO VERDICT. Else CLEAR FAIL only if the units CI sits
below zero; POTENTIAL PASS only if both halves are positive on units AND on certified CLV AND the
units CI sits above zero; everything else CONTINUE TESTING. A 50-play window is noisy, so every
units figure prints its 95% CI.
"""
import csv
import io
import json
import os
import random
import re
import statistics as st
import sys
from collections import Counter

import clv_scorecard as sc

N = 50
SEED = 20261113
L = []


def say(t=""):
    L.append(t)
    print(t)


def load(p):
    try:
        d = json.load(open(p))
    except Exception:
        return None
    if isinstance(d, list):
        return d
    for k in ("alerts", "bets"):
        if isinstance(d, dict) and isinstance(d.get(k), list):
            return d[k]
    return d


def am_from_prob(p):
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    if not 0 < p < 1:
        return None
    return round(100 * (1 - p) / p) if p < 0.5 else -round(100 * p / (1 - p))


def unit_of(am, res):
    if am is None or res not in ("W", "L"):
        return None
    return (am / 100 if am > 0 else 100 / abs(am)) if res == "W" else -1.0


def ci_mean(xs):
    """95% bootstrap CI of the mean, seeded so the same data prints the same interval."""
    if len(xs) < 2:
        return None
    rnd = random.Random(SEED)
    ms = sorted(st.mean(rnd.choices(xs, k=len(xs))) for _ in range(2000))
    return ms[50], ms[1949]


def window(rows):
    """Dedupe to one play per key (first alert), order by time, keep the last N graded."""
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: r["ts"]):
        if r["res"] not in ("W", "L", "P") or r["key"] in seen:
            continue
        seen.add(r["key"])
        out.append(r)
    return out[-N:], len(out)


def half_stats(xs):
    graded = [r for r in xs if r["res"] in ("W", "L")]
    us = [unit_of(r["am"], r["res"]) for r in graded]
    us = [u for u in us if u is not None]
    clvs = [r["clv"] for r in xs if r["clv"] is not None]
    return {"n": len(xs), "w": sum(1 for r in xs if r["res"] == "W"),
            "l": sum(1 for r in xs if r["res"] == "L"), "units": sum(us),
            "roi": (100 * sum(us) / len(us)) if us else None, "us": us,
            "clv": st.mean(clvs) if clvs else None, "clv_n": len(clvs)}


def fmt(h):
    roi = "n/a" if h["roi"] is None else f"{h['roi']:+.1f}%"
    clv = "n/a" if h["clv"] is None else f"{h['clv']:+.2f}% (n {h['clv_n']})"
    return f"n {h['n']:2d} | {h['w']}-{h['l']} | {h['units']:+6.2f}u | ROI {roi} | CLV {clv}"


def verdict(w, h1, h2, ho):
    if len(w) < N:
        return "NO VERDICT (n<50)"
    ci = ci_mean(ho["us"])
    if ci and ci[1] < 0:
        return "CLEAR FAIL"
    clv_ok = all(h["clv"] is not None and h["clv"] > 0 and h["clv_n"] >= 0.8 * h["n"] for h in (h1, h2))
    if ci and ci[0] > 0 and h1["units"] > 0 and h2["units"] > 0 and clv_ok:
        return "POTENTIAL PASS"
    return "CONTINUE TESTING"


def report(name, rows, note="", frozen=False):
    """One block per test. Returns (status, csv rows)."""
    w, total = window(rows)
    say("")
    say(f"{name}" + ("   [FROZEN - closed test, read-only regrade]" if frozen else ""))
    if note:
        say(f"  {note}")
    if not w:
        say("  UNANSWERED: no graded plays in the data this report can read")
        return "UNANSWERED", []
    h = len(w) // 2
    h1, h2, ho = half_stats(w[:h]), half_stats(w[h:]), half_stats(w)
    ci = ci_mean(ho["us"])
    say(f"  window: last {len(w)} of {total} graded plays | {w[0]['ts'][:10]} to {w[-1]['ts'][:10]}")
    say(f"  H1 (older)   {fmt(h1)}")
    say(f"  H2 (newer)   {fmt(h2)}")
    say(f"  OVERALL      {fmt(ho)}")
    if ci:
        say(f"  per-play units 95% CI [{ci[0]:+.2f}, {ci[1]:+.2f}] (n {len(ho['us'])})")
    v = verdict(w, h1, h2, ho)
    full = ho["clv"] is not None and ho["clv_n"] >= 0.8 * ho["n"]
    status = "ANSWERED" if len(w) >= N and full else "PARTIAL"
    say(f"  STATUS {status} | VERDICT {v}")
    if ho["clv"] is None:
        say("  CLV: n/a - no standard (Pinnacle same-line, after-fee) close on these rows; cannot pass")
    elif ho["clv_n"] < ho["n"]:
        say(f"  CLV coverage {ho['clv_n']}/{ho['n']} rows usable; the rest are EXCLUDED, not estimated")
    out = [{"test": name, "half": "H1" if i < h else "H2", "ts": r["ts"], "game": r["game"],
            "price_am": r["am"], "result": r["res"], "std_clv_pct": ("" if r["clv"] is None else round(r["clv"], 3))}
           for i, r in enumerate(w)]
    return status, out


# --------------------------------------------------------------------------- populations
def sharp_rows():
    S = load("alerts.json") or []
    rows = []
    for x in S:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P"):
            continue
        am = x.get("price_after_fee") if x.get("price_after_fee") is not None else x.get("price")
        c = sc.std_clv(x.get("close_fair_prob"), am, x.get("book_key"))
        g = frozenset(sc.toks(x.get("game")))
        rows.append({"ts": str(x.get("alert_utc") or ""), "game": x.get("game") or "", "am": am,
                     "res": x["result"], "clv": c, "sent": bool(x.get("sent_to_phone")),
                     "lg": x.get("sport"), "kind": x.get("kind"), "bet": str(x.get("bet") or ""),
                     "key": (str(x.get("alert_utc") or "")[:10], g, str(x.get("kind")), str(x.get("bet") or ""))})
    return rows


def liq_rows():
    Q = load("liquidity/alerts.json") or []
    rows = []
    for x in Q:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or x.get("artifact") or x.get("close_suspect"):
            continue
        am = x.get("price_american")
        c = sc.std_clv(x.get("close_price"), am, x.get("book"))
        rows.append({"ts": str(x.get("alerted_utc") or ""), "game": x.get("game") or "", "am": am,
                     "res": x["result"], "clv": c, "lg": x.get("league"), "mk": x.get("market"),
                     "side": x.get("side"), "book": x.get("book"), "lead": x.get("lead_min"),
                     "nm": x.get("new_money"),
                     "key": (str(x.get("alerted_utc") or "")[:10], frozenset(sc.toks(x.get("game"))),
                             x.get("market"), x.get("side"))})
    return rows


def lane_rows(name):
    d = (load("lanes/lanes.json") or {}).get(name) or {}
    rows = []
    for k, x in d.items():
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or not x.get("entered"):
            continue
        am = am_from_prob(x.get("price"))
        rows.append({"ts": str(x.get("snapshot_utc") or x.get("detected_utc") or ""), "game": x.get("game") or "",
                     "am": am, "res": x["result"], "clv": None,
                     "key": (str(x.get("start_utc") or "")[:10], frozenset(sc.toks(x.get("game"))),
                             x.get("market"), x.get("side") or x.get("pulled_side"))})
    return rows


def board_rows():
    d = (load("board/calls.json") or {}).get("calls") or {}
    rows = []
    for k, x in d.items():
        if x.get("call") != "PLAY" or x.get("result") not in ("W", "L", "P"):
            continue
        rows.append({"ts": str(x.get("at") or ""), "game": x.get("game") or "", "am": x.get("price"),
                     "res": x["result"], "clv": None,
                     "key": (x.get("day"), frozenset(sc.toks(x.get("game"))), x.get("mk"), x.get("side"))})
    return rows


def registry_names():
    out = {}
    try:
        for ln in open("REGISTRY.md"):
            m = re.match(r"\|\s*(\d+)\s*\|\s*\*\*(.+?)\*\*", ln)
            if m:
                out[int(m.group(1))] = m.group(2).strip()
    except OSError:
        pass
    return out


def send_csv(subject, body, rows):
    try:
        import executor as ex
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import smtplib
        user, pw, to = ex.gmail()
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
        return
    buf = io.StringIO()
    cols = ["test", "half", "ts", "game", "price_am", "result", "std_clv_pct"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    m = MIMEMultipart()
    m["Subject"], m["From"], m["To"] = subject, user, to
    m.attach(MIMEText(body, "plain", "utf-8"))
    part = MIMEBase("text", "csv")
    part.set_payload(buf.getvalue().encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename="last50_plays.csv")
    m.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=120) as sv:
        sv.login(user, pw)
        sv.sendmail(user, [to], m.as_string())


def main():
    say("VALUE LAB - LAST-50 REPORT (deterministic; no model computed these numbers)")
    say(sc.cs.stamp())
    say("CLV BASIS: Pinnacle no-vig close, same line, net of fees (CLV_STANDARD.md). Circa close is")
    say("NOT in this report yet (circa_close data is not read here) - see OPEN ITEMS.")
    say("Window: last 50 graded plays per test, one play per game+market+side, 25 older / 25 newer.")
    say("Flat 1u at the logged price. No dollars. Fills are never assumed.")

    status, csv_rows = {}, []

    def run(label, rows, note="", frozen=False):
        s, o = report(label, rows, note, frozen)
        status[label] = s
        csv_rows.extend(o)

    S = sharp_rows()
    run("SHARP ALERTS - all graded", S, "population the feed draws on; not any one lane")
    run("SHARP ALERTS - sent to phone", [r for r in S if r["sent"]])
    run("SHARP ALERTS - NBA unders", [r for r in S if r["lg"] == "NBA" and "under" in r["bet"].lower()],
        "PROXY for Lane 1's market only - Lane 1's real fills are not in this repo (see OPEN ITEMS)")
    Q = liq_rows()
    run("LIQ - NBA UNDER, Kalshi-triggered", [r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                              and r["side"] == "UNDER" and r["book"] == "kalshi"],
        "bettable venue only; Polymarket GLOBAL rows are excluded by venue")
    run("LIQ-BOT (reg 9) - NBA totals, 4h+ lead", [r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                   and r["lead"] is not None and r["lead"] >= 240])
    run("LIQ-SMALL (reg 13) - NBA totals, $25-50k prints", [r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                            and r["nm"] is not None and 25000 <= r["nm"] <= 50000])
    run("PULL_FADE (reg 25)", lane_rows("pull_fade"), "paper lane; price is the logged probability")
    run("SOLO (reg 26)", lane_rows("solo"), "paper lane; price is the logged probability")
    run("BETS BOARD PLAYS (reg 7)", board_rows(), "PLAY calls only; frozen call log")

    reg = registry_names()
    covered = {7, 9, 13, 25, 26}
    say("")
    say("=" * 100)
    say("UNANSWERED - registered tests this report cannot grade from the repo files")
    say("=" * 100)
    for n, name in sorted(reg.items()):
        if n in covered:
            continue
        say(f"  #{n:>2} {name} - per-play record is not in a file this report reads "
            f"(encrypted state, bot ledger email, or its own run output)")
    say("")
    say("OPEN ITEMS (carried until answered or you close them)")
    say("  1. Lane 1 / R1 / Board live fills: executed results are in the executor ledger email, not the repo.")
    say("  2. Encrypted per-play CLV (clv/state.enc, tracker, slowhr): needs TRACKER_PASSPHRASE in the run.")
    say("  3. Circa close: not yet included; Pinnacle only until circa_close data is wired in.")
    say("  4. Lane rows and Board PLAYs have no standard CLV here, so they can reach CONTINUE TESTING at best.")
    say("  5. Tests with a rule change need their change-point date; none is flagged automatically yet.")
    say("")
    say("SUMMARY: " + ", ".join(f"{k}: {v}" for k, v in Counter(status.values()).items()))
    send_csv("VALUE LAB last-50 report", "\n".join(L), csv_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())

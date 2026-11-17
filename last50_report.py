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
    if os.environ.get("LAST50_PRINT") == "1":   # public Actions log: counts only, so print only when asked locally
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
    clvs = [r["clv"] for r in xs if r.get("clv") is not None]
    ex = [r for r in xs if r.get("us_exec", True)]          # s7 operational population (all rows when unmarked)
    ex_g = [r for r in ex if r["res"] in ("W", "L")]
    ex_u = [u for u in (unit_of(r["am"], r["res"]) for r in ex_g) if u is not None]
    pcl = [r["pclv"] for r in xs if r.get("pclv") is not None]
    return {"n": len(xs), "w": sum(1 for r in xs if r["res"] == "W"),
            "l": sum(1 for r in xs if r["res"] == "L"), "units": sum(us),
            "roi": (100 * sum(us) / len(us)) if us else None, "us": us,
            "clv": st.mean(clvs) if clvs else None, "clv_n": len(clvs), "clv_ci": ci_mean(clvs),
            "clv_pos_pct": (100 * sum(1 for c in clvs if c > 0) / len(clvs)) if clvs else None,
            "pclv": st.mean(pcl) if pcl else None, "pclv_n": len(pcl),
            "exec_n": len(ex), "exec_w": sum(1 for r in ex if r["res"] == "W"), "exec_l": sum(1 for r in ex if r["res"] == "L"),
            "exec_units": sum(ex_u), "exec_roi": (100 * sum(ex_u) / len(ex_u)) if ex_u else None,
            "pclv_src": next((r.get("pclv_src") for r in xs if r.get("pclv") is not None), None)}


def fmt(h):
    roi = "n/a" if h["roi"] is None else f"{h['roi']:+.1f}%"
    clv = "n/a" if h["clv"] is None else (f"{h['clv']:+.2f}% (n {h['clv_n']}, beat close {h['clv_pos_pct']:.0f}%"
                                          + (f", 95% CI [{h['clv_ci'][0]:+.2f}, {h['clv_ci'][1]:+.2f}]" if h.get("clv_ci") else "") + ")")
    if h.get("exec_n") is not None and h["exec_n"] != h["n"]:
        clv += (f" | coverage {h['clv_n']}/{h['exec_n']} US-executable, {h['clv_n']}/{h['n']} whole population"
                f" | executable subset {h['exec_w']}-{h['exec_l']} {h['exec_units']:+.2f}u")
    pv = "" if not h.get("pclv_n") else f" | provisional, NOT certified: {h['pclv']:+.2f}% (n {h['pclv_n']})"
    return f"n {h['n']:2d} | {h['w']}-{h['l']} | {h['units']:+6.2f}u | ROI {roi} | CERTIFIED CLV {clv}{pv}"


def verdict(w, h1, h2, ho):
    if len(w) < N:
        return "NO VERDICT (n<50)"
    ci = ci_mean(ho["us"])
    if ci and ci[1] < 0:
        return "CLEAR FAIL"
    den = ho.get("exec_n", ho["n"])   # CLV_STANDARD.md s7 (14 Nov): eligible US-executable rows are the denominator
    if ho["clv_n"] < 0.8 * den:
        # without certified CLV on 80%+ of the executable window there is nothing to qualify on
        return f"INSUFFICIENT EVIDENCE (certified CLV {ho['clv_n']}/{den} executable, {ho['clv_n']}/{ho['n']} all)"
    cc = ho.get("clv_ci")
    if cc and cc[1] < 0:
        # SCORECARD.md: CLEAR FAIL also on "a precise and representative certified-CLV CI excluding zero negative"
        # (representative = certified on 80%+ of the EXECUTABLE window, s7, checked above)
        return f"CLEAR FAIL (certified CLV 95% CI {cc[0]:+.2f} to {cc[1]:+.2f}, below zero)"
    clv_ok = all(h["clv"] is not None and h["clv"] > 0 and h["clv_n"] >= 0.8 * h.get("exec_n", h["n"]) for h in (h1, h2))
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
    full = ho["clv"] is not None and ho["clv_n"] >= 0.8 * ho.get("exec_n", ho["n"])
    status = "ANSWERED" if len(w) >= N and full else "PARTIAL"
    say(f"  STATUS {status} | VERDICT {v} | CONFIDENCE {confidence(ho['n'], ho['clv_n'], ho.get('exec_n'))}")
    if ho["clv"] is None:
        say("  CLV: n/a - no standard (Pinnacle same-line, after-fee) close on these rows; cannot pass")
    elif ho["clv_n"] < ho["n"]:
        say(f"  CLV coverage {ho['clv_n']}/{ho['n']} rows usable; the rest are EXCLUDED, not estimated")
    out = [{"test": name, "half": "H1" if i < h else "H2", "ts": r["ts"], "game": r["game"],
            "price_am": r["am"], "result": r["res"], "certified_clv_pct": ("" if r["clv"] is None else round(r["clv"], 3)),
            "provisional_clv_pct_not_certified": ("" if r.get("pclv") is None else round(r["pclv"], 3)),
            "provisional_source": r.get("pclv_src") or ""}
           for i, r in enumerate(w)]
    return status, out


# --------------------------------------------------------------------------- populations
# 16 Nov (Peter): "clv" on a row is CERTIFIED Pinnacle CLV only. Anything else lives in "pclv", labelled by source,
# and never reaches a CLV heading, a verdict or a confidence grade.
PROV_ALERT = "provisional: live feed read 5-30 min before start, line not verified (clv_verified False)"
PROV_VENUE = "not Pinnacle: the alerting venue's own last pregame price"


def liq_certified(rows, path="liquidity/clv_certified.json"):
    """16 Nov: certified Pinnacle CLV from liq_clv_certify (cache-only, clv_obs_audit waterfall) onto LIQ rows.
    Applied ONLY to LIQ-SMALL and LIQ-BOT. A row without a certified entry keeps clv None; its venue close stays
    in pclv, labelled. Returns new row dicts; the inputs and their W-L/units are untouched."""
    try:
        cert = (json.load(open(path)) or {}).get("certified") or {}
    except (OSError, ValueError):
        cert = {}
    try:
        rej = (json.load(open(path)) or {}).get("rejected") or {}
    except (OSError, ValueError):
        rej = {}
    out = []
    for r in rows:
        c = cert.get(r.get("aid") or "")
        o = dict(r, clv=c["clv_pct"]) if c and c.get("clv_pct") is not None else dict(r)
        # CLV_STANDARD.md s7: a venue that cannot be bet from the US is outside the operational denominator.
        # ONLY that exact class; a missing close on an executable venue stays in as a genuine gap.
        why = str(rej.get(r.get("aid") or "") or "")
        o["us_exec"] = not (why.startswith("VENUE_NOT_PRICEABLE") and "not tradeable from the US" in why)
        out.append(o)
    return out


def sharp_rows():
    S = load("alerts.json") or []
    rows = []
    for x in S:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P"):
            continue
        am = x.get("price_after_fee") if x.get("price_after_fee") is not None else x.get("price")
        c = sc.std_clv(x.get("close_fair_prob"), am, x.get("book_key"))
        cert = x.get("clv_verified") is True     # 16 Nov: the writer marks a live feed read PROVISIONAL (False)
        g = frozenset(sc.toks(x.get("game")))
        rows.append({"ts": str(x.get("alert_utc") or ""), "game": x.get("game") or "", "am": am,
                     "res": x["result"], "clv": c if cert else None, "pclv": None if cert else c,
                     "pclv_src": PROV_ALERT, "sent": bool(x.get("sent_to_phone")),
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
        # 16 Nov: close_price is the ALERTING VENUE'S own last pregame price (liquidity_monitor), not Pinnacle.
        rows.append({"ts": str(x.get("alerted_utc") or ""), "game": x.get("game") or "", "am": am,
                     "res": x["result"], "clv": None, "pclv": c, "pclv_src": PROV_VENUE,
                     "aid": f"{x.get('key')}|{x.get('alerted_utc')}",
                     "lg": x.get("league"), "mk": x.get("market"),
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


def board_rows(field="call"):
    """field="call" = the live v3 call; field="v2" = the superseded v2 call, which keeps grading (reg 14)."""
    d = (load("board/calls.json") or {}).get("calls") or {}
    try:   # Nov 17: grade late-finishing calls from the full feeds (same fix the board build now applies)
        import board_build as _bb
        _bb.backfill_results(d, _bb.load())
    except Exception:
        pass
    rows = []
    for k, x in d.items():
        if x.get(field) != "PLAY" or x.get("result") not in ("W", "L", "P"):
            continue
        rows.append({"ts": str(x.get("at") or ""), "game": x.get("game") or "", "am": x.get("price"),
                     "res": x["result"], "clv": None, "aid": k,   # aid = the source liquidity alert id (key|alerted_utc)
                     "key": (x.get("day"), frozenset(sc.toks(x.get("game"))), x.get("mk"), x.get("side"))})
    return rows


EXCH = ("prophetx", "novig", "kalshi", "polymarket_us", "polymarket.us")
T18 = "2026-11-03T16:45:00Z"   # EDGE2 clock (paper_rules T60); reg 18 is its SENT exchange subset


def misprice_rows():
    """Reg 18 EXCHANGE MISPRICE: a SENT alert priced at an exchange, stated edge_pct >= +2 vs Pinnacle fair after fee,
    bettable pricing only (Polymarket Global is refused), from the EDGE2 clock. Read-only over alerts.json."""
    S = load("alerts.json") or []
    rows = []
    for x in S:
        if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or not x.get("sent_to_phone"):
            continue
        if str(x.get("book_key") or "").lower() not in EXCH or x.get("pricing_bettable") is False:
            continue
        try:
            if float(x.get("edge_pct")) < 2:
                continue
        except (TypeError, ValueError):
            continue
        if str(x.get("alert_utc") or "") < T18:
            continue
        am = x.get("price_after_fee") if x.get("price_after_fee") is not None else x.get("price")
        c_ = sc.std_clv(x.get("close_fair_prob"), am, x.get("book_key"))
        cert = x.get("clv_verified") is True
        rows.append({"ts": str(x.get("alert_utc") or ""), "game": x.get("game") or "", "am": am, "res": x["result"],
                     "clv": c_ if cert else None, "pclv": None if cert else c_, "pclv_src": PROV_ALERT,
                     "key": (str(x.get("alert_utc") or "")[:10], frozenset(sc.toks(x.get("game"))),
                             str(x.get("kind")), str(x.get("bet") or ""))})
    return rows


# --------------------------------------------------------------------------- live (reporting ledger)
def live_rows(acct, lane):
    """One row per LIVE BOT PLAY with a confirmed fill and a settled result (live_ledger.account)."""
    return [{"ts": p["t"], "game": p["key"].split("|")[1] if "|" in p["key"] else p["key"], "am": p["am_net"],
             "res": p["res"], "clv": p["clv"], "key": p["key"]}
            for p in acct["plays"] if p["lane"] == lane and p["res"] in ("W", "L", "P") and p["am_net"] is not None]


def manual_rows(acct, src):
    return [{"ts": m["t"], "game": f"{m['game']} - {m['bet']}", "am": m["am"], "res": m["res"], "clv": m["clv"],
             "key": tuple(sorted(m["rows"]))}
            for m in acct["manual"] if m["src"] == src and m["res"] in ("W", "L", "P") and m["am"] is not None]


# --------------------------------------------------------------------------- SLOW-HR / DOG BAND (paper)
SLOWHR_EV_MIN = 2.0                      # slowhr_cell.EV_MIN - the registered cell
DOG_BAND_FROM = "2026-11-07T05:00:00Z"   # REGISTRY 12: forward from 7 Nov (ET)


def slowhr_rows(dog_band=False):
    """SLOW-HR (#11) registered cell: Type P x moneyline x Hard Rock underdog (price > 0) x EV >= +2% x not LATE, first
    sighting per event + market + side (slowhr_cell rules), graded 1u at the Hard Rock price on ESPN finals.
    DOG BAND (#12): the same cell, +100 to +299 only, from 7 Nov. Paper. None if the state cannot be decrypted."""
    if not os.environ.get("TRACKER_PASSPHRASE"):
        return None
    try:
        import tracker_build as tb
        S = (tb.dec(json.load(open("slowhr/state.enc"))) or {}).get("sightings") or []
        import finals as fin
    except Exception as e:
        print(f"slowhr not readable ({type(e).__name__})")
        return None
    first = {}
    for x in sorted(S, key=lambda z: str(z.get("t_move") or "")):
        am = x.get("hr_am")
        if not (x.get("kind") == "P" and x.get("type") == "moneyline" and am is not None and am > 0
                and x.get("ev_pct") is not None and x["ev_pct"] >= SLOWHR_EV_MIN and not x.get("late")):
            continue
        if dog_band and not (100 <= am <= 299 and str(x.get("t_confirm") or "") >= DOG_BAND_FROM):
            continue
        day = str(x.get("start") or "")[:10]
        ev = (x.get("league"), day, frozenset(sc.toks(x.get("game"))), x.get("type"), str(x.get("side")))
        first.setdefault(ev, x)
    rows = []
    for k, x in first.items():
        try:
            res = fin.result(x)
        except Exception:
            res = None
        if res is None:
            continue
        cf = x.get("close_fair")
        clv = None if cf is None or not x.get("hr_price") else 100 * (float(cf) * float(x["hr_price"]) - 1)
        rows.append({"ts": str(x.get("t_confirm") or x.get("t_move") or ""), "game": f"{x.get('game')} - {x.get('team')}",
                     "am": x["hr_am"], "res": res, "clv": None, "pclv": clv,   # 16 Nov: no certification record
                     "pclv_src": "SLOW-HR close_fair: no certification record", "key": k})
    return rows


def confidence(n, clv_n, exec_n=None):
    """Stated rule: HIGH = 50 plays and certified CLV on 80%+; MEDIUM = 25+ plays and CLV on 50%+; else LOW.
    Coverage is against eligible US-executable rows (CLV_STANDARD.md s7) when the caller knows them."""
    den = exec_n if exec_n is not None else n
    cov = (clv_n / den) if den else 0
    if n >= 50 and cov >= 0.8:
        return "HIGH"
    if n >= 25 and cov >= 0.5:
        return "MEDIUM"
    return "LOW"


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


def send_telegram(body, rows):
    """Private Telegram delivery (Peter, 13 Nov: no Gmail). Text in 4000-char chunks, then the CSV as a
    document - a CSV cannot be half-valid the way truncated text can. Nothing is printed to the public log
    except a count. Missing secrets or a failed send exits non-zero so a dead report is loud."""
    import urllib.request
    tok = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not tok or not chat:
        print("telegram not configured - report NOT delivered")
        return False
    base = f"https://api.telegram.org/bot{tok}/"
    chunks, cur = [], ""
    for ln in body.split("\n"):
        if len(cur) + len(ln) + 1 > 3900:
            chunks.append(cur)
            cur = ""
        cur += ln + "\n"
    chunks.append(cur)
    try:
        for c in chunks:
            data = json.dumps({"chat_id": chat, "text": c}).encode()
            req = urllib.request.Request(base + "sendMessage", data, {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=30).read()
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["test", "half", "ts", "game", "price_am", "result", "certified_clv_pct", "provisional_clv_pct_not_certified", "provisional_source"],
                           extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        bd = "----last50"
        parts = [f'--{bd}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat}\r\n',
                 f'--{bd}\r\nContent-Disposition: form-data; name="document"; filename="last50_plays.csv"\r\n'
                 f'Content-Type: text/csv\r\n\r\n{buf.getvalue()}\r\n--{bd}--\r\n']
        req = urllib.request.Request(base + "sendDocument", "".join(parts).encode(),
                                     {"Content-Type": f"multipart/form-data; boundary={bd}"})
        urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        print(f"telegram send failed ({type(e).__name__})")
        return False
    print(f"telegram delivered: {len(chunks)} message(s) + CSV")
    return True


WHY_NOT = {
    4: "no executed-play log links Hard Rock wagers to scanner flags (only 2 documented pushes); signals are not bets",
    10: "post_test recomputes on each run; no stored per-play record - not integrated yet",
    15: "rule text and start date are not in the repo or the BUCKET REPORT emails - needs Peter's definition",
    16: "rule text and start date are not in the repo or the BUCKET REPORT emails - needs Peter's definition",
    17: "registry one-liner only; start date and data source not documented",
    19: "'gettable' is not defined anywhere; the 61-row second queue is player props, which Peter excluded",
    20: "rule text and start date are not in the repo or the BUCKET REPORT emails - needs Peter's definition",
    21: "CLOSED - final read 11 Nov (FAIL); not re-graded here",
    22: "no FanDuel / DraftKings play log exists (exlag covers the four exchanges only)",
    23: "CLOSED - CLEAR FAIL 11 Nov; not re-graded here",
}


def main():
    import live_ledger as ll
    say("VALUE LAB - LAST-50 REPORT (deterministic; no model computed these numbers)")
    say(sc.cs.stamp())
    say("LIVE first (real fills only), then the top 5 paper tests, then the rest. Paper and live are never pooled.")
    say("Window: last 50 graded plays per test, one play per game+market+side, older half / newer half.")
    say("Flat 1u at the actual fill (live) or logged (paper) price. No dollars. Fills are never assumed.")
    say("CLV: CERTIFIED only (Pinnacle no-vig close, same line or moneyline, after fees); coverage printed. Provisional")
    say("     closes (live feed reads, venue closes) are shown separately, labelled, and never count toward a verdict.")
    say("CONFIDENCE: HIGH = 50 plays and certified CLV on 80%+; MEDIUM = 25+ plays and CLV on 50%+; else LOW.")

    status, csv_rows = {}, []
    covered = set()

    def run(label, rows, note="", frozen=False):
        s, o = report(label, rows, note, frozen)
        status[label] = s
        csv_rows.extend(o)

    # ------------------------------------------------------------------ LIVE
    say("")
    say("=" * 100)
    say(f"LIVE - actual bot fills from {ll.START_UTC[:10]} 00:00 ET (reporting ledger; lane from the bot's own order row)")
    say("=" * 100)
    src = ll.load()
    if src is None:
        say("  UNANSWERED: reporting ledger / tracker not decrypted in this run (TRACKER_PASSPHRASE missing)")
        acct = None
    else:
        Lg, B, C = src
        acct = ll.account(Lg, B, C, ll.feed_alerts())
        for lane, reg_n in (("LANE 1", 1), ("R1", None), ("BOARD V3", None), ("LANE 2", 8)):
            rows = live_rows(acct, lane)
            run(f"{lane} - live fills", rows, "confirmed fills only; partial fills merged; 1u at the fill price")
            if reg_n and rows:
                covered.add(reg_n)
        if not live_rows(acct, "LANE 2"):
            say("  LANE 2: no live orders in the ledger - Lane 2 is paper + dry-run (REGISTRY 8)")
        res_by_key = {p["key"]: p["res"] for p in acct["plays"]}
        am_by_key = {p["key"]: p["am_net"] for p in acct["plays"]}
        rest = [{"ts": r["t"], "game": r["key"].split("|")[1], "am": r["am"] if r["am"] is not None else am_by_key.get(r["key"]),
                 "res": res_by_key.get(r["key"]), "clv": None, "key": r["key"]}
                for r in ll.resting(Lg) if r["filled"] and (r["am"] is not None or am_by_key.get(r["key"]) is not None)]
        run("RESTING BIDS (reg 2) - resting legs that filled", rest,
            "graded with the play's settled result at the resting leg's own fill price (the play's blended price when the leg "
            "has none); CLV not joined per leg")
        covered.add(2)
        nf = [r for r in ll.resting(Lg) if not r["filled"]]
        say(f"  resting legs with no confirmed fill: {len(nf)} (excluded)")

        say("")
        say("LIVE RECONCILIATION - every bot order in the window")
        for p in sorted(acct["plays"], key=lambda p: p["t"]):
            clv = "n/a" if p["clv"] is None else f"{p['clv']:+.2f}%"
            say(f"  COUNTED  {p['t'][:16]} {p['lane']:<9} {p['key']} | fill {p['am']} (after fees {p['am_net']}) "
                f"{p['res'] or '-'} | {p['status']} | "
                f"{p['evidence']} | legs {p['fills']} | CLV {clv}")
        for e in sorted(acct["excluded"], key=lambda e: e["t"]):
            say(f"  EXCLUDED {e['t'][:16]} {str(e['lane']):<9} {e['key']} | {e['why']}")
        for u in sorted(acct["unresolved"], key=lambda u: u["t"]):
            say(f"  UNRESOLVED {u['t'][:16]} {str(u['lane']):<9} {u['key']} | {u['why']} | tracker rows {len(u['rows'])}")

    # ------------------------------------------------------------------ MANUAL (real money, not bot)
    say("")
    say("=" * 100)
    say("MANUAL - Peter's own bets (bot-linked fills removed, partial fills merged)")
    say("=" * 100)
    if acct is None:
        say("  UNANSWERED: tracker not decrypted in this run")
    else:
        run("PETER - FEED PLAYS (reg 3)", manual_rows(acct, "Peter feed"),
            "manual bets with an alert (sharp / liquidity / board) on the same game+market+side BEFORE the bet")
        run("STREET VALUE (reg 5)", manual_rows(acct, "Street Value"), "rows tagged Street Value from the private SV notes")
        covered.update({3, 5})
        other = [m for m in acct["manual"] if m["src"] == "manual, no feed origin"]
        say(f"  manual bets with no documented feed origin (not graded as a strategy): {len(other)}")

    # ------------------------------------------------------------------ PAPER
    S = sharp_rows()
    Q = liq_rows()
    paper = [
        (6, "STEAM (reg 6) - sharp alerts, all graded", S, "the whole Steam alert feed; not any one lane"),
        (None, "SHARP ALERTS - sent to phone", [r for r in S if r["sent"]], ""),
        (None, "SHARP ALERTS - NBA unders", [r for r in S if r["lg"] == "NBA" and "under" in r["bet"].lower()],
         "PROXY for Lane 1's market only, not Lane 1's fills"),
        (None, "LIQ - NBA UNDER, Kalshi-triggered", [r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                     and r["side"] == "UNDER" and r["book"] == "kalshi"], "bettable venue only"),
        (9, "LIQ-BOT (reg 9) - NBA totals, 4h+ lead", liq_certified([r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                       and r["lead"] is not None and r["lead"] >= 240]), ""),
        (13, "LIQ-SMALL (reg 13) - NBA totals, $25-50k prints", liq_certified([r for r in Q if r["lg"] == "NBA" and r["mk"] == "total"
                                                                and r["nm"] is not None and 25000 <= r["nm"] <= 50000]), ""),
        (25, "PULL_FADE (reg 25)", lane_rows("pull_fade"), "price is the logged probability"),
        (26, "SOLO (reg 26)", lane_rows("solo"), "price is the logged probability"),
        (7, "BETS BOARD PLAYS (reg 7)", liq_certified(board_rows()), "PLAY calls only; frozen call log; certified CLV = the source liquidity alert's"),
        (14, "BOARD v2 (reg 14)", liq_certified(board_rows("v2")), "v2 PLAY calls from the same frozen call log; certified CLV = the source liquidity alert's"),
        (24, "ML_STAY (reg 24)", lane_rows("ml_stay"), "price is the logged probability"),
        (18, "EXCHANGE MISPRICE (reg 18)", misprice_rows(), "SENT, exchange-priced, edge >= +2% vs Pinnacle fair, from 3 Nov"),
    ]
    for reg_n, label, dog in ((11, "SLOW-HR (reg 11) - registered cell", False), (12, "DOG BAND (reg 12)", True)):
        rows = slowhr_rows(dog)
        if rows is None:
            say("")
            say(f"{label}: UNANSWERED - slowhr state not decrypted in this run")
        else:
            paper.append((reg_n, label, rows, "Type P ML Hard Rock dogs, EV >= +2%, not LATE, first sighting; ESPN finals"
                          + ("; +100 to +299, from 7 Nov" if dog else "")))

    def rank(item):
        w, _t = window(item[2])
        ci = ci_mean(half_stats(w)["us"]) if len(w) >= N else None
        return ci[0] if ci else -9.0

    top = sorted([x for x in paper if len(window(x[2])[0]) >= N], key=rank, reverse=True)[:5]
    say("")
    say("=" * 100)
    say("PAPER - TOP 5 by the lower end of the units 95% CI (50-play windows only; no CLV gate applied to the rank)")
    say("=" * 100)
    for reg_n, label, rows, note in top:
        run(label, rows, note)
    say("")
    say("=" * 100)
    say("PAPER - all other tests")
    say("=" * 100)
    for reg_n, label, rows, note in paper:
        if reg_n:
            covered.add(reg_n)
        if (reg_n, label, rows, note) not in top:
            run(label, rows, note)

    reg = registry_names()
    say("")
    say("=" * 100)
    say("NOT IN THIS REPORT - with the reason")
    say("=" * 100)
    for n, name in sorted(reg.items()):
        if n in covered:
            continue
        say(f"  #{n:>2} {name} - {WHY_NOT.get(n, 'research track; not verified as a play log (not classified yet)')}")
    say("")
    say("OPEN ITEMS (carried until answered or you close them)")
    say("  1. UNRESOLVED live plays above count for nobody until a venue order record settles who placed them.")
    say("  2. Novig bot fills join the tracker by bot wallet + play (E3): the tracker stores a Novig position id, not the")
    say("     order id. E1/E2 are exact order-id joins.")
    say("  3. #15 / #16 / #20 definitions and start dates; #17 / #19 documented rules (see above).")
    say("  4. Circa close not included; Pinnacle only.")
    say("")
    say("SUMMARY: " + ", ".join(f"{k}: {v}" for k, v in Counter(status.values()).items()))
    return 0 if send_telegram("\n".join(L), csv_rows) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""One-screen daily report of SETTLED bets: what we paid, what Pinnacle closed at, result, CLV.

Peter, Nov 20: "Reporting actual bets" and "researching CLV accuracy" are two jobs, and the first
must not wait for the second. So this is READ-ONLY and INDEPENDENT of the V2 backfill: it projects
what is already stored and never computes, fetches or guesses a closing price. A field we do not
hold prints as a dash with its reason. Missing V2 never hides the other columns.

No dollar figures: units only, at UNIT per unit, per the repo rule that logs carry counts and units.
No API calls, no paid credits, no writes, nothing touching a live trading path.
"""
import json
import os
import sys
from datetime import datetime, timedelta

import tracker_build as tb

STATE = "clv/state.enc"
UNIT = 200.0          # 1u, as the real-plays recap uses


def am(dec_price):
    """Decimal -> American, for display only."""
    if not dec_price or dec_price <= 1:
        return None
    return round((dec_price - 1) * 100) if dec_price >= 2 else -round(100 / (dec_price - 1))


def et_day(iso_ts):
    """The ET calendar day of an ISO timestamp, or None."""
    t = tb.tp(iso_ts) if hasattr(tb, "tp") else None
    if t is None:
        try:
            t = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
        except Exception:
            return None
    return t.astimezone(tb.ET).strftime("%Y-%m-%d")


def bets_on(tracker, day):
    """Keys of tracker rows BELONGING to the given ET day, newest first, settled or not.

    Nov 20 (Peter, relayed): "report every previous-day actual bet each morning, even when the
    final close or V2 is missing." Selecting on the SETTLE date alone dropped a bet placed
    yesterday that had not settled, which is exactly a row you need to see. A row counts for the
    day if it was PLACED or SETTLED or its GAME started on it; an unsettled row is reported with
    its result blank rather than hidden.
    """
    out, seen = [], set()
    for k, b in (tracker or {}).items():
        days = {et_day(b.get(f)) for f in ("settled", "placed", "game_start") if b.get(f)}
        if day not in days:
            continue
        fp = (b.get("book"), b.get("game"), b.get("bet"), b.get("placed"), b.get("stake"))
        if fp in seen:
            continue            # the same fill reaching us twice is one bet, not two
        seen.add(fp)
        out.append((k, b))
    out.sort(key=lambda kb: str(kb[1].get("settled") or kb[1].get("placed") or ""), reverse=True)
    return out


def manual_file(day, directory="manual"):
    """Bets Peter entered elsewhere (Muse) that the tracker has no row for, from manual/<day>.json.

    REPORTING ONLY. These rows never reach tracker_build, so they cannot touch the executor's
    MANUAL_HELD gating or any live path - that wiring needs Peter's explicit yes and is not done
    here. Their purpose is that a hand-placed bet still appears in the morning report with its
    result and price instead of vanishing.
    """
    import os
    f = os.path.join(directory, f"{day}.json")
    if not os.path.exists(f):
        return []
    try:
        d = json.load(open(f))
    except Exception:
        return []
    return [r for r in (d if isinstance(d, list) else [d]) if isinstance(r, dict)]


def units(b):
    """Signed units from the venue's own settlement, or None if it carries no figure."""
    p = b.get("profit")
    if p is None:
        return None
    try:
        return round(float(p) / UNIT, 2)
    except Exception:
        return None


def why_missing(rec):
    """Why a row has no V1 CLV - the ledger's own recorded reason, never a guess."""
    if rec is None:
        return "not in the CLV ledger"
    if rec.get("clv") is not None:
        return None
    if rec.get("fixture_doubt"):
        return "held out: game assignment doubtful"
    return rec.get("why") or ("awaiting a close" if not rec.get("done") else "not scored")


def row_view(k, b, rec):
    """Everything the report shows for one settled bet. Absent means absent: no substitution."""
    rec = rec or {}
    v = {"key": k, "game": b.get("game"), "bet": b.get("bet"), "league": b.get("league"),
         "book": b.get("book"), "lane": b.get("source"), "result": b.get("result"),
         "units": units(b), "paid": b.get("price_af") if b.get("price_af") is not None else b.get("price"),
         "our_line": rec.get("our_line"), "main_line": rec.get("main_line"),
         "close_at_our_line": None, "close_main": None,
         "v1": rec.get("clv"), "v2": rec.get("clv_v2"),
         "v1_missing": why_missing(rec if rec else None),
         "v2_missing": None, "how": rec.get("how"), "age_min": rec.get("age_min")}
    alt, mn = rec.get("alt_px"), rec.get("main_px")
    if alt and len(alt) == 2:
        v["close_at_our_line"] = am(alt[0])
    elif rec.get("close_p") is not None and rec.get("how") == "own line":
        v["close_at_our_line"] = "fair stored, raw quote not kept for this row"
    if mn and len(mn) == 2:
        v["close_main"] = am(mn[0])
    # Nov 20 (Peter): resolve the half-point main-line difference WITHOUT changing CLV. The ledger
    # picks the candidate with the BIGGEST LIMIT as the main line; another source may pick the one
    # an API labels main, or the most even price. Printing which rule produced our number is the
    # diagnostic; no score is touched by it.
    v["main_rule"] = "biggest Pinnacle limit" if v["main_line"] is not None else None
    v["src"] = ("certified Pinnacle close" if v["v1"] is not None else
                "MANUAL FILE (not in the tracker)" if rec.get("_manual") else "unavailable")
    if v["v2"] is None:
        v["v2_missing"] = (rec.get("v2_unsupported") or
                           ("V2 == V1 (our number was the main line)" if rec.get("at_main")
                            else "not yet recomputed" if rec.get("clv") is not None
                            else "no V1 close to derive from"))
    return v


def pct(x):
    return "-" if x is None else f"{x * 100:+.2f}%"


def render(day, views):
    L = [f"SETTLED BETS - {day} (ET). Units at 1u = {UNIT:.0f}; no dollar figures by design.",
         "Read-only projection of stored records. A dash is a field we do not hold, with its reason.",
         ""]
    if not views:
        L.append("No settled bets recorded for that ET day.")
        return L
    w = sum(v["units"] or 0 for v in views)
    won = sum(1 for v in views if str(v["result"]).upper().startswith("W"))
    lost = sum(1 for v in views if str(v["result"]).upper().startswith("L"))
    L.append(f"{len(views)} settled | {won}-{lost} | {w:+.2f}u")
    scored = [v for v in views if v["v1"] is not None]
    L.append(f"V1 CLV on {len(scored)}/{len(views)}"
             + (f", mean {sum(v['v1'] for v in scored) / len(scored) * 100:+.2f}%" if scored else "")
             + f" | V2 on {sum(1 for v in views if v['v2'] is not None)}/{len(views)}")
    L.append("")
    for v in views:
        L.append(f"{v['bet']} | {v['league']} {v['book']} [{v['lane']}] | {v['game']}")
        L.append(f"    result {v['result']} {('%+.2fu' % v['units']) if v['units'] is not None else '(no settled figure)'}"
                 f" | paid {v['paid'] if v['paid'] is not None else '-'}"
                 f" | our line {v['our_line'] if v['our_line'] is not None else '-'}")
        if v.get("snap"):
            sn = v["snap"]
            L.append(f"    SNAPSHOT ({sn['label']}): line {sn['line']} @ our side {sn['price_our']} /"
                     f" other {sn['price_other']}, captured T-{sn['t_minus']} min"
                     + (f" | movement {sn['movement']:+g} pts our way" if sn.get("movement") is not None else "")
                     + (f" | PROVISIONAL CLV {pct(sn['clv'])}" if sn.get("clv") is not None
                        else f" | no provisional CLV ({sn['why']})"))
        L.append(f"    source: {v.get('src')}"
                 + (f" | main line chosen by {v['main_rule']}" if v.get("main_rule") else ""))
        L.append(f"    Pinnacle close: main line {v['main_line'] if v['main_line'] is not None else '-'}"
                 f" @ {v['close_main'] if v['close_main'] is not None else '-'}"
                 f" | at our line {v['close_at_our_line'] if v['close_at_our_line'] is not None else '-'}"
                 + (f" | read '{v['how']}'" if v["how"] else "")
                 + (f", tick {v['age_min']} min pre-start" if v["age_min"] is not None else ""))
        L.append(f"    V1 CLV {pct(v['v1'])}" + (f" ({v['v1_missing']})" if v["v1"] is None else "")
                 + f" | V2 CLV {pct(v['v2'])}" + (f" ({v['v2_missing']})" if v["v2"] is None else ""))
    return L


def main(argv):
    day = argv[1] if len(argv) > 1 else (datetime.now(tb.ET) - timedelta(days=1)).strftime("%Y-%m-%d")
    if not tb.PASS:
        print("daily report: TRACKER_PASSPHRASE not set; cannot read the encrypted records")
        return 1
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        print(f"daily report: tracker state unreadable ({type(e).__name__})")
        return 1
    try:
        bets = (tb.dec(json.load(open(STATE))) or {}).get("bets") or {}
    except Exception:
        bets = {}
        print("daily report: CLV ledger state unreadable - bet and settlement columns only")
    rows = bets_on(tracker, day)
    have = {(b.get("book"), b.get("game"), b.get("bet")) for _, b in rows}
    for r in manual_file(day):
        if (r.get("book"), r.get("game"), r.get("bet")) not in have:
            rows.append((r.get("id") or f"manual|{r.get('bet')}", dict(r, _manual=True)))
    views = []
    for k, b in rows:
        rec = dict(bets.get(k) or {})
        if b.get("_manual"):
            rec["_manual"] = True
        views.append(row_view(k, b, rec))
    # SECOND-PRIORITY evidence, only where the certified close is absent.
    # A silent except here would be the worst failure available: the report would look complete
    # while every snapshot was quietly dropped. It says so instead.
    ss, snaps = None, []
    try:
        import snapshot_source as ss
        snaps, _bad = ss.load()
        if _bad:
            print(f"daily report: {_bad} snapshot file(s) unreadable and skipped", flush=True)
    except Exception as e:
        print(f"daily report: snapshot source UNAVAILABLE ({type(e).__name__}: {e}) - "
              f"certified rows only, no provisional CLV this run", flush=True)
    for v, (k, b) in zip(views, rows):
        if v["v1"] is not None or not snaps or ss is None:
            continue
        for sn in snaps:
            try:
                if not ss.matches(sn, b, day):
                    continue
                clv, why = ss.provisional_clv(sn, b)
            except Exception:
                continue
            v["snap"] = {"label": ss.LABEL, "line": sn.get("line"),
                         "price_our": sn.get("price_our", "-"), "price_other": sn.get("price_other", "-"),
                         "t_minus": sn.get("t_minus_min", "?"), "movement": ss.movement(sn, b),
                         "clv": clv, "why": why}
            if clv is not None:
                v["src"] = "verified snapshot (PROVISIONAL, not certified)"
            break
    body = "\n".join(render(day, views))
    print(body, flush=True)
    if os.environ.get("REPORT_EMAIL") == "1":
        try:
            import executor as ex
            import smtplib
            from email.mime.text import MIMEText
            user, pw, to = ex.gmail()
            m = MIMEText(body, "plain", "utf-8")
            m["Subject"] = f"Bets DAILY REPORT {day}"
            m["From"], m["To"] = user, to
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as sv:
                sv.login(user, pw)
                sv.sendmail(user, [to], m.as_string())
            print("daily report: emailed", flush=True)
        except Exception as e:
            print(f"daily report: email FAILED ({type(e).__name__}) - the report above still stands",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

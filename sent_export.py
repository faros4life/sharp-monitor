#!/usr/bin/env python3
"""
SENT ALERTS - PER-PLAY EXPORT (Peter Nov 4 "go"; Muse's column spec Nov 4 22:04 ET). READ-ONLY DIAGNOSTIC.

Population: alerts.json, every alert with sent_to_phone, every league and market, from the history floor onward.
NOTHING is filtered on profitability, CLV, gettability or grade: every sent alert gets exactly ONE row, and when a
field could not be read the row says why in exclusion_reason instead of disappearing. Rows are never dropped for
being losers, ungraded, ungettable or unmatched.

This file changes no rule, no threshold, no alert and no execution path. It is the SENT-side twin of the liq-history
export, built so that (Muse, Nov 4):
  a) the SENT <-> LIQ game overlap can be measured - the two populations can share games, so the Pinnacle-limit
     result is NOT two independent sightings until that overlap is known;
  b) item 56's Pinnacle-limit LOW / HIGH split can be reproduced off the raw rows, independently, before Lane 2's
     Friday review.

Grading basis, stated so it can be reproduced rather than trusted:
  entry       = the alert's own after-fee price at the trigger book, American -> decimal (cl.am_to_dec).
  exec 5m     = best after-fee price on ProphetX / Novig / Kalshi / Polymarket US at alert + 5 min, on the alert's
                own line. A quote implying better than +15% vs the close is dropped as a misread (the P1 rule, and
                the same test the fill audit now applies per book) and counted in suspect_quotes_dropped.
  pin close   = Pinnacle's no-vig fair at the LAST pre-start read, at the bet's own line where Pinnacle had it;
                close_same_line = 1 only then, and close_how records how it was derived otherwise. Compare only
                equivalent contracts.
  pin entry   = the same no-vig fair read at the alert time, so entry CLV and close CLV share one basis.
No keys, no stakes, no balances, no account data. Private email; the log prints counts only.
"""
import csv
import io
import json
import os
import smtplib
import statistics as stt
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import clv_ledger as cl
import exchange_lag as el
import executor as ex
import hist_cache as hc
import plimit_level as pl
import tracker_build as tb

ET = tb.ET
EXCH = ("prophetx", "novig.us", "kalshi", "polymarket.us")
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)   # OddsPapi history depth
EXEC_SEC = int(os.environ.get("SENTX_EXEC_SEC", "") or "300")   # Muse: the five-minute executable price
CACHE_ONLY = (os.environ.get("SENTX_CACHE_ONLY") or "") == "1"
ALERTS = os.environ.get("SENTX_ALERTS", "") or "alerts.json"

MKNAME = {"tot": "total", "spr": "spread", "ml": "moneyline", "rl": "runline"}

COLS = ["game_id", "game", "league", "market", "side", "line", "alert_utc", "lead_hours",
        "pin_limit_at_alert", "pin_limit_read", "pin_limit_x_vs_2h_before",
        "entry_after_fee_dec", "entry_after_fee_american", "trigger_book", "trigger_book_key",
        "exec_5m_after_fee_dec", "exec_5m_after_fee_american", "exec_5m_book", "exec_5m_beats_entry",
        "pin_novig_at_entry", "pin_novig_at_close", "close_same_line", "close_how", "close_age_min",
        "entry_vs_close_clv_pct", "exec_5m_vs_close_clv_pct",
        "result", "units_flat", "late", "top25", "edge_pct", "confirmed_by", "executable_book",
        "pricing_bettable", "suspect_quotes_dropped", "exclusion_reason"]


def am(dec):
    try:
        d = float(dec)
    except Exception:
        return None
    if d <= 1:
        return None
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def side_of(a):
    """The held side, from the alert's own bet text / kind. Never inferred from the result."""
    bet = (a.get("bet") or "").strip()
    k = a.get("kind")
    if k == "tot":
        up = bet.upper()
        return "OVER" if up.startswith("OVER") else "UNDER" if up.startswith("UNDER") else ""
    return bet.split(" (")[0].strip()


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
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as sv:
        sv.login(user, pw)
        sv.sendmail(user, [to], m.as_string())


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("sent export: ODDSPAPI_KEY not set")
        return
    every = [a for a in (json.load(open(ALERTS)).get("alerts") or []) if a.get("sent_to_phone")]
    A = [a for a in every if cl.tp(a.get("alert_utc")) and cl.tp(a["alert_utc"]) >= FROM]
    before = len(every) - len(A)
    st = {"billable": {}}
    mkmap = cl.load_markets(st, now)
    for lg in sorted(set(a.get("sport") for a in A) & set(cl.SPORT)):
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))

    X = []
    miss = {}

    def bump(k):
        miss[k] = miss.get(k, 0) + 1

    def xrow(a, **kw):
        t0_, s0_ = cl.tp(a.get("alert_utc")), cl.tp(a.get("start_utc"))
        cb = a.get("confirmed_by") or []
        d = {"game": a.get("game"), "league": a.get("sport"), "market": MKNAME.get(a.get("kind"), a.get("kind")),
             "side": side_of(a), "line": a.get("point"), "alert_utc": a.get("alert_utc"),
             "lead_hours": (round((s0_ - t0_).total_seconds() / 3600, 2) if (t0_ and s0_) else None),
             "trigger_book": a.get("book"), "trigger_book_key": a.get("book_key"),
             "result": a.get("result"), "units_flat": a.get("units_flat"),
             "late": 1 if a.get("late") else 0,
             "top25": ("" if a.get("top25") is None else (1 if a.get("top25") else 0)),
             "edge_pct": a.get("edge_pct"),
             "confirmed_by": "|".join(str(x) for x in cb) if cb else "",
             "executable_book": 1 if a.get("executable_book") else 0,
             "pricing_bettable": 1 if a.get("pricing_bettable") else 0,
             "suspect_quotes_dropped": 0, "exclusion_reason": ""}
        d.update(kw)
        X.append(d)
        return d

    for a in A:
        lg, t0 = a.get("sport"), cl.tp(a["alert_utc"])
        if lg not in cl.SPORT:
            bump("league has no history mapping")
            xrow(a, exclusion_reason=f"{lg} has no OddsPapi history mapping (NCAAB / MLB are not graded here)")
            continue
        b = {"bet": a.get("bet"), "league": lg, "game": a.get("game"), "game_start": a.get("start_utc"),
             "book": a.get("book")}
        fid = cl.find_fixture(st, b)
        if not fid:
            bump("no fixture")
            xrow(a, exclusion_reason="no fixture matched in OddsPapi")
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
        if not start or now - start < hc.FINAL_AFTER:
            bump("game not finished")
            xrow(a, game_id=fid, exclusion_reason="game not finished (no close to grade against yet)")
            continue
        if CACHE_ONLY and not all(os.path.exists(hc._path(fid, x)) for x in ("pinnacle",) + EXCH):
            bump("not in cache")
            xrow(a, game_id=fid, exclusion_reason="fixture not in the history cache")
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(EXCH), start)
        if isinstance(h, dict) and h.get("_error"):
            bump("history error")
            xrow(a, game_id=fid, exclusion_reason="history read error")
            continue
        pin = cl.book_markets(h, "pinnacle")
        lim, how = pl.pin_limit_at(b, f, pin, mkmap, t0, lg)
        lim2, _ = pl.pin_limit_at(b, f, pin, mkmap, t0 - timedelta(hours=2), lg)
        limx = round(lim / lim2, 3) if lim and lim2 else None
        px = a.get("price_after_fee") if a.get("price_after_fee") is not None else a.get("price")
        want = cl.am_to_dec(px) if px is not None else None

        c, cwhy = cl.close_for(b, f, pin, mkmap, start, lg)
        if not c:
            bump("no Pinnacle close")
            xrow(a, game_id=fid, pin_limit_at_alert=lim, pin_limit_read=how, pin_limit_x_vs_2h_before=limx,
                 entry_after_fee_dec=(round(want, 4) if want else None),
                 entry_after_fee_american=(am(want) if want else None),
                 exclusion_reason=f"no Pinnacle close: {cwhy}")
            continue
        ce, _ = cl.close_for(b, f, pin, mkmap, t0, lg)   # same basis, read at entry

        when = min(t0 + timedelta(seconds=EXEC_SEC), start)
        best, best_bk, dropped = None, None, 0
        for slug in EXCH:
            bk = cl.book_markets(h, slug)
            x = cl.novig_at(b, f, bk, mkmap, when, lg) if bk else None
            if not x:
                continue
            v = el.eff(slug, x[0])
            if c["p"] * v - 1 > 0.15:   # P1 misread rule: a quote this far above the close is bad data, not a price
                dropped += 1
                bump("suspect quote dropped")
                continue
            if best is None or v > best:
                best, best_bk = v, slug

        xrow(a, game_id=fid,
             pin_limit_at_alert=lim, pin_limit_read=how, pin_limit_x_vs_2h_before=limx,
             entry_after_fee_dec=(round(want, 4) if want else None),
             entry_after_fee_american=(am(want) if want else None),
             exec_5m_after_fee_dec=(round(best, 4) if best else None),
             exec_5m_after_fee_american=(am(best) if best else None),
             exec_5m_book=best_bk,
             exec_5m_beats_entry=("" if (best is None or want is None) else (1 if best >= want - 1e-9 else 0)),
             pin_novig_at_entry=(round(ce["p"], 5) if ce else None),
             pin_novig_at_close=round(c["p"], 5),
             close_same_line=1 if c.get("how") in ("own line", "moneyline") else 0,
             close_how=c.get("how"), close_age_min=c.get("age_min"),
             entry_vs_close_clv_pct=(round(100 * (c["p"] * want - 1), 3) if want else None),
             exec_5m_vs_close_clv_pct=(round(100 * (c["p"] * best - 1), 3) if best else None),
             suspect_quotes_dropped=dropped)

    graded = [r for r in X if r.get("entry_vs_close_clv_pct") is not None]
    sameln = [r for r in graded if r.get("close_same_line") == 1]
    withlim = [r for r in X if r.get("pin_limit_at_alert")]
    L = [f"SENT ALERTS - PER-PLAY EXPORT (read-only) | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         "Every sent alert from the history floor gets one row. Nothing filtered on profitability, CLV or grade.",
         "No rule, threshold, alert or execution path is touched by this file.",
         "",
         f"Sent alerts in file: {len(every)}  (before the {FROM:%b %d} history floor, not exported: {before})",
         f"Rows exported: {len(X)}",
         f"  with an entry-vs-close CLV: {len(graded)}",
         f"  of those, Pinnacle closed on the bet's own line: {len(sameln)}",
         f"  with a Pinnacle limit read at the alert: {len(withlim)}",
         ""]
    if miss:
        L.append("Rows carrying an exclusion_reason (counts only):")
        L += [f"  {k}: {v}" for k, v in sorted(miss.items(), key=lambda kv: -kv[1])]
        L.append("")
    if graded:
        cv = [r["entry_vs_close_clv_pct"] for r in graded]
        L.append(f"Entry CLV vs Pinnacle's no-vig close, all exported graded rows: mean {stt.mean(cv):+.2f}% "
                 f"| beat {sum(1 for x in cv if x > 0)}/{len(cv)}")
        L.append("  (descriptive only - this is the export's own arithmetic, not a registered test result)")
        L.append("")
    L += ["Columns: " + ", ".join(COLS), "",
          "Intended use: measure the SENT <-> LIQ game overlap, and reproduce item 56's Pinnacle-limit LOW / HIGH",
          "split off the raw rows. Until that overlap is measured, the Pinnacle-limit result is TWO populations that",
          "may share games, never two independent sightings."]
    body = "\n".join(L)
    try:
        send_csv("Bets SENT ALERTS per-play export (read-only)", body, X,
                 f"sent_perplay_{now.astimezone(ET):%Y%m%d_%H%M}.csv")
    except Exception as exn:
        print(f"sent export attachment failed: {str(exn)[:80]}")
        ex.send("Bets SENT ALERTS per-play export (read-only)", body)
    print(f"sent export: rows {len(X)}, graded {len(graded)}, same-line {len(sameln)}, with limit {len(withlim)}")


if __name__ == "__main__":
    main()

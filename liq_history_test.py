#!/usr/bin/env python3
"""
LIQUIDITY ALERTS vs THE DOWNLOADED HISTORY (Nov 4, 2026; Peter 9:22 "5 minutes after is too long ... bot will be faster
than that and we get price at alert or better"). PAPER / MEASUREMENT ONLY - reads history, touches no bet, no alert, no
board, no executor input.

Population: liquidity/alerts.json, NBA / NFL / NCAAF / NHL, moneyline / spread / total, graded W/L/P, not an artifact
or close_suspect, inside the history window (Oct 12+; liquidity alerts start Oct 22).
PRICE: every play is graded at the ALERT price (after the trigger exchange's fee) - the bot only bets that price or better.
GETTABLE: at least one exchange we can bet (ProphetX / Novig / Kalshi / Polymarket US) had that after-fee price OR BETTER
on its last quote at or before alert + GET_SEC seconds (default 60). Not gettable = counted, not graded in the judged rows.
CLV: Pinnacle's true no-vig close for the held side x the alert's after-fee price - 1 (percent), not the exchange's own close.
PINNACLE LIMIT: Pinnacle's raw max-stake limit on that side at the alert (last tick within 60 min), and vs its own value
2 hours earlier (rising = 1.5x+). Limits rise toward tip-off, so the lead split always goes with it.
JUDGED rule (proposed Nov 4): NBA totals, alerted 4h+ before tip. H1 <= FIT_END < H2. Everything else is descriptive.
Private email; the Actions log prints counts only.
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
import nba_names as nn
import event_id as eid
import executor as ex
import hist_cache as hc
import plimit_level as pl
import tracker_build as tb

ET = tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("prophetx", "novig.us", "kalshi", "polymarket.us")
SLUG = {"kalshi": "kalshi", "polymarket": "polymarket.us", "novig": "novig.us", "prophetx": "prophetx"}
FROM = datetime(2026, 10, 12, tzinfo=timezone.utc)
FIT_END = os.environ.get("LIQH_FIT_END", "") or "2026-10-28"
GET_SEC = int(os.environ.get("LIQH_GET_SEC", "") or "60")
CACHE_ONLY = (os.environ.get("LIQH_CACHE_ONLY") or "1") == "1"   # default: the history we already hold, no downloads
ALERTS = os.environ.get("LIQH_ALERTS", "") or "liquidity/alerts.json"


# Nov 5 (Peter): READ-ONLY per-play diagnostic export, sent as a CSV attachment. It changes no rule, threshold, alert or
# execution, and it does NOT touch the judged rows - the report is still built from R exactly as before, while the export
# is a separate list that keeps EVERY qualifying play (losses, ungettable quotes, unmatched fixtures, missing closes),
# each with its own reason flag. Nothing is filtered on profitability or CLV. Pinnacle's close is recorded at the bet's
# OWN line wherever Pinnacle had it (close_same_line = 1); where it did not, close_how says how it was derived, so only
# equivalent contracts get compared. No keys, no stakes, no account data in the file.
EXPORT_COLS = ["game_id", "game", "league", "market", "side", "line", "alert_utc", "lead_hours",
               "entry_after_fee_dec", "entry_after_fee_american", "trigger_book",
               "best_exch_after_fee_dec", "best_exch_after_fee_american", "best_exch_book", "gettable",
               "best_raw_after_fee_dec", "best_raw_book", "best_raw_age_s", "gettable_raw",
               "best_causal_after_fee_dec", "best_causal_book", "best_causal_age_s", "gettable_causal",
               "best_causal_vs_close_clv_pct", "quotes_seen", "quotes_fresh_in_window", "quotes_rejected_causal",
               "pin_novig_at_entry", "pin_novig_at_exec", "pin_age_at_exec_min",
               "pin_novig_at_close", "close_same_line", "close_how", "close_age_min",
               "entry_vs_close_clv_pct", "best_vs_close_clv_pct",
               "pin_limit_at_alert", "pin_limit_read", "pin_limit_x_vs_2h_before",
               "base_depth", "new_money", "size_x", "sharp_agree", "sharp_oppose", "sharp_quiet",
               "result", "units_at_entry", "units_at_best", "suspect_quotes_dropped", "exclusion_reason"]


def send_csv(subject, body, rows, filename):
    """Report body as text, per-play rows as a CSV attachment."""
    user, pw, to = ex.gmail()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLS, extrasaction="ignore")
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


def am(dec):
    """Decimal price -> American, for the export only."""
    try:
        d = float(dec)
    except Exception:
        return None
    if d <= 1:
        return None
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def units(res, dec):
    return (dec - 1) if res == "W" else (-1.0 if res == "L" else 0.0)


def bet_text(a):
    """Bet text the history tools parse, from the alert's own side and line (Polymarket labels like 'Over (237.5)' or
    'Team (+3.5)' don't parse; Kalshi 'NOT ...' wording is already resolved in side/line)."""
    sd, ln, mk = a.get("side"), a.get("line"), a.get("market")
    if mk == "total" and sd in ("OVER", "UNDER") and ln is not None:
        return f"{'Over' if sd == 'OVER' else 'Under'} {ln:g}"
    if mk == "spread" and sd and ln is not None:
        return f"{sd} {ln:+g}"
    if mk == "moneyline" and sd:
        return f"{sd} ML"
    return a.get("side_label")


def size_x(a):
    b, n = a.get("base_depth") or 0, a.get("new_money") or 0
    return (b + n) / b if b > 0 else None


def main():
    now = datetime.now(timezone.utc)
    if not cl.KEY:
        print("liq history test: ODDSPAPI_KEY not set")
        return
    A = [a for a in (json.load(open(ALERTS)).get("alerts") or [])
         if a.get("league") in LEAGUES and a.get("market") in ("moneyline", "spread", "total")
         and a.get("result") in ("W", "L", "P") and not a.get("artifact") and not a.get("close_suspect")
         and cl.tp(a.get("alerted_utc")) and cl.tp(a["alerted_utc"]) >= FROM and a.get("price")]
    if (os.environ.get("LIQH_FROZEN") or "") == "1":
        # Nov 5 (Peter): judge exactly the board's FROZEN PLAY calls (board/calls.json - the call each row had when it
        # posted), not the whole alert population. Pinnacle no-vig close is the benchmark; the monitor's own clv_cents
        # grades an alert against the book the money hit, which moves toward it.
        try:
            FZ = {k for k, e in (json.load(open("board/calls.json")).get("calls") or {}).items() if e.get("call") == "PLAY"}
        except Exception:
            FZ = set()
        A = [a for a in A if f"{a.get('key') or ''}|{a.get('alerted_utc') or ''}" in FZ]
        print(f"liq history test: frozen-PLAY filter -> {len(A)} of {len(FZ)} frozen calls carry a graded alert")
    st = {"billable": {}}
    # Nov 6 (Peter): reuse the fixtures the CLV ledger has ALREADY paid for. This used to start from a
    # bare dict every run, so it re-bought /fixtures on every single run - a re-run of this report cost
    # a credit for data already on disk. Read-only: this script never saves st (checked), so the
    # ledger's own state cannot be touched from here. Carrying fx_last too means a re-run inside the
    # ledger's 6 h window spends NOTHING; outside it, one top-up call as before. The run still prints
    # its own call count, so the spend is always visible. A fixture the cache lacks still shows up in
    # the "no fixture" miss count rather than being silently dropped.
    try:
        _prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(_prev.get("fixtures") or {})
        st["fx_last"] = dict(_prev.get("fx_last") or {})
        for _k in ("tid", "tname"):
            if _prev.get(_k) is not None:
                st[_k] = _prev[_k]
        print(f"liq history test: reusing {len(st['fixtures'])} cached fixtures "
              f"({len(st['fx_last'])} league refresh timestamps) - no re-purchase")
    except Exception as _e:
        print(f"liq history test: no cached fixtures ({type(_e).__name__}) - will fetch")
    mkmap = cl.load_markets(st, now)
    # Nov 6 (Peter, 1-credit budget): refresh fixtures only for the leagues actually IN the population.
    # Each refresh_fixtures is one billable /fixtures call, and this loop used to spend one per league in
    # LEAGUES whatever the population held - so a LIQH_FROZEN=1 run, whose board PLAYs are all NBA
    # totals, paid for NFL, NCAAF and NHL fixtures it never looked at. Never more calls than before,
    # usually fewer, and identical results because a league with no rows had no fixture to match.
    need = sorted({(a.get("league") or "").upper() for a in A} & set(LEAGUES))
    print(f"liq history test: fixtures needed for {need or 'no leagues'} "
          f"({len(LEAGUES) - len(need)} league refresh(es) skipped as unused)")
    for lg in need:
        cl.refresh_fixtures(st, now, lg, (FROM - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    R = []
    X = []   # the per-play export: every qualifying play, kept whatever happened to it
    miss = {"no fixture": 0, "not in cache": 0, "history error": 0, "no Pinnacle close": 0}

    def xrow(a, **kw):
        sd_ = (a.get("side") or "").upper()
        t0_, st_0 = cl.tp(a.get("alerted_utc")), cl.tp(a.get("start_utc"))
        d = {"game": (a.get("game") or "").split(":")[0], "league": a.get("league"), "market": a.get("market"),
             "side": sd_ if sd_ in ("OVER", "UNDER") else (a.get("side") or ""), "line": a.get("line"),
             "alert_utc": a.get("alerted_utc"), "trigger_book": a.get("book"),
             "lead_hours": (round((st_0 - t0_).total_seconds() / 3600, 2) if (t0_ and st_0) else None),
             "base_depth": a.get("base_depth"), "new_money": a.get("new_money"), "size_x": size_x(a),
             "sharp_agree": 1 if a.get("sharp_agree") else 0, "sharp_oppose": 1 if a.get("sharp_oppose") else 0,
             "sharp_quiet": 0 if (a.get("sharp_agree") or a.get("sharp_oppose")) else 1,
             "result": a.get("result"), "suspect_quotes_dropped": 0, "exclusion_reason": ""}
        d.update(kw)
        X.append(d)
        return d
    for a in A:
        lg, t0 = a["league"], cl.tp(a["alerted_utc"])
        game = (a.get("game") or "").split(":")[0]
        b = {"bet": bet_text(a), "league": lg, "game": game, "game_start": a.get("start_utc"), "book": a.get("book")}
        tms = nn.teams_of(a)   # Nov 5 (Peter "do now"): Kalshi names NBA teams by city, Polymarket by nickname, so a
        if tms:                # game string has one distinctive word a side and fails the matcher's two-word floor.
            b["teams"] = tms   # Handing it the full names clears that floor without loosening the matcher.
        fid = cl.find_fixture(st, b)
        if not fid:
            miss["no fixture"] += 1
            xrow(a, exclusion_reason="no fixture matched in OddsPapi")
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
        if CACHE_ONLY and not all(os.path.exists(hc._path(fid, x)) for x in ("pinnacle",) + EXCH):
            miss["not in cache"] += 1
            xrow(a, game_id=fid, exclusion_reason="fixture not in the history cache")
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(EXCH), start)
        if isinstance(h, dict) and h.get("_error"):
            miss["history error"] += 1
            xrow(a, game_id=fid, exclusion_reason="history read error")
            continue
        pin = cl.book_markets(h, "pinnacle")
        c, cwhy = cl.close_for(b, f, pin, mkmap, start, lg)
        if not c:
            lim0, how0 = pl.pin_limit_at(b, f, pin, mkmap, t0, lg)
            xrow(a, game_id=fid, pin_limit_at_alert=lim0, pin_limit_read=how0,
                 entry_after_fee_dec=(round(el.eff(SLUG.get(a.get("book"), a.get("book")), 1 / a["price"]), 4) if a.get("price") else None),
                 exclusion_reason=f"no Pinnacle close: {cwhy}")
            miss["no Pinnacle close"] += 1
            continue
        ce, _ = cl.close_for(b, f, pin, mkmap, t0, lg)   # Pinnacle's no-vig fair for the same side AT ENTRY TIME
        want = el.eff(SLUG.get(a.get("book"), a.get("book")), 1 / a["price"])   # alert price, after the trigger book's fee
        when = min(t0 + timedelta(seconds=GET_SEC), start)
        # Nov 5 (Peter GO 22:50): THREE BASES. `best` keeps the ORIGINAL close-filtered behaviour, so every figure
        # already published by this report is unchanged - nothing is overwritten retroactively. Beside it: `rbest`
        # (RAW, nothing removed) and `kbest` (CAUSAL - a quote is rejected only against Pinnacle's fair read at the
        # quote's OWN timestamp, which was observable then). The CAUSAL BASIS section below reports the judged-row
        # membership delta and the Gate 1 rerun.
        # Peter's guard: causality is not executability. A quote can be causally valid and still be a price nobody
        # could take. So exchange quote age, Pinnacle quote age and in-window publication are reported SEPARATELY
        # and are never folded into any basis.
        cw, _ = cl.close_for(b, f, pin, mkmap, when, lg)
        best, best_bk, dropped = None, None, 0
        rbest, rbest_bk, rage = None, None, None
        kbest, kbest_bk, kage, krej = None, None, None, 0
        seen, fresh = 0, 0
        for slug in EXCH:
            bk = cl.book_markets(h, slug)
            x = cl.novig_at(b, f, bk, mkmap, when, lg) if bk else None
            if not x:
                continue
            v, age = el.eff(slug, x[0]), x[1]
            seen += 1
            if age is not None and age <= GET_SEC:
                fresh += 1          # this book actually published inside the alert -> +GET_SEC window
            if rbest is None or v > rbest:
                rbest, rbest_bk, rage = v, slug, age
            if cw and cw["p"] * v - 1 > 0.15:
                krej += 1
            elif kbest is None or v > kbest:
                kbest, kbest_bk, kage = v, slug, age
            if c["p"] * v - 1 > 0.15:   # same rule as P1 / exchange-lag: a quote > +15% vs the close is a misread
                miss["suspect quote dropped"] = miss.get("suspect quote dropped", 0) + 1
                dropped += 1
                continue
            if best is None or v > best:
                best, best_bk = v, slug
        lim, how = pl.pin_limit_at(b, f, pin, mkmap, t0, lg)
        lim2, _ = pl.pin_limit_at(b, f, pin, mkmap, t0 - timedelta(hours=2), lg)
        lead = (start - t0).total_seconds() / 3600 if start else None
        res = a["result"]
        sd = (a.get("side") or "").upper()
        R.append({"lg": lg, "mk": a["market"], "day": t0.astimezone(ET).strftime("%Y-%m-%d"), "lead": lead,
                  "side": sd if sd in ("OVER", "UNDER") else a["market"], "book": a.get("book"),
                  "size_x": size_x(a), "nm": a.get("new_money"), "quiet": not a.get("sharp_agree") and not a.get("sharp_oppose"),
                  "agree": bool(a.get("sharp_agree")), "pulled": bool(a.get("pulled")),
                  "gettable": best is not None and best >= want - 1e-9, "best": best, "best_bk": best_bk,
                  "clv": round(100 * (c["p"] * want - 1), 2), "u": units(res, want),
                  "u_best": units(res, best) if best and best >= want - 1e-9 else None,
                  "lim": lim, "lim_how": how, "lim_x": (lim / lim2) if lim and lim2 else None,
                  "own_clv": a.get("clv_cents"),
                  # the causal and raw bases, beside the original, so the membership delta is measurable
                  "get_k": kbest is not None and kbest >= want - 1e-9, "best_k": kbest,
                  "get_r": rbest is not None and rbest >= want - 1e-9, "best_r": rbest,
                  "age_k": kage, "age_r": rage, "seen": seen, "fresh": fresh, "krej": krej,
                  # Nov 6 (Peter): canonical identity (event_id.py) so duplicate alerts on one game collapse
                  "at": a.get("alerted_utc"),
                  "ekey": eid.event_key(lg, a.get("teams"), a.get("start_utc"), a.get("game"))[0],
                  "bkey": eid.bet_key(lg, a.get("teams"), a.get("start_utc"), a.get("market"), sd, a.get("line"), a.get("game"))[0]})
        got = best is not None and best >= want - 1e-9
        xrow(a, game_id=fid,
             entry_after_fee_dec=round(want, 4), entry_after_fee_american=am(want),
             best_exch_after_fee_dec=(round(best, 4) if best else None),
             best_exch_after_fee_american=(am(best) if best else None),
             best_exch_book=best_bk, gettable=1 if got else 0,
             best_raw_after_fee_dec=(round(rbest, 4) if rbest else None), best_raw_book=rbest_bk,
             best_raw_age_s=(round(rage) if rage is not None else None),
             gettable_raw=1 if (rbest is not None and rbest >= want - 1e-9) else 0,
             best_causal_after_fee_dec=(round(kbest, 4) if kbest else None), best_causal_book=kbest_bk,
             best_causal_age_s=(round(kage) if kage is not None else None),
             gettable_causal=1 if (kbest is not None and kbest >= want - 1e-9) else 0,
             best_causal_vs_close_clv_pct=(round(100 * (c["p"] * kbest - 1), 3) if kbest else None),
             quotes_seen=seen, quotes_fresh_in_window=fresh, quotes_rejected_causal=krej,
             pin_novig_at_entry=(round(ce["p"], 5) if ce else None),
             pin_novig_at_exec=(round(cw["p"], 5) if cw else None),
             pin_age_at_exec_min=(cw.get("age_min") if cw else None),
             pin_novig_at_close=round(c["p"], 5),
             close_same_line=1 if c.get("how") in ("own line", "moneyline") else 0,
             close_how=c.get("how"), close_age_min=c.get("age_min"),
             entry_vs_close_clv_pct=round(100 * (c["p"] * want - 1), 3),
             best_vs_close_clv_pct=(round(100 * (c["p"] * best - 1), 3) if best else None),
             pin_limit_at_alert=lim, pin_limit_read=how,
             pin_limit_x_vs_2h_before=(round(lim / lim2, 3) if lim and lim2 else None),
             units_at_entry=round(units(res, want), 4),
             units_at_best=(round(units(res, best), 4) if got else None),
             suspect_quotes_dropped=dropped)

    def st_(xs, only_get=True):
        g = [x for x in xs if x["gettable"]] if only_get else xs
        if not g:
            return f"n {len(xs)} | gettable 0"
        w = sum(x["u"] > 0 for x in g)
        l_ = sum(x["u"] < 0 for x in g)
        u = sum(x["u"] for x in g)
        cv = [x["clv"] for x in g]
        h1 = [x for x in g if x["day"] <= FIT_END]
        h2 = [x for x in g if x["day"] > FIT_END]
        pp = lambda z: f"{sum(x['u'] for x in z) / len(z):+.3f} (n{len(z)})" if z else "n0"
        return (f"n {len(xs)} | gettable {len(g)} | {w}-{l_} {u:+.2f}u {u / len(g):+.3f}/play | Pinnacle CLV "
                f"{stt.mean(cv):+.2f}% beat {100 * sum(v > 0 for v in cv) / len(cv):.0f}% | H1 {pp(h1)} H2 {pp(h2)}")

    rule = [r for r in R if r["lg"] == "NBA" and r["mk"] == "total" and r["lead"] is not None and r["lead"] >= 4]
    L = [f"LIQUIDITY ALERTS vs DOWNLOADED HISTORY - PAPER ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
         f"Graded 1u flat at the ALERT price (after fee). Gettable = that price or better on ProphetX/Novig/Kalshi/PM US within "
         f"{GET_SEC}s of the alert. CLV vs Pinnacle's no-vig close. H1 <= {FIT_END} < H2. Judged rows count gettable plays only.",
         f"Alerts in scope {len(A)}, read {len(R)}. Not read: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v),
         f"Gettable: {sum(r['gettable'] for r in R)}/{len(R)}.", "",
         "JUDGED - NBA totals, alerted 4h+ before tip:",
         f"   {st_(rule)}",
         f"   all plays incl. not gettable (alert price): {st_(rule, False)}",
         f"   gettable plays at the best price found: "
         + (f"{sum(r['u_best'] for r in rule if r['u_best'] is not None):+.2f}u" if any(r['u_best'] is not None for r in rule) else "n0"),
         "", "INSIDE THE RULE (gettable):"]
    for nm, f in (("Under", lambda r: r["side"] == "UNDER"), ("Over", lambda r: r["side"] == "OVER"),
                  ("4-12h", lambda r: r["lead"] < 12), ("12h+", lambda r: r["lead"] >= 12),
                  ("size 2x+", lambda r: (r["size_x"] or 0) >= 2), ("size 1.5-2x", lambda r: 1.5 <= (r["size_x"] or 0) < 2),
                  ("size <1.5x", lambda r: (r["size_x"] or 0) < 1.5), ("quiet", lambda r: r["quiet"]),
                  ("sharp agrees", lambda r: r["agree"]), ("pulled", lambda r: r["pulled"]), ("stayed", lambda r: not r["pulled"]),
                  ("Kalshi trigger", lambda r: r["book"] == "kalshi"), ("Polymarket trigger", lambda r: r["book"] == "polymarket"),
                  ("Pinnacle limit rising 1.5x+ (vs 2h before)", lambda r: (r["lim_x"] or 0) >= 1.5),
                  # Nov 5: renamed. This is the COMPLEMENT of the rising bucket (lim_x < 1.5), not a flat-limit read -
                  # on the Nov 4 CSV the per-play edge is higher in the 1.0-1.5x band than at <= 1.0x, so the old name
                  # ("not rising") invited a mechanism that is not there. Treat it as a threshold artifact.
                  ("Pinnacle limit not rising 1.5x+ (complement, NOT a flat-limit read)", lambda r: r["lim_x"] is not None and r["lim_x"] < 1.5),
                  ("no Pinnacle limit read", lambda r: r["lim"] is None),
                  # Nov 4 (Peter + Muse): the print-size split. On the board's own close, NBA totals 4h+ with a
                  # 25-50k print is +18.22u on 80 (both halves) while 50k+ is negative. These rows grade that same
                  # split at the ALERT price against PINNACLE'S no-vig close - the test that decides whether the
                  # candidate cell is a lane or a hot streak.
                  ("print under 25k", lambda r: (r["nm"] or 0) < 25_000),
                  ("print 25-50k  <= THE CANDIDATE", lambda r: 25_000 <= (r["nm"] or 0) < 50_000),
                  ("print 50-100k", lambda r: 50_000 <= (r["nm"] or 0) < 100_000),
                  ("print 100k+", lambda r: (r["nm"] or 0) >= 100_000),
                  ("print 25-50k, unders", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["side"] == "UNDER"),
                  ("print 25-50k, overs", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["side"] == "OVER"),
                  ("print 25-50k, quiet (no sharp tag)", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["quiet"]),
                  ("print 25-50k, 4-12h", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["lead"] < 12),
                  ("print 25-50k, 12h+", lambda r: 25_000 <= (r["nm"] or 0) < 50_000 and r["lead"] >= 12)):
        L.append(f"   {nm}: {st_([r for r in rule if f(r)])}")
    lims = sorted(r["lim"] for r in rule if r["lim"])
    if len(lims) >= 9:
        t1, t2 = lims[len(lims) // 3], lims[(2 * len(lims)) // 3]
        L.append(f"   Pinnacle limit low (<= {t1:,.0f}): {st_([r for r in rule if r['lim'] and r['lim'] <= t1])}")
        L.append(f"   Pinnacle limit mid: {st_([r for r in rule if r['lim'] and t1 < r['lim'] <= t2])}")
        L.append(f"   Pinnacle limit high (> {t2:,.0f}): {st_([r for r in rule if r['lim'] and r['lim'] > t2])}")
    L += ["", "NBA totals under 4h (the rule's excluded side):",
          f"   {st_([r for r in R if r['lg'] == 'NBA' and r['mk'] == 'total' and r['lead'] is not None and r['lead'] < 4])}",
          "", "BY LEAGUE x MARKET (descriptive, all leads, gettable):"]
    for lg in LEAGUES:
        for mk in ("total", "moneyline", "spread"):
            xs = [r for r in R if r["lg"] == lg and r["mk"] == mk]
            if xs:
                L.append(f"   {lg} {mk}: {st_(xs)}")
    ag = [r for r in rule if r["own_clv"] is not None]
    if ag:
        L += ["", f"CHECK - exchange close vs Pinnacle close on the rule's plays: exchange CLV {stt.mean(r['own_clv'] for r in ag):+.2f}c, "
                  f"Pinnacle CLV {stt.mean(r['clv'] for r in ag):+.2f}% (n {len(ag)})"]
    def st_k(xs):
        """The same statistics as st_(), on the CAUSAL basis (gettable decided without future information)."""
        g = [x for x in xs if x.get("get_k")]
        if not g:
            return f"n {len(xs)} | gettable 0"
        u = sum(x["u"] for x in g)
        cv = [x["clv"] for x in g]
        h1 = [x for x in g if x["day"] <= FIT_END]
        h2 = [x for x in g if x["day"] > FIT_END]
        pp = lambda z: f"{sum(x['u'] for x in z) / len(z):+.3f} (n{len(z)})" if z else "n0"
        return (f"n {len(xs)} | gettable {len(g)} | {sum(x['u'] > 0 for x in g)}-{sum(x['u'] < 0 for x in g)} "
                f"{u:+.2f}u {u / len(g):+.3f}/play | Pinnacle CLV {stt.mean(cv):+.2f}% "
                f"beat {100 * sum(v > 0 for v in cv) / len(cv):.0f}% | H1 {pp(h1)} H2 {pp(h2)}")

    gh_ = sum(1 for r in R if r["gettable"])
    gk_ = sum(1 for r in R if r.get("get_k"))
    gr_ = sum(1 for r in R if r.get("get_r"))
    flip = [r for r in R if bool(r["gettable"]) != bool(r.get("get_k"))]
    agk = [r["age_k"] for r in R if r.get("age_k") is not None]
    L += ["", "=== CAUSAL BASIS v2 (NEW; every figure above is the ORIGINAL hindsight basis and is unchanged) ===",
          "Causal = a quote is rejected only against Pinnacle's no-vig fair at the quote's OWN timestamp. No future data.",
          f"Judged-row membership, of {len(R)} read plays: gettable under hindsight {gh_}, causal {gk_}, raw {gr_}.",
          f"  Plays whose membership FLIPS between the hindsight and causal bases: {len(flip)}.",
          "AVAILABILITY is reported separately and forms no part of any basis (Peter Nov 4 22:50): a causal pass is",
          "  NOT an executable fill. Exchange quote age, Pinnacle quote age and in-window publication stay distinct:",
          f"  median exchange quote age on the causal pick {(f'{stt.median(agk):.0f}s' if agk else '-')}; quotes that",
          f"  actually published inside the {GET_SEC}s window {sum(r.get('fresh') or 0 for r in R)}"
          f"/{sum(r.get('seen') or 0 for r in R)}; Pinnacle's own age per row in pin_age_at_exec_min.",
          f"GATE 1 on the causal basis - NBA totals, 4h+ before tip: {st_k(rule)}",
          f"  print 25-50k (the candidate) on the causal basis: "
          f"{st_k([r for r in rule if 25_000 <= (r['nm'] or 0) < 50_000])}"]

    # Nov 6 (Peter): the candidate DEDUPLICATED on event_id.py's canonical identity, first alert kept. Two views:
    # one play per game total (event + market; first side stays, the v3 rule's intent) and one per exact bet
    # (event + market + side + line). Rows whose identity does not resolve are kept and counted, never dropped.
    def _dedupe(xs, key):
        seen_, out_, unres = set(), [], 0
        for r_ in sorted(xs, key=lambda z: z.get("at") or ""):
            k_ = key(r_)
            if k_ is None:
                unres += 1
                out_.append(r_)
                continue
            if k_ in seen_:
                continue
            seen_.add(k_)
            out_.append(r_)
        return out_, unres
    cand = [r for r in rule if 25_000 <= (r["nm"] or 0) < 50_000]
    d_ev, u_ev = _dedupe(cand, lambda r: (r["ekey"], r["mk"]) if r.get("ekey") else None)
    d_bt, u_bt = _dedupe(cand, lambda r: r.get("bkey"))
    L += ["", f"CANDIDATE DEDUPED (event_id.py, first alert kept) - print 25-50k, NBA totals 4h+ | before dedupe {len(cand)} rows:",
          f"  one per game total (event + market): {len(d_ev)} plays, {len({r['ekey'] for r in d_ev if r.get('ekey')})} distinct games"
          f"{f', {u_ev} unresolved kept' if u_ev else ''}",
          f"     hindsight basis: {st_(d_ev)}", f"     causal basis:    {st_k(d_ev)}",
          f"  one per exact bet (event + market + side + line): {len(d_bt)} plays{f', {u_bt} unresolved kept' if u_bt else ''}",
          f"     hindsight basis: {st_(d_bt)}", f"     causal basis:    {st_k(d_bt)}"]
    L.append(f"\nHistory cache: hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}; OddsPapi calls {len(cl.CALLS)} "
             f"(billable {cl.STATS['billable']}).")
    L += ["", f"PER-PLAY EXPORT attached: {len(X)} rows - every qualifying play, including the {len(X) - len(R)} not fully read.",
          "Columns: " + ", ".join(EXPORT_COLS)]
    try:
        send_csv("Bets LIQUIDITY vs HISTORY (paper) + per-play export", "\n".join(L), X,
                 f"liq_history_perplay_{now.astimezone(ET):%Y%m%d_%H%M}.csv")
    except Exception as exn:   # the report must still arrive even if the attachment fails
        print(f"per-play export failed: {str(exn)[:80]}")
        ex.send("Bets LIQUIDITY vs HISTORY (paper)" + (" - FROZEN BOARD PLAYS" if (os.environ.get("LIQH_FROZEN") or "") == "1" else ""), "\n".join(L))
    print("liq history test: not read -> " + ", ".join(f"{k} {v}" for k, v in miss.items() if v))   # Nov 5: why, in the log
    print(f"liq history test: scope {len(A)}, read {len(R)}, gettable {sum(r['gettable'] for r in R)}, "
          f"rule {len(rule)}, cache hits {hc.STATS['hit']}, downloads {hc.STATS['miss']}")   # counts only


if __name__ == "__main__":
    main()

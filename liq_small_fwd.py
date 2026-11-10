#!/usr/bin/env python3
"""
$25-50k NBA LIQUIDITY - FORWARD PAPER TEST (Nov 6, 2026; Peter: "move it forward now"). PAPER ONLY. Lane 1 unchanged;
the candidate stays paper until Peter approves. Reads, never places: no order, no alert, no executor input.

CANDIDATE (the historical 34): a Bets Board v3 PLAY (NBA total, 4h+ before tip, money still there, one per game total,
cap 5) whose liquidity print (new_money) is $25,000 - $49,999.
EXECUTION SOURCE: the executor's existing Lane 3 shadow. Every board PLAY is already priced there against the LIVE order
books of ProphetX / Novig / Kalshi / Polymarket US at decision time, with the same routing, -130 cap and $200 unit as live
money, and written to the LEDGER in its "Bets LIVE:" email at that moment. This script only reads those ledger rows, so
every price is the one that was really up when the decision was made - no hindsight, no later re-pricing, no stale quote
(the books are read live at the decision; the age reported is decision time minus the alert, i.e. how old the alert
number was by the time we could act).
FORWARD ONLY: decisions made at or after FWD_START. One row per canonical event + market (event_id.py), first decision kept.
PER OPPORTUNITY: alert price, real best available price + book + line, decision age, depth at that price vs the $200-unit
stake, estimated fill (full / partial / none), SIMULATED vs CONFIRMED execution (confirmed = a real order fill in the
ledger; none expected while paper), Pinnacle no-vig close CLV at the fill line and price, and the result at the fill.
Daily private email; the log prints counts only.
"""
import json
import os
import statistics as stt
from datetime import datetime, timedelta, timezone

import board_build as bb
import clv_ledger as cl
import event_id as eid
import executor as ex
import exchange_lag as el
import finals as fin
import hist_cache as hc
import nba_names as nn
import tracker_build as tb

ET = tb.ET
FWD_START = os.environ.get("LSF_START", "") or "2026-11-06T11:00:00Z"
LO, HI = 25_000, 50_000
# LIVE_UNIT 200 -> 300, commit 901dbd9b6, 2026-11-09T15:52:34Z (verified from git, not assumed).
UNIT_CHANGE = datetime(2026, 11, 9, 15, 52, 34, tzinfo=timezone.utc)


def unit_for(decided_utc):
    """The unit that was actually live when this row was decided. 200 before the change, 300 after."""
    t = cl.tp(decided_utc) if decided_utc else None
    return 300.0 if (t and t >= UNIT_CHANGE) else 200.0
SLUG = {"novig": "novig.us", "prophetx": "prophetx", "kalshi": "kalshi", "polymarket_us": "polymarket.us"}


def am_dec(a):
    return None if a in (None, 0) else (1 + (a / 100 if a > 0 else 100 / abs(a)))


def ledger_rows():
    M = ex.imap_open()
    out = []
    try:
        since = (datetime.fromisoformat(FWD_START.replace("Z", "+00:00")) - timedelta(days=1)).strftime("%d-%b-%Y")
        typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", since)
        for uid in (data[0].split() if typ == "OK" and data and data[0] else []):
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
            out += [r for r in led if r.get("source") == "board" and (r.get("decided_utc") or "") >= FWD_START]
    finally:
        ex.imap_close(M)
    return out


def match_alert(r, alerts):
    """The liquidity alert behind a board ledger row: same alert time, NBA total, same side, same line."""
    sd = (r.get("key") or "").rsplit("|", 1)[-1]
    for a in alerts:
        if (a.get("alerted_utc") == r.get("alert_utc") and a.get("league") == "NBA" and a.get("market") == "total"
                and (a.get("side") or "").upper() == sd and a.get("line") == r.get("alert_line")):
            return a
    return None


def build(rows, alerts):
    first = {}
    for r in sorted(rows, key=lambda z: z.get("decided_utc") or ""):
        a = match_alert(r, alerts)
        if not a or not (LO <= (a.get("new_money") or 0) < HI):
            continue
        ek, _ = eid.event_key("NBA", a.get("teams"), a.get("start_utc"), a.get("game"))
        k = (ek or f"unresolved|{a.get('game')}|{a.get('start_utc')}", "total")
        first.setdefault(k, (r, a))
    return list(first.values())


def pin_clv(a, r, st, mkmap):
    """Pinnacle no-vig close at the FILL line x the fill after-fee price - 1 (%); None until the game's history is final."""
    sd = (a.get("side") or "").upper()
    line = r.get("fill_line") if r.get("fill_line") is not None else a.get("line")
    dec = am_dec(r.get("fill_price_after_fee"))
    if not dec or line is None:
        return None
    b = {"bet": f"{'Over' if sd == 'OVER' else 'Under'} {float(line):g}", "league": "NBA", "game": (a.get("game") or "").split(":")[0],
         "game_start": a.get("start_utc"), "book": a.get("book")}
    tms = nn.teams_of(a)
    if tms:
        b["teams"] = tms
    fid = cl.find_fixture(st, b)
    if not fid:
        return None
    f = st["fixtures"][fid]
    start = cl.tp(f["start"]) or cl.tp(a.get("start_utc"))
    if not start or datetime.now(timezone.utc) - start < hc.FINAL_AFTER:
        return None
    h = hc.get_hist(fid, ["pinnacle"], start)
    if isinstance(h, dict) and h.get("_error"):
        return None
    c, _ = cl.close_for(b, f, cl.book_markets(h, "pinnacle"), mkmap, start, "NBA")
    return round(100 * (c["p"] * dec - 1), 2) if c else None


def result_at_fill(a, r):
    sd = (a.get("side") or "").upper()
    line = r.get("fill_line") if r.get("fill_line") is not None else a.get("line")
    x = {"league": "NBA", "type": "totals", "side": "Over" if sd == "OVER" else "Under", "line": line,
         "game": (a.get("game") or "").split(":")[0], "start": a.get("start_utc")}
    try:
        return fin.result(x)
    except Exception:
        return None


def row_view(r, a, clv):
    # PER-ROW STAKE, not a hardcoded 200 (Peter, Nov 10). LIVE_UNIT went 200 -> 300 in commit
    # 901dbd9b6 at 2026-11-09T15:52:34Z, and FWD_START is Nov 6 - so this forward cohort SPANS the
    # change. The old code printed "$200 unit" for every row, which mislabelled every decision made
    # after Nov 9.
    #
    # WHAT IS NOT TOUCHED: the fill classification. fill_avail / fill_partial come from the LEDGER
    # (executor.py:1058 computes fillable=min(avail, risk) and partial=avail<risk against the stake
    # that was actually live at that decision), so each row's full/partial/none is already correct
    # for its own era. This only labels the stake honestly; it does not recompute anything.
    unit_risk = None
    fa = r.get("fill_price_after_fee")
    if fa is not None:
        u = unit_for(r.get("decided_utc"))
        unit_risk = u if fa > 0 else round(u * abs(fa) / 100, 2)
    filled = bool((r.get("live_order") or {}).get("filled_stake"))
    placed = r.get("verdict") == "WOULD PLACE" and fa is not None
    depth = r.get("fill_avail")
    fill = ("none" if not placed else
            ("unknown depth" if depth is None else ("full" if not r.get("fill_partial") else f"partial ${depth:,.0f}")))
    res = result_at_fill(a, r) if placed else None
    dec = am_dec(fa)
    u = None if res is None or not dec else (dec - 1 if res == "W" else (-1.0 if res == "L" else 0.0))
    return {"day": cl.tp(r["decided_utc"]).astimezone(ET).strftime("%Y-%m-%d"), "game": (a.get("game") or "").split(":")[0],
            "bet": f"{(a.get('side') or '').title()} {a.get('line')}", "print": a.get("new_money"),
            "alert": r.get("alert_price_after_fee"), "fill_book": r.get("fill_book"), "fill_line": r.get("fill_line"),
            "fill": fa, "age_min": round((r.get("latency_s") or 0) / 60), "unit_risk": unit_risk, "depth": depth,
            "est_fill": fill, "status": "CONFIRMED" if filled else ("SIMULATED" if placed else "NO FILL"),
            "skip": None if placed else (r.get("reason") or r.get("verdict")), "clv": clv, "res": res, "u": u,
            "slip_c": (None if fa is None or r.get("alert_price_after_fee") is None else
                       round(100 * (1 / am_dec(fa) - 1 / am_dec(r["alert_price_after_fee"])), 1))}


def summarise(V):
    n = len(V)
    sim = [v for v in V if v["status"] in ("SIMULATED", "CONFIRMED")]
    full = [v for v in sim if v["est_fill"] == "full"]
    g = [v for v in sim if v["u"] is not None]
    cv = [v["clv"] for v in sim if v["clv"] is not None]
    sl = [v["slip_c"] for v in sim if v["slip_c"] is not None]
    u = sum(v["u"] for v in g)
    return (f"opportunities {n} | executable at decision {len(sim)} ({len(full)} full-unit fills) | no fill {n - len(sim)}\n"
            f"  confirmed executions {sum(v['status'] == 'CONFIRMED' for v in V)} | simulated {sum(v['status'] == 'SIMULATED' for v in V)}\n"
            f"  graded {len(g)}: {sum(v['u'] > 0 for v in g)}-{sum(v['u'] < 0 for v in g)} {u:+.2f}u"
            + (f" ({u / len(g):+.3f}/play)" if g else "") + " at the real fill price\n"
            + f"  Pinnacle CLV at fill: " + (f"{stt.mean(cv):+.2f}% (n {len(cv)}, beat close {sum(c > 0 for c in cv)}/{len(cv)})" if cv else "n/a yet")
            + "\n  raw price vs alert price: " + (f"{stt.mean(sl):+.1f}c avg (+ = paid more; the fill line can differ from the alert line)" if sl else "n/a"))


def main():
    rows = ledger_rows()
    alerts = bb.load()
    P = build(rows, alerts)
    st = {"billable": {}}
    # Nov 6 (Peter): reuse the fixtures the CLV ledger already paid for instead of re-buying them.
    # This started from a bare dict, so every run bought /fixtures data already on disk - and with
    # this script now registered in tick at a daily cadence that was about to become a standing
    # charge. Read-only: nothing here saves that state. Needs TRACKER_PASSPHRASE in the workflow;
    # without it the decrypt fails, this falls through, and the calls are bought silently - which is
    # exactly how plimit-level spent 5 unapproved credits on Nov 6.
    try:
        _prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(_prev.get("fixtures") or {})
        st["fx_last"] = dict(_prev.get("fx_last") or {})
        print(f"fixture cache: reusing {len(st['fixtures'])} fixtures - no re-purchase")
    except Exception as _e:
        print(f"fixture cache: unavailable ({type(_e).__name__}) - fixtures will be fetched")
    now = datetime.now(timezone.utc)
    mkmap = cl.load_markets(st, now) if cl.KEY else {}
    if cl.KEY and P:
        cl.refresh_fixtures(st, now, "NBA", (cl.tp(FWD_START) - timedelta(days=1)).astimezone(ET), (now + timedelta(days=1)).astimezone(ET))
    V = []
    for r, a in P:
        try:
            clv = pin_clv(a, r, st, mkmap) if cl.KEY else None
        except Exception:
            clv = None
        V.append(row_view(r, a, clv))
    today = now.astimezone(ET).strftime("%Y-%m-%d")
    L = [f"$25-50k NBA LIQUIDITY - FORWARD PAPER TEST | {now.astimezone(ET):%a %b %d %I:%M %p} ET | since {FWD_START}",
         "Candidate: board v3 PLAY (NBA total 4h+) with a $25-50k print. Prices = the executor's live-book read at decision (Lane 3",
         "shadow ledger): no hindsight, no re-pricing. Paper only; Lane 1 unchanged. One row per game total (event_id.py).", "",
         "SINCE START:", "  " + summarise(V), "",
         f"YESTERDAY + TODAY:", "  " + summarise([v for v in V if v["day"] >= (now - timedelta(days=1)).astimezone(ET).strftime("%Y-%m-%d")]), "",
         "EVERY OPPORTUNITY (oldest first):"]
    for v in V:
        L.append(f"  {v['day']} {v['game']} | {v['bet']} | print ${(v['print'] or 0):,.0f} | alert {v['alert']:+d} | "
                 + (f"real {v['fill']:+d} {v['fill_book']} {v['fill_line']} | age {v['age_min']}m | unit risk ${v['unit_risk']:,.0f} | "
                    f"depth {('$' + format(v['depth'], ',.0f')) if v['depth'] is not None else 'n/a'} | fill {v['est_fill']}"
                    if v["fill"] is not None else f"no fill ({v['skip']}) | age {v['age_min']}m")
                 + f" | {v['status']} | CLV {('%+.2f%%' % v['clv']) if v['clv'] is not None else 'pending'}"
                 + f" | {v['res'] or 'pending'}" + (f" {v['u']:+.2f}u" if v["u"] is not None else ""))
    if not V:
        L.append("  none yet")
    L += ["", "Read: depth n/a = decided before the ledger carried fill depth (Nov 6). Age = minutes from the alert to our decision."]
    ex.send(f"Bets LIQ $25-50k NBA FORWARD (paper) - {today}", "\n".join(L))
    print(f"liq small fwd: ledger board rows {len(rows)}, candidate opportunities {len(V)}")   # counts only


if __name__ == "__main__":
    main()

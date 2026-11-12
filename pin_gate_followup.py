#!/usr/bin/env python3
"""
PINNACLE GATE - FOLLOW-UP AFTER THE REJECT (Muse, Nov 12, relayed by Peter). READ-ONLY.

NO deployment. No change to a live gate, pricing, routing, sizing, venue priority or risk control.
No order. No paid OddsPapi call - every number comes from records already on disk.

Muse's item 2 is NOT re-tested here: it is already settled, by code and by data.
  executor.pin_check() records pin_line and NEVER converts. half_point_value is not imported into
  executor.py at all. 13 of 13 attempts were adjacent-line, mean gap -7.28%. So yes, the existing
  gap calculation compares mismatched lines. Re-running that proves nothing new.

This answers items 1, 3, 5 and 6.

ITEM 1, THE JOIN - and why it is built as a UNIQUENESS TEST rather than a matcher.
Muse: "establish a reliable bet-to-CLV join using existing records. Do not fabricate matches."
No identifier is common to the two records: the CLV ledger keys st["bets"] on the tracker's own bet
id ("mn|..", "px|.."), while the executor's ledger row carries derive_key (SPORT|game|market|side).
tracker_build.bot_match stores no key, and tracker rows carry no order_id. So a join must be built
from natural fields, and the only honest way to present one is with its collision rate: a candidate
set of exactly ONE is evidence, a set of several is ambiguity, and a set of none is absence. That is
the same discipline find_fixture uses - unique winner or None - which is why a wrong fixture never
became a confidently wrong CLV. A join that silently picked the first candidate would be the
fabrication Muse ruled out.

PRICE BASIS IN THE JOIN. The ledger stores fill_price_after_fee (fees already taken) and fill_screen
(the raw screen price). The tracker stores whatever basis the venue uses - a QUOTE for ProphetX, net
MONEY for Novig and Polymarket US. So a price match is accepted against EITHER the screen price or
the after-fee price, within one American point, and which one matched is reported. Insisting on one
basis would reject real matches at quote-basis venues.

ITEM 3, THE CORRECTED ADJACENT COMPARISON. pin_check stored fair_am - Pinnacle's no-vig fair price
at PINNACLE's line. Applying sharp_monitor.half_point_value moves that fair value to OUR line, which
is the comparison the gate was supposed to make. Its uncertainty is reported next to it, and any row
whose verdict is smaller than the conversion that produced it is flagged: there the conversion, not
the price, is deciding, and Muse's item 5 says such a row must not veto a real order.

A LIMITATION THAT CANNOT BE ENGINEERED AWAY: fair_am was stored ROUNDED to a whole American point
(lm.american(fair)), so recovering the probability from it carries up to half a point of error
before any conversion is applied. The corrected gap below is therefore good to roughly a half point,
which is stated with every figure rather than hidden behind a decimal.
"""
import collections
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import executor as ex
import rest_depth_report as rd
import sharp_monitor as sm
import tracker_build as tb

ET = tb.ET
DAYS = int(os.environ.get("PG_DAYS", "") or "30")
TSTATE = "tracker/state.enc"
L = []
MONEY = re.compile(r"\$\s*[+-]?[\d,]+(?:\.\d+)?")


def say(t=""):
    L.append(t)
    if MONEY.search(str(t)):
        print("  [line withheld from the public log: carries a dollar amount]")
        return
    print(t)


def priv(t=""):
    L.append(t)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def mean_ci(v):
    if not v:
        return (None, None)
    m = sum(v) / len(v)
    if len(v) < 2:
        return (m, None)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    return (m, 1.959964 * sd / math.sqrt(len(v)))


def am_to_prob(a):
    a = float(a)
    return (100.0 / (a + 100.0)) if a > 0 else (abs(a) / (abs(a) + 100.0))


def am_to_dec(a):
    a = float(a)
    return 1 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def et_day(v):
    d = cl.tp(v)
    return d.astimezone(ET).strftime("%Y-%m-%d") if d else None


def toks(s):
    return tb.toks(str(s or "")) - tb.WEAK


def placed_legs(r):
    out = []
    lo = r.get("live_order") or {}
    if lo.get("status") == "placed" and lo.get("order_id"):
        out.append(("taker", lo))
    lr = r.get("live_rest") or {}
    if lr.get("status") == "placed" and lr.get("order_id"):
        out.append(("rest", lr))
    for o in (r.get("live_more") or []):
        o = o or {}
        if o.get("status") == "placed" and o.get("order_id"):
            out.append(("more", o))
    return out


def lane_of(r):
    s = str(r.get("source") or "").lower()
    if s.startswith("board"):
        return "Board v3"
    if s.startswith("r1") or s == "lane1":
        return "R1"
    if s == "lane2":
        return "Lane 2"
    return "Phase 1"


def corrected_gap(r, pc):
    """(corrected_gap_pct, conv_pts, conv_value_pct, why) - the comparison the gate SHOULD make.

    Moves Pinnacle's stored no-vig fair value from Pinnacle's line to ours with the existing
    half_point_value, in the same direction close_prob uses, then scores our after-fee price
    against it. Returns (None, ...) rather than a guess whenever a required input is absent."""
    pin_line, ours = num(pc.get("pin_line")), num(r.get("fill_line"))
    fair_am, our_am = num(pc.get("fair_am")), num(r.get("fill_price_after_fee"))
    if fair_am is None or our_am is None:
        return (None, None, None, "no stored fair or fill price")
    key = str(r.get("key") or "")
    parts = key.split("|")
    if len(parts) < 4:
        return (None, None, None, "key not parseable")
    lg, mkt, side = parts[0], parts[2], parts[3]
    p = am_to_prob(fair_am)
    if pin_line is None or ours is None:
        # moneyline, or a line we cannot read: no conversion needed or none possible
        if mkt == "side" and (pin_line is None and ours is None):
            return (100.0 * (p * am_to_dec(our_am) - 1), 0.0, 0.0, "moneyline, no conversion")
        return (None, None, None, "line missing on one side")
    conv = ours - pin_line
    v = 0.0
    if abs(conv) > 1e-9:
        kind = "tot" if mkt == "total" else "spr"
        try:
            v = sm.half_point_value(lg, kind, pin_line, ours, pin_line)
        except Exception as e:
            return (None, conv, None, f"conversion failed ({type(e).__name__})")
        if kind == "tot":
            better = (ours < pin_line) if side.lower().startswith("o") else (ours > pin_line)
        else:
            better = ours > pin_line
        p = p + (v if better else -v)
        p = min(max(p, 0.01), 0.99)
    return (100.0 * (p * am_to_dec(our_am) - 1), conv, 100.0 * v, "")


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    say("PINNACLE GATE FOLLOW-UP - items 1, 3, 5, 6 (item 2 already settled)")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET | window {DAYS}d | fee model {cs.FEE_MODEL}")
    say("READ-ONLY. No deployment, no order, no gate/pricing/routing/sizing/risk change.")
    say("0 paid OddsPapi calls - every figure is replayed from records already on disk.")
    say("=" * 100)

    rows, mails = [], 0
    M = ex.imap_open()
    try:
        for s in rd.SUBJECTS:
            rr, n = rd.ledger_rows(M, s, since)
            rows += rr
            mails += n
    finally:
        try:
            M.logout()
        except Exception:
            pass
    seen = {}
    for r in rows:
        k = r.get("key") or r.get("play_key")
        if not k:
            continue
        cur = seen.get(k)
        if cur is None or (placed_legs(r) and not placed_legs(cur)):
            seen[k] = r
    att = [(k, r, r["pin_check"]) for k, r in seen.items() if isinstance(r.get("pin_check"), dict)]
    say(f"  {mails} email(s), {len(rows)} row(s), {len(seen)} play(s), "
        f"{len(att)} live order attempt(s) with a pin_check")

    # ---------------------------------------------------------------- item 1
    say("")
    say("=" * 100)
    say("ITEM 1 - BET-TO-CLV JOIN, presented as a uniqueness test")
    say("=" * 100)
    cbets, tbets = {}, []
    try:
        cst = cl.tb.dec(json.load(open(cl.STATE)))
        cbets = {k: v for k, v in (cst.get("bets") or {}).items() if v.get("clv") is not None}
    except Exception as e:
        say(f"  CLV ledger unreadable ({type(e).__name__}) - join cannot be tested")
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        tbets = (list(raw.items()) if isinstance(raw, dict)
                 else [(str(i), b) for i, b in enumerate(raw or [])])
    except Exception as e:
        say(f"  tracker unreadable ({type(e).__name__})")
    say(f"  CLV ledger: {len(cbets)} scored row(s) | tracker: {len(tbets)} row(s)")
    say("  identifiers available: CLV keys on the TRACKER bet id; the ledger row carries")
    say("  derive_key (SPORT|game|market|side); tracker rows carry no order_id and bot_match")
    say("  stores no key. So no id is shared and the join must be built from natural fields.")

    def candidates(r):
        """Tracker rows that could be this order attempt. Unique set of 1 = evidence."""
        key = str(r.get("key") or "")
        parts = key.split("|")
        lg = parts[0] if parts else ""
        gt = toks(r.get("game"))
        bk = cs.canon(r.get("fill_book")) if r.get("fill_book") else None
        day = et_day(r.get("decided_utc") or r.get("run_start_utc"))
        scr, aft = num(r.get("fill_screen")), num(r.get("fill_price_after_fee"))
        out = []
        for tk, b in tbets:
            if str(b.get("league") or "").upper() != lg.upper():
                continue
            if bk and b.get("book") and cs.canon(b.get("book")) != bk:
                continue
            bt = toks(b.get("game"))
            if not (bt and gt and (bt & gt)):
                continue
            bd = et_day(b.get("game_start") or b.get("placed") or b.get("first_seen") or b.get("date"))
            if day and bd and abs((datetime.strptime(bd, "%Y-%m-%d")
                                   - datetime.strptime(day, "%Y-%m-%d")).days) > 1:
                continue
            bp = num(b.get("price"))
            if bp is None:
                continue
            basis = None
            if scr is not None and abs(bp - scr) <= 1.0:
                basis = "screen"
            elif aft is not None and abs(bp - aft) <= 1.0:
                basis = "after-fee"
            if basis is None:
                continue
            out.append((tk, b, basis))
        return out

    uniq, none_, multi = [], [], []
    for k, r, pc in att:
        c = candidates(r)
        (uniq if len(c) == 1 else none_ if not c else multi).append((k, r, pc, c))
    tot = len(att)
    say("")
    say(f"  exactly ONE tracker row matches   {len(uniq):4d}" + (f"  ({100*len(uniq)/tot:.0f}%)" if tot else ""))
    say(f"  NO tracker row matches            {len(none_):4d}")
    say(f"  SEVERAL match (ambiguous)         {len(multi):4d}")
    if uniq:
        bb = collections.Counter(c[0][2] for _, _, _, c in uniq)
        say(f"  of the unique matches, price basis that matched: "
            f"{', '.join(f'{a} {b}' for a, b in bb.items())}")
        got = 0
        for k, r, pc, c in uniq:
            tk = c[0][0]
            rec = cbets.get(tk)
            if rec and num(rec.get("clv")) is not None:
                got += 1
        say(f"  of {len(uniq)} uniquely matched attempt(s), {got} carry a certified CLV")
        say("  -> this is the join. It is only usable where the match is unique AND the matched")
        say("     tracker row is itself scored; both counts are above, neither is extrapolated.")
    if multi:
        say("")
        say(f"  the {len(multi)} ambiguous attempt(s) are NOT resolved here - picking one would be")
        say("  the fabricated match Muse ruled out. Each needs a distinguishing field:")
        for k, r, pc, c in multi[:6]:
            say(f"    {str(k)[:52]:<52} {len(c)} candidates")

    # ---------------------------------------------------------------- item 3
    say("")
    say("=" * 100)
    say("ITEM 3 - EXACT LINE vs CORRECTLY CONVERTED ADJACENT LINE")
    say("=" * 100)
    ex_rows, adj_rows, bad = [], [], []
    for k, r, pc in att:
        cg, conv, cv, why = corrected_gap(r, pc)
        if cg is None:
            bad.append((k, why))
            continue
        rec = {"key": k, "row": r, "pc": pc, "raw": num(pc.get("gap_pct")), "cg": cg,
               "conv": conv, "cv": cv, "lane": lane_of(r)}
        (ex_rows if abs(conv or 0) < 1e-9 else adj_rows).append(rec)
    say(f"  exact-line attempts    {len(ex_rows):4d}")
    say(f"  adjacent-line attempts {len(adj_rows):4d}")
    if bad:
        say(f"  not comparable         {len(bad):4d}  ({collections.Counter(w for _, w in bad).most_common(1)[0][0]})")

    for nm, grp in (("EXACT", ex_rows), ("ADJACENT (converted)", adj_rows)):
        if not grp:
            continue
        rawm, rawh = mean_ci([x["raw"] for x in grp if x["raw"] is not None])
        cgm, cgh = mean_ci([x["cg"] for x in grp])
        p_raw = sum(1 for x in grp if (x["raw"] or 0) > 0)
        p_cor = sum(1 for x in grp if x["cg"] > 0)
        say("")
        say(f"  {nm}  n {len(grp)}")
        say(f"    gap as the code computes it (UNCONVERTED): "
            f"{(f'{rawm:+.2f}%' if rawm is not None else 'n/a')}"
            f"{(f' +/-{rawh:.2f}' if rawh is not None else '')}   would PASS {p_raw}/{len(grp)}")
        say(f"    gap with the conversion APPLIED:           "
            f"{(f'{cgm:+.2f}%' if cgm is not None else 'n/a')}"
            f"{(f' +/-{cgh:.2f}' if cgh is not None else '')}   would PASS {p_cor}/{len(grp)}")
        if nm.startswith("ADJACENT"):
            cvs = [abs(x["cv"]) for x in grp if x["cv"] is not None]
            m2, _ = mean_ci(cvs)
            say(f"    the conversion itself is worth {(f'{m2:.2f}%' if m2 is not None else 'n/a')} on average")
            rests = sum(1 for x in grp if x["cv"] is not None and abs(x["cg"]) < abs(x["cv"]))
            say(f"    attempts where |verdict| < |conversion|: {rests} of {len(grp)}")
            say("      -> on those, the CONVERSION decides, not the price. Muse item 5: such a")
            say("         row must not veto a real order.")
            say("    plus up to ~0.5 American point of error inherited from the ROUNDED fair_am")
            say("    that pin_check stored; the figures above cannot be read finer than that.")
        say("    per-attempt detail (line gap, unconverted -> converted):")
        for x in grp[:14]:
            say(f"      {x['lane']:<9} our {num(x['row'].get('fill_line')):>7} vs pin "
                f"{num(x['pc'].get('pin_line')):>7} ({x['conv']:+.1f}) "
                f"{(f'{x['raw']:+.2f}%' if x['raw'] is not None else '  n/a'):>8} -> "
                f"{x['cg']:+.2f}%")

    # ---------------------------------------------------------------- item 5
    say("")
    say("=" * 100)
    say("ITEM 5 - PASS/REFUSE PER LANE, on the CORRECTED comparison")
    say("=" * 100)
    allc = ex_rows + adj_rows
    say(f"  {'lane':<12} {'n':>3} {'PASS':>5} {'REFUSE':>7} {'mean corrected gap':>20}")
    say("  " + "-" * 56)
    for lane in ("Phase 1", "Board v3", "R1", "Lane 2"):
        sub = [x for x in allc if x["lane"] == lane]
        if not sub:
            continue
        p = sum(1 for x in sub if x["cg"] > 0)
        m, h = mean_ci([x["cg"] for x in sub])
        say(f"  {lane:<12} {len(sub):3d} {p:5d} {len(sub)-p:7d} "
            f"{(f'{m:+.2f}%' if m is not None else 'n/a'):>13}"
            f"{(f' +/-{h:.2f}' if h is not None else ''):>7}")
    if allc:
        p = sum(1 for x in allc if x["cg"] > 0)
        say(f"  {'ALL':<12} {len(allc):3d} {p:5d} {len(allc)-p:7d}")

    # realized + CLV, only where the join was unique: Muse item 4
    ok_keys = {k for k, _, _, _ in uniq}
    use = [x for x in allc if x["key"] in ok_keys]
    say("")
    say(f"  defensible realized/CLV subset: {len(use)} of {len(allc)} attempt(s) (unique join only)")
    if use:
        kmap = {k: c[0][0] for k, _, _, c in uniq}
        cv, st_, pl, nres = [], 0.0, 0.0, 0
        for x in use:
            tk = kmap.get(x["key"])
            rec = cbets.get(tk)
            z = num((rec or {}).get("clv"))
            if z is not None:
                cv.append(100.0 * z)
            tr = next((b for t2, b in tbets if t2 == tk), None)
            if tr and tr.get("result") in ("W", "L", "P"):
                st_ += num(tr.get("stake")) or 0.0
                pl += num(tr.get("profit")) or 0.0
                nres += 1
        m, h = mean_ci(cv)
        say(f"    certified CLV: n {len(cv)}, mean "
            f"{(f'{m:+.2f}%' if m is not None else 'n/a')}"
            f"{(f' +/-{h:.2f}' if h is not None else '')}")
        say(f"    graded results available on {nres} of {len(use)}")
        priv(f"    realized (private): staked ${st_:,.2f}, P&L ${pl:+,.2f} over {nres} graded row(s)")
    else:
        say("    none - so realized units and certified CLV per lane remain UNANSWERED, by")
        say("    absence of a defensible join rather than by absence of analysis.")

    # ---------------------------------------------------------------- item 6
    say("")
    say("=" * 100)
    say("ITEM 6 - THE UNCOVERED PATHS: remainder and resting orders")
    say("=" * 100)
    kinds = collections.Counter()
    rest_rows, more_rows = [], []
    for k, r in seen.items():
        for kind, lo in placed_legs(r):
            kinds[kind] += 1
            if kind == "rest":
                rest_rows.append((k, r, lo))
            elif kind == "more":
                more_rows.append((k, r, lo))
    say(f"  placed legs in the window: taker {kinds.get('taker',0)}, "
        f"rest {kinds.get('rest',0)}, remainder {kinds.get('more',0)}")
    say("  WHY these are uncovered, from the call order in executor.py:")
    say("    pin_check(...)      line 3910   <- runs once, before live_order")
    say("    live_order(...)     line 3919   <- covered")
    say("    live_remainder(...) line 3921   <- runs AFTER pin_check: the second venue's leg is")
    say("                                      submitted with no Pinnacle check of its own")
    say("    rest_wanted(...)                <- a resting bid is matched by the book later, with")
    say("                                      the executor not running at all")
    if rest_rows:
        say("")
        say("  resting legs, with what the record does and does not contain:")
        for k, r, lo in rest_rows[:10]:
            say(f"    {str(k)[:46]:<46} book {str(lo.get('book'))[:9]:<9} "
                f"expires {str(lo.get('expires_utc'))[:16]} filled={lo.get('filled_stake')}")
        say("  No Pinnacle read exists for the instant a rested bid filled, in any local record.")
        say("  So Muse item 3's placement-vs-fill price comparison has NO SOURCE here. It is")
        say("  reported unavailable rather than estimated from a later snapshot, which would be")
        say("  exactly the hindsight price the brief forbids.")
    if more_rows:
        say("")
        say(f"  {len(more_rows)} remainder leg(s) went to a second venue after the check:")
        for k, r, lo in more_rows[:10]:
            say(f"    {str(k)[:46]:<46} book {str(lo.get('book'))[:9]:<9} "
                f"status {lo.get('status')} filled={lo.get('filled_stake')}")
        say("  These are reachable in principle: live_remainder could call pin_check per leg with")
        say("  the venue's own price. That is a code change and is NOT made here.")

    say("")
    say("=" * 100)
    try:
        ex.send(f"Bets PIN GATE FOLLOW-UP ({len(att)} attempts, join unique {len(uniq)})",
                "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
    print(f"pin gate follow-up: attempts {len(att)}, join unique {len(uniq)}/{len(att)}, "
          f"exact {len(ex_rows)}, adjacent {len(adj_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

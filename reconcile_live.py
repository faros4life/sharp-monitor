"""reconcile_live.py - one authoritative attribution of every live bot fill (Peter, Nov 27). READ-ONLY, zero API calls.

AUTHORITY: the bot's own order rows in reporting/ledger.enc, attributed by live_ledger.account (registry.row_lane on the
stored order; evidence E1 order id, E2 registry order id, E3 bot wallet + same play). The tracker's display `lane` field
is NOT an attribution source; it is compared against the ledger here so the two reports' disagreement is explained fill
by fill. Nothing is guessed: a fill the ledger cannot place is UNRESOLVED with its reason.

POPULATION: tracker rows with source == "bot" (the bot wallets / bot-linked fills) whose bet date is on or after
live_ledger.START_UTC (12 Nov 2026 00:00 ET). Partial fills of one play merge into one play (game + market + side).

PUBLIC LOG: counts, units, percentages, short row ids. PRIVATE EMAIL: the same plus games, bets, dollars risked and net
profit per strategy, and the venue-settlement check. Nothing financial reaches the log.
"""
import collections
import hashlib
import os
import statistics as st
import sys

import live_ledger as ll

PRIV = []


def say(t=""):
    print(t)
    PRIV.append(t)


def priv(t=""):
    PRIV.append(t)


def rid(i):
    return hashlib.sha1(str(i).encode()).hexdigest()[:7]


def lane_label(b):
    """The tracker's display lane, normalised only for spelling (rules / phase 1 / lane 1 are one label)."""
    s = str(b.get("lane") or "").strip().lower()
    return {"rules": "LANE 1", "phase 1": "LANE 1", "lane 1": "LANE 1", "r1": "R1", "board v3": "BOARD V3",
            "board v4": "BOARD V4", "dogs": "DOGS", "ncs": "NCS"}.get(s, s.upper() or "(no tracker lane)")


def ci(xs):
    if len(xs) < 2:
        return None
    m, se = st.mean(xs), st.stdev(xs) / len(xs) ** 0.5
    return m - 1.96 * se, m + 1.96 * se


def block(name, P, B):
    S = sorted([p for p in P if p.get("res") in ("W", "L", "P")], key=lambda p: p["t"])
    W = S[-50:]
    def stats(xs):
        u = [ll.units(p["am_net"], p["res"]) for p in xs]
        u = [x for x in u if x is not None]
        c = [p["clv"] for p in xs if p.get("clv") is not None]
        risk = sum(float(B[i].get("stake") or 0) for p in xs for i in p.get("rows") or [] if i in B)
        prof = sum(float(B[i].get("profit") or 0) for p in xs for i in p.get("rows") or [] if i in B)
        return {"n": len(xs), "w": sum(p["res"] == "W" for p in xs), "l": sum(p["res"] == "L" for p in xs),
                "p": sum(p["res"] == "P" for p in xs), "u": sum(u), "roi": 100 * sum(u) / len(u) if u else None,
                "clv": st.mean(c) if c else None, "cn": len(c), "ci": ci(c),
                "beat": 100 * sum(x > 0 for x in c) / len(c) if c else None, "risk": risk, "prof": prof}
    def fmt(h):
        roi = "n/a" if h["roi"] is None else f"{h['roi']:+.1f}%"
        clv = "n/a" if h["clv"] is None else (f"{h['clv']:+.2f}% ({h['cn']}/{h['n']} covered, beat {h['beat']:.0f}%"
                                              + (f", 95% [{h['ci'][0]:+.2f},{h['ci'][1]:+.2f}]" if h["ci"] else "") + ")")
        return f"{h['w']}-{h['l']}-{h['p']} | {h['u']:+.2f}u | ROI {roi} | certified CLV {clv}"
    say(f"\n{name}: settled plays {len(S)} (window = last {len(W)})")
    if not W:
        return
    h = len(W) // 2
    for tag, part in (("ALL ", W), ("H1  ", W[:h]), ("H2  ", W[h:])):
        s = stats(part)
        say(f"  {tag} n{s['n']:<3} {fmt(s)}")
        if tag == "ALL ":
            priv(f"        dollars: risked ${s['risk']:,.2f} | net profit ${s['prof']:+,.2f} (tracker venue settlement)")


def main():
    src = ll.load()
    if src is None:
        print("UNANSWERED: TRACKER_PASSPHRASE missing - the ledger cannot be read")
        return 1
    L, B, C = src
    acct = ll.account(L, B, C, ll.feed_alerts())
    start = ll.START_UTC[:10]

    bot = {i: b for i, b in B.items() if str(b.get("source") or "").lower() == "bot"
           and str(b.get("placed") or b.get("first_seen") or b.get("date") or "")[:10] >= start}
    graded = {i for i, b in bot.items() if b.get("result") in ("W", "L", "P")}

    where = {}
    for p in acct["plays"]:
        for i in p.get("rows") or []:
            where[i] = ("PLAY", p["lane"], p)
    for u in acct["unresolved"]:
        for i in u.get("rows") or []:
            where.setdefault(i, ("UNRESOLVED", u.get("lane"), u))
    for m in acct["manual"]:
        for i in m.get("rows") or []:
            where.setdefault(i, ("MANUAL", None, m))

    say("RECONCILIATION - live bot fills from " + start + " (authority: the bot's own order rows, reporting/ledger.enc)")
    say(f"tracker bot rows {len(bot)} | graded {len(graded)} | in a ledger play {sum(where.get(i, ('',))[0] == 'PLAY' for i in bot)}"
        f" | unresolved {sum(where.get(i, ('',))[0] == 'UNRESOLVED' for i in bot)}"
        f" | tracker says bot but ledger calls it manual {sum(where.get(i, ('',))[0] == 'MANUAL' for i in bot)}"
        f" | no ledger order {sum(i not in where for i in bot)}")
    say(f"ledger plays {len(acct['plays'])} | excluded orders {len(acct['excluded'])} | unresolved {len(acct['unresolved'])}")

    say("\nTRACKER DISPLAY LANE vs LEDGER LANE (bot rows; this is the executed-CLV report's label vs the authority)")
    x = collections.Counter((lane_label(b), (where.get(i) or ("NONE", None))[1] or (where.get(i) or ("NONE",))[0])
                            for i, b in bot.items())
    for (t, l), n in sorted(x.items(), key=lambda kv: -kv[1]):
        say(f"  {t:<20} -> {str(l):<14} {n}")

    say("\nPER ROW (id | date | tracker lane | ledger status/lane | result | evidence)")
    for i, b in sorted(bot.items(), key=lambda kv: str(kv[1].get("first_seen") or "")):
        st_, ln, obj = where.get(i) or ("NO LEDGER ORDER", None, {})
        ev = obj.get("evidence") or obj.get("why") or ""
        say(f"  {rid(i)} {str(b.get('first_seen') or b.get('date') or '')[:10]} {lane_label(b):<18} {st_:<11} "
            f"{str(ln or ''):<9} {b.get('result') or '-':<2} {str(ev)[:40]} | {b.get('book')} | lane_src {b.get('lane_src')} "
            f"| order_ref {'yes' if b.get('order_ref') else 'no'} | placed {str(b.get('placed') or b.get('first_seen') or '')[:16]}")
        priv(f"          {b.get('game')} | {b.get('bet')} | {b.get('book')} | stake ${float(b.get('stake') or 0):,.2f} "
             f"| profit ${float(b.get('profit') or 0):+,.2f}")

    say("")
    for ln in ll.lane_summary(acct):
        say(ln)
    for lane in sorted({str(p["lane"]) for p in acct["plays"]}):
        P = [p for p in acct["plays"] if str(p["lane"]) == lane and p.get("res") in ("W", "L", "P")]
        risk = sum(float(B[i].get("stake") or 0) for p in P for i in p.get("rows") or [] if i in B)
        prof = sum(float(B[i].get("profit") or 0) for p in P for i in p.get("rows") or [] if i in B)
        priv(f"  {lane}: dollars risked ${risk:,.2f} | net profit ${prof:+,.2f} (tracker venue settlement, bot rows)")

    # fills vs orders vs plays (Peter, Nov 27)
    inplay = [i for i in bot if where.get(i, ("",))[0] == "PLAY"]
    e4 = sum(1 for p in acct["plays"] if not (p.get("rows") or []))
    say("\nFILLS vs ORDERS vs PLAYS")
    say(f"  FILL  = one tracker settlement row on a bot wallet/order (a partial fill can be several rows)")
    say(f"  ORDER = one bot order row in the ledger (may fill in several legs, or not at all)")
    say(f"  PLAY  = one game + market + side for one strategy; every confirmed-filled order leg on it merges into it")
    say(f"  bot fills since {start}: {len(bot)} = {len(inplay)} inside confirmed plays + "
        f"{sum(1 for i in bot if where.get(i, ('',))[0] == 'UNRESOLVED')} unresolved + {sum(1 for i in bot if i not in where)} with no ledger order")
    rows_all = {i for p in acct["plays"] for i in p.get("rows") or []}
    other = rows_all - set(bot)
    say(f"  {len(inplay)} bot-tagged fills merge into {len({id(where[i][2]) for i in inplay})} plays")
    say(f"  {len(other)} further fills sit in confirmed plays but are NOT tagged source=bot in the tracker (joined by order id,"
        f" E1/E2) -> {len({id(p) for p in acct['plays'] if set(p.get('rows') or []) & other and not set(p.get('rows') or []) & set(bot)})} more plays")
    say(f"  {e4} plays have a confirmed fill on the order row and no tracker row (E4)")
    say(f"  confirmed plays total {len(acct['plays'])} | settled {sum(p.get('res') in ('W', 'L', 'P') for p in acct['plays'])}")
    print("  tracker source of the untagged order-linked fills:",
          dict(collections.Counter(str(B[i].get('source')) for i in other if i in B)))

    say("\nUNRESOLVED / EXCLUDED (counts for nobody), by reason")
    why = collections.Counter()
    for u in acct["unresolved"]:
        why["unresolved: " + str(u.get("why"))[:70]] += 1
    for e in acct["excluded"]:
        why["excluded order: " + str(e.get("why"))[:62]] += 1
    for i in bot:
        if i not in where:
            why["tracker bot row with no ledger order"] += 1
    for k, n in why.most_common():
        say(f"  {n:4d}  {k}")

    # Nov 27 (Peter): two corrections to this block.
    #  1. The window is 23 NOV, not 25 Nov - the day he switched EXEC_DOGS_LIVE on. The 25th is the date of the
    #     $300 spec change, which moved the stake and nothing about what the lane selects. Starting on the 25th
    #     silently dropped the first two days of live signals.
    #  2. The lane's own FIRST-PRINT rule applies: dogs_select takes the first bettable print per game + market
    #     + side over all eligible rows and only that print can qualify. Counting every qualifying print
    #     overstated what the lane could ever have played.
    # The first-print set is built exactly as dogs_select builds it, from the executor's own constants, so the
    # count here cannot drift from the lane.
    DOGS_LIVE_FROM = "2026-11-23"      # Peter flipped the switch ~10:50 AM ET; the $300 unit followed on the 25th
    say(f"\nDOGS - every tracker row on a Dogs alert play since the lane went live ({DOGS_LIVE_FROM}), by source")
    import executor as ex
    import json as _j
    Q = _j.load(open("liquidity/alerts.json"))
    Q = Q if isinstance(Q, list) else Q.get("alerts") or []
    _elig = [x for x in Q if isinstance(x, dict) and not x.get("artifact") and not x.get("close_suspect")
             and str(x.get("book") or "").strip().lower() not in ex.DOGS_NOT_BETTABLE and ex.iso_t(x.get("alerted_utc"))]
    _elig.sort(key=lambda x: ex.iso_t(x.get("alerted_utc")))
    _first = {}
    for x in _elig:
        _first.setdefault((str(x.get("game")).lower(), x.get("market"), str(x.get("side")).lower()), x)
    dg = [x for x in _first.values() if str(x.get("alerted_utc") or "") >= DOGS_LIVE_FROM
          and ex.dogs_qualifies(x) and ex.dogs_bet(x)]
    _laterprints = sum(1 for x in Q if isinstance(x, dict) and str(x.get("alerted_utc") or "") >= DOGS_LIVE_FROM
                       and ex.dogs_qualifies(x)) - sum(1 for x in _first.values()
                                                       if str(x.get("alerted_utc") or "") >= DOGS_LIVE_FROM
                                                       and ex.dogs_qualifies(x))
    hits = collections.Counter()
    for x in dg:
        gt = set(ll.toks(x.get("game")))
        for i, b in B.items():
            if str(b.get("first_seen") or "")[:10] >= DOGS_LIVE_FROM and len(gt & set(ll.toks(b.get("game")))) >= 2 \
                    and set(ll.toks(x.get("side"))) & set(ll.toks(b.get("bet"))):
                hits[(str(b.get("source")), str(b.get("book")), where.get(i, ("NO LEDGER ORDER",))[0])] += 1
    say(f"  playable Dogs signals since {DOGS_LIVE_FROM} (first print per game+market+side, bet readable): {len(dg)}"
        f" | later prints on the same play, which the lane can never take: {_laterprints}"
        f" | tracker rows on those plays: {sum(hits.values())}")
    for k, n in hits.most_common():
        say(f"    source {k[0]:<8} venue {k[1]:<9} ledger {k[2]:<16} {n}")
    dlo = [p for p in acct["plays"] if str(p["lane"]) == "DOGS"] + [e for e in acct["excluded"] if str(e.get("lane")) in ("dogs", "DOGS")]
    say(f"  ledger Dogs orders since 12 Nov: confirmed plays {sum(1 for p in acct['plays'] if str(p['lane']) == 'DOGS')} | "
        f"unfilled/excluded {sum(1 for e in acct['excluded'] if str(e.get('lane')) in ('dogs', 'DOGS'))}")

    say("\nDOGS ORDER ROWS IN THE ENCRYPTED LEDGER (price-gate evidence; no money)")
    n = 0
    for (kind, oid), (_seen, o) in ll.latest(L).items():
        import json as _jj
        if (str(o.get("source") or "").lower() != "dogs" and not str(o.get("key") or "").startswith("dogs|")
                and '"dogs_gate": "' not in _jj.dumps(o) and "Buffalo vs Akron" not in _jj.dumps(o)):
            continue
        n += 1
        lo = o.get("live_order") or {}
        say(f"  {kind} {str(o.get('decided_utc') or '')[:16]} | gate {o.get('dogs_gate')} | tol {o.get('dogs_tol_cents')}c | "
            f"give-back {o.get('dogs_giveback_cents')}c | alert {o.get('alert_price_after_fee')} | book {lo.get('book') or o.get('live_book')}"
            f" | status {lo.get('status')} | dispatched {lo.get('dispatched_utc')} | answered {lo.get('answered_utc')}")
    say(f"  dogs ledger rows: {n}")

    # ------------------------------------------------------------------------------- 12K
    # Same shape as the Dogs block above and for the same reason: a lane that reaches live money
    # must be reconciled from the day the switch is flipped, not from the day someone notices it is
    # missing. The lane's own producer is reused (k12_plays' selector), so the signal count here is
    # the lane's, never a re-implementation that can drift from it. While EXEC_12K_LIVE is off this
    # prints zero orders against a non-zero signal count, which is exactly the expected reading.
    say("\n12K - NFL three-book $12k ML-depth plays, and what reached the ledger")
    try:
        _k12sel, _k12skip = ex.k12_select(Q, ex.datetime.now(ex.timezone.utc))
        _k12ok = [x for x in _k12sel if ex.k12_bet(x)]
        say(f"  playable 12K signals (first qualifying print per matchup, 12-24h out, spread readable):"
            f" {len(_k12ok)} | qualifying rows skipped: {_k12skip}")
    except Exception as _ex12:
        say(f"  12K signal count UNAVAILABLE: {type(_ex12).__name__}: {str(_ex12)[:80]}")
    say(f"  ledger 12K orders: confirmed plays {sum(1 for p in acct['plays'] if str(p['lane']) == '12K')} | "
        f"unfilled/excluded {sum(1 for e in acct['excluded'] if str(e.get('lane')) in ('12k', '12K'))}")
    n12 = 0
    for (kind, oid), (_seen, o) in ll.latest(L).items():
        if str(o.get("source") or "").lower() != "12k" and not str(o.get("key") or "").startswith("12k|"):
            continue
        n12 += 1
        lo = o.get("live_order") or {}
        say(f"  {kind} {str(o.get('decided_utc') or '')[:16]} | alert {o.get('alert_price_after_fee')} | "
            f"book {lo.get('book') or o.get('live_book')} | status {lo.get('status')} | "
            f"dispatched {lo.get('dispatched_utc')} | answered {lo.get('answered_utc')}")
    say(f"  12k ledger rows: {n12}")

    say("\nVENUE SETTLEMENT CHECK (tracker profit vs stake x price x result, bot rows that are graded)")
    bad = 0
    for i in graded:
        b = B[i]
        am, stake, prof = b.get("price"), float(b.get("stake") or 0), float(b.get("profit") or 0)
        try:
            am = float(am)
        except (TypeError, ValueError):
            continue
        exp = {"W": stake * (am / 100 if am > 0 else 100 / abs(am)), "L": -stake, "P": 0.0}[b["result"]]
        if abs(exp - prof) > max(0.05, 0.02 * stake):
            bad += 1
            say(f"  MISMATCH {rid(i)} | {b.get('book')} | {b['result']} | profit / price-implied = "
                f"{(prof / exp) if exp else float('nan'):.3f}")
            priv(f"  MISMATCH {rid(i)} {b.get('game')} {b.get('bet')} {b['result']} stake ${stake:,.2f} "
                 f"profit ${prof:+,.2f} expected ${exp:+,.2f}")
    say(f"  graded bot rows {len(graded)} | profit differs from the price-implied result by >2%: {bad} (detail by email)")

    # identical-results check: the other two reports' per-strategy blocks, captured in-process (no email sent)
    say("\nVERIFY - per-strategy table as printed by last50_report and executed_clv")
    import contextlib, io
    def block_of(lines):
        out, on = [], False
        for t in lines:
            t = t.strip()
            if t.startswith("AUTHORITATIVE LIVE TABLE"):
                on, out = True, [t]
                continue
            if on:
                if t and any(t.startswith(str(p["lane"]) + " ") for p in acct["plays"]):
                    out.append(t)
                else:
                    break
        return out
    mine = block_of(ll.lane_summary(acct))
    import last50_report as L5
    L5.send_report = lambda *a, **k: True
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            L5.main()
        except SystemExit:
            pass
    a = block_of(L5.L)
    import executed_clv as ec
    ec.send_csv = lambda *a, **k: None
    ec.ex.send = lambda *a, **k: None
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            ec.main()
        except SystemExit:
            pass
    b_ = block_of(ec.L)
    for nm, blk in (("last50_report", a), ("executed_clv", b_)):
        say(f"  {nm}: {'IDENTICAL' if blk == mine else 'DIFFERENT'} ({len(blk)} lines vs {len(mine)})")

    if os.environ.get("GMAIL_ADDRESS"):
        try:
            import executor as ex
            ex.send("Bets LIVE RECONCILIATION - authoritative attribution (private)", "\n".join(PRIV))
            print("private email sent")
        except Exception as e:
            print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

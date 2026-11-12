#!/usr/bin/env python3
"""
BET-TO-CLV LINKAGE - READ-ONLY RECONCILIATION (Muse GO, relayed by Peter, Nov 12).

Muse's step 5: "Run read-only reconciliation first, reporting exact matched/unmatched counts per
venue." That is all this does. It writes NOTHING - no tracker row, no CLV record, no historical
value, no live execution, pricing, sizing, routing, notification or risk control. Every venue call
is a GET. No order of any kind is created, amended or cancelled.

NO FUZZY MATCHING ANYWHERE. Every edge below is an equality on an identifier the venue itself
returned. Where an identifier is absent, the row is reported UNMATCHED. No game text, line, price,
stake or timestamp is used to infer a link, and no id is constructed from anything but venue data.

THE CHAIN, and which hop this measures.
  1  venue trade/fill  ->  order_id            present (measured: 100 PX trades, 100 NV trades)
  2  order_id          ->  play key            present: the executor's ledger row carries both
  3  order_id          ->  tracker row id      THE BREAK - this is what is measured here
  4  tracker row id    ->  CLV ledger row      present: st["bets"] is keyed on exactly that id

PROPHETX - the join Muse approved, and why it needs no new field. A ProphetX trade carries BOTH
`id` and `order_id`, and the tracker row is keyed `px|{trade.id}`. So the executor's order_id
reaches the CLV row through two venue-supplied equalities and one key format that already exists:

    executor live_order.order_id
      == trade.order_id      ->  trade.id  ->  "px|{trade.id}"  ->  st["bets"]["px|..."]

NOVIG - what Muse asked, and the better question. Muse asked to verify strike_id <-> outcomeId.
Reading the code first changes the question: /v3/portfolio/fills returns rows carrying `orderId`
(novig_live_order.fills_for matches on exactly that), while the tracker row is keyed
`nv|{marketId}|{outcomeId}` from /v3/portfolio/positions. So if a FILL carries marketId/outcomeId,
Novig joins deterministically with no equivalence to assume at all. This prints the field names on
a real fill and decides from that, rather than assuming either way. If the fields are absent, Novig
is reported UNMATCHED with the missing field named - which is what Muse asked for.

KALSHI / POLYMARKET US - why these are not joined, by construction. Their tracker ids are
`ks|{ticker}|{side}` and `pm|{slug}|{outcome}`: a POSITION, not an order. Several orders on one side
collapse into one row by design, so attaching several orders' CLV to that row would be exactly the
aggregation Muse's item 3 forbids. This counts the collapse instead, which is the evidence for
whether order-level tracking is worth a new field.
"""
import collections
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import executor as ex
import rest_depth_report as rd
import tracker_build as tb

ET = tb.ET
DAYS = int(os.environ.get("LINK_DAYS", "") or "30")
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
    """Email body ONLY - never the public Actions log. This file used say() for everything and had
    no priv(), so the first stake comparison that carried a dollar amount raised NameError and took
    the rest of the report with it: the orders probe, the unfilled ids and the Kalshi/PM section all
    never printed. Amounts belong in the private email; the log gets counts and verdicts."""
    L.append(t)


def legs(r):
    """Every placed order leg on a ledger row, with its container. All three are real orders at a
    venue, so all three are candidates for the join - not only live_order."""
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


def fields_of(rows, n=120):
    """Field names present across a sample, so a missing identifier is NAMED rather than guessed at.
    This is the same evidence positions_check prints for trades."""
    c = collections.Counter()
    for r in rows[:n]:
        if isinstance(r, dict):
            for k in r:
                c[k] += 1
    return sorted(c)


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=DAYS)).strftime("%d-%b-%Y")
    say("BET-TO-CLV LINKAGE - READ-ONLY RECONCILIATION")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET | window {DAYS}d")
    say("Writes nothing. GET only. No order created, amended or cancelled.")
    say("No fuzzy matching: every edge is an equality on a venue-supplied id.")
    say("=" * 100)

    # ------------------------------------------------ the executor's own orders (hops 1-2)
    rows, mails = [], 0
    M = ex.imap_open()
    try:
        for s in rd.SUBJECTS:
            rr, k = rd.ledger_rows(M, s, since)
            rows += rr
            mails += k
    finally:
        try:
            M.logout()
        except Exception:
            pass
    # order_id -> (play key, container, book). Several legs can share a play key; a given order_id
    # belongs to exactly one leg, so this map is one-to-one by construction and needs no tie-break.
    omap = {}
    for r in rows:
        key = r.get("key") or r.get("play_key")
        for kind, lo in legs(r):
            oid = str(lo.get("order_id"))
            if oid and oid not in omap:
                omap[oid] = {"key": key, "kind": kind,
                             "book": cs.canon(lo.get("book")) if lo.get("book") else None}
    say(f"  {mails} ledger email(s), {len(rows)} row(s)")
    say(f"  HOP 2: executor order_id -> play key : {len(omap)} order id(s) carry a play key")
    bybook = collections.Counter(v["book"] or "?" for v in omap.values())
    say(f"    by venue: {', '.join(f'{a} {b}' for a, b in bybook.most_common())}")
    bykind = collections.Counter(v["kind"] for v in omap.values())
    say(f"    by container: {', '.join(f'{a} {b}' for a, b in bykind.most_common())}")

    # ------------------------------------------------ the two state files (hop 4)
    tbets, cbets, call_ = {}, {}, {}
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        tbets = raw if isinstance(raw, dict) else {str(i): b for i, b in enumerate(raw or [])}
    except Exception as e:
        say(f"  tracker unreadable ({type(e).__name__}) - hop 3/4 cannot be measured")
    try:
        cst = cl.tb.dec(json.load(open(cl.STATE)))
        call_ = (cst.get("bets") or {})
        cbets = {k: v for k, v in call_.items() if v.get("clv") is not None}
    except Exception as e:
        say(f"  CLV ledger unreadable ({type(e).__name__})")
    say(f"  tracker rows {len(tbets)} | CLV-scored rows {len(cbets)}")

    # ================================================ PROPHETX
    say("")
    say("=" * 100)
    say("PROPHETX - the deterministic join")
    say("=" * 100)
    px_oids = {o for o, v in omap.items() if v["book"] == "prophetx"}
    say(f"  executor ProphetX order id(s): {len(px_oids)}")
    # px_live.trades() signs with the TRADING key, which this job deliberately is not given - that
    # returned 401 on the first run, which was my error, not a venue problem. positions.py already
    # has the right fallback: the same GET through bc.px_call on the DATA key. Trade keys stay out.
    trades, how = [], ""
    try:
        import book_check as bc
        # px_call sends no Authorization header until _PX["token"] is set, so the first run got a
        # 401 for want of a login, not for want of a permission. positions.py logs in first.
        bc.px_login()
        d = bc.px_call("/v4/mm/get_trades") or {}
        trades = ((d.get("data") or {}).get("trades")) or []
        how = "bc.px_call, data key (read-only)"
    except Exception as e:
        say(f"  ProphetX trades unreadable ({type(e).__name__}: {str(e)[:70]}) - PX join untested")
    if trades:
        say(f"  venue trades read: {len(trades)}  (GET /v4/mm/get_trades via {how})")
        say(f"  trade fields: {', '.join(fields_of(trades))}")

    px_m, px_no_trade, px_no_tracker, px_no_clv = [], [], [], []
    if trades:
        by_order = collections.defaultdict(list)
        for t in trades:
            if t.get("order_id") is not None:
                by_order[str(t["order_id"])].append(t)
        say(f"  trades carrying order_id: {sum(len(v) for v in by_order.values())} "
            f"across {len(by_order)} distinct order id(s)")
        for oid in sorted(px_oids):
            ts = by_order.get(oid) or []
            if not ts:
                px_no_trade.append(oid)
                continue
            # one order can produce several trades (partial fills). EACH trade is its own tracker
            # row, because the tracker keys on the TRADE id - so this is one-to-many by design and
            # every trade is checked, not just the first.
            for t in ts:
                tid = f"px|{t.get('id')}"
                if tid not in tbets:
                    px_no_tracker.append((oid, tid))
                elif tid not in cbets:
                    px_no_clv.append((oid, tid))
                else:
                    px_m.append((oid, tid, omap[oid]["key"]))
        say("")
        say(f"  MATCHED  order -> trade -> tracker -> CLV   {len(px_m):4d}")
        say(f"  UNMATCHED: no venue trade with that order_id {len(px_no_trade):4d}")
        say(f"  UNMATCHED: trade found, no tracker row       {len(px_no_tracker):4d}")
        say(f"  UNMATCHED: tracker row found, not CLV-scored {len(px_no_clv):4d}")
        for oid, tid, key in px_m[:10]:
            say(f"    MATCH {oid} -> {tid} -> {str(key)[:44]}")
        if px_no_trade:
            say(f"    no-trade order ids (order placed but no matching trade in the window):")
            for o in px_no_trade[:8]:
                say(f"      {o}")
        if px_no_tracker:
            for oid, tid in px_no_tracker[:8]:
                say(f"    trade exists, tracker row absent: {oid} -> {tid}")
        if px_no_clv:
            # HOP 4, diagnosed rather than named. These reached the tracker through the approved
            # chain, so linkage is PROVEN for them; the question is why the CLV ledger has not
            # scored them. The ledger keeps unscored rows with their own reason, so it is read
            # rather than guessed.
            say("")
            say("  hop 4 - linked but not CLV-scored. The ledger's own reason per row:")
            for oid, tid in px_no_clv[:10]:
                tr = tbets.get(tid) or {}
                rec2 = call_.get(tid)
                if rec2 is None:
                    why = "absent from the CLV ledger entirely"
                else:
                    why = (str(rec2.get("why") or rec2.get("reason") or "")[:52]
                           or f"present, clv None, tries {rec2.get('tries')}")
                say(f"    {tid[:30]:<30} result {str(tr.get('result') or '-'):<3} {why}")

    # ================================================ NOVIG
    say("")
    say("=" * 100)
    say("NOVIG - is the join deterministic, or is the field genuinely missing?")
    say("=" * 100)
    nv_oids = {o for o, v in omap.items() if v["book"] in ("novig.us", "novig")}
    say(f"  executor Novig order id(s): {len(nv_oids)}")
    say("  Muse asked to verify strike_id <-> outcomeId. The code says the sharper question is")
    say("  whether a FILL carries marketId/outcomeId directly, because the tracker row is keyed")
    say("  nv|{marketId}|{outcomeId} and /v3/portfolio/fills matches on orderId. Field names first:")
    fills = []
    try:
        import novig_signed as nv
        if not nv.ready():
            say("  Novig read key not ready - fills unreadable, Novig join untested")
        else:
            # nv.get returns a dict KEYED BY WALLET, not a bare list - read_positions() unwraps
            # it with d.values(). The first run parsed it as items/fills/data and read 0 rows,
            # which was my error, not an empty account. Both wallets are read, as the executor
            # does: the main one and the auto-place sub-wallet.
            fills = []
            for kid in dict.fromkeys([nv._S["id"],
                                      (os.environ.get("NOVIG_TRADE_KEY_ID") or "").strip()]):
                if not kid:
                    continue
                # PAGINATE. One page is 100 rows; 2 wallets gave 130 fills and every one of the
                # 35 order ids missed, which is what a 30-day order window against a few days of
                # fills looks like. The executor stores Novig's own orderId (novig_live_order:
                # rec["order_id"] = resp.get("orderId")), so the namespace was never the problem.
                after, pages = None, 0
                while pages < 40:
                    pages += 1
                    prm = {"limit": 100, "keyId": kid}
                    if after:
                        prm["after"] = after
                    d = nv.get("/v3/portfolio/fills", prm)
                    got, nxt = [], None
                    for v in (d.values() if isinstance(d, dict) else [d]):
                        if isinstance(v, list):
                            got += v
                        elif isinstance(v, dict):
                            got += v.get("items") or v.get("fills") or v.get("data") or []
                            nxt = nxt or v.get("next")
                    if isinstance(d, dict):
                        nxt = nxt or d.get("next")
                    fills += got
                    if not got or not nxt:
                        break
                    after = nxt
            say(f"  fills read: {len(fills)}  (GET /v3/portfolio/fills)")
            say(f"  FILL FIELDS: {', '.join(fields_of(fills))}")
    except Exception as e:
        say(f"  Novig fills unreadable ({type(e).__name__}: {str(e)[:60]}) - join untested")

    if fills:
        f0 = fields_of(fills)
        has_mk = any(k in f0 for k in ("marketId", "market_id"))
        has_oc = any(k in f0 for k in ("outcomeId", "outcome_id"))
        has_st = any(k in f0 for k in ("strikeId", "strike_id"))
        say("")
        say(f"  marketId on a fill  : {has_mk}")
        say(f"  outcomeId on a fill : {has_oc}")
        say(f"  strike_id on a fill : {has_st}")
        if has_mk and has_oc:
            say("  -> DETERMINISTIC. The fill itself carries both halves of the tracker key, so no")
            say("     strike_id/outcomeId equivalence has to be assumed at all.")
            nv_m, nv_nf, nv_nt, nv_nc = [], [], [], []
            byo = collections.defaultdict(list)
            for f in fills:
                oid = str(f.get("orderId") or f.get("order_id") or "")
                if oid:
                    byo[oid].append(f)
            # A fill carries THREE ids: orderId, clientId and fillId. The executor stores orderId,
            # but proving a miss means showing the id is absent from all three, not just the one we
            # expect - otherwise a namespace mix-up reads as a missing fill.
            alt = {k: collections.Counter() for k in ("orderId", "clientId", "fillId")}
            for f in fills:
                for k in alt:
                    if f.get(k) is not None:
                        alt[k][str(f[k])] += 1
            for k in ("orderId", "clientId", "fillId"):
                hit = sum(1 for o in nv_oids if o in alt[k])
                say(f"  executor order ids present as fill.{k:<9}: {hit} of {len(nv_oids)}")
            # THE CORRECTION. 0 of 35 executor ids appeared as fill.orderId and 28 of 35 appeared
            # as fill.clientId, and two of the ProphetX ids are literally "intent-<hex>" -
            # journal_intent's own format. So what the ledger stores in live_order.order_id is the
            # CLIENT id the executor generated, not the venue's order id. The id was on both sides
            # all along; the reader compared the wrong pair. Join on clientId, fall back to orderId.
            byc = collections.defaultdict(list)
            for f in fills:
                for k in ("clientId", "client_id", "orderId", "order_id"):
                    v = f.get(k)
                    if v is not None:
                        byc[str(v)].append(f)
            # PARTIAL FILLS: one client id can have several fills. They are summed ONCE per order
            # below, never counted per fill, so a resting order that filled in pieces is one
            # reconciliation - not N.
            for oid in sorted(nv_oids):
                fs = byc.get(oid) or byo.get(oid) or []
                if not fs:
                    nv_nf.append(oid)
                    continue
                # every fill of one order must point at the same market+outcome; if it does not,
                # the id is ambiguous and the order is left unresolved rather than joined
                tids = {f"nv|{f.get('marketId') or f.get('market_id')}|"
                        f"{f.get('outcomeId') or f.get('outcome_id')}" for f in fs}
                if len(tids) != 1:
                    nv_nt.append((oid, f"AMBIGUOUS: {len(tids)} market/outcome pairs"))
                    continue
                tid = tids.pop()
                qty = sum(int(f.get("qty") or 0) for f in fs)
                cost = sum(float(f.get("cost") or 0) for f in fs)
                if tid not in tbets:
                    nv_nt.append((oid, tid))
                elif tid not in cbets:
                    nv_nc.append((oid, tid, len(fs), qty, cost))
                else:
                    nv_m.append((oid, tid, omap[oid]["key"], len(fs), qty, cost))
            say("")
            say(f"  MATCHED  order -> fill -> tracker -> CLV   {len(nv_m):4d}")
            say(f"  FILLED, no fill row for that id            {len(nv_nf):4d}   <- UNFILLED or UNRESOLVED")
            say(f"  FILLED, fill found but no tracker row      {len(nv_nt):4d}")
            say(f"  FILLED, tracker row found but not scored   {len(nv_nc):4d}")
            # Muse item 5: fills must reconcile to stake, price and quantity with no double-count.
            # Novig cost is qty x price x 1c, so stake = cost; the tracker's stake is the check.
            say("")
            say("  fills vs the tracker's own stake (partials summed ONCE per order):")
            for oid, tid, key, nf, qty, cost in nv_m[:14]:
                tr = tbets.get(tid) or {}
                ts = tr.get("stake")
                agree = ("n/a" if ts is None else
                         "AGREES" if abs(float(ts) - cost) <= 0.02 else "DIFFERS")
                say(f"    {oid[:26]:<26} {tid[:30]:<30} fills {nf:2d} qty {qty:5d} -> {agree}")
                if ts is not None and agree == "DIFFERS":
                    priv(f"      fill cost ${cost:,.2f} vs tracker stake ${float(ts):,.2f}")
            for oid, tid, nf, qty, cost in nv_nc[:10]:
                say(f"    not CLV-scored: {oid[:24]:<24} {tid[:30]:<30} fills {nf:2d} qty {qty:5d}")
            for oid, tid in nv_nt[:8]:
                say(f"    no tracker row: {oid[:24]:<24} {str(tid)[:40]}")
            if nv_nf:
                say("")
                say("  the ids with no fill row at all - UNFILLED vs UNRESOLVED is NOT decided here:")
                say("  deciding it needs the venue's ORDER status, and order_state() in")
                say("  novig_live_order signs with the TRADING key, which this job is deliberately")
                say("  not given. A read-only /v3/portfolio/orders probe is tried below instead.")
                for oid in nv_nf[:10]:
                    say(f"    {oid}")
            # UNFILLED vs UNRESOLVED, without the trading key. If the READ key can list orders,
            # the order's own status settles it; if the endpoint refuses, that is reported and the
            # split stays undecided rather than inferred from the absence of a fill.
            if nv_nf:
                try:
                    od = nv.get("/v3/portfolio/orders", {"limit": 100})
                    orders = []
                    for v in (od.values() if isinstance(od, dict) else [od]):
                        if isinstance(v, list):
                            orders += v
                        elif isinstance(v, dict):
                            orders += v.get("items") or v.get("orders") or v.get("data") or []
                    say("")
                    say(f"  read-only orders probe: {len(orders)} order(s)")
                    if orders:
                        say(f"  ORDER FIELDS: {', '.join(fields_of(orders))}")
                        idx = {}
                        for o in orders:
                            for k in ("clientId", "client_id", "orderId", "order_id", "id"):
                                if o.get(k) is not None:
                                    idx.setdefault(str(o[k]), o)
                        hit = [(o2, idx[o2]) for o2 in nv_nf if o2 in idx]
                        say(f"  of {len(nv_nf)} unfilled-or-unresolved ids, {len(hit)} found in orders")
                        for o2, rec2 in hit[:10]:
                            st2 = rec2.get("status") or rec2.get("state")
                            fq = rec2.get("filledQty") or rec2.get("filled_qty")
                            say(f"    {o2[:26]:<26} status {str(st2)[:14]:<14} filledQty {fq}")
                        if hit:
                            say("  -> these are now classifiable: a status with no fill and no")
                            say("     filledQty is UNFILLED; anything else stays UNRESOLVED.")
                except Exception as e:
                    say("")
                    say(f"  orders probe refused ({type(e).__name__}: {str(e)[:50]})")
                    say("  -> UNFILLED vs UNRESOLVED stays UNDECIDED. Deciding it needs either the")
                    say("     trading key in a read-only job (Peter's call - it is the key that can")
                    say("     place) or a read-scoped orders endpoint.")
        elif has_st:
            say("  -> NOT PROVEN. A fill carries strike_id but not marketId/outcomeId, so reaching")
            say("     the tracker key would need strike_id == outcomeId, which no record here")
            say("     establishes. Muse's instruction applies: Novig stays UNMATCHED.")
            say("     MISSING LINK: no field common to /v3/portfolio/fills and the")
            say("     nv|{marketId}|{outcomeId} key built from /v3/portfolio/positions.")
        else:
            say("  -> UNMATCHED. The fill carries neither marketId/outcomeId nor strike_id.")
            say("     MISSING LINK: the fill exposes no identifier that reaches the tracker key.")

    # ================================================ KALSHI / PM US
    say("")
    say("=" * 100)
    say("KALSHI / POLYMARKET US - the aggregation Muse forbids attaching CLV to")
    say("=" * 100)
    for pre, nm in (("ks|", "Kalshi"), ("pm|", "Polymarket US")):
        oids = {o for o, v in omap.items() if v["book"] == ("kalshi" if pre == "ks|" else "polymarket.us")}
        trows = [k for k in tbets if k.startswith(pre)]
        say(f"  {nm}: executor order id(s) {len(oids)} | tracker rows {len(trows)}")
    say("  Their ids are market+side - a POSITION. Several orders on one side collapse into one")
    say("  row, so attaching several orders' CLV to it would double-count the same close against")
    say("  different prices. NOT joined here, by design.")
    say("  Order-level tracking there needs a new per-order field at ingest; proposed separately,")
    say("  not implemented, per Muse item 3.")

    say("")
    say("=" * 100)
    say("WHAT THIS PROVES, AND WHAT REMAINS")
    say("=" * 100)
    say("  Hop 3 is the only break, and it is now measured per venue above rather than asserted.")
    say("  Nothing was written. No tracker id was changed, no CLV record altered, no history")
    say("  rewritten, and no link was inferred from game text, line, price or time.")
    say("=" * 100)
    try:
        ex.send(f"Bets CLV LINK RECON (PX matched {len(px_m)})", "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
    print(f"clv link recon: orders {len(omap)}, px matched {len(px_m)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

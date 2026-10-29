#!/usr/bin/env python3
"""
Week-to-date P&L by book (Oct 29, 2026; Peter). PRIVATE: emailed to the Bets inbox, never written to this public repo.
Week = this Monday 00:00 ET to now. Read-only GETs only.
  ProphetX: get_trades, settled trades with a settle/update time this week (win = profit after the 2% fee, loss = stake)
  Kalshi:   /portfolio/settlements since Monday (revenue - cost - fees)
  PM US:    /v1/portfolio/activities settlements since Monday (realized after fees, same parse as pmus_activity.py)
Novig is covered by novig_weekly.py with WEEK_OFFSET=-1 (run right after this in the same workflow).
Hard Rock has no read path. Public log: counts only.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import book_live
import executor as ex
import pmus_activity as pa
import px_live
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def money(x):
    return "n/a" if x is None else (f"${x:,.2f}" if x >= 0 else f"-${-x:,.2f}")


def num(x):
    if isinstance(x, dict):
        x = x.get("value")
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def tparse(t):
    if t in (None, ""):
        return None
    try:
        if isinstance(t, (int, float)) or str(t).isdigit():
            t = float(t)
            return datetime.fromtimestamp(t / 1000 if t > 1e11 else t, timezone.utc)
        return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except Exception:
        return None


def prophetx(ws):
    if not px_live.login():
        return "ProphetX: unavailable (login failed)", None, []
    tr = px_live.trades()
    W = L = P = 0
    pnl, rows, keys = 0.0, [], sorted(tr[0].keys()) if tr else []
    for t in tr:
        st = str(t.get("winning_status") or "").lower()
        when = None
        for k in ("settled_at", "settle_time", "settled_time", "updated_at", "update_time", "matched_at"):
            when = tparse(t.get(k))
            if when:
                break
        if not when or when < ws:
            continue
        stake = px_live.stake_of(t)
        if st in ("profit", "win", "won"):
            p = abs(float(t.get("profit") or 0)) * 0.98
            W += 1
        elif st in ("loss", "lose", "lost"):
            p = -stake
            L += 1
        elif st in ("push", "void", "refund", "cancel", "cancelled"):
            p = 0.0
            P += 1
        else:
            continue
        pnl += p
        rows.append(f"  {when.astimezone(ET).strftime('%a %m/%d')} {st[:4]:<4} stake {money(stake)} pnl {money(p)} "
                    f"| {str(t.get('line_name') or t.get('event_name') or t.get('selection') or '')[:60]}")
    return f"ProphetX: {W}-{L}-{P} | P&L {money(round(pnl, 2))}", pnl, rows + ([f"  (trade fields: {keys})"] if keys else [])


def kalshi(ws):
    items, cur = [], None
    for _ in range(20):
        p = {"limit": 200, "min_ts": int(ws.timestamp())}
        if cur:
            p["cursor"] = cur
        st, d = book_live._k_call("GET", "/portfolio/settlements", p)
        items += d.get("settlements") or []
        cur = d.get("cursor")
        if not cur:
            break
    W = L = 0
    pnl, rows = 0.0, []
    keys = sorted(items[0].keys()) if items else []
    for s in items:
        when = tparse(s.get("settled_time"))
        if when and when < ws:
            continue
        def dollars(k):
            v = num(s.get(k + "_dollars"))
            if v is not None:
                return v
            v = num(s.get(k))
            return v / 100 if v is not None else 0.0
        rev = dollars("revenue")
        cost = dollars("yes_total_cost") + dollars("no_total_cost")
        fee = num(s.get("fee_cost")) or 0.0
        p = rev - cost - fee
        pnl += p
        W, L = W + (p > 0), L + (p < 0)
        rows.append(f"  {(when or ws).astimezone(ET).strftime('%a %m/%d')} {s.get('ticker')} result {s.get('market_result')} "
                    f"cost {money(cost)} paid {money(rev)} fee {money(fee)} pnl {money(p)}")
    return f"Kalshi: {W} up / {L} down ({len(rows)} settled) | P&L {money(round(pnl, 2))}", pnl, \
        rows + ([f"  (settlement fields: {keys})"] if keys else [])


def pmus(ws):
    acts, params = [], {"limit": 100}
    for _ in range(30):
        d = pa.signed_get("/v1/portfolio/activities", params)
        got = pa.items_of(d)
        acts += got
        nc = pa.next_cursor(d)
        oldest = min((pa.when(a) for a in got if pa.when(a)), default=None)
        if not got or not nc or (oldest and oldest < ws):
            break
        params = {"limit": 100, nc[0] if nc[0] != "next" else "cursor": nc[1]}
    rows = [pa.row(a) for a in acts]
    st = [r for r in rows if r["type"] == "SETTLEMENT" and r["pnl"] is not None and r["time_et"]
          and datetime.strptime(r["time_et"], "%Y-%m-%d %H:%M").replace(tzinfo=ET) >= ws]
    pnl = sum(r["pnl"] for r in st)
    W, L = sum(r["pnl"] > 0 for r in st), sum(r["pnl"] < 0 for r in st)
    return f"Polymarket US: {W}-{L} ({len(st)} settled) | P&L {money(round(pnl, 2))}", pnl, \
        [f"  {r['time_et']} {r['market'][:60]} | cost {r['cost']} payout {r['amount']} pnl {money(r['pnl'])}" for r in st]


def main():
    now = datetime.now(timezone.utc)
    d = now.astimezone(ET)
    ws = (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    head = [f"WEEK TO DATE P&L | {ws.strftime('%a %b %d')} 12:00 AM - {d.strftime('%a %b %d %I:%M %p')} ET (settled bets)", ""]
    detail, total, n = [], 0.0, 0
    for name, fn in (("ProphetX", prophetx), ("Kalshi", kalshi), ("Polymarket US", pmus)):
        try:
            line, pnl, rows = fn(ws)
        except Exception as e:
            line, pnl, rows = f"{name}: unavailable ({str(e)[:80]})", None, []
        head.append(line)
        if pnl is not None:
            total += pnl
            n += 1
        detail += ["", name.upper()] + (rows or ["  (none)"])
    head += [f"SUBTOTAL ({n} books): {money(round(total, 2))}",
             "Novig: separate email 'Novig weekly' (this week) from the same run. Hard Rock: no read path.", ""]
    ex.send(f"Bets week P&L: {ws.strftime('%b %d')} - {d.strftime('%b %d')}", "\n".join(head + detail))
    print(f"Week P&L emailed; {n} books read.")   # counts only in the public log


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Balances email (Oct 29, 2026; Muse request via Peter). PRIVATE: emailed to the Bets inbox (Muse reads it there), never
written to this public repo or printed in the Actions log. One line per book, read-only:
  ProphetX (trading key: balance + open stake), Kalshi (balance + open market exposure), Polymarket US (balances +
  open position cost), Novig main + Novig auto-place (from the home PC's snapshot, which reads Novig because the cloud
  is blocked), Hard Rock: no read path -> "unavailable" (never guessed); Kay's share of Hard Rock from the secret
  KAY_HARDROCK (Peter, Oct 29), shown as a manual figure.
Runs hourly, and the executor sends one right after any live order it places.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import book_live
import executor as ex
import liquidity_monitor as lm
import px_live

ET = lm.ET


def money(x):
    return "n/a" if x is None else f"${x:,.2f}"


def _num(x):
    if isinstance(x, dict):
        x = x.get("value")
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def prophetx():
    if not px_live.login():
        return "ProphetX: unavailable (login failed)"
    d = px_live._call("/v4/mm/get_balance")
    bal = _num((d.get("data") or {}).get("balance"))
    DONE = ("profit", "loss", "win", "won", "lose", "lost", "push", "void", "refund", "cancel")
    open_ = [t for t in px_live.trades() if not any(w in str(t.get("winning_status") or "").lower() for w in DONE)
             and not any(w in str(t.get("status") or "").lower() for w in ("settled", "cancel", "void"))]
    expo = round(sum(px_live.stake_of(t) for t in open_), 2)
    return f"ProphetX: balance {money(bal)} | open exposure {money(expo)} ({len(open_)} open bet(s))"


def kalshi():
    st, d = book_live._k_call("GET", "/portfolio/balance")
    bal = d.get("balance") / 100 if isinstance(d.get("balance"), (int, float)) else None
    st, p = book_live._k_call("GET", "/portfolio/positions", {"limit": 200, "count_filter": "position"})
    expo, n = 0.0, 0
    for m in p.get("market_positions") or []:
        e = _num(m.get("market_exposure_dollars"))
        if e is None and m.get("market_exposure") is not None:
            e = _num(m.get("market_exposure")) / 100
        if e:
            expo += e
            n += 1
    return f"Kalshi: balance {money(bal)} | open exposure {money(round(expo, 2))} ({n} market(s))"


def pmus():
    st, d = book_live._pm_call("GET", "/v1/account/balances")
    b = ((d.get("balances") or [{}])[0] if isinstance(d, dict) else {})
    parts = []
    for k in ("currentBalance", "balance", "buyingPower"):
        v = _num(b.get(k))
        if v is not None:
            parts.append(f"{k} {money(v)}")
    try:
        st, pos = book_live._pm_call("GET", "/v1/portfolio/positions")
        items = pos.get("positions") if isinstance(pos, dict) else pos
        if isinstance(items, dict):
            items = list(items.values())
        cost = 0.0
        for x in items or []:
            c = _num(x.get("cost")) or _num(x.get("costBasis")) or 0
            cost += c
        parts.append(f"open cost {money(round(cost, 2))} ({len(items or [])} position(s))")
    except Exception:
        parts.append("open cost n/a")
    return "Polymarket US: " + (" | ".join(parts) if parts else "unavailable")


def novig():
    """Main + auto-place lines from the home PC's snapshot (it reads Novig; the cloud is often blocked)."""
    tok = (os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip()
    try:
        snap, age = ex._snap_read(tok)
    except Exception as e:
        return [f"Novig: unavailable (home snapshot unreadable: {str(e)[:60]})"]
    b = snap.get("balances")
    if not b:
        return [f"Novig: balances not in the home snapshot yet (snapshot {age:.0f} min old; update novig_positions_snapshot.py)"]
    out = [f"Novig main: balance {money(_num(b.get('main')))} (home snapshot {age:.0f} min old)"]
    for s in b.get("subaccounts") or []:
        out.append(f"Novig {s.get('label') or 'sub-account'}: balance {money(_num(s.get('balance')))}")
    expo = 0.0
    for p in snap.get("positions") or []:
        q, a = _num(p.get("qty")), _num(p.get("avgPrice")) or _num(p.get("avg")) or _num(p.get("averagePrice"))
        if q and a:
            expo += q * a / 100
    out.append(f"Novig open exposure (all wallets): {money(round(expo, 2))} ({len(snap.get('positions') or [])} position(s))")
    return out


def main():
    now = datetime.now(timezone.utc)
    lines = [f"BALANCES as of {now.astimezone(ET).strftime('%a %b %d %I:%M %p ET')} ({now.strftime('%Y-%m-%dT%H:%M:%SZ')})", ""]
    for fn in (prophetx, kalshi, pmus):
        try:
            lines.append(fn())
        except Exception as e:
            lines.append(f"{fn.__name__}: unavailable ({str(e)[:80]})")
    try:
        lines += novig()
    except Exception as e:
        lines.append(f"Novig: unavailable ({str(e)[:80]})")
    kay = _num(os.environ.get("KAY_HARDROCK"))
    lines.append("Hard Rock: unavailable (no read path; never guessed)"
                 + (f" | Kay's bucket (Hard Rock only): {money(kay)}, manual figure from Peter" if kay is not None else ""))
    lines += ["", "Read-only. Exposure = money in open bets (cost); Kalshi = market exposure; ProphetX = open stake.",
              "Sent hourly and right after any live bot order."]
    reason = os.environ.get("BAL_REASON", "hourly")
    ex.send(f"Bets balances ({reason})", "\n".join(lines))
    print(f"Balances emailed ({reason}); {len(lines)} lines.")   # nothing financial in the public log


if __name__ == "__main__":
    main()

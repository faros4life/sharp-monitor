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
TOT = {}   # book -> cash + money in open bets (this run); compared with the week's first email (private, Gmail only)
NAMES = {"px": "ProphetX", "kalshi": "Kalshi", "pmus": "Polymarket US", "novig_main": "Novig main",
         "novig_auto": "Novig auto-place", "hardrock": "Hard Rock (manual)"}


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
    if bal is not None:
        TOT["px"] = bal + expo
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
    if bal is not None:
        TOT["kalshi"] = bal + expo
    return f"Kalshi: balance {money(bal)} | open exposure {money(round(expo, 2))} ({n} market(s))"


def pmus():
    st, d = book_live._pm_call("GET", "/v1/account/balances")
    b = ((d.get("balances") or [{}])[0] if isinstance(d, dict) else {})
    parts = []
    cur = _num(b.get("currentBalance"))
    if cur is None:
        cur = _num(b.get("balance"))
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
        if cur is not None:
            TOT["pmus"] = cur + cost
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
    nm, na = _num(b.get("main")), 0.0
    for s in b.get("subaccounts") or []:
        out.append(f"Novig {s.get('label') or 'sub-account'}: balance {money(_num(s.get('balance')))}")
        na += _num(s.get("balance")) or 0.0
    expo, unread, names = 0.0, 0, set()
    for p in snap.get("positions") or []:
        names |= set(p.keys())
        c = next((_num(p.get(k)) for k in ("cost", "costBasis", "totalCost", "cost_basis", "openCost", "notional")
                  if _num(p.get(k))), None)
        if c:
            expo += c
            continue
        q = _num(p.get("qty")) or _num(p.get("quantity"))
        a = next((_num(p.get(k)) for k in ("avgPrice", "avg", "averagePrice", "avg_price", "avgCost", "averageCost",
                                          "entryPrice", "price") if _num(p.get(k))), None)
        if q and a:
            expo += q * (a / 100 if a > 1 else a) / 100   # 1 contract = 1c payout; price as 0.xxx (or cents)
        else:
            unread += 1
    if unread:   # public log: field NAMES only (no values) so the cost field can be wired
        print(f"Novig exposure: {unread} position(s) without a cost field; fields seen: {sorted(names)}")
    if nm is not None:   # Peter's open Novig bets sit in main (app check Oct 29): exposure counted with main
        TOT["novig_main"] = nm + expo
        TOT["novig_auto"] = na
    out.append(f"Novig open exposure (all wallets): {money(round(expo, 2))} ({len(snap.get('positions') or [])} position(s)"
               + (f"; {unread} without a cost, not counted" if unread else "") + ")")
    return out


def week_start(now):
    d = now.astimezone(ET)
    return (d - __import__("datetime").timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def baseline(now):
    """The week's FIRST balances email that carries a TOTALS line (private Gmail). Returns (when, {book: total})."""
    import email
    import re
    ws = week_start(now)
    M = ex.imap_open()
    try:
        typ, data = M.search(None, '(SUBJECT "Bets balances" SINCE "%s")' % ws.strftime("%d-%b-%Y"))
        for num in (data[0].split() if data and data[0] else []):
            typ, msg = M.fetch(num, "(RFC822)")
            m = email.message_from_bytes(msg[0][1])
            if not str(m.get("Subject") or "").startswith("Bets balances"):
                continue
            part = m.get_payload(decode=True) if not m.is_multipart() else m.get_payload(0).get_payload(decode=True)
            body = (part or b"").decode("utf-8", "replace")
            t = re.search(r"^TOTALS (\S+) (.*)$", body, re.M)
            if not t:
                continue
            when = datetime.fromisoformat(t.group(1).replace("Z", "+00:00"))
            if when < ws:
                continue
            vals = {k: float(v) for k, v in re.findall(r"(\w+)=(-?[\d.]+)", t.group(2))}
            return when, vals
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return None, {}


def hardrock_manual():
    """Newest 'Bets Hard Rock:' email (Peter's figure from his app, logged privately in Gmail). Returns (when, total, line)."""
    import email
    import re
    from email.utils import parsedate_to_datetime
    M = ex.imap_open()
    try:
        typ, data = M.search(None, '(SUBJECT "Bets Hard Rock:")')
        ids = data[0].split() if data and data[0] else []
        for num in reversed(ids[-20:]):
            typ, msg = M.fetch(num, "(RFC822)")
            m = email.message_from_bytes(msg[0][1])
            subj = str(m.get("Subject") or "")
            if not subj.startswith("Bets Hard Rock:"):
                continue
            v = {k: float(x.replace(",", "")) for k, x in re.findall(r"(cash|open|total)=\$?([\d,]+(?:\.\d+)?)", subj)}
            if "total" not in v and "cash" in v:
                v["total"] = v["cash"] + v.get("open", 0.0)
            if "total" in v:
                return parsedate_to_datetime(m.get("Date")), v
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return None, {}


def week_compare(now):
    if not TOT:
        return []
    out = ["", "Totals (cash + open bets):"]
    try:
        when, base = baseline(now)
    except Exception as e:
        when, base = None, {}
        out.append(f"(baseline unreadable: {str(e)[:60]})")
    label = when.astimezone(ET).strftime("%a %I:%M %p") if when else "this run (first of the week)"
    tn = tb = tc = 0.0   # tc = today's total over the books the baseline also has (like-for-like change)
    for k, nm in NAMES.items():
        if k not in TOT:
            out.append(f"{nm}: n/a")
            continue
        v = TOT[k]
        tn += v
        if k in base:
            tb += base[k]
            tc += v
            out.append(f"{nm}: {money(v)} | vs {label}: {'+' if v >= base[k] else '-'}"
                       f"{money(abs(v - base[k]))}")
        else:
            out.append(f"{nm}: {money(v)}")
    out.append(f"ALL{'' if 'hardrock' in TOT else ' (ex Hard Rock)'}: {money(tn)}" + (f" | vs {label} (same books): {'+' if tc >= tb else '-'}{money(abs(tc - tb))}"
                                                    if base else ""))
    out.append("Change includes deposits/withdrawals. Hard Rock = Peter's latest manual figure (its change moves only when he sends a new one).")
    out.append("TOTALS " + now.strftime("%Y-%m-%dT%H:%M:%SZ") + " " +
               " ".join(f"{k}={TOT[k]:.2f}" for k in NAMES if k in TOT))
    return out


def _nv_label(p):
    """Novig position -> 'game | side' from the public catalog (no key); falls back to the market id."""
    try:
        mk = lm.get(f"{lm.NOVIG}/v3/public/catalog/markets/{p.get('marketId')}")
        side = next((o.get("name") for o in mk.get("outcomes") or [] if o.get("outcomeId") == p.get("outcomeId")), "?")
        return f"{mk.get('description') or mk.get('title') or mk.get('marketType') or 'market'} | {side}"
    except Exception:
        return f"market {str(p.get('marketId'))[:8]}"


def new_positions():
    """Oct 30 (Peter): report NEW open positions on the 4 exchanges every hour, without Peter telling anyone (manual
    plays included). Each position is reported once (Gmail token = the record). The first run only records what is
    already open (no flood). Bot fills also show here; the bot's own FILLED message comes first."""
    import hashlib
    import positions as ps
    cur = []   # (token, line)
    for book, fn in (("Kalshi", ps.kalshi_positions), ("ProphetX", ps.px_positions), ("Polymarket US", ps.pmus_positions)):
        try:
            for h in fn() or []:
                side = h.get("label") or "?"
                if h.get("flip"):
                    side = ("NO " if h.get("mtype") != "total" else "") + side
                    if h.get("mtype") == "total":
                        side = side.replace("Over", "Under") if "Over" in side else side.replace("Under", "Over")
                cur.append((f"{book}|{h.get('game')}|{h.get('label')}|{h.get('flip')}", f"{book}: {h.get('game')} | {side}"))
        except Exception:
            pass
    try:
        snap, age = ex._snap_read((os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip())
        for p in snap.get("positions") or []:
            c = _num(p.get("cost"))
            cur.append((f"Novig|{p.get('marketId')}|{p.get('outcomeId')}",
                        f"Novig: {_nv_label(p)}" + (f" | cost {money(c)}" if c else "")))
    except Exception:
        pass
    M = ex.imap_open()
    out = []
    try:
        seeded = bool(ex.gsearch(M, "xmfseed"))
        fresh = []
        for k, line in cur:
            tok = "xmf" + hashlib.sha1(k.encode()).hexdigest()[:12]
            if not ex.gsearch(M, tok):
                fresh.append((tok, line))
    finally:
        M.logout()
    if not seeded:
        ex.send("Bets new positions: baseline", "Already open (recorded, not reported):\n" +
                "\n".join(l for _, l in cur) + "\n\nxmfseed " + " ".join(t for t, _ in fresh))
        return ["", f"New positions: baseline recorded ({len(cur)} open)."]
    if fresh:
        msg = "NEW POSITIONS (last hour, manual or bot):\n" + "\n".join(l for _, l in fresh)
        ex.tg(msg)
        ex.push("New positions: " + str(len(fresh)), "\n".join(l for _, l in fresh)[:900], mirror=False)
        ex.send(f"Bets new positions: {len(fresh)}", msg + "\n\n" + " ".join(t for t, _ in fresh))
        out = ["", msg]
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
    try:
        hw, hv = hardrock_manual()
    except Exception:
        hw, hv = None, {}
    if hv:
        TOT["hardrock"] = hv["total"]
        lines.append(f"Hard Rock (manual, from Peter's app {hw.astimezone(ET).strftime('%a %b %d %I:%M %p')}): "
                     f"cash {money(hv.get('cash'))} | open bets {money(hv.get('open'))} | total {money(hv['total'])}"
                     + (f" | Kay's bucket inside: {money(kay)}" if kay is not None else ""))
    else:
        lines.append("Hard Rock: unavailable (no read path; never guessed)"
                     + (f" | Kay's bucket (Hard Rock only): {money(kay)}, manual figure from Peter" if kay is not None else ""))
    lines += week_compare(now)
    try:
        lines += new_positions()
    except Exception as e:
        lines.append(f"New positions: check failed ({str(e)[:60]})")
    lines += ["", "Read-only. Exposure = money in open bets (cost); Kalshi = market exposure; ProphetX = open stake.",
              "Sent hourly and right after any live bot order."]
    reason = os.environ.get("BAL_REASON", "hourly")
    ex.send(f"Bets balances ({reason})", "\n".join(lines))
    print(f"Balances emailed ({reason}); {len(lines)} lines.")   # nothing financial in the public log


if __name__ == "__main__":
    main()

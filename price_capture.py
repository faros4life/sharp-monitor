#!/usr/bin/env python3
"""
Queue #7 PRICE-CAPTURE REPORT (Nov 2, 2026; Muse's definition, Peter yes). For every phase-1 executor decision:
the alert after-fee price, the gettable after-fee price per book at decision time, and the fill price or skip reason,
so slippage and gettability are computed from data. Source: the LEDGER rows in the executor's "Bets LIVE:" emails.
Per-book prices come from the ledger field books_at_decision (added Nov 2); older rows carry ProphetX only and are
labelled that way. PRIVATE email (no stakes); the Actions log prints counts only. Read-only.
"""
import json
from datetime import datetime, timezone

import executor as ex

SINCE = "26-Oct-2026"
BOOKS = ("prophetx", "novig", "kalshi", "polymarket_us")
SHORT = {"prophetx": "PX", "novig": "NV", "kalshi": "KA", "polymarket_us": "PM"}


def prob(a):
    if a in (None, 0):
        return None
    a = float(a)
    return -a / (-a + 100) if a < 0 else 100 / (a + 100)


def am(x):
    return "-" if x is None else f"{int(x):+d}"


def main():
    M = ex.imap_open()
    rows, seen = [], set()
    try:
        typ, data = M.uid("SEARCH", None, "SUBJECT", '"Bets LIVE:"', "SINCE", SINCE)
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
            for r in led:
                if not r.get("p1_qualifies") and not r.get("live"):
                    continue   # phase-1 decisions only (coded view, AGREE not applied - Muse's known gap)
                k = (r.get("key"), r.get("alert_utc"))
                if k in seen or not r.get("decided_utc"):
                    continue
                seen.add(k)
                rows.append(r)
    finally:
        M.logout()

    rows.sort(key=lambda r: r.get("decided_utc") or "")
    L = [f"PRICE-CAPTURE REPORT (queue #7), phase-1 decisions from executor ledgers since Oct 26, built "
         f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
         "Phase-1 = coded filter (p1_qualifies) or live-eligible; Muse AGREE not applied. Prices American, after fee, at the",
         "alert line. Per-book prices: full set where the ledger has books_at_decision (from Nov 2), ProphetX only before.",
         "Slippage = fill implied prob minus alert implied prob, in cents (+ = paid more than the alert). Equal-or-better",
         "prices at a converted line count as the converted line's price (see fill line).", ""]
    full = sum(1 for r in rows if r.get("books_at_decision"))
    L.append(f"Decisions: {len(rows)} | with all-book capture: {full} | ProphetX-only (older): {len(rows) - full}")
    L.append("")
    L.append("decided (UTC)      | play | alert | per-book at decision | outcome")
    slips, live_slips = [], []
    for r in rows:
        bd = r.get("books_at_decision")
        if bd:
            parts = []
            for b in BOOKS:
                x = bd.get(b) or {}
                if "best_after_fee" in x:
                    parts.append(f"{SHORT[b]} {am(x['best_after_fee'])}{'' if x.get('exact_line') else '*'}")
                else:
                    parts.append(f"{SHORT[b]} {x.get('status', '-')}")
            books = ", ".join(parts)
        else:
            books = f"PX {am(r.get('px_best_after_fee'))} (others not captured)"
        fill = r.get("fill_price_after_fee")
        lo = r.get("live_order") or {}
        if fill is not None:
            s = (prob(fill) - prob(r.get("alert_price_after_fee"))) * 100 if r.get("alert_price_after_fee") is not None else None
            same = r.get("fill_line") is None or r.get("alert_line") is None or \
                abs(float(r["fill_line"]) - float(r["alert_line"])) < 1e-9
            if s is not None:
                slips.append((s, same))
                if r.get("live"):
                    live_slips.append((s, same))
            out = (f"FILL {r.get('fill_book')} {am(fill)} line {r.get('fill_line')}"
                   + (f" (slip {s:+.1f}c)" if s is not None else "")
                   + (f" | LIVE order {lo.get('status')}" if lo else ""))
        else:
            out = f"{r.get('verdict')}: {(r.get('reason') or '')[:90]}"
        L.append(f"{r.get('decided_utc')} | {r.get('key')} | {am(r.get('alert_price_after_fee'))} @ {r.get('alert_line')} "
                 f"({r.get('alert_book')}) | {books} | {out}")
    L.append("")
    for lab, S in (("all phase-1 fills", slips), ("LIVE phase-1 fills (T3 bar: avg <= 3c)", live_slips)):
        for sub, keep in (("same line", True), ("converted line", False)):
            v = [x for x, sm in S if sm == keep]
            if v:
                L.append(f"Slippage, {lab}, {sub}: n {len(v)} | avg {sum(v) / len(v):+.2f}c | max {max(v):+.2f}c | "
                         f"worse {sum(x > 0.05 for x in v)} | same {sum(abs(x) <= 0.05 for x in v)} | better {sum(x < -0.05 for x in v)}")
    L.append("Converted-line slippage is price only: the better line bought with it is not credited here (see decay curve v5).")
    L.append("* = book's best is not at the exact alert line.")
    ex.send("Bets PRICE CAPTURE (phase-1 decisions)", "\n".join(L))
    print(f"Price capture emailed: {len(rows)} decisions, {full} with all-book capture")   # counts only


if __name__ == "__main__":
    main()

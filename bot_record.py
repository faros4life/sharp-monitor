#!/usr/bin/env python3
"""BOT-ONLY BETTING RECORD from the authoritative encrypted tracker (Peter, Nov 12).

READ-ONLY. Decrypts tracker/state.enc, writes nothing, changes nothing, places nothing.

MONEY RULE (CLAUDE.md): dollars go in the PRIVATE EMAIL only. The Actions log prints counts.

WHAT COUNTS AS A BOT BET
  source == "bot" only. Excluded: "Peter", "Peter (Hard Rock note…)", "ntfy (Peter manual)" and
  "Street Value". tracker_build sets source="bot" from the Novig sub-wallet or from bot_match()
  against the bot's own ledger keys, so this is the tracker's own attribution, not a guess of mine.

GROUPING - two layers, because one is not enough
  1. tb.group_fills(): the EXISTING function. It merges ProphetX fills sharing a strike id and sums
     stake, to_pay and profit. It does NOT merge anything else.
  2. Same day + same normalised bet + same book. Novig fills in pieces and a top-up or retry is a
     separate row, so without this layer one wager counts two or three times. Normalisation reuses
     tracker_audit.py's shape (token set + numbers) so the two tools agree.
  Different BOOK is left distinct: the same side on two venues is two wagers at two prices, and
  merging them would invent a blended price that was never taken. Both counts are reported so the
  effect of layer 2 is visible rather than assumed.

AMBIGUITY IS FLAGGED, NEVER RESOLVED SILENTLY
  A group whose rows disagree on result (one W, one L) is NOT counted as either. It is reported as
  ambiguous with its row count, because a wrong W-L record is worse than an incomplete one.
"""
import copy
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

import executor as ex
import tracker_build as tb

BOT = "bot"
EXCLUDE_PREFIX = ("Peter", "ntfy", "Street Value")


def norm_bet(s):
    """Same normalisation as tracker_audit.py, so the two tools group identically."""
    s = (s or "").lower().replace("not over", "under").replace("not under", "over")
    s = re.sub(r"\(([-+]?\d+(?:\.\d+)?)\)", r"\1", s)
    return " ".join(sorted(tb.toks(s) - tb.WEAK)) + " " + " ".join(re.findall(r"[-+]?\d+(?:\.\d+)?", s))


def when(b):
    return tb.tparse(b.get("game_start")) or tb.tparse(b.get("settled")) or tb.tparse(b.get("first_seen"))


def money(x):
    return f"{'-' if x < 0 else ''}${abs(x):,.2f}"


def main():
    now = datetime.now(timezone.utc)
    st = tb.dec(json.load(open(tb.STATE)))
    raw = copy.deepcopy(st.get("bets") or {})
    tb.mark_manual_dups(raw)
    rows = tb.group_fills([b for b in raw.values() if not b.get("dup_of")])

    bot = [b for b in rows if (b.get("source") or "") == BOT]
    other = [b for b in rows if (b.get("source") or "") != BOT]
    src_counts = defaultdict(int)
    for b in other:
        src_counts[str(b.get("source") or "(none)")] += 1

    # ---- layer 2: same day + same normalised bet + same book -------------------------------
    g = defaultdict(list)
    for b in bot:
        day = (b.get("game_start") or b.get("settled") or b.get("first_seen") or "")[:10]
        g[(day, norm_bet(b.get("bet")), str(b.get("book") or ""))].append(b)

    wagers, ambiguous = [], []
    for k, xs in g.items():
        results = {x.get("result") for x in xs if x.get("result")}
        anyopen = any(x.get("open") and not x.get("result") for x in xs)
        stake = round(sum(x.get("stake") or 0 for x in xs), 2)
        profit = round(sum(x.get("profit") or 0 for x in xs if x.get("result")), 2)
        topay = round(sum(x.get("to_pay") or 0 for x in xs), 2)
        lanes = {x.get("lane") for x in xs if x.get("lane")}
        w = {"key": k, "rows": len(xs), "stake": stake, "profit": profit, "to_pay": topay,
             "lane": (lanes.pop() if len(lanes) == 1 else None), "lanes": len(lanes),
             "open": anyopen and not results,
             "result": (results.pop() if len(results) == 1 else None),
             "settled": max((x.get("settled") or "" for x in xs), default="") or None,
             "game": next((x.get("game") for x in xs if x.get("game")), ""),
             "bet": next((x.get("bet") for x in xs if x.get("bet")), ""),
             "book": k[2]}
        if len(results) > 1:
            w["mixed"] = sorted(results)
            ambiguous.append(w)
            continue
        wagers.append(w)

    settled = [w for w in wagers if w["result"] in ("W", "L", "P")]
    openb = [w for w in wagers if w["open"]]
    unknown = [w for w in wagers if not w["result"] and not w["open"]]

    W = [w for w in settled if w["result"] == "W"]
    L = [w for w in settled if w["result"] == "L"]
    P = [w for w in settled if w["result"] == "P"]

    # ROI denominator: stake on DECIDED bets only. A push returns the stake, so including pushed
    # stake would shrink ROI on money that was never at risk of loss - stated either way below.
    risked_decided = round(sum(w["stake"] for w in W + L), 2)
    risked_all = round(sum(w["stake"] for w in settled), 2)
    pnl = round(sum(w["profit"] for w in settled), 2)
    cutoff = max((w["settled"] or "" for w in settled), default="") or "(none)"

    lanes = defaultdict(lambda: {"W": 0, "L": 0, "P": 0, "stake": 0.0, "pnl": 0.0, "n": 0})
    for w in settled:
        key = w["lane"] or "UNATTRIBUTED"
        lanes[key][w["result"]] += 1
        lanes[key]["stake"] = round(lanes[key]["stake"] + w["stake"], 2)
        lanes[key]["pnl"] = round(lanes[key]["pnl"] + w["profit"], 2)
        lanes[key]["n"] += 1

    # ------------------------------------------------------------------ private email (dollars)
    E = ["BOT-ONLY BETTING RECORD (read-only; tracker/state.enc is authoritative)", ""]
    E.append(f"Settlement cutoff (newest settled bot bet): {cutoff}")
    E.append(f"Computed at: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    E += ["", "RECONCILIATION", f"  tracker state rows            : {len(st.get('bets') or {})}",
          f"  after manual-dup + fill group : {len(rows)}",
          f"  source == bot                 : {len(bot)}",
          f"  after same-book wager grouping: {len(wagers) + len(ambiguous)}",
          f"  excluded (not bot)            : {len(other)}"]
    for s, n in sorted(src_counts.items(), key=lambda kv: -kv[1]):
        E.append(f"      {s}: {n}")
    E += ["", "TOTALS",
          f"  W-L-P            : {len(W)}-{len(L)}-{len(P)}",
          f"  realized P&L     : {money(pnl)}",
          f"  staked (decided) : {money(risked_decided)}",
          f"  staked (incl. P) : {money(risked_all)}",
          f"  ROI on decided   : {(100.0 * pnl / risked_decided):+.2f}%" if risked_decided else "  ROI: n/a",
          f"  ROI incl. pushes : {(100.0 * pnl / risked_all):+.2f}%" if risked_all else "",
          f"  open bets        : {len(openb)}",
          f"  no result, not open (unsettled/unknown): {len(unknown)}"]
    E += ["", "BY LANE"]
    for k in sorted(lanes):
        v = lanes[k]
        roi = (100.0 * v["pnl"] / v["stake"]) if v["stake"] else 0.0
        E.append(f"  {k:14} {v['W']}-{v['L']}-{v['P']}   P&L {money(v['pnl'])}   staked {money(v['stake'])}   ROI {roi:+.2f}%")
    if ambiguous:
        E += ["", f"AMBIGUOUS - NOT COUNTED ({len(ambiguous)}): rows in one group disagree on result"]
        for w in ambiguous:
            E.append(f"  {w['key'][0]} {w['book']} {w['game']} | {w['bet']} | rows={w['rows']} results={w['mixed']} stake {money(w['stake'])}")
    multi = [w for w in wagers if w["rows"] > 1]
    if multi:
        E += ["", f"COMBINED WAGERS ({len(multi)}): more than one order/fill merged into one wager"]
        for w in sorted(multi, key=lambda z: -z["rows"])[:40]:
            E.append(f"  {w['key'][0]} {w['book']} {w['game']} | {w['bet']} | rows={w['rows']} stake {money(w['stake'])} "
                     f"result={w['result']} lane={w['lane'] or '-'}")
    if openb:
        E += ["", f"OPEN BOT BETS ({len(openb)})"]
        for w in sorted(openb, key=lambda z: z["key"][0]):
            E.append(f"  {w['key'][0]} {w['book']} {w['game']} | {w['bet']} | stake {money(w['stake'])} lane={w['lane'] or '-'}")
    if unknown:
        E += ["", f"NO RESULT AND NOT OPEN ({len(unknown)}) - excluded from the record"]
        for w in sorted(unknown, key=lambda z: z["key"][0])[:30]:
            E.append(f"  {w['key'][0]} {w['book']} {w['game']} | {w['bet']} | stake {money(w['stake'])}")
    E += ["", "SETTLED BOT WAGERS (newest first)"]
    for w in sorted(settled, key=lambda z: (z["settled"] or ""), reverse=True):
        E.append(f"  {w['settled'] or '-'} {w['result']} {w['book']:12} {w['game']} | {w['bet']} | "
                 f"stake {money(w['stake'])} profit {money(w['profit'])} lane={w['lane'] or '-'} rows={w['rows']}")

    ex.send("Bets BOT-ONLY RECORD (read-only)", "\n".join(E))

    # ------------------------------------------------------------------ public log: counts only
    print("bot-only record (counts only; dollars in the private email)")
    print(f"  settlement cutoff        : {cutoff}")
    print(f"  state rows               : {len(st.get('bets') or {})}")
    print(f"  bot rows after fill group: {len(bot)}")
    print(f"  distinct bot wagers      : {len(wagers) + len(ambiguous)}")
    print(f"  W-L-P                    : {len(W)}-{len(L)}-{len(P)}")
    print(f"  open                     : {len(openb)}")
    print(f"  ambiguous (not counted)  : {len(ambiguous)}")
    print(f"  no result, not open      : {len(unknown)}")
    print(f"  combined multi-row wagers: {len(multi)}")
    for k in sorted(lanes):
        v = lanes[k]
        print(f"  lane {k:14} {v['W']}-{v['L']}-{v['P']}  (n={v['n']})")
    print("  excluded non-bot rows    : " + ", ".join(f"{s}={n}" for s, n in sorted(src_counts.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()

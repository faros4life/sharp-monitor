#!/usr/bin/env python3
"""BOT FILL P&L PULL - read-only (Peter, Nov 5 2026: "the P&L pull ... that number is the
profitability test").

Peter's question: every bot fill, site dollars, stake and result, split Lane 1 immediate fills /
resting bids / the kept Lane 3 Celtics bet.

WHY THIS EXISTS RATHER THAN AN EXISTING REPORT
  * the Nov 2 forensic recap splits by source, but its "ntfy (bot fill)" bucket is Novig only - the
    bot's ProphetX fills are pooled into "Peter ProphetX" and are not separable there.
  * plays_recap pushes its REAL PLAYS summary to the phone, not to email, and is a day/week/month
    aggregate with no lane split.
  * the per-fill record does exist, in tracker/state.enc, which is encrypted and only readable
    inside Actions. Hence a job.

WHAT IT DOES
Reads the tracker state, takes the rows the tracker itself tags as bot fills, and prints them one
per line with stake, price, result and site P&L, then totals. It INVENTORIES the state's own source
values and lane-bearing fields first and splits by what is actually present - it does not invent a
lane marker. If the state carries nothing that separates an immediate fill from a resting bid, the
report says so instead of guessing, and names what would carry it.

READ-ONLY: opens no file for writing, places no bet, changes no rule. Dollars go to the private
email; the Actions log gets counts only.
"""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

import executor as ex
import tracker_build as tb

ET = tb.ET
STATE = "tracker/state.enc"
UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")


def rows():
    """The bet records, whatever shape the state holds them in.

    tracker_build builds state = {"bets": {}} - a DICT keyed by bet id, not a list. The first
    version of this pull required a list and so reported 0 rows against a populated state. It now
    accepts either, and falls back to scanning for the largest collection of dicts that look like
    bet records, so a future reshape degrades to a wrong label rather than a silent zero.
    """
    st = tb.dec(json.load(open(STATE)))
    for key in ("bets", "all", "rows"):
        v = (st or {}).get(key)
        if isinstance(v, dict) and v:
            return list(v.values()), f"{key} (dict of {len(v)})"
        if isinstance(v, list) and v:
            return v, f"{key} (list)"
    best, where = [], "(nothing bet-shaped found)"
    for k, v in (st or {}).items():
        cand = list(v.values()) if isinstance(v, dict) else (v if isinstance(v, list) else [])
        cand = [x for x in cand if isinstance(x, dict) and ("bet" in x or "result" in x)]
        if len(cand) > len(best):
            best, where = cand, f"{k} (scanned)"
    return best, where


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def main():
    L = ["BOT FILL P&L PULL - read-only", ""]
    try:
        R, where = rows()
    except Exception as e:
        ex.send("Bets BOT FILL P&L (failed)", f"could not read {STATE}: {str(e)[:200]}")
        print(f"pnl pull: state unreadable ({str(e)[:60]})")
        return
    try:
        top = sorted((tb.dec(json.load(open(STATE))) or {}).keys())
    except Exception:
        top = []
    L += [f"tracker state: {len(R)} rows, read from st[{where!r}]",
          f"  top-level keys present: {top}", ""]

    # ---- inventory first: do not invent a lane marker
    srcs = Counter(str(b.get("source") or "(none)") for b in R)
    L += ["=" * 74, "SOURCE VALUES PRESENT IN THE STATE (so nothing is dropped silently)", "=" * 74]
    for s, n in srcs.most_common():
        L.append(f"  {n:>5}  {s}")
    keys = Counter(k for b in R for k in b.keys())
    lane_keys = [k for k in sorted(keys) if any(w in k.lower() for w in
                 ("lane", "rest", "order", "fill", "kind", "mode", "stream", "tag", "how"))]
    L += ["", f"  fields that could carry the lane / fill type: {lane_keys or 'NONE'}", ""]

    bot = [b for b in R if str(b.get("source") or "") == "bot"]
    ntfy_bot = [b for b in R if str(b.get("source") or "").startswith("ntfy") and "bot" in str(b.get("source"))]
    pool = bot or ntfy_bot
    L += ["=" * 74, f"BOT FILLS: {len(bot)} tagged source=='bot'"
          + (f", plus {len(ntfy_bot)} tagged ntfy-bot" if ntfy_bot else ""), "=" * 74]
    if not pool:
        L += ["  No row in the tracker state is tagged as a bot fill.",
              "  That is the finding: the per-fill P&L cannot be produced from this record, because",
              "  the tracker does not mark which fills were the bot's. The executor's own order ids",
              "  are the only authoritative link (px_live.bot_orders reads them out of the 'Bets LIVE'",
              "  emails for the daily stop), so the join would have to run from there instead."]
        body = "\n".join(L)
        ex.send("Bets BOT FILL P&L (no bot-tagged rows)", body)
        print(f"pnl pull: rows {len(R)}, bot-tagged 0, sources {len(srcs)}")
        return

    def one(b):
        st_ = num(b.get("stake")) or num(b.get("risk"))
        pf = num(b.get("profit"))
        return (f"  {str(b.get('game_start') or b.get('placed') or '')[:10]}  "
                f"{str(b.get('bet'))[:30]:<30} {str(b.get('book'))[:10]:<10} "
                f"{('price ' + str(b.get('price'))) if b.get('price') is not None else '':<12} "
                f"stake {('$%.2f' % st_) if st_ is not None else '?':>10}  "
                f"{str(b.get('result') or 'open'):<5} "
                f"P&L {('$%+.2f' % pf) if pf is not None else '?':>11}")

    def tot(xs, label):
        g = [b for b in xs if b.get("result") in ("W", "L", "P")]
        p = sum(num(b.get("profit")) or 0 for b in g)
        s_ = sum(num(b.get("stake")) or num(b.get("risk")) or 0 for b in g)
        w = sum(1 for b in g if b["result"] == "W")
        l_ = sum(1 for b in g if b["result"] == "L")
        pu = sum(1 for b in g if b["result"] == "P")
        return (f"  {label:<34} n {len(g):>3}  {w}-{l_}" + (f"-{pu}" if pu else "")
                + f"  staked ${s_:,.2f}  P&L ${p:+,.2f}"
                + (f"  ROI {100 * p / s_:+.1f}%" if s_ else "")
                + f"  ({p / UNIT:+.2f}u at a ${UNIT:,.0f} unit)")

    for b in sorted(pool, key=lambda x: str(x.get("game_start") or "")):
        L.append(one(b))
    L += ["", "=" * 74, "TOTALS", "=" * 74, tot(pool, "ALL BOT FILLS")]

    # ---- split by whatever the state actually carries
    groups = defaultdict(list)
    for b in pool:
        lane = None
        for k in lane_keys:
            v = b.get(k)
            if isinstance(v, str) and v:
                lane = f"{k}={v}"
                break
            if isinstance(v, dict) and v:
                lane = f"{k} present"
                break
        groups[lane or "no lane marker on the row"].append(b)
    L += ["", "  split by the state's own lane / fill fields:"]
    for g, xs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        L.append(tot(xs, g[:34]))
    if list(groups) == ["no lane marker on the row"]:
        L += ["", "  LIMITATION: the tracker rows carry nothing that separates a Lane 1 immediate",
              "  fill from a resting bid or the Lane 3 board bet. That split lives in the executor's",
              "  ledger (live_order / live_rest / live_more in the 'Bets LIVE' emails), not here, so",
              "  it cannot be produced from this record alone."]
    # ---- unit-exposure check (Peter, Nov 5 item 2): did any bot order exceed one unit?
    # The unit is "$UNIT to win": on MINUS money the stake is sized so the win is UNIT, so the
    # stake legitimately exceeds UNIT; on PLUS money the stake IS the risk and equals UNIT. So the
    # quantity to test is TO-WIN, never the stake. A stake over UNIT is normal and not a breach.
    L += ["", "=" * 74, f"UNIT EXPOSURE - to-win per fill against a ${UNIT:,.0f} unit", "=" * 74]
    over, part, fine, unknown = [], [], [], []
    for b in pool:
        st_ = num(b.get("stake")) or num(b.get("risk"))
        pr = num(b.get("price"))
        if st_ is None or pr is None or pr == 0:
            unknown.append(b)
            continue
        win = st_ * 100.0 / abs(pr) if pr < 0 else st_ * pr / 100.0
        risk = st_
        # a breach is to-win materially above the unit; 2% of tolerance covers rounding and the
        # half-point snapping the ladder does
        b["_win"], b["_risk"] = win, risk
        if win > UNIT * 1.02:
            over.append(b)
        elif win < UNIT * 0.5:
            part.append(b)
        else:
            fine.append(b)
    L.append(f"  within one unit (to-win {UNIT * 0.5:,.0f}-{UNIT * 1.02:,.0f}): {len(fine)}")
    L.append(f"  partials (to-win under half a unit, expected on a thin ladder): {len(part)}")
    L.append(f"  price or stake unreadable: {len(unknown)}")
    L.append(f"  *** OVER ONE UNIT: {len(over)} ***" if over else "  OVER ONE UNIT: none")
    for b in sorted(over, key=lambda x: -x["_win"]):
        L.append(f"     {str(b.get('game_start') or '')[:10]}  {str(b.get('bet'))[:26]:<26} "
                 f"{str(b.get('book'))[:10]:<10} price {b.get('price')} stake ${b['_risk']:,.2f} "
                 f"-> TO-WIN ${b['_win']:,.2f} = {b['_win'] / UNIT:.2f} units")
    if over:
        L += ["", "  A to-win above one unit means either a stake sized off a different unit (the",
              "  unit was $50 before Oct 28), a top-up aggregated into one tracker row, or a real",
              "  breach of the per-order cap. The row's date against the unit history and the",
              "  executor ledger for that day separate those three; this report cannot."]

    # ---- duplicate detection: the same bet recorded twice
    L += ["", "=" * 74, "DUPLICATE ROWS (same bet, book and stake)", "=" * 74]
    seen = defaultdict(list)
    for b in pool:
        st_ = num(b.get("stake")) or num(b.get("risk"))
        seen[(str(b.get("bet")), str(b.get("book")), round(st_, 2) if st_ else None,
              str(b.get("game_start") or "")[:10])].append(b)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    L.append(f"  groups with more than one row: {len(dups)}")
    for k, v in dups.items():
        L.append(f"     {k[3]} {k[0][:26]} {k[1]} ${k[2]} x{len(v)}  "
                 f"results {[x.get('result') or 'open' for x in v]}")
    if dups:
        L += ["", "  Only settled rows enter the totals above, so an open duplicate does not",
              "  double-count P&L - but one bet held as two rows is a tracker-state problem."]

    L += ["", "  by book:"]
    for bk in sorted({str(b.get("book")) for b in pool}):
        L.append(tot([b for b in pool if str(b.get("book")) == bk], f"book {bk}"))

    # ---- OPEN / UPCOMING across every source (Peter, Nov 5: "tracker is wrong ... upcoming")
    L += ["", "=" * 74, "OPEN / UPCOMING ROWS - every source, not just the bot", "=" * 74]
    now_ = datetime.now(timezone.utc)
    opens = [b for b in R if b.get("result") not in ("W", "L", "P")]
    L.append(f"  rows with no W/L/P result: {len(opens)} of {len(R)}")
    buckets = {"upcoming (game not started)": [], "in play or just started (0-4h)": [],
               "STALE - game ended 4h+ ago, still ungraded": [], "no start time on the row": []}
    for b in opens:
        s_ = tb.tparse(b.get("game_start")) or tb.tparse(b.get("placed"))
        if s_ is None:
            buckets["no start time on the row"].append((None, b))
            continue
        if s_.tzinfo is None:
            s_ = s_.replace(tzinfo=timezone.utc)
        age = (now_ - s_).total_seconds() / 3600.0
        if age < 0:
            buckets["upcoming (game not started)"].append((s_, b))
        elif age < 4:
            buckets["in play or just started (0-4h)"].append((s_, b))
        else:
            buckets["STALE - game ended 4h+ ago, still ungraded"].append((s_, b))
    for name in ("STALE - game ended 4h+ ago, still ungraded", "no start time on the row",
                 "in play or just started (0-4h)", "upcoming (game not started)"):
        xs = buckets[name]
        L.append("")
        L.append(f"  {name}: {len(xs)}")
        for s_, b in sorted(xs, key=lambda t: str(t[0]))[:30]:
            when = f"{s_:%Y-%m-%d %H:%M}Z" if s_ else "(none)"
            hrs = f" ({(now_ - s_).total_seconds() / 3600.0:+.1f}h)" if s_ else ""
            L.append(f"     {when}{hrs}  {str(b.get('bet'))[:30]:<30} "
                     f"{str(b.get('book'))[:11]:<11} {str(b.get('source'))[:16]:<16} "
                     f"{str(b.get('game'))[:34]}")
        if len(xs) > 30:
            L.append(f"     ... +{len(xs) - 30} more")
    L += ["", "  A STALE row is the tracker being wrong: the game is over and the row still shows",
          "  as open. A row with no start time cannot be placed in time at all."]

    L += ["", "Read-only: no file written, no bet placed, no rule changed. Dollars are in this",
          "email only; the Actions log carries counts."]
    body = "\n".join(L)
    ex.send("Bets BOT FILL P&L (read-only)", body)
    graded = [b for b in pool if b.get("result") in ("W", "L", "P")]
    print(f"pnl pull: rows {len(R)}, bot-tagged {len(pool)}, graded {len(graded)}, "
          f"lane groups {len(groups)}")   # counts only


if __name__ == "__main__":
    main()

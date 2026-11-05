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

import executor as ex
import tracker_build as tb

ET = tb.ET
STATE = "tracker/state.enc"
UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")


def rows():
    st = tb.dec(json.load(open(STATE)))
    for key in ("all", "bets", "rows"):
        v = (st or {}).get(key)
        if isinstance(v, list) and v:
            return v, key
    return [], "(none found)"


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
    L += [f"tracker state: {len(R)} rows, read from st[{where!r}]", ""]

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
    L += ["", "  by book:"]
    for bk in sorted({str(b.get("book")) for b in pool}):
        L.append(tot([b for b in pool if str(b.get("book")) == bk], f"book {bk}"))

    L += ["", "Read-only: no file written, no bet placed, no rule changed. Dollars are in this",
          "email only; the Actions log carries counts."]
    body = "\n".join(L)
    ex.send("Bets BOT FILL P&L (read-only)", body)
    graded = [b for b in pool if b.get("result") in ("W", "L", "P")]
    print(f"pnl pull: rows {len(R)}, bot-tagged {len(pool)}, graded {len(graded)}, "
          f"lane groups {len(groups)}")   # counts only


if __name__ == "__main__":
    main()

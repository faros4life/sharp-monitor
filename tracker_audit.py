#!/usr/bin/env python3
"""
TRACKER AUDIT (Nov 6, 2026; Peter: "a lot of dupes on the tracker - check all the games and bets and have the right score").
READ-ONLY: decrypts tracker/state.enc, changes nothing, writes nothing. Lists every bet shown on the page (open or settled,
last 10 days) and every group that looks like the SAME bet more than once (same game + side/line, any id, any book), with
each row's id, source, stake, result and score, so the cause can be fixed in tracker_build. PRIVATE email (amounts stay in
email); the Actions log prints counts only.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import executor as ex
import tracker_build as tb


def norm_bet(s):
    s = (s or "").lower().replace("not over", "under").replace("not under", "over")
    s = re.sub(r"\(([-+]?\d+(?:\.\d+)?)\)", r"\1", s)
    return " ".join(sorted(tb.toks(s) - tb.WEAK)) + " " + " ".join(re.findall(r"[-+]?\d+(?:\.\d+)?", s))


def main():
    now = datetime.now(timezone.utc)
    st = tb.dec(json.load(open(tb.STATE)))
    B = list((st.get("bets") or {}).values())
    cut = now - timedelta(days=10)
    def when(b):
        return tb.tparse(b.get("game_start")) or tb.tparse(b.get("settled")) or tb.tparse(b.get("first_seen"))
    shown = [b for b in B if (b.get("result") or b.get("open")) and (when(b) or now) >= cut]
    groups = defaultdict(list)
    for b in shown:
        day = (b.get("game_start") or b.get("settled") or b.get("first_seen") or "")[:10]
        gk = " ".join(sorted(tb.toks(b.get("game")) - tb.WEAK))[:60]
        groups[(day, norm_bet(b.get("bet")), b.get("book"))].append(b)
        b["_gk"] = gk
    dup = {k: v for k, v in groups.items() if len(v) > 1}
    # looser: same day + same normalised bet, ANY book (manual note vs book row)
    loose = defaultdict(list)
    for b in shown:
        day = (b.get("game_start") or b.get("settled") or b.get("first_seen") or "")[:10]
        loose[(day, norm_bet(b.get("bet")))].append(b)
    cross = {k: v for k, v in loose.items() if len(v) > 1 and len({x.get("book") for x in v}) > 1}

    def row(b):
        return (f"    id={b.get('id')} | {b.get('book')} | {b.get('bet')} | game={b.get('game')} | start={b.get('game_start')} | "
                f"stake={b.get('stake')} to_pay={b.get('to_pay')} | src={b.get('source')} | open={b.get('open')} site={b.get('site')} | "
                f"result={b.get('result')} profit={b.get('profit')} | score={b.get('score')} final={b.get('teams_final')} | "
                f"settled={b.get('settled')} first_seen={b.get('first_seen')}")
    L = [f"TRACKER AUDIT (read-only) | {now:%Y-%m-%d %H:%M}Z | rows in state {len(B)}, shown last 10 days {len(shown)}",
         f"Same book + day + bet, more than one row: {len(dup)} groups", ""]
    for k, v in sorted(dup.items()):
        L.append(f"  {k[0]} {k[2]} :: {k[1]}  ({len(v)} rows)")
        L += [row(b) for b in v]
    L += ["", f"Same day + bet on DIFFERENT books (e.g. manual note + book row): {len(cross)} groups", ""]
    for k, v in sorted(cross.items()):
        L.append(f"  {k[0]} :: {k[1]}  ({len(v)} rows)")
        L += [row(b) for b in v]
    L += ["", "ALL SHOWN ROWS (newest first):"]
    L += [row(b) for b in sorted(shown, key=lambda b: (when(b) or now), reverse=True)]
    ex.send("Bets TRACKER AUDIT (read-only)", "\n".join(L))
    print(f"tracker audit: state {len(B)}, shown {len(shown)}, same-book dup groups {len(dup)}, cross-book groups {len(cross)}")


if __name__ == "__main__":
    main()

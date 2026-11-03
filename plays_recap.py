#!/usr/bin/env python3
"""
REAL PLAYS RECAP (Nov 3, 2026; Peter 6:35 AM: "I want actual plays and that day's results ... keep the total recap on
top ... keep track of actual plays"). Replaces the alert-based daily recap on the phone.

Once per ET day (first bets-board run at or after RECAP_HOUR, default 8 AM ET) it pushes ONE ntfy message:
  - header: yesterday's record and units, then week and month totals (totals only, no old bets listed)
  - one line per bet settled for yesterday's games: result, bet, price, book, who placed it, final score, units
Reads the encrypted tracker state (tracker/state.enc, the same record the Bet Tracker page shows). Units = profit / UNIT
(default $200, Peter's unit), so no dollar amounts go through ntfy. The only thing written is lanes/plays_recap.json
(the last date sent - public, no bet data). The Actions log prints counts only.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import tracker_build as tb

ET = tb.ET
FILE = "lanes/plays_recap.json"
TOPIC = (os.environ.get("NTFY_TOPIC") or "").strip()
UNIT = float(os.environ.get("PLAYS_UNIT") or 200)
HOUR = int(os.environ.get("RECAP_HOUR") or 8)
ICON = {"W": "✅", "L": "❌", "P": "➖"}


def who(b):
    s = str(b.get("source") or "")
    return "Bot" if s == "bot" else ("ntfy" if s.startswith("ntfy") else ("Street Value" if "Street" in s else "Peter"))


def gdate(b):
    t = tb.tparse(b.get("game_start")) or tb.tparse(b.get("settled"))
    return t.astimezone(ET).date() if t else None


def rec(xs):
    w = sum(b["result"] == "W" for b in xs)
    l_ = sum(b["result"] == "L" for b in xs)
    p = sum(b["result"] == "P" for b in xs)
    u = sum((b.get("profit") or 0) for b in xs) / UNIT
    return f"{w}-{l_}" + (f"-{p}" if p else "") + f" {u:+.1f}u"


def line(b):
    tm = b.get("teams") or []
    sc = ", ".join(f"{t.get('short') or t.get('name')} {t.get('score')}" for t in tm if isinstance(t, dict)) if len(tm) == 2 else ""
    pr = b.get("price")
    pr = "" if pr is None else (f" {'+' if pr > 0 else ''}{int(pr)}" if isinstance(pr, (int, float)) else f" {pr}")
    return (f"{ICON.get(b['result'], '?')} {b.get('bet')}{pr} · {tb.nice(b.get('book')) if hasattr(tb, 'nice') else b.get('book')}"
            f" · {who(b)}" + (f" · {sc}" if sc else "") + f" · {(b.get('profit') or 0) / UNIT:+.1f}u")


def main(force=False):
    now = datetime.now(timezone.utc).astimezone(ET)
    try:
        mark = json.load(open(FILE))
    except Exception:
        mark = {}
    today = now.date().isoformat()
    if not force and (now.hour < HOUR or mark.get("sent_day") == today):
        print("plays recap: not due")
        return
    bets = (tb.dec(json.load(open(tb.STATE))).get("bets") or {}).values()
    sett = [b for b in bets if b.get("result") in ("W", "L", "P") and gdate(b)]
    y = now.date() - timedelta(days=1)
    yday = sorted([b for b in sett if gdate(b) == y], key=lambda b: b.get("game_start") or "")
    week0 = now.date() - timedelta(days=now.weekday())
    if now.weekday() == 0:           # Monday: show the week that just ended
        week0 -= timedelta(days=7)
    month0 = y.replace(day=1)
    wk = [b for b in sett if week0 <= gdate(b) <= y]
    mo = [b for b in sett if month0 <= gdate(b) <= y]
    opn = sum(1 for b in bets if not b.get("result") and b.get("open"))
    head = [f"REAL PLAYS · {y.strftime('%a %b %-d')}",
            f"Day: {rec(yday)} ({len(yday)} bets)" if yday else "Day: no settled bets",
            f"Week (from {week0.strftime('%b %-d')}): {rec(wk)} · {y.strftime('%B')}: {rec(mo)}",
            f"Units: 1u = ${UNIT:,.0f} of profit or loss. Open now: {opn}.", ""]
    body = "\n".join(head + [line(b) for b in yday])
    if TOPIC:
        try:
            req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
                                         headers={"Title": f"Real plays recap {y.strftime('%b %-d')}", "Tags": "moneybag"})
            urllib.request.urlopen(req, timeout=20).read()
        except Exception as ex:
            print(f"plays recap: push failed ({type(ex).__name__})")
            return
    else:
        print("plays recap: no NTFY_TOPIC (dry run)\n" + body)   # only without a topic, i.e. never in Actions
    mark["sent_day"] = today
    os.makedirs("lanes", exist_ok=True)
    json.dump(mark, open(FILE, "w"))
    print(f"plays recap: sent, {len(yday)} bets for {y}")   # counts only


if __name__ == "__main__":
    main(force=(os.environ.get("PLAYS_RECAP_FORCE") or "") == "1")

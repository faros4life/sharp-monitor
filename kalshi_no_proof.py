#!/usr/bin/env python3
"""
Kalshi NO-position read proof (Oct 28, Muse fix list #6). Reads Peter's open Kalshi positions with the same code the
executor uses (positions.kalshi_positions), and for each one says which side the bot believes he holds, then runs the
executor's duplicate/conflict check for BOTH sides of that game. Results go to Telegram + the Bets email (private);
the public log prints counts only. Compare the message with the Kalshi app: a NO must read as the opposite side.
"""
import executor as ex
import liquidity_monitor as lm
import positions


def main():
    held = positions.kalshi_positions()
    if held is None:
        print(f"Kalshi positions unreadable: {positions.WHY.get('kalshi')}")
        raise SystemExit(1)
    lines = [f"KALSHI NO-READ PROOF: {len(held)} open Kalshi position(s)"]
    nflip = 0
    for h in held:
        nflip += bool(h.get("flip"))
        lab, mt = h.get("label") or "", h.get("mtype")
        if mt == "total":
            s = "OVER" if "over" in lab.lower() else "UNDER" if "under" in lab.lower() else "?"
            if h.get("flip") and s in ("OVER", "UNDER"):
                s = "UNDER" if s == "OVER" else "OVER"
            import re as _re
            num = _re.search(r"\d+(?:\.\d+)?", lab)
            held_side = (s.title() + (f" {num.group(0)}" if num else "")) if s != "?" else lab
        else:
            held_side = None
        teams = lm.split_teams((h.get("game") or "").replace(" vs. ", " @ ").replace(" vs ", " @ ").replace(" at ", " @ "))
        if held_side is None:
            held_side = lab
            if h.get("flip"):
                other = [t for t in (teams or []) if t.lower() not in lab.lower() and lab.lower() not in t.lower()]
                held_side = other[0] if len(other) == 1 else f"NOT {lab}"
        lines.append(f"- {h.get('game')} ({h.get('date')}): you played {held_side}")
        if teams and mt:
            al = {"sport": (lm.K_LEAGUE.get(h.get("series", ""), "") if hasattr(lm, "K_LEAGUE") else "") or "NBA",
                  "start_utc": None}
            sides = ("OVER", "UNDER") if mt == "total" else (0, 1)
            for sd in sides:
                c = positions.conflict(al, mt, sd, teams, {"kalshi": [h]})
                nm = sd if mt == "total" else teams[sd]
                lines.append(f"    alert on {nm.title() if mt == 'total' else nm}: {c[0] if c else 'no match'}")
    msg = "\n".join(lines)
    ex.tg(msg)
    try:
        ex.send("Bets Kalshi NO-read proof", msg)
    except Exception:
        pass
    print(f"Kalshi positions read: {len(held)} ({nflip} NO). Details sent to Telegram + email.")   # counts only


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Signal alerts (Nov 1, 2026; Peter). Every ~10 minutes, looks at the liquidity feeds (liquidity/ + liquidity-extra/,
public) and the sharp feed, and pushes Peter's phone (ntfy + Telegram) ONLY for:
  1. TWO SIGNALS   confirmed big money (rule_met, >= $100k new) on a side a sharp alert also took (sharp_agree), pregame,
                   not pulled.
  2. AGAINST YOU   confirmed big money (>= $250k new) on the OTHER side of a bet you or the bot hold, SAME bet type
                   (spread vs spread, moneyline vs moneyline, total vs total), pregame.
                   Held sides = the bot's own live orders (Gmail ledger), Peter's 'Bets manual' notes, and open exchange
                   positions (Kalshi / ProphetX / Polymarket US, plus Novig from the home snapshot).
  3. NBA UNDER     confirmed liquidity on an NBA total UNDER (the one liquidity lane that has made money; paper).
                   SILENT by default (Nov 1, Peter): email log only; repo variable PUSH_NBA_UNDER=1 turns the push on.
  4. FLIP          big money (>= $100k) on one side, then later big money (>= $100k) on the other side of the same game
                   and bet type, with what history says (Nov 1 study of 262 flips): totals and NBA -> the FIRST money
                   won 58%; spreads -> the LATER money won 61%; moneylines -> coin flip.
Each alert is pushed once (a Gmail token email is the record). Public log: counts only.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

import executor as ex
import liquidity_monitor as lm

ET = lm.ET
TWO_MIN, AGAINST_MIN, FLIP_MIN = 100_000, 250_000, 100_000
# Nov 1 (Peter, via Muse): the NBA UNDER lane is silent until Peter turns it on (repo variable PUSH_NBA_UNDER=1).
# Off = no phone push; the alert is still logged by email (its dedupe record), so paper tracking is unchanged.
PUSH_NBA_UNDER = (os.environ.get("PUSH_NBA_UNDER") or "").strip().lower() in ("1", "on", "true", "yes")
HIST = {"total": "On totals the FIRST money has won 58% of flips (57 games).",
        "spread": "On spreads the LATER money has won 61% of flips (74 games).",
        "moneyline": "On moneylines flips have been a coin flip (131 games)."}
NBA_HIST = "In the NBA the FIRST money has won 58% of flips (102 games)."


def tok(name):
    """Team name -> a short key that matches across books ('Atlanta' = 'Atlanta Falcons', 'Los Angeles C' = 'Los Angeles
    Chargers', 'New York J' = 'New York Jets')."""
    w = re.sub(r"[^a-z ]", " ", (name or "").lower()).split()
    if not w:
        return ""
    if w[0] in ("los", "new", "san", "st", "las", "kansas", "tampa", "green", "golden", "oklahoma", "salt") and len(w) >= 2:
        if len(w) >= 3 and w[1] in ("york", "angeles"):
            return w[0] + w[1] + w[2][0]
        return w[0] + w[1]
    return w[0]


def t(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None


def side_of(x):
    """'OVER' / 'UNDER' or the team key of the side the money is on."""
    s = x.get("side")
    if s in ("OVER", "UNDER"):
        return s
    teams = x.get("teams") or []
    if isinstance(s, int) and s < len(teams):
        return tok(teams[s])
    if isinstance(s, str):
        k = tok(s)
        for tm in teams:
            if tok(tm) == k or k in tok(tm) or tok(tm) in k:
                return tok(tm)
        return k
    return None


def game_of(x):
    return (x.get("league"), tuple(sorted(tok(tm) for tm in (x.get("teams") or [])[:2])), x.get("market"),
            (x.get("start_utc") or "")[:10])


def other(side, teams):
    if side in ("OVER", "UNDER"):
        return "UNDER" if side == "OVER" else "OVER"
    o = [tm for tm in teams if tm != side]
    return o[0] if o else None


def load_liq():
    rows = []
    for f in ("liquidity/alerts.json", "liquidity-extra/alerts.json"):
        try:
            a = json.load(open(f))
        except Exception:
            continue
        rows += a if isinstance(a, list) else (a.get("alerts") or [])
    return rows


def held_sides(M):
    """{(league-or-None, game teams key, market, side)} the bot or Peter holds."""
    out = set()
    mk = {"spread": "spread", "side": "spread", "moneyline": "moneyline", "total": "total"}

    def add(league, game, market, side):
        teams = re.split(r"\s+(?:@|at|vs\.?|v)\s+", game or "")
        if len(teams) < 2 or not market or not side:
            return
        tk = tuple(sorted(tok(x) for x in teams[:2]))
        s = side.upper() if side.upper() in ("OVER", "UNDER") else tok(side)
        # same market only (Muse, Nov 1): a moneyline flow is not "against" a spread bet. Bot/manual keys say "side" for
        # spread-or-moneyline; phase-1 sides are spreads, so "side" counts as spread.
        out.add((league, tk, "spread" if market == "side" else mk.get(market, market), s))
    # the bot's own live orders (last 2 days)
    try:
        ex.bot_orders(M, days=2)
        for k in ex.LIVEKEYS:
            sp, game, market, side = (k.split("|") + [None] * 4)[:4]
            add(sp, game, market, side)
    except Exception:
        pass
    # Peter's manual-bet notes
    try:
        ex.read_manual(M)
        for k in ex.MANUAL_HELD:
            if ex.MANUAL_HELD[k] == "duplicate":
                sp, game, market, side = (k.split("|") + [None] * 4)[:4]
                add(sp, game, market, side)
    except Exception:
        pass
    # open exchange positions
    try:
        import positions as ps
        for b, rows in ps.all_positions().items():
            for h in rows or []:
                mt = h.get("mtype")
                lab = h.get("label") or ""
                if mt == "total":
                    s = "OVER" if "over" in lab.lower() else "UNDER" if "under" in lab.lower() else None
                    if s and h.get("flip"):
                        s = "UNDER" if s == "OVER" else "OVER"
                    add(None, h.get("game"), "total", s)
                elif not h.get("flip") and mt in ("spread", "moneyline"):
                    add(None, h.get("game"), mt, re.sub(r"[+-]\d.*$", "", lab).strip())
    except Exception:
        pass
    # Novig (Peter's main wallet + the bot's auto-place), from the home PC's snapshot + the public catalog
    try:
        import book_check as bc
        snap, _age = ex._snap_read((os.environ.get("NOVIG_SNAPSHOT_TOKEN") or "").strip())
        pos = snap.get("positions") or []
        if pos:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            evs, mks = bc.novig_catalog(now_ms - 6 * 3600 * 1000, now_ms + 9 * 86400 * 1000)
            ev_by = {e.get("eventId"): e for e in evs}
            mk_by = {m.get("marketId"): m for m in mks}
            for p in pos:
                m = mk_by.get(p.get("marketId"))
                e = ev_by.get((m or {}).get("eventId"))
                if not m or not e:
                    continue
                mt = bc.N_MKT.get((m.get("marketType") or "").upper())
                teams = list(lm.split_teams(e.get("description") or "") or [])
                name = next((o.get("name") or "" for o in m.get("outcomes") or [] if o.get("outcomeId") == p.get("outcomeId")), "")
                league = lm.N_LEAGUE.get((e.get("league") or "").upper().strip())
                if mt == "total":
                    s = "OVER" if "over" in name.lower() else "UNDER" if "under" in name.lower() else None
                    add(league, e.get("description"), "total", s)
                elif mt and len(teams) == 2:
                    i = lm.team_side(name, teams, league)
                    if i is not None:
                        add(league, e.get("description"), mt, teams[i])
    except Exception:
        pass
    return out


def main():
    now = datetime.now(timezone.utc)
    rows = [x for x in load_liq() if x.get("alerted_utc") and t(x["alerted_utc"]) > now - timedelta(hours=30)]
    pre = lambda x: x.get("start_utc") and t(x["start_utc"]) > now and not x.get("pulled")
    fresh = [x for x in rows if t(x["alerted_utc"]) > now - timedelta(minutes=45) and pre(x)]
    found = []   # (token, title, body)

    def money(v):
        return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v / 1e3:.0f}k"

    def sitting(x):
        fs = t(x.get("first_seen_utc") or x["alerted_utc"])
        m = round((now - fs).total_seconds() / 60)
        return f"{m // 60}h {m % 60}m" if m >= 60 else f"{m}m"

    def line(x):
        return (f"{x.get('league')} {x.get('game')}\n{x.get('side_label')} ({x.get('market')}) on {x.get('book')}: "
                f"{money(x.get('new_money') or 0)} new, sitting {sitting(x)}")

    for x in fresh:
        nm = x.get("new_money") or 0
        if x.get("rule_met") and nm >= TWO_MIN and x.get("sharp_agree"):
            found.append(("two|" + str(x.get("key")) + str(x.get("alerted_utc")), "TWO SIGNALS: " + str(x.get("side_label")),
                          line(x) + f"\nSharp alert agrees: {', '.join(x['sharp_agree'])}"))
        if x.get("league") == "NBA" and x.get("market") == "total" and x.get("side") == "UNDER" and x.get("rule_met"):
            found.append(("nbau|" + str(x.get("key")) + str(x.get("alerted_utc")), "NBA UNDER lane: " + str(x.get("game")),
                          line(x) + "\nPaper lane (12-8, +0.20/play so far); watch it."))
    # flips: the newest alert vs an earlier one on the other side of the same game + bet type
    groups = {}
    for x in rows:
        groups.setdefault(game_of(x), []).append(x)
    for g, xs in groups.items():
        xs.sort(key=lambda x: x["alerted_utc"])
        for later in [x for x in xs if x in fresh and (x.get("new_money") or 0) >= FLIP_MIN]:
            ls = side_of(later)
            firsts = [x for x in xs if x["alerted_utc"] < later["alerted_utc"] and side_of(x) not in (None, ls)
                      and (x.get("new_money") or 0) >= FLIP_MIN]
            if not firsts or ls is None:
                continue
            f0 = firsts[0]
            hist = NBA_HIST if later.get("league") == "NBA" else HIST.get(later.get("market"), "")
            found.append(("flip|" + str(later.get("key")) + str(later.get("alerted_utc")), "FLIP: " + str(later.get("game")),
                          f"{later.get('league')} {later.get('market')}\nFirst: {money(f0.get('new_money') or 0)} on "
                          f"{f0.get('side_label')} ({t(f0['alerted_utc']).astimezone(ET).strftime('%-I:%M %p')})\n"
                          f"Later: {money(later.get('new_money') or 0)} on {later.get('side_label')} "
                          f"({t(later['alerted_utc']).astimezone(ET).strftime('%-I:%M %p')})\n{hist}"))
    M = ex.imap_open()
    try:
        held = held_sides(M)
        for x in fresh:
            nm = x.get("new_money") or 0
            if not (x.get("rule_met") and nm >= AGAINST_MIN):
                continue
            lg, tk, mt, _ = game_of(x)
            s = side_of(x)
            teams = list(tk)
            opp = other(s, teams)
            if any(h[1] == tk and h[2] == mt and h[3] == opp and h[0] in (None, lg) for h in held):
                found.append(("vs|" + str(x.get("key")) + str(x.get("alerted_utc")), "AGAINST YOUR BET: " + str(x.get("game")),
                              line(x) + "\nThis money is on the OTHER side of a bet you or the bot hold. Heads-up only."))
        sent = 0
        for key, title, body in found:
            tokn = "xsig" + hashlib.sha1(key.encode()).hexdigest()[:12]
            if ex.gsearch(M, tokn):
                continue
            if PUSH_NBA_UNDER or not key.startswith("nbau|"):
                ex.push(title[:80], body)
            try:
                ex.send(f"Bets signal: {title[:60]}", body + f"\n\n{tokn}")
            except Exception:
                pass
            sent += 1
    finally:
        M.logout()
    print(f"Signal alerts: {len(found)} candidates, {sent} new pushed")   # counts only


if __name__ == "__main__":
    main()

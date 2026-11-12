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
import time as _time
import threading as _threading
from datetime import datetime, timedelta, timezone

import executor as ex
import liquidity_monitor as lm

ET = lm.ET
TWO_MIN, AGAINST_MIN, FLIP_MIN = 100_000, 250_000, 100_000
# Nov 1 (Peter, via Muse): the NBA UNDER lane is silent until Peter turns it on (repo variable PUSH_NBA_UNDER=1).
# Off = no phone push; the alert is still logged by email (its dedupe record), so paper tracking is unchanged.
PUSH_NBA_UNDER = (os.environ.get("PUSH_NBA_UNDER") or "").strip().lower() in ("1", "on", "true", "yes")
# Nov 4 (Peter: "I don't want to see any other alerts unless we make them bot or actionable"): signal pushes OFF.
# Still detected and logged by email (the dedupe record) exactly as before. PUSH_SIGNALS=on brings the push back.
PUSH_SIGNALS = (os.environ.get("PUSH_SIGNALS") or "off").strip().lower() == "on"
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
    # Nov 12: per-source timings. The job was dying inside this function and "held_sides took 350s" does not say
    # WHICH source. Four independent reads happen here; one of them is the cost and the others are being blamed for it.
    _mark("held: start")
    # the bot's own live orders (last 2 days)
    try:
        ex.bot_orders(M, days=2)
        for k in ex.LIVEKEYS:
            sp, game, market, side = (k.split("|") + [None] * 4)[:4]
            add(sp, game, market, side)
    except Exception:
        pass
    # Nov 12: this label was the hardcoded string "(gmail)", which claimed a path instead of
    # reporting one - it read as a measurement and said nothing. bot_orders() brackets whichever
    # path it takes, so the label now comes from that, and "store" vs "gmail" is the real answer to
    # whether the private-registry fast path was available this cycle.
    _mark(f"held: bot orders ({'gmail' if 'registry read (Gmail IMAP)' in ex.PERF['t'] else 'store'})")
    # Peter's manual-bet notes
    try:
        ex.read_manual(M)
        for k in ex.MANUAL_HELD:
            if ex.MANUAL_HELD[k] == "duplicate":
                sp, game, market, side = (k.split("|") + [None] * 4)[:4]
                add(sp, game, market, side)
    except Exception:
        pass
    # Nov 12 (Peter, Phase 1): surface read_manual()'s registry-mirror result. This job never read
    # ex.LOG, so the AGREE/DIVERGE line the mirror writes was invisible here - and this is the job
    # that runs every few minutes and actually completes, while the executor's queue drops most of
    # its runs. Counts only, which is all the mirror line carries. Reporting; gates nothing.
    for _l in ex.LOG:
        if "manual mirror" in _l:
            print(f"  {_l}", flush=True)
    _mark("held: manual notes (gmail)")
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
    _mark("held: exchange positions (kalshi + prophetx + pm us)")
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
    _mark("held: novig snapshot + catalog")
    return out


# Nov 11: this job takes about 7m40s against a 10-minute schedule and was being killed by an 8-minute timeout, with
# no way to tell which part cost the time. Seconds per step, counts only - nothing financial, same as every other log.
# Seconds held_sides() may take before AGAINST YOUR BET is skipped for the cycle. Must leave room inside the
# workflow's timeout for the rest of the run; the rest is about 4 seconds.
HELD_BUDGET_S = float(os.environ.get("SIGNAL_HELD_BUDGET_S", "") or "240")
_T0 = _time.time()
_MARKS = []
_PREV = {}   # per-thread last mark: deltas must never cross threads
_GAVE_UP = [False]   # set by the MAIN thread when the held-read budget expires; only then is a daemon line abandoned


def _mark(what):
    """Prints IMMEDIATELY, and keeps each thread's deltas to ITSELF.

    Nov 12, second correction. The first version accumulated and printed at the end, so a run killed on its timeout
    - the one case it was written for - produced nothing. The second printed live but kept ONE shared previous-mark,
    so once the main thread abandoned held_sides() the orphaned daemon kept appending to the same list and the two
    threads' deltas interleaved: the run showed "1.1s for bot orders (gmail)" for a call that had just blown a
    240-second budget. A measurement that mixes two timelines is worse than none, because it reads as a result.

    Each thread now has its own previous mark and is labelled, so an abandoned read can still report what it was
    doing without corrupting the main line."""
    at = _time.time() - _T0
    me = _threading.current_thread().name
    prev = _PREV.get(me, 0.0)
    _PREV[me] = at
    _MARKS.append((me, what, at))
    # Nov 12, third correction. This said "[held-read, abandoned]" for EVERY non-main thread, so a
    # clean 101.8s completion printed as abandoned - two states with opposite meanings under one
    # label, which is the failure this repo has a rule about. Only the main thread giving up makes a
    # line abandoned, and it is the main thread that knows: it sets _GAVE_UP when the budget expires.
    tag = "" if me == "MainThread" else (f" [{me}, abandoned]" if _GAVE_UP[0] else f" [{me}]")
    print(f"  timing: {at:6.1f}s total, {at - prev:6.1f}s for {what}{tag}", flush=True)


def main():
    now = datetime.now(timezone.utc)
    rows = [x for x in load_liq() if x.get("alerted_utc") and t(x["alerted_utc"]) > now - timedelta(hours=30)]
    _mark("feeds read")
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
    _mark("candidates built")
    M = ex.imap_open()
    _mark("gmail open")

    sent = 0

    def flush(items):
        """Send what is ready. Nov 12: everything used to be pushed AFTER held_sides(), which costs ~350s - so when
        the job was killed on its timeout NOTHING went out, including the three alert types that need no position
        read at all. TWO SIGNALS, NBA UNDER and FLIP come from the feeds alone and now go first, in about a second.
        AGAINST YOUR BET still needs held sides and still runs after; if that read dies, it no longer takes the
        other three with it. The sent-token check is unchanged, so an alert is still pushed exactly once."""
        nonlocal sent
        if items:
            _mark(f"flush start, {len(items)} candidates to check against gmail")
        for key, title, body in items:
            tokn = "xsig" + hashlib.sha1(key.encode()).hexdigest()[:12]
            if ex.gsearch(M, tokn):
                continue
            # Nov 12 (Peter): report DELIVERY, not that the function was called. ex.push returning falsey, or
            # raising, is a push that did not reach the phone; the email is the durable copy and its failure is
            # named too. A silent except here is how "0 new pushed" and "3 pushed but none arrived" come to look
            # the same in the log.
            pushed_ok = "not attempted"
            if PUSH_SIGNALS and (PUSH_NBA_UNDER or not key.startswith("nbau|")):
                try:
                    pushed_ok = bool(ex.push(title[:80], body))   # ONE call: pushing twice would double-alert
                except Exception as _pe:
                    pushed_ok = False
                    print(f"  alert PUSH FAILED ({type(_pe).__name__}): {title[:50]}", flush=True)
            try:
                ex.send(f"Bets signal: {title[:60]}", body + f"\n\n{tokn}")
                mailed = True
            except Exception as _se:
                mailed = False
                print(f"  alert EMAIL FAILED ({type(_se).__name__}): {title[:50]}", flush=True)
            print(f"  alert delivered: push={pushed_ok} email={mailed}  {title[:60]}", flush=True)
            sent += 1

    try:
        flush(found)                      # the feed-only alerts, before anything expensive
        _mark(f"feed alerts pushed ({sent})")
        found = []
        # Nov 12: held_sides() reads Gmail plus four venues' positions. It was 352s on Nov 11 and has since grown past
        # the job's whole timeout, so every run was killed inside it - 3.5s of useful work and then nine minutes of
        # dying, with nothing delivered. It now gets a budget. Over budget: AGAINST YOUR BET is skipped for this
        # cycle and SAID so, the other three alerts have already gone out, and the job ends cleanly instead of being
        # killed. A skipped cycle costs one heads-up; a killed job costs every alert.
        # Nov 12: this used ThreadPoolExecutor, and a `with` block on one calls shutdown(wait=True) on exit - so the
        # 240s timeout fired and the context manager then waited for the very call it had given up on. The run was
        # killed at 499s anyway. A DAEMON thread is what actually abandons work: join() returns at the deadline and
        # a daemon does not hold the process open. The orphaned read finishes or dies with the process; either way
        # it touches nothing but its own locals, and AGAINST YOUR BET is simply skipped for the cycle.
        held, box = [], {}

        def _read():
            try:
                box["v"] = held_sides(M)
            except Exception as _e:
                box["err"] = type(_e).__name__

        th = _threading.Thread(target=_read, daemon=True, name="held-read")
        th.start()
        th.join(HELD_BUDGET_S)
        # Nov 12 (Peter): an unreadable position list is UNAVAILABLE, not "no conflict". The two look identical
        # downstream - both produce an empty held set and therefore zero AGAINST YOUR BET alerts - so the state is
        # named here and emailed, rather than being inferred from silence. This alert only ADDS a heads-up; it gates
        # no bet, so an unavailable cycle costs a notification and never authorises anything.
        unavailable = ""
        if th.is_alive():
            unavailable = f"abandoned after {HELD_BUDGET_S}s"
            _GAVE_UP[0] = True   # from here on the orphaned daemon's own lines are correctly tagged abandoned
        elif "err" in box:
            unavailable = f"failed ({box['err']})"
        if unavailable:
            _mark(f"held sides {unavailable} - AGAINST YOUR BET UNAVAILABLE this cycle")
            try:
                ex.send("Bets signal: AGAINST YOUR BET unavailable",
                        f"The position read {unavailable}, so this cycle could not say whether big money hit the "
                        f"other side of anything you hold.\n\nThis is NOT 'no conflict found' - it is 'not "
                        f"checked'. TWO SIGNALS, NBA UNDER and FLIP were unaffected and went out normally.")
            except Exception:
                pass
        else:
            held = box.get("v") or []
            _mark("held sides read (gmail + exchange positions)")
        for x in ([] if unavailable else fresh):
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
        flush(found)                      # AGAINST YOUR BET, which needed the held sides
    finally:
        ex.imap_close(M)
    _mark("done")
    print(f"Signal alerts: {len(found)} candidates, {sent} new pushed")   # counts only



if __name__ == "__main__":
    main()

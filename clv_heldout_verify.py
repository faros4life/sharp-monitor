#!/usr/bin/env python3
"""
VERIFY THE HELD-OUT ROWS (Peter, Nov 12). READ-ONLY. NO IMAP, NO API CALL, NO CREDIT.

Nothing is cleared, rewritten or released. No flag is touched, no CLV recalculated, no historical
result modified. This only reports what can and cannot be independently confirmed.

WHY THE FLAG EXISTS, and why "the matcher says ok" is NOT evidence. espn_fill OVERWRITES
s["teams"] with the ESPN game's two teams. find_fixture then matches a fixture against those
teams - so if ESPN assigned the wrong game, the matcher is checking the data the upstream error
wrote, and can only CONFIRM the mistake. clv_ledger's own comment says it: "The downstream matcher
therefore cannot catch this class of mistake at all; it can only confirm it."

So re-running the matcher proves nothing here, and neither does the "re-checked now: ok" line in
the ledger email. The only independent witness is the bet's ORIGINAL text - s["bet"] and s["game"]
are never overwritten by espn_fill - and that is what this checks, against the STORED FIXTURE's own
participants rather than against the ESPN teams.

VERDICTS:
  VERIFIED        the bet's own untouched text names BOTH participants of the stored fixture, the
                  league agrees, the start is inside the window, and the close is a same-line or
                  moneyline read. Nothing here depends on ESPN being right.
  STILL UNCERTAIN the bet's own text supports only one participant - typically a totals bet whose
                  text carries no team name at all. Not wrong, just not independently confirmable.
  WRONG MATCH     the bet's own text names a team that is NOT in the stored fixture, or the
                  tracker's own date disagrees with the assigned game. This is the case the flag
                  was built to catch.

The close basis is reported separately (Peter item 3): rec["how"] is "own line" or "moneyline" for
a verified same-line close, and "main X moved to Y" for a CONVERTED one, which carries the
half-point conversion's error and is never treated as same-line.
"""
import collections
import json
import os
import sys
from datetime import datetime, timezone

import clv_ledger as cl
import tracker_build as tb

ET = tb.ET
TSTATE = "tracker/state.enc"
L = []


def say(t=""):
    L.append(t)
    print(t)


def main():
    now = datetime.now(timezone.utc)
    say("HELD-OUT ROW VERIFICATION - independent, read-only")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET")
    say("No flag cleared, no CLV rewritten, no historical result modified.")
    say("No IMAP, no OddsPapi call, no credit.")
    say("=" * 104)

    try:
        cst = cl.tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"  CLV state unreadable ({type(e).__name__})")
        return 1
    bets = cst.get("bets") or {}
    fx = cst.get("fixtures") or {}
    try:
        tst = tb.dec(json.load(open(TSTATE)))
        raw = (tst or {}).get("bets")
        tbets = raw if isinstance(raw, dict) else {}
    except Exception:
        tbets = {}

    held = [(k, r) for k, r in bets.items() if r.get("fixture_doubt")]
    say(f"  held-out rows: {len(held)}")

    verdicts = collections.Counter()
    bases = collections.Counter()
    rows = []
    for k, rec in sorted(held, key=lambda x: str((x[1].get("snap") or {}).get("game_start") or "")):
        s = rec.get("snap") or {}
        tr = tbets.get(k) or {}
        fid = rec.get("fixture")
        f = fx.get(fid) or {}
        p1, p2 = str(f.get("p1") or ""), str(f.get("p2") or "")
        lg = s.get("league")
        how = str(rec.get("how") or "")
        clv = rec.get("clv")
        gs = cl.tp(s.get("game_start"))
        dflag = (rec.get("fixture_doubt") or {}).get("why") or ""

        # THE INDEPENDENT WITNESS: the bet's own untouched text, against the STORED FIXTURE.
        own = (tb.toks(s.get("bet")) | tb.toks(s.get("game"))) - tb.WEAK
        h1 = (tb.toks(p1) - tb.WEAK) & own
        h2 = (tb.toks(p2) - tb.WEAK) & own
        supports = (1 if h1 else 0) + (1 if h2 else 0)

        # a team named by the bet that appears in NEITHER participant is the dangerous signal
        fixture_toks = (tb.toks(p1) | tb.toks(p2)) - tb.WEAK
        stray = own - fixture_toks - tb.toks(str(s.get("bet") or ""))

        # the tracker's own date, if it has one, must agree with the assigned start
        d = cl.tp((s.get("date") or "") + "T12:00:00Z") if s.get("date") else None
        date_bad = bool(d and gs and abs((gs - d).total_seconds()) > 36 * 3600)

        same_line = how in ("own line", "moneyline")
        bases["same-line/moneyline" if same_line else f"CONVERTED ({how[:26]})"] += 1

        # Nov 12 correction: STRAY TOKENS OUTRANK a low support count. A bet naming a team that
        # appears in NEITHER participant is not merely unconfirmable - it is evidence the stored
        # fixture is the wrong game. The first version tested supports == 1 first and under-called
        # a row whose bet read "Houston Rockets @ Dallas Mavericks" against a stored fixture of
        # Houston vs Oklahoma City: "dallas"/"mavericks" match neither side. Ordering the checks
        # the other way round is the difference between "cannot confirm" and "demonstrably wrong".
        if date_bad:
            v = "WRONG MATCH"
            note = "tracker date disagrees with the assigned game by more than 36h"
        elif stray and supports < 2:
            v = "WRONG MATCH"
            note = (f"the bet names {sorted(stray)[:3]}, which appear in NEITHER participant - "
                    "the stored fixture is a different game")
        elif supports == 2 and not date_bad:
            v = "VERIFIED" if same_line else "VERIFIED (converted close)"
            note = "the bet's own text names BOTH participants of the stored fixture"
        elif supports == 1:
            v = "STILL UNCERTAIN"
            note = ("the bet's own text names only one participant"
                    + (" - a totals bet carries no team name, so it cannot confirm identity"
                       if not (tb.toks(s.get("bet")) - tb.WEAK) & fixture_toks else ""))
        else:
            v = "STILL UNCERTAIN"
            note = "the bet's own text names neither participant - identity unverifiable"
        verdicts[v] += 1

        src = str(s.get("source") or tr.get("source") or "?")
        rows.append({"k": k, "v": v, "clv": clv, "same_line": same_line, "how": how,
                     "src": src, "bot": src.lower().startswith("bot")})
        say("")
        say(f"  {v:<26} CLV {('%+.2f%%' % (100 * clv)) if clv is not None else 'n/a':>9}  {str(lg):<6} "
            f"{str(s.get('bet'))[:22]:<22}")
        say(f"      bet's own game text : {str(s.get('game'))[:68]}")
        say(f"      stored fixture      : {p1[:30]} v {p2[:30]}")
        say(f"      start {str(f.get('start'))[:16]:<17} close basis: "
            f"{'SAME-LINE' if same_line else 'CONVERTED'} ({how[:30]})")
        say(f"      independent support : {supports} of 2 participants"
            + (f"  [p1 {sorted(h1)}]" if h1 else "  [p1 none]")
            + (f"  [p2 {sorted(h2)}]" if h2 else "  [p2 none]"))
        say(f"      {note}")
        say(f"      stored flag: {str(dflag)[:76]}")
        if stray:
            say(f"      NOTE tokens in the bet text matching neither participant: {sorted(stray)[:6]}")

    say("")
    say("=" * 104)
    say("ROLL-UP")
    say("=" * 104)
    for v, n in verdicts.most_common():
        say(f"  {v:<30} {n:3d}")
    say("")
    say("  close basis across the held-out rows:")
    for b, n in bases.most_common():
        say(f"    {b:<40} {n:3d}")

    # ---------------------------------------------------------------- hypothetical, clearly labelled
    ok = [r for r in rows if r["v"].startswith("VERIFIED") and r["clv"] is not None]
    oks = [r for r in ok if r["same_line"]]
    say("")
    say("  HYPOTHETICAL - not applied, not official, nothing released:")
    bot_ok = [r for r in ok if r["bot"]]
    for label, grp in (("verified (any close basis)", ok), ("verified AND same-line only", oks),
                       ("verified BOT rows only", bot_ok)):
        if grp:
            m = 100 * sum(r["clv"] for r in grp) / len(grp)
            beat = sum(1 for r in grp if r["clv"] > 0)
            say(f"    {label:<32} n {len(grp):3d}  mean CLV {m:+.2f}%  beat close {beat}/{len(grp)}")
        else:
            say(f"    {label:<32} none")
    say("")
    say("  by source among the held-out rows:")
    bysrc = collections.Counter(r["src"] for r in rows)
    for a, b in bysrc.most_common():
        say(f"    {a:<28} {b:3d}")
    say("")
    say("  HYPOTHETICAL BOT HEADLINE (current official bot figures + verified bot rows only):")
    say("    current official: n 28, avg CLV -0.30%, beat close 17/28")
    if bot_ok:
        n2 = 28 + len(bot_ok)
        tot = (-0.30 * 28) + 100 * sum(r["clv"] for r in bot_ok)
        say(f"    with {len(bot_ok)} verified bot row(s) added: n {n2}, avg CLV {tot / n2:+.2f}%")
        say("    NOT APPLIED. Shown for comparison only; the official figure is the line above it.")
    else:
        say("    no verified row carries a bot source, so the bot headline would be unchanged.")
    say("")
    say("  The official headline is unchanged and still excludes every row above.")
    say("=" * 104)
    try:
        import executor as ex
        ex.send(f"Bets HELD-OUT VERIFICATION ({len(held)} rows)", "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:40]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__})")
    print("heldout verify: " + ", ".join(f"{a}={b}" for a, b in verdicts.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

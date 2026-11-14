#!/usr/bin/env python3
"""tb.same_event and the mark_manual_dups gate (Nov 14).

The writer linked a manual note to a venue row on book + stake-to-the-cent + 90 minutes with no
identity test, and mis-linked NBA Charlotte @ Phoenix onto NCAAF Ohio State @ USC. These tests
pin BOTH directions: the bad link must not be written, and the ordinary dedupe Peter asked for
on Nov 6 must still be written. A stricter writer that stops writing good links would put the
duplicates back on the page, so that regression is tested explicitly.
"""
import tracker_build as tb

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


print("1. same_event: positive evidence is shared game tokens")
ok, why = tb.same_event({"league": "NBA", "game": "Hornets at Suns"},
                        {"league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns"})
check("same game, differently written -> ok", ok, why)
check("the reason names the shared tokens", "hornets" in why or "suns" in why, why)

ok, why = tb.same_event({"league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns"},
                        {"league": "NCAAF", "game": "Ohio State @ USC"})
check("the real mis-link is refused", not ok, why)
check("and the reason is the league conflict", "league" in why.lower(), why)

ok, why = tb.same_event({"league": "NBA", "game": "Hornets at Suns"},
                        {"league": "NBA", "game": "Lakers at Celtics"})
check("same league, different games -> refused", not ok, why)
check("reason is the absent token overlap", "shared" in why.lower(), why)

print("2. a league named on only one side cannot confirm, and does not veto")
ok, why = tb.same_event({"game": "Hornets at Suns"},
                        {"league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns"})
check("missing league does not block a token-verified link", ok, why)
check("but the gap is stated", "unnamed" in why, why)

print("3. no game text on either side is never 'same event'")
for a, b in (({"league": "NBA"}, {"league": "NBA", "game": "Hornets at Suns"}),
             ({"league": "NBA", "game": ""}, {"league": "NBA", "game": "Hornets at Suns"}),
             ({}, {})):
    ok, why = tb.same_event(a, b)
    check(f"unverifiable -> refused ({str(a)[:28]})", not ok, why)

print("4. WEAK tokens alone do not pin a game")
ok, why = tb.same_event({"league": "NCAAF", "game": "Michigan State at North Texas"},
                        {"league": "NCAAF", "game": "Washington State at North Carolina"})
check("'state'/'north' shared but refused", not ok, why)

print("5. mark_manual_dups writes the ordinary dedupe (Nov 6 behaviour kept)")
bets = {
    "nv|a": {"book": "Novig", "stake": 200.0, "placed": "2026-11-12T18:00:00Z",
             "league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns", "bet": ""},
    "mn|a": {"book": "Novig", "stake": 200.0, "placed": "2026-11-12T18:20:00Z",
             "league": "NBA", "game": "Hornets at Suns", "bet": "Under 214.5 (+100)"},
}
tb.mark_manual_dups(bets)
check("the note is marked dup_of the venue row", bets["mn|a"].get("dup_of") == "nv|a", bets["mn|a"])
check("the reason is recorded", bool(bets["mn|a"].get("dup_why")), bets["mn|a"].get("dup_why"))
check("nothing was rejected", "dup_rejected" not in bets["mn|a"], bets["mn|a"].get("dup_rejected"))
check("the bet name is still lent to the venue row", bets["nv|a"].get("bet") == "Under 214.5",
      bets["nv|a"].get("bet"))

print("6. the cross-league link is NOT written, and the near-miss is recorded")
bets = {
    "nv|usc": {"book": "Novig", "stake": 200.0, "placed": "2026-10-31T18:00:00Z",
               "league": "NCAAF", "game": "Ohio State @ USC", "bet": "USC +6.5"},
    "mn|cha": {"book": "Novig", "stake": 200.0, "placed": "2026-10-31T18:10:00Z",
               "league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns",
               "bet": "Under 214.5 (+100)"},
}
tb.mark_manual_dups(bets)
check("no dup_of written", "dup_of" not in bets["mn|cha"], bets["mn|cha"].get("dup_of"))
check("the rejected candidate is recorded, not dropped silently",
      any("nv|usc" in r for r in bets["mn|cha"].get("dup_rejected") or []),
      bets["mn|cha"].get("dup_rejected"))
check("the venue row's own bet text is untouched", bets["nv|usc"]["bet"] == "USC +6.5")

print("7. a correct candidate is still found when a wrong one is nearer in time")
bets = {
    "nv|wrong": {"book": "Novig", "stake": 100.0, "placed": "2026-11-12T18:19:00Z",
                 "league": "NCAAF", "game": "Ohio State @ USC", "bet": "USC +6.5"},
    "nv|right": {"book": "Novig", "stake": 100.0, "placed": "2026-11-12T17:40:00Z",
                 "league": "NBA", "game": "Charlotte Hornets @ Phoenix Suns", "bet": ""},
    "mn|note": {"book": "Novig", "stake": 100.0, "placed": "2026-11-12T18:20:00Z",
                "league": "NBA", "game": "Hornets at Suns", "bet": "Under 214.5 (+100)"},
}
tb.mark_manual_dups(bets)
check("the identity-verified row wins over the nearer-in-time one",
      bets["mn|note"].get("dup_of") == "nv|right", bets["mn|note"].get("dup_of"))

print("8. reader and writer share ONE definition")
import clv_selection as cs
src = inspect = None
import inspect as _i
check("clv_selection.row_key calls tb.same_event",
      "tb.same_event" in _i.getsource(cs.row_key), "row_key no longer uses the shared predicate")
check("mark_manual_dups calls same_event",
      "same_event" in _i.getsource(tb.mark_manual_dups), "writer no longer gates on identity")

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_same_event: all passed")

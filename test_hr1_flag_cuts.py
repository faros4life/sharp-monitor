"""HR1 flag-only cuts (Peter, 24 Nov 2026): lead floor 180 min, totals 145-155 dead zone.

The point of these checks is the LAYER, not the arithmetic. hr1() defines the graded pool and is
called twice - once by the stored-row recorder (sharp_monitor hr1_eligible) and once at the push
site. If the cuts had gone into hr1(), the cut cells would stop being recorded as eligible and the
pre-committed review would have nothing out-of-sample to read, while the pool kept filling and
still looked healthy. So every check below asserts the same thing from a different angle: a cut
play is STILL IN THE POOL and is NOT FLAGGED."""
import agree_rules as ar

FAILED = []


def ok(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILED.append(name)


def play(**kw):
    """An otherwise-eligible HR1 play: non-Top-25 NCAAB, Hard Rock, -110 after fee, 6 hours out."""
    a = {"sport": "NCAAB", "book_key": "hardrockbet", "kind": "spr", "bet": "HOME -3.5 ",
         "top25": False, "late": False, "price_after_fee": -110.0,
         "alert_utc": "2026-11-24T18:00:00Z", "start_utc": "2026-11-25T00:00:00Z", "point": -3.5}
    a.update(kw)
    return a


# --- the baseline both functions agree on ----------------------------------------------------
ok("eligible spread: in the pool", ar.hr1(play())[0] is True)
ok("eligible spread: flagged", ar.hr1_flag(play())[0] is True)

u = play(kind="tot", bet="UNDER 160.5 ", point=160.5)
ok("total above the dead zone: in the pool", ar.hr1(u)[0] is True)
ok("total above the dead zone: flagged", ar.hr1_flag(u)[0] is True)

d = play(kind="tot", bet="UNDER 140.5 ", point=140.5)
ok("total below the dead zone: flagged", ar.hr1_flag(d)[0] is True)

# --- cut 2: the totals dead zone, flag-only --------------------------------------------------
# Peter's test, named in the spec: a 150-total play must still land in the graded pool.
mid = play(kind="tot", bet="UNDER 150 ", point=150.0)
ok("150 total: STILL IN THE POOL (hr1 unchanged)", ar.hr1(mid)[0] is True)
ok("150 total: NOT flagged", ar.hr1_flag(mid)[0] is False)
ok("150 total: reason names the dead zone",
   any("dead zone" in w for w in ar.hr1_flag(mid)[1]))

for pt in (145.0, 145.5, 150.0, 154.5, 155.0):     # inclusive on both edges
    ok(f"total {pt:g} inside the dead zone: not flagged",
       ar.hr1_flag(play(kind="tot", bet=f"UNDER {pt:g} ", point=pt))[0] is False)
for pt in (144.5, 155.5):                          # and the edges are not off by a half point
    ok(f"total {pt:g} outside the dead zone: flagged",
       ar.hr1_flag(play(kind="tot", bet=f"UNDER {pt:g} ", point=pt))[0] is True)

# the dead zone is TOTALS only - a spread of 150 is not a thing, but -150 must not be caught
ok("spread is never dead-zoned", ar.hr1_flag(play(kind="spr", point=-150.0))[0] is True)

# fails closed rather than flagging a number it cannot read
ok("total with no number: not flagged", ar.hr1_flag(play(kind="tot", bet="UNDER ", point=None))[0] is False)
ok("total with an unreadable number: not flagged",
   ar.hr1_flag(play(kind="tot", bet="UNDER ", point="x"))[0] is False)
ok("total with no number: still in the pool", ar.hr1(play(kind="tot", bet="UNDER 150 ", point=None))[0] is True)

# --- cut 1: the lead floor, flag-only --------------------------------------------------------
# Peter's test: a sub-180m play must still land in the graded pool.
near = play(alert_utc="2026-11-24T22:00:00Z", start_utc="2026-11-25T00:00:00Z")   # 120 min out
ok("120 min out: STILL IN THE POOL (60-min pool floor unchanged)", ar.hr1(near)[0] is True)
ok("120 min out: NOT flagged", ar.hr1_flag(near)[0] is False)
ok("120 min out: reason names the flag floor",
   any("flag floor" in w for w in ar.hr1_flag(near)[1]))

ok("179 min out: not flagged",
   ar.hr1_flag(play(alert_utc="2026-11-24T21:01:00Z", start_utc="2026-11-25T00:00:00Z"))[0] is False)
ok("180 min out: flagged (floor is inclusive)",
   ar.hr1_flag(play(alert_utc="2026-11-24T21:00:00Z", start_utc="2026-11-25T00:00:00Z"))[0] is True)
ok("30 min out: outside the old 60-min pool floor too",
   ar.hr1(play(alert_utc="2026-11-24T23:30:00Z", start_utc="2026-11-25T00:00:00Z"))[0] is False)

# --- the constants, and that hr1() was not quietly edited ------------------------------------
ok("flag lead floor is 180", ar.HR1_FLAG_MIN_LEAD == 180)
ok("pool lead floor is still 60", ar.HR1_MIN_LEAD == 60)
ok("dead zone is 145-155", ar.HR1_FLAG_TOTAL_DEAD == (145.0, 155.0))
ok("price band unchanged", ar.HR1_PRICE == (-119.0, -101.0))

# no band/grade filter was added: B is the strongest band in the pool and both bands stay
for g in ("A", "B", "C", None):
    ok(f"grade {g}: flagging ignores the band", ar.hr1_flag(play(grade=g))[0] is True)

# --- the push site must consult hr1_flag, and must pass the number it keys on -----------------
src = open("sharp_monitor.py", encoding="utf-8").read()
ok("push site calls hr1_flag", "_ar.hr1_flag(" in src)
ok("recorder still stamps hr1_eligible from hr1", 'row["hr1_eligible"] = _ar.hr1(row)[0]' in src)
flag_call = src[src.index("_ar.hr1_flag("):]
ok("push site passes point (or the dead zone cuts nothing)",
   '"point": a.get("pt")' in flag_call[:600])

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)

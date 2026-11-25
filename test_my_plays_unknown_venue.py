"""Nov 25, 2026: one FanDuel bet made my_plays crash on UnknownVenue in the venue tally, so no
row was scored. An unknown venue must be named and left unscored, never stop the report and never
be priced as fee-free."""
import my_plays as m
import clv_std as cs

FAILED = []


def ok(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILED.append(name)


ok("unknown venue is shown by its own name", m.venue({"book": "FanDuel"}) == "FanDuel")
ok("known venue still canonicalises", m.venue({"book": "Hard Rock"}) == "hardrockbet")
ok("missing venue shows '?'", m.venue({}) == "?")
try:
    cs.canon("FanDuel")
    ok("the registry itself still refuses FanDuel (not priced as fee-free)", False)
except cs.UnknownVenue:
    ok("the registry itself still refuses FanDuel (not priced as fee-free)", True)
src = open(m.__file__).read()
ok("no strict canon call left in my_plays", "cs.canon(b.get(\"book\"))" not in src
   and "cs.canon(b.get('book'))" not in src)
print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)

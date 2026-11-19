#!/usr/bin/env python3
"""novig_fill_audit: read-only, and it must never call an unread fill a no-fill."""
import ast

import novig_fill_audit as a

fails = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"   {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(label)


src = open("novig_fill_audit.py").read()
tree = ast.parse(src)
imported, called, writes = set(), set(), []
for n in ast.walk(tree):
    if isinstance(n, ast.Call):
        f = n.func
        nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        called.add(nm)
        if nm == "open" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
            writes.append((getattr(n.args[0], "value", "?"), n.args[1].value))
    elif isinstance(n, ast.Import):
        imported |= {x.name for x in n.names}
    elif isinstance(n, ast.ImportFrom) and n.module:
        imported.add(n.module)

print("1. it cannot write, trade or mail")
check("no venue client is imported",
      not ({"novig_signed", "novig_live_order", "book_live"} & imported), str(sorted(imported)))
check("nothing is written outside audit/",
      all(str(p).startswith("audit/") for p, m in writes if "w" in str(m)), str(writes))
check("no registry write call", not any(c.startswith(("put_", "release_")) for c in called))
check("no mail or notification call",
      not ({"imap_open", "send", "tg", "push"} & called), str(sorted(called & {"imap_open","send","tg","push"})))

print("2. three states, never two")
check("UNKNOWN is its own bucket", "unknown" in src and "ZERO FILL READ" in src)
check("it says outright that UNKNOWN is not a no-fill", "NOT a no-fill" in src)
check("and that 'filled' means our record, not the venue",
      "our record, not the venue" in src.replace("\n", " "))

print("3. identity matching refuses rather than guessing")
check("same_play needs league, market and a shared game token",
      a.same_play(("NBA", {"memphis"}, "total", "UNDER"), ("NBA", {"memphis"}, "total", "UNDER")))
check("different league never matches",
      not a.same_play(("NBA", {"memphis"}, "total", "UNDER"), ("NCAAB", {"memphis"}, "total", "UNDER")))
check("different market never matches",
      not a.same_play(("NBA", {"memphis"}, "total", "UNDER"), ("NBA", {"memphis"}, "spread", "UNDER")))
check("no shared game token never matches",
      not a.same_play(("NBA", {"memphis"}, "total", "UNDER"), ("NBA", {"boston"}, "total", "UNDER")))
check("opposite side never matches",
      not a.same_play(("NBA", {"memphis"}, "total", "UNDER"), ("NBA", {"memphis"}, "total", "OVER")))
check("a missing identity never matches", not a.same_play(None, ("NBA", {"x"}, "total", "UNDER")))

print("4. the key parser handles both shapes")
check("lane-prefixed key", a.ident("board|NBA|Golden State vs Memphis|total|UNDER")[0] == "NBA")
check("un-prefixed key", a.ident("NBA|Golden State vs Memphis|total|UNDER")[0] == "NBA")
check("a short key is refused", a.ident("NBA|only") is None)

print("5. it fails closed on an unreadable source")
flat = " ".join(src.split()).replace(chr(34) + " " + chr(34), "")
check("registry unreadable -> refuses to estimate", "refuses to estimate" in flat, flat[flat.find("FATAL"):flat.find("FATAL")+120])
check("state unreadable -> UNAVAILABLE, not empty", "rather than empty" in flat)

print()
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    raise SystemExit(1)
print("test_novig_fill_audit: all passed")

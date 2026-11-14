#!/usr/bin/env python3
"""
PRIORITY 2 REGRESSION (Peter, Nov 13 2026): every new selection records its league at creation.

100 ledger rows carry neither a league nor a game text. A row with no league can NEVER match a
fixture, because _qualifies requires f["lg"] == lg, so its CLV is unreachable forever - and those
100 are not recoverable from stored data, because nothing authoritative about which game they
were was ever written down. The remedy is at creation, and this pins it.

The league is not inferred from any name: positions._walk finds a strike by reading ONE league's
events, so `lg` is a fact about how the record was obtained.
"""
import ast
import os
import pathlib
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "test-only-not-a-secret")

import registry  # noqa: E402

BAD = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        BAD.append(name)
        print(f"  FAIL {name}  {detail}")


def main():
    print("1. the strike walk records the league it found the strike in")
    src = pathlib.Path("positions.py").read_text()
    i = src.find('found[sid] = {"book": "prophetx"')
    check("found[sid] carries a league", i > 0 and '"league": lg' in src[i:i + 400],
          src[i:i + 300] if i > 0 else "record not found")
    # and lg really is the league loop variable, not something shadowed
    tree = ast.parse(src)
    walk = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_walk"), None)
    check("_walk loops over PX_TOURNAMENTS as lg", walk is not None and any(
        isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "lg"
        for n in ast.walk(walk)), "lg is not the league loop variable")

    print("2. the registry keeps league without making it required")
    check("league is optional, not required", "league" in registry.STRIKE_OPTIONAL
          and "league" not in registry.STRIKE_FIELDS,
          (registry.STRIKE_FIELDS, registry.STRIKE_OPTIONAL))
    captured = {}

    def fake_commit(merge, tries=4):
        d = {}
        merge(d)
        captured.update(d.get("strikes") or {})
        return True

    real = registry._commit
    registry._commit = fake_commit
    try:
        registry.put_strikes({"s1": {"book": "prophetx", "game": "A at B", "date": "2026-11-14",
                                     "mtype": "total", "label": "Over 1.5", "league": "NCAAB",
                                     "start": "2026-11-14T00:00:00Z"}})
        check("league is stored", (captured.get("s1") or {}).get("league") == "NCAAB", captured)
        check("start is stored", (captured.get("s1") or {}).get("start"), captured)
        captured.clear()
        # a record with no league must still be accepted - existing caches have none
        registry.put_strikes({"s2": {"book": "prophetx", "game": "C at D", "date": "2026-11-14",
                                     "mtype": "spread", "label": "D -2"}})
        check("a record without a league is still stored", "s2" in captured, captured)
        check("and no null league key is invented", "league" not in (captured.get("s2") or {}),
              captured.get("s2"))
    finally:
        registry._commit = real

    print("3. strike_map still accepts records that predate the league field")
    real_load = registry.load
    registry.load = lambda: {"strikes": {
        "old": {"book": "prophetx", "game": "A at B", "date": "2026-11-14",
                "mtype": "total", "label": "Over 1.5"},
        "new": {"book": "prophetx", "game": "C at D", "date": "2026-11-14",
                "mtype": "spread", "label": "D -2", "league": "NBA"}}}
    try:
        m = registry.strike_map()
        check("old record survives", "old" in m, list(m))
        check("new record survives with its league", (m.get("new") or {}).get("league") == "NBA", m)
    finally:
        registry.load = real_load

    print("4. the ProphetX tracker row carries the league at creation")
    tsrc = pathlib.Path("tracker_build.py").read_text()
    j = tsrc.find('b = {"id": f"px|{t.get(\'id\')}"')
    check("the row dict sets league from the strike",
          j > 0 and '"league": (h or {}).get("league")' in tsrc[j:j + 400],
          tsrc[j:j + 260] if j > 0 else "row builder not found")

    print()
    if BAD:
        print(f"FAILED {len(BAD)}: {BAD}")
        return 1
    print("all league-at-creation checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

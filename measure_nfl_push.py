#!/usr/bin/env python3
"""Reproduces the NFL MASS rows in line_value.py from the public nflverse games file (Nov 12, 2026).

CONDITIONING RULE (stated once, applies to every row): among UNIQUE regular-season games (game_id) whose CLOSING line
is exactly the whole number k, the share whose final result lands exactly on k.
   spreads: closing |spread_line| == k  and  the FAVOURITE wins by exactly k   (home/away pooled; overtime included)
   totals:  closing total_line   == k  and  final total   == k       (overtime included)
Not conditioned on anything else (not on the other market, weather, roof, season). A row is INCLUDED in the table only
if n >= MIN_N (200); thinner rows are printed as EXCLUDED and never reach line_value.MASS.

Usage:   python3 measure_nfl_push.py [path/to/games.csv]       (default: downloads from raw.githubusercontent.com)
         python3 measure_nfl_push.py games.csv --emit           (prints the MASS entries to paste, nothing else)
Counts only - no keys, no money.
"""
import csv
import math
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
MIN_N = 200


def rows(path=None):
    if path:
        f = open(path, newline="")
    else:
        import io
        f = io.StringIO(urllib.request.urlopen(URL, timeout=60).read().decode())
    return [r for r in csv.DictReader(f) if r["home_score"] not in ("", "NA") and r["game_type"] == "REG"]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def measure(g):
    """{('spread'|'total', k): {n, hits, d0, d1}} over UNIQUE games, plus the overall (games, d0, d1)."""
    seen, out = set(), {}
    for r in g:
        gid = r["game_id"]
        if gid in seen:
            continue
        seen.add(gid)
        day = r["gameday"]
        L, res, T, t = num(r["spread_line"]), num(r["result"]), num(r["total_line"]), num(r["total"])
        # spread: a push needs the SIGNED result to equal the SIGNED line (the favourite wins by exactly k). The underdog
        # winning by k is a cover, not a push - comparing |result| to |line| would double-count it (a bug caught Nov 12).
        for kind, key, hit in (("spread", None if L is None else abs(L), None if (L is None or res is None) else res == L),
                               ("total", T, None if (T is None or t is None) else t == T)):
            if key is None or hit is None or key != int(key):
                continue
            c = out.setdefault((kind, int(key)), {"n": 0, "hits": 0, "d0": day, "d1": day})
            c["n"] += 1
            c["hits"] += bool(hit)
            c["d0"], c["d1"] = min(c["d0"], day), max(c["d1"], day)
    days = [r["gameday"] for r in g]
    return out, (len(seen), min(days), max(days))


def main(path=None, emit=False):
    g = rows(path)
    out, (ng, d0, d1) = measure(g)
    if emit:
        for (kind, k), c in sorted(out.items()):
            if c["n"] >= MIN_N:
                print(f'    ("NFL", "{kind}", {k}): _nfl({c["hits"]}, {c["n"]}, "{"margin" if kind == "spread" else "total"}", "{c["d0"]}", "{c["d1"]}"),')
        return
    print(f"unique regular-season games: {ng}  {d0}..{d1}\nrule: closing line is exactly k -> share whose result lands on k")
    for kind in ("spread", "total"):
        print(f"{kind}: k  unique_games  hits  share  se  (95% range)  first..last  status")
        for (kd, k), c in sorted(out.items()):
            if kd != kind:
                continue
            p = c["hits"] / c["n"]
            se = math.sqrt(p * (1 - p) / c["n"])
            print(f"  {k:>3}  n={c['n']:<4} hits={c['hits']:<4} {100 * p:5.2f}%  se {100 * se:.2f}  "
                  f"[{100 * max(0, p - 1.96 * se):.1f}-{100 * (p + 1.96 * se):.1f}]  {c['d0']}..{c['d1']}  "
                  f"{'INCLUDED' if c['n'] >= MIN_N else f'EXCLUDED (n<{MIN_N})'}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0] if a else None, "--emit" in sys.argv)

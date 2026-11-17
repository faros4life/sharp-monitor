#!/usr/bin/env python3
"""APPEND-ONLY HISTORY OF EVERY PUBLISHED LIQUIDITY ALERT (Peter, 17 Nov 2026).

WHY. `liquidity/alerts.json` is the LIVE export: each run rewrites it in full from that run's own state, and the
workflow then replaces the whole directory with that run's snapshot. Any process writing from older state therefore
DELETES newer published alerts. It happened on 16 Nov: the Houston/Miami Under 232.5 was published at 16:21:11 UTC
and gone at 16:22:46, together with five alerts from the 15:45:44 batch (2888 rows -> 2884). The board had already
frozen a PLAY call on it, so that call can never be graded - it still sits `result: None`.

WHAT THIS IS. `liquidity/history.jsonl`, one JSON object per line, one line per alert id, FIRST PUBLICATION WINS and
never changes. It records that an alert existed with these fields at this time. Union-merged, so the order two
processes write in cannot lose a row: merge(a, b) == merge(b, a).

WHAT THIS IS NOT. It is NOT an execution feed. The executor, the board and every selection rule read `alerts.json`
and only `alerts.json`; nothing here is ever offered for a bet, so a stale signal cannot be re-introduced. It is NOT
a grading source either: results stay in the live export, and no figure moves because of this file.
"""
import json
import os
import sys

HIST = "history.jsonl"


def aid(x):
    """An alert's identity: the venue key plus the moment it was published."""
    return f"{(x or {}).get('key')}|{(x or {}).get('alerted_utc')}"


def alerts_of(doc):
    if isinstance(doc, dict):
        a = doc.get("alerts")
        return a if isinstance(a, list) else []
    return doc if isinstance(doc, list) else []


def read(path):
    """{id: record} from a .jsonl file. A truncated or corrupt final line is skipped, never fatal: this file is
    written by more than one process and a half-written line must not lose the rest of the history."""
    out = {}
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    x = json.loads(line)
                except ValueError:
                    continue
                if isinstance(x, dict) and x.get("key") is not None:
                    out.setdefault(aid(x), x)
    except OSError:
        return {}
    return out


def merge(*stores):
    """Union of {id: record}. FIRST record for an id wins, so an original publication is never rewritten by a later
    pass. Commutative and idempotent: the order processes write in cannot change the result or lose a row."""
    out = {}
    for s in stores:
        for k, v in (s or {}).items():
            out.setdefault(k, v)
    return out


def write(path, store):
    """Rewrite the file from a store, sorted by id so two runs with the same content produce the same bytes."""
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w") as fh:
        for k in sorted(store):
            fh.write(json.dumps(store[k], separators=(",", ":"), sort_keys=True) + "\n")
    os.replace(tmp, path)


def record(dirname, alerts):
    """Add every alert not already in this directory's history. Returns (added, total). Never removes or rewrites."""
    path = os.path.join(dirname, HIST)
    have = read(path)
    new = {aid(x): x for x in alerts if isinstance(x, dict) and x.get("key") is not None}
    merged = merge(have, new)
    added = len(merged) - len(have)
    if added:
        write(path, merged)
    return added, len(merged)


def main():
    """Merge two history files into the first. Used by the commit step: the run's snapshot is unioned with whatever
    upstream already has, so replacing the directory wholesale can no longer delete a published alert."""
    if len(sys.argv) != 3:
        print("usage: liq_history.py <into.jsonl> <from.jsonl>")
        return 2
    into, frm = sys.argv[1], sys.argv[2]
    a, b = read(into), read(frm)
    m = merge(a, b)
    write(into, m)
    print(f"history merge: upstream {len(a)} + run {len(b)} -> {len(m)} (kept {len(m) - len(a)} new)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

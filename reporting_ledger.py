#!/usr/bin/env python3
"""DURABLE REPORTING LEDGER (Peter, 15 Nov 2026). Reporting only.

WHY: registry.py keeps orders, intents and handled for KEEP_DAYS=4 and prunes on every write. That
window is a risk control and must not change, so the long-term study cannot live in it. This job
copies what the registry, tracker and CLV ledger hold into reporting/ledger.enc, which is never
pruned.

APPEND-ONLY: every record is stored as a versioned observation {kind, id, seen_utc, sha, data}.
A record is appended when it is first seen or when its content changes; earlier versions are kept,
so a corrected observation stays traceable to the original. Nothing is ever deleted.

INDEPENDENT OF EXECUTION: imports no executor code, reads the registry with the raw fetch (no
write, no claim, no prune), holds no venue or trading credential, makes no OddsPapi call.

PUBLIC LOG = COUNTS ONLY. Stakes, prices and P/L stay inside the encrypted file.
"""
import collections, hashlib, json, os, sys
from datetime import datetime, timezone, timedelta

import tracker_build as tb

OUT = "reporting/ledger.enc"
START_ET = "2026-11-12"            # Peter: every live bot bet from 12 Nov 2026, 00:00 ET
ET = timezone(timedelta(hours=-5))  # EST from 1 Nov; the study window has no DST change


def sha(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def et_day(ts):
    t = tb.tparse(ts) if ts else None
    return t.astimezone(ET).strftime("%Y-%m-%d") if t else None


def load_ledger(path=OUT):
    if not os.path.exists(path):
        return {"version": 1, "events": [], "head": {}}
    return tb.dec(json.load(open(path)))


def observe(L, kind, rid, data, now):
    """Append a version when (kind, id) is new or changed. Returns 'new' | 'changed' | None."""
    data = json.loads(json.dumps(data, default=str))   # a frozen copy: a later change must not rewrite history
    k, h = f"{kind}|{rid}", sha(data)
    old = L["head"].get(k)
    if old == h:
        return None
    L["events"].append({"kind": kind, "id": str(rid), "seen_utc": now, "sha": h, "data": data})
    L["head"][k] = h
    return "changed" if old else "new"


def latest(L):
    """{(kind, id): (first_seen_utc, latest data)} from the append-only events."""
    out = {}
    for e in L["events"]:
        key = (e["kind"], e["id"])
        first = out[key][0] if key in out else e["seen_utc"]
        out[key] = (first, e["data"])
    return out


def snapshot(L, reg, tracker, clv, now):
    n = collections.Counter()
    for o in (reg or {}).get("orders") or []:
        rid = o.get("key") or sha(o)[:16]
        rid = f"{rid}@{o.get('decided_utc') or o.get('et_day') or ''}"
        n[("order", observe(L, "order", rid, o, now))] += 1
    for i in (reg or {}).get("intents") or []:
        n[("intent", observe(L, "intent", sha(i)[:20], i, now))] += 1
    for fid, f in ((reg or {}).get("fills") or {}).items():
        n[("fill", observe(L, "fill", fid, f, now))] += 1
    for cid, v in ((reg or {}).get("venue_ids") or {}).items():
        n[("venue_id", observe(L, "venue_id", cid, v, now))] += 1
    for bid, b in (tracker or {}).items():
        if b.get("source") == "bot":
            n[("tracker_bot", observe(L, "tracker_bot", bid, b, now))] += 1
    for bid, r in (clv or {}).items():
        if bid in (tracker or {}) and (tracker[bid] or {}).get("source") == "bot":
            n[("clv", observe(L, "clv", bid, r, now))] += 1
    return n


RES = {"W": "W", "WIN": "W", "WON": "W", "L": "L", "LOSS": "L", "LOST": "L", "P": "P", "PUSH": "P", "VOID": "P"}
LANES = ("rules", "rule", "board", "r1", "lane2", "dogs", "ncs")   # Nov 27: dogs/ncs added (lane_of_key only)


def lane_of_key(k):
    """DEPRECATED for counts (Peter, 16 Nov): a key prefix proves nothing - executor.ledger_row stores key = derive_key(play),
    normally with NO lane prefix, so this returned '?' for most real orders. Kept for any external caller."""
    p = str(k or "").split("|")[0]
    return {"rule": "rules"}.get(p, p) if p in LANES else "?"


def lane_of_row(d):
    """Lane counts come from the STORED order row's verified fields (registry.row_lane: 'source' = rules|board|r1|lane2, or a
    lane prefix that agrees with it). Unknown or disagreeing -> '?'. Reads the record; never alters it."""
    try:
        import registry as _rg
        return _rg.row_lane(d or {}) or "?"
    except Exception:
        return "?"


def daily(L):
    """Per ET day from START_ET: counts only. Execution day = order decided/et_day or fill write ts;
    settlement day = tracker settled; first-seen day = tracker ingest_checked (Project 1 stamp)."""
    cur = latest(L)
    D = collections.defaultdict(collections.Counter)
    # Fill lanes come from the ORDER the fill belongs to, joined by immutable id (fill record id == order_id or client_id),
    # with the lane from that stored order row - not from the fill's unprefixed play_key. Two lanes on one id -> '?'.
    id_lane = {}
    for (kind, _rid), (_f, d) in cur.items():
        if kind != "order":
            continue
        ln = lane_of_row(d)
        los = [d.get("live_order"), d.get("live_rest")] + list(d.get("live_more") or [])
        for lo in los:
            lo = lo if isinstance(lo, dict) else {}
            for fld in ("order_id", "client_id"):
                i = str(lo.get(fld) or "")
                if i:
                    id_lane[i] = ln if id_lane.get(i, ln) == ln else "?"
    for (kind, rid), (first, d) in cur.items():
        if kind == "order":
            day = (d.get("et_day") or et_day(d.get("decided_utc")) or "?")
            if day >= START_ET:
                D[day]["orders"] += 1
                D[day]["orders_with_live_order"] += 1 if d.get("live_order") else 0
                D[day][f"orders_lane_{lane_of_row(d)}"] += 1
        elif kind == "fill":
            day = et_day(d.get("ts")) or "?"
            if day >= START_ET:
                D[day][f"fill_{d.get('state')}"] += 1
                D[day][f"fill_lane_{id_lane.get(str(rid), '?')}"] += 1 if d.get("state") in ("FILLED", "PARTIAL") else 0
        elif kind == "tracker_bot":
            sday = et_day(d.get("settled"))
            fday = et_day(d.get("ingest_checked"))
            if sday and sday >= START_ET:
                D[sday]["bot_settled"] += 1
                D[sday]["bot_graded"] += 1 if RES.get(str(d.get("result") or "").upper()) else 0
                D[sday][f"bot_lane_src_{d.get('lane_src') or 'unset'}"] += 1
                D[sday]["bot_clv_certified"] += 1 if (cur.get(("clv", rid)) or (None, {}))[1].get("clv") is not None else 0
            elif not sday and (fday or "") >= START_ET:
                D[fday or "?"]["bot_open"] += 1
            if fday and fday >= START_ET:
                D[fday]["p1_first_seen"] += 1
    return D


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    import registry as rg
    import clv_ledger as cl
    if not rg.enabled():
        print("FAIL: registry not configured (REGISTRY_TOKEN missing) - nothing written")
        return 1
    reg, _ = rg._fetch()                       # raw read: no write, no claim, no prune
    if reg is None:
        print("FAIL: registry unreadable - nothing written")
        return 1
    tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    clv = (tb.dec(json.load(open(cl.STATE))) or {}).get("bets") or {}
    L = load_ledger()
    before = len(L["events"])
    n = snapshot(L, reg, tracker, clv, now)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(tb.enc(L), open(tmp, "w"))
    assert tb.dec(json.load(open(tmp)))["events"][:before] == L["events"][:before], "append-only violated"
    os.replace(tmp, OUT)
    print(f"ledger events {before} -> {len(L['events'])}")
    for (kind, what), c in sorted(n.items(), key=lambda x: (x[0][0], str(x[0][1]))):
        print(f"  {kind:<12} {what or 'unchanged':<9} {c}")
    print(f"registry window as stored: earliest order day "
          f"{min((o.get('et_day') or str(o.get('decided_utc') or '')[:10] or '9') for o in reg.get('orders') or [{}])}")
    print(f"PER ET DAY from {START_ET} (counts only; execution, settlement and first-seen days are distinct)")
    for day, c in sorted(daily(L).items()):
        print(f"  {day}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

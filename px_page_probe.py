#!/usr/bin/env python3
"""ONE-OFF READ-ONLY PROBE (Peter, 16 Nov): how does ProphetX /v4/mm/get_trades page and sort?
The tracker reads it once and gets 100 rows; a Nov 13 bot fill is in ProphetX's matching detail but not in those rows.
GET requests only, ProphetX DATA key only. Prints counts, field names and DATES only - no amounts, sides or ids."""
import urllib.parse as up
from datetime import datetime, timezone
import book_check as bc

SINCE = datetime(2026, 11, 12, 5, tzinfo=timezone.utc)


def t(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None


def summ(label, d):
    data = d.get("data") if isinstance(d, dict) else None
    data = data if isinstance(data, dict) else {}
    rows = data.get("trades") or []
    ts = sorted(x for x in (t(r.get("created_at")) for r in rows if isinstance(r, dict)) if x)
    cur = next((data.get(k) or d.get(k) for k in ("next_cursor", "nextCursor", "cursor") if k in data or k in d), None)
    order = "n/a"
    if len(ts) > 1:
        raw = [t(r.get("created_at")) for r in rows if isinstance(r, dict) and t(r.get("created_at"))]
        order = "newest-first" if raw == sorted(raw, reverse=True) else "oldest-first" if raw == sorted(raw) else "unsorted"
    print(f"{label}: rows {len(rows)} | data keys {sorted(data)} | top keys {sorted(d) if isinstance(d, dict) else '?'} | "
          f"created {ts[0].date() if ts else '-'} .. {ts[-1].date() if ts else '-'} | since 12 Nov {sum(1 for x in ts if x >= SINCE)} | "
          f"order {order} | cursor present {cur is not None} ({'non-empty' if cur else 'empty'})")
    return cur


def call(label, path):
    try:
        return summ(label, bc.px_call(path) or {})
    except Exception as e:
        print(f"{label}: ERROR {type(e).__name__} {getattr(e, 'code', '')}")
        return None


def main():
    if not bc.px_login():
        print("login failed")
        return 1
    frm, to = int(SINCE.timestamp()), int(datetime.now(timezone.utc).timestamp())
    cur = call("plain", "/v4/mm/get_trades")
    call("limit=5", "/v4/mm/get_trades?limit=5")
    c2 = call("from/to since 12 Nov", "/v4/mm/get_trades?" + up.urlencode({"from": frm, "to": to}))
    call("from/to + limit=100", "/v4/mm/get_trades?" + up.urlencode({"from": frm, "to": to, "limit": 100}))
    for label, c in (("page 2 via plain cursor", cur), ("page 2 via from/to cursor", c2)):
        if c:
            call(label, "/v4/mm/get_trades?" + up.urlencode({"next_cursor": c}))
    call("matching detail since 12 Nov (reference)", "/v2/mm/get_wager_matching_detail?" + up.urlencode({"from": frm, "to": to, "limit": 100}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

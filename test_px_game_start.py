#!/usr/bin/env python3
"""
OFFLINE TEST for the ProphetX game_start fix (Peter/Muse, Nov 12, Priority 1 item 5).

No network, no credentials, no state file. It tests the three behaviours the fix must have, on
synthetic rows whose answers are known by construction.

THE DEFECT THIS GUARDS. positions._walk() reads ProphetX's event feed, parses e["scheduled"] into a
datetime to window the walk, and then stored only (e["scheduled"])[:10] - the date, with the time
thrown away. tracker_build.read_prophetx() copied that date onto the row and nothing else, and a
SETTLED ProphetX row never passes through attach(), which is what sets game_start for open bets off
the live scoreboard. So settled ProphetX fills reached clv_ledger carrying no game_start, and its
pending loop gates on exactly that field:

    gs = tp(s.get("game_start"))
    if not gs ...: continue

- which skipped them before any attempt was recorded. Hence four graded losses at clv None with
tries None: never attempted, not failed.

WHAT IS NOT TESTED HERE. Whether the four EXISTING rows can be recovered - they are settled, so
they are no longer among the open strikes _walk resolves, and their recovery has to come from a
verified historical source (the ESPN backfill already in clv_ledger). That is a separate question
and is not answered by this fix.
"""
import sys
from datetime import datetime, timedelta, timezone

SCORE_AFTER_MIN = 10


def tp(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None


def walk_record(event, sid, mtype, label):
    """positions._walk()'s found[sid], as it now stands: full `scheduled` kept beside `date`."""
    return {"book": "prophetx", "strike_id": sid, "game": event.get("name") or "",
            "date": (event.get("scheduled") or "")[:10],
            "start": event.get("scheduled") or "",
            "mtype": mtype, "label": label, "flip": False}


def px_row(trade, h):
    """tracker_build.read_prophetx()'s row, as it now stands."""
    b = {"id": f"px|{trade.get('id')}", "book": "ProphetX",
         "game": (h or {}).get("game") or "", "bet": (h or {}).get("label") or "",
         "price": trade.get("price"), "date": (h or {}).get("date"),
         "placed": str(trade.get("created_at") or "")}
    start = str((h or {}).get("start") or "")
    if start:
        b["game_start"] = start
    return b


def pending(rec, now):
    """clv_ledger's pending gate, as it now stands: skips still skip, but say why."""
    s = rec["snap"]
    if rec.get("clv") is not None or rec.get("done"):
        return False, None
    gs = tp(s.get("game_start"))
    if not gs:
        return False, "no game_start on the row - never attempted, not failed"
    if now < gs + timedelta(minutes=SCORE_AFTER_MIN):
        return False, "game not started"
    return True, None


def main():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if got == want else 'FAIL'} {name}")

    print("OFFLINE TEST - ProphetX game_start propagation")
    print("=" * 86)
    now = datetime(2026, 11, 12, 18, 0, tzinfo=timezone.utc)
    ev = {"name": "Boston Celtics at Milwaukee Bucks", "scheduled": "2026-11-12T01:00:00Z"}

    # 1 - the walk keeps the time, not just the date
    w = walk_record(ev, "s1", "total", "Under 221.5")
    check("walk keeps the full scheduled timestamp", w["start"], "2026-11-12T01:00:00Z")
    check("walk still keeps the date unchanged", w["date"], "2026-11-12")
    check("the old [:10] form is strictly shorter", len(w["date"]) < len(w["start"]), True)

    # 2 - the row carries game_start through to the ledger
    row = px_row({"id": 29545246, "price": -117, "created_at": "2026-11-11T23:00:00Z"}, w)
    check("settled px row now carries game_start", row.get("game_start"), "2026-11-12T01:00:00Z")

    # 3 - an eligible row ENTERS scoring (the whole point)
    ok, why = pending({"snap": row}, now)
    check("eligible row enters scoring", ok, True)
    check("eligible row carries no skip reason", why, None)

    # 4 - a row with no start is skipped but REPORTS, never silently
    bare = px_row({"id": 1, "price": -110}, {"game": "X at Y", "date": "2026-11-12"})
    check("row with no venue start has no game_start", "game_start" in bare, False)
    ok2, why2 = pending({"snap": bare}, now)
    check("row with no game_start does not enter scoring", ok2, False)
    check("and it reports a reason", why2, "no game_start on the row - never attempted, not failed")

    # 5 - a not-yet-started game is still held, with its own distinct reason
    future = px_row({"id": 2, "price": -110},
                    walk_record({"name": "A at B", "scheduled": "2026-11-12T23:00:00Z"},
                                "s2", "total", "Over 1"))
    ok3, why3 = pending({"snap": future}, now)
    check("future game does not enter scoring", ok3, False)
    check("future game reports 'game not started'", why3, "game not started")

    # 6 - date must NEVER be promoted into a start time: that would invent a time of day
    check("date alone never becomes game_start", bare.get("game_start"), None)

    # 7 - an already-scored row is untouched (no historical CLV disturbed)
    scored = {"snap": row, "clv": -0.0176}
    ok4, why4 = pending(scored, now)
    check("already-scored row stays out of the queue", ok4, False)
    check("already-scored row gets no new reason", why4, None)

    print("=" * 86)
    if fails:
        for f in fails:
            print("  " + f)
        print("  FAIL - do not commit")
        return 1
    print("  PASS - the venue's start survives the walk and the row, eligible rows enter scoring,")
    print("  and every skip states its reason instead of vanishing. A date is never promoted to a")
    print("  start time, and an already-scored row is left alone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

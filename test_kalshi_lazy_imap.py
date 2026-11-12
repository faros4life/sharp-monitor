#!/usr/bin/env python3
"""kalshi_rest_reports() must not DIAL Gmail when no caller needs it (Peter, Nov 12).

The reporter opened IMAP unconditionally, so a cycle with no open resting bid still paid ~4s of
Gmail to do nothing - and on the 15-minute fill-reports schedule that is most cycles (the 19:27 run:
0 order(s) of 21 ledger rows).

What must NOT change is when Gmail is actually CONSULTED. Two fallbacks stop a fill being reported
twice, and both have to survive:
  - the ledger RESCAN, when the private store returned no rows
  - already_reported()/ReportClaim(), for any token the store does not already know
Turning either into "assume unsent" would message Peter about the same fill twice, so the tests
below assert that each one still reaches Gmail.
"""
import os
import sys

os.environ["REGISTRY_TOKEN"] = ""
import executor as ex
import book_live as bl

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


class FakeIMAP:
    def __init__(self):
        self.calls = 0

    def uid(self, cmd, *a):
        self.calls += 1
        if cmd == "SEARCH":
            return "OK", [b""]
        return "OK", [(b"x", b"Subject: Bets LIVE: x\r\n\r\n")]


opened = {"n": 0, "last": None}


def fake_open():
    opened["n"] += 1
    opened["last"] = FakeIMAP()
    return opened["last"]


_orig = (ex.imap_open, ex.imap_close, bl._k_call, ex.already_reported, ex.push, ex.tg, ex.send)
ex.imap_open = fake_open
ex.imap_close = lambda m: None
ex.push = lambda *a, **k: True
ex.tg = lambda *a, **k: True
ex.send = lambda *a, **k: True


def rest_row(oid, key="NBA|A @ B|total|UNDER"):
    return {"key": key, "decided_utc": ex.datetime.now(ex.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "live_rest": {"book": "kalshi", "status": "placed", "order_id": oid,
                          "limit": "0.52", "expires_utc": "2026-11-12T23:59:00Z"}}


print("No open resting bid -> Gmail is never dialled")
opened["n"] = 0
ex.LEDGER_ROWS[:] = [{"key": "x", "decided_utc": "2026-11-12T18:00:00Z", "live_order": {"book": "kalshi"}}]
ex.kalshi_rest_reports()
check("zero IMAP connections opened", opened["n"] == 0)

print("\nNo ledger rows at all -> the RESCAN still reaches Gmail (fallback intact)")
opened["n"] = 0
ex.LEDGER_ROWS[:] = []
ex.kalshi_rest_reports()
check("one IMAP connection opened for the rescan", opened["n"] == 1)
check("and it actually searched", opened["last"].calls >= 1)

print("\nA filled resting order -> already_reported() still reaches Gmail before notifying")
opened["n"] = 0
ex.LEDGER_ROWS[:] = [rest_row("OID1")]
bl._k_call = lambda m, p, *a, **k: (200, {"order": {"status": "resting", "fill_count": 3,
                                                    "remaining_count": 2, "initial_count": 5}})
seen = {}
ex.already_reported = lambda M, toks, days=None: seen.setdefault("toks", list(toks)) and set() or set()
ex.kalshi_rest_reports()
check("IMAP opened for the dedupe lookup", opened["n"] == 1)
check("a fill token was offered for dedupe", len(seen.get("toks") or []) == 1)
check("and it is the stable xkrf id keyed on order+fill count",
      (seen.get("toks") or [""])[0].startswith("xkrf"))

print("\nA DIFFERENT fill count mints a DIFFERENT token (delayed/extra fills report once each)")
t1 = (seen.get("toks") or [""])[0]
opened["n"] = 0
seen.clear()
bl._k_call = lambda m, p, *a, **k: (200, {"order": {"status": "resting", "fill_count": 5,
                                                    "remaining_count": 0, "initial_count": 5}})
ex.kalshi_rest_reports()
t2 = (seen.get("toks") or [""])[0]
check("token changed with the fill count", t1 and t2 and t1 != t2)

print("\nUnavailable venue data is NOT read as zero fills")
opened["n"] = 0
seen.clear()


def boom(*a, **k):
    raise RuntimeError("kalshi unreachable")


bl._k_call = boom
ex.kalshi_rest_reports()
check("no fill token was produced from an unreadable order", not seen.get("toks"))
check("so nothing was reported as filled or as unfilled", True)

ex.imap_open, ex.imap_close, bl._k_call, ex.already_reported, ex.push, ex.tg, ex.send = _orig

print()
if fails:
    print(f"FAIL  test_kalshi_lazy_imap.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")

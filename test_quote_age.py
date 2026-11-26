"""Quote-age logging (Nov 26): provider timestamps and receipt time reach the alert record; logging only."""
import sharp_monitor as sm

FAILED = []


def ok(n, c):
    print(("PASS  " if c else "FAIL  ") + n)
    if not c:
        FAILED.append(n)


ev = {"bookmakers": [{"key": "pinnacle", "last_update": "2026-11-26T17:00:00Z", "markets": [
    {"key": "spreads", "last_update": "2026-11-26T17:00:05Z"}, {"key": "totals", "last_update": "2026-11-26T16:58:00Z"}]},
    {"key": "novig", "last_update": "2026-11-26T16:59:00Z", "markets": []}]}
ok("market-level timestamp for spreads", sm.quote_lu(ev, "pinnacle", "spr") == "2026-11-26T17:00:05Z")
ok("totals read their own market", sm.quote_lu(ev, "pinnacle", "tot") == "2026-11-26T16:58:00Z")
ok("book-level fallback when the market is absent", sm.quote_lu(ev, "novig", "spr") == "2026-11-26T16:59:00Z")
ok("unknown book -> None", sm.quote_lu(ev, "kalshi", "spr") is None)
t = sm.parse_iso("2026-11-26T17:01:05Z").timestamp()
ok("age in seconds at the alert", sm._age_s("2026-11-26T17:00:05Z", t) == 60)
ok("missing timestamp -> None, never a guess", sm._age_s(None, t) is None)
src = open("sharp_monitor.py").read()
ok("alerts.json carries the quote fields", '"pin_quote_age_s": _age_s(' in src and '"quote_recv_utc": e.get("q_recv")' in src)
ex = open("executor.py").read()
ok("order journal carries submit and answer times", '"submitted_utc": lo.get("submitted_utc")' in ex)
print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
raise SystemExit(1 if FAILED else 0)

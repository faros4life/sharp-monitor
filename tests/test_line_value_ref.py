"""Nov 12: the independent reference validates game, market, line, period, freshness and the reference book's rule."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_value as lv  # noqa: E402
import line_value_ref as lr  # noqa: E402

OK, BAD = [], []


def ck(n, c, d=""):
    (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))


NOW = datetime(2026, 11, 12, 13, 0, 0, tzinfo=timezone.utc)
START = "2026-11-12T18:00:00Z"
iso = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def feed(kind="spread", pts=(-2.5, 2.5), prices=(-110, -110), age=30, commence=START, mine="A", book="pinnacle"):
    names = ("A", "B") if kind == "spread" else ("Over", "Under")
    return {"market": {"outcomes": [{"name": names[0], "point": pts[0], "price": prices[0]},
                                    {"name": names[1], "point": pts[1], "price": prices[1]}],
                       "last_update": iso(NOW - timedelta(seconds=age + 40))},
            "mine": mine if kind == "spread" else "Over", "book": book, "read_utc": iso(NOW - timedelta(seconds=age)),
            "commence_utc": commence}


r, rec = lr.pinnacle_reference(feed(), "spread", 0, START, NOW, "NFL")
ck("good spread feed -> Reference at its own line with q de-vigged", r and r.line == -2.5 and abs(r.q - 0.5) < 1e-12 and r.source == "pinnacle", str(rec))
ck("record carries both prices, last_update, read time, age, gap, period, devig method",
   all(k in rec for k in ("am_mine", "am_other", "last_update", "read_utc", "age_s", "start_gap_min", "period", "devig")), str(rec))
r, rec = lr.pinnacle_reference(feed(prices=(-120, 100)), "spread", 0, START, NOW, "NFL")
ck("q is the de-vigged share of OUR side", r and abs(r.q - lv.devig_two_sided(-120, 100)) < 1e-12 and r.q > 0.5, str(rec))
cases = [("one-sided market", {"market": {"outcomes": [{"name": "A", "point": -2.5, "price": -110}]}, "mine": "A", "read_utc": iso(NOW), "commence_utc": START}, "not_two_sided"),
         ("our side not identified", feed(mine="Z"), "our_side_not_identified"),
         ("handicaps not mirrored", feed(pts=(-2.5, 3.5)), "handicaps_not_mirrored"),
         ("implausible overround", feed(prices=(-110, 400)), "implausible_overround"),
         ("stale read", feed(age=900), "stale_read"),
         ("future read time", feed(age=-600), "stale_read"),
         ("different game start", feed(commence="2026-11-13T18:00:00Z"), "different_game_start"),
         ("no commence time", dict(feed(), commence_utc=None), "game_time_unverifiable"),
         ("feed said why", {"why": "pinnacle_not_cached"}, "pinnacle_not_cached"),
         ("no feed", None, "pinnacle_not_read")]
for name, inp, why in cases:
    r, rec = lr.pinnacle_reference(inp, "spread", 0, START, NOW, "NFL")
    ck(f"{name} -> no reference, reason '{why}'", r is None and rec["why"].startswith(why), str(rec["why"]))
r, rec = lr.pinnacle_reference(feed(), "moneyline", 0, START, NOW, "NFL")
ck("a moneyline is refused", r is None and rec["why"] == "market_not_spread_or_total")
# totals
r, rec = lr.pinnacle_reference(feed("total", pts=(44.5, 44.5)), "total", "OVER", START, NOW, "NFL")
ck("total at a half line -> Reference", r and r.line == 44.5, str(rec))
r, rec = lr.pinnacle_reference(feed("total", pts=(44.5, 45.5)), "total", "OVER", START, NOW, "NFL")
ck("totals with different points are refused", r is None and rec["why"] == "totals_points_differ")
# whole-number REFERENCE lines need the reference book's refund rule
r, rec = lr.pinnacle_reference(feed(pts=(-3.0, 3.0)), "spread", 0, START, NOW, "NFL")
ck("whole-number SPREAD reference allowed (pinnacle.com states the refund)", r and r.line == -3.0 and rec["settlement"] == "refund", str(rec))
r, rec = lr.pinnacle_reference(feed("total", pts=(44.0, 44.0)), "total", "OVER", START, NOW, "NFL")
ck("whole-number TOTAL reference refused until a primary Pinnacle rule is read",
   r is None and rec["why"] == "reference_settlement_unverified_on_whole_line", str(rec))
ck("the unverified total rule is recorded as unverified", "NOT VERIFIED" in lr.REFERENCE_SETTLEMENT_SOURCE[("pinnacle", "total")])
r, rec = lr.pinnacle_reference(feed(pts=(-3.0, 3.0), book="somebook"), "spread", 0, START, NOW, "NFL")
ck("a different reference book gets no pinnacle rule", r is None, str(rec))
r, rec = lr.pinnacle_reference({"market": "garbage", "mine": 1}, "spread", 0, START, NOW, "NFL")
ck("garbage input never raises", r is None and rec["why"].startswith("error:"), str(rec))
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD:
    print("FAIL", b)
sys.exit(1 if BAD else 0)

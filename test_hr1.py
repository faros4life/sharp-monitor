#!/usr/bin/env python3
"""HR1 (Peter, 17 Nov 2026): the manual Hard Rock college-basketball alert rule, and its push wiring."""
import agree_rules as ar

GOOD = {"sport": "NCAAB", "book_key": "hardrockbet", "top25": False, "kind": "tot", "bet": "Under 140.5 (-110)",
        "price_after_fee": -110, "late": False, "alert_utc": "2026-11-17T18:00:00Z", "start_utc": "2026-11-18T00:00:00Z"}


def m(**kw):
    return dict(GOOD, **kw)


def t_rule():
    assert ar.hr1(GOOD) == (True, [])
    assert ar.hr1(m(kind="spr", bet="Duke -6.5 (-108)"))[0]                   # spreads in
    assert ar.hr1(m(book_key="hardrockbet_fl"))[0]                            # either Hard Rock key
    for bad, word in ((m(sport="NCAAF"), "college basketball"), (m(sport="NBA"), "college basketball"),
                      (m(book_key="prophetx"), "Hard Rock"), (m(book_key=None), "Hard Rock"),
                      (m(top25=True), "non-Top-25"), (m(top25=None), "non-Top-25"),
                      (m(bet="Over 140.5 (-110)"), "unders only"), (m(kind="ml", bet="Duke ML"), "unders only"),
                      (m(price_after_fee=-120), "outside"), (m(price_after_fee=-100), "outside"),
                      (m(price_after_fee=100), "outside"), (m(price_after_fee=None), "outside"),
                      (m(price_after_fee="x"), "unreadable"), (m(late=True), "late"),
                      (m(start_utc="2026-11-17T18:30:00Z"), "60 min"), (m(start_utc=None), "60 min")):
        ok, why = ar.hr1(bad)
        assert ok is False and any(word in w for w in why), (bad, why)
    assert ar.hr1(m(price_after_fee=-119))[0] and ar.hr1(m(price_after_fee=-101))[0]   # band is inclusive


def t_push_wiring():
    s = open("sharp_monitor.py").read()
    assert "hr1_ok = False" in s and "_ar.hr1(" in s
    assert "(not repeat) and" in s                                  # first alert per game/market/side only
    # hr1_ok must be bound on EVERY path: it is read outside the if/elif/else chain that computes it, so an alert
    # taking an earlier branch (the Hard Rock spread-dog skip) killed three runs on 17 Nov.
    init = [l for l in s.split("\n") if l.strip().startswith("hr1_ok = False")]
    assert len(init) == 1 and len(init[0]) - len(init[0].lstrip()) == 20
    assert s.index("hr1_ok = False") < min(s.index(x) for x in ("if hr1_ok:", "or hr1_ok)", "if hr1_ok else"))
    assert "PUSH_SHARP or p1_ok or hr_ev or hr1_ok" in s            # HR1 is pushed even while paper alerts are muted
    assert "live=p1_ok or hr1_ok" in s                              # ... and mirrored to Telegram
    assert "HR1 MANUAL " in s and "HR1 MANUAL BET at HARD ROCK" in s
    # HR1 must not reach any betting decision: no executor or gate reads it
    for f in ("executor.py", "book_live.py"):
        try:
            assert "hr1" not in open(f).read().lower().replace("hr1_", "")
        except FileNotFoundError:
            pass


def t_backtest_population():
    """The shipped rule must reproduce the population the decision was made on."""
    import json
    import clv_scorecard as sc
    rows, seen = [], set()
    for a in sorted(json.load(open("alerts.json"))["alerts"], key=lambda a: a.get("alert_utc") or ""):
        if a.get("result") not in ("W", "L", "P") or not ar.hr1(a)[0]:
            continue
        k = (str(a.get("start_utc"))[:10], frozenset(sc.toks(a.get("game"))), a.get("kind"), ar.side_of(a))
        if k in seen:
            continue
        seen.add(k)
        rows.append(a)
    w = sum(a["result"] == "W" for a in rows)
    assert len(rows) >= 120 and w >= 78, (len(rows), w)   # 124 and 81 at adoption; grows forward


def t_record_kept():
    """HR1 alerts stay on the record whether or not Peter bets them: the push flag is stored, and the rule's
    verdict is written beside it. An HR1 alert he skipped must never look like no alert at all."""
    s = open("sharp_monitor.py").read()
    assert 'if hr1_ok:' in s and 'e["hr1"] = True' in s          # push decision persisted on the durable event
    assert '"hr1_pushed": bool(e.get("hr1")),' in s              # ... and exported
    assert 'row["hr1_eligible"] = _ar.hr1(row)[0]' in s          # ... with the rule's verdict on the stored row
    assert s.index('e["hr1"] = True') > s.index("hr1_ok = False")
    # the report reads the rule, not a hand-copied filter
    r = open("last50_report.py").read()
    assert "def hr1_rows" in r and "ar.hr1(x)[0]" in r





def t_prices_at_alert():
    """Nov 17: every bettable venue's price for the alerted side, captured at alert time. Logging only."""
    import sharp_monitor as sm
    assert set(sm.BET_BOOKS) >= {"novig", "kalshi", "prophetx", "polymarket_us", "hardrockbet"}
    p = sm.book_prices([(224.5, -110, "novig"), (224.5, -105, "novig"), (224.5, -108, "kalshi"),
                        (224.5, -112, "pinnacle"), (224.5, -109, "betonlineag"), (224.5, None, "prophetx")], "NBA")
    assert set(p) == {"novig", "kalshi"}                      # only venues Peter can bet; junk dropped
    assert p["novig"]["price"] == -105                        # best after-fee per book kept
    assert p["novig"]["point"] == 224.5 and isinstance(p["novig"]["after_fee"], (int, float))
    assert p["kalshi"]["after_fee"] < p["kalshi"]["price"]        # the venue fee is applied, not the raw price
    assert sm.book_prices([(-110, "novig")], "NBA")["novig"]["point"] is None   # two-tuple (RL/ML) form
    assert sm.book_prices(None, "NBA") == {} and sm.book_prices([], "NBA") == {}
    s = open("sharp_monitor.py").read()
    assert s.count("offers=offers") == 4                      # spreads, totals, run line, moneyline
    assert 'prices=book_prices(offers, cfg["label"])' in s
    assert '"prices_at_alert": e.get("prices") or None,' in s
    assert '"fade", "prices")' in s                           # carried onto the durable event


for f in (t_rule, t_push_wiring, t_backtest_population, t_record_kept, t_prices_at_alert):
    f()
print("hr1 tests: OK")

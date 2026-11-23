#!/usr/bin/env python3
"""Offline tests for live_ledger (no network, no secrets). Each case mirrors a real Nov 12-16 shape."""
import os
import sys

os.environ.setdefault("TRACKER_PASSPHRASE", "synthetic-test-only")
import live_ledger as ll

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)


def ev(kind, rid, data, t="2026-11-16T13:00:00Z"):
    return {"kind": kind, "id": rid, "seen_utc": t, "sha": "x", "data": data}


E = [
    # R1 Novig taker fill, tracker row only on the bot wallet (E3); PSU abbreviation in tracker text
    ev("order", "o1", {"key": "r1|NCAAF|Minnesota Golden Gophers @ Penn State Nittany Lions|side|Penn State Nittany Lions",
                       "source": "r1", "decided_utc": "2026-11-14T01:26:00Z",
                       "live_order": {"book": "novig", "order_id": "c1", "status": "placed"}}),
    ev("fill", "v1", {"client_id": "c1", "state": "FILLED", "filled_qty": 100, "avg_price": None}),
    # Board ProphetX: filled_stake on the leg, tracker row is "Peter" but order_ref matches (E1) -> Board, not manual
    ev("order", "o2", {"key": "board|NBA|Milwaukee vs Orlando: Total Points|total|UNDER", "source": "board",
                       "decided_utc": "2026-11-13T19:06:00Z",
                       "live_order": {"book": "prophetx", "order_id": "partner_abc", "filled_stake": 204,
                                      "avg_price": -102, "status": "placed"}}),
    # Board Novig placed, NO fill record, tracker shows Peter's own bet on the same play -> UNRESOLVED
    ev("order", "o3", {"key": "board|NBA|Charlotte vs Phoenix: Total Points|total|UNDER", "source": "board",
                       "decided_utc": "2026-11-12T17:35:00Z",
                       "live_order": {"book": "novig", "order_id": "c3", "status": "placed"}}),
    # Lane 1 voided intent -> excluded
    ev("order", "o4", {"key": "rule|NBA|New York Knicks @ Indiana Pacers|total|UNDER", "source": "rules",
                       "decided_utc": "2026-11-13T13:21:00Z", "voided": True,
                       "live_order": {"book": "novig", "status": "void"}}),
    # Lane 1 NO_FILL with no tracker row -> excluded, not unresolved
    ev("order", "o5", {"key": "rule|NBA|Brooklyn Nets @ Memphis Grizzlies|total|UNDER", "source": "rules",
                       "decided_utc": "2026-11-14T19:51:00Z",
                       "live_order": {"book": "novig", "order_id": "c5", "status": "placed"}}),
    ev("fill", "c5", {"client_id": "c5", "state": "NO_FILL", "filled_qty": None}),
    # R1 duplicate orders (same play twice, with and without prefix), resting leg fills via venue-id map
    ev("order", "o6", {"key": "r1|NCAAB|Xavier Musketeers @ Mississippi St Bulldogs|total|UNDER", "source": "r1",
                       "decided_utc": "2026-11-13T16:57:00Z",
                       "live_order": {"book": "novig", "order_id": "c6a", "status": "placed"},
                       "live_rest": {"book": "novig", "order_id": "c6b", "status": "placed"}}),
    ev("order", "o6b", {"key": "NCAAB|Xavier Musketeers @ Mississippi St Bulldogs|total|UNDER", "source": "r1",
                        "decided_utc": "2026-11-13T16:58:00Z",
                        "live_order": {"book": "novig", "order_id": "c6a", "status": "placed"}}),
    ev("venue_id", "c6a", {"venue_order_id": "V6A"}),
    ev("fill", "V6A", {"client_id": "zz", "state": "FILLED", "filled_qty": 69, "avg_price": None}),
    ev("fill", "c6b", {"client_id": "c6b", "state": "FILLED", "filled_qty": 346, "avg_price": 0.52}),
    # R1 Polymarket US leg filled on the order row; the tracker row has no order id and is labelled Peter (Stanford case)
    ev("order", "o7", {"key": "r1|NCAAF|Stanford Cardinal @ Virginia Tech Hokies|side|Virginia Tech Hokies", "source": "r1",
                       "decided_utc": "2026-11-14T14:57:00Z",
                       "live_order": {"book": "polymarket_us", "order_id": "DQ1", "filled_stake": 207.57,
                                      "avg_price": -104, "status": "placed"}}),
    # Virginia Tech plays twice in the week: an NCAAB voided intent must not grab the NCAAF tracker row
    ev("order", "o8", {"key": "r1|NCAAB|Mt. St. Mary's Mountaineers @ Virginia Tech Hokies|side|Mt. St. Mary's Mountaineers",
                       "source": "r1", "decided_utc": "2026-11-13T14:30:00Z", "voided": True,
                       "live_order": {"book": "prophetx", "status": "void"}}),
    # an order row that names no lane -> excluded, must not crash
    ev("order", "o9", {"key": "NBA|Phoenix Suns @ Utah Jazz|total|UNDER", "source": "muse",
                       "decided_utc": "2026-11-15T14:00:00Z", "live_order": {"book": "novig", "status": "placed"}}),
    # before the window -> ignored
    ev("order", "o0", {"key": "board|NBA|Denver vs Memphis: Total Points|total|UNDER", "source": "board",
                       "decided_utc": "2026-11-11T16:50:00Z",
                       "live_order": {"book": "novig", "order_id": "c0", "status": "placed"}}),
]
L = {"events": E}

B = {
    "nv|psu": {"source": "bot", "book": "Novig", "game": "Minnesota @ Penn State", "bet": "PSU -10.5", "price": -111,
               "result": "W", "first_seen": "2026-11-14T01:45:00Z", "game_start": "2026-11-15T00:00Z"},
    "px|1": {"source": "Peter", "book": "ProphetX", "game": "Milwaukee Bucks at Orlando Magic", "bet": "under 223.5",
             "price": -102, "result": "W", "order_ref": "partner_abc", "first_seen": "2026-11-13T19:10:00Z"},
    "nv|cha": {"source": "Peter", "book": "Novig", "game": "Charlotte Hornets @ Phoenix Suns", "bet": "Under 214.5",
               "price": -100, "result": "W", "first_seen": "2026-11-12T18:00:00Z"},
    "mn|cha": {"source": "Peter (Hard Rock note)", "book": "Novig", "game": "Charlotte Hornets @ Phoenix Suns",
               "bet": "Under 214.5 (+100)", "price": 100, "result": "W", "first_seen": "2026-11-12T18:05:00Z"},
    "nv|xav": {"source": "bot", "book": "Novig", "game": "Xavier @ Mississippi State", "bet": "Under 163.5",
               "price": -108, "result": "W", "first_seen": "2026-11-13T17:01:00Z"},
    # 13 partial fills of one manual ProphetX bet, plus a feed alert before it
    **{f"px|t{n}": {"source": "Peter", "book": "ProphetX", "game": "Toronto Raptors at Philadelphia 76ers",
                    "bet": "under 223.5", "price": 104, "result": "L", "order_ref": "manualref",
                    "first_seen": "2026-11-12T20:00:00Z"} for n in range(13)},
    # Lane 1 fills the ledger has not caught up with (E2)
    **{f"px|g{n}": {"source": "Peter", "book": "ProphetX", "game": "Golden State Warriors at New Orleans Pelicans",
                    "bet": "under 224.5", "price": -111, "order_ref": "partner_gsw", "lane": "rules",
                    "lane_src": "registry-order-id", "league": "NBA", "first_seen": "2026-11-16T14:41:00Z"}
       for n in range(4)},
    "pm|stan": {"source": "Peter", "book": "Polymarket US", "game": "Stanford vs. Virginia Tech", "bet": "-15.50", "league": "NCAAF",
                "price": -114, "result": "L", "first_seen": "2026-11-14T14:58:00Z"},
    # manual ProphetX rows on the Knicks play whose bot intents were all voided
    **{f"px|k{n}": {"source": "Peter", "book": "ProphetX", "game": "New York Knicks at Indiana Pacers", "bet": "under 219.5",
                    "price": -114, "result": "W", "order_ref": "webref", "first_seen": "2026-11-13T15:00:00Z"} for n in range(3)},
    # Street Value, documented tag
    "hr|sv": {"source": "Street Value", "book": "Hard Rock", "game": "Jets @ Chiefs", "bet": "Chiefs -9.5 (-110)",
              "price": -110, "result": "W", "first_seen": "2026-11-15T15:00:00Z"},
    # manual with no alert anywhere
    "nv|lsu": {"source": "Peter", "book": "Novig", "game": "Texas @ LSU", "bet": "LSU -3.5", "price": -108,
               "result": "L", "first_seen": "2026-11-14T15:00:00Z"},
}
C = {"nv|psu": {"how": "own line", "close_p": 0.55}, "nv|xav": {"how": "main 163.5 moved to 162.5", "close_p": 0.6}}
A = [{"t": "2026-11-12T15:00:00Z", "game": "Toronto vs Philadelphia: Total Points", "src": "liquidity alert",
      "mk": "total", "side": "UNDER"}]

R = ll.account(L, B, C, A)
P = {p["key"]: p for p in R["plays"]}

psu = P.get("NCAAF|Minnesota Golden Gophers @ Penn State Nittany Lions|side|Penn State Nittany Lions")
check("R1 Novig fill joins bot-wallet row", psu and psu["lane"] == "R1" and psu["res"] == "W"
      and psu["evidence"] == "E3 bot-wallet" and psu["am"] == -111)
check("certified CLV on own line", psu and psu["clv"] is not None)

mil = P.get("NBA|Milwaukee vs Orlando: Total Points|total|UNDER")
check("ProphetX order_ref attributes to Board", mil and mil["lane"] == "BOARD V4" and mil["evidence"] == "E1 order-id"
      and mil["res"] == "W" and mil["am"] == -102)
check("after-fee price applies the ProphetX fee", mil and mil["am_net"] == -104)
stan = P.get("NCAAF|Stanford Cardinal @ Virginia Tech Hokies|side|Virginia Tech Hokies")
check("confirmed PM US bot fill graded from the game settlement (E4)", stan and stan["lane"] == "R1" and stan["res"] == "L"
      and stan["evidence"].startswith("E4") and stan["am"] == -104)

xav = P.get("NCAAB|Xavier Musketeers @ Mississippi St Bulldogs|total|UNDER")
check("duplicate orders merge to one play", xav is not None and sum(
    1 for k in P if "Xavier" in k) == 1)
check("both legs confirmed (venue map + resting fill)", xav and xav["fills"] == 2 and xav["res"] == "W")
check("converted close is NOT certified", xav and xav["clv"] is None)

ex_keys = {e["key"]: e["why"] for e in R["excluded"]}
check("voided intent never counted", not any("Knicks" in k for k in P)
      and any("Knicks" in u["key"] and "voided" in u["why"] for u in R["unresolved"]))
check("NO_FILL excluded", any("Brooklyn" in k and "NO_FILL" in w for k, w in ex_keys.items()))
check("no-lane order excluded", any("Phoenix" in k and "no lane" in w for k, w in ex_keys.items()))
check("pre-window order ignored", not any("Denver" in k for k in list(P) + list(ex_keys)))

un = R["unresolved"]
uk = {u["key"]: u for u in un}
cha = [u for k, u in uk.items() if "Charlotte" in k]
check("placed-no-fill + manual row = UNRESOLVED", len(cha) == 1 and set(cha[0]["rows"]) == {"nv|cha", "mn|cha"})
check("tracker row on a confirmed bot fill is UNRESOLVED, not manual", any("Stanford" in k for k in uk))
check("same team, other sport: no false join", not any("Mt. St. Mary" in u["key"] for u in un)
      and any("Mt. St. Mary" in e["key"] for e in R["excluded"]))
check("voided bot intent + manual rows = UNRESOLVED", any("Knicks" in k and len(u["rows"]) == 3 for k, u in uk.items()))

gsw = [p for p in R["plays"] if "Golden State" in p["key"]]
check("registry-order-id rows become one Lane 1 play", len(gsw) == 1 and gsw[0]["lane"] == "LANE 1"
      and gsw[0]["evidence"] == "E2 registry" and gsw[0]["status"] == "open" and gsw[0]["fills"] == 4)

M = R["manual"]
tor = [m for m in M if "Toronto" in m["game"]]
check("13 partial fills merge to one manual bet", len(tor) == 1 and tor[0]["merged"] == 13)
check("feed origin found for Toronto", tor and tor[0]["src"] == "Peter feed")
check("no bot fill counted as manual", not any(set(m["rows"]) & {"px|1", "nv|cha", "mn|cha", "pm|stan", "px|k0"} for m in M))
check("Street Value kept separate", any(m["src"] == "Street Value" for m in M))
check("manual without alert is not Peter feed", any("LSU" in m["game"] and m["src"] == "manual, no feed origin" for m in M))

rest = ll.resting(L)
check("resting leg recorded once per play", sum(1 for r in rest if "Xavier" in r["key"]) == 1
      and any("Xavier" in r["key"] and r["filled"] for r in rest))

check("one shared team is not the same game", not ll.same_game("Brooklyn Nets @ Memphis Grizzlies",
                                                                "Brooklyn Nets @ New Orleans Pelicans"))
check("venue name styles match", ll.same_game("Milwaukee vs Orlando: Total Points", "Milwaukee Bucks at Orlando Magic")
      and ll.same_game("Stanford vs. Virginia Tech", "Stanford Cardinal @ Virginia Tech Hokies"))
check("NOT-side alert backs the other team", ll.feed_origin(
    {"first_seen": "2026-11-15T21:26:00Z", "game": "San Francisco 49ers @ Dallas Cowboys", "bet": "Cowboys +3.5 (-110)"},
    [{"t": "2026-11-15T19:00:00Z", "game": "San Francisco vs Dallas: Spread", "src": "liquidity alert", "mk": "side",
      "side": "NOT San Francisco wins by over 3.5 points"}]) == "liquidity alert")
check("alert after the bet is not an origin", ll.feed_origin(
    {"first_seen": "2026-11-10T01:00:00Z", "game": "Miami Dolphins @ Indianapolis Colts", "bet": "IND -2.5"},
    [{"t": "2026-11-15T17:20:00Z", "game": "Miami Dolphins @ Indianapolis Colts", "src": "liquidity alert", "mk": "side",
      "side": "IND -4.5"}]) is None)
check("an alert on the same matchup weeks earlier is not an origin", ll.feed_origin(
    {"first_seen": "2026-11-15T21:26:00Z", "game": "San Francisco 49ers @ Dallas Cowboys", "bet": "Cowboys +3.5 (-110)"},
    [{"t": "2026-10-05T15:25:00Z", "game": "San Francisco 49ers @ Dallas Cowboys", "src": "sharp alert", "mk": "side",
      "side": "Dallas Cowboys +3.5 (-110)"}]) is None)
check("am_of probability", ll.am_of(0.52) == -108 and ll.am_of(0.4) == 150 and ll.am_of(-110) == -110)

if FAILS:
    print(f"FAIL  test_live_ledger.py  {len(FAILS)} failed: {FAILS}")
    sys.exit(1)
print("ok    test_live_ledger.py")

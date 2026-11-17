#!/usr/bin/env python3
"""Offline tests for paper_clv_certify (no network, no cache)."""
import paper_clv_certify as p
import last50_report as r


def t_flip():
    assert p.flip({"market": "total", "side": "Over", "line": 220})["side"] == "Under"
    y = p.flip({"market": "spread", "side": "Akron", "line": 14.5, "teams": ["Ohio", "Akron"],
                "ref": {"kalshi_side": "no", "market_ticker": "T"}})
    assert y["side"] == "Ohio" and y["line"] == -14.5 and y["ref"] == {"market_ticker": "T"}
    assert p.flip({"market": "moneyline", "side": "Suns", "teams": ["Spurs", "Suns"]})["side"] == "Spurs"
    assert p.flip({"market": "moneyline", "side": "X", "teams": ["Spurs", "Suns"]}) is None


def t_lane_inputs():
    lanes = {"pull_fade": {"a|t": {"entered": True, "result": "W", "price": 0.4},
                           "b|t": {"entered": True, "result": "L", "price": 0.5}},
             "solo": {"c|t": {"entered": False, "result": "W"}}}
    feed = {"a|t": {"market": "total", "side": "Over", "line": 200, "price": 0.6}}
    out = p.lane_inputs(lanes, feed)
    assert len(out) == 2
    i, y, why = [o for o in out if o[0] == "lane:pull_fade|a|t"][0]
    assert why is None and y["side"] == "Under" and y["price"] == 0.4
    assert feed["a|t"]["side"] == "Over"            # source row untouched
    assert [o for o in out if o[0] == "lane:pull_fade|b|t"][0][2].startswith("FIXTURE")


def t_certify():
    res = {"own": ("VERIFIED_PINNACLE", {"clv": 0.02, "entry": 1.9, "how": "own line", "age_min": 3, "fid": "f"}),
           "move": ("VERIFIED_PINNACLE", {"clv": 0.01, "entry": 1.9, "how": "main 5 moved to 5.5", "age_min": 3}),
           "noage": ("VERIFIED_PINNACLE", {"clv": 0.01, "entry": 1.9, "how": "own line", "age_min": None}),
           "miss": ("MISSING_HISTORY", "no file")}
    items = [(k, {"k": k}, "sharp", None) for k in res] + [("dup", {"k": "own"}, "sharp", None)] * 2 \
        + [("pre", None, "liquidity", "FIXTURE_OR_IDENTITY: x")]
    cert, est, rej = p.certify(items, lambda x, s: res[x["k"]])
    assert set(cert) == {"own"} and cert["own"]["clv_pct"] == 2.0
    assert set(est) == {"move"} and rej["move"].startswith("ESTIMATED_ONLY")
    assert rej["noage"].startswith("TIMING") and rej["miss"].startswith("MISSING")
    assert rej["dup"].startswith("AMBIGUOUS") and rej["pre"].startswith("FIXTURE")


def t_apply(tmp="/tmp/_pc.json"):
    import json
    json.dump({"certified": {"a": {"clv_pct": 1.5}, "b": {"clv_pct": 9.0}},
               "rejected": {"c": "VENUE_NOT_PRICEABLE: polymarket.global not tradeable from the US"}}, open(tmp, "w"))
    rows = [{"pid": "a", "clv": None, "pclv": 3.0}, {"pid": "b", "clv": 0.7}, {"pid": "c", "clv": None},
            {"pid": "d", "clv": None}]
    o = r.paper_certified(rows, tmp)
    assert o[0]["clv"] == 1.5 and o[0]["pclv"] == 3.0     # filled; provisional kept separately
    assert o[1]["clv"] == 0.7                             # existing certified value never overwritten
    assert o[2]["us_exec"] is False and o[3]["us_exec"] is True and o[3]["clv"] is None   # gap stays a gap


for f in (t_flip, t_lane_inputs, t_certify, t_apply):
    f()
print("paper_clv_certify tests: OK")

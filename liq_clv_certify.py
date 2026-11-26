#!/usr/bin/env python3
"""CERTIFIED PINNACLE CLV FOR LIQ-SMALL AND LIQ-BOT (Peter, 16 Nov 2026). Cache-only, read-only.

The Last 50 page showed the liquidity board's own exchange close as CLV. This job certifies a
Pinnacle close instead, for the NBA-totals liquidity alerts that LIQ-SMALL (reg 13) and LIQ-BOT
(reg 9) draw from, using the SAME waterfall the observation audit uses (clv_obs_audit.classify):
executable after-fee entry, a bet that parses into market/side/line, a unique fixture, cached
Pinnacle history, and the ledger's no-vig close (same line, or the standard line-move adjustment;
last pregame quote). On top of that it requires the parsed market to be a TOTAL and rejects any
alert id that appears more than once.

NO NETWORK. Pinnacle history comes only from the restored hcache; fixtures from the ledger state
and the committed fixture stores. The workflow passes no OddsPapi key, so no call is possible.

Writes liquidity/clv_certified.json: per alert id, the certified CLV (percent), fixture id, method
and quote age, or the rejection class and reason. No stakes, no balances. Log: counts only.
"""
import collections
import json
import os
import sys
from datetime import datetime, timezone

import clv_basis as cb
import clv_ledger as cl
import clv_obs_audit as oa
import fixture_match as fxm
import tracker_build as tb

OUT = "liquidity/clv_certified.json"


def in_scope(x):
    """The union of LIQ-SMALL and LIQ-BOT, exactly as last50_report selects them."""
    if not isinstance(x, dict) or x.get("result") not in ("W", "L", "P") or x.get("artifact") or x.get("close_suspect"):
        return False
    if x.get("league") != "NBA" or x.get("market") != "total":
        return False
    lead, nm = x.get("lead_min"), x.get("new_money")
    return (lead is not None and lead >= 240) or (nm is not None and 25000 <= nm <= 50000)


def alert_id(x):
    return f"{x.get('key')}|{x.get('alerted_utc')}"


def certify(rows, classify, parsed_kind):
    """(certified {id: {...}}, rejected {id: reason}). Pure given classify/parsed_kind."""
    ids = collections.Counter(alert_id(x) for x in rows)
    cert, rej = {}, {}
    for x in rows:
        i = alert_id(x)
        if ids[i] > 1:
            rej[i] = "AMBIGUOUS: alert id appears more than once"
            continue
        cls, d = classify(x)
        if cls != "VERIFIED_PINNACLE" or not isinstance(d, dict) or d.get("clv") is None:
            rej[i] = f"{cls}: {str(d)[:90]}"
            continue
        if parsed_kind(x) != "total":
            rej[i] = "MARKET: the bet does not parse as a total"
            continue
        if d.get("age_min") is None:
            rej[i] = "TIMING: no quote age recorded for the close"
            continue
        cert[i] = {"clv_pct": round(100 * d["clv"], 3), "fid": d.get("fid"), "how": d.get("how"),
                   "src": d.get("src") or "oddspapi",   # Nov 26: tagged by source (approved for the scorecard)
                   "age_min": d.get("age_min"), "entry_dec": round(d["entry"], 4) if d.get("entry") else None}
    return cert, rej


def main():
    now = datetime.now(timezone.utc)
    st = tb.dec(json.load(open(cl.STATE)))
    mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
    fxs = st.get("fixtures") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    allfx = dict(alt, **fxs)
    hc = len(os.listdir(oa.HC)) if os.path.isdir(oa.HC) else 0
    rows = [x for x in oa.load(oa.LIQ) if in_scope(x)]
    cert, rej = certify(rows, lambda x: oa.classify(x, "liquidity", fxs, alt, allfx, mkmap),
                        lambda x: (cl.parsed(oa.snap_for(x, "liquidity")) or [None])[0])
    json.dump({"generated": cl.iso(now), "basis": cb.BASIS_VERSION, "scope": "NBA totals: lead >= 240 min OR new money 25-50k",
               "method": "clv_obs_audit.classify (cache-only) + total-market and unique-id checks",
               "certified": cert, "rejected": rej}, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"liq certify: in scope {len(rows)} | certified {len(cert)} | rejected {len(rej)} | hcache files {hc} | "
          f"fixtures {len(allfx)}")
    print("rejections by class:", dict(collections.Counter(v.split(":")[0] for v in rej.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

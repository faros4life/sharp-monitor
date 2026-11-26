#!/usr/bin/env python3
"""CERTIFIED PINNACLE CLV FOR THE OTHER LAST-50 PAPER TESTS (Peter, 17 Nov 2026: "yes run them"). Cache-only.

liq_clv_certify covers LIQ-SMALL / LIQ-BOT. Eight Last 50 tests still showed provisional CLV only. This certifies
them through the SAME waterfall (clv_obs_audit.classify), with no network:

  sharp  - alerts.json rows (Steam, sent-to-phone, NBA unders, exchange misprice). American after-fee entry.
  liq    - liquidity rows (the Kalshi NBA-under test). 0-1 cost entry, structured market/side/line.
  lane   - lanes/lanes.json entries (pull_fade, solo, ml_stay). Each lane entry IS a liquidity alert id; the bet
           is rebuilt from that source row with the LANE's entry price. pull_fade bets the OPPOSITE side, so the
           side is flipped (moneyline/spread: the other team, spread line negated; total: Over<->Under).

Certified = VERIFIED_PINNACLE with how in CERT_HOW (own line / exact moneyline) and a recorded quote age. A
line-move adjusted close is written under "estimated" and never counted as certified. A row id seen twice is
rejected as ambiguous. Writes paper/clv_certified.json (CLV percents only, no stakes). Log: counts only.
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

OUT = "paper/clv_certified.json"
LANES = "lanes/lanes.json"
CERT_HOW = ("own line", "moneyline")


def sharp_id(x):
    return f"sharp|{x.get('alert_utc')}|{x.get('game')}|{x.get('bet')}|{x.get('book_key')}"


def liq_id(x):
    return f"liq|{x.get('key')}|{x.get('alerted_utc')}"


def lane_id(name, k):
    return f"lane:{name}|{k}"


def flip(src):
    """The opposite side of a liquidity row's market, or None when it cannot be stated without guessing."""
    mk = str(src.get("market") or "").lower()
    side = str(src.get("side") or "").strip()
    y = dict(src)
    if mk.startswith("total"):
        o = {"over": "Under", "under": "Over"}.get(side.lower())
        if not o:
            return None
        y["side"] = o
        return y
    tms = [t if isinstance(t, str) else (t or {}).get("name") for t in (src.get("teams") or [])][:2]
    if len(tms) != 2 or side not in tms:
        return None
    y["side"] = tms[1] if side == tms[0] else tms[0]
    if mk.startswith("spread"):
        ln = tb.num(src.get("line"))
        if ln is None:
            return None
        y["line"] = -ln
    if isinstance(y.get("ref"), dict):
        y["ref"] = {k: v for k, v in y["ref"].items() if k != "kalshi_side"}
    return y


def lane_inputs(lanes, feed):
    """[(id, liquidity-shaped row or None, reason)] for every graded, entered lane bet."""
    out = []
    for name in ("pull_fade", "solo", "ml_stay"):
        for k, e in ((lanes or {}).get(name) or {}).items():
            if not isinstance(e, dict) or not e.get("entered") or e.get("result") not in ("W", "L", "P"):
                continue
            i = lane_id(name, k)
            src = feed.get(k)
            if src is None:
                out.append((i, None, "FIXTURE_OR_IDENTITY: source liquidity alert not in the feeds"))
                continue
            y = flip(src) if name == "pull_fade" else dict(src)
            if y is None:
                out.append((i, None, "FIXTURE_OR_IDENTITY: opposite side cannot be stated"))
                continue
            y["price"] = e.get("price")
            out.append((i, y, None))
    return out


def certify(items, classify):
    """items: [(id, row, src, pre_reject)]. Returns (cert, est, rej). Pure given classify."""
    ids = collections.Counter(i for i, *_ in items)
    cert, est, rej = {}, {}, {}
    for i, x, src, pre in items:
        if ids[i] > 1:
            rej[i] = "AMBIGUOUS: row id appears more than once"
            continue
        if pre:
            rej[i] = pre
            continue
        cls, d = classify(x, src)
        if cls != "VERIFIED_PINNACLE" or not isinstance(d, dict) or d.get("clv") is None:
            rej[i] = f"{cls}: {str(d)[:90]}"
            continue
        if d.get("age_min") is None:
            rej[i] = "TIMING: no quote age recorded for the close"
            continue
        rec = {"clv_pct": round(100 * d["clv"], 3), "fid": d.get("fid"), "how": d.get("how"),
               # Nov 26 (Peter): approved for the scorecard, tagged by source
               "src": d.get("src") or "oddspapi",
               "age_min": d.get("age_min"), "entry_dec": round(d["entry"], 4) if d.get("entry") else None}
        if str(d.get("how") or "") in CERT_HOW:
            cert[i] = rec
        else:
            est[i] = rec
            rej[i] = f"ESTIMATED_ONLY: {str(d.get('how'))[:60]}"
    return cert, est, rej


def gather(sharp, liq, lanes, feed):
    items = [(sharp_id(x), x, "sharp", None) for x in sharp
             if isinstance(x, dict) and x.get("result") in ("W", "L", "P")]
    items += [(liq_id(x), x, "liquidity", None) for x in liq
              if isinstance(x, dict) and x.get("result") in ("W", "L", "P") and not x.get("artifact")
              and not x.get("close_suspect")]
    items += [(i, y, "liquidity", why) for i, y, why in lane_inputs(lanes, feed)]
    return items


def main():
    import board_build as bb
    now = datetime.now(timezone.utc)
    st = tb.dec(json.load(open(cl.STATE)))
    mkmap = (json.load(open(oa.MKFILE)) or {}).get("m") or {}
    fxs = st.get("fixtures") or {}
    alt = {fid: f for fid, (f, _s) in fxm.alt_fixtures().items()}
    allfx = dict(alt, **fxs)
    hc = len(os.listdir(oa.HC)) if os.path.isdir(oa.HC) else 0
    feed = {f"{x.get('key')}|{x.get('alerted_utc')}": x for x in bb.load()}
    try:
        lanes = json.load(open(LANES))
    except (OSError, ValueError):
        lanes = {}
    items = gather(oa.load(oa.SHARP), oa.load(oa.LIQ), lanes, feed)
    cert, est, rej = certify(items, lambda x, s: oa.classify(x, s, fxs, alt, allfx, mkmap))
    os.makedirs("paper", exist_ok=True)
    json.dump({"generated": cl.iso(now), "basis": cb.BASIS_VERSION,
               "method": "clv_obs_audit.classify (cache-only); certified = own line or exact moneyline; unique ids",
               "certified": cert, "estimated": est, "rejected": rej}, open(OUT, "w"), indent=1, sort_keys=True)
    for p in ("sharp", "liq", "lane:pull_fade", "lane:solo", "lane:ml_stay"):
        n = sum(1 for i, *_ in items if i.startswith(p + "|"))
        c = sum(1 for i in cert if i.startswith(p + "|"))
        e = sum(1 for i in est if i.startswith(p + "|"))
        t = sum(1 for i, r in cert.items() if i.startswith(p + "|") and r.get("src") == "theoddsapi")
        print(f"{p}: graded {n} | certified {c} (OddsPapi {c - t}, The Odds API {t}) | estimated {e}")
    print(f"hcache files {hc} | fixtures {len(allfx)}")
    print("rejections by class:", dict(collections.Counter(v.split(":")[0] for v in rej.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

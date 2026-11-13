#!/usr/bin/env python3
"""LIVE BOT PLAYS for the Last 50 page, by lane (Peter, Nov 13). READ-ONLY.

Decrypts tracker/state.enc, keeps source == "bot" rows (same grouping as bot_record.py), splits them by
lane (PHASE 1 = Lane 1, BOARD V3, R1, LANE 2) and writes tracker/bot_live.enc, encrypted with the same
TRACKER_PASSPHRASE scheme as state.enc. The plaintext never reaches the repo or the log.

NO DOLLARS: units are profit / stake per play (flat 1u risked, the same convention as the last-50 report),
plus the logged price, result and scoreboard. Stakes and balances are not exported.
The log prints counts only.
"""
import copy
import json
import sys
from datetime import datetime, timezone

import tracker_build as tb

# Trigger attribution as ruled by Peter and carried in the recap ledger (VALUE LAB email, Nov 13):
# (ET game date, word in team A, word in team B). Matching is by game, never by tracker row number.
TRIGGERS = {
 "Lane 1": [("10-31","notre","navy"),("10-31","portland","utah"),("10-31","sacramento","memphis"),
  ("11-01","england","miami"),("11-01","oklahoma","dallas"),("11-01","charlotte","detroit"),("11-01","charlotte","washington"),
  ("11-01","philadelphia","charlotte"),("11-01","toronto","lakers"),("11-01","boston","orlando"),("11-01","indianapolis","jacksonville"),
  ("11-01","clippers","golden"),("11-02","brooklyn","york"),("11-02","detroit","charlotte"),("11-02","sacramento","dallas"),
  ("11-02","boston","houston"),("11-02","miami","lakers"),("11-04","cleveland","oklahoma"),("11-05","orlando","phoenix"),
  ("11-05","miami","golden"),("11-06","boston","charlotte"),("11-06","utah","orleans"),("11-06","toronto","milwaukee"),
  ("11-07","denver","indiana"),("11-08","boston","milwaukee"),("11-11","lakers","milwaukee")],
 "R1": [("11-11","furman","cross"),("11-12","louisiana","monroe")],
 "Bets Board v3": [("11-04","milwaukee","boston"),("11-11","denver","memphis"),("11-11","brooklyn","orleans"),
  ("11-11","washington","indiana"),("11-12","dallas","minnesota"),("11-12","charlotte","phoenix"),("11-12","toronto","philadelphia")],
}
FIRST_MULTI_LANE_DAY = "2026-11-11"   # R1 and Board v3 were approved on Nov 11; before it only Lane 1 (PHASE 1) could place

OUT = "tracker/bot_live.enc"
LANES = {"PHASE 1": "Lane 1", "BOARD V3": "Bets Board v3", "R1": "R1", "LANE 2": "Lane 2"}


def play(b):
    st = b.get("stake") or 0
    res = b.get("result")
    units = round((b.get("profit") or 0) / st, 2) if res in ("W", "L", "P") and st else None
    t = b.get("teams") or []
    return {"game": b.get("game") or "", "bet": b.get("bet") or "", "book": b.get("book") or "",
            "price": b.get("price"), "result": res, "open": bool(b.get("open") and not res), "units": units,
            "start": b.get("game_start") or "", "settled": b.get("settled") or "",
            "seen": b.get("first_seen") or "",
            "state": b.get("g_state") or "", "detail": b.get("g_detail") or "",
            "teams": [{"n": x.get("name"), "s": x.get("score")} for x in t] if len(t) == 2 else None,
            "final": bool(b.get("teams_final"))}


def registry_lanes():
    """key -> lane name from the bot's PRIVATE GitHub registry (the source of truth; Gmail is only the backup).
    The store keeps about 4 days, so it cannot label older plays. Returns {} when unreadable."""
    out = {}
    try:
        import executor as ex
        import registry as reg
        for row in reg.rows() or []:
            if not row.get("key"):
                continue
            d = lambda x: x if isinstance(x, dict) else {}   # some rows carry False/None here
            more = row.get("live_more")
            los = ([d(row.get("live_order")), d(row.get("live_rest"))]
                   + [d(x) for x in (more if isinstance(more, list) else [])])
            if any(lo.get("status") == "placed" and lo.get("order_id") and not lo.get("intent")
                   and not lo.get("voided") for lo in los):
                safe = dict(row, live=d(row.get("live")), play=d(row.get("play")))   # lane_of() calls .get on both
                out[row["key"]] = ex.LANE_NAME.get(ex.lane_of(safe), "PHASE 1")
    except Exception as e:
        print(f"registry unreadable ({type(e).__name__}: {str(e)[:90]}); lanes fall back to the tracker own tags")
    return out


def trigger_plays(rows):
    """One play per ruled game: every tracker row for that game (any source) is merged, net profit decides W/L.
    Returns ({lane: [plays]}, used row ids, counts). Record is RECOMPUTED from the tracker, not copied."""
    from datetime import datetime, timedelta
    out, used, miss = {k: [] for k in TRIGGERS}, set(), []
    for lane, games in TRIGGERS.items():
        for md, a, b in games:
            d0 = datetime.strptime("2026-" + md, "%Y-%m-%d")
            days = {(d0 + timedelta(days=x)).strftime("%Y-%m-%d") for x in (-1, 0, 1)}
            hit = [r for r in rows if str(r.get("game_start") or r.get("settled") or r.get("first_seen") or "")[:10] in days
                   and {a, b} <= tb.toks(r.get("game") or "")]
            if not hit:
                miss.append((lane, md, a, b))
                continue
            for r in hit:
                used.add(id(r))
            st = sum(r.get("stake") or 0 for r in hit)
            pr = sum(r.get("profit") or 0 for r in hit if r.get("result"))
            settled = all(r.get("result") for r in hit)
            top = max(hit, key=lambda r: r.get("stake") or 0)
            pl = play(top)
            srcs = {(r.get("source") or "") == "bot" for r in hit}
            pl.update({"result": ("W" if pr > 0 else "L" if pr < 0 else "P") if settled else None,
                       "open": not settled, "units": round(pr / st, 2) if settled and st else None,
                       "how": "recap ledger trigger", "by": "bot" if srcs == {True} else "hand" if srcs == {False} else "mixed",
                       "rows": len(hit)})
            out[lane].append(pl)
    return out, used, miss


def main():
    st = tb.dec(json.load(open(tb.STATE)))
    raw = copy.deepcopy(st.get("bets") or {})
    tb.mark_manual_dups(raw)
    rows = tb.group_fills([b for b in raw.values() if not b.get("dup_of")])
    from collections import Counter   # counts only: which source labels the tracker really uses
    print("source labels (all rows):", dict(Counter(str(b.get("source")) for b in rows)))
    print("lane tags (all rows):", dict(Counter(str(b.get("lane")) for b in rows)))
    print("bot-only vs lane tag:", dict(Counter(str(b.get("lane")) for b in rows if b.get("source") == "bot")))
    out = {k: [] for k in LANES.values()}
    out["Unattributed"] = []
    tp, used, miss = trigger_plays(rows)
    for k, v in tp.items():
        out[k].extend(v)
    print("trigger games matched:", {k: len(v) for k, v in tp.items()}, "| unmatched:", len(miss),
          [f"{a} {b}-{c}" for a, b, c, d in [(m[0], m[1], m[2], m[3]) for m in miss]][:12])
    print("trigger record (W-L, recomputed):", {k: f"{sum(1 for p in v if p['result']=='W')}-{sum(1 for p in v if p['result']=='L')}" for k, v in tp.items()})
    print("unmapped bot rows (day | game | result):", sorted(
        (str(b.get("game_start") or b.get("settled") or b.get("first_seen") or "")[5:10], str(b.get("game")), str(b.get("result")))
        for b in rows if (b.get("source") or "") == "bot" and id(b) not in used)[:30])
    print("Toronto/Philadelphia rows:", [(b.get("source"), b.get("result"), bool(b.get("open"))) for b in rows if {"toronto", "philadelphia"} <= tb.toks(b.get("game") or "")])
    keylane = registry_lanes()
    how = {"tracker tag": 0, "registry": 0, "before R1/Board (inferred Lane 1)": 0, "none": 0}
    for b in rows:
        if (b.get("source") or "") != "bot" or id(b) in used:
            continue
        lane, src = b.get("lane"), "tracker tag"
        if not lane:
            lane = next((v for k, v in keylane.items() if tb.bot_match(b, {k})), None)
            src = "registry"
        if not lane:
            day = (b.get("game_start") or b.get("settled") or b.get("first_seen") or "")[:10]
            if day and day < FIRST_MULTI_LANE_DAY:
                lane, src = "PHASE 1", "before R1/Board (inferred Lane 1)"
        if not lane:
            src = "none"
        how[src] += 1
        pl = play(b)
        pl["how"] = src
        out[LANES.get(lane, "Unattributed")].append(pl)
    for k in out:
        out[k].sort(key=lambda p: p["start"] or p["seen"], reverse=True)
        out[k] = out[k][:80]
    doc = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "lanes": out}
    json.dump(tb.enc(doc), open(OUT, "w"))
    print("lane source:", how)
    print("exported plays per lane:", {k: len(v) for k, v in out.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())

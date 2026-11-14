#!/usr/bin/env python3
"""
SELECTION-LEVEL CLV (Stage 2, Peter, Nov 13 2026).

ONE STRATEGY SELECTION IS ONE CLV OBSERVATION, however many pieces it filled in.

The defect: Nov 12's Toronto @ Philadelphia Under 223.5 filled on ProphetX in 13 pieces. Each
piece is its own tracker row, so each is its own ledger row, so each is its own certified CLV -
13 observations of one bet, all with the same sign, inside a 150-row headline. tracker_build's
group_fills() already collapses ProphetX pieces for the PAGE, but it runs at page-build time on
a copy; the ledger seeds st["bets"] from the raw tracker dict and never sees the grouping. The
same gap swallows dup_of: tracker_build marks a manual note as a duplicate of the venue row, and
the word dup_of does not appear anywhere in clv_ledger, clv_stale or clv_readout.

IDENTITY, NOT PRICE. A selection is (league, the game's distinctive tokens, market, side, line).
That is the market and outcome the money is on - the venue's own identity for the position - not
"same book, same stake to the cent, within 90 minutes", which is what mark_manual_dups uses and
which on Nov 12 linked a note to the WRONG Novig position (mn|3ed1b8065067 -> nv|01a16b28...,
a different play than the nv|01a1cd5e... row for that selection).

NOTHING IS DELETED AND NO STORED LEDGER IS CHANGED. These are pure functions over rows that are
handed in. Every individual fill stays exactly where it is; collapsing happens at READ time, the
same way clv_ledger already excludes stale rows at read time rather than pruning them.

COLLAPSE RULE. A selection's one observation is rebuilt from the position, not averaged from the
pieces: stake and payout are summed, that gives the position's true after-fee decimal price, and
the CLV is that price against the close. Averaging the pieces' CLVs would weight a $5 remainder
the same as a $200 fill. Where stake and payout are not both present the stake-weighted mean of
the stored CLVs is used instead, and the row is marked so the fallback is visible rather than
silent.
"""
import collections

import tracker_build as tb

WEAK = tb.WEAK


def toks(s):
    return tb.toks(s or "") - WEAK


def key_of(league, game, bet):
    """The selection identity: league + game tokens + market + side + line.

    Returns None when the bet text will not parse. A row that cannot be identified is NEVER
    merged into a neighbouring group on a guess - it keeps its own row and is reported.
    """
    pb = tb.parse_bet(bet or "")
    if not pb:
        return None
    g = "+".join(sorted(toks(game)))
    if not g:
        return None
    lg = (league or "?").upper()
    if pb[0] == "total":
        return f"{lg}|{g}|total|{pb[1]}|{pb[2]:g}"
    if pb[0] == "spread":
        return f"{lg}|{g}|spread|{'+'.join(sorted(toks(pb[1]))) or '?'}|{pb[2]:+g}" + ("|NO" if pb[3] else "")
    return f"{lg}|{g}|ml|{'+'.join(sorted(toks(pb[1]))) or '?'}" + ("|NO" if pb[3] else "")


def row_key(rid, rec, tracker=None):
    """(selection key, why) for one ledger row.

    dup_of is honoured first and transitively: when the tracker says this row duplicates another,
    the TARGET's identity is used, so a manual note and the venue row it shadows land in the same
    selection even if the note's own text parses differently. A dup_of chain that does not
    resolve falls back to the row's own identity rather than being dropped.
    """
    tracker = tracker or {}
    seen = set()
    cur = rid
    while True:
        row = tracker.get(cur) or {}
        nxt = row.get("dup_of")
        if not nxt or nxt in seen or nxt not in tracker:
            break
        seen.add(cur)
        cur = nxt
    src = (tracker.get(cur) or {}) if cur != rid else (rec.get("snap") or {})
    if cur != rid:
        # A dup_of pointer is only honoured when it names the SAME GAME. mark_manual_dups links a
        # note to a venue row on book + stake-to-the-cent + 90 minutes, with no game or league
        # test, and it has mis-linked across both: mn|3ed1b8065067 (Charlotte @ Phoenix, NBA,
        # Nov 12) carries dup_of pointing at nv|01a16b28... (Ohio State @ USC, NCAAF, Oct 31).
        # Following that pointer blindly merges two unrelated selections into one observation and
        # silently moves one bet's CLV onto another's strategy. Verified here rather than trusted.
        own = (rec.get("snap") or {})
        tgt_lg, own_lg = (src.get("league") or ""), (own.get("league") or "")
        shared = toks(src.get("game")) & toks(own.get("game"))
        if tgt_lg and own_lg and tgt_lg == own_lg and shared:
            k = key_of(src.get("league"), src.get("game"), src.get("bet"))
            if k:
                return k, f"dup_of -> {cur[:28]}"
        # pointer rejected: fall through to the row's own identity, and say so
        s = own
        k = key_of(s.get("league"), s.get("game"), s.get("bet"))
        if k:
            return k, (f"dup_of -> {cur[:20]} REJECTED (target is "
                       f"{tgt_lg or '?'}/{str(src.get('game'))[:18]}, row is "
                       f"{own_lg or '?'}/{str(own.get('game'))[:18]})")
    s = rec.get("snap") or {}
    k = key_of(s.get("league"), s.get("game"), s.get("bet"))
    if k:
        return k, "own identity"
    return f"UNIDENTIFIED|{rid}", "bet text did not parse - kept as its own selection"


def collapse(rows):
    """One observation from a selection's rows.

    rows: [(id, rec)]. Returns a dict with clv, n_fills, stake, profit, basis and the inputs the
    figure was built from, or None when no row in the group carries a CLV.
    """
    scored = [(i, r) for i, r in rows if r.get("clv") is not None]
    if not scored:
        return None
    stake = sum(tb.num((r.get("snap") or {}).get("stake")) or 0 for _, r in scored)
    pay = sum(tb.num((r.get("snap") or {}).get("to_pay")) or 0 for _, r in scored)
    closes = [r.get("close_p") for _, r in scored if r.get("close_p") is not None]
    out = {"n_fills": len(scored), "ids": [i for i, _ in scored],
           "stake": round(stake, 2) if stake else None,
           "league": (scored[0][1].get("snap") or {}).get("league"),
           "source": (scored[0][1].get("snap") or {}).get("source"),
           "book": (scored[0][1].get("snap") or {}).get("book"),
           "game_start": (scored[0][1].get("snap") or {}).get("game_start"),
           "scored": max((r.get("scored") or "") for _, r in scored) or None,
           "how": sorted({r.get("how") for _, r in scored if r.get("how")}),
           "close_spread": (round(max(closes) - min(closes), 4) if len(closes) > 1 else 0.0)}
    results = {(r.get("snap") or {}).get("result") for _, r in scored}
    profits = [tb.num((r.get("snap") or {}).get("profit")) for _, r in scored]
    out["result"] = results.pop() if len(results) == 1 else None
    out["profit"] = round(sum(p for p in profits if p is not None), 2) if any(p is not None for p in profits) else None
    # The position's own price, rebuilt from the position: sum the stakes, sum the payouts.
    if stake and pay and pay > stake and closes:
        cp = sum((tb.num((r.get("snap") or {}).get("stake")) or 0) * r["close_p"]
                 for _, r in scored if r.get("close_p") is not None) / (stake or 1)
        out["clv"] = round(cp * (pay / stake) - 1, 4)
        out["basis"] = "position (summed stake and payout) vs stake-weighted close"
        return out
    # Fallback: stake-weighted mean of the stored CLVs, marked so it is never mistaken for the
    # position figure above. Equal weights only when no stake is known at all.
    w = [(tb.num((r.get("snap") or {}).get("stake")) or 0, r["clv"]) for _, r in scored]
    tot = sum(x for x, _ in w)
    if tot:
        out["clv"] = round(sum(x * c for x, c in w) / tot, 4)
        out["basis"] = "FALLBACK stake-weighted mean of fill CLVs (no summable stake/payout)"
    else:
        out["clv"] = round(sum(c for _, c in w) / len(w), 4)
        out["basis"] = "FALLBACK equal-weighted mean of fill CLVs (no stake on any fill)"
    return out


def selections(bets, tracker=None, exclude=None):
    """{selection key: collapsed observation} over a ledger's bets dict.

    exclude: ids to leave out entirely (the ledger's stale map, for instance). Rows are grouped
    by identity, then each group is collapsed to one observation.
    """
    exclude = exclude or set()
    groups = collections.defaultdict(list)
    whys = {}
    for rid, rec in bets.items():
        if rid in exclude:
            continue
        k, why = row_key(rid, rec, tracker)
        groups[k].append((rid, rec))
        # Prefer a dup_of attribution over "own identity": the venue row is usually seen first,
        # so setdefault alone would record "own identity" and hide the fact that a note was
        # folded in by dup_of rather than by matching text.
        if k not in whys or (why.startswith("dup_of") and not whys[k].startswith("dup_of")):
            whys[k] = why
    out = {}
    for k, rows in groups.items():
        c = collapse(rows)
        if c:
            c["why"] = whys.get(k)
            out[k] = c
    return out


def stats(obs):
    """Headline figures over collapsed observations. Bounded, never asserted."""
    v = [o["clv"] for o in obs if o.get("clv") is not None]
    if not v:
        return {"n": 0}
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5 if len(v) > 1 else None
    stake = sum(o["stake"] for o in obs if o.get("stake"))
    # ROI needs profit, and clv_ledger's snapshot does NOT capture it: its field list at
    # clv_ledger.py:915 is book/game/bet/flip/league/source/teams/game_start/placed/settled/
    # first_seen plus price/stake/to_pay and result - no profit. So profit sums to zero over the
    # ledger and an ROI computed from it would be a fabricated +0.00%, which is worse than a
    # blank. has_profit says whether ANY observation carried one; roi_pct stays None otherwise.
    have_profit = [o for o in obs if o.get("profit") is not None]
    profit = sum(o["profit"] for o in have_profit)
    settled = [o for o in obs if o.get("result") and o.get("stake")]
    settled_stake = sum(o["stake"] for o in settled)
    return {"n": len(v), "mean": m, "sd": sd,
            "se": (sd / len(v) ** 0.5) if sd is not None else None,
            "pos": sum(1 for x in v if x > 0),
            "pos_pct": 100.0 * sum(1 for x in v if x > 0) / len(v),
            "stake": round(stake, 2) if stake else 0.0,
            "profit": round(profit, 2) if have_profit else None,
            "has_profit": len(have_profit),
            "roi_pct": (100.0 * profit / settled_stake) if (have_profit and settled_stake) else None,
            "n_settled": len(settled),
            "fills": sum(o.get("n_fills", 1) for o in obs)}


def halves(obs, by="game_start"):
    """(first half, second half) of the observations in time order, split by count.

    Rows with no sort key go in neither half and are reported separately by the caller, because
    silently dropping them would change the denominator without saying so.
    """
    have = [o for o in obs if o.get(by)]
    have.sort(key=lambda o: o[by])
    mid = len(have) // 2
    return have[:mid], have[mid:], [o for o in obs if not o.get(by)]

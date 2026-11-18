#!/usr/bin/env python3
"""LIVE ACCOUNTING FOR THE LAST-50 REPORT (Peter, 16 Nov 2026: reporting/grading fix only). READ-ONLY.

Lane attribution comes from the BOT'S OWN ORDER ROWS in reporting/ledger.enc (registry.row_lane on each stored order),
never from the tracker's display lane. A play counts as a LIVE BOT PLAY only when a leg of that order has a CONFIRMED
fill:
  - a ledger fill record (joined by order id, client id, or the venue-id map) in state FILLED / PARTIAL, or
  - the order leg's own filled_stake > 0 (ProphetX / Polymarket US legs record it on the order).
Its result comes from the tracker, joined by EVIDENCE, strongest first:
  E1 order-id   tracker order_ref == the leg's order id (ProphetX "partner_" refs, Polymarket US)
  E2 registry   tracker lane_src == "registry-order-id" (tracker_build's exact order-id join; covers ledger lag)
  E3 bot-wallet tracker source == "bot" (the bot's own Novig sub-wallet) and the same game + market + side as the
                order (tracker_build.bot_match), or the ONLY bot-wallet row on that game + market. Novig rows carry a
                position id, not an order id, so E3 is the strongest join the tracker allows for Novig.
  E4 settlement the bot fill is confirmed on its own order row but no bot-linked tracker row exists: the game result is
                read from the same-play tracker row, and that row is listed UNRESOLVED (it counts for nobody).
Partial fills of one bet merge into ONE play (one play = game + market + side). Unfilled, voided and NO_FILL orders are
EXCLUDED and listed. A manual-looking tracker row on the same play as a bot order with NO confirmed fill is UNRESOLVED:
it counts for nobody. Nothing here guesses ownership.

Manual bets: tracker rows that are not bot-wallet and not order-linked, partial fills merged. PETER FEED (#3) = a manual
bet with a documented alert-feed origin: an alert (alerts.json, liquidity alerts or a board call) on the same game +
market + side BEFORE the bet was first seen. STREET VALUE (#5) = rows the tracker tagged "Street Value" from the private
SV notes. Everything else manual is "manual, no feed origin" and is reported but not graded as a strategy.

Certified CLV only: clv/state.enc row with how in ("own line", "moneyline") and a close, via clv_scorecard.std_clv.
Units are flat 1u at the actual fill price (stake-weighted average across a play's fills). No dollars leave this module.
"""
import json
import os
import re
from collections import defaultdict

START_UTC = "2026-11-12T05:00:00Z"          # Peter: every live bot bet from 12 Nov 2026 00:00 ET
LANES = {"rules": "LANE 1", "r1": "R1", "board": "BOARD V3", "lane2": "LANE 2"}
PREFIX = ("rule", "rules", "board", "r1", "lane2")
FEED_MAX_DAYS = 7
RES = {"W": "W", "WIN": "W", "WON": "W", "L": "L", "LOSS": "L", "LOST": "L", "P": "P", "PUSH": "P", "VOID": "P"}
WORD = re.compile(r"[a-z0-9.]+")
STOP = {"at", "vs", "the", "total", "points", "spread", "state", "st", "university"}


# ------------------------------------------------------------------ small helpers
def toks(s):
    return {w for w in WORD.findall(str(s or "").lower()) if len(w) > 1 and w not in STOP
            and not w.replace(".", "").isdigit()}


def strip_key(k):
    p = str(k or "").split("|")
    return "|".join(p[1:]) if p and p[0] in PREFIX else "|".join(p)


def norm_ref(x):
    s = str(x or "").strip()
    return s[len("partner_"):] if s.startswith("partner_") else s


def am_of(p):
    """American odds from a stored price: probability (0-1), decimal (1-~50) or American. None if unusable."""
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    if 0 < p < 1:
        return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
    if 1 < p < 50:
        return round(100 * (p - 1)) if p >= 2 else round(-100 / (p - 1))
    if abs(p) >= 100:
        return round(p)
    return None


def units(am, res):
    if res == "P":
        return 0.0
    if res == "L":
        return -1.0
    return 100 / -am if am < 0 else am / 100


def net_dec(book, dec):
    """After-fee decimal from the repo's fee model (clv_std via clv_scorecard); the raw decimal if the venue is unknown."""
    try:
        import clv_scorecard as sc
        return sc.cs.net_dec(sc.cs.canon(book), dec)
    except Exception:
        return dec


def leg_clv_pct(close_p, filled):
    """FILL-IMPLIED CLV from a certified close and the confirmed legs. (weighted_pct, legs) or (None, []).

    Its own measure - never the official clv_report basis, never averaged into the certified `clv`.

    Each leg is priced at its RAW fill price with its OWN venue's fee, then stake-weighted. Passing an
    already-netted price (a play's `am_net`) would double-charge the fee, because sc.std_clv applies
    net_dec itself. Per-leg also preserves the venue economics of a mixed-venue fill.
    """
    import clv_scorecard as sc
    if close_p is None:
        return None, []
    out, num, den = [], 0.0, 0.0
    for l in filled or []:
        c = sc.std_clv(close_p, l.get("am"), l.get("book"),
                       fee_coef=l.get("fee_coef"), maker=bool(l.get("fee_maker")))
        if c is None:
            continue
        out.append({"book": l.get("book"), "am": l.get("am"), "clv": round(c, 2),
                    "fee_coef": l.get("fee_coef"), "fee_model": l.get("fee_model")})
        wt = l.get("w") or 0.0
        num += c * wt
        den += wt
    if not out:
        return None, []
    # equal weight when no leg carries a stake, so a play is never dropped for want of a weight
    mean = (num / den) if den else (sum(x["clv"] for x in out) / len(out))
    return round(mean, 2), out


def bare_side(bet):
    """Polymarket US labels a spread by its number only ('-15.50')."""
    return bool(re.fullmatch(r"\s*[+-]\d+(?:\.\d+)?\s*", str(bet or "")))


def bet_norm(s):
    return re.sub(r"\s+", " ", re.sub(r"\(\s*[+-]?\d+\s*\)", "", str(s or "")).strip().lower())


def side_word(text):
    t = str(text or "").upper()
    if t.startswith("NOT OVER"):
        return "UNDER"
    if t.startswith("NOT UNDER"):
        return "OVER"
    return "UNDER" if "UNDER" in t else ("OVER" if "OVER" in t else None)


SEP = re.compile(r"\s+(?:@|at|vs\.?|v)\s+", re.I)


def sides(g):
    g = re.split(r":", str(g or ""), 1)[0]
    p = SEP.split(g)
    return [toks(x) for x in p] if len(p) == 2 else None


def same_game(a, b):
    """Both teams must match (either order) when both names split into two sides; else 2 shared words.
    'Brooklyn Nets @ Memphis' must not match 'Brooklyn Nets @ New Orleans'."""
    sa, sb = sides(a), sides(b)
    if sa and sb and all(sa) and all(sb):
        return bool((sa[0] & sb[0] and sa[1] & sb[1]) or (sa[0] & sb[1] and sa[1] & sb[0]))
    return len(toks(a) & toks(b)) >= 2


def _ts(x):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00").replace("+00:00", "") + "+00:00")
    except Exception:
        return None


def near(lg, t, b):
    """A tracker row can belong to an order's play only in the same league (when the row names one) and with its game
    or first sighting between 1 day before and 3 days after the decision. Stops a team that plays twice in a week
    (Virginia Tech: NCAAB Nov 13, NCAAF Nov 14) from joining the wrong game."""
    rl = str(b.get("league") or "").upper()
    if rl and lg and rl != str(lg).upper():
        return False
    t0, t1 = _ts(t), _ts(b.get("game_start") or b.get("first_seen"))
    if not t0 or not t1:
        return True
    d = (t1 - t0).total_seconds() / 86400
    return -1 <= d <= 3


def market_of_bet(bet):
    return "total" if side_word(bet) else "side"


# ------------------------------------------------------------------ ledger
def latest(L):
    out = {}
    for e in (L or {}).get("events") or []:
        k = (e.get("kind"), str(e.get("id")))
        out[k] = (out[k][0] if k in out else e.get("seen_utc"), e.get("data") or {})
    return out


def row_lane(o):
    try:
        import registry as rg
        ln = rg.row_lane(o)
        if ln:
            return ln
    except Exception:
        pass
    src = str((o or {}).get("source") or "").strip().lower()
    return {"rule": "rules"}.get(src, src) if src in PREFIX else None


def legs(o):
    out = []
    for name in ("live_order", "live_rest"):
        if isinstance(o.get(name), dict):
            out.append((name, o[name]))
    for x in o.get("live_more") or []:
        if isinstance(x, dict):
            out.append(("live_more", x))
    return out


def fill_index(cur):
    fills, vmap = {}, {}
    for (kind, rid), (_f, d) in cur.items():
        if kind == "fill":
            fills[rid] = d
            if d.get("client_id"):
                fills.setdefault(str(d["client_id"]), d)
        elif kind == "venue_id" and d.get("venue_order_id"):
            vmap[rid] = str(d["venue_order_id"])
    return fills, vmap


def leg_fill(lo, fills, vmap):
    """(confirmed, price_am, weight, how) for one order leg."""
    ids = [str(lo.get(f) or "") for f in ("order_id", "client_id")]
    ids += [vmap[i] for i in ids if i in vmap]
    for i in ids:
        f = fills.get(i) if i else None
        if f and f.get("state") in ("FILLED", "PARTIAL") and (f.get("filled_qty") or f.get("filled_stake")):
            w = float(f.get("filled_qty") or f.get("filled_stake") or 1)
            return True, am_of(f.get("avg_price")) or am_of(lo.get("avg_price")), w, f"fill {f.get('state')}"
    try:
        fs = float(lo.get("filled_stake") or 0)
    except (TypeError, ValueError):
        fs = 0.0
    if fs > 0:
        return True, am_of(lo.get("avg_price")), fs, "order leg filled_stake"
    st = next((fills[i].get("state") for i in ids if i and i in fills), None)
    return False, None, 0.0, st or str(lo.get("status") or "no fill record")


# ------------------------------------------------------------------ main accounting
def account(L, bets, clv=None, alerts=None, start=START_UTC):
    """Returns {"plays": [...], "excluded": [...], "unresolved": [...], "manual": [...]} - every row self-describing."""
    import clv_scorecard as sc
    cur = latest(L)
    fills, vmap = fill_index(cur)
    bets = bets or {}
    clv = clv or {}

    # 1. bot orders in the window, grouped into plays by lane-stripped key
    P = {}
    excluded = []
    for (kind, rid), (first, o) in sorted(cur.items(), key=lambda kv: str(kv[1][1].get("decided_utc") or kv[1][0])):
        if kind != "order":
            continue
        t = str(o.get("decided_utc") or first or "")
        if t < start:
            continue
        lane = row_lane(o)
        key = strip_key(o.get("key"))
        p = P.setdefault(key, {"key": key, "lanes": set(), "t": t, "legs": {}, "order_ids": set(), "voided": 0})
        if o.get("voided"):
            p["voided"] += 1
            p["lanes"].add(lane)
            continue
        p["lanes"].add(lane)
        # Nov 17 (Peter, O19): which price basis the board floor used on this order, so the daily report can split
        # before and after the fee correction without inferring it from a date. Absent on every pre-17-Nov row.
        if o.get("board_fee_basis") is not None:
            p["fee_basis"] = bool(o["board_fee_basis"])
        for nm, lo in legs(o):
            lid = str(lo.get("order_id") or lo.get("client_id") or f"{rid}:{nm}")
            ok, am, w, how = leg_fill(lo, fills, vmap)
            prev = p["legs"].get(lid)
            if not prev or (ok and not prev["ok"]):
                # Nov 18: carry the EXECUTION-TIME fee off the registry row. Absent on every
                # historical fill, which is what preserves their original treatment.
                p["legs"][lid] = {"ok": ok, "am": am, "w": w, "how": how, "book": lo.get("book"),
                                  "fee_coef": lo.get("fee_coef"), "fee_model": lo.get("fee_model"),
                                  "fee_maker": bool(lo.get("fee_maker"))}
            p["order_ids"].add(norm_ref(lo.get("order_id")))

    # 2. tracker rows: index for joins
    tr = [(i, b) for i, b in bets.items() if str(b.get("first_seen") or b.get("game_start") or "") >= start
          or str(b.get("game_start") or "") >= start]
    used = set()
    plays, unresolved = [], []

    def row_res(b):
        return RES.get(str(b.get("result") or "").upper())

    def fee_by_book(filled):
        """{canonical venue: (fee_coef, maker)} from the EXECUTION-TIME fee recorded on each leg.

        Only legs that actually recorded a coefficient are included, so a play with no such legs - every
        historical play - yields an empty map and grades exactly as it always did.
        """
        import clv_std as _cs
        out = {}
        for l in filled or []:
            if l.get("fee_coef") is None:
                continue
            try:
                out[_cs.canon(l.get("book"), strict=False)] = (l["fee_coef"], bool(l.get("fee_maker")))
            except Exception:
                continue
        return out

    def certified(ids, am_by_id, fees=None):
        """CERTIFICATION RULES ARE UNCHANGED (Peter, requirement 5): still a verified same-line or exact
        moneyline Pinnacle close and nothing else. Only the ECONOMICS the certified price is netted at
        can now come from the order row - the fee that applied when the bet executed, instead of the
        grader's own default hours later. `fees` empty or absent -> the venue model, as before.
        """
        import clv_std as _cs
        for i in ids:
            r = clv.get(i) or {}
            how = str(r.get("how") or "").strip().lower()
            if how in ("own line", "moneyline") and r.get("close_p") is not None:
                bk = bets[i].get("book")
                fc, mk = None, False
                if fees:
                    try:
                        fc, mk = fees.get(_cs.canon(bk, strict=False), (None, False))
                    except Exception:
                        fc, mk = None, False
                c = sc.std_clv(r.get("close_p"), am_by_id.get(i), bk, fee_coef=fc, maker=mk)
                if c is not None:
                    return c
        return None

    def close_p_of(ids):
        """The certified close probability for this play, or None. Same guard as certified(): a verified
        same-line or exact-moneyline Pinnacle close only - a line-move-adjusted close is never used here."""
        for i in ids:
            r = clv.get(i) or {}
            if str(r.get("how") or "").strip().lower() in ("own line", "moneyline") and r.get("close_p") is not None:
                return r["close_p"]
        return None

    def fill_implied(ids, filled):
        """FILL-IMPLIED CLV for this play (Peter, Nov 18). See leg_clv_pct - the math lives there so it
        is testable. Percentages only, no stakes or dollars."""
        return leg_clv_pct(close_p_of(ids), filled)

    for key, p in P.items():
        lg, game, mk, side = (key.split("|") + [None] * 4)[:4]
        lanes = {x for x in p["lanes"] if x}
        filled = [l for l in p["legs"].values() if l["ok"]]
        if not lanes:
            excluded.append({"key": key, "lane": None, "t": p["t"], "why": "order row names no lane"})
            continue
        lane_name = LANES.get(next(iter(lanes)), next(iter(lanes))) if len(lanes) == 1 else None
        # tracker rows for this play
        e1 = [(i, b) for i, b in tr if norm_ref(b.get("order_ref")) and norm_ref(b.get("order_ref")) in p["order_ids"]]
        e3 = []
        if not e1:
            cand = [(i, b) for i, b in tr if b.get("source") == "bot" and same_game(game, b.get("game")) and near(lg, p["t"], b)
                    and market_of_bet(b.get("bet")) == mk]
            exact = [(i, b) for i, b in cand if (mk == "total" and side_word(b.get("bet")) == side)
                     or (mk == "side" and toks(side) & toks(b.get("bet")))]
            e3 = exact or (cand if len(cand) == 1 else [])
        rows = e1 or e3
        ev = "E1 order-id" if e1 else ("E3 bot-wallet" if e3 else None)
        manual_same = [(i, b) for i, b in tr if b.get("source") != "bot" and (i, b) not in rows
                       and same_game(game, b.get("game")) and near(lg, p["t"], b) and market_of_bet(b.get("bet")) == mk
                       and ((mk == "total" and side_word(b.get("bet")) == side)
                            or (mk == "side" and (toks(side) & toks(b.get("bet")) or bare_side(b.get("bet")))))]
        if not filled:
            why = "; ".join(sorted({l["how"] for l in p["legs"].values()})) or ("voided intent" if p["voided"] else "no leg")
            if manual_same:
                for i, _b in manual_same:
                    used.add(i)
                unresolved.append({"key": key, "lane": lane_name, "t": p["t"], "rows": [i for i, _ in manual_same],
                                   "res": row_res(manual_same[0][1]), "am": manual_same[0][1].get("price"),
                                   "why": f"bot order with no confirmed fill ({why}); tracker credits a manual bet"})
            else:
                excluded.append({"key": key, "lane": lane_name, "t": p["t"], "why": f"no confirmed fill ({why})"})
            continue
        for i, _b in rows:
            used.add(i)
        if manual_same:
            # a non-bot row on a play the bot DID fill: it may be the bot's own fill (no order id on the row) or a separate
            # manual bet. Its game result can grade the bot play (E4); the row itself counts for nobody.
            for i, _b in manual_same:
                used.add(i)
            unresolved.append({"key": key, "lane": lane_name, "t": p["t"], "rows": [i for i, _ in manual_same],
                               "res": row_res(manual_same[0][1]), "am": manual_same[0][1].get("price"),
                               "why": "same play as a confirmed bot fill; tracker row carries no bot order id"})
            if not rows:
                rows, ev = manual_same, "E4 game settlement (row ownership unresolved)"
        if len(lanes) != 1:
            unresolved.append({"key": key, "lane": None, "t": p["t"], "rows": [i for i, _ in rows],
                               "why": f"filled under more than one lane: {sorted(map(str, lanes))}"})
            continue
        res = next((row_res(b) for _i, b in rows if row_res(b)), None)
        w = sum(l["w"] for l in filled) or 1.0
        prices = [(l["am"], l["w"]) for l in filled if l["am"] is not None]
        am = am_net = None
        if prices:
            dec = sum((1 + (100 / -a if a < 0 else a / 100)) * wt for a, wt in prices) / sum(wt for _a, wt in prices)
            am = am_of(dec)
            nets = [(net_dec(l["book"], 1 + (100 / -l["am"] if l["am"] < 0 else l["am"] / 100)), l["w"])
                    for l in filled if l["am"] is not None]
            am_net = am_of(sum(d * wt for d, wt in nets) / sum(wt for _d, wt in nets))
        if am is None and rows and ev != "E4 game settlement (row ownership unresolved)":
            am = am_net = rows[0][1].get("price")   # tracker price of the bot's own row (venue-reported, after fees)
        am_by_id = {i: (b.get("price") if b.get("price") is not None else am) for i, b in rows}
        fi_mean, fi_legs = fill_implied([i for i, _ in rows], filled)
        plays.append({"lane": lane_name, "key": key, "t": p["t"], "am": am, "am_net": am_net, "res": res, "evidence": ev,
                      "rows": [i for i, _ in rows], "fills": len(filled),
                      # Nov 17 (Peter, O19): the venues this play actually FILLED on, and the board price basis,
                      # so the report can ask whether the newly eligible venues carry their own weight.
                      "books": sorted({l["book"] for l in filled if l.get("book")}),
                      "fee_basis": p.get("fee_basis"),
                      "clv": certified([i for i, _ in rows], am_by_id, fees=fee_by_book(filled)),
                      # Nov 18 (Peter): fill-implied CLV - its own measure, kept beside the certified `clv`
                      # above and never blended into it. Percentages only.
                      "clv_fill": fi_mean,
                      "clv_fill_legs": fi_legs,
                      "status": "graded" if res else ("open" if rows else "filled, no tracker settlement")})

    # 2b. registry-order-id rows the ledger has not caught up with (E2)
    seen_keys = {p["key"] for p in plays}
    grp = defaultdict(list)
    for i, b in tr:
        if i in used or b.get("lane_src") != "registry-order-id" or b.get("lane") not in LANES:
            continue
        grp[(b.get("lane"), norm_ref(b.get("order_ref")) or i)].append((i, b))
    for (lane, _ref), rows in grp.items():
        b0 = rows[0][1]
        k = f"{b0.get('league')}|{b0.get('game')}|{market_of_bet(b0.get('bet'))}|{side_word(b0.get('bet')) or b0.get('bet')}"
        if k in seen_keys:
            continue
        for i, _b in rows:
            used.add(i)
        res = next((row_res(b) for _i, b in rows if row_res(b)), None)
        am = rows[0][1].get("price")
        plays.append({"lane": LANES[lane], "key": k, "t": str(b0.get("first_seen") or ""), "am": am, "am_net": am, "res": res,
                      "evidence": "E2 registry", "rows": [i for i, _ in rows], "fills": len(rows),
                      "clv": certified([i for i, _ in rows], {i: b.get("price") for i, b in rows}),
                      "status": "graded" if res else "open"})

    # 3. manual rows: everything else that is not bot-wallet, partial fills merged
    mgrp = defaultdict(list)
    for i, b in tr:
        if i in used or b.get("source") == "bot" or (b.get("dup_of") and not b.get("dup_rejected")):
            continue
        if str(b.get("game_start") or b.get("first_seen") or "") < start:
            continue   # a manual bet belongs to the window by its game time (notes can be logged after the game)
        ref = norm_ref(b.get("order_ref"))
        k = ("ref", ref) if ref else ("bet", b.get("book"), frozenset(toks(b.get("game"))), bet_norm(b.get("bet")))
        mgrp[k].append((i, b))
    # one bet seen twice (venue row + Peter's own note on the same venue) merges on game + bet text
    merged = {}
    for k, rows in mgrp.items():
        b0 = rows[0][1]
        mk2 = (frozenset(toks(b0.get("game"))), bet_norm(b0.get("bet")), str(b0.get("game_start") or "")[:10])
        merged.setdefault(mk2, []).extend(rows)
    manual = []
    for rows in merged.values():
        b0 = sorted(rows, key=lambda r: str(r[1].get("first_seen") or ""))[0][1]
        res = next((row_res(b) for _i, b in rows if row_res(b)), None)
        src = "Street Value" if any(b.get("source") == "Street Value" for _i, b in rows) else "manual"
        feed = feed_origin(b0, alerts or [])
        manual.append({"src": src if src == "Street Value" else ("Peter feed" if feed else "manual, no feed origin"),
                       "feed": feed, "game": b0.get("game"), "bet": b0.get("bet"), "book": b0.get("book"),
                       "t": str(b0.get("first_seen") or b0.get("game_start") or ""), "am": b0.get("price"), "res": res,
                       "rows": [i for i, _ in rows], "merged": len(rows),
                       "clv": certified([i for i, _ in rows], {i: b.get("price") for i, b in rows})})
    return {"plays": plays, "excluded": excluded, "unresolved": unresolved, "manual": manual}


def feed_origin(b, alerts):
    """The first alert on the same game + market + side before the bet was first seen, or None."""
    t = str(b.get("first_seen") or "")
    mk = market_of_bet(b.get("bet"))
    sd = side_word(b.get("bet"))
    bt = toks(b.get("bet"))
    t0 = _ts(t)
    for a in alerts:
        if str(a.get("t") or "") > t or not same_game(a.get("game"), b.get("game")):
            continue
        ta = _ts(a.get("t"))
        if t0 and ta and (t0 - ta).days > FEED_MAX_DAYS:
            continue   # same matchup weeks earlier is a different game
        if a.get("mk") != mk:
            continue
        if mk == "total" and side_word(a.get("side")) == sd:
            return a.get("src")
        if mk == "side" and side_index(b.get("game"), a.get("side")) is not None \
                and side_index(b.get("game"), a.get("side")) == side_index(b.get("game"), b.get("bet")):
            return a.get("src")
    return None


def side_index(game, text):
    """0 / 1 = which team of `game` the side text backs, or None. 'NOT <team> wins by ...' backs the other team."""
    sd = sides(game)
    if not sd or not all(sd):
        return None
    t = str(text or "").strip()
    neg = t.upper().startswith("NOT ")
    tt = toks(t[4:] if neg else t)
    hit = [i for i in (0, 1) if sd[i] & tt]
    if len(hit) != 1:
        return None
    return 1 - hit[0] if neg else hit[0]


def feed_alerts():
    """Alert-feed events from the public files: sharp alerts, liquidity alerts, board calls. Read-only."""
    out = []
    try:
        A = json.load(open("alerts.json"))
        for a in (A if isinstance(A, list) else A.get("alerts") or []):
            out.append({"t": a.get("alert_utc"), "game": a.get("game"), "src": "sharp alert",
                        "mk": "total" if a.get("kind") == "tot" else "side", "side": a.get("bet")})
    except Exception:
        pass
    for p in ("liquidity/alerts.json", "liquidity-extra/alerts.json"):
        try:
            Q = json.load(open(p))
            for a in (Q if isinstance(Q, list) else Q.get("alerts") or []):
                mk = "total" if a.get("market") == "total" else "side"
                out.append({"t": a.get("alerted_utc"), "game": a.get("game"), "src": "liquidity alert", "mk": mk,
                            "side": a.get("side_label") or a.get("side")})
        except Exception:
            pass
    try:
        for c in ((json.load(open("board/calls.json")) or {}).get("calls") or {}).values():
            out.append({"t": c.get("at"), "game": c.get("game"), "src": "board call",
                        "mk": "total" if c.get("mk") == "total" else "side", "side": c.get("side")})
    except Exception:
        pass
    return out


def load():
    """(ledger, tracker bets, clv bets) decrypted with TRACKER_PASSPHRASE, or None."""
    if not os.environ.get("TRACKER_PASSPHRASE"):
        return None
    try:
        import tracker_build as tb
        L = tb.dec(json.load(open("reporting/ledger.enc")))
        B = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
        try:
            C = (tb.dec(json.load(open("clv/state.enc"))) or {}).get("bets") or {}
        except Exception:
            C = {}
        return L, B, C
    except Exception as e:
        print(f"live ledger not readable ({type(e).__name__})")
        return None


def resting(L, start=START_UTC):
    """RESTING BIDS (#2): every resting leg (live_rest) placed in the window, with its confirmed outcome. Read-only."""
    cur = latest(L)
    fills, vmap = fill_index(cur)
    out = []
    for (kind, rid), (first, o) in cur.items():
        if kind != "order" or o.get("voided") or not isinstance(o.get("live_rest"), dict):
            continue
        t = str(o.get("decided_utc") or first or "")
        if t < start:
            continue
        ok, am, _w, how = leg_fill(o["live_rest"], fills, vmap)
        out.append({"key": strip_key(o.get("key")), "lane": LANES.get(row_lane(o), row_lane(o)), "t": t,
                    "book": o["live_rest"].get("book"), "filled": ok, "am": am, "how": how})
    # one resting play per game + market + side
    best = {}
    for r in sorted(out, key=lambda r: (not r["filled"], r["t"])):
        best.setdefault(r["key"], r)
    return list(best.values())

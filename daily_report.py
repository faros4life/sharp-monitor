#!/usr/bin/env python3
"""One-screen daily report of SETTLED bets: what we paid, what Pinnacle closed at, result, CLV.

Peter, Nov 20: "Reporting actual bets" and "researching CLV accuracy" are two jobs, and the first
must not wait for the second. So this is READ-ONLY and INDEPENDENT of the V2 backfill: it projects
what is already stored and never computes, fetches or guesses a closing price. A field we do not
hold prints as a dash with its reason. Missing V2 never hides the other columns.

No dollar figures: units only, at UNIT per unit, per the repo rule that logs carry counts and units.
No API calls, no paid credits, no writes, nothing touching a live trading path.
"""
import json
import os
import sys
from datetime import datetime, timedelta

import tracker_build as tb

STATE = "clv/state.enc"
UNIT = 200.0          # 1u, as the real-plays recap uses


def am(dec_price):
    """Decimal -> American, for display only."""
    if not dec_price or dec_price <= 1:
        return None
    return round((dec_price - 1) * 100) if dec_price >= 2 else -round(100 / (dec_price - 1))


def et_day(iso_ts):
    """The ET calendar day of an ISO timestamp, or None."""
    t = tb.tp(iso_ts) if hasattr(tb, "tp") else None
    if t is None:
        try:
            t = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
        except Exception:
            return None
    return t.astimezone(tb.ET).strftime("%Y-%m-%d")


def merge_summaries(rows):
    """Keys of rows that are a MERGED SUMMARY of sibling wagers, not wagers themselves.

    Peter's ruling, Nov 20: for a same-exchange multi-fill the ORIGINAL wagers are authoritative
    and the merged CSV row is a summary that must never be counted again. SMU +20.5 was two Hard
    Rock wagers, 210 and 105, which the CSV merges into one 315 row - counting all three reads 525
    of exposure where 315 was wagered.

    A row is a summary only when it sits on the SAME book, game and bet as two or more siblings
    AND its stake equals their sum to the cent AND it arrived by a different ingestion path
    (different source tag). All three conditions, because arithmetic alone would mis-flag a third
    genuine wager that happens to equal the other two, and under-counting exposure is as wrong as
    over-counting it. Nothing is deleted: the row is excluded from the report's totals and said so.
    """
    groups = {}
    for k, b in rows:
        groups.setdefault((b.get("book"), b.get("game"), b.get("bet")), []).append((k, b))
    out = {}
    for _g, members in groups.items():
        if len(members) < 3:
            continue
        for k, b in members:
            st = num(b.get("stake"))
            sibs = [(k2, b2) for k2, b2 in members if k2 != k and num(b2.get("stake")) is not None]
            if st is None or len(sibs) < 2:
                continue
            tot = sum(num(b2.get("stake")) for _k2, b2 in sibs)
            same_path = any((b2.get("source") or "") == (b.get("source") or "") for _k2, b2 in sibs)
            if abs(tot - st) < 0.01 and not same_path:
                out[k] = (f"MERGE SUMMARY EXCLUDED: this row's stake equals the sum of "
                          f"{len(sibs)} sibling wagers on the same book, game and bet, and it "
                          f"arrived by a different path. The original wagers are authoritative "
                          f"(Peter, Nov 20); this summary is not counted again.")
    return out


def game_day_of(b):
    """THE game day for a bet, in one place.

    Precedence: a corrections entry, then an authoritative transfer event record, then the
    tracker's own game_start. Two copies of this existed - the day filter preferred the event
    record while the cohort view still used the tracker's game_start - so Houston was admitted to
    Nov 19 and then excluded from the Nov 19 game-day total. One definition, as CLAUDE.md says.
    """
    return b.get("_gameday") or b.get("_gameday_ev") or et_day(b.get("game_start"))


def bets_on(tracker, day, corr=None):
    """Keys of tracker rows BELONGING to the given ET day, newest first, settled or not.

    Nov 20 (Peter, relayed): "report every previous-day actual bet each morning, even when the
    final close or V2 is missing." Selecting on the SETTLE date alone dropped a bet placed
    yesterday that had not settled, which is exactly a row you need to see. A row counts for the
    day if it was PLACED or SETTLED or its GAME started on it; an unsettled row is reported with
    its result blank rather than hidden.
    """
    out, seen = [], set()
    corr = corr or {}
    for k, b in (tracker or {}).items():
        c = corr.get((b.get("book"), b.get("game"), b.get("bet")))
        if c:
            b = dict(b)
            b["_gameday"] = c.get("game_day")
            b["_gameday_basis"] = c.get("game_day_basis")
        if c:
            if c.get("placed_actual"):
                b["placed"], b["placed_src"] = c["placed_actual"], "corrected: real placement time"
                b["received_at"] = c.get("received_at")
            if c.get("settled_actual") and not b.get("settled"):
                b["settled"], b["settled_src"] = c["settled_actual"], "corrected: venue settle time"
            if c.get("result") and not b.get("result"):
                b["result"], b["result_src"] = c["result"], "corrected: venue outcome"
                pf = profit_from(b, c["result"])
                if pf is not None:
                    b["profit"] = pf
                b["score"] = c.get("score")
        # GAME_START is informational and is NEVER an identity for the placement date
        # (ChatGPT/Peter, Nov 20). Day membership rests on an authenticated placed or settled
        # timestamp only; game_start no longer admits a row to a day.
        days = {et_day(b.get(f)) for f in ("settled", "placed") if b.get(f)}
        # An event-record date, backed by an immutable event id, outranks the tracker's own
        # game_start. The disagreement is reported, never hidden.
        gd = game_day_of(b)
        if day not in days and gd != day:
            continue
        fp = (b.get("book"), b.get("game"), b.get("bet"), b.get("placed"), b.get("stake"))
        if fp in seen:
            continue            # the same fill reaching us twice is one bet, not two
        seen.add(fp)
        out.append((k, b))
    out.sort(key=lambda kb: str(kb[1].get("settled") or kb[1].get("placed") or ""), reverse=True)
    return out


def corrections(day, directory="corrections"):
    """REPORTING-LAYER corrections for a day, from corrections/<day>.json. Approved by Peter Nov 20.

    Nothing here touches tracker_build, MANUAL_HELD, the three-day window, duplicate protection or
    any execution or risk path - the correction is applied when the report is rendered and nowhere
    else. Nor does the file carry money: it holds only public facts (the real placement time, the
    email receipt time kept separately, the win/loss and the final score). Units are computed from
    the stake and price the tracker already stores, so no stake or dollar figure enters this repo.

    Why it is needed: tracker_build takes `placed` from the note's email receipt, so the four Hard
    Rock bets re-sent on Nov 20 were stamped Nov 20 although they were placed Nov 19.
    """
    import os
    f = os.path.join(directory, f"{day}.json")
    if not os.path.exists(f):
        return {}
    try:
        d = json.load(open(f))
    except Exception:
        return {}
    out, meta = {}, {}
    for r in (d if isinstance(d, list) else [d]):
        if not isinstance(r, dict):
            continue
        if r.get("_meta"):
            meta = r
        elif r.get("bet"):
            out[(r.get("book"), r.get("game"), r.get("bet"))] = r
    out["_meta"] = meta
    return out


def event_days(day, directory="events"):
    """{(book, bet-prefix): (game_date_et, event_id)} from Muse's private transfer.

    This is an AUTHORITATIVE game date with the venue's own start time and, where present, an
    immutable event id - so a row backed by it is no longer PROVISIONAL. Nothing is inferred from
    the settlement.
    """
    import os
    f = os.path.join(directory, f"{day}.json")
    if not os.path.exists(f):
        return {}
    try:
        d = json.load(open(f))
    except Exception:
        return {}
    out = {}
    out["_by_game"] = {}
    for r in (d if isinstance(d, list) else [d]):
        if not isinstance(r, dict) or not r.get("game_date_et"):
            continue
        val = (r["game_date_et"], r.get("odds_api_event_id"), r.get("game_start_et"))
        if r.get("bet"):
            out[(r.get("book"), str(r.get("bet"))[:24])] = val
        if r.get("game"):
            # A metadata-only entry supplies a game date for a bet ALREADY in the tracker. It is
            # never turned into a bet of its own.
            out["_by_game"][r["game"]] = val
    return out


def profit_from(b, result):
    """Signed profit implied by the tracker's OWN stake and payout plus a win/loss verdict.

    The verdict is a public fact; the money comes from records already held. Nothing is invented:
    if the row lacks a stake, or a payout on a win, this returns None and the report says so.
    """
    st, tp_ = num(b.get("stake")), num(b.get("to_pay"))
    r = str(result or "").upper()[:1]
    if st is None:
        return None
    if r == "L":
        return -st
    if r == "W":
        return None if tp_ is None else round(tp_ - st, 2)
    if r == "P":
        return 0.0
    return None


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def manual_file(day, directory="manual"):
    """Bets Peter entered elsewhere (Muse) that the tracker has no row for, from manual/<day>.json.

    REPORTING ONLY. These rows never reach tracker_build, so they cannot touch the executor's
    MANUAL_HELD gating or any live path - that wiring needs Peter's explicit yes and is not done
    here. Their purpose is that a hand-placed bet still appears in the morning report with its
    result and price instead of vanishing.
    """
    import os
    f = os.path.join(directory, f"{day}.json")
    if not os.path.exists(f):
        return []
    try:
        d = json.load(open(f))
    except Exception:
        return []
    return [r for r in (d if isinstance(d, list) else [d]) if isinstance(r, dict)]


def units(b):
    """Signed units from the venue's own settlement, or None if it carries no figure."""
    p = b.get("profit")
    if p is None:
        return None
    try:
        return round(float(p) / UNIT, 2)
    except Exception:
        return None


def why_missing(rec):
    """Why a row has no V1 CLV - the ledger's own recorded reason, never a guess."""
    if rec is None:
        return "not in the CLV ledger"
    if rec.get("clv") is not None:
        return None
    if rec.get("fixture_doubt"):
        return "held out: game assignment doubtful"
    return rec.get("why") or ("awaiting a close" if not rec.get("done") else "not scored")


def row_view(k, b, rec):
    """Everything the report shows for one settled bet. Absent means absent: no substitution."""
    rec = rec or {}
    v = {"key": k, "game": b.get("game"), "bet": b.get("bet"), "league": b.get("league"),
         "book": b.get("book"), "lane": b.get("source"), "result": b.get("result"),
         "units": units(b), "paid": b.get("price_af") if b.get("price_af") is not None else b.get("price"),
         "our_line": rec.get("our_line"), "main_line": rec.get("main_line"),
         "close_at_our_line": None, "close_main": None,
         "v1": rec.get("clv"), "v2": rec.get("clv_v2"),
         "v1_missing": why_missing(rec if rec else None),
         "v2_missing": None, "how": rec.get("how"), "age_min": rec.get("age_min")}
    alt, mn = rec.get("alt_px"), rec.get("main_px")
    if alt and len(alt) == 2:
        v["close_at_our_line"] = am(alt[0])
    elif rec.get("close_p") is not None and rec.get("how") == "own line":
        v["close_at_our_line"] = "fair stored, raw quote not kept for this row"
    if mn and len(mn) == 2:
        v["close_main"] = am(mn[0])
    # Nov 20 (Peter): resolve the half-point main-line difference WITHOUT changing CLV. The ledger
    # picks the candidate with the BIGGEST LIMIT as the main line; another source may pick the one
    # an API labels main, or the most even price. Printing which rule produced our number is the
    # diagnostic; no score is touched by it.
    v["main_rule"] = "biggest Pinnacle limit" if v["main_line"] is not None else None
    v["src"] = ("certified Pinnacle close" if v["v1"] is not None else
                "MANUAL FILE (not in the tracker)" if rec.get("_manual") else "unavailable")
    if v["v2"] is None:
        v["v2_missing"] = (rec.get("v2_unsupported") or
                           ("V2 == V1 (our number was the main line)" if rec.get("at_main")
                            else "not yet recomputed" if rec.get("clv") is not None
                            else "no V1 close to derive from"))
    return v


def pct(x):
    return "-" if x is None else f"{x * 100:+.2f}%"


L_SUMMARY = []


def render(day, views, meta=None):
    L = [f"SETTLED BETS - {day} (ET). Units at 1u = {UNIT:.0f}; no dollar figures by design.",
         "Read-only projection of stored records. A dash is a field we do not hold, with its reason.",
         ""]
    if not views:
        L.append("No bets recorded for that ET day.")
        return L
    # Nov 20 (Peter): "an older bet settling yesterday shouldn't read as yesterday's action."
    # The day's RESULT is only what SETTLED that day - that is when the money moved. Bets PLACED
    # that day which settle later are listed too, per the requirement to report every bet, but
    # they are counted separately and never folded into the day's units. Earlier today this
    # report totalled both together, so a bet placed Nov 16 and settled Nov 19 was counted in
    # Nov 16's units. That was wrong and is what this split fixes.
    # Two cohorts, never mixed (Peter, Nov 20): what SETTLED this day carries the day's P&L;
    # what was PLACED this day is the day's action. A bet in both cohorts is counted once, in
    # settlements, and appears in the placed list marked so.
    def tot(rs):
        u = sum(v["units"] or 0 for v in rs)
        w = sum(1 for v in rs if str(v["result"]).upper().startswith("W"))
        l = sum(1 for v in rs if str(v["result"]).upper().startswith("L"))
        return len(rs), w, l, u

    gameday = [v for v in views if v.get("game_day") == day]
    excl = (meta or {}).get("subset_exclude") or []
    def is_excluded(v):
        return any(all(str(v["ident"][i] or "").startswith(str(e.get(k) or ""))
                       for i, k in ((0, "book"), (1, "bet")) if e.get(k)) for e in excl)
    subset = [v for v in gameday if not is_excluded(v)]
    dropped = [v for v in gameday if is_excluded(v)]
    sett = [v for v in views if v.get("on_day") == "settled"]
    # (C) is every bet with a verified placement timestamp on this day, INCLUDING ones that also
    # settled today. Membership is independent per cohort (Peter: "include pending"); only the
    # TOTALS are kept separate, which is what prevents double counting.
    other = [v for v in views if v.get("placed_day") == day]
    unver = [v for v in views if v.get("on_day") == "UNVERIFIED date"]
    n, w_, l_, u_ = tot(gameday)
    L.append(f"(A) GAME-DAY PERFORMANCE - all venues, games played this day: {n} | {w_}-{l_} | {u_:+.2f}u")
    prov = [v for v in gameday if str(v.get("game_day_basis") or "").startswith("PROVISIONAL")]
    conf = [v for v in gameday if v.get("gameday_conflict")]
    if conf:
        L.append(f"    {len(conf)} row(s) had a game-date disagreement between the tracker and the "
                 f"verified event record - each is printed in full on its row")
    L.append(f"    game-day verification: {n - len(prov)}/{n} authoritative, {len(prov)} PROVISIONAL"
             + (" (no immutable event id yet - see the note at the end)" if prov else ""))
    if excl:
        ns, ws, ls, us = tot(subset)
        L.append(f"(B) {(meta or {}).get('subset_label') or 'subset'}: {ns} | {ws}-{ls} | {us:+.2f}u")
        for v in dropped:
            L.append(f"    OTHER SETTLED BET - in (A), not in the (B) subset: {v['bet']} | {v['book']}"
                     f" | game day {v.get('game_day') or 'unknown'} | {('%+.2fu' % v['units']) if v['units'] is not None else '-'}"
                     f" | reason: {(meta or {}).get('why', 'excluded from the discussed card')[:90]}")
    nc, wc, lc, uc = tot(other)
    nd, wd, ld, ud = tot(sett)
    L.append(f"(C) PLACED THIS DAY (verified placement timestamp, pending included): {nc}"
             + (f" | {wc}-{lc} | {uc:+.2f}u of which settled" if nc else ""))
    L.append(f"(D) SETTLED THIS DAY: {nd} | {wd}-{ld} | {ud:+.2f}u")
    L.append("    (A) and (D) answer different questions and are never the same card. A bet counts "
             "once inside each total; totals are not added together.")
    if other:
        L.append(f"PLACED THIS DAY, settling later or still open: {len(other)}"
                 f" - NOT counted in the units above")
    if unver:
        L.append(f"!! {len(unver)} row(s) carry NO authenticated placement timestamp - shown as "
                 f"UNVERIFIED date, never inferred from the event or the settlement")
    nou = [v for v in views if v.get("units_missing")]
    if nou:
        L.append(f"!! {len(nou)} settled row(s) have no units: {nou[0]['units_missing']}")
    scored = [v for v in views if v["v1"] is not None]
    cert = [v for v in views if (v.get("snap") or {}).get("certified")]
    prov = [v for v in views if (v.get("snap") or {}).get("clv") is not None
            and not (v.get("snap") or {}).get("certified")]
    # Same-line coverage is V1's own certified closes PLUS same-line snapshots. Counting only the
    # snapshots read 3/7 and hid the three rows that already carry a certified ledger close.
    v1_cert = [v for v in gameday if v["v1"] is not None]
    snap_cert = [v for v in gameday if (v.get("snap") or {}).get("certified")]
    snap_prov = [v for v in gameday if (v.get("snap") or {}).get("clv") is not None
                 and not (v.get("snap") or {}).get("certified")]
    unavail = [v for v in gameday if v["v1"] is None and (v.get("snap") or {}).get("clv") is None]
    for _m in L_SUMMARY:
        L.append(f"!! {_m}")
    L.append(f"CLV SAME-LINE COVERAGE: {len(v1_cert) + len(snap_cert)}/{len(gameday)}"
             f" = {len(v1_cert)} certified V1 ledger close + {len(snap_cert)} same-line snapshot"
             f" | provisional converted {len(snap_prov)}"
             f" | UNAVAILABLE {len(unavail)} (never counted as zero)")
    L.append(f"V1 CLV on {len(scored)}/{len(views)}"
             + (f", mean {sum(v['v1'] for v in scored) / len(scored) * 100:+.2f}%" if scored else "")
             + f" | V2 on {sum(1 for v in views if v['v2'] is not None)}/{len(views)}")
    L.append("")
    for v in views:
        L.append(f"{v['bet']} | {v['league']} {v['book']} [{v['lane']}] | {v['game']}"
                 + f"   <{v.get('on_day') or 'on this day'}>")
        L.append(f"    result {v['result']} {('%+.2fu' % v['units']) if v['units'] is not None else '(no settled figure)'}"
                 f" | paid {v['paid'] if v['paid'] is not None else '-'}"
                 f" | our line {v['our_line'] if v['our_line'] is not None else '-'}")
        if v.get("snap"):
            sn = v["snap"]
            L.append(f"    SNAPSHOT ({sn['label']}): line {sn['line']} @ our side {sn['price_our']} /"
                     f" other {sn['price_other']}, captured T-{sn['t_minus']} min"
                     + (f" | movement {sn['movement']:+g} pts our way" if sn.get("movement") is not None else "")
                     + (f" | PROVISIONAL CLV {pct(sn['clv'])}" if sn.get("clv") is not None
                        else f" | no provisional CLV ({sn['why']})"))
        if v.get("placed_src") or v.get("result_src"):
            L.append("    REPORTING CORRECTION: "
                     + "; ".join(x for x in (v.get("placed_src"), v.get("settled_src"),
                                                 v.get("result_src")) if x)
                     + (f" | email receipt kept separately: {v['received_at']}" if v.get("received_at") else "")
                     + (f" | final {v['score']}" if v.get("score") else "")
                     + " | tracker_build, MANUAL_HELD and live gating untouched")
        if v.get("gameday_conflict"):
            L.append(f"    !! {v['gameday_conflict']}")
        if v.get("placed_day") or v.get("settled_day") or v.get("game_day"):
            L.append(f"    dates ET: placed {v.get('placed_day') or '-'} | settled "
                     f"{v.get('settled_day') or '-'} | game {v.get('game_day') or '-'}"
                     + ("   !! GAME AFTER SETTLEMENT - one of these timestamps is wrong"
                        if (v.get("game_day") and v.get("settled_day")
                            and v["game_day"] > v["settled_day"]) else ""))
        L.append(f"    source: {v.get('src')}"
                 + (f" | main line chosen by {v['main_rule']}" if v.get("main_rule") else ""))
        L.append(f"    Pinnacle close: main line {v['main_line'] if v['main_line'] is not None else '-'}"
                 f" @ {v['close_main'] if v['close_main'] is not None else '-'}"
                 f" | at our line {v['close_at_our_line'] if v['close_at_our_line'] is not None else '-'}"
                 + (f" | read '{v['how']}'" if v["how"] else "")
                 + (f", tick {v['age_min']} min pre-start" if v["age_min"] is not None else ""))
        L.append(f"    V1 CLV {pct(v['v1'])}" + (f" ({v['v1_missing']})" if v["v1"] is None else "")
                 + f" | V2 CLV {pct(v['v2'])}" + (f" ({v['v2_missing']})" if v["v2"] is None else ""))
    return L


def main(argv):
    day = argv[1] if len(argv) > 1 else (datetime.now(tb.ET) - timedelta(days=1)).strftime("%Y-%m-%d")
    if not tb.PASS:
        print("daily report: TRACKER_PASSPHRASE not set; cannot read the encrypted records")
        return 1
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        print(f"daily report: tracker state unreadable ({type(e).__name__})")
        return 1
    try:
        bets = (tb.dec(json.load(open(STATE))) or {}).get("bets") or {}
    except Exception:
        bets = {}
        print("daily report: CLV ledger state unreadable - bet and settlement columns only")
    corr = corrections(day)
    ev = event_days(day)
    # An authoritative game date from the private transfer OUTRANKS the provisional one in the
    # corrections file, and clears the PROVISIONAL label.
    for key, rec_c in list(corr.items()):
        if key == "_meta" or not isinstance(rec_c, dict):
            continue
        hit = ev.get((rec_c.get("book"), str(rec_c.get("bet"))[:24]))
        if hit:
            rec_c["game_day"] = hit[0]
            rec_c["game_day_basis"] = (f"authoritative: Muse private transfer, start {hit[2]}"
                                       + (f", event id {hit[1]}" if hit[1] else ", no event id"))
    # Authoritative game dates for tracker rows that carry none, matched on the game name from
    # the transfer. Two shared tokens, the same bar the snapshot matcher uses.
    import tracker_build as _tb
    by_game = ev.get("_by_game") or {}
    for _k, _b in (tracker or {}).items():
        if not _b.get("game"):
            continue
        for g, val in by_game.items():
            # Two shared tokens was far too loose: it tied Houston's event record to bets from
            # Nov 15, Nov 1 and Oct 31. Game names must be near-identical, so this requires
            # Jaccard similarity >= 0.6 on the token sets - "Indianapolis Colts at Houston Texans"
            # against "Indianapolis Colts @ Houston Texans" scores 1.0, an unrelated game scores
            # far below - and at least two shared tokens as a floor.
            ta, tbk = _tb.toks(g), _tb.toks(_b.get("game"))
            inter = ta & tbk
            if len(inter) < 2 or not ta or not tbk:
                continue
            if len(inter) / len(ta | tbk) < 0.6:
                continue
            own = et_day(_b.get("game_start")) if _b.get("game_start") else None
            _b["_gameday_ev"] = val[0]
            _b["_gameday_basis_ev"] = (f"authoritative: transfer event record, start {val[2]}"
                                       + (f", event id {val[1]}" if val[1] else ""))
            # Peter, Nov 20: do NOT blindly overwrite the tracker's date. Where the two disagree,
            # the report SHOWS both, with the tracker's raw timestamp so the cause is visible, and
            # states which one it used. Where they agree, nothing is said.
            if own and own != val[0]:
                _b["_gameday_conflict"] = (
                    f"GAME DATE DISAGREEMENT: tracker {own} (from game_start "
                    f"{_b.get('game_start')}) vs transfer {val[0]} (start {val[2]}"
                    + (f", event id {val[1]}" if val[1] else "") + "). Using the verified event "
                    "record; the tracker row is left untouched.")
            break
    rows = bets_on(tracker, day, corr)
    have = {(b.get("book"), b.get("game"), b.get("bet")) for _, b in rows}
    for r in manual_file(day):
        if (r.get("book"), r.get("game"), r.get("bet")) not in have:
            rows.append((r.get("id") or f"manual|{r.get('bet')}", dict(r, _manual=True)))
    summaries = merge_summaries(rows)
    views = []
    for k, b in rows:
        if k in summaries:
            L_SUMMARY.append(summaries[k] + f" | {b.get('book')} {b.get('bet')}")
            continue
        rec = dict(bets.get(k) or {})
        if b.get("_manual"):
            rec["_manual"] = True
        vw = row_view(k, b, rec)
        # WHY this bet is on this day - so a row can never be silently counted on two days.
        # UNVERIFIED means we hold NO authenticated placement or settlement timestamp at all -
        # not merely that neither falls on this day. A bet present only by its game date is
        # labelled as such, which is accurate and was previously mislabelled UNVERIFIED.
        vw["on_day"] = ("settled" if et_day(b.get("settled")) == day
                        else "placed this day" if et_day(b.get("placed")) == day
                        else "game this day" if (b.get("placed") or b.get("settled"))
                        else "UNVERIFIED date")
        vw["placed_src"] = b.get("placed_src")
        vw["settled_src"] = b.get("settled_src")
        vw["result_src"] = b.get("result_src")
        vw["received_at"] = b.get("received_at")
        vw["score"] = b.get("score")
        vw["game_day"] = game_day_of(b)
        vw["game_day_basis"] = b.get("_gameday_basis") or b.get("_gameday_basis_ev") or (
            "authoritative game_start" if b.get("game_start") else None)
        vw["ident"] = (b.get("book"), b.get("bet"))
        vw["gameday_conflict"] = b.get("_gameday_conflict")
        vw["tracker_game_start"] = b.get("game_start")
        vw["placed_day"] = et_day(b.get("placed")) if b.get("placed") else None
        vw["settled_day"] = et_day(b.get("settled")) if b.get("settled") else None
        if b.get("result") and vw["units"] is None:
            vw["units_missing"] = "no stake or payout stored, so units cannot be computed"
        views.append(vw)
    # SECOND-PRIORITY evidence, only where the certified close is absent.
    # A silent except here would be the worst failure available: the report would look complete
    # while every snapshot was quietly dropped. It says so instead.
    ss, snaps = None, []
    try:
        import snapshot_source as ss
        snaps, _bad = ss.load()
        if _bad:
            print(f"daily report: {_bad} snapshot file(s) unreadable and skipped", flush=True)
    except Exception as e:
        print(f"daily report: snapshot source UNAVAILABLE ({type(e).__name__}: {e}) - "
              f"certified rows only, no provisional CLV this run", flush=True)
    for v, (k, b) in zip(views, rows):
        if v["v1"] is not None or not snaps or ss is None:
            continue
        for sn in sorted(snaps, key=ss.rank):      # our own line first, then freshest
            try:
                if not ss.matches(sn, b, day):
                    continue
                clv, why = ss.provisional_clv(sn, b)
            except Exception:
                continue
            v["snap"] = {"label": ss.label_for(sn), "line": sn.get("line"),
                         "price_our": sn.get("price_our", "-"), "price_other": sn.get("price_other", "-"),
                         "t_minus": sn.get("t_minus_min", "?"), "movement": ss.movement(sn, b),
                         "clv": clv, "why": why}
            if clv is not None:
                v["snap"]["certified"] = str(why or "").startswith("SAME-LINE")
                v["src"] = ("verified snapshot, SAME-LINE (no model conversion)"
                            if v["snap"]["certified"] else
                            "verified snapshot, PROVISIONAL converted")
            break
    body = "\n".join(render(day, views, corr.get("_meta")))
    print(body, flush=True)
    if os.environ.get("REPORT_EMAIL") == "1":
        try:
            import executor as ex
            import smtplib
            from email.mime.text import MIMEText
            user, pw, to = ex.gmail()
            m = MIMEText(body, "plain", "utf-8")
            m["Subject"] = f"Bets DAILY REPORT {day}"
            m["From"], m["To"] = user, to
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as sv:
                sv.login(user, pw)
                sv.sendmail(user, [to], m.as_string())
            print("daily report: emailed", flush=True)
        except Exception as e:
            print(f"daily report: email FAILED ({type(e).__name__}) - the report above still stands",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""
CLV RECOVERY AUDIT (Peter, Nov 13 2026). READ-ONLY.

Two parts in one pass over the same loaded state, so nothing is scanned twice:

  PART A - DAY AUDIT (AUDIT_DATE, default 2026-11-12). Every actual selection on that date with
           all of its tracker / registry / journal / manual records linked, each order's status,
           its economics, Pinnacle availability, the reason it lacks certified CLV, the release
           reflag mechanism, the whole unscored population by reason, and a reconciliation of the
           day's recap against the underlying orders without double-counting partial fills.

  PART B - HISTORICAL RECOVERY INVENTORY (all dates). Every unscored, held-out, retired and
           duplicate record, each classified RECOVERABLE NOW or BLOCKED-BY-<specific thing>
           using only data already on disk, plus before/after coverage by date, source and lane.

WHAT THIS FILE MAY NOT DO, and does not:
  * NO OddsPapi call of any kind, billable or free. Pinnacle history is read from the hcache
    files already on disk; a game with no cached file is reported as NO CACHED HISTORY, never
    fetched and never modelled. clv_ledger.load_markets() is deliberately NOT called because it
    can bill - clv/markets.json is read directly instead.
  * NO IMAP. Peter, Nov 13: "no emails reads". bot_novig_orders() is never called, so the bot's
    Gmail fill ledger is out of scope and is reported as a GAP rather than guessed around.
  * NO WRITE to any production state: not clv/state.enc, not tracker/state.enc, not the
    registry, not clv/markets.json. Nothing is released, cleared, rescored, retired or repaired.
    The only file produced is the checkpoint below, which no production job reads.
  * NO GUESSED FIXTURE, NO ASSUMED FILL, NO MODELLED CLOSE. Peter, explicitly: "Unknown must
    remain unknown." Every cell that cannot be established from stored data prints UNKNOWN with
    the reason. A half-point conversion ("main 228.5 moved to 229.5") is NOT a verified close:
    it has its own bucket and is never counted as recoverable coverage.

PROJECTED CLV. Part B prints what the recoverable rows WOULD score. Those figures are computed
in memory from cached Pinnacle ticks at the bet's own line and are labelled PROJECTED. They are
not written anywhere and they do not touch a stored CLV. No historical result is rewritten.

CHECKPOINT (Peter: "save checkpoints so work is incremental"). CKPT_PATH holds the verdict for
every record keyed by a fingerprint of the inputs that decide it. A record whose fingerprint is
unchanged reuses its stored verdict instead of re-opening its history file, so a second run
touches only records that actually moved. Delete the file to force a full re-classification.

MONEY RULE (CLAUDE.md): the log prints counts, American odds, results and reasons. Dollar
amounts go to the private email only - say(..., money=True) never reaches stdout.
"""
import collections
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_stale as cstale
import tracker_build as tb

ET = tb.ET
DATE = (os.environ.get("AUDIT_DATE") or "2026-11-12").strip()
HC = os.environ.get("HCACHE_DIR", "") or "hcache"
CKPT_PATH = os.environ.get("CKPT_PATH") or "audit/recovery_ckpt.json"
OUT_PATH = os.environ.get("OUT_PATH") or "audit/recovery_inventory.json"
# The only two files this script writes. Both are audit artefacts no production job reads. The
# paths are env-overridable for local runs, so the guard below makes it impossible for an
# override - or a typo in a workflow - to land a write inside the encrypted state directories.
for _p in (CKPT_PATH, OUT_PATH):
    if not os.path.normpath(_p).startswith("audit" + os.sep):
        raise SystemExit(f"refusing to write outside audit/: {_p}")
MKFILE = "clv/markets.json"
EVIDENCE = "novig_recon_evidence.json"

L, SCREEN = [], []
_PIN = {}          # fid -> cached history or None, opened at most once per run
# Bump CLASSIFIER_VERSION whenever classify(), pin_lines() or cached_pin() changes what a
# verdict MEANS. It is part of every row's fingerprint, so a code change invalidates the whole
# checkpoint automatically. This is not optional bookkeeping: the first checkpointed run after
# the cached_pin envelope fix reported "reused 382 verdict(s), recomputed 0" and silently
# re-served every verdict the buggy reader had produced. A checkpoint that cannot tell that the
# classifier moved is worse than no checkpoint, because it looks like a confirmation.
CLASSIFIER_VERSION = 2
CK = {"v": 4, "rows": {}}
CK_HIT = [0, 0]    # [reused, recomputed]


def say(t="", money=False):
    L.append(t)
    if not money:
        SCREEN.append(t)
        print(t, flush=True)


def iso_day(s):
    d = cl.tp(s)
    return d.astimezone(ET).strftime("%Y-%m-%d") if d else None


def toks(s):
    return tb.toks(s or "") - tb.WEAK


def sel_key(league, game, bet):
    """One selection: league + the game's distinctive tokens + market + side + line.

    This is the identity a repair would key on, so it is computed and reported here rather than
    asserted later. Records collapse only when all parts agree; anything that will not parse
    keeps its own raw key and shows as UNPARSED rather than being merged on a guess - merging on
    a guess is how one selection became several in the first place.
    """
    pb = tb.parse_bet(bet or "")
    g = "+".join(sorted(toks(game))) or "?"
    lg = (league or "?").upper()
    if not pb:
        return f"{lg}|{g}|UNPARSED|{(bet or '').strip()[:28]}"
    if pb[0] == "total":
        return f"{lg}|{g}|total|{pb[1]}|{pb[2]:g}"
    if pb[0] == "spread":
        return f"{lg}|{g}|spread|{'+'.join(sorted(toks(pb[1]))) or '?'}|{pb[2]:+g}" + ("|NO" if pb[3] else "")
    return f"{lg}|{g}|ml|{'+'.join(sorted(toks(pb[1]))) or '?'}" + ("|NO" if pb[3] else "")


def reg_sel_key(k):
    parts = [p for p in str(k or "").split("|") if p]
    if parts and parts[0] in ("rule", "board", "r1", "lane2"):
        parts = parts[1:]
    if len(parts) < 4:
        return None, parts
    return f"{parts[0].upper()}|{'+'.join(sorted(toks(parts[1]))) or '?'}|{parts[2]}|{parts[3]}", parts


# --------------------------------------------------------------- Pinnacle, cache only
def cached_pin(fid):
    """Cached Pinnacle history for a fixture, or None. NEVER fetches. Memoised per run."""
    if fid in _PIN:
        return _PIN[fid]
    p = os.path.join(HC, f"{fid}__pinnacle.json.gz")
    d = None
    if os.path.exists(p):
        try:
            with gzip.open(p, "rt") as fh:
                d = json.load(fh)
        except Exception:
            d = None
    # hist_cache writes the BOOK payload directly ({"markets": {...}}, hist_cache.py:172-173),
    # NOT a {"bookmakers": {...}} envelope - get_hist builds that envelope when it hands the file
    # to a caller. clv_ledger.book_markets() expects the envelope, so the file is wrapped here.
    # The first version of this function passed the bare file and every row came back "no Pinnacle
    # markets", including 13 rows the ledger had already scored "own line" - the scored rows
    # disproved the reader, not the data.
    _PIN[fid] = {"bookmakers": {"pinnacle": d}} if d is not None else None
    return _PIN[fid]


def pin_lines(fid, s, f, mkmap):
    """(verdict, detail, p_at_own_line|None) from cached ticks only.

    Verdicts: EXACT (bet's own number hung - certifiable), EQUIVALENT (moneyline, no line to
    match - certifiable), MAIN ONLY (only other numbers - a CONVERSION, not a verified close),
    plus the coverage gaps. close_for() is deliberately not used: it falls back to a half-point
    conversion, and a conversion is a model, not a close.
    """
    start = cl.tp(f.get("start")) or cl.tp(s.get("game_start"))
    if not start:
        return "NO START", "no start time on fixture or row", None
    h = cached_pin(fid)
    if h is None:
        return "NO CACHED HISTORY", f"hcache has no pinnacle file for {fid}", None
    pm = cl.book_markets(h, "pinnacle")
    if not pm:
        return "NO PINNACLE LINE", "cached file holds no Pinnacle markets", None
    pz = cl.parsed(s)
    if not pz:
        return "UNPARSED", "bet text did not parse", None
    sid = cl.SPORT.get(s.get("league"))
    if sid is None:
        return "LEAGUE NOT COVERED", f"league {s.get('league') or 'unknown'} has no sport id", None
    if pz[0] == "ml":
        mid = cl.ML_MARKET.get(sid)
        tw = cl.two_way(pm, mid, start) if mid else {}
        if len(tw) < 2:
            return "NO PINNACLE LINE", "no two-sided moneyline ticks before start", None
        side = cl.which_team(f, pz[1])
        if not side:
            return "NO PINNACLE LINE", "held team not matched to the fixture", None
        oc = {v: k for k, v in (mkmap.get(mid, [0, 0, 0, {}])[3]).items()} or {"1": str(mid), "2": str(int(mid) + 1)}
        o1, o2 = oc.get("1"), oc.get("2")
        if o1 not in tw or o2 not in tw:
            return "NO PINNACLE LINE", "moneyline outcome ids not in the cached ticks", None
        age = (start - min(tw[o1][1], tw[o2][1])).total_seconds() / 60
        if age > cl.FRESH_MIN:
            return "NO PINNACLE LINE", f"moneyline close {age / 60:.0f}h stale", None
        p = cl.novig_p(tw[o1][0], tw[o2][0])
        if pz[3]:
            side = "2" if side == "1" else "1"
        return "EQUIVALENT", f"moneyline, last tick {age:.0f} min before start", (p if side == "1" else 1 - p)
    typ = "spreads" if pz[0] == "spread" else "totals"
    cands = []
    for mid, (sp, t, hcap, outs) in (mkmap or {}).items():
        if sp != sid or t != typ or mid not in pm:
            continue
        tw = cl.two_way(pm, mid, start)
        nm = {v: k for k, v in outs.items()}
        a, b = (nm.get("1"), nm.get("2")) if typ == "spreads" else (nm.get("Over"), nm.get("Under"))
        if a in tw and b in tw:
            age = (start - min(tw[a][1], tw[b][1])).total_seconds() / 60
            if age <= cl.FRESH_MIN:
                cands.append((hcap, cl.novig_p(tw[a][0], tw[b][0]), age))
    if not cands:
        return "NO PINNACLE LINE", f"no fresh two-sided {typ} ticks before start", None
    if typ == "totals":
        want, over = pz[2], pz[1] == "OVER"
        hit = next((c for c in cands if abs(c[0] - want) < 1e-9), None)
        if hit:
            return "EXACT", f"own line {want:g}, tick {hit[2]:.0f} min before start", (hit[1] if over else 1 - hit[1])
    else:
        side = cl.which_team(f, pz[1])
        if not side:
            return "NO PINNACLE LINE", "held team not matched to the fixture", None
        want = pz[2]
        if pz[3]:
            side, want = ("2" if side == "1" else "1"), -want
        t1 = want if side == "1" else -want
        hit = next((c for c in cands if abs(c[0] - t1) < 1e-9), None)
        if hit:
            return "EXACT", f"own line {want:+g}, tick {hit[2]:.0f} min before start", (hit[1] if side == "1" else 1 - hit[1])
        want = t1
    near = ", ".join(f"{c[0]:g}" for c in sorted(cands, key=lambda c: abs(c[0] - want))[:3])
    return "MAIN ONLY", f"own line {want:g} NOT hung; nearest {near} - a conversion, not a close", None


def fingerprint(k, r, fid):
    """What a verdict depends on. Unchanged fingerprint -> reuse the checkpointed verdict."""
    s = r.get("snap") or {}
    return hashlib.sha256(json.dumps([
        CLASSIFIER_VERSION,
        k, fid, s.get("league"), s.get("bet"), s.get("game"), s.get("game_start"),
        s.get("stake"), s.get("to_pay"), s.get("price"), s.get("price_af"), s.get("flip"),
        r.get("clv"), bool(r.get("done")), bool(r.get("fixture_doubt")), bool(r.get("released_from")),
        os.path.exists(os.path.join(HC, f"{fid}__pinnacle.json.gz")) if fid else False,
    ], sort_keys=True, default=str).encode()).hexdigest()[:16]


def classify(k, r, st, mkmap):
    """(state, verdict, detail, projected_clv|None) for one ledger row, from stored data only."""
    s = r.get("snap") or {}
    if r.get("clv") is not None and not r.get("fixture_doubt"):
        state = "SCORED"
    elif r.get("fixture_doubt"):
        state = "HELD OUT"
    elif r.get("done"):
        state = "RETIRED"
    else:
        state = "UNSCORED"
    fid = r.get("fixture")
    if not fid or fid not in (st.get("fixtures") or {}):
        try:
            fid = cl.find_fixture(st, s)
        except Exception:
            fid = None
    fp = fingerprint(k, r, fid)
    prev = CK["rows"].get(k)
    if prev and prev.get("fp") == fp:
        CK_HIT[0] += 1
        return state, prev["verdict"], prev["detail"], prev.get("pclv")
    CK_HIT[1] += 1
    # An already-certified row is not a recovery candidate and its cached-history verdict says
    # nothing useful: hcache is pruned over time, so a row scored weeks ago can legitimately have
    # no cached file now. Reporting those as "BLOCKED" would invent a problem that does not exist.
    if state == "SCORED":
        v, d = "ALREADY CERTIFIED", f"how={r.get('how')} scored={str(r.get('scored'))[:10]}"
        CK["rows"][k] = {"fp": fp, "verdict": v, "detail": d, "pclv": r.get("clv")}
        return state, v, d, r.get("clv")
    # A row that ALREADY has a CLV and is held out does not need re-deriving - it needs its
    # identity established or its release respected. Those are different remedies, so they get
    # different verdicts and are never added together in the coverage arithmetic below.
    if state == "HELD OUT" and r.get("clv") is not None:
        fw = (r.get("fixture_doubt") or {}).get("why") or ""
        if r.get("released_from"):
            v = "RELEASE GRANTED, REFLAGGED"
            d = f"Peter released this row; step 5 re-raised the flag ({fw[:40]})"
        else:
            v = "HELD: IDENTITY NOT ESTABLISHED"
            d = fw[:70] or "fixture_doubt present with no reason recorded"
        CK["rows"][k] = {"fp": fp, "verdict": v, "detail": d, "pclv": r.get("clv")}
        return state, v, d, r.get("clv")
    # League first: "no OddsPapi sport id" and "no fixture in the cache" have opposite remedies
    # (one is a coverage decision, the other a fetch), and find_fixture returns None for both.
    if (s.get("league") or None) not in cl.SPORT:
        v = "BLOCKED: LEAGUE NOT COVERED"
        d = f"league {s.get('league') or 'unknown'} has no OddsPapi sport id (SPORT={sorted(cl.SPORT)})"
        CK["rows"][k] = {"fp": fp, "verdict": v, "detail": d, "pclv": None}
        return state, v, d, None
    if not fid:
        v, d, p = "BLOCKED: NO FIXTURE", "no stored fixture and none resolves against the current cache", None
    else:
        f = (st.get("fixtures") or {}).get(fid) or {}
        v, d, p = pin_lines(fid, s, f, mkmap)
        if v in ("EXACT", "EQUIVALENT"):
            dec = cl.eff_dec(s)
            if not dec:
                v, d, p = "BLOCKED: NO PRICE", "close is available but the row carries no after-fee price", None
            else:
                p = round(p * dec - 1, 4)
                v = "RECOVERABLE NOW"
                d = f"verified same-line close available in cache ({d})"
        elif v == "MAIN ONLY":
            v = "NOT CERTIFIABLE: CONVERSION ONLY"
        else:
            v = f"BLOCKED: {v}"
    CK["rows"][k] = {"fp": fp, "verdict": v, "detail": d, "pclv": p}
    return state, v, d, p


# =============================================================== PART A
def day_audit(st, cbets, tracker, mkmap, reg, ev):
    say("")
    say("#" * 100)
    say(f"PART A - DAY AUDIT: {DATE} (ET)")
    say("#" * 100)
    say("")
    say("A1. SELECTIONS ON THIS DATE, WITH EVERY LINKED RECORD")
    say("=" * 100)
    say("A row is included when its GAME DATE or its DECISION DATE is the audit date; both are")
    say("shown, because the tracker groups by one and the executor by the other, and the 19-row")
    say("figure has to be reproducible on whichever basis produced it.")
    sel = collections.defaultdict(lambda: {"tracker": [], "clv": [], "reg": [], "manual": [], "alerts": 0})
    basis = {}
    for k, b in tracker.items():
        gd, dd = iso_day(b.get("game_start")), iso_day(b.get("placed") or b.get("first_seen"))
        if DATE in (gd, dd):
            sel[sel_key(b.get("league"), b.get("game"), b.get("bet"))]["tracker"].append((k, b))
            basis[k] = (gd, dd)
    for k, r in cbets.items():
        s = r.get("snap") or {}
        gd, dd = iso_day(s.get("game_start")), iso_day(s.get("placed") or s.get("placed_bot") or r.get("first_seen"))
        if DATE in (gd, dd):
            sel[sel_key(s.get("league"), s.get("game"), s.get("bet"))]["clv"].append((k, r))
            basis[k] = (gd, dd)
    for o in ((reg or {}).get("orders") or []):
        if iso_day(o.get("decided_utc")) == DATE:
            sk, _ = reg_sel_key(o.get("key"))
            sel[sk or f"UNPARSED-REGKEY|{o.get('key')}"]["reg"].append(o)
    for m in ((reg or {}).get("manual") or []):
        if iso_day(m.get("_sent")) == DATE:
            sel[sel_key(m.get("sport"), m.get("game"), m.get("bet"))]["manual"].append(m)
    try:
        al = (json.load(open("alerts.json")) or {}).get("alerts") or []
    except Exception:
        al = []
    for a in al:
        if iso_day(a.get("alert_utc")) == DATE:
            sk = sel_key(a.get("sport"), a.get("game"), a.get("bet"))
            if sk in sel:
                sel[sk]["alerts"] += 1

    tot = collections.Counter()
    say("")
    say(f"  DISTINCT SELECTIONS: {len(sel)}")
    for sk in sorted(sel):
        v = sel[sk]
        for fld in ("tracker", "clv", "reg", "manual"):
            tot[fld] += len(v[fld])
        say("")
        say(f"  SELECTION  {sk}")
        say(f"    records: tracker {len(v['tracker'])} | clv {len(v['clv'])} | registry-order "
            f"{len(v['reg'])} | manual-note {len(v['manual'])} | alerts {v['alerts']}")
        for k, b in v["tracker"]:
            gd, dd = basis.get(k, (None, None))
            say(f"      tracker  {k[:40]:<40} book={b.get('book')} game={gd} decided={dd} "
                f"dup_of={b.get('dup_of') or '-'} result={b.get('result') or '-'}")
        for k, r in v["clv"]:
            say(f"      clv      {k[:40]:<40} clv={r.get('clv')} done={bool(r.get('done'))} "
                f"tries={r.get('tries')} doubt={bool(r.get('fixture_doubt'))} "
                f"released={bool(r.get('released_from'))}")
        for o in v["reg"]:
            lo = o.get("live_order") or {}
            say(f"      registry {str(o.get('decided_utc'))[:19]} key={str(o.get('key'))[:44]:<44} "
                f"live={o.get('live')} src={o.get('source')} intent={lo.get('intent')} "
                f"order_id={str(lo.get('order_id'))[:38]}")
        for m in v["manual"]:
            say(f"      note     {str(m.get('_sent'))[:19]} {m.get('book')} src={m.get('source')} "
                f"bet={str(m.get('bet'))[:30]}")
    say("")
    say(f"  TOTALS on {DATE}: tracker {tot['tracker']}, clv {tot['clv']}, registry {tot['reg']}, "
        f"notes {tot['manual']}, for {len(sel)} distinct selection(s)")

    say("")
    say("A2. ORDER STATUS - placed / filled / cancelled / pending / unknown")
    say("=" * 100)
    say("Status comes only from what the record says plus terminal venue evidence. A position")
    say("existing is NOT treated as proof a given order filled (Peter: \"Don't infer 'killed'")
    say("from the position count\") - the converse is just as unsound, so position evidence is")
    say("listed separately and never promoted to a fill.")
    vids = (reg or {}).get("venue_ids") or {}
    ev_by = {}
    for e in ev:
        for i in ((e.get("match") or {}).get("order_ids") or []) + ((e.get("match") or {}).get("client_ids") or []):
            ev_by[str(i)] = e
    stc = collections.Counter()
    for sk in sorted(sel):
        if not sel[sk]["reg"]:
            continue
        say("")
        say(f"  SELECTION  {sk}")
        for o in sel[sk]["reg"]:
            lo = o.get("live_order") or {}
            oid, cid = str(lo.get("order_id") or ""), str(lo.get("client_id") or "")
            e = ev_by.get(oid) or ev_by.get(cid)
            filled, avg = lo.get("filled_stake"), lo.get("avg_price")
            if lo.get("intent") or oid.startswith("intent-"):
                s_, w_ = "INTENT ONLY", "journal record, no venue order id"
            elif e and e.get("kind") == "terminal_at_venue":
                s_, w_ = "CANCELLED/TERMINAL", f"evidence {e.get('id')}: {str(e.get('verdict'))[:44]}"
            elif filled not in (None, "") and tb.num(filled):
                s_, w_ = "FILLED", f"filled_stake recorded, avg_price {avg}"
            elif str(lo.get("status") or "").lower() == "placed":
                s_, w_ = "PLACED, FILL UNKNOWN", "accepted by the venue; no fill ever written back"
            else:
                s_, w_ = "UNKNOWN", f"status={lo.get('status')}"
            stc[s_] += 1
            say(f"    {str(o.get('decided_utc'))[:19]}  {s_:<20} {w_}")
            say(f"        order_id {oid or '-'}  client_id {cid or '-'}  venue_order_id "
                f"{(vids.get(cid) or {}).get('venue_order_id') or 'NOT MAPPED'}")
            say(f"        filled_stake={filled if filled is not None else 'UNKNOWN'} "
                f"avg_price={avg if avg is not None else 'UNKNOWN'} "
                f"screen={o.get('fill_screen')} line={o.get('fill_line')}")
        for k, b in [(k, b) for k, b in sel[sk]["tracker"] if str(k).startswith("nv|")]:
            say(f"    position evidence (NOT an order status): {k[:40]} "
                f"result={b.get('result') or 'unsettled'} open={bool(b.get('open'))}")
    say("")
    say(f"  order status roll-up: {dict(stc)}")

    say("")
    say("A3. STAKE, EXECUTION PRICE, FEES, RESULT, NET P&L")
    say("=" * 100)
    say("Dollar amounts are in the private email only (repo rule: logs print counts).")
    for sk in sorted(sel):
        say("")
        say(f"  SELECTION  {sk}")
        for k, b in sel[sk]["tracker"]:
            d = cl.eff_dec(b)
            src = ("stake/to_pay" if (tb.num(b.get("stake")) and tb.num(b.get("to_pay")))
                   else "bot fill record" if b.get("price_af") not in (None, "")
                   else "quoted price" if b.get("price") not in (None, "") else "NONE")
            say(f"    {k[:40]:<40} book={b.get('book')} price={b.get('price')} "
                f"after-fee-dec={round(d, 4) if d else 'UNKNOWN'} basis={src} "
                f"result={b.get('result') or 'UNSETTLED'}")
            say(f"      stake={b.get('stake')} to_pay={b.get('to_pay')} profit={b.get('profit')}", money=True)
        for o in sel[sk]["reg"]:
            lo = o.get("live_order") or {}
            say(f"    registry {str(o.get('decided_utc'))[:19]} limit={lo.get('limit')} "
                f"screen={o.get('fill_screen')} fee_basis={o.get('fee_basis')} EXECUTION PRICE: "
                f"{'UNKNOWN - no avg_price written back' if lo.get('avg_price') in (None, '') else lo.get('avg_price')}")
            say(f"      asked={lo.get('asked_stake')} filled={lo.get('filled_stake')}", money=True)
    say("")
    say("  An execution price shown as UNKNOWN is not a reporting gap: no fill price is persisted")
    say("  anywhere outside the bot's Gmail ledger, which this audit does not read.")

    say("")
    say("A4. PINNACLE CLOSING-LINE AVAILABILITY (cache only - nothing fetched, nothing modelled)")
    say("=" * 100)
    av = collections.Counter()
    for sk in sorted(sel):
        say("")
        say(f"  SELECTION  {sk}")
        if not sel[sk]["clv"]:
            say("    NO CLV ROW - the selection never reached the ledger at all")
            av["NO CLV ROW"] += 1
            continue
        for k, r in sel[sk]["clv"]:
            state, v, d, p = classify(k, r, st, mkmap)
            av[v] += 1
            say(f"    {k[:40]:<40} {state:<9} {v:<34} {d[:40]}")
    say("")
    say(f"  availability roll-up: {dict(av)}")

    say("")
    say("A5. WHY EACH SELECTION LACKS CERTIFIED CLV")
    say("=" * 100)
    for sk in sorted(sel):
        say("")
        say(f"  SELECTION  {sk}")
        if not sel[sk]["clv"]:
            say("    no clv row on this date - see A1 for which sources did carry it")
            continue
        for k, r in sel[sk]["clv"]:
            if r.get("clv") is not None and not r.get("fixture_doubt"):
                say(f"    {k[:40]:<40} CERTIFIED clv={r.get('clv')} how={r.get('how')}")
                continue
            fv, fw = cl.fixture_check(st, r)
            iv, iw = cl.identity_check(r)
            say(f"    {k[:40]:<40} clv={r.get('clv')} done={bool(r.get('done'))} tries={r.get('tries')}")
            say(f"        stored reason : {str(r.get('why') or '(none stored)')[:74]}")
            say(f"        fixture_check : {fv} {fw}")
            say(f"        identity_check: {iv} {iw}")
            if r.get("fixture_doubt"):
                say(f"        HELD OUT since {(r['fixture_doubt'] or {}).get('since')}: "
                    f"{str((r['fixture_doubt'] or {}).get('why'))[:58]}")
    return sel, tot, basis, stc


# =============================================================== PART B
def reflag_section(cbets):
    say("")
    say("B1. ARE THE RELEASED ROWS BEING REFLAGGED?")
    say("=" * 100)
    rel = [(k, r) for k, r in cbets.items() if r.get("released_from")]
    reflag = [(k, r) for k, r in rel if r.get("fixture_doubt")]
    same = sum(1 for _, r in reflag
               if (r.get("released_from") or {}).get("why") == (r.get("fixture_doubt") or {}).get("why"))
    say(f"  rows carrying released_from                       {len(rel)}")
    say(f"  of those, carrying fixture_doubt again            {len(reflag)}   (the release intended 0)")
    say(f"  reflagged with the IDENTICAL reason string        {same}/{len(reflag)}")
    say("")
    say("  MECHANISM, from the code rather than inferred:")
    say("    clv_release_verified.py:180  rec['released_from'] = rec.pop('fixture_doubt')")
    say("        -> the release is correct; the flag IS cleared.")
    say("    clv_ledger.main() step 5     for every row with clv not None:")
    say("        fv,_=fixture_check(...); iv,_=identity_check(...)")
    say("        if (fv=='doubt' or iv=='doubt') and not rec.get('fixture_doubt'): re-set it")
    say("        -> the only guard is 'is the flag absent right now'. released_from is never")
    say("           consulted, and identity_check reads espn_filled + teams + bet text, none of")
    say("           which the release changed, so the next run reaches the same verdict.")
    for k, r in reflag[:6]:
        iv, iw = cl.identity_check(r)
        say(f"    {k[:38]:<38} identity_check now: {iv} - {iw[:50]}")
    if len(reflag) > 6:
        say(f"    ... {len(reflag)} reflagged rows in total")
    say("")
    say("  THE EXACT SAFE FIX (one condition; no historical CLV rewritten):")
    say("    prev = rec.get('released_from') or {}")
    say("    if (fv=='doubt' or iv=='doubt') and not rec.get('fixture_doubt') \\")
    say("            and not (prev.get('fixture') == rec.get('fixture')")
    say("                     and prev.get('why') == (fw if fv=='doubt' else iw)):")
    say("        rec['fixture_doubt'] = ...")
    say("    Keying on fixture AND reason is what makes it safe: a row that later develops a")
    say("    DIFFERENT doubt, or whose fixture changes, is flagged normally. Nothing is released")
    say("    that Peter did not already release by hand on Nov 12.")
    say("    PREREQUISITE: released_from currently stores only {since, why} - NOT the fixture it")
    say("    covered. Recording rec['fixture'] at release time is part of the fix; without it the")
    say("    condition can key only on the reason string, which is weaker.")
    return rel, reflag


def recovery_inventory(st, cbets, tracker, mkmap, reg):
    say("")
    say("#" * 100)
    say("PART B - HISTORICAL RECOVERY INVENTORY (all dates)")
    say("#" * 100)

    rows = [(k, r) for k, r in cbets.items()]
    buckets = collections.defaultdict(list)
    for k, r in rows:
        state, v, d, p = classify(k, r, st, mkmap)
        buckets[state].append((k, r, v, d, p))

    say("")
    say("B2. INVENTORY BY STATE")
    say("=" * 100)
    say(f"  ledger rows total      {len(rows)}")
    for s_ in ("SCORED", "HELD OUT", "RETIRED", "UNSCORED"):
        say(f"    {s_:<10} {len(buckets[s_]):5d}")
    try:
        stale = cstale.stale_map(cbets, tracker)
    except Exception:
        stale = {}
    dup_live = [k for k, b in tracker.items() if b.get("dup_of")]
    say(f"  duplicates: stale_map excludes {len(stale)} | tracker marks {len(dup_live)} rows dup_of,")
    say(f"    of which {sum(1 for k in dup_live if k in cbets)} still carry their own ledger row")
    say("    (clv_ledger, clv_stale and clv_readout contain no reference to dup_of at all)")

    say("")
    say("B3. RECOVERABILITY, FROM CACHED DATA ONLY")
    say("=" * 100)
    say("  RECOVERABLE NOW = a fixture resolves against the current cache AND the bet's own line")
    say("  (or a moneyline) is present in cached Pinnacle ticks before start AND the row carries")
    say("  an after-fee price. Everything else names the specific missing piece. A conversion off")
    say("  the main line is NOT recoverable coverage and has its own row.")
    for s_ in ("HELD OUT", "RETIRED", "UNSCORED"):
        if not buckets[s_]:
            continue
        say("")
        say(f"  {s_}  (n={len(buckets[s_])})")
        for v, n in collections.Counter(x[2] for x in buckets[s_]).most_common():
            say(f"    {n:5d}  {v}")

    rec = [(k, r, v, d, p) for s_ in ("HELD OUT", "RETIRED", "UNSCORED")
           for (k, r, v, d, p) in buckets[s_] if v == "RECOVERABLE NOW"]
    say("")
    say(f"  TOTAL RECOVERABLE NOW: {len(rec)}")

    say("")
    say("B4. PROJECTED RECOVERY BY DATE, SOURCE AND LANE  (PROJECTED, NOT WRITTEN)")
    say("=" * 100)
    say("  These are what the recoverable rows WOULD score, computed in memory from cached ticks")
    say("  at the bet's own line. Nothing is stored and no existing CLV is altered.")
    lane_by_sel = {}
    for o in ((reg or {}).get("orders") or []):
        sk, _ = reg_sel_key(o.get("key"))
        if sk and o.get("source"):
            lane_by_sel.setdefault(sk, o["source"])

    def lane_of(r):
        s = r.get("snap") or {}
        return lane_by_sel.get(sel_key(s.get("league"), s.get("game"), s.get("bet")), "unlinked")

    def grp(fn, label):
        say("")
        say(f"  by {label}:")
        agg = collections.defaultdict(list)
        for k, r, v, d, p in rec:
            agg[fn(r)].append(p)
        for key in sorted(agg, key=lambda x: str(x)):
            v_ = [x for x in agg[key] if x is not None]
            if not v_:
                say(f"    {str(key):<24} n {len(agg[key]):4d}   projected CLV UNKNOWN")
                continue
            m = sum(v_) / len(v_)
            # Peter's rule: bound a claim, do not assert it. A zero standard deviation is a real
            # measurement (identical rows), so test for None rather than truthiness - `if sd`
            # would silently relabel a genuine 0.00 spread as "no spread".
            sd = (sum((x - m) ** 2 for x in v_) / (len(v_) - 1)) ** 0.5 if len(v_) > 1 else None
            se = (sd / len(v_) ** 0.5) if sd is not None else None
            rng = f"   +/-{200 * se:.2f}% (1 s.e.)" if se is not None else "   (n=1, no spread)"
            say(f"    {str(key):<24} n {len(v_):4d}   projected mean CLV {100 * m:+.2f}%{rng}")

    grp(lambda r: iso_day((r.get("snap") or {}).get("game_start")) or "no game date", "date")
    grp(lambda r: (r.get("snap") or {}).get("source") or "unknown", "source")
    grp(lane_of, "lane (from registry key; 'unlinked' = not resolvable without the Gmail ledger)")

    say("")
    say("B5. BEFORE / AFTER COVERAGE")
    say("=" * 100)
    scored_now = len(buckets["SCORED"])
    denom = len(rows)
    # The two additions below are disjoint BY CONSTRUCTION, not by assumption: a held-out row
    # that already carries a CLV is classified "RELEASE GRANTED, REFLAGGED" and can never also
    # be "RECOVERABLE NOW", which is reserved for rows with no CLV at all. Counting them from
    # the same buckets keeps that guarantee visible instead of re-scanning and hoping.
    reflag_fix = [x for s_ in ("HELD OUT", "RETIRED", "UNSCORED")
                  for x in buckets[s_] if x[2] == "RELEASE GRANTED, REFLAGGED"]
    overlap = {x[0] for x in reflag_fix} & {x[0] for x in rec}
    say(f"  rows in ledger                      {denom}")
    say(f"  certified now                       {scored_now}  ({100 * scored_now / denom:.1f}%)")
    say(f"  + released rows, flag no longer re-raised  {len(reflag_fix)}")
    say(f"  + recoverable from cached data            {len(rec)}")
    say(f"  overlap between those two sets      {len(overlap)}  (must be 0)")
    after = scored_now + len(reflag_fix) + len(rec)
    say(f"  = projected certified               {after}  ({100 * after / denom:.1f}%)")
    say("")
    say("  UNRESOLVED AFTER EVERY FIX ABOVE, by exact reason:")
    left = collections.Counter()
    FIXED_BY_REPAIR = ("RECOVERABLE NOW", "RELEASE GRANTED, REFLAGGED")
    for s_ in ("HELD OUT", "RETIRED", "UNSCORED"):
        for k, r, v, d, p in buckets[s_]:
            if v not in FIXED_BY_REPAIR:
                left[v] += 1
    for v, n in left.most_common():
        say(f"    {n:5d}  {v}")
    say("")
    say("  Each of those needs something this audit is forbidden to invent: a fixture that is not")
    say("  in the cache, a Pinnacle file that was never downloaded, a price that was never")
    say("  written back, or a league with no OddsPapi sport id. None is recoverable by reasoning.")
    return buckets, rec, left


# =============================================================== main
def main():
    now = datetime.now(timezone.utc)
    say("CLV RECOVERY AUDIT - READ-ONLY")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET   audit date (Part A) {DATE}")
    say("No OddsPapi call (billable or free). No IMAP. No write to production state. No guessed")
    say("fixture, assumed fill or modelled close - unknown stays unknown.")
    say("=" * 100)
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        say(f"FATAL: clv/state.enc unreadable ({type(e).__name__})")
        return 1
    cbets = st.get("bets") or {}
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        tracker = {}
        say(f"WARNING: tracker/state.enc unreadable ({type(e).__name__}) - tracker rows UNKNOWN")
    try:
        mkmap = (json.load(open(MKFILE)) or {}).get("m") or {}
    except Exception as e:
        mkmap = {}
        say(f"WARNING: {MKFILE} unreadable ({type(e).__name__}) - line availability UNKNOWN")
    reg = None
    try:
        import registry
        reg = registry.load() if registry.enabled() else None
    except Exception as e:
        say(f"WARNING: registry import failed ({type(e).__name__})")
    if reg is None:
        say("WARNING: private registry UNREADABLE - order ids, fills and lanes UNKNOWN")
    try:
        ev = (json.load(open(EVIDENCE)) or {}).get("entries") or []
    except Exception:
        ev = []
    global CK
    try:
        prev = json.load(open(CKPT_PATH))
        if prev.get("v") == CK["v"]:
            CK = prev
    except Exception:
        pass
    say(f"  hcache files {len(os.listdir(HC)) if os.path.isdir(HC) else 0} | clv rows {len(cbets)} | "
        f"tracker rows {len(tracker)} | market ids {len(mkmap)} | "
        f"registry orders {len((reg or {}).get('orders') or [])} | "
        f"checkpoint rows {len(CK['rows'])}")

    sel, tot, basis, stc = day_audit(st, cbets, tracker, mkmap, reg, ev)
    rel, reflag = reflag_section(cbets)
    buckets, rec, left = recovery_inventory(st, cbets, tracker, mkmap, reg)

    say("")
    say("A6. RECAP RECONCILIATION FOR " + DATE)
    say("=" * 100)
    try:
        stale = cstale.stale_map(cbets, tracker)
    except Exception:
        stale = {}
    dups = [(k, b) for k, b in tracker.items() if b.get("dup_of") and DATE in basis.get(k, (None, None))]
    say(f"  distinct selections                  {len(sel)}")
    say(f"  tracker rows                         {tot['tracker']}")
    say(f"    of which marked dup_of             {len(dups)}  (tracker hides them; the ledger does not)")
    say(f"  clv rows                             {tot['clv']}")
    say(f"    of which excluded by stale_map     {sum(1 for sk in sel for k, _ in sel[sk]['clv'] if k in stale)}")
    say(f"  registry order records               {tot['reg']}")
    say(f"    INTENT-ONLY journal records        {stc.get('INTENT ONLY', 0)}")
    oids = [str((o.get('live_order') or {}).get('order_id')) for sk in sel for o in sel[sk]['reg']]
    real = [i for i in oids if i and not i.startswith('intent-')]
    say(f"    distinct venue order ids           {len(set(real))} from {len(real)} record(s)")
    say("")
    say("  INFLATION SOURCES, measured:")
    say(f"    a) registry stores each live order twice (lane-prefixed key + bare key): "
        f"{len(real) - len(set(real))} duplicate record(s)")
    say(f"    b) manual notes beside the venue row: {len(dups)} marked dup_of, "
        f"{sum(1 for sk in sel for k, b in sel[sk]['tracker'] if str(k).startswith('mn|') and not b.get('dup_of'))} unmarked")
    say(f"    c) group_fills() collapses partials for ProphetX only; books on this date: "
        f"{sorted({b.get('book') for sk in sel for _, b in sel[sk]['tracker'] if b.get('book')})}")
    say("")
    say("  Each selection is counted ONCE. No partial fill is summed into the selection count and")
    say("  no order id is counted twice even where the registry stored it twice.")

    say("")
    say("=" * 100)
    say(f"checkpoint: reused {CK_HIT[0]} verdict(s), recomputed {CK_HIT[1]}")
    say("END. Nothing was written to production state, fetched, released, rescored or repaired.")

    try:
        os.makedirs(os.path.dirname(CKPT_PATH) or ".", exist_ok=True)
        json.dump(CK, open(CKPT_PATH, "w"), separators=(",", ":"))
        json.dump({"generated": cl.iso(now), "audit_date": DATE,
                   "states": {k: len(v) for k, v in buckets.items()},
                   "recoverable": [{"id": k, "verdict": v, "detail": d, "projected_clv": p}
                                   for k, r, v, d, p in rec],
                   "unresolved": dict(left),
                   "reflagged": [k for k, _ in reflag]},
                  open(OUT_PATH, "w"), indent=1)
        print(f"wrote {CKPT_PATH} and {OUT_PATH} (audit artefacts; no production state touched)", flush=True)
    except Exception as e:
        print(f"checkpoint not written ({type(e).__name__})", flush=True)

    if os.environ.get("EMAIL_NOW") == "1":
        try:
            import executor as ex
            ex.send(f"CLV recovery audit {DATE} (read-only)", "\n".join(L))
            print("report emailed (full detail incl. dollar figures)", flush=True)
        except Exception as e:
            print(f"email skipped ({type(e).__name__})", flush=True)
    print(f"recovery audit: rows {len(cbets)}, scored {len(buckets['SCORED'])}, "
          f"held {len(buckets['HELD OUT'])}, retired {len(buckets['RETIRED'])}, "
          f"unscored {len(buckets['UNSCORED'])}, recoverable {len(rec)}, reflagged {len(reflag)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

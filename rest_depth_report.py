#!/usr/bin/env python3
"""
RESTING-DEPTH MEASUREMENT (Nov 10). Read-only, 0 OddsPapi credits, MANUAL DISPATCH ONLY.

THE ONE QUESTION IT ANSWERS: how often do BOTH Novig and Kalshi lack the exact alert line, so a
third resting venue would have been the only way to rest at all?

WHY IT EXISTS. Peter asked whether to add Polymarket US to REST_BOOKS as a third venue. The maker
case died with the PDI test - participateDontInitiate is dropped by the venue, so Polymarket is a
taker there at -116.8 on a -110 screen, the worst of the three. That leaves exactly one argument
for adding it: DEPTH, on the plays where neither of the first two can rest. Against that sits a
real asymmetry - Polymarket is the only venue whose expiry does not work, so every bid needs an
active cancel and a failed cancel leaves money resting all day.

Nobody knew the frequency. Claude and Muse independently landed on the same conclusion - leave the
chain at Novig, Kalshi - and both said the flip should never happen on a read when it can happen
on a measurement. This is the measurement.

NOT A NEW SCAN OR LENS, and deliberately not scheduled: a one-off diagnostic for a pending
decision, run by hand, registering nothing. The idea freeze stands.

HOW. The executor already records the answer and nobody had read it. Every run's email carries a
LEDGER row per play, and rest_bid writes its refusal into live_rest.reason - including, per book,
"<Book>: no exact-line market". Gmail is the registry here as it is for bot_orders(), so this
reads the executor's own emails rather than re-deriving anything or spending a credit.
"""
import collections
import email
import email.header
import json
import os
import sys

import executor as ex

DAYS = int(os.environ.get("DEPTH_DAYS", "") or "7")
SUBJECTS = ('"Bets dry run:"', '"Bets LIVE:"')


def say(s):
    print(s, flush=True)


def ledger_rows(M, subject, since):
    """Every LEDGER row from the executor's own emails with this subject prefix."""
    rows, mails = [], 0
    typ, data = M.uid("SEARCH", None, "SUBJECT", subject, "SINCE", since)
    if typ != "OK":
        return rows, 0
    want = subject.strip('"')
    for uid in (data[0].split() if data and data[0] else []):
        typ, d = M.uid("FETCH", uid, "(RFC822)")
        if typ != "OK" or not d or not d[0]:
            continue
        raw = d[0][1]
        # IMAP SUBJECT is a SUBSTRING match - the Oct 27 bug that read dry-run mail as live. The
        # real header is re-checked before the body is trusted.
        subj = str(email.header.make_header(email.header.decode_header(
            email.message_from_bytes(raw).get("Subject") or "")))
        if not subj.startswith(want):
            continue
        txt = ex.body_text(raw)
        # Extracted exactly the way executor.bot_orders() already does it (rfind the header, then
        # raw_decode from the first bracket). My first draft used a line-anchored regex, which is
        # a second way of doing a solved thing - and would have broken the moment the ledger JSON
        # wrapped or something else in the body looked like a list on its own line.
        i = txt.rfind("LEDGER (machine-readable")
        if i < 0:
            continue
        try:
            parsed, _ = json.JSONDecoder().raw_decode(txt[txt.index("[", i):])
        except Exception:
            continue
        rows.extend(parsed)
        mails += 1
    return rows, mails


def audit(rows):
    """REJECTED vs ACCEPTED, read-only (Peter, Nov 10). Cached ledger + cached Pinnacle only.

    Every column is computed from what was knowable AT THE DECISION. fill_price_after_fee is the
    real best book price after that venue's fee at the moment the executor decided, so it is an
    EXECUTABLE TAKER price - a price that was actually up. A resting bid is NOT modelled anywhere
    here: nothing in the ledger says whether an unfilled post would have been crossed to, so
    assuming one would have filled is the one inference this audit refuses to make.

    Categories are the executor's OWN live_why_not strings - the original blocking rules, not
    buckets invented afterwards. A play can carry MORE THAN ONE reason, so the category counts sum
    above the number of rejected plays; the primary (first) reason is used for the exclusive
    grouping and the overlap is reported rather than hidden.
    """
    import clv_ledger as _cl
    import clv_std as _cs
    import hist_cache as _hc
    import nba_names as _nn
    from datetime import datetime as _dt, timezone as _tz

    now = _dt.now(_tz.utc)
    say("")
    say("=" * 100)
    say("REJECTED vs ACCEPTED - Lane 1 qualification audit (READ-ONLY, 0 paid credits)")
    say("=" * 100)

    # FROZEN WINDOW (Peter): Nov 4-10 2026 ET, explicit, so the count stops drifting with a
    # trailing 7-day read. Earlier runs reported 167, then 172, then 175 for exactly this reason.
    W0, W1 = "2026-11-04T05:00:00Z", "2026-11-11T04:59:59Z"   # ET days, as the system uses
    before = len(rows)
    rows = [r for r in rows if r.get("decided_utc") and W0 <= str(r["decided_utc"]) <= W1]
    say(f"  window {W0} .. {W1} (Nov 4-10 ET)")
    say(f"  rows in window {len(rows)} of {before} read")

    acc = [r for r in rows if r.get("live")]
    rej = [r for r in rows if not r.get("live")]
    say(f"  unique opportunities {len(rows)}   accepted {len(acc)}   rejected {len(rej)}")

    def reasons(r):
        w = r.get("live_why_not")
        return [str(x) for x in (w if isinstance(w, list) else [w] if w else [])]

    multi = sum(1 for r in rej if len(reasons(r)) > 1)
    say(f"  rejected plays carrying MORE THAN ONE blocking rule: {multi} "
        f"(grouped below by the FIRST reason, so groups are mutually exclusive)")

    # ---- Pinnacle close per row, from the cache only. No fetch, no estimate. ----
    # FIXTURES. The first version called _cl.load_state() behind a hasattr guard - and that
    # function DOES NOT EXIST, so the guard silently left an empty fixture map and every
    # find_fixture() failed, which is why the whole CLV column came back n=0. A missing leg read
    # exactly like missing data. Read the way circa_close.py does it: the encrypted state file.
    st = {"fixtures": {}}
    try:
        import tracker_build as _tb
        st["fixtures"] = dict((_tb.dec(json.load(open(_cl.STATE))).get("fixtures") or {}))
        say(f"  fixture cache: {len(st['fixtures'])} fixture(s) read from disk")
    except Exception as e:
        say(f"  fixture cache UNAVAILABLE ({type(e).__name__}) - the CLV column cannot compute")
    mkmap = {}
    try:
        mkmap = _cl.load_markets(st, now)
    except Exception:
        pass

    def clv_fields(r):
        """league / market / bet text for close_for, derived from what a ledger row ACTUALLY carries.
        Ledger rows have no league/market/side fields - they are inside r["key"] (SPORT|game|market|side)
        and the exact line is r["alert_line"]. The previous reader passed r.get("league"/"market"/"side"),
        i.e. None x3, so close_for returned "bet text not parsed" for every row (the 0% join).
        EXACT LINE ONLY: totals need a side AND a line; a row whose executable fill is on a different
        line than the alert is NOT scored (no converted line without a validated equivalent price).
        Returns None (UNKNOWN) for anything it cannot pin down - never a guess."""
        k = str(r.get("key") or "").split("|")
        if len(k) < 4:
            return None
        lg, mk, sd = k[0].upper(), k[2].lower(), k[3]
        ln = r.get("alert_line")
        if mk != "total" or sd.upper() not in ("OVER", "UNDER") or ln is None:
            return None   # spreads/MLs: team-text parse is not covered here -> UNKNOWN, not zero
        if r.get("fill_line") is not None and float(r["fill_line"]) != float(ln):
            return None   # executable price is on another line: not comparable to this close
        return lg, "total", f"{sd.capitalize()} {float(ln):g}"

    def clv_of(r):
        """(clv_pct, beat) at the EXECUTABLE price against a verified same-line Pinnacle close.
        None where any leg is missing - never estimated, never substituted."""
        am = r.get("fill_price_after_fee")
        if am is None:
            return None, None
        cf = clv_fields(r)
        if cf is None:
            return None, None
        _lg, _mk, _bet = cf
        game = r.get("game") or str(r.get("key") or "").split("|")[1]
        try:
            fid = _cl.find_fixture(st, {"bet": _bet, "league": _lg, "game": game,
                                        "teams": _nn.teams_of({"league": _lg, "teams": None}),
                                        "game_start": r.get("start_utc")})
        except Exception:
            fid = None
        if not fid or not os.path.exists(_hc._path(fid, "pinnacle")):
            return None, None
        f = (st.get("fixtures") or {}).get(fid) or {}
        start = _cl.tp(f.get("start"))
        if not start:
            return None, None
        try:
            h = _hc.get_hist(fid, ["pinnacle"], start)
            c, _why = _cl.close_for({"bet": _bet, "league": _lg, "market": _mk}, f,
                                    _cl.book_markets(h, "pinnacle"), mkmap, start, _lg)
        except Exception:
            return None, None
        if not c or not _cs.close_verified(c.get("how")):
            return None, None
        dec = 1 + (am / 100.0 if am > 0 else 100.0 / abs(am))
        try:
            v = _cs.canon(r.get("fill_book"))
            pct = _cs.net_clv(c["p"], dec, v, maker=False, league=_lg)
        except Exception:
            return None, None
        return pct, (pct is not None and pct > 0)

    # OUTCOMES come from the FEED, and the KEYS DO NOT MATCH, which is why the previous attempt
    # loaded 2,303 graded results and joined zero of them. The feed's key is
    # 'kalshi|{"market_ticker": ...}' - a book/market identifier - while a ledger key is
    # derive_key()'s sport|game|market|side. Different namespaces; they can never meet.
    #
    # derive_key() cannot bridge them either: it needs p["bet"] and p["sport"], and a feed alert
    # carries neither. But BOTH sides carry league, market, side and game, so the join is built
    # from those directly - no parse_bet, no key lookup. Game names are reduced to a token set so
    # "Boston Celtics @ Milwaukee Bucks" matches "Celtics @ Bucks".
    def jkey(x):
        g = str(x.get("game") or "").lower()
        for ch in "@/-,.":
            g = g.replace(ch, " ")
        toks = frozenset(t for t in g.split() if len(t) > 2)
        return (str(x.get("league") or "").upper(), str(x.get("market") or "").lower(),
                str(x.get("side") or x.get("side_label") or "").upper(), toks)

    graded = {}
    try:
        for a in (json.load(open("liquidity/alerts.json")).get("alerts") or []):
            if a.get("result") in ("W", "L", "P"):
                graded[jkey(a)] = a["result"]
        say(f"  graded outcomes in the feed: {len(graded)}")
    except Exception as e:
        say(f"  feed outcomes UNAVAILABLE ({type(e).__name__}) - the units column cannot compute")

    # VALIDATE THE JOIN BEFORE TRUSTING ANY AGGREGATE. A match rate near zero means the join is
    # broken, not that the games are ungraded - which is exactly the failure this report has
    # already produced twice.
    hit = [r for r in rows if jkey(r) in graded]
    say(f"  JOIN CHECK: {len(hit)} of {len(rows)} ledger rows matched a graded feed outcome "
        f"({100.0 * len(hit) / max(len(rows), 1):.0f}%)")
    for r in hit[:3]:
        say(f"     e.g. {str(r.get('game'))[:40]:<40} {r.get('market')} {r.get('side')} "
            f"-> {graded[jkey(r)]}")
    if not hit:
        say("     JOIN FAILED. Units and beat-close cannot be computed; reported as unavailable")
        say("     rather than as zero.")

    def units_at_exec(r):
        """Hypothetical net units ONLY where a price was demonstrably executable AND the play is
        graded. Flat 1u risked at that executable price."""
        am = r.get("fill_price_after_fee")
        res = r.get("result") or graded.get(jkey(r))
        if am is None or res not in ("W", "L", "P"):
            return None
        if res == "P":
            return 0.0
        return round((am / 100.0 if am > 0 else 100.0 / abs(am)) if res == "W" else -1.0, 3)

    def block(name, rs):
        exe = [r for r in rs if r.get("fill_price_after_fee") is not None]
        u = [units_at_exec(r) for r in exe]
        u = [x for x in u if x is not None]
        cl_ = [clv_of(r) for r in exe]
        pct = [p for p, _b in cl_ if p is not None]
        beat = [b for _p, b in cl_ if b is not None]
        dep = [r.get("fill_avail") for r in exe if r.get("fill_avail") is not None]
        say(f"  {name[:56]:<56} {len(rs):4}  exec {len(exe):3}  "
            f"units {(f'{sum(u):+.2f}' if u else '   n/a'):>7} (n={len(u)})  "
            f"CLV {(f'{sum(pct)/len(pct):+.2f}%' if pct else '  n/a'):>8} (n={len(pct)})  "
            f"beat {(f'{sum(beat)}/{len(beat)}' if beat else 'n/a'):>7}  "
            f"depth med {(f'${sorted(dep)[len(dep)//2]:,.0f}' if dep else 'n/a')}")

    say("")
    say("  category                                                  opps  exec  units          "
        "CLV              beat     depth")
    say("  " + "-" * 96)
    block("ACCEPTED (reached live)", acc)
    say("  " + "-" * 96)
    groups = collections.Counter()
    for r in rej:
        rs_ = reasons(r)
        groups[(rs_[0][:56] if rs_ else "(no reason recorded)")] += 1
    for name, _n in groups.most_common():
        block(name, [r for r in rej if (reasons(r)[0][:56] if reasons(r) else "(no reason recorded)") == name])

    say("")
    say("  RESTING BIDS ARE NOT MODELLED. Every 'units' figure above is a TAKER price that was")
    say("  actually on the book at the decision. Nothing in the ledger records whether an unfilled")
    say("  resting post would have been crossed to, so no resting fill is assumed anywhere.")
    say("  'n/a' means a required leg is MISSING, not zero: no executable price recorded, no")
    say("  graded result, or no verified same-line Pinnacle close in the cache.")


def lane1_scope(rows):
    """SUPPLY vs PRICE vs GATE, inside Lane 1's actual scope only.

    The question this answers: the bot placed 9 times in the week to Nov 8 and nothing since
    Nov 9. Is that because in-scope candidates stopped arriving (supply), because they arrive and
    the price is gone by the time we decide (speed), or because they arrive at a good price and a
    gate stops them (policy)? Those have completely different answers, and the aggregate funnel
    cannot tell them apart.

    SCOPE is Lane 1's real rule, not every alert: totals UNDERS in NBA/NFL/NCAAF, plus NCAAF
    OVERS. Everything else is out of scope by design and is counted separately so it cannot
    inflate the picture.
    """
    import collections as _c
    say("")
    say("=" * 100)
    say("LANE 1 SCOPE: is the drought SUPPLY, PRICE or a GATE?")
    say("=" * 100)

    # These rows carry league/market/side INSIDE the key, not as fields. r.get("league") is empty
    # on every one of them - a filter on those fields matched 0 of 179 and I read that zero as a
    # supply drought, which it was not. The key is executor.derive_key: SPORT|game|market|side,
    # where market is "total" or "side" (spread and moneyline both collapse to "side") and side is
    # "Under"/"Over" or a team name. So parse the key, and print the vocabulary it yields so the
    # scope count below is checkable against it rather than asserted.
    #
    # NOTE for the CLV column: audit() reads the same absent r.get("league"/"market"/"side") and
    # passes them into close_for, so its 0% join is this same defect and not a namespace mismatch.
    # Not fixed in this pass - flagged, because it changes what that 0% meant.
    def parts(r):
        k = str(r.get("key") or r.get("play_key") or "")
        p = k.split("|")
        if len(p) >= 4:
            return p[0].upper(), p[2].lower(), p[3]
        return (str(r.get("league") or "-").upper(), str(r.get("market") or "-").lower(),
                str(r.get("side") or "-"))

    vocab = _c.Counter()
    for r in rows:
        lg, mk, sd = parts(r)
        vocab[(lg, mk, sd[:20])] += 1
    say("  what the ledger keys actually contain (sport / market / side):")
    for (lg, mk, sd), n in vocab.most_common(16):
        say(f"      {n:4}  {lg:<8} {mk:<8} {sd}")
    if len(vocab) > 16:
        say(f"      ... and {len(vocab) - 16} more combination(s)")
    say("")

    def in_scope(r):
        lg, mk, sd = parts(r)
        sd = sd.lower()
        if mk != "total":
            return False
        if sd.startswith("under") and lg in ("NBA", "NFL", "NCAAF"):
            return True
        return sd.startswith("over") and lg == "NCAAF"

    scope = [r for r in rows if in_scope(r)]
    say(f"  in Lane 1 scope {len(scope)} of {len(rows)} opportunities "
        f"(totals unders NBA/NFL/NCAAF, plus NCAAF overs)")
    if not scope:
        say("  NO in-scope candidate at all in this window. That is a SUPPLY answer: the lane is")
        say("  quiet because nothing it is allowed to bet was alerted, not because of a gate.")
        return

    # SUPPLY: in-scope candidates per ET day, so a stop shows as a date and not an average.
    per_day = _c.Counter()
    for r in scope:
        d = str(r.get("decided_utc") or "")[:10]
        if d:
            per_day[d] += 1
    say("")
    say("  SUPPLY - in-scope candidates by day (decided, UTC date):")
    for d in sorted(per_day):
        say(f"      {d}  {per_day[d]:3}  {'#' * min(per_day[d], 40)}")

    # PRICE vs GATE vs PLACED
    placed = [r for r in scope if (r.get("live_order") or {}).get("status") == "placed"]
    live_ok = [r for r in scope if r.get("live")]
    skip_price = [r for r in scope if str(r.get("verdict")) == "SKIP"
                  and str(r.get("reason") or "").startswith("price:")]
    skip_other = [r for r in scope if str(r.get("verdict")) == "SKIP"
                  and not str(r.get("reason") or "").startswith("price:")]
    gated = [r for r in scope if str(r.get("verdict")) == "WOULD PLACE" and not r.get("live")]
    say("")
    say(f"  PLACED (a real order in the ledger)        {len(placed):4}")
    say(f"  live-eligible                             {len(live_ok):4}")
    say(f"  SKIP on PRICE (nothing at the number)     {len(skip_price):4}   <- speed / the market")
    say(f"  SKIP for another reason                   {len(skip_other):4}")
    say(f"  WOULD PLACE but a GATE stopped it         {len(gated):4}   <- policy")
    if gated:
        g = _c.Counter()
        for r in gated:
            w = r.get("live_why_not")
            for x in (w if isinstance(w, list) else [w] if w else []):
                g[str(x)[:62]] += 1
        say("      gates that stopped an in-scope, priced candidate:")
        for k, n in g.most_common(8):
            say(f"        {n:4}  {k}")

    say("")
    n = len(scope)
    if skip_price and len(skip_price) >= max(1, n // 3):
        say("  READ: a large share of in-scope candidates died on PRICE. The signal is arriving and")
        say("  the number is gone by the time the bot decides - that is a speed/market problem, not")
        say("  a gate. Check decision latency before touching any rule.")
    elif gated and len(gated) >= max(1, n // 3):
        say("  READ: in-scope candidates are arriving AT a gettable price and a GATE is stopping")
        say("  them. That is a policy choice, and the gate names itself above.")
    else:
        say("  READ: neither price nor a gate dominates. The lane is mostly quiet because few")
        say("  in-scope candidates exist - a SUPPLY answer. Look at the per-day counts above.")
    say("")
    say("  Decision latency on in-scope rows (alert -> decision), which bounds how often the price")
    say("  can still be there:")
    lat = sorted(r.get("latency_s") for r in scope if r.get("latency_s") is not None)
    if lat:
        say(f"      n={len(lat)}  median {lat[len(lat)//2]/60:.1f} min  "
            f"min {lat[0]/60:.1f}  max {lat[-1]/60:.1f}")
    else:
        say("      no latency recorded")


def stake_vs_depth(rows):
    """Nov 9-10 in-scope candidates, before and after the 10:52 ET unit change (Peter, Nov 10).

    Frozen decision-time records only. No hindsight, no paid call, no live change.

    THE ONE TRAP, named because it decides what can and cannot be concluded. The ledger's
    'fill_avail' is NOT raw book depth - executor.py:2057 stores r['fillable'], which is
    min(avail, risk) at the stake live at that moment. So:
      fill_partial True   avail was BELOW the stake -> fill_avail IS the exact depth
      fill_partial False  avail was AT OR ABOVE the stake -> depth is known only as '>= stake'
    A full fill at the $200 unit therefore does NOT tell us whether $300 would have filled, and
    no arithmetic here can recover it. Those rows are reported as UNKNOWN rather than assumed.

    Sizing is also not a yes/no gate. MIN_ORDER is $50 and a partial fill rests the remainder
    (executor.py:1546), so a candidate is placeable whenever min(avail, need) >= $50. A larger
    unit against thin depth produces a SMALLER FILL, not a rejection.
    """
    import collections as _cc
    import datetime as _ddt
    from zoneinfo import ZoneInfo as _Z
    et = _Z("America/New_York")
    CUT = _ddt.datetime(2026, 11, 9, 15, 52, 34, tzinfo=_ddt.timezone.utc)   # commit 901dbd9b6
    MIN_ORDER = 50.0

    def need(am, unit):
        return round(unit if am > 0 else unit * abs(am) / 100.0, 2)

    def when(r):
        v = str(r.get("decided_utc") or "")
        try:
            d = _ddt.datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=_ddt.timezone.utc)
        except Exception:
            return None

    def parts(r):
        p = str(r.get("key") or r.get("play_key") or "").split("|")
        return (p[0].upper(), p[2].lower(), p[3]) if len(p) >= 4 else ("-", "-", "-")

    def in_scope(r):
        lg, mk, sd = parts(r)
        sd = sd.lower()
        if mk != "total":
            return False
        return (sd.startswith("under") and lg in ("NBA", "NFL", "NCAAF")) or \
               (sd.startswith("over") and lg == "NCAAF")

    say("")
    say("=" * 118)
    say("STAKE vs DEPTH | Nov 9-10 in-scope candidates | frozen decision records | 0 paid credits")
    say("=" * 118)

    cand = []
    for r in rows:
        t = when(r)
        if not t or t < _ddt.datetime(2026, 11, 9, 5, 0, tzinfo=_ddt.timezone.utc) or not in_scope(r):
            continue
        cand.append((t, r))
    cand.sort()
    if not cand:
        say("  No in-scope candidate recorded on Nov 9-10. Nothing to size against.")
        return

    say(f"  {len(cand)} in-scope candidate(s) on Nov 9-10 "
        f"({sum(1 for t, _ in cand if t < CUT)} before the change, "
        f"{sum(1 for t, _ in cand if t >= CUT)} after)")
    say("")
    hdr = (f"  {'ET time':<12} {'U':<1} {'game':<30} {'odds':>6} {'need200':>8} {'need300':>8} "
           f"{'depth':>11} {'q200':>5} {'q300':>5} {'sizing?':<8} verdict / reason")
    say(hdr)
    say("  " + "-" * 114)
    sizing_blocked = 0
    unknown = 0
    for t, r in cand:
        lg, mk, sd = parts(r)
        am = r.get("fill_price_after_fee")
        av = r.get("fill_avail")
        par = r.get("fill_partial")
        n200 = need(am, 200.0) if am is not None else None
        n300 = need(am, 300.0) if am is not None else None
        game = str(str(r.get("key") or "").split("|")[1] if "|" in str(r.get("key") or "") else "")[:30]
        u = "3" if t >= CUT else "2"
        if am is None or av is None:
            q2 = q3 = "?"
            dep = "no record"
            unknown += 1
        elif par:
            dep = f"${av:,.0f} exact"
            q2 = "Y" if min(av, n200) >= MIN_ORDER else "N"
            q3 = "Y" if min(av, n300) >= MIN_ORDER else "N"
        else:
            dep = f">=${av:,.0f}"
            # avail >= the then-stake, and the then-stake exceeds MIN_ORDER, so min(avail, need)
            # clears $50 at EITHER unit. Decidable despite the censoring.
            q2 = "Y" if av >= MIN_ORDER else "?"
            q3 = "Y" if av >= MIN_ORDER else "?"
        blocked = (q2 == "Y" and q3 == "N")
        if blocked:
            sizing_blocked += 1
        why = str(r.get("reason") or "")
        if not why:
            w = r.get("live_why_not")
            why = "; ".join(str(x) for x in (w if isinstance(w, list) else [w] if w else []))
        say(f"  {t.astimezone(et).strftime('%m-%d %H:%M'):<12} {u:<1} {game:<30} "
            f"{(f'{am:+.0f}' if am is not None else '-'):>6} "
            f"{(f'${n200:,.0f}' if n200 else '-'):>8} {(f'${n300:,.0f}' if n300 else '-'):>8} "
            f"{dep:>11} {q2:>5} {q3:>5} {('YES' if blocked else 'no'):<8} "
            f"{str(r.get('verdict') or '')} {why[:46]}")

    say("")
    say(f"  candidates where the $300 unit alone caused the rejection: {sizing_blocked}")
    if unknown:
        say(f"  candidates with no frozen price or depth record: {unknown} (reported, not inferred)")
    say("")
    if sizing_blocked == 0:
        say("  VERDICT ON SIZING: not the cause. Under MIN_ORDER $50 with the remainder rested, a")
        say("  bigger unit against the same depth yields a smaller fill, never a refusal, and no")
        say("  candidate above flips from placeable at $200 to unplaceable at $300.")

    # ---- item 5: the Nov 2-8 decline, from the same frozen rows ----
    say("")
    say("  Nov 2-8 decline - in-scope supply, placements and the leading block, by ET day:")
    say(f"    {'day':<12} {'in scope':>8} {'placed':>7}  leading reason among the rest")
    def pl(r):
        los = [r.get("live_order") or {}, r.get("live_rest") or {}]
        los += [x or {} for x in (r.get("live_more") or [])]
        return any(l.get("status") == "placed" and l.get("order_id") for l in los)
    byday = {}
    for r in rows:
        t = when(r)
        if not t or not in_scope(r):
            continue
        byday.setdefault(t.astimezone(et).strftime("%Y-%m-%d"), []).append(r)
    for d in sorted(byday):
        rs = byday[d]
        c = _cc.Counter()
        for r in rs:
            if pl(r):
                continue
            w = r.get("live_why_not")
            lst = [str(x) for x in (w if isinstance(w, list) else [w] if w else [])]
            c[(lst[0] if lst else str(r.get("reason") or "(none)"))[:52]] += 1
        top = c.most_common(1)
        say(f"    {d:<12} {len(rs):>8} {sum(1 for r in rs if pl(r)):>7}  "
            f"{(top[0][0] + f' x{top[0][1]}') if top else '-'}")
    say("")
    say("=" * 118)


def _qof(r):
    """(league, game, market, side, line) for a ledger row, from the KEY plus the stored line.

    The row carries no league/market/side field - that was the defect behind the 0% CLV join. The
    key is executor.derive_key: SPORT|game|market|side. The line is on the row as fill_line (the
    line actually taken) or alert_line. close_for's first guard is parsed(bet), so the bet must be
    real TEXT with its number - passing None is what produced 'bet text not parsed' before.
    """
    p = str(r.get("key") or r.get("play_key") or "").split("|")
    if len(p) < 4:
        return None
    lg, game, mk, sd = p[0].upper(), p[1], p[2].lower(), p[3]
    ln = r.get("fill_line")
    if ln is None:
        ln = r.get("alert_line")
    if mk != "total" or ln is None:
        return None          # totals only: the key collapses spread and moneyline into "side"
    try:
        bet = f"{sd.title()} {float(ln):g}"
    except Exception:
        return None
    return lg, game, mk, bet, float(ln)


def novig_restriction_clv(rows):
    """Does 'priced on Novig, not ProphetX' reject profitable opportunities? (Peter, Nov 10.)

    The only authorized question. Read-only, frozen decision records, no paid call, no live change.

    WHAT IS BEING PRICED. These opportunities were never placed, so there is no fill to price. The
    executable price is the one that was actually on the book at the decision, after fee
    (fill_price_after_fee) - the same basis every other executable number in this system uses. CLV
    is that price against a VERIFIED same-line Pinnacle close; an unverified or different-line
    close is dropped, never substituted.
    """
    import collections as _c
    import statistics as _st
    import clv_ledger as _cl
    import clv_std as _cs
    import hist_cache as _hc
    from datetime import datetime as _dtd, timezone as _tzd
    say("")
    say("=" * 100)
    say("NOVIG-NOT-PROPHETX: does the restriction reject profitable opportunities?")
    say("=" * 100)

    def blocked(r):
        w = r.get("live_why_not")
        lst = [str(x) for x in (w if isinstance(w, list) else [w] if w else [])]
        hit = [x for x in lst if "Novig, not ProphetX" in x]
        return (bool(hit), len(lst))

    pop = []
    only = 0
    for r in rows:
        hit, n = blocked(r)
        if not hit:
            continue
        q = _qof(r)
        if q is None:
            continue
        if n == 1:
            only += 1
        pop.append((r, q))
    say(f"  {len(pop)} totals opportunity(ies) blocked by the restriction "
        f"({only} with NO other blocking reason)")
    if not pop:
        say("  Nothing to price. Not a verdict on the restriction - an empty population.")
        return

    st = {"fixtures": {}}
    try:
        import tracker_build as _tb
        st["fixtures"] = dict((_tb.dec(json.load(open(_cl.STATE))).get("fixtures") or {}))
    except Exception as e:
        say(f"  fixture cache UNAVAILABLE ({type(e).__name__}) - cannot price. STOP.")
        return
    try:
        import tracker_build as _tb2
        toks = _tb2.toks
    except Exception:
        say("  tracker_build.toks unavailable - cannot match fixtures. STOP.")
        return
    mkmap = {}
    try:
        mkmap = _cl.load_markets(st, _dtd.now(_tzd.utc))
    except Exception:
        pass

    def fixture_for(game):
        """Same token test bot_match uses in production: >=2 shared words with the fixture sides."""
        g = toks(game)
        for fid, f in (st.get("fixtures") or {}).items():
            if len(g & (toks(f.get("p1") or "") | toks(f.get("p2") or ""))) >= 2:
                return fid, f
        return None, None

    out, lost = [], _c.Counter()
    for r, (lg, game, mk, bet, ln) in pop:
        am = r.get("fill_price_after_fee")
        if am is None:
            lost["no executable price recorded at the decision"] += 1
            continue
        fid, f = fixture_for(game)
        if not fid:
            lost["no fixture matched the game text"] += 1
            continue
        if not os.path.exists(_hc._path(fid, "pinnacle")):
            lost["no stored Pinnacle history for the fixture"] += 1
            continue
        start = _cl.tp(f.get("start"))
        if not start:
            lost["fixture has no start time"] += 1
            continue
        try:
            h = _hc.get_hist(fid, ["pinnacle"], start)
            c, why = _cl.close_for({"bet": bet, "league": lg, "market": mk,
                                    "game": f.get("game"), "game_start": f.get("start")},
                                   f, _cl.book_markets(h, "pinnacle"), mkmap, start, lg)
        except Exception as e:
            lost[f"close_for raised {type(e).__name__}"] += 1
            continue
        if not c:
            lost[f"no close: {str(why)[:44]}"] += 1
            continue
        if not _cs.close_verified(c.get("how")):
            lost["close present but NOT verified (dropped, never substituted)"] += 1
            continue
        dec = 1 + (am / 100.0 if am > 0 else 100.0 / abs(am))
        try:
            pct = _cs.net_clv(c["p"], dec, _cs.canon(r.get("fill_book")), maker=False, league=lg)
        except Exception as e:
            lost[f"net_clv raised {type(e).__name__}"] += 1
            continue
        if pct is None:
            lost["net_clv returned None"] += 1
            continue
        out.append((str(r.get("decided_utc") or ""), pct))

    say("")
    if lost:
        say("  could not be priced (reported, not counted as zero):")
        for k, n in lost.most_common(8):
            say(f"      {n:4}  {k}")
    say("")
    if not out:
        say(f"  PRICED: 0 of {len(pop)}. NO VERDICT. The restriction is neither cleared nor")
        say("  convicted - there is no measurement here, and the reasons above say why.")
        say("  Per Peter Nov 10, nothing gets built on this until it shows positive executable CLV,")
        say("  and it cannot show anything until the missing leg above is fixed.")
        return

    out.sort()
    v = [p for _, p in out]
    n = len(v)
    mean = sum(v) / n
    sd = _st.stdev(v) if n > 1 else 0.0
    se = sd / (n ** 0.5) if n > 1 else 0.0
    beat = sum(1 for x in v if x > 0) / n * 100
    say(f"  PRICED {n} of {len(pop)} - executable price at the decision vs verified Pinnacle close")
    say(f"      mean net CLV   {mean:+.2f}%")
    say(f"      sd {sd:.2f}%   SE {se:.2f}%   95% range "
        f"{mean - 1.96 * se:+.2f}% .. {mean + 1.96 * se:+.2f}%")
    say(f"      beat the close {beat:.0f}%  ({sum(1 for x in v if x > 0)} of {n})")
    if n >= 4:
        h = n // 2
        a, b = v[:h], v[h:]
        say(f"      first half  n={len(a)}  mean {sum(a) / len(a):+.2f}%")
        say(f"      second half n={len(b)}  mean {sum(b) / len(b):+.2f}%")
    say("")
    lo = mean - 1.96 * se
    if n < 30:
        say(f"  VERDICT: n={n} is too small to decide. The 95% range above spans "
            f"{lo:+.2f}% to {mean + 1.96 * se:+.2f}%,")
        say("  so this neither clears nor convicts the restriction. No change on this.")
    elif lo > 0:
        say("  VERDICT: positive executable CLV with the 95% range entirely above zero. This is the")
        say("  evidence Peter named as the precondition. It still needs a both-halves check and his")
        say("  yes before any live change.")
    else:
        say("  VERDICT: not positive. The 95% range includes zero or sits below it, so the")
        say("  restriction is not demonstrably rejecting profitable opportunities. Keep it, and")
        say("  per Peter Nov 10 nothing further gets built on this.")
    say("=" * 100)


def main():
    since = (__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
             - __import__("datetime").timedelta(days=DAYS)).strftime("%d-%b-%Y")
    say(f"RESTING-DEPTH MEASUREMENT | last {DAYS} days | read-only, 0 credits")
    say("Question: how often did BOTH Novig and Kalshi lack the exact alert line?\n")

    rows, mails = [], 0
    M = ex.imap_open()
    try:
        for s in SUBJECTS:
            r, n = ledger_rows(M, s, since)
            rows.extend(r)
            mails += n
    finally:
        ex.imap_close(M)
    say(f"read {mails} executor email(s), {len(rows)} ledger row(s)")

    # One row per play KEY, newest wins: the executor re-reports a play every run until it is
    # decided, so counting raw rows would weight a long-lived play dozens of times and the
    # frequency would be meaningless.
    # Keep the row that records a PLACEMENT, not merely the last row for the key. Last-wins let a
    # later candidate row for the same play overwrite the one holding the order, which is how this
    # report came to show 12 placements against 28 in the bot's own mail. A placement is also
    # recorded in live_rest or live_more, not live_order alone - tracker_build.bot_keys has always
    # read all three.
    def _placed_any(r):
        los = [r.get("live_order") or {}, r.get("live_rest") or {}]
        los += [x or {} for x in (r.get("live_more") or [])]
        return any(lo.get("status") == "placed" and lo.get("order_id") for lo in los)

    seen = {}
    for r in rows:
        k = r.get("key") or r.get("play_key")
        if not k:
            continue
        cur = seen.get(k)
        if cur is None or (_placed_any(r) and not _placed_any(cur)):
            seen[k] = r
    say(f"{len(seen)} distinct play(s) after de-duplicating by key\n")

    # THE FUNNEL, which is the question underneath the depth question. On Nov 10 the executor's
    # own subject lines read "0 placed, 0 would go live, 2 would bet" - plays were being FOUND and
    # none were reaching live. Resting is strictly downstream of phase-1 live eligibility
    # (rest_wanted returns False unless the play is live-eligible or was skipped on price), so a
    # zero in the depth count below may say nothing about resting and everything about the gate
    # above it. Measuring one without the other invites the wrong fix.
    say("=" * 78)
    say("FUNNEL: how far does a play actually get?")
    say("=" * 78)
    verdicts = collections.Counter(r.get("verdict") or "(none)" for r in seen.values())
    for k, n in verdicts.most_common():
        say(f"  verdict {k:<14} {n:4}")
    live_ok = [r for r in seen.values() if r.get("live")]
    say(f"\n  live-eligible (live=true)      {len(live_ok):4}  of {len(seen)}")
    ordered = [r for r in seen.values() if (r.get("live_order") or {}).get("status")]
    placed_o = [r for r in ordered if (r.get("live_order") or {}).get("status") == "placed"]
    say(f"  reached a live ORDER attempt   {len(ordered):4}")
    say(f"  order status 'placed'          {len(placed_o):4}")
    if not live_ok:
        say("\n  NOTHING reached live eligibility in this window. Whatever blocks it sits ABOVE")
        say("  resting, so the resting count below cannot be read as a fact about resting.")
    whys = collections.Counter()
    for r in seen.values():
        w = r.get("live_why_not")
        for item in (w if isinstance(w, list) else [w] if w else []):
            whys[str(item)[:72]] += 1
    if whys:
        say("\n  why not live (top reasons):")
        for k, n in whys.most_common(10):
            say(f"      {n:4}  {k}")
    say("")

    audit(list(seen.values()))
    lane1_scope(list(seen.values()))
    stake_vs_depth(list(seen.values()))
    novig_restriction_clv(list(seen.values()))

    attempted = [r for r in seen.values() if (r.get("live_rest") or {}).get("status")]
    placed = [r for r in attempted if (r.get("live_rest") or {}).get("status") == "placed"]
    refused = [r for r in attempted if (r.get("live_rest") or {}).get("status") == "refused"]

    say("=" * 78)
    say("RESTING")
    say("=" * 78)
    say(f"resting ATTEMPTED on {len(attempted)} play(s): {len(placed)} placed, {len(refused)} refused")
    if not attempted:
        say("")
        if not live_ok:
            say("Zero resting attempts, AND zero plays reached live eligibility. So this zero is")
            say("explained by the funnel above, not by the resting lane or by REST_BOOKS. Adding a")
            say("third resting venue would change nothing, and neither would changing the chain -")
            say("the binding constraint is upstream. Do not 'fix' resting on the strength of this.")
        else:
            # THE FILL CHECK, missing from the first version and the reason its verdict was wrong.
            # It concluded "the resting lane is not firing, worth a look" from live-eligibility
            # alone. But resting is meant to fire only when nothing filled AT the number - so if
            # every live order filled, rest_wanted correctly never fires and there is nothing to
            # look at. On the Nov 10 run that was exactly the case: 3 plays reached live, all 3
            # placed, so a zero here is the design working, not a lane that is broken. Reporting it
            # as suspicious would have sent someone hunting a bug that does not exist.
            filled = [r for r in ordered
                      if (r.get("live_order") or {}).get("status") == "placed"
                      and ((r.get("live_order") or {}).get("filled_stake") or 0) > 0]
            say(f"Zero resting attempts, and {len(live_ok)} play(s) reached live eligibility:")
            say(f"  {len(ordered)} reached an order attempt, {len(placed_o)} placed, "
                f"{len(filled)} with a recorded fill.")
            if len(placed_o) and len(placed_o) == len(ordered):
                say("")
                say("Every live order that was attempted was PLACED. Resting exists for the case where")
                say("nothing filled at the number, so it correctly never fired. This zero is the design")
                say("working - not a resting bug, and not an argument about REST_BOOKS either way.")
            else:
                say("")
                say("Some live attempts did NOT place, yet resting still never fired. THAT is a fact")
                say("about the resting lane and is worth a look at rest_wanted's conditions.")
        return

    # The question: among refusals, how many were BOTH books lacking the exact line - the only
    # case a third venue could have rescued? A refusal for any other reason (under the minimum,
    # a guard, an ambiguous market) would not have been helped by adding Polymarket.
    both, one_only, other = 0, 0, collections.Counter()
    for r in refused:
        why = ((r.get("live_rest") or {}).get("reason") or "")
        nov = "Novig: no exact-line market" in why
        kal = "Kalshi: no exact-line market" in why
        if nov and kal:
            both += 1
        elif nov or kal:
            one_only += 1
        else:
            other[why[:70] or "(no reason recorded)"] += 1

    say("")
    say("=" * 78)
    say("WOULD A THIRD RESTING VENUE HAVE HELPED?")
    say("=" * 78)
    say(f"  both books lacked the exact line   {both:4}   <- only these could a 3rd venue rescue")
    say(f"  only one book lacked it            {one_only:4}   (the other could already rest)")
    say(f"  refused for some other reason      {sum(other.values()):4}   (a 3rd venue changes nothing)")
    for k, n in other.most_common(6):
        say(f"        {n:3}  {k}")

    pct = 100.0 * both / max(len(attempted), 1)
    say("")
    say(f"So {both} of {len(attempted)} resting attempts ({pct:.1f}%) are the case that argues for a "
        f"third venue.")
    say("")
    # The threshold is stated, not implied, so the decision does not drift to whoever reads it.
    if both == 0:
        say("VERDICT: zero. Adding Polymarket US to REST_BOOKS would have changed NOTHING in this")
        say("  window, while adding the one venue whose expiry does not work and whose bids need an")
        say("  active cancel. Leave the chain at (novig, kalshi).")
    elif pct < 5:
        say("VERDICT: marginal. A third venue would have rescued under 5% of attempts - not worth")
        say("  taking on the only venue where a failed cancel leaves a bid resting all day.")
        say("  Leave the chain at (novig, kalshi).")
    else:
        say(f"VERDICT: {pct:.1f}% is material. Worth Peter weighing the depth gain against the")
        say("  cancel risk - note that Polymarket would be entering as a TAKER (-116.8 at a -110")
        say("  screen, worst of the three), so it only helps where resting is otherwise impossible,")
        say("  never where it is merely cheaper.")
    say("")
    say("Counts only. No prices, stakes, balances or order ids in this output.")


if __name__ == "__main__":
    sys.exit(main())

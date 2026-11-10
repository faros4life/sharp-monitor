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

    def clv_of(r):
        """(clv_pct, beat) at the EXECUTABLE price against a verified same-line Pinnacle close.
        None where any leg is missing - never estimated, never substituted."""
        am = r.get("fill_price_after_fee")
        if am is None:
            return None, None
        try:
            fid = _cl.find_fixture(st, {"bet": r.get("side") or r.get("game"),
                                        "league": r.get("league"), "game": r.get("game"),
                                        "teams": _nn.teams_of({"league": r.get("league"),
                                                               "teams": None}),
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
            c, _why = _cl.close_for({"bet": r.get("side"), "league": r.get("league"),
                                     "market": r.get("market")}, f,
                                    _cl.book_markets(h, "pinnacle"), mkmap, start, r.get("league"))
        except Exception:
            return None, None
        if not c or not _cs.close_verified(c.get("how")):
            return None, None
        dec = 1 + (am / 100.0 if am > 0 else 100.0 / abs(am))
        try:
            v = _cs.canon(r.get("fill_book"))
            pct = _cs.net_clv(c["p"], dec, v, maker=False, league=r.get("league"))
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

    def in_scope(r):
        lg = str(r.get("league") or "").upper()
        mk = str(r.get("market") or "").lower()
        sd = str(r.get("side") or "").upper()
        if mk != "total":
            return False
        if sd == "UNDER" and lg in ("NBA", "NFL", "NCAAF"):
            return True
        return sd == "OVER" and lg == "NCAAF"

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
    seen = {}
    for r in rows:
        k = r.get("key") or r.get("play_key")
        if k:
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

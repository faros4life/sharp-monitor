#!/usr/bin/env python3
"""
MY PLAYS, WITH CLV STATUS PER PLAY (Peter, Nov 11: "record my plays today and confirm the clv",
"do it right before the game starts on all", "go to GitHub, it has all my plays").

READ-ONLY. No bet, no order, no rule change, no switch change. Writes nothing back.

WHY THIS EXISTS AND executed_clv.py DOES NOT ANSWER IT. executed_clv reports one AGGREGATE over
GRADED bot fills. Peter asked for the per-play record of TODAY - and today's plays are not graded,
because the games have not been played. An aggregate over a sample of zero is the right answer to
the question executed_clv asks and the wrong answer to this one.

WHAT IT REUSES RATHER THAN RE-DERIVES, deliberately:
  clv_ledger.find_fixture   the two-token matcher - a hand-rolled matcher produced a confidently
                            wrong CLV of -7.30% on Nov 10 and is the reason this imports instead
  clv_ledger.close_for      which Pinnacle market is the SAME line as the bet
  clv_std.close_verified    the official standard: only "own line" or "moneyline" counts
  clv_std.net_clv           the headline formula, 100*(p*net_dec - 1)
  executed_clv.net_of       which venues store MONEY with the fee inside and which store a QUOTE
                            with the fee still to come. Novig and Polymarket US are net already;
                            ProphetX is a quote and takes 2% of net gains at settlement. Getting
                            this backwards is what made the Polymarket fee wrong on 25 Oct.

CLV BEFORE THE CLOSE DOES NOT EXIST. The benchmark IS the closing line, so a play whose game has
not finished can only be reported as PENDING - never as a number. That is the honest shape of the
answer to "confirm the clv right before the game starts": the RECORD is taken now, at the price
actually filled, and the CLV is certified once Pinnacle has closed. Every status below says which
of the two a play is in, and why.

MONEY. The repo is public. say() carries counts, lines, prices and percentages; every dollar
figure goes through priv() to the private email only, the same split executed_clv uses after the
Nov 9 run that put 28 dollar figures into a public log.
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import executed_clv as xc
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
TSTATE = "tracker/state.enc"
DAY = (os.environ.get("MP_DAY") or "").strip()          # ET day, YYYY-MM-DD; blank = today ET
BACK = int(os.environ.get("MP_BACK") or "0")            # also include this many earlier ET days
CACHE_ONLY = (os.environ.get("MP_CACHE_ONLY") or "0") != "0"

L = []
MONEY = re.compile(r"\$\s*[+-]?[\d,]+(?:\.\d+)?")


def say(t=""):
    """Email body AND the public log - never a dollar amount. The guard is the same one
    executed_clv uses: a line carrying money routes itself away from the log rather than relying
    on whoever edits this file next to remember that the repo is public."""
    L.append(t)
    if MONEY.search(str(t)):
        print("  [line withheld from the public log: carries a dollar amount]")
        return
    print(t)


def priv(t=""):
    """Email body ONLY."""
    L.append(t)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def days_wanted():
    if DAY:
        base = datetime.strptime(DAY, "%Y-%m-%d").date()
    else:
        base = datetime.now(timezone.utc).astimezone(ET).date()
    return {(base - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(BACK + 1)}


def row_day(b):
    """The ET day to file a play under.

    game_start first: a play belongs to the day its GAME is on, which is the day Peter means by
    "today". The fallbacks exist because an ungraded row may not carry a start yet, and a row with
    no date at all must be reported as undated rather than silently filed under today."""
    for f in ("game_start", "placed", "first_seen", "date", "settled"):
        v = b.get(f)
        if not v:
            continue
        d = cl.tp(v)
        if d:
            return d.astimezone(ET).strftime("%Y-%m-%d"), f
        s = str(v)[:10]
        if len(s) == 10 and s[4] == "-":
            return s, f
    return None, None


def clv_for(st, b, mkmap, now):
    """(status, clv_pct, detail). status is CERTIFIED, PENDING, or a one-line reason it cannot be.

    This is executed_clv's own gate order, kept in the same sequence so the two can never report
    different reasons for the same play."""
    lg = b.get("league")
    gs = (b.get("game_start") or b.get("settled") or b.get("placed") or b.get("first_seen"))
    q = {"bet": b.get("bet"), "league": lg, "game": b.get("game"), "teams": b.get("teams"),
         "game_start": gs, "book": b.get("book"), "_start_was_given": bool(b.get("game_start"))}

    fid = cl.find_fixture(st, q)
    if not fid:
        g, _, detail = xc.why_no_fixture(st, q, lg)
        return "no fixture", None, g
    f = st["fixtures"][fid]
    start = cl.tp(f.get("start")) or cl.tp(gs)
    if not start:
        return "no game start", None, ""
    if now - start < hc.FINAL_AFTER:
        mins = (start - now).total_seconds() / 60.0
        when = (f"starts in {mins:.0f} min" if mins > 0
                else f"started {-mins:.0f} min ago, not final yet")
        return "PENDING", None, when
    if CACHE_ONLY and not os.path.exists(hc._path(fid, "pinnacle")):
        return "close not in cache", None, "would need a history download"
    h = hc.get_hist(fid, ["pinnacle"], start)
    if isinstance(h, dict) and h.get("_error"):
        return "history error", None, str(h.get("_error"))[:40]
    c, why = cl.close_for(q, f, cl.book_markets(h, "pinnacle"), mkmap, start, lg)
    if not c:
        return "no same-line close", None, str(why)[:46]
    if not cs.close_verified(c.get("how")):
        return "close not certifiable", None, f"how={str(c.get('how'))[:34]}"

    bk = cs.canon(b.get("book"))
    am = num(b.get("price"))
    if am is None:
        return "no fill price", None, ""
    raw = cl.am_to_dec(am)
    try:
        nd = xc.net_of(bk, raw, lg, False)
    except cs.UnknownVenue:
        return "venue not in registry", None, bk
    return "CERTIFIED", 100 * (c["p"] * nd - 1), f"close p={c['p']:.4f} ({c.get('how')})"


def main():
    now = datetime.now(timezone.utc)
    want = days_wanted()
    say("MY PLAYS - the record, and the CLV status of each")
    say(f"generated {now.astimezone(ET):%Y-%m-%d %H:%M} ET | ET day(s): {', '.join(sorted(want))}")
    say(f"CLV: {cs.FEE_MODEL} | certified = verified same-line Pinnacle close, net of fees")
    say("read-only: no bet, no order, no rule or switch change" +
        (" | CACHE ONLY, zero credits" if CACHE_ONLY else ""))
    say("=" * 96)

    try:
        tstate = tb.dec(json.load(open(TSTATE)))
    except Exception as e:
        say(f"  tracker state unreadable ({type(e).__name__}: {str(e)[:60]}) - nothing to report.")
        return 1
    raw = (tstate or {}).get("bets")
    allrows = list(raw.values()) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])

    rows, undated = [], 0
    for b in allrows:
        d, src = row_day(b)
        if d is None:
            undated += 1
            continue
        if d in want:
            b = dict(b)
            b["_day"], b["_dayfrom"] = d, src
            rows.append(b)
    rows.sort(key=lambda b: (b["_day"], str(b.get("game") or "")))

    say(f"  {len(allrows)} tracker row(s) in all | {len(rows)} on the requested day(s)"
        + (f" | {undated} carry no usable date" if undated else ""))
    if not rows:
        say("")
        say("  No play is filed under that day. If a bet was placed and is missing here, the")
        say("  tracker has not ingested it yet rather than the bet having been lost.")
        try:
            import executor as ex
            ex.send("Bets MY PLAYS (none found)", "\n".join(L))
        except Exception:
            pass
        return 0

    by_src = Counter(str(b.get("source") or "?") for b in rows)
    by_bk = Counter(cs.canon(b.get("book")) if b.get("book") else "?" for b in rows)
    say(f"  by source: {', '.join(f'{k} {v}' for k, v in by_src.most_common())}")
    say(f"  by venue:  {', '.join(f'{k} {v}' for k, v in by_bk.most_common())}")

    # The fixture/market data this CLV depends on, and how old it is. A stale cache is the usual
    # reason a play reads "no fixture", and that is a MEASUREMENT fault, never a betting fault -
    # so the age is printed next to the result rather than left for someone to wonder about.
    #
    # Loaded exactly the way executed_clv loads it, including the CACHE_ONLY branch around
    # load_markets(): that function BILLS when clv/markets.json is over 7 days old by falling
    # through to api("/markets", True), which is how plimit-level spent 5 unapproved credits on
    # 6 Nov. "Zero credits" must not rest on the file happening to be fresh.
    st = {"fixtures": {}, "fx_last": {}}
    try:
        prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(prev.get("fixtures") or {})
        st["fx_last"] = dict(prev.get("fx_last") or {})
    except Exception as e:
        say(f"  fixture cache unavailable ({type(e).__name__}) - every play will read 'no fixture'")
    if CACHE_ONLY:
        try:
            _mk = json.load(open(cl.MKFILE))
            mkmap = _mk.get("m") or {}
            _age = (now - cl.tp(_mk["fetched"])).days
            mknote = f"{len(mkmap)} entries, {_age}d old, from disk - no paid call"
        except Exception as e:
            mkmap, mknote = {}, f"unavailable ({type(e).__name__}) - not bought"
    else:
        mkmap = cl.load_markets(st, now)
        mknote = f"{len(mkmap or {})} entries"
    fx = st.get("fixtures") or {}
    newest = max((cl.tp(f.get("start")) for f in fx.values() if cl.tp(f.get("start"))),
                 default=None)
    say(f"  fixture cache: {len(fx)} fixture(s)"
        + (f", latest start {newest.astimezone(ET):%Y-%m-%d %H:%M} ET" if newest else "")
        + f" | market map: {mknote}")

    say("")
    say("=" * 96)
    say("THE PLAYS")
    say("=" * 96)
    say(f"  {'day':<10} {'lg':<6} {'game':<34} {'bet':<22} {'venue':<11} {'px':>6} {'res':>4}")
    say("  " + "-" * 92)
    out, stat = [], Counter()
    for b in rows:
        status, clv, detail = clv_for(st, b, mkmap, now)
        stat[status] += 1
        am = num(b.get("price"))
        say(f"  {b['_day']:<10} {str(b.get('league') or '?'):<6} "
            f"{str(b.get('game') or '?')[:34]:<34} {str(b.get('bet') or '?')[:22]:<22} "
            f"{(cs.canon(b.get('book')) if b.get('book') else '?')[:11]:<11} "
            f"{(f'{am:+.0f}' if am is not None else '?'):>6} "
            f"{str(b.get('result') or '-'):>4}")
        line = (f"       -> {status}" + (f"  CLV {clv:+.2f}%" if clv is not None else "")
                + (f"  [{detail}]" if detail else ""))
        say(line)
        out.append({"day": b["_day"], "league": b.get("league"), "game": b.get("game"),
                    "bet": b.get("bet"), "venue": cs.canon(b.get("book")) if b.get("book") else "",
                    "american": am, "result": b.get("result"), "clv_status": status,
                    "clv_pct": (None if clv is None else round(clv, 3)),
                    "detail": detail, "stake": num(b.get("stake")),
                    "fee_model": cs.FEE_MODEL})

    # DUPLICATE OR LEGS - this must be settled before any per-play average is quoted.
    # The Nov 11 record showed one Lakers play as 10 identical rows. Ten legs of one play and ten
    # copies of one row look the same in a list and mean opposite things: the first is one position
    # filled in pieces, the second is a measurement fault that would weight that play 10x in any
    # average. The distinguishing evidence is whether the rows carry DIFFERENT order ids or
    # different first-seen times. Printed as counts, never as stakes.
    groups = {}
    for b in rows:
        k = (str(b.get("game") or ""), str(b.get("bet") or ""),
             cs.canon(b.get("book")) if b.get("book") else "", num(b.get("price")))
        groups.setdefault(k, []).append(b)
    dup = {k: v for k, v in groups.items() if len(v) > 1}
    if dup:
        say("")
        say("=" * 96)
        say("REPEATED ROWS - legs of one play, or duplicates?")
        say("=" * 96)
        for (g, bet, bk, px), v in sorted(dup.items(), key=lambda x: -len(x[1])):
            oid = {str(b.get("order_id") or b.get("oid") or "") for b in v} - {""}
            fs = {str(b.get("first_seen") or b.get("placed") or "")[:19] for b in v} - {""}
            key = {str(b.get("key") or b.get("play_key") or "") for b in v} - {""}
            verdict = ("separate legs - distinct order ids" if len(oid) == len(v) and oid else
                       "separate fills - distinct timestamps" if len(fs) == len(v) and fs else
                       f"UNRESOLVED - {len(oid)} order id(s), {len(fs)} timestamp(s) for {len(v)} rows")
            say(f"  {len(v):3d}x  {g[:36]:<36} {bet[:18]:<18} {bk[:10]:<10} "
                f"{(f'{px:+.0f}' if px is not None else '?'):>6}")
            say(f"        order ids {len(oid)} | distinct timestamps {len(fs)} | "
                f"tracker keys {len(key)}  ->  {verdict}")
        say("")
        say("  Until a group reads 'separate legs' or 'separate fills', no average over these")
        say("  plays is quoted: duplicates would weight one play by its row count.")

    say("")
    say("=" * 96)
    say("STATUS ROLL-UP")
    say("=" * 96)
    for k, n in stat.most_common():
        say(f"  {k:<24} {n:4d}")
    cert = [r for r in out if r["clv_status"] == "CERTIFIED" and r["clv_pct"] is not None]
    if cert:
        m = sum(r["clv_pct"] for r in cert) / len(cert)
        beat = sum(1 for r in cert if r["clv_pct"] > 0)
        say("")
        say(f"  certified plays {len(cert)} | mean CLV {m:+.2f}% | beat the close {beat}/{len(cert)}")
        say("  This is a same-day figure on a handful of plays, not a verdict on any strategy.")
    if stat.get("PENDING"):
        say("")
        say(f"  {stat['PENDING']} play(s) PENDING: their games are not final, so Pinnacle has not")
        say("  closed and no CLV exists for them yet. Their prices are recorded above; re-run this")
        say("  after the games finish and they certify.")

    # dollars, private email only
    stk = [r["stake"] for r in out if r["stake"] is not None]
    if stk:
        priv("")
        priv(f"  staked across {len(stk)} play(s): ${sum(stk):,.2f}"
             f" | largest ${max(stk):,.2f} | smallest ${min(stk):,.2f}")

    say("")
    say("=" * 96)
    try:
        import executor as ex
        ex.send(f"Bets MY PLAYS {min(want)}"
                + (f"..{max(want)}" if len(want) > 1 else "")
                + f" ({len(rows)} plays, {stat.get('CERTIFIED', 0)} certified)", "\n".join(L))
        print("report emailed")
    except SystemExit as e:
        print(f"email skipped (credentials: {str(e)[:50]})")
    except Exception as e:
        print(f"email skipped ({type(e).__name__}: {str(e)[:50]})")
    try:
        with open("my_plays.json", "w") as f:
            json.dump({"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "plays": out}, f, indent=1)
    except Exception:
        pass
    print(f"my plays: {len(rows)} on {sorted(want)}, "
          + ", ".join(f"{k}={v}" for k, v in stat.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

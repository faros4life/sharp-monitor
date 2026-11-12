#!/usr/bin/env python3
"""EXECUTED CLV - Lane 1 filled bets, priced at what the books actually filled (Peter, item 2:
"Books fill").

WHAT WAS MISSING. clv_report.py says it plainly: "Actual Executed CLV UNAVAILABLE - no executed-fill
record is wired to this population. Needs the venues' own fill histories; not inferred from a
displayed price." This wires them.

WHY THE ALERT EMAILS CANNOT ANSWER IT. A "Bets LIVE" email is written when the order is SENT, so a
resting bid that fills a minute later is recorded as "[PLACED: $0.00 filled, asked $91.80]" with
filled_stake null. 24 such emails carry a non-zero placed amount against 26 placed events. Counting
fills from the alert stream therefore cannot be right at any sample size - it is not a coverage
problem that more days would fix. The books' own records are the only authoritative fill prices, and
the tracker already holds them.

HOW THE JOIN WORKS - all of it already existed, none of it is new here:
  * the books' own fill records   tracker_build.read_novig / read_prophetx / read_kalshi / read_pmus
  * the Lane 1 link              tracker_build.bot_keys() lifts the bot's play keys out of its own
                                 "Bets LIVE" emails; bot_match() ties a book's fill row to them, and
                                 the result is stored on the row as source == "bot"
  * the verified Pinnacle close  clv_ledger.find_fixture / close_for, same path clv_report uses
  * the fee                      clv_std, fee model below
This script adds exactly one thing: the CLV of the price the book really filled.

THE FEE BASIS, WHICH IS THE ONE DECISION THAT CAN MAKE EVERY NUMBER WRONG. The tracker does not
store a quoted price; it stores the MONEY. Novig and Polymarket US rows carry
price = p_to_american(cost / payout) - real dollars in over real dollars out - so any fee charged at
the trade is ALREADY inside that price and applying a fee again would double-count it. ProphetX rows
carry the book's own displayed American price (read_prophetx: pr = int(t["price"])), which is a quote
and carries no fee at all, and ProphetX bills 2% of net gains per market at SETTLEMENT, so for
ProphetX the fee must be applied. That split is a property of how each reader builds its row, not an
assumption about the venues:

  Novig        cost/payout, fee-inclusive by construction, and Novig's pre-game fee is 0 anyway
               -> raw == net. UNAMBIGUOUS.
  ProphetX     the book's displayed price, no fee in it; 2% of net gains applies at settlement
               -> fee applied here. UNAMBIGUOUS.
  Kalshi       cost/contracts. Whether Kalshi's API "cost" is gross or net of its trading fee is NOT
  Polymarket   established in this repo, so these are reported as a BRACKET - as filled, and with
  US           the taker fee applied - and never folded into the headline. Naming the uncertainty is
               the point; picking the rounder number is how the Polymarket fee got set wrong on
               25 Oct.

CATEGORY DISCIPLINE (CLV_STANDARD.md section 2). This produces Executed CLV and nothing else. It is
never averaged with AUTO Opportunity, MANUAL Opportunity, Passive Posting or Paper Fill-Supported
CLV, and an unfilled order never appears here at all.

COST: zero OddsPapi credits by default. CACHE_ONLY skips any fixture whose Pinnacle history is not
already on disk, because hist_cache.get_hist() FETCHES whatever it is asked for and cannot find.
Set XC_CACHE_ONLY=0 to allow purchases - it will say what it bought.

Read-only: places no bet, changes no rule, opens no file for writing. Dollars go to the private
email; the Actions log gets counts only.
"""
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import executor as ex
import hist_cache as hc
import tracker_build as tb

ET = tb.ET
TSTATE = "tracker/state.enc"
DAYS = int(os.environ.get("XC_DAYS", "") or "30")
UNIT = float(os.environ.get("EXEC_UNIT", "") or "200")
CACHE_ONLY = (os.environ.get("XC_CACHE_ONLY", "") or "1") != "0"
TOL = 1e-9

# How each venue's stored price relates to a NET price. See the docstring: this follows from how
# tracker_build builds the row, not from a guess about the venue.
#   "money"  the price is already real-dollars-in / real-dollars-out, so it IS the net price
#   "quote"  the price is a displayed quote, so the venue's fee still has to come off
BASIS = {"novig.us": "money", "polymarket.us": "money", "kalshi": "money",
         "prophetx": "quote", "hardrockbet": "money"}
# Venues where that reading is not established, so they are bracketed and kept out of the headline.
AMBIG = ("kalshi", "polymarket.us")
L = []


MONEY = re.compile(r"\$\s*[+-]?[\d,]+(?:\.\d+)?")

# CLV-WORKS per-row export (Muse's runner is built and idle waiting on this). One row per GRADED
# BOT FILL, including the excluded ones with their reason, so the population is auditable rather
# than taken on trust - the same principle sent_export.py uses.
#
# NO STAKES, NO DOLLARS, NO BALANCES, NO ACCOUNT DATA, NO KEYS. Peter's export rule, and it is why
# stake/profit are deliberately absent from these columns even though the rows carry them: an
# export leaves here and the figures that matter for grading are prices and closes, not size.
XCOLS = ["day", "league", "game", "bet", "venue", "fee_basis", "in_headline",
         "fill_american", "fill_net_decimal", "pin_close_novig_prob",
         "executed_clv_pct", "executed_clv_pct_alt_basis", "beat_close", "result",
         "included", "exclusion_reason", "fee_model"]


def send_csv(subject, body, rows, filename):
    """The per-row export, as a CSV attachment on the private email - the same channel
    sent_export.py uses. A local copy of the sender because COLS there is module-level; there is
    no shared model here to drift, unlike a fee schedule."""
    import csv
    import io
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    user, pw, to = ex.gmail()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=XCOLS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    m = MIMEMultipart()
    m["Subject"], m["From"], m["To"] = subject, user, to
    m.attach(MIMEText(body, "plain", "utf-8"))
    part = MIMEBase("text", "csv")
    part.set_payload(buf.getvalue().encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    m.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as sv:
        sv.login(user, pw)
        sv.sendmail(user, [to], m.as_string())


def say(t=""):
    """Email body AND the public log. Only for lines that carry no money.

    The money check is not decoration: it is the guard that makes the rule hold even if someone
    later edits a line here without remembering that this repo is public. A dollar amount routes
    itself to the email instead of the log rather than relying on whoever is editing to notice."""
    L.append(t)
    if MONEY.search(str(t)):
        print("  [line withheld from the public log: carries a dollar amount]")
        return
    print(t)


def priv(t=""):
    """Email body ONLY - never the Actions log.

    Nov 9: run 42564956308 put 28 dollar figures into a PUBLIC Actions log, including the
    staked/P&L total, because say() printed everything and the report carries money. The repo is
    public and the rule is that the log gets counts only. Every line with a dollar amount, a stake,
    a P&L or an ROI goes through priv(); say() is for counts, percentages and field names."""
    L.append(t)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def wilson(k, n):
    """95% interval on a beat-close rate. Guard 2 asks for the interval, not just the point."""
    if not n:
        return None, None
    p, z = k / n, 1.959964
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


# Nov 11 (Peter, "go to GitHub, it has all my plays"): the same machinery, pointed at HIS bets as
# well as the bot's. Defaults are unchanged - bot only, graded only - so the existing Executed CLV
# report is byte-identical unless one of these is set. The fee basis is the whole reason to extend
# this file rather than write a new one: net_of() already knows which venues store money (fee
# inside) and which store a quote (fee still to apply), and getting that wrong is how the
# Polymarket fee came to be set wrong on 25 Oct.
SOURCES = tuple(x.strip().lower() for x in (os.environ.get("XC_SOURCES") or "bot").split(",") if x.strip())
UNGRADED = (os.environ.get("XC_UNGRADED") or "") == "1"
SINCE_ET = (os.environ.get("XC_SINCE") or "").strip()      # YYYY-MM-DD, ET day, inclusive


def fill_rows():
    """Bot fills by default. With XC_SOURCES / XC_UNGRADED / XC_SINCE, any source and any grade."""
    st = tb.dec(json.load(open(TSTATE)))
    raw = (st or {}).get("bets")
    rows = list(raw.values()) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    out = []
    for b in rows:
        src = str(b.get("source") or "").lower()
        if "all" not in SOURCES and src not in SOURCES:
            continue
        if not UNGRADED and b.get("result") not in ("W", "L", "P"):
            continue
        if num(b.get("price")) is None:
            continue
        if SINCE_ET:
            d = str(b.get("date") or b.get("settled") or b.get("first_seen") or "")[:10]
            if d and d < SINCE_ET:
                continue
        out.append(b)
    return out, len(rows)


def why_no_fixture(st, q, lg):
    """Which GATE did this fill fail? Measured per gate, so the fix is aimed rather than guessed.

    find_fixture returns a bare None whether the league was wrong, the clock was wrong, the names
    did not overlap, or two fixtures tied. Those need different fixes, and "no fixture matched" at
    24% of the population is too big a hole to attack blind."""
    words = (tb.toks(" ".join(t.get("name", "") for t in q.get("teams") or []))
             or tb.toks(q.get("game"))) - tb.WEAK
    gs = cl.tp(q.get("game_start"))
    fx = (st.get("fixtures") or {})
    if not words:
        return ("no usable team words", q.get("game"), "")
    same_lg = [f for f in fx.values() if f.get("lg") == lg]
    if not same_lg:
        return (f"no fixture at all in league {lg!r}", q.get("game"), "")
    in_win = [f for f in same_lg
              if not (gs and cl.tp(f.get("start"))
                      and abs((cl.tp(f.get("start")) - gs).total_seconds()) > 36 * 3600)]
    if not in_win:
        return (f"league {lg} has fixtures but none within 36h", q.get("game"), "")
    qual = [f for f in in_win if cl._qualifies(f, lg, gs, words)]
    if len(qual) > 1:
        # whether a start time was present decides what fixes this: with one, the window already
        # applied and the fixture cache really does hold two candidates (likely duplicates); with
        # none, the window was skipped and the fallback date is the fix.
        tag = ("AMBIGUOUS even WITH a start time - duplicate fixtures in the cache"
               if q.get("_start_was_given") else
               "AMBIGUOUS because no start time was on the row - window skipped")
        return (tag, q.get("game"),
                " | ".join(f"{f.get('p1')} v {f.get('p2')} @ {f.get('start')}" for f in qual[:3]))
    # none qualified: show the closest near-miss and what the token test actually saw
    best, bs = None, -1
    for f in in_win:
        a = (tb.toks(f.get("p1") or "") - tb.WEAK) & words
        c = (tb.toks(f.get("p2") or "") - tb.WEAK) & words
        s = len(a) + len(c)
        if s > bs:
            best, bs = (f, a, c), s
    if not best or bs <= 0:
        return ("no token overlap with any fixture in the window", q.get("game"), "")
    f, a, c = best
    gate = ("one side matched nothing" if not (a and c) else
            "a side was carried only by words the other side also matched" if not ((a - c) and (c - a)) else
            "neither side reached the two-distinctive-token floor")
    return (gate, q.get("game"),
            f"closest: {f.get('p1')} v {f.get('p2')}  p1 hit {sorted(a)}  p2 hit {sorted(c)}")


def net_of(book, raw_dec, league, live):
    """The NET decimal for a stored fill price, by that venue's basis."""
    if BASIS.get(book) == "money":
        return raw_dec                      # the fee is already in the money
    return cs.net_dec(book, raw_dec, maker=False, league=league, live=live)


def main():
    now = datetime.now(timezone.utc)
    say("EXECUTED CLV - Lane 1 fills at the price the books actually filled")
    say(cs.stamp())
    say(f"fee model {cs.FEE_MODEL} | window {DAYS}d | "
        f"{'CACHE ONLY - zero OddsPapi credits' if CACHE_ONLY else 'PURCHASES ALLOWED'}")
    say()

    try:
        F, total = fill_rows()
    except Exception as e:
        say(f"tracker state unreadable ({type(e).__name__}: {str(e)[:80]})")
        say("Nothing computed. This job needs tracker/state.enc, which only decrypts inside Actions.")
        try:
            ex.send("Bets EXECUTED CLV (state unreadable)", "\n".join(L))
        except Exception:
            pass
        return 1

    say("=" * 74)
    say("POPULATION - what the books' own records give us")
    say("=" * 74)
    say(f"  tracker rows                       {total}")
    say(f"  tagged source=='bot' AND graded    {len(F)}")
    if not F:
        say()
        say("  No graded bot fill is in the tracker state. That is the finding, not an error:")
        say("  Executed CLV cannot be computed without a filled price, and the join that tags a")
        say("  fill as the bot's is tracker_build.bot_keys/bot_match over the 'Bets LIVE' emails.")
        say("  If fills exist but none is tagged, that join is what to look at - not this script.")
        try:
            ex.send("Bets EXECUTED CLV (no graded bot fills)", "\n".join(L))
        except Exception:
            pass
        print(f"executed clv: rows {total}, graded bot fills 0")
        return 0

    bybook = Counter(cs.canon(b.get("book")) if b.get("book") else "(none)" for b in F)
    say()
    say("  by venue, with the basis its stored price is on:")
    for bk, n in bybook.most_common():
        bs = BASIS.get(bk, "?")
        note = ("  net by construction" if bs == "money" and bk not in AMBIG else
                "  fee applied here" if bs == "quote" else
                "  BRACKETED - basis not established" if bk in AMBIG else "  unknown basis")
        say(f"    {bk:16s} {n:4d}   price is {bs:6s}{note}")

    # ---------------------------------------------------------------- the closes
    st = {"fixtures": {}, "fx_last": {}}
    try:
        prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(prev.get("fixtures") or {})
        st["fx_last"] = dict(prev.get("fx_last") or {})
        say(f"\n  fixture cache: reusing {len(st['fixtures'])} fixtures - nothing re-purchased")
    except Exception as e:
        say(f"\n  fixture cache unavailable ({type(e).__name__}) - fixtures would be fetched")

    # clv_ledger.load_markets() BILLS when clv/markets.json is older than 7 days: it falls through
    # to api("/markets", True) + bill(). "Zero credits" cannot rest on that file happening to be
    # fresh today, so in CACHE_ONLY we read the file ourselves and never reach the paid call. A
    # stale or missing map costs us market ids, which shows up as an honest exclusion below - it
    # never produces a wrong number. That silent fall-through is how plimit-level spent 5
    # unapproved credits on 6 Nov.
    if CACHE_ONLY:
        try:
            _mk = json.load(open(cl.MKFILE))
            mkmap = _mk.get("m") or {}
            _age = (now - cl.tp(_mk["fetched"])).days
            say(f"  market map: {len(mkmap)} entries, {_age}d old, read from disk - no paid call"
                + ("  (STALE: load_markets would have bought a refresh)" if _age >= 7 else ""))
        except Exception as e:
            mkmap = {}
            say(f"  market map unavailable ({type(e).__name__}) - proceeding without it; closes that")
            say("    need a market id will be excluded rather than bought")
    else:
        mkmap = cl.load_markets(st, now)

    miss = Counter()
    unmatched = []
    excl = []
    R = []
    for b in F:
        lg = b.get("league")
        # Nov 9: "teams" was missing from this dict, and find_fixture PREFERS it over "game" -
        # words = toks(teams names) or toks(game). tracker_build.read_status stores ESPN's full
        # team names there whenever the bet matched a game, which is exactly the canonical naming
        # the matcher wants, while b["game"] is the BOOK's own terse string. Omitting it made every
        # fill match on the weaker source. "no fixture matched" was 10 of 41 fills, 24% of the
        # population, and this was my caller's fault, not the matcher's.
        # Nov 9, second finding: 8 of the 10 unmatched fills failed as AMBIGUOUS, not on names.
        # _qualifies only applies its 36h window when a start time is present -
        #     if gs and fs and abs(fs - gs) > 36h: return False
        # - so a fill with NO game_start skips the window, every meeting of those two teams all
        # season qualifies, and find_fixture rightly returns None rather than pick one. Two teams
        # playing twice is enough to do it. So supply a date when game_start is absent: a graded
        # fill's settle time is within 36h of its own game for any normal market. This can only
        # help or stay neutral - a fallback more than 36h out excludes the right fixture and the
        # fill stays unmatched, which is the safe outcome, never a confidently wrong one.
        gstart = (b.get("game_start") or b.get("settled") or b.get("placed")
                  or b.get("first_seen"))
        q = {"bet": b.get("bet"), "league": lg, "game": b.get("game"), "teams": b.get("teams"),
             "game_start": gstart, "book": b.get("book"),
             "_start_was_given": bool(b.get("game_start"))}
        def drop(reason):
            # one place for both, so the Guard 2 counts and the exported rows can never disagree
            miss[reason] += 1
            excl.append({"day": str(b.get("game_start") or "")[:10], "league": lg,
                         "game": b.get("game"), "bet": b.get("bet"),
                         "venue": cs.canon(b.get("book")) if b.get("book") else "",
                         "fee_basis": BASIS.get(cs.canon(b.get("book")) if b.get("book") else "", ""),
                         "fill_american": num(b.get("price")), "result": b.get("result"),
                         "included": 0, "exclusion_reason": reason, "fee_model": cs.FEE_MODEL})
        fid = cl.find_fixture(st, q)
        if not fid:
            drop("no fixture matched")
            unmatched.append(why_no_fixture(st, q, lg))
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f.get("start")) or cl.tp(b.get("game_start"))
        if not start:
            drop("no game start")
            continue
        if now - start < hc.FINAL_AFTER:
            drop("game not final yet")
            continue
        if CACHE_ONLY and not os.path.exists(hc._path(fid, "pinnacle")):
            drop("Pinnacle close not in cache (not bought)")
            continue
        h = hc.get_hist(fid, ["pinnacle"], start)
        if isinstance(h, dict) and h.get("_error"):
            drop("history error")
            continue
        c, why = cl.close_for(q, f, cl.book_markets(h, "pinnacle"), mkmap, start, lg)
        if not c:
            drop(f"no verified same-line close ({str(why)[:28]})")
            continue

        bk = cs.canon(b.get("book"))
        am = num(b.get("price"))
        raw = cl.am_to_dec(am)
        try:
            nd = net_of(bk, raw, lg, False)
        except cs.UnknownVenue:
            drop("venue not in the registry")
            continue
        R.append({
            "day": start.astimezone(ET).strftime("%Y-%m-%d"),
            "book": bk, "lg": lg, "game": b.get("game"), "bet": b.get("bet"),
            "am": am, "net_dec": nd,
            "clv": 100 * (c["p"] * nd - 1),
            # the other side of the bracket, for the two venues whose basis is not established
            "clv_alt": (100 * (c["p"] * cs.net_dec(bk, raw, league=lg) - 1)
                        if bk in AMBIG else None),
            "pin_p": c["p"],            # the verified close itself, so the export can be re-graded
            "beat": c["p"] * nd > 1 + TOL,
            "stake": num(b.get("stake")), "profit": num(b.get("profit")), "res": b.get("result"),
        })

    say()
    say("=" * 74)
    say("GUARD 2 - exclusions, reported with the headline (CLV_STANDARD.md section 3)")
    say("=" * 74)
    say(f"  graded bot fills considered        {len(F)}")
    for k, n in miss.most_common():
        say(f"    excluded, {k:44s} {n:4d}")
    say(f"  verified same-line sample          {len(R)}")
    if F:
        say(f"  coverage                           {100 * len(R) / len(F):.1f}% of graded bot fills")

    if unmatched:
        # "no fixture matched" is the biggest single hole in this measurement, so it is broken down
        # by GATE rather than left as one number. Each gate needs a different fix.
        say()
        say("  WHY the unmatched fills failed, by gate:")
        for g, n in Counter(g for g, _, _ in unmatched).most_common():
            say(f"    {n:3d}  {g}")
        priv("")
        priv("  the unmatched fills, with the closest fixture and what the token test saw:")
        for g, game, detail in unmatched:
            priv(f"    [{g}] {game}")
            if detail:
                priv(f"        {detail}")
    if not R:
        say()
        say("  No fill cleared the standard's requirements, so there is no Executed CLV to report.")
        say("  The standard forbids a modelled or converted close in a headline figure, so this")
        say("  reports nothing rather than something weaker. The exclusion counts above say why.")
        try:
            ex.send("Bets EXECUTED CLV (no verified closes)", "\n".join(L))
        except Exception:
            pass
        print(f"executed clv: graded bot fills {len(F)}, verified 0, "
              f"top exclusion {miss.most_common(1)[0][0] if miss else '-'}")
        return 0

    # ---------------------------------------------------------------- the headline
    clean = [r for r in R if r["book"] not in AMBIG]
    say()
    say("=" * 74)
    say("EXECUTED CLV  (CLV_STANDARD.md section 2: this category only, never merged)")
    say("=" * 74)

    def block(rows, title, note=""):
        if not rows:
            say(f"\n  {title}: no rows")
            return
        n = len(rows)
        m = sum(r["clv"] for r in rows) / n
        k = sum(1 for r in rows if r["beat"])
        lo, hi = wilson(k, n)
        say(f"\n  {title}")
        if note:
            say(f"    {note}")
        say(f"    n                    {n}")
        say(f"    Executed CLV         {m:+.2f}%   (mean, net of fees, at the filled price)")
        say(f"    beat the close       {k}/{n} = {100 * k / n:.1f}%   95% CI [{lo:.1f}%, {hi:.1f}%]")
        say(f"    excludes a coin flip {'YES' if (lo > 50 or hi < 50) else 'NO'}")
        st_ = sum(r["stake"] or 0 for r in rows)
        pf = sum(r["profit"] or 0 for r in rows)
        w = sum(1 for r in rows if r["res"] == "W")
        l_ = sum(1 for r in rows if r["res"] == "L")
        p_ = sum(1 for r in rows if r["res"] == "P")
        say(f"    record               {w}-{l_}" + (f"-{p_}" if p_ else ""))
        if st_:
            # money: private email only. The log gets the unit-denominated version, which is
            # what Peter wants in chat anyway and carries no account size.
            priv(f"    staked / P&L         ${st_:,.2f} / ${pf:+,.2f}   ROI {100 * pf / st_:+.1f}%")
            say(f"    P&L in units         {pf / UNIT:+.2f}u on {st_ / UNIT:.2f}u staked"
                f"   ROI {100 * pf / st_:+.1f}%")

    block(clean, "HEADLINE - venues whose fee basis is established (Novig, ProphetX, Hard Rock)",
          "Novig: price is already net. ProphetX: 2% of net gains applied here.")

    amb = [r for r in R if r["book"] in AMBIG]
    if amb:
        n = len(amb)
        a1 = sum(r["clv"] for r in amb) / n
        a2 = sum(r["clv_alt"] for r in amb) / n
        say(f"\n  BRACKET - Kalshi and Polymarket US ({n} fill(s)), KEPT OUT of the headline")
        say(f"    taking the stored price as already net : {a1:+.2f}%")
        say(f"    applying the taker fee on top of it    : {a2:+.2f}%")
        say(f"    The truth is one of these two. Which one depends on whether those venues' API")
        say(f"    'cost' is gross or net of the trading fee, which this repo has not established.")
        say(f"    One API response for a known fill settles it; until then it stays a bracket.")

    say()
    say("=" * 74)
    say("GUARD 1 - the scope this figure applies to (CLV_STANDARD.md section 3)")
    say("=" * 74)
    say("  Population      Lane 1 bot fills as the VENUES recorded them, not as the alert stream")
    say("                  reported them. Tagged by tracker_build.bot_keys/bot_match.")
    say("  Execution basis actual filled price, net of fees, taker side.")
    say("  Category        Executed CLV. Not AUTO, not MANUAL, not Passive Posting, not Paper.")
    say(f"  Sample          {len(clean)} in the headline"
        + (f", {len(amb)} bracketed separately" if amb else ""))
    say("  This is NOT the CLV of Lane 2, Lane 3, the liquidity-alert population or the system.")
    say("  The -0.37% AUTO Opportunity figure on 910 liquidity alerts is a different measurement of")
    say("  a different population and the two are never averaged.")

    say()
    say("  Maker fills: every row here is priced as a TAKER. Where the bot's order rested and was")
    say("  hit, the true fee is the maker rate - on Polymarket US a -0.0125 REBATE, which would")
    say("  make that fill better than shown. The tracker carries no maker/taker marker, so this")
    say("  reports the taker side, which is the conservative one, and says so rather than guessing.")

    say()
    say("=" * 74)
    say("THE FILLS   (per-bet money is in the private email only, never this log)")
    say("=" * 74)
    priv(f"  {'day':10s} {'venue':12s} {'lg':6s} {'bet':26s} {'fill':>6s} {'CLV':>8s} {'res':>4s} {'P&L':>10s}")
    for r in sorted(R, key=lambda r: (r["day"], str(r["game"]))):
        priv(f"  {r['day']:10s} {r['book'][:12]:12s} {str(r['lg'] or '')[:6]:6s} "
             f"{str(r['bet'])[:26]:26s} {cl.dec_to_am(cl.am_to_dec(r['am'])):+6.0f} "
             f"{r['clv']:+7.2f}% {str(r['res']):>4s} "
             f"{('$%+.2f' % r['profit']) if r['profit'] is not None else '-':>10s}")

    say()
    say("Actual filled-bet profitability remains the ultimate measure. Positive CLV is evidence of")
    say("pricing value, not proof of realised profitability.")

    # CLV-WORKS per-row export: one row per graded bot fill, INCLUDING the excluded ones with their
    # reason, so the population can be audited rather than trusted. No stakes, no dollars, no
    # account data, no keys - Peter's export rule.
    xrows = [{
        "day": r["day"], "league": r["lg"], "game": r["game"], "bet": r["bet"],
        "venue": r["book"], "fee_basis": BASIS.get(r["book"], ""),
        "in_headline": 0 if r["book"] in AMBIG else 1,
        "fill_american": r["am"], "fill_net_decimal": round(r["net_dec"], 6),
        "pin_close_novig_prob": round(r["pin_p"], 6),
        "executed_clv_pct": round(r["clv"], 4),
        "executed_clv_pct_alt_basis": (round(r["clv_alt"], 4) if r["clv_alt"] is not None else ""),
        "beat_close": int(bool(r["beat"])), "result": r["res"],
        "included": 1, "exclusion_reason": "", "fee_model": cs.FEE_MODEL,
    } for r in sorted(R, key=lambda r: (r["day"], str(r["game"])))] + excl
    note = ("\n\nAttached: one row per graded bot fill, the excluded ones included with their\n"
            "reason, so the population is auditable rather than trusted. No stakes, dollars,\n"
            "balances or keys. fill_net_decimal is net of fees by that venue's basis - see\n"
            "fee_basis: 'money' means the stored price is already dollars-in over dollars-out,\n"
            "'quote' means the venue's fee is applied. in_headline=0 rows are the Kalshi /\n"
            "Polymarket US bracket, where executed_clv_pct_alt_basis is the other reading.")
    try:
        send_csv("Bets EXECUTED CLV - per-row export for CLV-WORKS", "\n".join(L) + note,
                 xrows, f"executed_clv_perrow_{now.astimezone(ET):%Y%m%d_%H%M}.csv")
        print(f"per-row export sent: {len(xrows)} rows ({len(R)} included, {len(excl)} excluded)")
    except Exception as exn:
        print(f"per-row export failed ({type(exn).__name__}) - sending the report as text")
        try:
            ex.send("Bets EXECUTED CLV - Lane 1 fills at the books' own prices", "\n".join(L))
        except Exception as e:
            print(f"email failed ({type(e).__name__})")
    # counts only to the public log
    print(f"executed clv: graded bot fills {len(F)}, verified {len(R)}, "
          f"headline {len(clean)}, bracketed {len(amb)}, excluded {sum(miss.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

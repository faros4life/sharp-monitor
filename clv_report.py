#!/usr/bin/env python3
"""
VALUE LAB CLV REPORT - the one reporter for the Final CLV Calculation Standard (Peter, Nov 6).

ONE FORMULA, net of fees, against Pinnacle's VERIFIED SAME-LINE no-vig close:

    net CLV % = (pinnacle_no_vig_close_p  x  effective_entry_decimal_after_fees  -  1) x 100

This file adds no fee logic and no second close rule. It reuses what is already built and tested:
  clv_ledger.close_for()   Pinnacle no-vig close for the held side, + how it was read and its age
  clv_std                  the venue registry, the one fee call, AUTO/MANUAL scope, close_verified
  hist_cache               the historical quotes, from the cache only
  exchange_lag             eff() / size_at(), through clv_std

SCOPE. Peter, Nov 6: "first report's header labels its scope - liquidity alerts only, not
system-wide." The header says so and so does every section title. Nothing here speaks for Lane 1,
the board, or any registered test.

FOUR NUMBERS, NEVER POOLED (standard section 3)
  AUTO Opportunity CLV    best net quote across auto-eligible exchanges, Hard Rock EXCLUDED
  MANUAL Opportunity CLV  the same plus Hard Rock
  Executed CLV            actual filled price, fee side as filled
  Paper fill-supported    modelled fill, computed in a separate pass, never merged into Executed
A category with no data prints UNAVAILABLE and its reason. It never borrows another's number.

PETER'S QUOTE SAFEGUARD (his correction to my proposal, Nov 6). A best-net price counts only if it
is a CONTEMPORANEOUS quote with SUFFICIENT DISPLAYED SIZE, and its age is printed. Failing either,
the row is labelled quote-only and EXCLUDED from the headline. A stale or unsized quote is not an
opportunity, and calling it one is how a paper edge appears that no one could have taken.

EXCHANGE SELF-CLOSE. The liquidity feed's own `clv_cents` compares our entry to the LAST PREGAME
PRICE ON THE TRIGGER EXCHANGE - the venue we traded on, not Pinnacle. Where we were the liquidity
that is partly our own footprint. Peter, Nov 6: keep it, rename it "Exchange Self-Close Price
Movement", the word CLV never appears in its name, and it is never a headline and never a gate.

CREDITS. Cache only. This report buys nothing: a fixture that is not cached is excluded with a
reason rather than fetched. It needs TRACKER_PASSPHRASE to read the encrypted fixture cache, so it
runs as a workflow. Without the secret the decrypt fails and the run STOPS - it does not fall
through to a fetch, because that silence is how plimit-level spent 5 unapproved credits on Nov 6.

WHAT IS PRINTED WHERE. The repo is public, so the Actions log gets counts, percentages and field
names only. Per-bet detail goes to the private address.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_ledger as cl
import clv_std as cs
import exchange_lag as el
import hist_cache as hc
import liq_history_test as lh
import nba_names as nn
import tracker_build as tb

ET = tb.ET
FROM = cl.tp(os.environ.get("CLV_FROM", "") or "2026-10-12T00:00:00Z")

# Peter's safeguard, both printed in the header so the bar is never implicit.
QUOTE_MAX_AGE_S = int(os.environ.get("CLV_QUOTE_MAX_AGE_S", "") or "900")   # contemporaneous
QUOTE_MIN_SIZE = float(os.environ.get("CLV_QUOTE_MIN_SIZE", "") or "0")     # 0 = size unknown is
#   allowed but REPORTED; set it above 0 to make displayed size a hard requirement. It starts at 0
#   because OddsPapi does not carry a limit for every venue and tick, and a bar that silently voids
#   most of the population would be worse than one that counts and shows what it could not size.

L = []


def say(line, public=True):
    L.append(line)
    if public:
        print(line)


def pct(n, d):
    return f"{100.0 * n / d:.1f}%" if d else "n/a"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, s="%"):
    return "n/a" if x is None else f"{x:+.2f}{s}"


# Nov 6: I first wrote my own bet-text builder here and every one of 1,774 rows fell out -
# 810 on "no fixture matched". liq_history_test.bet_text() is the one that actually parses this
# population, and its EXCH tuple carries the keys the history cache really uses ("novig.us",
# "polymarket.us"), which my own SLUG map had inverted. Reusing both rather than reinventing them,
# for the same reason event_id.py was refactored onto nba_names: a second copy drifts from the
# first and the drift shows up as an empty report, not as an error.
bet_text = lh.bet_text
EXCH = lh.EXCH                       # ("prophetx", "novig.us", "kalshi", "polymarket.us")


def main():
    say("VALUE LAB CLV REPORT")
    say("SCOPE: LIQUIDITY ALERTS ONLY - not system-wide. This speaks for no other lane or test.")
    say(cs.stamp())
    say(f"Quote rule: read AT OR BEFORE the alert timestamp - no look-ahead - and no staler than "
        f"{QUOTE_MAX_AGE_S}s. Age printed on every headline row; a stale quote is excluded.")
    say("Displayed size is NOT an eligibility requirement (Peter's decision, Nov 6). Size is "
        "reported where known and never used to admit or reject a posting opportunity.")
    say("Public log carries counts, percentages and field names only - never an amount.")

    try:
        pop = json.load(open("liquidity/alerts.json"))
        pop = pop if isinstance(pop, list) else (pop.get("alerts") or [])
    except Exception as e:
        say(f"population unreadable ({type(e).__name__}) - nothing to report")
        return 1

    A = [a for a in pop
         if a.get("result") in ("W", "L", "P")
         and not a.get("artifact")
         and cl.tp(a.get("alerted_utc"))
         and cl.tp(a["alerted_utc"]) >= FROM]
    say(f"\npopulation: {len(pop)} rows -> {len(A)} graded, close-clean, in window")

    now = datetime.now(timezone.utc)
    st = {"billable": {}}
    try:
        prev = cl.tb.dec(json.load(open(cl.STATE)))
        st["fixtures"] = dict(prev.get("fixtures") or {})
        st["fx_last"] = dict(prev.get("fx_last") or {})
        say(f"fixture cache: {len(st['fixtures'])} fixtures, read-only, zero credits")
    except Exception as e:
        say(f"STOP: fixture cache could not be decrypted ({type(e).__name__}). TRACKER_PASSPHRASE "
            f"is required. Refusing to fall through to a paid fetch.")
        return 1
    mkmap = cl.load_markets(st, now)

    head, excl, selfmove = [], {}, []

    def drop(why):
        excl[why] = excl.get(why, 0) + 1

    for a in A:
        lg, t0 = a.get("league"), cl.tp(a["alerted_utc"])
        game = (a.get("game") or "").split(":")[0]
        b = {"bet": bet_text(a), "league": lg, "game": game,
             "game_start": a.get("start_utc"), "book": a.get("book")}
        tms = nn.teams_of(a)
        if tms:
            b["teams"] = tms

        # the self-close movement is available for every row and needs no Pinnacle at all
        if a.get("clv_cents") is not None:
            selfmove.append(a["clv_cents"])

        fid = cl.find_fixture(st, b)
        if not fid:
            drop("no fixture matched in OddsPapi")
            continue
        f = st["fixtures"][fid]
        start = cl.tp(f.get("start")) or cl.tp(a.get("start_utc"))
        if not all(os.path.exists(hc._path(fid, x)) for x in ("pinnacle",) + EXCH):
            drop("fixture not in the history cache")
            continue
        h = hc.get_hist(fid, ["pinnacle"] + list(EXCH), start)
        if isinstance(h, dict) and h.get("_error"):
            drop("history read error")
            continue

        pin = cl.book_markets(h, "pinnacle")
        c, why = cl.close_for(b, f, pin, mkmap, start, lg)
        if not c:
            drop(f"no Pinnacle close: {why}")
            continue
        # standard section 4: ONLY a verified same-line close reaches a headline
        if not cs.close_verified(c.get("how")):
            drop(f"close not same-line (derived: {c.get('how')})")
            continue

        # the opportunity set, with Peter's safeguard applied per quote.
        # Nov 6 (Peter, code review): this read the book AS OF t0 + QUOTE_MAX_AGE_S, i.e. up to 15
        # MINUTES AFTER the alert fired - look-ahead bias, and it would have flattered every
        # opportunity figure with prices nobody could have seen at the alert. two_way() returns the
        # last tick AT OR BEFORE the time it is given, so the read time is the alert itself and
        # QUOTE_MAX_AGE_S does the job it was named for: a ceiling on how STALE a quote may be,
        # never a licence to look forward.
        when = t0
        quotes, ages, sizes, unqualified = {}, {}, {}, 0
        for slug in EXCH:
            bk = cl.book_markets(h, slug)
            x = cl.novig_at(b, f, bk, mkmap, when, lg) if bk else None
            if not x:
                continue
            raw, age = x[0], x[1]
            try:
                size = el.size_at(bk, mkmap, lg, {"type": a.get("market"), "side": a.get("side")}, when)
            except Exception:
                size = None
            # contemporaneous?
            if age is None or age > QUOTE_MAX_AGE_S:
                unqualified += 1
                continue
            # Peter, Nov 6: displayed size is NOT an eligibility requirement for a posting
            # opportunity. It is recorded and reported, and it never admits or rejects a quote.
            quotes[slug], ages[slug], sizes[slug] = raw, age, size

        if not quotes:
            drop("quote-only: no contemporaneous, sufficiently sized quote at the alert")
            continue

        # league drives ProphetX's NHL schedule; live=False because this population is pre-game
        # alerts by construction (close_price is the last PREGAME price), never in-game Novig.
        av, and_, asrc = cs.best_net(quotes, "auto", league=lg, live=False)
        mv, mnd, msrc = cs.best_net(quotes, "manual", league=lg, live=False)
        if and_ is None:
            drop("quote-only: no AUTO-eligible quote cleared the safeguard")
            continue

        head.append({
            "game": game, "league": lg, "market": a.get("market"), "side": a.get("side"),
            "line": a.get("line"), "alert_utc": a.get("alerted_utc"), "result": a.get("result"),
            "trigger_book": a.get("book"),
            "auto_venue": av, "auto_source_venue": asrc, "auto_net_dec": round(and_, 5),
            "auto_clv": round(100 * (c["p"] * and_ - 1), 3),
            "auto_quote_age_s": ages.get(asrc), "auto_quote_size": sizes.get(asrc),
            "manual_venue": mv, "manual_source_venue": msrc,
            "manual_net_dec": (round(mnd, 5) if mnd else None),
            "manual_clv": (round(100 * (c["p"] * mnd - 1), 3) if mnd else None),
            "pin_close_p": round(c["p"], 5), "close_how": c.get("how"),
            "close_age_min": c.get("age_min"), "close_same_line": 1,
            "quotes_unqualified": unqualified, "fee_model": cs.FEE_MODEL,
        })

    # ---------------------------------------------------------------- the nine required fields
    n = len(head)
    say(f"\n{'='*74}\nHEADLINE - LIQUIDITY ALERTS ONLY, verified same-line Pinnacle closes\n{'='*74}")
    if not n:
        say("  no row cleared both the verified-close rule and the quote safeguard.")
    else:
        auto = [r["auto_clv"] for r in head]
        beat = sum(1 for x in auto if x > 0)
        say(f"  1. AUTO Opportunity CLV      {fmt(mean(auto))}   (n {n})")
        man = [r["manual_clv"] for r in head if r["manual_clv"] is not None]
        if any(r["manual_venue"] == "hardrockbet" for r in head):
            say(f"  2. MANUAL Opportunity CLV    {fmt(mean(man))}   (n {len(man)})")
        else:
            say("  2. MANUAL Opportunity CLV    UNAVAILABLE - Hard Rock quotes are not in this "
                "population, so MANUAL would merely copy AUTO. Not reported as a second number.")
        say("  3. Actual Executed CLV       UNAVAILABLE - no executed-fill record is wired to this "
            "population. Needs the venues' own fill histories; not inferred from a displayed price.")
        say("  4. Paper fill-supported CLV  UNAVAILABLE - no paper-fill pass runs on this "
            "population. It would be a separate pass and is never merged into field 3.")
        say(f"  5. Beating the verified close {pct(beat, n)}  ({beat}/{n})")
        say(f"  6. Sample size {n}; exclusions {sum(excl.values())} (named below)")
        vb = {}
        for r in head:
            vb[r["auto_venue"]] = vb.get(r["auto_venue"], 0) + 1
        say(f"  7. Entry venue and net price  per-row in the private detail; AUTO winners: "
            f"{dict(sorted(vb.items(), key=lambda x: -x[1]))}")
        say(f"  8. Fee-model version          {cs.FEE_MODEL}")
        ages = [r["auto_quote_age_s"] for r in head if r["auto_quote_age_s"] is not None]
        sized = sum(1 for r in head if r["auto_quote_size"] is not None)
        say(f"  9. Close verification         100% same-line (own line or moneyline); nothing "
            f"derived or converted reached this figure")
        say(f"     quote age: median {sorted(ages)[len(ages)//2] if ages else 'n/a'}s; "
            f"displayed size known on {pct(sized, n)} of rows")

    say(f"\nEXCLUSIONS - every dropped row named ({sum(excl.values())} total)")
    for k, v in sorted(excl.items(), key=lambda x: -x[1]):
        say(f"  {v:5d}  {k}")

    say(f"\n{'='*74}\nEXCHANGE SELF-CLOSE PRICE MOVEMENT - NOT CLV, never a headline, never a gate\n{'='*74}")
    say("  The liquidity feed compares entry to the last pregame price ON THE TRIGGER EXCHANGE,")
    say("  not to Pinnacle. Where we were the liquidity, it is partly our own footprint.")
    if selfmove:
        up = sum(1 for x in selfmove if x > 0)
        say(f"  mean movement {mean(selfmove):+.2f}c over {len(selfmove)} rows; moved toward the "
            f"held side on {pct(up, len(selfmove))}")

    say(f"\nfee model {cs.FEE_MODEL}. Cache only - zero OddsPapi credits spent.")

    try:
        import executor as ex
        ex.send("Bets VALUE LAB CLV REPORT (liquidity alerts only)",
                "\n".join(L) + "\n\nPER-BET DETAIL\n" + json.dumps(head, indent=1)[:900000])
    except Exception as e:
        print(f"email failed ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

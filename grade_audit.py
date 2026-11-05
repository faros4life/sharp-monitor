#!/usr/bin/env python3
"""READ-ONLY grading audit - Nov 5 2026, on Peter's written approval.

THE QUESTION
tracker_build.match_game() can identify a game from ONE matching team when the league is known:
    return best if score >= 2 or (score == 1 and bet.get("league")) else None
For Novig, Hard Rock and manual bets the tracker then reads that game's final score and writes
b["result"] and b["profit"]. So a wrong game assignment can produce a wrong W/L and a wrong P&L.
This already happened once: pin_bad()'s own docstring records "Seattle -10.5 placed Nov 3 for Sun
Nov 8 had been pinned to, and graded on, Monday's Bears @ Seahawks". The incidence is what is unknown.

WHAT COUNTS AS INDEPENDENT EVIDENCE
attach() overwrites teams, g_state, g_detail, teams_final (and league/game_start when absent), and
the grading path synthesises settled from the matched game's start + 4h. None of those can serve as
proof of the assignment they came from. Independent, for site=False rows:
    bet text, the book's own game description, placed, price/stake/to_pay, the bookmaker id,
    and first_seen as an OBSERVATION BOUND only - not a placement time.

HOW A GAME IS IDENTIFIED
placed BOUNDS the search and never selects. The window runs forward from placed by a documented
sport-specific span, because a bet may be placed weeks before kickoff. Selection is by name only;
proximity to placement is never a tie-breaker. Two qualifying games stay AMBIGUOUS.
LIMITATION, stated rather than papered over: nv|{marketId}|{outcomeId} is a Novig-internal id with
NO mapping to an ESPN game. There is no join key, so identification rests on the book's own game
text. That is independent of attach(), but it is text matching, not an id match.

THE GRADER IS INDEPENDENT
Peter, Nov 5: the audit must not reuse read_status() OR its underlying parse_bet(). Both are
re-implemented here from scratch, so a parsing or grading bug cannot be inherited by the tracker and
its own audit at once. Where the two parsers disagree, that is REPORTED as a discrepancy to
adjudicate - neither implementation is privileged.

Writes nothing. Corrected P&L is reported as a PROPOSED ADJUSTMENT, never applied.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

import executor as ex
import tracker_build as tb

ET = timezone(timedelta(hours=-5))

# Forward search windows, documented. Weekly sports take bets weeks out; near-daily sports can see
# the same pairing twice inside the span, which is why recurrence is REPORTED, never resolved.
FWD = {"NFL": 21, "NCAAF": 21, "NBA": 10, "NHL": 10, "MLB": 10, "NCAAB": 10, "WNBA": 10}
BACK_TOL = timedelta(hours=8)        # pin_bad's own tolerance, reused so there is no rival threshold
MAX_DATES = 220                      # bound the ESPN fetch (free, but keep the run sane)
NUMBER = r"[+-]?\d+(?:\.\d+)?"


def tpa(v):
    d = tb.tparse(v)
    return d.replace(tzinfo=timezone.utc) if (d is not None and d.tzinfo is None) else d


# ----------------------------------------------------------------- independent bet parser
def my_parse(text, flip=False):
    """(market, side, line) | None. Written from scratch - NOT tracker_build.parse_bet.

    market: 'total' | 'spread' | 'ml'
    side:   'OVER'/'UNDER' for a total, otherwise the team text as written
    line:   the number, signed from the bet's point of view; None for a moneyline
    flip / an explicit NOT means the held side is the NO side, which inverts the bet."""
    raw = (text or "").strip()
    if not raw:
        return None
    t = re.sub(r"\(\s*[+-]?\d+\s*\)", " ", raw)              # strip a trailing price in parentheses
    low = " " + re.sub(r"\s+", " ", t.lower()).strip() + " "
    neg = bool(flip) ^ bool(re.search(r"\bnot\b", low))

    # 1) "TEAM wins by over/under N points" is a SPREAD wearing a total's words - test it first
    m = re.search(r"^\s*(.+?)\s+wins by (over|under|more than|at least)\s+(" + NUMBER + r")", low)
    if m:
        ln = float(m.group(3))
        side = m.group(1).strip()
        if m.group(2) == "under":                            # "wins by under N" = the other side
            neg = not neg
        return ("spread", side, (ln if neg else -ln))        # favourite laying N -> negative line

    # 2) a plain total
    m = re.search(r"\b(over|under|o|u)\b\s*(" + NUMBER + r")", low)
    if m:
        side = "OVER" if m.group(1) in ("over", "o") else "UNDER"
        if neg:
            side = "UNDER" if side == "OVER" else "OVER"
        return ("total", side, float(m.group(2)))

    # 3) a spread: team text then a signed number
    m = re.search(r"^\s*(.+?)\s*(" + NUMBER + r")\s*$", low)
    if m and re.match(r"^[+-]", m.group(2)):
        ln = float(m.group(2))
        return ("spread", m.group(1).strip(), (-ln if neg else ln))

    # 4) a moneyline
    m = re.search(r"^\s*(.+?)\s*(?:\bml\b|\bmoneyline\b|\bwins\b|\bto win\b)\s*$", low)
    if m:
        return ("ml", m.group(1).strip(), None)
    if not re.search(r"\d", low):                            # bare team name
        return ("ml", low.strip(), None)
    return None


def toks(s):
    """Local tokeniser - deliberately NOT tb.toks, for the same independence reason."""
    return {w for w in re.findall(r"[a-z0-9.]+", (s or "").lower())
            if len(w) > 1 and not w.replace(".", "").isdigit()}


STOPW = {"at", "vs", "v", "the", "fc", "game", "points", "point", "wins", "by", "over", "under",
         "not", "total", "ml", "moneyline", "spread", "win", "to"}
WEAKW = {"state", "st", "tech", "university", "college", "north", "south", "east", "west",
         "central", "new", "city", "los", "la"}


def team_words(s):
    return (toks(s) - STOPW) - WEAKW


# ----------------------------------------------------------------- independent grader
def my_grade(market, side, line, away, home, a_score, h_score):
    """(W|L|P|None, which_team) computed from first principles - NOT read_status()."""
    if market == "total":
        tot = a_score + h_score
        if line is None:
            return None, None
        if tot == line:
            return "P", None
        return ("W" if ((tot > line) == (side == "OVER")) else "L"), None
    w = team_words(side)
    pick = None
    if w & team_words(away):
        pick = "away"
    if w & team_words(home):
        pick = "home" if pick is None else "both"      # ambiguous side - do not guess
    if pick in (None, "both"):
        return None, pick
    mine, theirs = (a_score, h_score) if pick == "away" else (h_score, a_score)
    if market == "ml":
        return ("P" if mine == theirs else ("W" if mine > theirs else "L")), pick
    margin = mine - theirs + (line or 0.0)
    if abs(margin) < 1e-9:
        return "P", pick
    return ("W" if margin > 0 else "L"), pick


def expected_profit(result, stake, to_pay):
    """The tracker's own convention for a graded bet, recomputed: W -> to_pay - stake, L -> -stake,
    P -> 0. No fee is assumed for any book: ProphetX's 0.98 belongs to ProphetX's settlement path and
    ProphetX is excluded from tracker grading, so the two never meet."""
    if result == "W":
        return None if (stake is None or to_pay is None) else round(to_pay - stake, 2)
    if result == "L":
        return None if stake is None else -round(stake, 2)
    if result == "P":
        return 0.0
    return None


def main():
    now = datetime.now(timezone.utc)
    if not os.environ.get("TRACKER_PASSPHRASE"):
        print("grade audit: TRACKER_PASSPHRASE not set; skipped")
        return
    bets = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    L = [f"GRADING AUDIT - READ-ONLY | {now.astimezone(ET):%Y-%m-%d %H:%M} ET", "",
         "Asks whether the tracker's own W/L and P&L are right, using only evidence the grading path",
         "could not have written. Nothing is changed; corrected P&L is a PROPOSED adjustment only.",
         "The grader and the bet parser are re-implemented from scratch: neither read_status() nor",
         "parse_bet() is reused, so a bug cannot be inherited by the tracker and its audit at once.", ""]

    settled = {k: b for k, b in bets.items() if b.get("result")}
    book = {k: b for k, b in settled.items() if b.get("site") is True}
    trk = {k: b for k, b in settled.items() if b.get("site") is not True}
    L += ["=" * 74, "A. POPULATION - the two groups stay separate throughout", "=" * 74,
          f"  settled rows: {len(settled)}",
          f"    BOOK-SETTLED (site=True), result and profit from the bookmaker: {len(book)}",
          f"    TRACKER-GRADED (site is not True), result and profit computed by the tracker: {len(trk)}", ""]

    def cut(rows, keyf, label):
        c = {}
        for b in rows.values():
            c[str(keyf(b))] = c.get(str(keyf(b)), 0) + 1
        L.append(f"    by {label}: " + ", ".join(f"{a} {n}" for a, n in sorted(c.items(), key=lambda kv: -kv[1])))

    def market_of(b):
        p = my_parse(b.get("bet"), b.get("flip"))
        return p[0] if p else "unparsed"

    for nm, rows in (("BOOK-SETTLED", book), ("TRACKER-GRADED", trk)):
        L.append(f"  {nm} ({len(rows)}):")
        cut(rows, lambda b: b.get("book") or "?", "book")
        cut(rows, lambda b: b.get("league") or "?", "sport")
        cut(rows, lambda b: market_of(b), "market type")
        cut(rows, lambda b: b.get("result"), "recorded result")
    L += ["", "  NOTE: totals carry the least protection in the original logic - read_status() grades a",
          "  total by summing both scores and never calls team_of(), so a wrong game is graded silently.",
          "  Spreads and moneylines must resolve a side against the game, which often fails instead.", ""]

    # ------------------------------------------------------------- B. parser agreement
    L += ["=" * 74, "B. PARSER AGREEMENT - two independent readings of the same bet text", "=" * 74,
          "  Neither parser is privileged. A disagreement is a discrepancy to adjudicate, not proof",
          "  that the tracker is wrong.", ""]
    dis = []
    for k, b in settled.items():
        mine = my_parse(b.get("bet"), b.get("flip"))
        try:
            theirs = tb.parse_bet(b.get("bet"), b.get("flip"))
        except Exception:
            theirs = None
        if (mine is None) != (theirs is None):
            dis.append((k, b, mine, theirs, "one parser read it, the other did not"))
        elif mine and theirs:
            if mine[0] != theirs[0]:
                dis.append((k, b, mine, theirs, "different market type"))
            elif mine[0] == "total" and (mine[1] != theirs[1] or abs((mine[2] or 0) - (theirs[2] or 0)) > 1e-9):
                dis.append((k, b, mine, theirs, "different total side or line"))
            elif mine[0] == "spread" and abs((mine[2] or 0) - (theirs[2] or 0)) > 1e-9:
                dis.append((k, b, mine, theirs, "different spread line"))
    L.append(f"  disagreements: {len(dis)} of {len(settled)}")
    for k, b, mine, theirs, why in dis[:20]:
        L.append(f"     {b.get('book') or '?':<11} {(b.get('bet') or '')[:30]:<30} | mine {mine} | tracker {theirs} | {why}")
    if len(dis) > 20:
        L.append(f"     ... +{len(dis) - 20} more")
    L.append("")

    # ------------------------------------------------------------- C. temporal conflicts
    L += ["=" * 74, "C. TEMPORAL CONFLICTS - assigned game earlier than placement", "=" * 74,
          "  Peter, Nov 5: this is NOT automatically an error. In-play betting exists and a placed",
          "  stamp may be a recording time. These are conflicts to adjudicate; a conflict becomes",
          "  CONFIRMED WRONG only where independent evidence shows the bet was pregame.",
          f"  Tolerance {int(BACK_TOL.total_seconds() // 3600)}h, reused from pin_bad so there is no rival threshold.", ""]
    conflicts = []
    for k, b in trk.items():
        gs, pl = tpa(b.get("game_start")), tpa(b.get("placed"))
        fs = tpa(b.get("first_seen"))
        anchor, anchor_kind = (pl, "placed") if pl else (fs, "first_seen (observation bound only)")
        if gs and anchor and gs < anchor - BACK_TOL:
            conflicts.append((k, b, gs, anchor, anchor_kind))
    L.append(f"  tracker-graded rows with a temporal conflict: {len(conflicts)} of {len(trk)}")
    for k, b, gs, anchor, kind in conflicts[:20]:
        L.append(f"     {b.get('book') or '?':<11} {(b.get('bet') or '')[:26]:<26} assigned {gs:%Y-%m-%d %H:%M} "
                 f"vs {kind} {anchor:%Y-%m-%d %H:%M} | result {b.get('result')}")
    if len(conflicts) > 20:
        L.append(f"     ... +{len(conflicts) - 20} more")
    L += ["", "  Pregame-versus-in-play cannot be established from the preserved fields for site=False",
          "  rows: the evidence that would settle it is either absent or is the field under test. These",
          "  therefore stay CONFLICT, not CONFIRMED WRONG.", ""]

    # ------------------------------------------------------------- D. independent identification
    L += ["=" * 74, "D. INDEPENDENT IDENTIFICATION + REGRADE (tracker-graded rows only)", "=" * 74,
          "  placed bounds the search and never selects; the window runs FORWARD by "
          + ", ".join(f"{k} {v}d" for k, v in sorted(FWD.items())) + ".",
          "  Selection is by name only. Two qualifying games stay AMBIGUOUS - proximity never breaks a tie.", ""]
    need, cand = {}, {}
    for k, b in trk.items():
        lg = b.get("league")
        anchor = tpa(b.get("placed")) or tpa(b.get("first_seen"))
        if not lg or lg not in FWD or not anchor:
            continue
        days = []
        d0 = anchor.astimezone(ET).replace(hour=12, minute=0, second=0, microsecond=0)
        for i in range(FWD[lg] + 1):
            days.append(d0 + timedelta(days=i))
        need.setdefault(lg, set()).update(days)
        cand[k] = (lg, days)
    tot_dates = sum(len(v) for v in need.values())
    L.append(f"  distinct (league, date) scoreboard reads required: {tot_dates}"
             + ("" if tot_dates <= MAX_DATES else f" - capped at {MAX_DATES}"))
    games = {}
    for lg, days in need.items():
        dl = sorted(days)[:MAX_DATES]
        try:
            games[lg] = tb.espn_games(dl, [lg]) or []
        except Exception as e:
            games[lg] = []
            L.append(f"  ESPN fetch failed for {lg}: {type(e).__name__}")
    L.append("  ESPN scoreboards are free (site.api.espn.com); no OddsPapi credit is spent by this audit.")
    L.append("")

    cls = {}
    deltas, exposure = [], []
    detail = []
    for k, b in trk.items():
        lg = b.get("league")
        own = team_words(b.get("game")) | team_words(b.get("bet"))
        anchor = tpa(b.get("placed")) or tpa(b.get("first_seen"))
        if k not in cand or not games.get(lg):
            cls["UNVERIFIABLE - no league, no anchor, or no schedule fetched"] = \
                cls.get("UNVERIFIABLE - no league, no anchor, or no schedule fetched", 0) + 1
            exposure.append(b)
            continue
        if len(own) < 2:
            cls["UNVERIFIABLE - the book's own text names fewer than two sides"] = \
                cls.get("UNVERIFIABLE - the book's own text names fewer than two sides", 0) + 1
            exposure.append(b)
            continue
        lo = anchor - BACK_TOL
        hi = anchor + timedelta(days=FWD[lg] + 1)
        q = []
        for g in games[lg]:
            gs = tpa(g.get("start"))
            if not gs or not (lo <= gs <= hi):
                continue
            if len(g.get("teams") or []) != 2:
                continue
            hits = [team_words(t.get("full")) & own for t in g["teams"]]
            a, c = hits
            if a and c and (a - c) and (c - a) and max(len(a), len(c)) >= 2:
                q.append(g)
        if not q:
            cls["UNVERIFIABLE - no qualifying game in the forward window"] = \
                cls.get("UNVERIFIABLE - no qualifying game in the forward window", 0) + 1
            exposure.append(b)
            continue
        if len(q) > 1:
            cls[f"AMBIGUOUS - {len(q)} qualifying games, not resolved by proximity"] = \
                cls.get(f"AMBIGUOUS - {len(q)} qualifying games, not resolved by proximity", 0) + 1
            exposure.append(b)
            detail.append((b, "AMBIGUOUS", [f"{t.get('full')}" for g in q[:3] for t in g["teams"]], None, None))
            continue
        g = q[0]
        if not g.get("final"):
            cls["UNVERIFIABLE - the identified game is not final on ESPN"] = \
                cls.get("UNVERIFIABLE - the identified game is not final on ESPN", 0) + 1
            exposure.append(b)
            continue
        a, h = sorted(g["teams"], key=lambda t: t["home"])
        p = my_parse(b.get("bet"), b.get("flip"))
        if not p:
            cls["UNVERIFIABLE - this audit's parser could not read the bet"] = \
                cls.get("UNVERIFIABLE - this audit's parser could not read the bet", 0) + 1
            exposure.append(b)
            continue
        got, pick = my_grade(p[0], p[1], p[2], a.get("full"), h.get("full"),
                             int(a.get("score") or 0), int(h.get("score") or 0))
        if got is None:
            cls[f"UNVERIFIABLE - the bet's side does not resolve against the identified game ({pick})"] = \
                cls.get(f"UNVERIFIABLE - the bet's side does not resolve against the identified game ({pick})", 0) + 1
            exposure.append(b)
            continue
        want_p = expected_profit(got, b.get("stake"), b.get("to_pay"))
        same_r = (got == b.get("result"))
        same_p = (want_p is None or b.get("profit") is None or abs(want_p - float(b["profit"])) < 0.015)
        if same_r and same_p:
            cls["CONFIRMED CORRECT - independent game, result and P&L all agree"] = \
                cls.get("CONFIRMED CORRECT - independent game, result and P&L all agree", 0) + 1
            continue
        kind = ("CONFIRMED WRONG - result disagrees" if not same_r
                else "CONFIRMED WRONG - result agrees but recorded P&L does not")
        cls[kind] = cls.get(kind, 0) + 1
        deltas.append((b, got, want_p))
        detail.append((b, kind, [a.get("full"), h.get("full")], got, want_p))

    L.append("  CLASSIFICATION:")
    for a, n in sorted(cls.items(), key=lambda kv: -kv[1]):
        L.append(f"     {n:>5}  {a}")
    L.append("")

    # ------------------------------------------------------------- E. the three answers
    conf = sum(n for a, n in cls.items() if a.startswith("CONFIRMED CORRECT"))
    wrong = sum(n for a, n in cls.items() if a.startswith("CONFIRMED WRONG"))
    amb = sum(n for a, n in cls.items() if a.startswith("AMBIGUOUS"))
    unv = sum(n for a, n in cls.items() if a.startswith("UNVERIFIABLE"))
    d_sum = round(sum((w if w is not None else 0) - float(b.get("profit") or 0) for b, _, w in deltas), 2)
    e_sum = round(sum(abs(float(b.get("profit") or 0)) for b in exposure), 2)
    L += ["=" * 74, "E. THE THREE ANSWERS", "=" * 74,
          f"  1. independently verified (tracker-graded): {conf} of {len(trk)}",
          f"  2. confirmed wrong {wrong} | ambiguous {amb} | unverifiable {unv}",
          f"  3. CONFIRMED dollar impact of correcting only the confirmed errors: {d_sum:+.2f}",
          f"     P&L EXPOSURE sitting on ambiguous or unverifiable rows: {e_sum:.2f} (NOT an error estimate",
          "     and never to be added to the figure above - it measures how much recorded profit rests",
          "     on assignments this audit could not verify)", ""]
    if detail:
        L.append("  rows behind those numbers:")
        for b, kind, who, got, want_p in detail[:30]:
            L.append(f"     [{kind[:34]}] {b.get('book') or '?'} {b.get('league') or '?'} "
                     f"{(b.get('bet') or '')[:24]} | recorded {b.get('result')} profit {b.get('profit')}"
                     + (f" | independent {got} profit {want_p}" if got else "")
                     + f" | game {' vs '.join([w for w in who[:2] if w])}")
        if len(detail) > 30:
            L.append(f"     ... +{len(detail) - 30} more")
    L.append("")

    # ------------------------------------------------------------- F. breakdowns
    L += ["=" * 74, "F. BY BOOK / SPORT / MARKET - confirmed wrong and exposure", "=" * 74]
    for lab, keyf in (("book", lambda b: b.get("book") or "?"),
                      ("sport", lambda b: b.get("league") or "?"),
                      ("market", lambda b: market_of(b))):
        w, e = {}, {}
        for b, _, _ in deltas:
            w[str(keyf(b))] = w.get(str(keyf(b)), 0) + 1
        for b in exposure:
            e[str(keyf(b))] = e.get(str(keyf(b)), 0) + 1
        L.append(f"  by {lab}:")
        for a in sorted(set(w) | set(e)):
            L.append(f"     {a:<16} confirmed wrong {w.get(a, 0):>3} | ambiguous/unverifiable {e.get(a, 0):>3}")
    L += ["", "  No error rate is carried from the book-settled group to the tracker-graded group. The two",
          "  face different missing-data and matching problems, and comparability is not assumed.", ""]

    L += ["Nothing was written. No result, profit, fixture or grading rule was changed. The dollar figure",
          "above is a PROPOSED adjustment for Peter's decision, not an applied correction."]
    ex.send("Bets GRADING AUDIT (read-only)", "\n".join(L))
    print(f"grade audit: settled {len(settled)}, book {len(book)}, tracker {len(trk)}, "
          f"verified {conf}, wrong {wrong}, ambiguous {amb}, unverifiable {unv}")   # counts only


if __name__ == "__main__":
    main()

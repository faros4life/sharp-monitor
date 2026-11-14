#!/usr/bin/env python3
"""
ONE FIXTURE MATCHER, shared by the live scorer and the scorecard (Peter, Nov 13 2026).

Peter: "Make the live scorer read the same fixture and historical-odds caches as the scorecard,
using the verified fallback" and "Both systems must use the same verified closing-price
calculation." Two implementations of the same rule is exactly how the first version of the
fixture exclusion went wrong, so there is one implementation and both callers import it.

TWO THINGS LIVE HERE:

  alt_fixtures()  - every fixture this repo already downloaded, from the stores other jobs
                    maintain: oddspapi/fixtures.json and any clv_backup snapshot. The live ledger
                    kept its own cache and read nothing else, which is why the Nov 12 Louisiana
                    row sat unscored while the fixture for that exact game was already on disk in
                    oddspapi/fixtures.json.

  ordered_match() - the ORDERED-SIDES test, used only after clv_ledger.find_fixture has returned
                    None. find_fixture compares unordered token sets, so a game whose two teams
                    share a token defeats it: "Louisiana @ UL Monroe" against participants
                    "Louisiana-Monroe Warhawks" and "Louisiana Ragin Cajuns" leaves the Cajuns
                    side carried only by "louisiana", which the Monroe side also carries, so the
                    match is refused. The row names its sides IN ORDER - away first - and OddsPapi
                    lists the home side as p1, so away->p2 / home->p1 resolves it one-to-one.

                    This is NOT a relaxed rule. It uses an ordering the unordered test throws
                    away, and it is stricter in every other respect: both sides must map
                    one-to-one, each on a token the other does not carry, within 12 hours, same
                    league, and the winner must be unique. An ambiguous pair is refused and the
                    reason is returned, because a wrong fixture produces a confidently wrong CLV,
                    which is worse than no CLV (Peter, Nov 5).
"""
import glob
import json
import re

import tracker_build as tb

# Fixture caches held OUTSIDE clv/state.enc. ONE list: clv_coverage, clv_fallback and
# clv_obs_audit all import it from here. Nov 14 - it was copied into three modules, so a new
# cache file added to one of them would have been read by one reader and silently ignored by the
# other two: a no-op that looks like success.
#   oddspapi/fixtures.json           written by the plimit-logger workflow (x2_tag / slow_hr)
#   oddspapi/fixtures_recovered.json written ONLY by clv_recover (the liquidity CLV recovery), so
#                                    recovery never contends with that workflow's own commits
ALT_PATHS = ["oddspapi/fixtures.json", "oddspapi/fixtures_recovered.json"]


def alt_fixtures():
    """{fixture id: (fixture, where it came from)} for fixtures held outside clv/state.enc."""
    out = {}
    for path in ALT_PATHS:
        try:
            for fid, f in (json.load(open(path)).get("fixtures") or {}).items():
                out.setdefault(fid, (f, path))
        except Exception:
            continue
    for path in sorted(glob.glob("clv_backup/*.enc")):
        try:
            for fid, f in (tb.dec(json.load(open(path))).get("fixtures") or {}).items():
                out.setdefault(fid, (f, path))
        except Exception:
            continue
    return out


def sides_of(s):
    """([away tokens, home tokens], how) for a row, or (None, why).

    snap.teams is preferred when it has two names, because espn_fill writes it from the
    scoreboard; otherwise the game text is split on the '@' that separates away from home.
    """
    tms = [(t.get("name") or "").strip() for t in (s.get("teams") or []) if (t.get("name") or "").strip()]
    if len(tms) >= 2:
        return [tb.toks(tms[0]) - tb.WEAK, tb.toks(tms[1]) - tb.WEAK], "snap.teams"
    txt = str(s.get("game") or "").replace(" v ", " @ ").replace(" vs ", " @ ")
    parts = [p for p in txt.split("@") if p.strip()]
    if len(parts) == 2:
        return [tb.toks(parts[0]) - tb.WEAK, tb.toks(parts[1]) - tb.WEAK], "game text"
    return None, "could not split the row into two sides"


def raw_sides_of(s):
    """[away text, home text] exactly as the row wrote them, or None. No tokenizing.

    Needed because tokenizing destroys the one character that distinguishes some venue titles -
    see truncation_pick below.
    """
    tms = [(t.get("name") or "").strip() for t in (s.get("teams") or [])
           if (t.get("name") or "").strip()]
    if len(tms) >= 2:
        return tms[:2]
    txt = str(s.get("game") or "").replace(" v ", " @ ").replace(" vs ", " @ ")
    parts = [p.strip() for p in txt.split("@") if p.strip()]
    return parts[:2] if len(parts) == 2 else None


def _names(f):
    out = []
    for k in ("n1", "n2", "p1", "p2"):
        v = str(f.get(k) or "").strip()
        if v:
            out.append((k, v))
    return out


def name_pick(s, cands):
    """(fid, why) when the raw team TEXT maps one-to-one onto exactly one candidate fixture.

    Nov 14. Every unresolved NBA unit in the registered-candidate tier was a Los Angeles game, and
    five billable /fixtures calls bought 79 fixtures and resolved none of them. The fixtures were
    never missing - the Nov 13 Clippers game was already in the cache. Two separate naming facts
    defeated the token test:

      * Kalshi titles the market "Oklahoma City vs Los Angeles C: Total Points", truncated
        mid-word, and tb.toks drops a one-character token, so "Los Angeles C" reduces to
        {los, angeles} and the Clippers/Lakers distinction is gone.
      * OddsPapi calls the team "LA Clippers", not "Los Angeles Clippers". So the row's
        {los, angeles} shares NOTHING with the fixture's {la, clippers, lac}, the side gets zero
        overlap, the fixture is skipped before the ambiguity test is ever reached, and the matcher
        reports "no fixture in any cache matches this league and date" - a message about the cache
        for a problem that was entirely in the names. Buying more fixtures could not have fixed it,
        and five credits say so.

    Two passes, both refusing rather than guessing. liquidity_monitor.team_side FIRST: it is the
    repo's own team matcher, it already handles abbreviations and city/nickname forms, and it
    returns None on a tie, so an ambiguous abbreviation stays ambiguous. Then a plain PREFIX test
    on the raw text, which is what rescues a truncation whose remaining letter is the only
    distinguishing mark ("Los Angeles C" prefixes "Los Angeles Clippers" and not "... Lakers").

    Every pass requires that both sides resolve, that they resolve to DIFFERENT participants, and
    that exactly one fixture survives. Peter, Nov 13: "Never force an ambiguous match." A bare
    "Los Angeles" against an LA derby matches both and is refused.
    """
    raw = raw_sides_of(s)
    if not raw or len(raw) != 2:
        return None, "no raw side text on the row"
    lg = s.get("league")
    try:
        import liquidity_monitor as lm      # lazy: this module stays a leaf
    except Exception:
        lm = None
    if lm is not None:
        hits = []
        for fid, f in cands:
            parts = [f.get("n1") or f.get("p1") or "", f.get("n2") or f.get("p2") or ""]
            idx = [lm.team_side(r, parts, lg) for r in raw]
            if None not in idx and idx[0] != idx[1]:
                hits.append((fid, parts, idx))
        if len(hits) == 1:
            fid, parts, idx = hits[0]
            return fid, (f"resolved by liquidity_monitor.team_side: '{raw[0]}'->"
                         f"{str(parts[idx[0]])[:20]} / '{raw[1]}'->{str(parts[idx[1]])[:20]}")
        if len(hits) > 1:
            return None, f"{len(hits)} fixtures resolve by team_side - ambiguous, not used"
    lo = [r.lower() for r in raw]
    if not any(len(r) > 3 for r in lo):
        return None, "side text too short to identify a team"
    hits = []
    for fid, f in cands:
        pick, ok = {}, True
        for i, side in enumerate(lo):
            picked = {v.lower() for _k, v in _names(f) if v.lower().startswith(side)}
            if len(picked) != 1:
                ok = False      # prefixes both participants, or neither: no information
                break
            pick[i] = next(iter(picked))
        if ok and len(set(pick.values())) == 2:
            hits.append((fid, pick))
    if len(hits) == 1:
        fid, pick = hits[0]
        return fid, (f"truncated title resolved by prefix: '{raw[0]}'->{pick[0][:20]} / "
                     f"'{raw[1]}'->{pick[1][:20]}")
    if len(hits) > 1:
        return None, f"{len(hits)} fixtures survive the prefix test - still ambiguous, not used"
    fid, why = ticker_pick(s, cands)
    if fid:
        return fid, why
    return None, f"the raw team text identifies neither or both participants ({why})"


def ticker_pick(s, cands):
    """(fid, why) from the VENUE'S OWN market ticker, when the row's prose cannot identify a team.

    Kalshi writes the ticker as KXNBATOTAL-26NOV13OKCLAC-223: the middle segment is the date
    followed by both teams' abbreviations. OddsPapi's participant strings carry the same codes
    ("LA Clippers LA Clippers LAC", "Oklahoma City Thunder Oklahoma City OKC"). So the two can be
    joined on codes the two systems independently recorded, which is reading an identity rather
    than inferring one - the distinction that matters for a row whose title was cut to "Los
    Angeles C" and whose fixture is spelled "LA Clippers", sharing no word at all.

    Refusals, deliberately strict: both participants must contribute a code of 2-4 letters, both
    codes must appear in the ticker, the two codes must differ, and exactly one candidate fixture
    may survive. Nothing is matched on one code alone, because a single code appears in every
    ticker that team plays in and would pick the wrong game on the wrong date.
    """
    tk = str(s.get("ticker") or "").upper()
    if not tk:
        return None, "no venue ticker on the row"
    hits = []
    for fid, f in cands:
        codes = []
        for k in ("p1", "p2"):
            up = [w for w in re.findall(r"[A-Z]{2,4}", str(f.get(k) or "")) if w.isupper()]
            codes.append(up[-1] if up else None)
        if None in codes or codes[0] == codes[1]:
            continue
        if all(c in tk for c in codes):
            hits.append((fid, codes))
    if len(hits) == 1:
        fid, codes = hits[0]
        return fid, f"venue ticker {tk[:34]} carries both {codes[0]} and {codes[1]}"
    if len(hits) > 1:
        return None, f"{len(hits)} fixtures match the ticker codes - ambiguous, not used"
    return None, "the ticker codes match no candidate fixture"


def ordered_match(s, fixtures, tp):
    """(fid, note) for the ONE fixture mapping one-to-one onto the row, or (None, why).

    fixtures: {fid: fixture}. tp: a timestamp parser (clv_ledger.tp), passed in so this module
    stays a leaf and cannot create an import cycle with clv_ledger.
    """
    sides, how = sides_of(s)
    if not sides or not all(sides):
        return None, f"no two distinguishable sides on the row ({how})"
    gs = tp(s.get("game_start"))
    lg = s.get("league")
    if not lg:
        return None, "no league on the row"
    ok, amb, cands = [], [], []
    for fid, f in fixtures.items():
        if f.get("lg") != lg:
            continue
        fs = tp(f.get("start"))
        if gs and fs and abs((fs - gs).total_seconds()) > 12 * 3600:
            continue
        cands.append((fid, f))
        p1 = tb.toks(f.get("p1") or "") - tb.WEAK
        p2 = tb.toks(f.get("p2") or "") - tb.WEAK
        # BOTH orientations are evaluated before deciding. The first version broke out of this
        # loop on the first orientation that had any overlap at all, so a fixture whose p1/p2
        # order is the reverse of the row's away/home order was judged on the WRONG pairing and
        # reported ambiguous. With snap.teams = [Ragin Cajuns, Louisiana-Monroe] against p1
        # Louisiana-Monroe / p2 Louisiana Ragin Cajuns, the losing orientation shares only
        # "louisiana" on both sides while the winning one separates cleanly - taking the first
        # was simply reading the pair backwards.
        best = None
        for a, b in ((p1, p2), (p2, p1)):
            ha, hb = a & sides[0], b & sides[1]
            if not (ha and hb):
                continue
            if (ha - hb) and (hb - ha):
                best = ("ok", None)
                break
            if best is None:
                best = ("amb", ha & hb)
        if best and best[0] == "ok":
            ok.append(fid)
        elif best:
            amb.append((fid, f, best[1]))
    if len(ok) == 1:
        return ok[0], f"ordered one-to-one match ({how})"
    if len(ok) > 1:
        return None, f"{len(ok)} fixtures match one-to-one - ambiguous, not used"
    # The token test has failed. Before blaming the cache or the date - which is the mistake that
    # cost five credits on 14 Nov - try the NAMES, on the candidates that passed league and date.
    fid, nwhy = name_pick(s, amb and [(fid, f) for fid, f, _sh in amb] or cands)
    if fid:
        return fid, nwhy
    if amb:
        f, shared = amb[0][1], amb[0][2]
        return None, (f"AMBIGUOUS: {str(f.get('p1'))[:26]} v {str(f.get('p2'))[:26]} - both sides "
                      f"share {sorted(shared)}, so neither is distinguished ({nwhy}). Not used.")
    if cands:
        return None, (f"{len(cands)} fixtures match the league and date but none maps onto the "
                      f"row's teams ({nwhy})")
    return None, "no fixture in any cache matches this league and date"


NON_TEAM = {"over", "under", "yes", "no", "o", "u"}


def resolve_side(fixture, team_text, league, which_team):
    """('1'|'2'|None, why). Which participant the bet's team text names.

    which_team() compares raw token overlap, so a venue abbreviation that shares no WORD with the
    participant name defeats it: "LAR -3.5" against "Los Angeles Rams LA Rams LA" has zero
    overlap, because "lar" is not one of {los, angeles, rams, la}. Eight rows with a fixture AND
    cached history produced no close for this reason alone.

    The fallback is liquidity_monitor.team_side, which is the repo's OWN team matcher and already
    handles this exact case ("ECU +6.5", "MEM") through abbr_match. Reusing it beats inventing a
    second abbreviation rule here, and it returns None on a tie, so an ambiguous abbreviation is
    still refused rather than forced.
    """
    t = str(team_text or "").strip()
    if not t:
        return None, "the bet text names no team at all"
    if t.lower() in NON_TEAM or not any(ch.isalpha() for ch in t):
        # "Under" with no number, or a bare price like "-108": this is not a team, and trying to
        # match it to a participant is how a totals row ends up scored as a side.
        return None, f"the bet text is '{t[:18]}', not a team - the side was never recorded"
    side = which_team(fixture, t)
    if side:
        return side, "token overlap"
    try:
        import liquidity_monitor as lm
        idx = lm.team_side(t, [fixture.get("p1") or "", fixture.get("p2") or ""], league)
    except Exception as ex:
        return None, f"abbreviation matcher unavailable ({type(ex).__name__})"
    if idx is None:
        return None, "held team not matched to either side of the fixture"
    return ("1" if idx == 0 else "2"), "abbreviation match (liquidity_monitor.team_side)"

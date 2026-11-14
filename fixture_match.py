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
    ok, amb = [], []
    for fid, f in fixtures.items():
        if f.get("lg") != lg:
            continue
        fs = tp(f.get("start"))
        if gs and fs and abs((fs - gs).total_seconds()) > 12 * 3600:
            continue
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
    if amb:
        fid, f, shared = amb[0]
        return None, (f"AMBIGUOUS: {str(f.get('p1'))[:26]} v {str(f.get('p2'))[:26]} - both sides "
                      f"share {sorted(shared)}, so neither is distinguished. Not used.")
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

"""LINE VALUE (Nov 12, 2026): push-aware value of moving a bet from the alert line to another line.

WHY THIS EXISTS. executor.half_point() credits a better line as `half_points x hp` subtracted from the
price's implied probability. That treats every half point as worth the same and ignores the settlement
difference between the two halves of a whole number:
    -3.5 -> -3   a LOSS (margin exactly 3) becomes a PUSH    worth  +m
    -3   -> -2.5 a PUSH becomes a WIN                        worth  +m * b      (b = net profit per $1)
These are different payoffs at ordinary odds, so "half the point" is only an approximation.

WHAT THIS MODULE IS. Pure arithmetic, no network, no I/O. It is NOT wired into live qualification.
executor.py calls it in SHADOW only (see LINE_VALUE_SHADOW there): the legacy rule keeps deciding.

THE CALCULATION (all outcomes per $1 staked):
    EV = P(win) * b  -  P(loss)            push = stake refunded, contributes 0
    b  = (1 - c) / c,   c = implied probability of the AFTER-FEE price
Prices passed in are ALWAYS the after-fee American price (what the ladders call best_price_american /
price_after_fee). Fees are applied exactly once, upstream, by the venue checkers. This module has no fee
code on purpose, so it cannot apply one twice.

INDEPENDENT PROBABILITY INPUT. EV needs absolute probabilities, and a price alone does not give them.
A two-sided quote at a line that can push (a whole number) gives only the probability CONDITIONAL on no
push: q = w / (w + l). Absolute probabilities also need the push mass m at that line:
    w = q (1 - m),   p = m,   l = (1 - q)(1 - m)
Moving to another line shifts probability across the integers between the two thresholds, each with its own
mass. Masses come from MASS below, every row carrying its dataset, dates, unique games and standard error.
A line or integer with no row is UNSUPPORTED: the answer is a labelled "unsupported", never a guess.

THRESHOLD FORM. Every bet is "bettor wins if X > c", pushes if X == c (c an integer), loses if X < c.
    spread  bettor handicap h : X = bettor margin,   c = -h
    over  total T             : X = total,           c = T
    under total T             : X = -total,          c = -T
A better line has a LOWER c.
"""
import math
from dataclasses import dataclass

CALC_VERSION = "line_value/v2"
EPS = 1e-9


class Unsupported(Exception):
    """The calculation cannot be done honestly. .code is a short machine-readable reason."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# ---------------------------------------------------------------- prices
def am_to_prob(a):
    """Implied probability of an American price. The input must already be AFTER FEES."""
    a = float(a)
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def prob_to_am(c):
    """American price whose implied probability is c (0 < c < 1)."""
    if not (0.0 < c < 1.0):
        raise Unsupported("price_out_of_range", f"c={c}")
    return -100.0 * c / (1.0 - c) if c >= 0.5 else 100.0 * (1.0 - c) / c


def net_per_dollar(am_after_fee):
    """b: net profit per $1 staked on a win at an after-fee American price."""
    c = am_to_prob(am_after_fee)
    return (1.0 - c) / c


def devig_two_sided(am_a, am_b):
    """Fair win probability of side A from a two-sided quote at ONE line, de-vigged proportionally.

    At a line that can push, this is the probability CONDITIONAL ON NO PUSH. It is not an absolute
    probability; Reference/outcomes() adds the push mass."""
    pa, pb = am_to_prob(am_a), am_to_prob(am_b)
    if pa + pb <= 0:
        raise Unsupported("bad_quote")
    return pa / (pa + pb)


# ---------------------------------------------------------------- thresholds
def cover_threshold(mtype, side, line):
    """c such that the bettor wins when X > c. See the module docstring."""
    if mtype == "spread":
        return -float(line)
    if mtype == "total":
        if side == "OVER":
            return float(line)
        if side == "UNDER":
            return -float(line)
    raise Unsupported("market_not_supported", f"{mtype}/{side}")


NO_TIE = {"NBA", "NCAAB", "NCAAF", "NHL", "MLB"}   # a margin of exactly 0 cannot happen there: ML == +/-0.5


def is_whole(c):
    return abs(c - round(c)) < EPS


# ---------------------------------------------------------------- masses
@dataclass(frozen=True)
class MassRow:
    m: float          # P(the event lands exactly on this integer | the closing line is exactly this integer) = hits / n
    n: int            # UNIQUE games (game_id) with that closing line
    se: float         # standard error of m (probability, not percent)
    source: str
    dates: str        # first..last game date among the games IN THIS ROW
    calc: str         # the conditioning rule
    hits: int = 0


_NFL_SRC = "nflverse/nfldata games.csv, regular season, unique game_id, closing spread_line/total_line"
MIN_N = 200           # a row with fewer unique games is never included: that line is Unsupported instead


def _nfl(hits, n, what, d0, d1):
    m = hits / n
    return MassRow(m, n, math.sqrt(m * (1 - m) / n), _NFL_SRC, f"{d0}..{d1}",
                   "share of games whose " + ("final total equals" if what == "total" else "favourite wins by exactly (signed result equals)")
                   + " the closing line, among games whose closing line is exactly that whole number; "
                   "not conditioned on anything else; overtime included (measure_nfl_push.py)", hits)


# ONLY rows with n >= MIN_N, generated by `measure_nfl_push.py --emit`. Everything else is Unsupported on purpose.
# NO pooled fallback: a total with no row of its own is Unsupported (Peter, Nov 12).
MASS = {
    ("NFL", "spread", 1): _nfl(7, 536, "margin", "1999-09-19", "2024-12-29"),
    ("NFL", "spread", 3): _nfl(105, 1140, "margin", "1999-09-12", "2026-11-09"),
    ("NFL", "spread", 4): _nfl(8, 324, "margin", "1999-09-12", "2024-12-30"),
    ("NFL", "spread", 6): _nfl(13, 341, "margin", "1999-09-12", "2026-11-01"),
    ("NFL", "spread", 7): _nfl(33, 478, "margin", "1999-09-12", "2026-11-01"),
    ("NFL", "spread", 10): _nfl(14, 204, "margin", "1999-11-14", "2026-11-01"),
    ("NFL", "total", 41): _nfl(11, 314, "total", "1999-09-19", "2024-12-08"),
    ("NFL", "total", 42): _nfl(5, 236, "total", "1999-09-12", "2024-12-28"),
    ("NFL", "total", 43): _nfl(12, 297, "total", "1999-09-12", "2024-12-22"),
    ("NFL", "total", 44): _nfl(14, 345, "total", "1999-09-19", "2024-12-23"),
    ("NFL", "total", 45): _nfl(7, 256, "total", "1999-09-19", "2024-12-08"),
    ("NFL", "total", 46): _nfl(3, 224, "total", "1999-10-31", "2024-12-15"),
    ("NFL", "total", 47): _nfl(6, 246, "total", "1999-11-07", "2024-12-22"),
}




def _pub(m, source, label, n=None, hits=None, dates="n/a"):
    """A PUBLISHED estimate (not measured here). n/hits when the source gives them, else None; se only when n is known."""
    se = math.sqrt(m * (1 - m) / n) if n else None
    return MassRow(m, n or 0, se if se is not None else float("nan"), source, dates, label, hits or 0)


_NCAAF_TOT_SRC = "https://www.dratings.com/half-point-values-for-college-football-totals/"
_NCAAF_TOT_LBL = "published historical estimate of the share of games landing on this total (not measured here)"
# Peter, Nov 12: integers 58-68 are NOT covered by the recovered table and stay unsupported; nothing below 47 or above 79.
for _k, _m in {47: .022, 48: .035, 49: .024, 50: .017, 51: .031, 52: .032, 53: .017, 54: .017, 55: .045, 56: .019, 57: .023,
               69: .029, 70: .015, 71: .014, 72: .032, 73: .021, 74: .011, 75: .016, 76: .035, 77: .016, 78: .013, 79: .019}.items():
    MASS[("NCAAF", "total", _k)] = _pub(_m, _NCAAF_TOT_SRC, _NCAAF_TOT_LBL)
NCAAF_TOTAL_GAP = range(58, 69)   # counted separately in coverage reports

_NCAAB_SPR_SRC = "https://www.boydsbets.com/college-basketball-key-numbers/"
_NCAAB_SPR_LBL = ("published closing-line estimate (not measured here): share of games whose favourite wins by exactly this number among games "
                  "closing at it (signed margin); applying it to a nearby starting line is an approximation")
for _k, (_h, _n) in {3: (87, 1563), 4: (66, 1502), 5: (50, 1315), 6: (48, 1247), 7: (49, 1096)}.items():
    MASS[("NCAAB", "spread", _k)] = _pub(_h / _n, _NCAAB_SPR_SRC, _NCAAB_SPR_LBL, _n, _h)

_NCAAB_TOT_SRC = "https://www.dratings.com/the-distribution-of-totals-for-betting-basketball/"
# (lo, hi, odd mass, even mass); 161 sits on two ranges in the source -> source_boundary_ambiguous, never a silent pick
NCAAB_TOTAL_BANDS = [(115, 126, .026, .023), (127, 136, .025, .022), (137, 152, .024, .021), (153, 160, .023, .021), (162, 172, .022, .020)]
NCAAB_TOTAL_AMBIGUOUS = {161}


def ncaab_total_mass(k):
    if k in NCAAB_TOTAL_AMBIGUOUS:
        raise Unsupported("source_boundary_ambiguous", f"NCAAB total {k}")
    for lo, hi, odd, even in NCAAB_TOTAL_BANDS:
        if lo <= k <= hi:
            return _pub(odd if k % 2 else even, _NCAAB_TOT_SRC,
                        f"published landing mass for {'odd' if k % 2 else 'even'} totals {lo}-{hi} (not measured here)")
    return None


def mass_row(sport, mtype, k):
    """The MassRow for integer event k (|margin| for spreads, the total for totals), or None."""
    if mtype == "spread":
        return MASS.get((sport, "spread", abs(int(k))))
    if sport == "NCAAB":
        return ncaab_total_mass(int(k))          # may raise source_boundary_ambiguous
    return MASS.get((sport, "total", int(k)))


def _mass(sport, mtype, k, line):
    if mtype == "spread" and k == 0 and sport in NO_TIE:
        return 0.0                                   # a tie cannot happen: nothing lands on 0
    row = mass_row(sport, mtype, k)
    if row is None:
        raise Unsupported("no_mass_row", f"{sport} {mtype} {k}")
    # the rows are conditional on the closing line being AT that integer; refuse to extrapolate far from it
    if abs(abs(float(line)) - abs(k)) > 1.0 + EPS:
        raise Unsupported("mass_far_from_line", f"integer {k} vs line {line}")
    return row.m


def _event_integer(mtype, side, x):
    """The integer the exact-landing event refers to: |margin| for spreads, the TOTAL for totals."""
    if mtype == "spread":
        return abs(x)
    return x if side == "OVER" else -x


# ---------------------------------------------------------------- reference and outcomes
@dataclass(frozen=True)
class Reference:
    """An independent probability reference at ONE line, for the bet's own side."""
    mtype: str
    side: str
    line: float            # the line the quote is AT (bettor's line: handicap for spread, total for total)
    q: float               # P(win | no push), de-vigged from a two-sided quote at `line`
    ts: str                # UTC timestamp the two-sided quote was read
    source: str            # venue/book the quote came from
    two_sided: bool = True


@dataclass(frozen=True)
class Outcomes:
    w: float
    p: float
    l: float
    c: float               # threshold these probabilities are at

    def check(self):
        assert abs(self.w + self.p + self.l - 1.0) < 1e-9 and min(self.w, self.p, self.l) >= -1e-12


def outcomes_at(ref, sport, line):
    """(win, push, loss) at `line` for the reference's own side, derived from the reference. Raises Unsupported."""
    if not ref.two_sided:
        raise Unsupported("reference_not_two_sided")
    if not (0.0 < ref.q < 1.0):
        raise Unsupported("reference_probability_out_of_range", f"q={ref.q}")
    c0 = cover_threshold(ref.mtype, ref.side, ref.line)
    c1 = cover_threshold(ref.mtype, ref.side, line)

    def ev_mass(x):
        return _mass(sport, ref.mtype, _event_integer(ref.mtype, ref.side, x), ref.line)

    # absolute probabilities at the reference line
    m0 = ev_mass(int(round(c0))) if is_whole(c0) else 0.0
    w0 = ref.q * (1.0 - m0)
    # G(c) = P(X > c): moving the threshold c0 -> c1 adds (c1 < c0) or removes (c1 > c0) the integers between
    f0, f1 = math.floor(c0 + EPS), math.floor(c1 + EPS)
    w1 = w0
    if c1 < c0 - EPS:
        for k in range(f1 + 1, f0 + 1):
            w1 += ev_mass(k)
    elif c1 > c0 + EPS:
        for k in range(f0 + 1, f1 + 1):
            w1 -= ev_mass(k)
    p1 = ev_mass(int(round(c1))) if is_whole(c1) else 0.0
    l1 = 1.0 - w1 - p1
    if w1 < -1e-12 or l1 < -1e-12:
        raise Unsupported("negative_probability", f"w={w1:.4f} l={l1:.4f}")
    out = Outcomes(max(w1, 0.0), p1, max(l1, 0.0), c1)
    out.check()
    return out


# ---------------------------------------------------------------- settlement
# How each venue settles a whole-number line. EMPTY until verified from the venue's own rules: a whole-number
# candidate on a venue with no entry is Unsupported, because the refund assumption is exactly what is unproven.
SETTLEMENT = {     # ACTIVE rules: {"book": "refund"} or {(book, sport, mtype): "refund"}. Only "refund" is modelled.
    # Nov 12: ProphetX NCAA D1 men's basketball spreads - Appendix A sec. H: an exact-strike margin voids the contract and
    # "collateral shall be returned to the applicable accounts"; whole-point strikes are listed. Read via a fetch of the
    # CFTC PDF (https://www.cftc.gov/filings/ptc/ptc10162634287.pdf). Everything else stays unsupported (see evidence).
    ("prophetx", "NCAAB", "spread"): "refund",
}

# EVIDENCE gathered Nov 12, 2026 from venue filings. Evidence is NOT activation: an entry here changes nothing until
# someone moves a confirmed "refund" into SETTLEMENT. status 'summary_read' = read through a summarising fetch of the
# CFTC PDF (the shell cannot reach cftc.gov), so the wording has NOT been re-read in the original text.
SETTLEMENT_EVIDENCE = [
    {"book": "prophetx", "sport": "NCAAB", "mtype": "spread", "rule": "refund", "status": "primary_text_quoted", "active": True,
     "finding": "exact-strike margin voids the contract; collateral returned; whole-point strikes are allowed",
     "source": "https://www.cftc.gov/filings/ptc/ptc10162634287.pdf (Appendix A section H)"},
    {"book": "prophetx", "sport": "NFL", "mtype": "spread/total", "rule": "refund", "status": "unconfirmed_for_mainline",
     "finding": "void and collateral returned, but the document read is the NFL player-statistic amendment",
     "source": "https://www.cftc.gov/filings/orgrules/rules08042613795.pdf"},
    {"book": "prophetx", "sport": "NBA/MLB/NHL", "mtype": "any", "rule": "unverified", "status": "not_read",
     "finding": "the NBA/NFL/NHL Mainline filings themselves were not located; every OTHER ProphetX sports filing read "
                "(soccer, CFL, FIBA, EuroLeague, NCAAB) voids an exact-strike SPREAD with collateral returned, and voids an "
                "exact-strike TOTAL without stating the collateral - a consistent pattern, not a read rule", "source": None},
    {"book": "prophetx", "sport": "any", "mtype": "total", "rule": "void_collateral_unstated", "status": "primary_text_quoted",
     "finding": "'void if the total exactly equals the Strike' - no sentence returns collateral for totals; ambiguous, unsupported",
     "source": "https://www.cftc.gov/filings/ptc/ptc0614266311.pdf (sec. E) ; ptc09222629066.pdf (sec. E)"},
    {"book": "polymarket_us", "sport": "any", "mtype": "total", "rule": "half_point_only", "status": "primary_text_quoted",
     "finding": "'All {total} thresholds are specified in half-point increments to avoid ties' - but the same document's "
                "example uses a whole number; a whole-number PMUS total should not exist and stays unsupported if seen",
     "source": "https://www.cftc.gov/sites/default/files/filings/orgrules/26/03/rules03272642617.pdf"},
    {"book": "novig", "sport": "NFL", "mtype": "total", "rule": "no_push_possible", "status": "summary_read",
     "finding": "line is always a half-integer so the total can never equal it; a void settles at a Fair Value Price "
               "(30-minute time-weighted composite), NOT a refund at the price paid",
     "source": "https://www.cftc.gov/filings/ptc/ptc07242611626.pdf"},
    {"book": "novig", "sport": "other", "mtype": "any", "rule": "unverified", "status": "not_read",
     "finding": "voids use the Fair Value Settlement Rule, so 'refund' must not be assumed on any Novig void",
     "source": "https://www.cftc.gov/filings/ptc/ptc07232611507.pdf"},
    {"book": "kalshi", "sport": "NBA/NFL", "mtype": "total/spread", "rule": "no_push_operator_decides", "status": "summary_read",
     "finding": "whole-number strikes may be listed; no push or void provision for an exact tie; the payout follows "
               "the contract's comparison operator ('above' is not met at equality)",
     "source": "https://kalshi-public-docs.s3.amazonaws.com/contract_terms/NBATOTAL.pdf ; NFLSPREAD.pdf"},
    {"book": "polymarket_us", "sport": "any", "mtype": "spread/total", "rule": "unverified", "status": "not_found",
     "finding": "the rulebook terms read do not say how a whole-number strike settles",
     "source": "https://www.cftc.gov/filings/orgrules/rules09112625091.pdf"},
]


def settlement_rule(book, sport=None, mtype=None):
    """The ACTIVE rule for this venue, most specific key first. None when nothing is active."""
    for k in ((book, sport, mtype), book):
        if k in SETTLEMENT:
            return SETTLEMENT[k]
    return None


def push_ok(book, c, sport=None, mtype=None):
    """Whole-number lines need a verified refund rule for the venue; half lines never push."""
    if not is_whole(c):
        return True
    if mtype == "spread" and abs(c) < EPS and sport in NO_TIE:
        return True                                  # pick-em in a no-tie sport cannot push
    if settlement_rule(book, sport, mtype) == "refund":
        return True
    raise Unsupported("settlement_rule_unverified", f"{book} on a whole-number line")


# ---------------------------------------------------------------- what a move would need (no reference required)
def requirements(sport, mtype, side, alert_line, cand_line, book):
    """Audit helper: which integers a move crosses, whether each has a mass row, and whether the venue's settlement
    rule is verified. Needs NO probability reference, so it can describe every historical or live decision."""
    out = {"calc": CALC_VERSION, "crossed": [], "mass_rows": {}, "mass_ok": True, "settlement": "n/a", "reasons": []}
    try:
        c0 = cover_threshold(mtype, side, alert_line)
        c1 = cover_threshold(mtype, side, cand_line)
    except Unsupported as u:
        return dict(out, mass_ok=False, reasons=[u.code])
    f0, f1 = math.floor(c0 + EPS), math.floor(c1 + EPS)
    xs = list(range(f1 + 1, f0 + 1)) if c1 < c0 - EPS else list(range(f0 + 1, f1 + 1)) if c1 > c0 + EPS else []
    needs = list(xs)
    for c in (c0, c1):
        if is_whole(c) and int(round(c)) not in needs:
            needs.append(int(round(c)))
    out["crossed"] = [_event_integer(mtype, side, x) for x in xs]
    for x in needs:
        k = _event_integer(mtype, side, x)
        row = mass_row(sport, mtype, k)
        far = abs(abs(float(alert_line)) - abs(k)) > 1.0 + EPS   # rows are conditional on the closing line being AT k
        out["mass_rows"][str(k)] = bool(row) and not far
        if row is None:
            out["reasons"].append(f"no_mass_row:{k}")
        elif far:
            out["reasons"].append(f"mass_far_from_line:{k}")
    out["mass_ok"] = all(out["mass_rows"].values())
    if is_whole(c0) or is_whole(c1):
        rule = settlement_rule(book, sport, mtype)
        out["settlement"] = rule if rule == "refund" else "unverified"
        if out["settlement"] == "unverified":
            out["reasons"].append("settlement_rule_unverified")
    return out


# ---------------------------------------------------------------- value registry (Peter, Nov 12 attachment)
# THREE INPUT TYPES, never mixed for one conversion:
#   prob_points  a credit in probability (0.0206 = 2.06 points) subtracted from the candidate's implied cost
#   mass         landing/push probabilities used ONLY through the win/push/loss calculation (needs a reference)
#   cents        an American-odds allowance on the price ladder (+100 == -100); probability equivalent depends on the start
VALUES = {
    ("NBA", "spread"): {"method": "prob_points", "half": .020604, "full": .041479, "input_type": "probability points",
                        "status": "provisional historical approximation", "source": "https://wizardofodds.com/games/sports-betting/nba/old-stuff/",
                        "assumptions": ["aggregate estimate, not a matchup probability", "additive credit does not preserve EV at every price",
                                        "sample excludes moves across zero"]},
    ("NBA", "total"): {"method": "prob_points", "half": .011576, "full": .024343, "input_type": "probability points",
                       "status": "provisional historical approximation", "source": "https://wizardofodds.com/games/sports-betting/nba/old-stuff/",
                       "assumptions": ["aggregate estimate, not a matchup probability", "additive credit does not preserve EV at every price"]},
    ("NFL", "spread"): {"method": "mass", "input_type": "landing mass", "status": "measured (nflverse, this repo)", "source": _NFL_SRC},
    ("NFL", "total"): {"method": "mass", "input_type": "landing mass", "status": "measured (nflverse, this repo)", "source": _NFL_SRC},
    ("NCAAF", "spread"): {"method": "prob_points_table", "input_type": "probability points", "status": "published estimate",
                          "source": "https://wizardofodds.com/games/sports-betting/college-football/",
                          "assumptions": ["source's 50% fair baseline, pushes excluded", "only the listed start->destination pairs"],
                          # (start handicap, destination handicap) -> credit; each full-point value starts from the ORIGINAL spread
                          "table": {(3, 3.5): .034178, (3, 4): .049390, (7, 7.5): .028483, (7, 8): .037874, (10, 10.5): .020296, (10, 11): .030492,
                                    (14, 14.5): .020920, (14, 15): .027482, (-3, -2.5): .034178, (-3, -2): .045551, (-7, -6.5): .028483,
                                    (-7, -6): .040396, (-10, -9.5): .020296, (-10, -9): .025907, (-14, -13.5): .020920, (-14, -13): .030338}},
    ("NCAAF", "total"): {"method": "mass", "input_type": "landing mass", "status": "published estimate", "source": _NCAAF_TOT_SRC},
    ("NCAAB", "spread"): {"method": "mass", "input_type": "landing mass", "status": "published estimate", "source": _NCAAB_SPR_SRC},
    ("NCAAB", "total"): {"method": "mass", "input_type": "landing mass", "status": "published estimate", "source": _NCAAB_TOT_SRC},
    ("NHL", "total"): {"method": "cents", "half": 25.0, "full": 50.0, "input_type": "American-odds cents",
                       "status": "Peter-approved placeholder assumption", "source": "Peter, Nov 12 2026 (midpoint placeholders)"},
    ("NHL", "spread"): {"method": "cents", "half": 37.5, "full": None, "ml_15": 80.0, "input_type": "American-odds cents",
                        "status": "Peter-approved placeholder assumption", "source": "Peter, Nov 12 2026 (midpoint placeholders)"},
    ("MLB", "total"): {"method": "cents", "half": 20.0, "full": 41.5, "input_type": "American-odds cents",
                       "status": "Peter-approved placeholder assumption", "source": "Peter, Nov 12 2026 (midpoint placeholders)"},
    ("MLB", "spread"): {"method": "cents", "half": 32.5, "full": None, "ml_15": 65.0, "input_type": "American-odds cents",
                        "status": "Peter-approved placeholder assumption", "source": "Peter, Nov 12 2026 (midpoint placeholders)"},
}
PRICE_INCREMENT = 1.0                               # cents; rounded CONSERVATIVELY (toward the less permissive price)


def cents_of(am):
    """Ladder coordinate: cents(-110) = -10, cents(+110) = +10, cents(+100) = cents(-100) = 0. Lower = more expensive."""
    return am + 100 if am < 0 else am - 100


def am_of_cents(c):
    return c - 100 if c < 0 else c + 100


def identical_outcomes(sport, mtype, c0, c1):
    """True when no achievable integer outcome separates the two thresholds (e.g. NHL ML vs -0.5)."""
    lo, hi = min(c0, c1), max(c0, c1)
    for k in range(math.floor(lo - EPS), math.ceil(hi + EPS) + 1):
        if lo - EPS <= k <= hi + EPS and not (mtype == "spread" and k == 0 and sport in NO_TIE):
            return False
    return True


def _steps(c0, c1):
    """(size, favourable): size of the move in threshold units and whether it improves the bettor's line."""
    d = round(c0 - c1, 6)
    return abs(d), d > 0


def convert(sport, mtype, side, alert_line, alert_am_after_fee, cand_line, cand_am_after_fee, book,
            tol_cents=0, worse=None, ref=None):
    """THE shared conversion. Used (in the replacement path only) for candidate selection, maximum acceptable price
    and the order recheck, so the three can never disagree. cand_am_after_fee=None asks only for the maximum price.
    Fees: every price passed in is already after fees (the venue checkers price them); nothing here adds a fee.
    Returns a record with method, input type, status, source, original line/price, target line, allowance,
    assumptions, calc version, max_am_after_fee and (when a price was given) qualifies. Never raises: an honest
    'cannot say' is status='unsupported' with a named reason, never a fallback to the old constant."""
    rec = {"calc": CALC_VERSION, "sport": sport, "mtype": mtype, "side": side, "book": book, "alert_line": alert_line,
           "alert_am_after_fee": alert_am_after_fee, "cand_line": cand_line, "cand_am_after_fee": cand_am_after_fee,
           "tol_cents": tol_cents, "method": None, "input_type": None, "value_status": None, "source": None,
           "allowance": None, "assumptions": [], "status": "unsupported", "reason": None, "detail": None,
           "max_am_after_fee": None, "max_prob": None, "qualifies": None}
    try:
        if mtype == "moneyline" and sport in NO_TIE and cand_line is not None and abs(abs(cand_line) - 1.5) < EPS:
            return _convert_ml15(rec, sport, side, alert_am_after_fee, cand_am_after_fee, book, tol_cents, worse)
        v = VALUES.get((sport, mtype))
        if v is None:
            raise Unsupported("market_not_supported", f"{sport} {mtype}")
        rec.update(method=v["method"], input_type=v["input_type"], value_status=v["status"], source=v["source"],
                   assumptions=list(v.get("assumptions") or []))
        c0, c1 = cover_threshold(mtype, side, alert_line), cover_threshold(mtype, side, cand_line)
        for c in (c0, c1):
            push_ok(book, c, sport, mtype)       # whole endpoints need the EXECUTION venue's verified rule, whatever the method
        if identical_outcomes(sport, mtype, c0, c1) and v["method"] != "mass":   # mass: same outcomes give the same w/p/l anyway
            rec.update(allowance=0.0, assumptions=rec["assumptions"] + ["identical winning outcomes: zero credit"])
            return _finish_prob(rec, alert_am_after_fee, cand_am_after_fee, 0.0, tol_cents, worse)
        size, fav = _steps(c0, c1)
        if v["method"] == "mass":
            if ref is None:
                raise Unsupported("no_reference", "mass method needs an independent two-sided reference")
            return _convert_mass(rec, ref, sport, book, alert_line, alert_am_after_fee, cand_line, cand_am_after_fee, tol_cents, worse)
        if v["method"] == "prob_points":
            if mtype == "spread" and (c0 < -EPS < EPS < c1 or c1 < -EPS < EPS < c0) and (c0 * c1 < 0):
                raise Unsupported("crosses_zero", "NBA spread sample excludes moves across zero")
            credit = {0.5: v["half"], 1.0: v["full"]}.get(size)
            if credit is None:
                raise Unsupported("move_size_not_listed", f"{size} points")
            rec["allowance"] = credit if fav else -credit
            return _finish_prob(rec, alert_am_after_fee, cand_am_after_fee, rec["allowance"], tol_cents, worse)
        if v["method"] == "prob_points_table":
            key = (_round_half(alert_line), _round_half(cand_line))
            credit, sign = v["table"].get(key), +1
            if credit is None:
                credit, sign = v["table"].get((key[1], key[0])), -1     # the listed pair walked backwards: the same credit, removed
            if credit is None:
                raise Unsupported("pair_not_in_table", f"{alert_line} -> {cand_line}")
            rec["allowance"] = sign * credit
            rec["assumptions"].append("reverse of a listed pair" if sign < 0 else "listed pair")
            return _finish_prob(rec, alert_am_after_fee, cand_am_after_fee, rec["allowance"], tol_cents, worse)
        if v["method"] == "cents":
            allow = {0.5: v["half"], 1.0: v["full"]}.get(size)
            if allow is None:
                raise Unsupported("move_size_not_listed" if size not in (0.5, 1.0) else "generic_full_point_not_supplied",
                                  f"{size} on {sport} {mtype}")
            rec["allowance"] = allow if fav else -allow
            return _finish_cents(rec, alert_am_after_fee, cand_am_after_fee, rec["allowance"], tol_cents)
        raise Unsupported("method_unknown", v["method"])
    except Unsupported as u:
        rec.update(status="unsupported", reason=u.code, detail=u.detail)
        return rec


def _round_half(x):
    return round(float(x) * 2) / 2


def _convert_ml15(rec, sport, side, alert_am, cand_am, book, tol_cents, worse):
    """ML <-> -1.5 on NHL/MLB: a specifically priced conversion (not a generic full-point move, no half-step on top)."""
    v = VALUES[(sport, "spread")]
    rec.update(method="cents", input_type=v["input_type"], value_status=v["status"], source=v["source"],
               assumptions=["ML <-> -1.5 specific allowance; not a generic full-point move"])
    # neither ML nor -1.5/+1.5 can push in a no-tie sport, so no settlement rule is needed here
    fav = (rec["cand_line"] or 0) > 0   # taking +1.5 is the better line; laying -1.5 is the worse line
    rec["allowance"] = v["ml_15"] if fav else -v["ml_15"]
    return _finish_cents(rec, alert_am, cand_am, rec["allowance"], tol_cents)


def _tol_prob(alert_am, tol_cents, worse):
    if not tol_cents:
        return 0.0
    if worse is None:
        raise Unsupported("worse_fn_missing")
    return am_to_prob(worse(alert_am, tol_cents)) - am_to_prob(alert_am)


def _finish_prob(rec, alert_am, cand_am, credit, tol_cents, worse):
    """prob-points: the candidate's implied cost minus the credit must not exceed the alert cost (+ tolerance)."""
    bar = am_to_prob(alert_am) + _tol_prob(alert_am, tol_cents, worse)
    max_c = bar + credit
    if not (EPS < max_c < 1 - EPS):
        raise Unsupported("incoherent_probability", f"max cost {max_c:.4f}")
    rec.update(status="ok", max_prob=max_c, max_am_after_fee=prob_to_am(max_c))
    if cand_am is not None:
        c_eq = am_to_prob(cand_am) - credit
        rec.update(c_eq=c_eq, qualifies=c_eq <= bar + EPS)
    return rec


def _finish_cents(rec, alert_am, cand_am, allow, tol_cents):
    """cents: the maximum price is the alert price moved `allow` cents down the ladder (+tolerance), rounded
    conservatively to the venue increment; +100 and -100 are the same even-money point."""
    max_c = cents_of(alert_am) - allow - tol_cents
    max_c = math.ceil(max_c / PRICE_INCREMENT) * PRICE_INCREMENT      # ceil = toward the LESS expensive price
    rec.update(status="ok", max_cents=max_c, max_am_after_fee=am_of_cents(max_c), max_prob=am_to_prob(am_of_cents(max_c)))
    if cand_am is not None:
        rec.update(qualifies=cents_of(cand_am) >= max_c - EPS)
    return rec


def _convert_mass(rec, ref, sport, book, alert_line, alert_am, cand_line, cand_am, tol_cents, worse):
    ev_bar, o0 = bar_ev(ref, sport, alert_line, alert_am, tol_cents, worse)
    o1 = outcomes_at(ref, sport, cand_line)
    if o1.w <= EPS:
        raise Unsupported("zero_win_probability")
    b = (ev_bar + o1.l) / o1.w
    if b <= 0:
        raise Unsupported("no_price_meets_bar", f"b={b:.4f}")
    c = 1.0 / (1.0 + b)
    if not (EPS < c < 1 - EPS):
        raise Unsupported("incoherent_probability", f"max cost {c:.4f}")
    used = requirements(sport, ref.mtype, ref.side, alert_line, cand_line, book)["mass_rows"]
    if any(abs(abs(float(alert_line)) - abs(int(k))) > EPS for k in used):
        rec["assumptions"].append("exact-closing-line mass applied to a nearby starting line (approximation)")
    rec.update(status="ok", ev_bar=ev_bar, max_prob=c, max_am_after_fee=prob_to_am(c), w=o1.w, p=o1.p, l=o1.l,
               w_alert=o0.w, p_alert=o0.p, l_alert=o0.l, reference={"line": ref.line, "q": ref.q, "ts": ref.ts, "source": ref.source})
    if cand_am is not None:
        ev1 = ev_per_dollar(o1, cand_am)
        rec.update(ev=ev1, qualifies=ev1 >= ev_bar - EPS)
    return rec


# ---------------------------------------------------------------- value
def ev_per_dollar(o, am_after_fee):
    """Expected profit per $1 staked. push refunded (0)."""
    return o.w * net_per_dollar(am_after_fee) - o.l


def bar_ev(ref, sport, alert_line, alert_am_after_fee, tol_cents=0, worse=None):
    """The EV the legacy rule is protecting: the alert bet at the alert line, priced `tol_cents` worse when the
    venue carries the tolerance. `worse(am, cents)` is executor.cents_worse (passed in to keep this pure)."""
    o = outcomes_at(ref, sport, alert_line)
    am = alert_am_after_fee
    if tol_cents:
        if worse is None:
            raise Unsupported("worse_fn_missing")
        am = worse(am, tol_cents)
    return ev_per_dollar(o, am), o


def evaluate(ref, sport, book, alert_line, alert_am_after_fee, cand_line, cand_am_after_fee, tol_cents=0, worse=None):
    """One candidate through convert() (ref may be None for the non-mass methods)."""
    mtype, side = (ref.mtype, ref.side) if ref is not None else (None, None)
    return convert(sport, mtype, side, alert_line, alert_am_after_fee, cand_line, cand_am_after_fee, book, tol_cents, worse, ref)


def max_acceptable(ref, sport, book, alert_line, alert_am_after_fee, cand_line, tol_cents=0, worse=None):
    """The worst after-fee price at cand_line that still qualifies: the SAME convert() as evaluate()."""
    mtype, side = (ref.mtype, ref.side) if ref is not None else (None, None)
    return convert(sport, mtype, side, alert_line, alert_am_after_fee, cand_line, None, book, tol_cents, worse, ref)

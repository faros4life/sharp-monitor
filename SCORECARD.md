# SCORECARD — master list of everything we have run

**Standing as of 2026-11-11.** Reporting view only. This file **registers nothing, promotes nothing
and changes nothing**: `REGISTRY.md` stays authoritative for names and scope, `SPLITS.md` for the
paper-split records, `CLV_STANDARD.md` for the CLV basis, `BUCKETS.md` for the standard cuts. Where
this file and one of those disagree, the other file wins and this one gets corrected.

Units only, 1u flat after fees. No dollar figures in this repo.

## The policy this scorecard applies (FUTURE research only; adopted 11 Nov)

- **Primary evidence is realized after-fee profitability, from actual fills at the alert price or
  better.** CLV is supporting evidence. Fills are never assumed.
- **CLV is never an automatic veto.** Provisional and modelled CLV veto nothing.
- Certified same-line, modelled/converted and missing CLV are reported **separately**, each with
  coverage, n and a 95% CI. Never pooled into one headline.
- Certified CLV contributes to a verdict only when it is **precise** (certified n ≥ 100, roughly
  ±0.4c) **and representative** across venue, league, market and lead-time band. There is **no
  fixed coverage percentage** — the 50% idea was tested and rejected (see "Why not a coverage
  threshold" below).
- Multiplicity is priced **before** any other reason is cited.
- **No fixed CLV cutoff in either direction.** A point estimate decides nothing; only an interval does.
- Provisional reads carry their known bias (~0.6 pt optimistic on the steam feed) stated inline.

### Classifications

| Label | Meaning |
| --- | --- |
| **CLEAR FAIL** | Realized-unit CI excludes zero on the negative side, or a precise and representative certified CLV CI does. |
| **CONTINUE TESTING** | The default. Intervals straddle zero, multiplicity unmet, no fills, or CLV coverage unrepresentative. A statement about **ignorance, not profit** — authorizes more paper observation and nothing else. |
| **POTENTIAL PASS** | Realized-unit CI excludes zero on the positive side **with actual fills**, certified CLV ≥ 0 and precise and representative, both chronological halves positive, multiplicity survived, rule pre-registered. All of it, or it continues. |

**Nothing in this repo currently holds an actual fill record.** Across every population read on
11 Nov — steam feed, liquidity board, EV study, CBB openers — fills are zero and all unit figures
are hypothetical at the alert price after fees. Under the policy above the honest ceiling for every
paper test today is CONTINUE. The binding constraint is fills, not CLV.

---

## A. Registry entries (REGISTRY.md 1–32)

`last read` = when this scorecard last saw real numbers for that entry. Blank means not read on
11 Nov; its own report is the source. Nothing here supersedes a registered verdict.

### LIVE — real money

| # | Name | Latest numbers | Fills | Last read | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | LANE 1 | — | live money | — | KEPT UNCHANGED |
| 2 | RESTING BIDS | — | live money | — | KEPT, graded separately |

### MANUAL — Peter bets by hand

| # | Name | Latest numbers | Fills | Last read | Status |
| --- | --- | --- | --- | --- | --- |
| 3 | PETER — FEED PLAYS | — | real money | — | KEPT |
| 4 | HR SCANNER FLAGS | — | real money | — | KEPT |
| 5 | STREET VALUE | — | real money | — | KEPT |
| 6 | STEAM | feed-wide 708 graded, −0.26u, −0.0%, day-CI [−6.4, +5.7]% | none (paper since 17 Oct) | 11 Nov | KEPT + ON · **CLEAR FAIL** feed-wide |
| 7 | BETS BOARD PLAYS | — | real money | — | keep/delete open as a lane |

### PAPER TESTS

| # | Name | Latest numbers | Fills | Last read | Status |
| --- | --- | --- | --- | --- | --- |
| 8 | LANE 2 | — | none | — | paper + dry-run; go-live package owed |
| 9 | LIQ-BOT | — | none | — | approved as a bot, HELD OFF |
| 10 | POST & WAIT | — | none | — | paper |
| 11 | SLOW-HR | diagnostic at 64 of 100 | none | — | KEPT |
| 12 | DOG BAND | — | none | — | paper, forward from 7 Nov |
| 13 | LIQ-SMALL | — | none | — | paper |
| 14 | BOARD v2 | — | none | — | parallel grading |
| 15 | P-NHL-DOGS | — | none | — | checkpoint 50, judged 100 |
| 16 | P-CFB-OVER / P-NFL-OVER | — | none | — | same bars as 15 |
| 17 | HR-A | — | none | — | judged at 100 sightings |
| 18 | EXCHANGE MISPRICE | ≥+2% EV on a SENT alert; broad build EDGE2 in `paper_rules` item 61 | none | 11 Nov | readout at 100 · **distinct from 21** |
| 19 | PLIMIT-CUT MISPRICE | — | none | — | readout at 100 gettable |
| 20 | EX-B | — | none | — | judged at 100 |
| 21 | EV TRIGGER B / B-TOTALS | see section B | none | 11 Nov | **all four triggers FAIL their gate**; final report never sent |
| 22 | RETAIL LAG | — | none | — | Muse recommends delete, unadopted |
| 23 | NCAAB OPENERS | first read 7 Nov, 61 sightings, −0.66% → STOP. Out-of-sample 66 more at −1.25%; all 127 at −0.97%, beat close 44.1%. MAE ours 14.28 vs open 13.58 | none | 11 Nov | **CLEAR FAIL, CLOSED.** Registry text still says "first read early December" |

### LENSES — slices, not standalone strategies

| # | Name | Status |
| --- | --- | --- |
| 24 | ML_STAY | lens inside the liquidity lanes |
| 25 | PULL_FADE | Muse recommends retiring, unadopted |
| 26 | SOLO | lens |

### RESEARCH / MEASUREMENT — not betting lanes

| # | Name | Status |
| --- | --- | --- |
| 27 | MODEL LAB | running, one fixed model per league |
| 28 | NBA TOTALS MODEL | paper |
| 29 | SMALL-BOOK SURGE | Muse recommends closing, unadopted |
| 30 | CLV-WORKS | per-row export landed 9 Nov |
| 31 | TOTALS STUDY | pre-registration drafted, ratification outstanding |
| 32 | CLOSE-VS-CLOSE / DECAY CURVE | Run 2 owed |

### CLOSED — names retired, never reuse

**EV-LANE A** · **EXCHANGE-LAG ×4** · **GATE 1** · **LANE 3 (live)**

---

## B. EV study triggers (registry 21), read 11 Nov from the `ev-study` branch

Collection is healthy — commits every 5–12 minutes through 11 Nov 03:24Z. Gate is the study's own:
≥50 graded, positive average CLV, positive flat record; A/B on consensus CLV, M on Pinnacle CLV.
CLV in cents. **Zero fills.**

| Trigger | Graded | Units | ROI | Units 95% CI | H1 / H2 | Certified CLV (cov.) | Modelled CLV | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A cross-book ≥2c | 8,373 | −289.65u | −3.5% | [−6.1, −0.5]% | −5.0 / −2.0 | −0.68c (6%) | −1.78c | **CLEAR FAIL** |
| A qualifying ≥3c | 1,834 | −147.56u | −8.0% | — | −8.1 / −8.0 | — | −2.67c | **CLEAR FAIL** |
| B Pinnacle ≥3% EV | 144 | −6.23u | −4.3% | [−24.5, +16.9]% | −8.2 / −0.5 | **+1.06c** [+0.51, +1.62] (33%) | −0.62c | **CLEAR FAIL** (units) |
| M move-watch gettable | 398 | +5.81u | +1.5% | [−7.9, +10.7]% | −1.0 / +3.9 | −0.46c [−0.65, −0.27] (41%) | −0.61c | **CLEAR FAIL** |
| MK maker fair−1c | 335 | +3.22u | — | — | — | — | −0.93c | **CLEAR FAIL** |
| MK maker fair−2c | 114 | +9.38u | — | — | — | — | −0.49c | **CLEAR FAIL** |

Pre-registered judged buckets, all **negative**: J1 B ex-NHL (92, +0.15c, −1.68u) · J2 B NBA
(63, +0.26c, −0.21u) · J3 B fresh reference (54, −0.01c, +0.30u) · J4 move-watch ex-NHL
(228, −0.60c, +1.37u).

Two findings worth keeping:
- **The move-watch control beat the gettable side.** Not-gettable moves held +1.98c against +0.18c
  for gettable, and the longest-surviving discrepancies held best of all. Persistence selects
  against us.
- **Excluded suspect rows are the most profitable bucket in the study** (+287.83u on 1,059 graded,
  +27.2%). That is the misread-quote pile and the strongest argument for keeping the exclusion.

---

## C. Research runs with no registry entry (11 Nov session)

All read-only, zero paid credits, nothing registered.

| Run | What it was | Result | Verdict |
| --- | --- | --- | --- |
| **Cross-market 83-cell sweep** | 23 pre-registered predictor families across STEAM (708 graded, 444 games) and LIQ (2,190 graded, 1,542 games), never pooled; studentized max-t FWER control | Best cell FWER **p = 0.489**. Both populations flat at top level: STEAM −0.0% [−6.2, +5.7], LIQ −0.9% [−4.8, +3.4] | **NO PASS**, nothing promoted |
| **NCAAF spread dogs** | Steam dogs, executable price | 97 graded, +10.14u, +10.5%, CI [−5.6, +25.1]. +11.09u of it from the 29 pre-grading-era alerts (8–17 Oct); other 50 are +0.91u | **CONTINUE** — withdrawn as a candidate |
| **P-CFB-STEAM-DOG** | Proposed NCAAF dog trigger | Withdrawn after reconciliation: units came from the cohort with no CLV reading | **WITHDRAWN** |
| **CBB openers audit** | Root-cause of registry 23's failure | Model runs **+4.97 pts high** vs the final (Pinnacle open −0.91). 71 of 80 sightings had our number above Pinnacle's. Gap size, timing and exchange pricing all cleared | **CLEAR FAIL, cause identified** |
| **H-CBB-EX1** | Proposed CBB exchange-mispricing test at the opener | Withdrawn — duplicates registry 21's trigger B construction; opener path has no staleness bound, no depth gate, a parallel fee copy, 51% whole-number lines on an untested push branch | **WITHDRAWN** |
| **Trigger B → NCAAB Top 100** | Feasibility of extending 21 to CBB | Affordable (~6–11k Odds API credits/30d against ~33k headroom) but blocked: the $250 depth test needs live venue reads that history lacks, and the parent trigger is already failing | **NOT PROCEEDING** |
| **B UNDERS** | Post-hoc cell inside 21 | 44 graded, +10.38u, +23.6%, but 32% certified, certified CI [−0.14, +1.09] contains zero, units CI [−4.2, +48.9] contains zero, win rate 59.1% [44.6, 73.6] vs 47.6% break-even, strictest subset 13 plays | **CLOSED NO PASS** |
| **Persistent exchange mispricing after Pinnacle moves** | 5–15 min executable window | Is registry 21's M move-watch. The 5–15 min band has **zero gettable observations** — detection lag is bounded by the poll loop. Control held 11× better | **NO NEW TEST** |
| **STEAM 6–24h** | Lead-time cell from the 83-cell sweep | 302 alerts on **217 unique games**. One per game: +18.41u, +8.5%, day-CI **[−1.3, +18.5]** — contains zero. Top 3 of 21 days = 79% of profit. NCAAF +27.2% carries it, NHL −66.6%. 110 of 217 already inside `paper_rules` item 27. FWER p = 0.981. 0% certified | **CONTINUE TESTING**, no separate registration |
| **CLV sensitivity audit** | Whether CLV requirements were killing profitable strategies | One strategy (STEAM 6–24h) was rejected on the wrong stated reason — multiplicity was the sound one. No verdict overturned. Certified-vs-modelled pooling bias is real and one-directional | Policy adopted, above |

---

## Why not a coverage threshold

A 50% certified-coverage rule was proposed and **rejected on evidence**:

- **Certification is strongly non-random.** NHL certifies at 56% against NBA 7%, NCAAF 9%, NFL 10%.
  ProphetX 18% against Kalshi 4% and Polymarket US 4%. Certified rows have a median lead time of
  212 min against 359, and a median price of −105 against −113. A certified CLV therefore describes
  a different population than the strategy it judges.
- **The two halves are not interchangeable.** On M move-watch the same rows return +10.7% certified
  against −4.9% modelled; on B, −8.5% against −2.3%. Opposite directions.
- **Coverage was never the binding quantity.** Per-row CLV sd is 2.18c, so precision depends on
  certified *n*: ±1.14c at n=14, ±0.61c at n=50, ±0.43c at n=100, ±0.21c at n=400. A 90%-covered
  20-row test is uninformative; a 6%-covered 496-row test (A cross-book) is precise.

Daily certification runs 7–23% with no trend — a structural property of same-line matching, not a
backlog that clears.

---

## Open discrepancies to settle (not changed here)

1. **Registry 23** reads "First read early December." The first read happened 7 Nov at 61 sightings
   and STOPped. `ncaab_openers.py` also calls itself "item 28" while the registry calls it 23.
2. **Registry 21** has no recorded final verdict. The report due 10 Nov was never sent; the live
   readout has all four triggers failing.
3. **18 vs 21 thresholds are not in conflict.** 18 is ≥+2% EV on a SENT alert (`paper_rules` item 61,
   no depth gate, from 3 Nov 11:45 ET). 21 is ≥3% EV with a ≥$250 depth gate (`ev_sightings.py`,
   approved 27 Oct). Trigger A's `A_MIN, A_QUAL = 0.02, 0.03` are **cents**, not percent — a third
   source of the confusion.
4. **`ncaab_grade.py`'s CLV is not an entry CLV.** It computes `close fair / open fair − 1` at
   Pinnacle, with no entry price and no fees, so registry 23's −0.66% is a line-movement metric and
   is not comparable to any figure under `CLV_STANDARD.md`.
5. **No script imports `clv_std`.** `ncaab_grade.eff()` is a fifth parallel fee implementation and
   returns the raw price for any venue key it does not recognise.

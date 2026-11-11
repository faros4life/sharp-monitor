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
| 1 | LANE 1 | **ACTUAL FILLS — the only realized record in the system.** 41 graded bot fills → **33 verified same-line (80.5% coverage)**. Executed CLV **+0.37%** [−1.46, +2.19], beat the close **24/33 = 72.7%** Wilson [55.8, 84.9] — **excludes a coin flip**. Record 20-13, **+3.70u on 35.77u staked, ROI +10.3%**. Halves: H1 +1.38% / **H2 −0.59%**. Venue: Novig 40, PM-US 1 (bracketed, out of headline). Taker basis (conservative; maker would read better) | **33 real fills** | 11 Nov (`executed_clv`) | **CONTINUE TESTING** — strongest evidence anywhere, but certified n=33 is below the n≥100 precision bar and H2 CLV is negative |
| 2 | RESTING BIDS | — | live money | — | KEPT, graded separately |

### MANUAL — Peter bets by hand

| # | Name | Latest numbers | Fills | Last read | Status |
| --- | --- | --- | --- | --- | --- |
| 3 | PETER — FEED PLAYS | — | real money | — | KEPT |
| 4 | HR SCANNER FLAGS | — | real money | — | KEPT |
| 5 | STREET VALUE | — | real money | — | KEPT |
| 6 | STEAM | feed-wide 708 graded, −0.26u, −0.0%, day-CI [−6.4, +5.7]% | none (paper since 17 Oct) | 11 Nov | KEPT + ON · **CLEAR FAIL** feed-wide |
| 7 | BETS BOARD PLAYS | **v3 rule (from 4 Nov, ratified 6 Nov as the rule the historical record ran on). PLAY: 62 graded, 42-20, +20.43u, +33.0%**, 22 Oct–10 Nov, all NBA totals. **LEAN: 308 graded, +20.65u, +6.7%**, from 5 Nov. **DEAD: 228 graded, −9.36u, −4.1%** | board paper for live money since 4 Nov; PLAY calls hand-bet | 11 Nov | **CONTINUE TESTING.** v3 PLAY *is* the LIQ-BOT rule (entry 9), so this is that lane's paper record — not a second strategy |

### PAPER TESTS

| # | Name | Latest numbers | Fills | Last read | Status |
| --- | --- | --- | --- | --- | --- |
| 8 | LANE 2 | — | none | — | paper + dry-run; go-live package owed |
| 9 | LIQ-BOT | **registry-9 definition (NBA total, lead ≥240 min): n=151, +23.81u — at the recorded ALERT price, which is NOT executable.** `liq_history_test` measured **3.42% fee drag** between the alert basis and the executable one, which is the whole sign difference. No verified-CLV leg of its own | none | 11 Nov (NBA totals master scorecard) | **INSUFFICIENT EVIDENCE** — approved as a bot, HELD OFF |
| 10 | POST & WAIT | — (own report not read this session) | none | — | paper |
| 11 | SLOW-HR | **508 sightings, all with a close. Avg CLV −1.73c, beat close 135/508 = 26.6%.** Judged (not LATE) 465, −1.70c, 129/465. LATE 43, −2.07c. Type P 500, −1.71c; Type L 8, −3.15c. NFL −2.63c (160) · NCAAF −1.35c (301) · NHL −1.12c (47). Deviation on record: graded vs Pinnacle close, consensus close not wired | none | 11 Nov (`slow_hr`) | **CLEAR FAIL on pricing** — negative in every league and both types |
| 12 | DOG BAND | — | none | — | paper, forward from 7 Nov |
| 13 | LIQ-SMALL | $25–50k-print subset **priced from Lane 3 rows — not an independent population**. Its executable entries are SIMULATED depth checks, not orders. Lane 3 shadow: 27 rows in window, **0 confirmed fills**, 7 simulated | **0 confirmed** | 11 Nov | **INSUFFICIENT EVIDENCE** |
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
| 24 | ML_STAY | **609 logged, 22 graded, 16-6, +5.33u, +24.2%**, CLV mean +0.009 (n=22). H1 +27.5% / H2 +20.9%. NBA 9 · NCAAF 7 · NFL 5 · NHL 1. Forward from 2 Nov. Source: `lanes/lanes.json`, read 11 Nov. Limitation: 22 of 609 graded, so 96% is still pending |
| 25 | PULL_FADE | **74 logged, 42 graded, −6.02u, −14.3%.** H1 −0.7% / H2 −28.0%. No CLV recorded. Source: `lanes/lanes.json`, 11 Nov. **Kill bar met** (readout 40, ≤0.00u/play) — Muse recommends retiring, unadopted |
| 26 | SOLO | **819 logged, 35 graded, 22-13, +0.56u, +1.6%**, CLV mean −0.008 (n=35). H1 +29.8% / **H2 −25.0%**. NBA 16 · TENNIS 10 · NCAAF 6 · NFL 3. Source: `lanes/lanes.json`, 11 Nov. Limitation: 35 of 819 graded; promotion needs ≥+0.08u/play |

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

## B2. Feed-level populations (read 11 Nov, deduped one play per game+market+side)

Units are 1u flat after fees at the alert price. CIs are day-clustered. **No fills in any of these.**

| Population | Graded | Units | ROI | Day-clustered 95% CI | Pinnacle CLV available |
| --- | --- | --- | --- | --- | --- |
| Steam feed, NBA+NFL+NCAAF+NHL | 708 | −0.26u | −0.0% | [−6.4, +5.7]% | none certified; provisional −0.80% on 373 |
| Steam feed, NCAAB (split: OPEN) | 285 | +10.92u | +3.8% | [−5.0, +12.0]% | none certified; provisional −1.40% on 279 |
| Liquidity board, all leagues | 2,665 | −29.04u | −1.1% | [−4.4, +2.5]% | **none of any kind** — only the trigger exchange's own close, which `CLV_STANDARD.md` §4 bars as a gate |

## B2b. The NBA-totals family — ONE nested strategy, four reports

Per the NBA totals master scorecard (10 Nov), narrowest last. **Nothing is summed across them,
because each inner set is the outer set filtered:**

```
registry 9   NBA total, lead >= 240 min                            (clv_rootcause:351)
BOARD v3     + money still there, one per game total, cap 5        (board_build:191)
Lane 3       + survives 15 min, not pulled, price not moved        (executor.board_plays)
LIQ-SMALL    + new money $25-50k, PRICED FROM Lane 3 rows          (liq_small_fwd)
```

**v3 PLAY and LIQ-BOT are the same strategy, not two findings.** The four NBA liquidity splits
sitting at ELIGIBLE are cuts of this one record.

### Board v3 PLAY investigated (11 Nov) — profitability survives dedupe and price, fails on CLV

| Basis | n | Games | Days | Record | Units | ROI | Day-clustered 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| As published (trigger book) | 62 | **62** | 19 | 42-20 | +20.43u | +33.0% | [+11.3, +54.9]% |
| **EXECUTABLE: gettable at the alert price or better at any bettable exchange** | **53** | **52** | **17** | **36-17** | **+17.81u** | **+33.6%** | **[+10.7, +56.0]%** |
| Executable, one per game | 52 | 52 | 17 | 35-17 | +16.90u | +32.5% | [+8.8, +55.7]% |
| Not gettable | 9 | — | — | — | +2.62u | +29.1% | — |

**Execution standard applied: the alert price or nothing** (with resting bids we get our price or no
fill), same line, at a venue Peter can bet — Kalshi, Novig or ProphetX, after each venue's own fee.
The trigger venue is irrelevant to whether a play was executable.

- **Dedupe: survives.** 53 executable calls sit on 52 distinct games; v3 already enforces one play
  per game total. Deduped: +32.5%.
- **Executable price: survives.** **53 of 62 (85%) were gettable.** Execution venue would have been
  **Novig 39 · Kalshi 10 · ProphetX 4** — the same venue profile as Lane 1's real fills (40 of 41
  at Novig). Of the 9 that were not gettable, 4 had no bettable exchange on that exact line and 5
  were quoted worse than the alert price after fees.
  **Correction, 11 Nov:** an earlier version of this row screened on the *trigger* book and reported
  only 41 Kalshi plays as executable, haircutting 34% as unbettable Polymarket GLOBAL. That was
  wrong. **15 of the 21 globally-triggered plays (71%) were available at the alert price or better
  on Novig, Kalshi or ProphetX.** A global trigger means the trigger venue was unbettable, not the
  play.
- **Multiplicity: survives.** Bonferroni on the day-clustered CI — m=1 [+11.0, +56.2] · m=3
  [+5.8, +61.1] · m=5 [+3.8, +63.6] · m=8 [+1.8, +64.1] · **m=12 [+0.3, +66.9], still excludes
  zero.**
- **Chronological stability: decaying.** H1 +51.3% [+27.7, +73.7] · **H2 +16.6% [−14.7, +55.5]
  (contains zero)**. Weeks +43.5% · +47.2% · +18.2% · +21.7% — all positive, trending down.
  Forward only, since the 6 Nov rebuild: 12 plays, +5.69u, +47.4%, CI [+5.4, +98.0].
- **Selection bias: present.** The rule was rewritten twice with outcomes visible and each rewrite
  improved the record — v1 PLAY +17.3% (n=6) → v2 +29.0% (n=32) → **v3 +33.0% (n=62)**. v3 was
  authored 4 Nov with 22 Oct–3 Nov results in view.
- **Certified CLV: negative, but computed on a mis-specified population.** `board_clv_check`'s last
  run: 30 of 58 verified, maker −0.41%, taker −2.90%, beat close 12/30, negative in both halves
  (−0.73%, −0.09%). **It excluded 20 rows for being priced on global Polymarket** — and 15 of those
  were gettable at a bettable venue, so they should have been priced there rather than dropped.
  Under the adopted policy a CLV figure on the wrong population cannot veto; it also cannot support.
  **This is open item O6 and it is now the blocking measurement defect, not a strategy verdict.**
- **Nightly cap, reported not tuned:** play #1 +37.8% (20) · #2 +21.8% (16) · #3 +56.8% (10) ·
  #4 +54.6% (9) · **#5 −17.0% (7)**. Cutting #5 would be threshold tuning and is not proposed.
- **Fills: zero.** `EXEC_BOARD_LIVE` is off; the board is paper for live money since 4 Nov.

Also preserved (never overwritten): the externally supplied **98-game NBA totals first-alert study**
— 91 verified closes, maker CLV **H1 −1.05% / H2 −1.10%, FAILED**, not reproducible in this repo.

## B3. Paper splits — the five standing at ELIGIBLE at next review

Full table and bars live in `SPLITS.md`; this is the promotion queue only.

| Split | W-L-P | Units | u/play |
| --- | --- | --- | --- |
| Hard Rock-priced, routed | 50-41-0 | +3.28u | +0.036 |
| NBA liquidity totals — unders | 46-36-0 | +8.79u | +0.107 |
| NBA liquidity totals — lead 4-12h | 44-32-0 | +10.78u | +0.142 |
| NBA liquidity totals — $25-50k prints | 56-40-0 | +13.78u | +0.144 |
| *(parent)* NBA liquidity totals (lane) | 81-65-0 | +13.06u | +0.089 |

**Four of these are the same population.** The parent lane plus its unders, lead-4-12h and
$25–50k-print slices are cuts of one NBA-totals liquidity record — which is also v3 PLAY and
LIQ-BOT (entry 9). They are not four independent findings, and promoting on the best slice would be
promoting a searched cut of a lane that is already approved-but-held. Hard Rock-priced routed is the
only one of the five from a different population.

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

## Rule changes, and where a record splices

Read any pooled number below against this list. Where a record spans a change, the figure mixes two
regimes and the post-change window is the one to read.

| Date | What changed | Which record it splices |
| --- | --- | --- |
| 2 Oct | Alert timing: same-day only → games today or tomorrow | Steam feed, all leagues |
| 14 Oct | Non-Top-25 college no longer graded or counted | Steam feed, NCAAF/NCAAB |
| 16 Oct | Alert liquidity minimum $10k → $25k; NCAAF odds range set to −170/+130 | Steam feed |
| 17 Oct | Claude's picks became paper-only | Steam feed — nothing after this is a real bet |
| **20 Oct** | **Grading begins.** Alerts from 8–17 Oct carry no grade | **Any grade-based cut exists only from 20 Oct.** The NCAAF dog cell was +38.2% on the 29 pre-grading alerts and +0.9u on the 50 after |
| 23 Oct | MLB and NCAAB added to the liquidity board | Liquidity board |
| 24 Oct | ProphetX became a liquidity trigger book | Liquidity board |
| 25 Oct | Regrade: `no_pregame_close` artifacts excluded from every record | Liquidity board |
| 27 Oct | Liquidity spreads closed by decision; steam renamed, evening runs added | Splits, steam feed |
| **31 Oct 14:35Z** | **EV study pre-registration cutoff.** J/D buckets judged only after this | A, B and M headlines pool pre- and post-cutoff; the J-buckets do not |
| 1 / 3 / 4 Nov | Bets Board v1 → v2 → v3. All three still grade in parallel tiles | See the board table below — v3 is applied consistently across the whole window, so it does not splice |
| 4 Nov | Polymarket US team totals were being read as game totals; fixed. Earlier PM-US football-total sightings flagged suspect | EV study |
| **6 Nov** | **`CLV_STANDARD.md` adopted.** Every CLV report published before run `42241855328` contains look-ahead bias and is void | Every CLV figure dated before 6 Nov |
| 6 Nov | Fee model `2026-11-06.11` → `.12` (Novig is not flat zero: 0 pre-game straights, 0.06·C·p(1−p) live/futures) | Any after-fee figure spanning it |
| 6 Nov | NCAAB openers freeze lookahead `AHEAD_DAYS` 2 → 3 | Entry 23 — before this, ~45% of Pinnacle-posted games were disqualified as "frozen after the open". The 7 Nov checkpoint straddles the change |
| 9 Nov | Lane 2 paid polling paused (`EXEC_LANE2_PAID` default off) | Entry 8 stops buying live Pinnacle limits |

### Bets Board, all three rule versions (graded, from `board/calls.json`)

| Version | PLAY | LEAN | DEAD |
| --- | --- | --- | --- |
| **v3** (4 Nov, ratified 6 Nov) | **62 graded, 42-20, +20.43u, +33.0%** | 308, +20.65u, +6.7% | 228, −9.36u, −4.1% |
| v2 (3 Nov) | 32 graded, 21-11, +9.28u, +29.0% | 283, +18.16u, +6.4% | 235, −8.56u, −3.6% |
| v1 (1 Nov) | 6 graded, 4-2, +1.04u, +17.3% | 501, +22.10u, +4.4% | 43, −4.26u, −9.9% |

v3 PLAY by week: 41.4% (n=25) · 30.9% (n=9) · 20.3% (n=18) · 36.4% (n=10). Halves +45.5% then
+20.4%. v3 applies no money threshold, no confirmation test, no sharp-agreement test and no fights
test — Peter's own note (6 Nov): a liquidity-flow heuristic, not a demonstrated +EV model, paper only.

## Backtest windows that stay out of a record

Stated in one place because the rule differs by lane and the differences are deliberate:

- **Bets Board (entry 7): the whole v3 record counts.** v3 dates from 4 Nov and Peter ratified it on
  6 Nov as the rule the historical record ran on, so the 22 Oct–5 Nov rows carry `recon: true`
  (48 of the 62 PLAY calls) and are part of the record, not a separate backtest. Calls are written
  when they post and never rewritten, so a PLAY whose money is later pulled still grades as the PLAY
  it was. `v3_n` caps the night at 5 plays by alert time.
- **Liquidity lanes:** the 22–31 Oct backtest is never part of their record (`lanes.py`).
- **EV study:** pre-registered buckets are judged only on sightings after 31 Oct 14:35Z.

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

## OPEN ITEMS — carried forward until answered or closed with Peter's approval

Numbers unavailable here are marked with what is needed.

| # | Item | Status | What is needed |
| --- | --- | --- | --- |
| O1 | Registry 23 says "first read early December"; it happened 7 Nov at 61 sightings and STOPped | open | registry edit (Peter/Muse) |
| O2 | `ncaab_openers.py` calls itself "item 28"; registry says 23 | open | registry or code correction |
| O3 | Registry 21 has no recorded final verdict; the report due 10 Nov was never sent | open | Peter/Muse to record the verdict |
| O4 | `ncaab_grade.py` CLV is `close/open − 1` — no entry price, no fees; not comparable to CLV_STANDARD | open | decision on whether to restate or retire the metric |
| O5 | No script imports `clv_std`; `ncaab_grade.eff()` is a fifth parallel fee copy returning raw prices for unknown venue keys | open | migration is approved-per-change work, not started |
| O6 | **Board calls are priced at the TRIGGER venue, not the best bettable venue.** `board_build.after_fee_dec` also prices Polymarket GLOBAL at the US fee. Consequence: `board_clv_check` drops 20 of 58 rows as unbettable when 15 of them were gettable on Novig/Kalshi/ProphetX, so the −0.41% certified CLV is computed on the wrong population | **open — now the blocking defect for the NBA-totals family** | price each call at the best bettable exchange quoting that line, then recompute certified CLV |
| O7 | Registry entries with no numbers on this scorecard | open | their own report emails: Resting Bids (2), Peter Feed Plays (3), HR Scanner Flags (4), Street Value (5), Lane 2 (8), POST & WAIT (10), DOG BAND (12), P-NHL-DOGS (15), P-CFB/NFL-OVER (16), HR-A (17), PLIMIT-CUT (19), EX-B (20), plus lenses 24-26 and research 27-32 |
| O8 | Zero confirmed fills outside Lane 1 | open | structural: nothing else is live |
| O9 | Certified CLV coverage is low and non-representative (NHL 56% vs NBA 7%) | open | fixture-matching quality is a standing objective |
| O10 | Lane 1's certified CLV is positive overall (+0.37%) but negative in H2 (−0.59%) on n=33 | open | more verified fills; n≥100 for the precision bar |

## O6 AUDIT RESULT (11 Nov) — entry basis corrected in code; close leg blocked

`board_clv_check.py` now prices each historical call at the **best BETTABLE venue quoting the same
line at the alert price or better**, from the decision-time liquidity snapshot joined on the call's
own key and `alerted_utc`. Measurement and reporting only — no production rule, execution, alert or
scanner path touched, no state written, `board/calls.json` read without mutation.

**Bettable set: Novig, Kalshi, ProphetX and POLYMARKET US.** PM US was missing from the first
version (Peter caught it). The snapshot carries both `polymarket` (the GLOBAL crypto book — not
bettable from the US, `clv_std` refuses to price it) and `polymarket_us` (ours, 817 snapshot rows);
only the latter maps through. On PM US the maker side is a **rebate** (−0.0125), so it can be the
best resting venue even where its taker price is not best — which is why maker and taker are
resolved separately.

**The comparison is RAW and LIKE-FOR-LIKE against the alert's own american price**, because the
standard is "the alert price or nothing". Two earlier versions were wrong and both are recorded:
comparing after-fee values against a target computed at the *trigger* venue priced global
Polymarket at the US fee (wrong, gave 53), and doing the same through `clv_std` produced no target
at all because `clv_std` refuses to price global — disqualifying all 21 globally-triggered calls for
a property of a venue we were never going to bet (gave 38). **An unpriceable trigger venue must not
disqualify a play.** Fees still apply to the chosen quote, which is what ranks the candidates.

### Reconciliation of all 62 calls, corrected basis

| | n |
| --- | --- |
| **GETTABLE at the alert price or better, bettable venue** | **51** (on 51 distinct games — no duplicates) |
| Not gettable — no bettable quote on that exact line | 4 |
| Not gettable — quoted on the line but worse than the alert price | 7 |

On the 51: **51 games, 18 days, +19.77u, +38.8%, day-clustered 95% CI [+16.5, +59.6]%**;
H1 +49.7% / H2 +28.3%. Execution venue — taker: Novig 28 · Kalshi 20 · ProphetX 3; maker:
Novig 27 · Kalshi 22 · ProphetX 2. By trigger: Kalshi-triggered 38 of 41 gettable,
globally-triggered **13 of 21**. **Polymarket US is the best venue on 0 of 62 — no board snapshot
carries a PM US quote at all**, so including it changes nothing here and is correct going forward.

**STILL BLOCKED — certified CLV cannot be recomputed in this session.** Running the corrected file
stops at `board_clv_check.py:143`:

```
st_ = tb.dec(json.load(open(cl.STATE)))
cryptography.exceptions.InvalidTag
```

`clv/state.enc` — the fixture and verified-close state — cannot be decrypted without
`TRACKER_PASSPHRASE`, which was not requested and must not be exposed. The decision-time snapshots
load fine (2,397 of them), so **only the close join is blocked**. Certified same-line Pinnacle CLV,
modelled CLV, coverage, confidence intervals and chronological halves for this population are
therefore **MISSING, not negative**, and under the adopted policy neither veto nor support.
**To obtain them:** run `board-clv-check` in Actions, where the secret and the history cache live.
It reads only free `/historical-odds`, spends zero paid credits — but it emails its report, so it
needs Peter's go.

**Tests:** `tests/test_board_clv_venue.py`, 36 checks, all passing — no-hindsight selection (the
function's executable code references no close, result or later price), fee treatment (delegation to
`clv_std` only, per-venue ordering, maker vs taker, PM US rebate, global unselectable, same-line
only, alert-price-or-better boundary, unpriceable trigger non-disqualifying), and no mutation of
historical calls or any live path.

**Related, already done on 10 Nov:** global Polymarket was removed from `LIQ_BOOKS` so future board
calls are not generated off an unbettable venue. That fixes generation, not the pricing of the 62
calls already recorded.

**Five-candidate brief (10 Nov), for the record:** NO PROVEN NEW EDGE — NO BUILD, under Peter's rule
that both halves must be positive on units and CLV. That verdict stands over the ELIGIBLE queue.

## O7 — what is filled, what is unavailable, and why

Filled from their own reports or from committed data (source and date on each row above):
Lane 1 · LIQ-BOT/registry 9 · SLOW-HR · LIQ-SMALL + Lane 3 shadow · Bets Board v1/v2/v3 ·
EV Trigger B and the EV study's other triggers · ML_STAY · PULL_FADE · SOLO · the feed-level
populations · the ELIGIBLE queue.

**Unavailable in this session, with the exact reason.** These entries publish no discrete report;
their numbers sit inside two consolidated emails, and an email body cannot be parsed locally — the
mail tool returns it into context, so there is no way to extract a section without loading the
whole message. The BUCKET REPORT is **430 KB** and the PAPER RULES TRACKER **55 KB**.

| Entry | Where its numbers live | Status |
| --- | --- | --- |
| 2 RESTING BIDS | executor ledger emails | unavailable here |
| 3 PETER — FEED PLAYS | BUCKET REPORT (430 KB) | unavailable here |
| 4 HR SCANNER FLAGS | HR phone ledger / HR push emails | unavailable here |
| 5 STREET VALUE | manual-bet emails, one per fill | unavailable here |
| 8 LANE 2 | Lane 2 dry-run email | unavailable here |
| 10 POST & WAIT | `post_test` email | unavailable here |
| 12 DOG BAND | BUCKET REPORT | unavailable here |
| 15 P-NHL-DOGS | BUCKET REPORT | unavailable here |
| 16 P-CFB-OVER / P-NFL-OVER | BUCKET REPORT | unavailable here |
| 17 HR-A | BUCKET REPORT | unavailable here |
| 19 PLIMIT-CUT MISPRICE | `PLIMIT LOG`, its own 25 KB daily email | retrievable on request |
| 20 EX-B | BUCKET REPORT | unavailable here |
| 27-32 research tracks | MODEL LAB / BOARD LAB / CLV-WORKS emails | unavailable here |

Marked unavailable rather than guessed. **Entry 18's** broad build EDGE2 reports inside the PAPER
RULES TRACKER (item 61) and is likewise unavailable here.

### Naming, provisional

- **"Liquidity Test" → the liquidity board plus registry 9, kept as two separate populations**
  (board: 2,665 graded, −29.04u, −1.1%; registry 9: n=151, +23.81u at the non-executable alert
  price). **UNCONFIRMED.**
- **"Beta Board" → BOARD v2** (PLAY 32 graded, 21-11, +9.28u, +29.0%). **UNCONFIRMED — no entry of
  that name exists in REGISTRY.md.**

## O1-O3 — proposed corrections, NOT applied (REGISTRY.md untouched)

**O1.** REGISTRY.md entry 23, replace:
> `| 23 | **NCAAB OPENERS** | Our frozen openers vs Pinnacle's open. First read early December. |`

with:
> `| 23 | **NCAAB OPENERS** | Our frozen openers vs Pinnacle's open. First read taken 7 Nov 2026 at 61 sightings: CLV −0.66%, beat close 26/61. Registered STOP rule (CLV ≤ 0) triggered. **CLOSED.** Out-of-sample since: 66 further sightings at −1.25%; all 127 at −0.97%, beat close 44.1%; MAE ours 14.28 vs open 13.58. |`

**O2.** `ncaab_openers.py` and `ncaab_grade.py` headers both read "item 28". Registry numbering is
authoritative, so the proposed edit is to those two docstrings: "item 28" → "registry 23". No code
behaviour changes. Needs separate authorization.

**O3.** Proposed final-verdict wording for entry 21:
> `| 21 | **EV TRIGGER B / B-TOTALS** | EV study sightings. **FINAL READ 11 Nov 2026: FAIL.** B Pinnacle ≥3% EV: 144 graded, 65-79, −6.23u, −4.3%; consensus CLV −0.87%; certified same-line Pinnacle CLV +1.06% on 33% coverage; both halves negative on units. Pre-registered J1-J4 all negative. A, A-qualifying and M also fail their gate. B-TOTALS was never added to the study's locked judged list (locked 31 Oct, before the 3 Nov proposal), so totals and unders remain descriptive. **No promotion.** |`

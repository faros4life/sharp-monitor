# V2 CLV validation - PRE-REGISTERED SPEC

Registered 2026-11-20 by Peter (relayed from ChatGPT), BEFORE any result was computed.
Committed ahead of the analysis code on purpose: thresholds chosen after seeing numbers are
not thresholds. Nothing in this file may be edited to match an outcome.

## What is being tested

For a row where the line moved, we hold two ESTIMATES of the same quantity - the fair
probability at OUR number at close:

- MARKET estimate: de-vig of Pinnacle's observed two-sided quote AT OUR ALT LINE.
- MODEL estimate (V2): Pinnacle's MAIN-line fair walked to our number using the registered
  MASS rows in `line_value.py` only (no fallback, never >1pt from a registered row).

Gap = model - market, in probability points (pp). Both are estimates. NEITHER is independent
ground truth. This is a calibration screen, not a proof of accuracy.

## Sample requirements

- Overall judgment: at least 30 matched moved-line observations.
- Subgroup judgment: at least 20 observations in that subgroup.
- Below those counts the verdict is INCONCLUSIVE. Never PASS on thin coverage.

## Thresholds (screening only)

- Mean signed gap within +/-1.0 pp.
- Mean ABSOLUTE gap no greater than 2.0 pp.
- Report the 95% confidence interval on the signed mean.
- Report the share of rows whose absolute gap exceeds 3.0 pp.

## Verdict rules

- PASS: n >= 30 AND |mean signed| <= 1.0 pp AND mean|gap| <= 2.0 pp AND the 95% CI on the
  signed mean lies entirely within +/-1.0 pp.
- FAIL: n >= 30 AND (|mean signed| > 1.0 pp OR mean|gap| > 2.0 pp).
- INCONCLUSIVE: n < 30, or n >= 30 with the point estimates inside the thresholds but a 95% CI
  that extends beyond +/-1.0 pp. A sample that cannot separate the hypotheses has not passed.

## Breakdowns required

By league; by favourable vs unfavourable movement; by distance moved; and for football, by
whether the move CROSSES a key number (3, 7, 10, 14). Each reported with its own n, and marked
INCONCLUSIVE below 20.

Leagues whose MASS rows are PUBLISHED ESTIMATES (NCAAB, NCAAF) are labelled as such. A PASS
resting on estimated mass is weaker evidence than one resting on measured (NFL/nflverse) mass.

## Overround

Report main-line overround, alt-line overround, their difference, and HOW the margin is split
between the two sides. A higher alt overround on its own does NOT prove V2 is correct - it
shows only that alts carry more margin, not that V2's size or allocation of the correction is
right.

## Timestamp confound (added 2026-11-20, still BEFORE any result was computed)

The four prices are NOT one simultaneous quote. `two_way` takes each outcome's last tick at or
before kick INDEPENDENTLY, so the alt pair and the main pair - and the two sides within each
pair - can carry different timestamps. `FRESH_MIN` bounds only the OLDER side of a line, at 24
hours. An earlier note in this work claimed the four came from one tick "by construction"; that
was wrong and is corrected here.

This matters because a STALE alt quote widens the alt overround and is indistinguishable, in the
number alone, from genuine alt vig. History stores CHANGES, so an old tick can mean the price
simply never moved - but it can equally mean the line was pulled, which is how the Novig stale
check caught an 83-hour-old -16667.

Required, therefore: report the spread between the oldest and newest of the four prices (median,
mean, max, and how many rows fall within 15 minutes), and report the calibration screen AGAIN on
near-simultaneous rows only, as a sensitivity check. If the full sample and the near-simultaneous
subset disagree, the overround gap is contaminated by staleness and is NOT evidence of alt vig.
Wide-spread rows are reported, never silently dropped.

## Interpretation limits - binding

- A positive V2-minus-V1 gap is NOT proof of asymmetric vig.
- Better-looking CLV does NOT validate V2.
- The distance bucket CANNOT separate alt-line vig from conversion-model error. Both grow with
  distance. Do not claim otherwise.
- A numerical PASS does NOT authorize promotion to official CLV. V1 stays official; V2 stays
  shadow. Promotion needs Peter's explicit yes.
- If the original two-sided quotes cannot be recovered for a row, that row is reported as
  unrecoverable. It is never estimated and never counted as agreement.

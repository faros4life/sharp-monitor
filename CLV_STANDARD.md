# VALUE LAB — OFFICIAL CLV STANDARD

**Adopted 6 November 2026 by Peter.** This is the authoritative CLV calculation and reporting
basis for the whole betting system. It supersedes every earlier CLV convention in this repo.

Recorded here so that it is versioned with the code it governs, rather than living only in email.

---

## 1. The formula

```
Net CLV (%) = (Pinnacle no-vig closing probability
               × effective entry decimal odds AFTER FEES
               − 1) × 100
```

Requirements, all of them binding:

- Verified **same-line** Pinnacle closes only
- Exact event, market, side and line
- **No modelled or converted closes** in a headline figure
- **No look-ahead bias** — a quote is read at or before the entry timestamp, never after
- Correct documented venue-specific fees, including maker/taker distinctions
- Quote freshness enforced
- **No minimum displayed-size requirement**
- Exclusions identified and reported

Fee model: **`2026-11-06.11`**, under normal version tracking for documented future changes.

## 2. The categories stay separate

| Category | Basis |
| --- | --- |
| AUTO Opportunity CLV | best net **taker** price across auto-eligible venues |
| MANUAL Opportunity CLV | manually accessible venues, Hard Rock included |
| Passive Posting CLV | registered **maker** posting price |
| Executed CLV | actual filled price, net of fees |
| Paper Fill-Supported CLV | predefined simulated execution model |

Never combine these into one figure. Never represent an unfilled posting opportunity as an actual
execution.

> **Implementation gap, recorded not resolved.** `clv_report.py` computes AUTO, MANUAL, Executed
> and Paper Fill-Supported. It does **not** yet compute Passive Posting CLV, because no maker
> posting price is registered for the liquidity-alert population. When a posting test is
> registered, that category gets its own line — it is never inferred from an AUTO figure, which is
> a taker price.

## 3. Two mandatory reporting guards

### Guard 1 — scope accompanies every CLV figure

Every result identifies its **population, strategy or lane, execution basis, and sample size**.

The −0.37% AUTO Opportunity CLV applies **only** to the 910 verified liquidity-alert observations.
It is not the CLV of Lane 1, Lane 2, Lane 3, or the system.

- Lane 1 retains its existing population and verified filled-bet CLV.
- The $25k–$50k forward test is judged on this standardised Pinnacle basis, **not** on exchange
  self-close movement.

### Guard 2 — exclusions accompany every headline

Every headline carries its population coverage and exclusion counts.

**The 6 November liquidity-alert report, as the reference case:**

| | |
| --- | --- |
| Eligible graded population | 1,713 |
| Verified same-line sample | 910 |
| Excluded | 803 |
| — of which *no fixture matched* | 776 |
| AUTO Opportunity CLV | **−0.37%** |
| Beat close | **45.3%** (412/910) |

Provenance: run `42241855328`, head SHA `238bebb7`, fee model `2026-11-06.11`, zero OddsPapi
credits. 95% Wilson interval on the beat rate is [42.1%, 48.5%], which excludes 50%.

**Never publish −0.37% without its population and the substantial missing-fixture coverage.**

Improving fixture matching is a standing data-quality objective. It does not delay adoption.

## 4. Historical integrity

- All original historical figures and registered thresholds are preserved.
- **Earlier CLV reports containing look-ahead bias remain void.** Nothing this report published
  before run `42241855328` should be read.
- **Exchange Self-Close Price Movement** stays separate, is never labelled Pinnacle CLV, and is
  never used as a CLV gate. It compares entry to the trigger venue's own last pregame price.
- Recalculated historical results appear alongside originals, each with its methodology named.

## 5. Implementation

This standard governs all future research, strategy evaluation and reporting.

Where existing scripts use inconsistent CLV calculations, the differences are identified and
migrated through **controlled, regression-tested** changes. Historical results are never silently
rewritten and no registered test criterion is changed.

`clv_audit.py` is the instrument for that: it derives each script's basis mechanically from its
source. As of adoption it reports that **not one** of 14 CLV-computing scripts imports `clv_std`.
That migration is a separate, approved-in-advance-per-change piece of work.

No further methodology redesign. No unnecessary enhancements.

## 6. Nothing live changes

- Lane 1 untouched
- Lane 2 and Lane 3 retain existing permissions and registered tests
- Lane 3 remains paper-only
- Hard Rock remains manual-only
- No betting rules, thresholds, order routing or risk limits change
- No live execution changes
- No additional OddsPapi spending without approval

**Actual filled-bet profitability remains the ultimate measure of strategy success. Positive CLV is
evidence of pricing value, not proof of realised profitability.**

---

**Final decision: adopt the methodology system-wide — not the liquidity-alert result system-wide.**

Every CLV number carries its scope and its exclusion coverage.

No additional changes unless a material calculation error is discovered.

---

## 7. Coverage denominator — definition decision, 14 Nov 2026 (Peter, explicit)

**The operational CLV coverage denominator is the set of ELIGIBLE US-EXECUTABLE observations.**
An observation whose venue cannot be bet from the US is not a coverage gap, because no price on it
was ever obtainable; counting it as missing evidence understates coverage with rows that could not
have been played at any number.

Both figures are reported, always, in this order and both labelled:

1. **coverage, priceable rows** — the operational figure, against eligible US-executable rows.
2. **coverage, whole population** — the original denominator, kept so the historical record stays readable
   and so the size of the exclusion is always visible.

**What this decision does NOT do.** It does not restate, revise or replace any verdict that was
registered before today. Every frozen figure in `SCORECARD.md` and `REGISTRY.md` stands exactly as
ratified, on the denominator in force when it was ratified, and is labelled frozen. The new
denominator applies from this record forward.

**Why it needed deciding rather than inferring.** On registry 9 the two denominators give 100% and
73%, and the registered representativeness test turns on which one it means: CLEAR FAIL on the
executable basis under the first, CONTINUE TESTING under the second. The CLV sign and interval are
identical either way — only the label moves. Reading the word "representative" as whichever
produced a verdict would have been inferring intent from a word, so it was put to Peter and he
decided it.

### 7a. Registry 9 / LIQ-BOT under this decision

| | value | basis |
| --- | --- | --- |
| verified Pinnacle CLV | **−3.01%**, 95% CI [−3.99, −2.03]% | no-vig close vs our after-fee entry |
| chronological halves | H1 **−3.36%**, H2 **−2.66%** — both NEGATIVE | same |
| beat close | 32/127 (25%) | same |
| executable units | **+7.94u**, +6.25% ROI, 1u flat | alert price AFTER fees |
| coverage | 127/127 priceable (100%); 127/174 whole population (73%) | 47 Polymarket-global rows excluded |
| **CLV qualification** | **FAILED** | negative CLV CI excluding zero; neither half positive |

**Excluded, by decision 2 of 14 Nov:** the 47 Polymarket-global observations, from the EXECUTABLE
evaluation only. They are not deleted, not re-priced and not counted as zero; they remain in the
raw record and in the whole-population denominator above.

**HISTORICAL, NON-EXECUTABLE — unchanged:** registry 9's published **+23.81u at the recorded ALERT
price, n=151, ratified 11 Nov 2026**. That basis is before fees and was never obtainable. It is
kept as the historical record and must never be quoted as an executable result.

Fees take the alert-price +22.31u to +7.94u on today's population. They do NOT flip the sign — the
published entry's "3.42% fee drag is the whole sign difference" holds for the CLV, not the units.

**No promotion, demotion, stake change or switch follows from any of this.** POTENTIAL PASS remains
structurally unreachable for this lane: the registered rule requires a realized-unit CI from actual
fills, and the lane is shadow-logged with none.

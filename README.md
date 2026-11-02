# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-02T11:50:28Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4268 | 3959 | -1.92c | 21.6% | 1602 | -1.15c | 3959 | 1997-1962-0 | -194.11u | -4.9% |  |  | criteria not met (3959/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1081 | 956 | -3.85c | 14.0% | 216 | -3.11c | 956 | 501-455-0 | -50.48u | -5.3% |  |  | criteria not met (956/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 62 | 61 | -0.66c | 32.8% | 59 | 0.13c | 61 | 28-33-0 | -1.11u | -1.8% |  |  | criteria not met (61/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 39 | 39 | -0.62c | 30.8% | 38 | 0.01c | 39 | 18-21-0 | +0.02u | 0.1% |  |  |  |
| B ref age 5m+ | 18 | 17 | -1.11c | 35.3% | 16 | -0.09c | 17 | 7-10-0 | -2.42u | -14.2% |  |  |  |
| M move-watch: gettable (sightings) | 154 | 154 | -0.57c | 32.5% | 152 | -0.59c | 154 | 78-75-1 | -3.15u | -2.0% | 0.29c | 22s | criteria not met (154/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 82 | 82 | -0.58c | 35.4% | 81 | -0.81c | 82 | 41-40-1 | -2.38u | -2.9% | 0.01c | 28s |  |
| M gettable, price moves | 72 | 72 | -0.56c | 29.2% | 71 | -0.34c | 72 | 37-35-0 | -0.77u | -1.1% | 0.61c | 20s |  |
| M control: not gettable | 592 | 470 | -0.87c | 34.0% | 466 | -1.22c | 482 | 253-221-8 | +4.51u | 0.9% | 1.76c | 26s |  |
| M all moves | 746 | 624 | -0.79c | 33.7% | 618 | -1.07c | 636 | 331-296-9 | +1.37u | 0.2% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 641 | 614 | 4.4c | 29.2% | 122 | 3.88c | 615 | 274-341-0 | +325.38u | 52.9% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 23 | 22 | 0.2c | 11-11-0 | +0.91u | 17, 0.0c, -0.36u | not enough yet |
| J2 B, NBA | 12 | 11 | 0.09c | 6-5-0 | +1.45u | 7, -0.25c, +1.26u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 16 | 16 | -0.17c | 8-8-0 | +0.70u | 13, -0.33c, +1.62u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 56 | 56 | -0.49c | 25-30-1 | -6.33u | 37, -0.58c, -6.91u | negative |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 12 | 12 | -0.58c | 6-6-0 | -2.35u | 8, -0.72c, -1.29u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 589 | 30 | 5.1% | -0.35c | 1.61c | 15-15-0 | +0.52u |  |
| MK novig fair-2c | 589 | 11 | 1.9% | -0.51c | 2.54c | 7-4-0 | +3.76u |  |
| MK prophetx fair-1c | 1891 | 93 | 4.9% | -0.88c | 1.1c | 45-46-2 | +0.79u |  |
| MK prophetx fair-2c | 1874 | 25 | 1.3% | -0.69c | 2.04c | 10-15-0 | -4.27u |  |
| MK all fair-1c | 2480 | 123 | 5.0% | -0.75c | 1.22c | 60-61-2 | +1.31u | criteria not met (123/50 graded, CLV not positive) |
| MK all fair-2c | 2463 | 36 | 1.5% | -0.63c | 2.16c | 17-19-0 | -0.50u | criteria not met (36/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 52.

## Odds API credits (100K/month plan)

Study: 607/day, projected 18200/30 days. All monitors on the key: 2048/day, projected 61428/30 days. Remaining 97272; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-02T11:50:28Z: outside read hours: closes/grades only
- 2026-11-02T11:40:44Z: outside read hours: closes/grades only
- 2026-11-02T11:30:39Z: outside read hours: closes/grades only
- 2026-11-02T11:20:43Z: outside read hours: closes/grades only
- 2026-11-02T11:10:35Z: outside read hours: closes/grades only
- 2026-11-02T11:01:18Z: outside read hours: closes/grades only
- 2026-11-02T10:50:35Z: outside read hours: closes/grades only
- 2026-11-02T10:40:33Z: outside read hours: closes/grades only
- 2026-11-02T10:30:34Z: outside read hours: closes/grades only
- 2026-11-02T10:20:28Z: outside read hours: closes/grades only

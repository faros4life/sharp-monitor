# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-13T08:32:55Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 10157 | 9773 | -1.62c | 24.5% | 4232 | -1.09c | 9774 | 5085-4689-0 | -300.58u | -3.1% |  |  | criteria not met (9774/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2380 | 2197 | -3.1c | 19.5% | 495 | -2.84c | 2197 | 1128-1069-0 | -173.62u | -7.9% |  |  | criteria not met (2197/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 177 | 175 | -0.8c | 31.4% | 164 | 0.15c | 175 | 74-101-0 | -17.98u | -10.3% |  |  | criteria not met (175/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 16 | 16 | -0.11c | 31.2% | 16 | 1.04c | 16 | 7-9-0 | -1.37u | -8.6% |  |  |  |
| B ref age 1-5m | 98 | 96 | -0.86c | 32.3% | 91 | 0.08c | 96 | 43-53-0 | -4.31u | -4.5% |  |  |  |
| B ref age 5m+ | 63 | 63 | -0.9c | 30.2% | 57 | 0.02c | 63 | 24-39-0 | -12.29u | -19.5% |  |  |  |
| M move-watch: gettable (sightings) | 468 | 464 | -0.6c | 35.3% | 462 | -0.54c | 468 | 241-222-5 | -4.41u | -0.9% | 0.21c | 28s | criteria not met (468/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 241 | 239 | -0.74c | 35.6% | 238 | -0.78c | 241 | 117-120-4 | -13.65u | -5.7% | -0.14c | 28s |  |
| M gettable, price moves | 227 | 225 | -0.44c | 35.1% | 224 | -0.28c | 227 | 124-102-1 | +9.25u | 4.1% | 0.59c | 26s |  |
| M control: not gettable | 1866 | 1490 | -0.82c | 35.6% | 1461 | -1.24c | 1533 | 764-745-24 | -69.73u | -4.5% | 1.88c | 184s |  |
| M all moves | 2334 | 1954 | -0.76c | 35.6% | 1923 | -1.07c | 2001 | 1005-967-29 | -74.14u | -3.7% | 1.55c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1118 | 1108 | 2.6c | 27.8% | 234 | 2.42c | 1109 | 494-615-0 | +292.17u | 26.3% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 120 | 118 | 0.12c | 50-68-0 | -12.55u | 77, -0.14c, -16.21u | negative |
| J2 B, NBA | 86 | 84 | 0.26c | 36-48-0 | -8.12u | 50, 0.01c, -8.26u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 70 | 68 | 0.04c | 30-38-0 | -4.89u | 51, -0.4c, -5.15u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 277 | 277 | -0.59c | 135-139-3 | -13.05u | 154, -0.68c, -14.22u | negative |
| D1 B, unders (descriptive) | 44 | 43 | 0.5c | 20-23-0 | -1.33u | 39, 0.45c, -1.54u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 16 | -0.3c | 10-5-1 | +1.43u | 12, -0.47c, +2.57u | descriptive only |
| D4 B, NHL (descriptive) | 19 | 19 | 0.53c | 8-11-0 | -1.08u | 18, 0.53c, -2.23u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 105 | 105 | -0.29c | 59-44-2 | +3.11u | 55, -0.4c, -0.14u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2742 | 117 | 4.3% | -0.57c | 1.58c | 58-59-0 | +1.27u |  |
| MK novig fair-2c | 2731 | 48 | 1.8% | -0.08c | 2.52c | 26-22-0 | +6.76u |  |
| MK prophetx fair-1c | 5922 | 281 | 4.7% | -1.08c | 1.1c | 132-144-5 | -6.07u |  |
| MK prophetx fair-2c | 5882 | 103 | 1.8% | -0.57c | 2.04c | 50-53-0 | +1.30u |  |
| MK all fair-1c | 8664 | 398 | 4.6% | -0.93c | 1.25c | 190-203-5 | -4.80u | criteria not met (398/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 8613 | 151 | 1.8% | -0.41c | 2.19c | 76-75-0 | +8.06u | criteria not met (151/50 graded, CLV not positive) |

A and B on the same side/line: 147.

## Odds API credits (100K/month plan)

Study: 647/day, projected 19412/30 days. All monitors on the key: 2423/day, projected 72692/30 days. Remaining 68823; guard holds 49800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-13T08:32:54Z: outside read hours: closes/grades only
- 2026-11-13T08:22:26Z: outside read hours: closes/grades only
- 2026-11-13T08:12:51Z: outside read hours: closes/grades only
- 2026-11-13T08:02:28Z: outside read hours: closes/grades only
- 2026-11-13T07:52:52Z: outside read hours: closes/grades only
- 2026-11-13T07:41:50Z: outside read hours: closes/grades only
- 2026-11-13T07:32:27Z: outside read hours: closes/grades only
- 2026-11-13T07:21:53Z: outside read hours: closes/grades only
- 2026-11-13T07:13:18Z: outside read hours: closes/grades only
- 2026-11-13T07:02:58Z: outside read hours: closes/grades only

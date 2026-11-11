# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-11T09:12:20Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9090 | 8795 | -1.62c | 24.2% | 3831 | -1.04c | 8796 | 4543-4253-0 | -326.07u | -3.7% |  |  | criteria not met (8796/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2071 | 1954 | -3.1c | 19.1% | 429 | -2.64c | 1954 | 1002-952-0 | -160.61u | -8.2% |  |  | criteria not met (1954/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 155 | 154 | -0.75c | 31.2% | 144 | 0.15c | 154 | 66-88-0 | -13.85u | -9.0% |  |  | criteria not met (154/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 14 | 14 | -0.1c | 28.6% | 14 | 1.06c | 14 | 7-7-0 | +0.63u | 4.5% |  |  |  |
| B ref age 1-5m | 88 | 88 | -0.84c | 30.7% | 84 | 0.04c | 88 | 38-50-0 | -6.87u | -7.8% |  |  |  |
| B ref age 5m+ | 53 | 52 | -0.79c | 32.7% | 46 | 0.07c | 52 | 21-31-0 | -7.61u | -14.6% |  |  |  |
| M move-watch: gettable (sightings) | 419 | 414 | -0.64c | 34.5% | 412 | -0.54c | 418 | 216-197-5 | +0.92u | 0.2% | 0.19c | 27s | criteria not met (418/50 graded, CLV not positive) |
| M gettable, line moves | 214 | 212 | -0.81c | 34.0% | 211 | -0.82c | 214 | 107-103-4 | -5.70u | -2.7% | -0.2c | 28s |  |
| M gettable, price moves | 205 | 202 | -0.46c | 35.1% | 201 | -0.24c | 204 | 109-94-1 | +6.62u | 3.2% | 0.6c | 26s |  |
| M control: not gettable | 1699 | 1358 | -0.81c | 35.8% | 1331 | -1.23c | 1396 | 696-677-23 | -62.99u | -4.5% | 1.89c | 184s |  |
| M all moves | 2118 | 1772 | -0.77c | 35.5% | 1743 | -1.07c | 1814 | 912-874-28 | -62.07u | -3.4% | 1.55c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1084 | 1072 | 2.51c | 27.0% | 227 | 2.64c | 1073 | 480-593-0 | +285.27u | 26.6% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 102 | 101 | 0.15c | 44-57-0 | -8.30u | 68, -0.02c, -11.36u | negative |
| J2 B, NBA | 70 | 70 | 0.26c | 31-39-0 | -4.82u | 43, 0.07c, -3.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 61 | 61 | -0.01c | 27-34-0 | -4.32u | 47, -0.31c, -3.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 242 | 241 | -0.62c | 119-119-3 | -7.77u | 139, -0.67c, -10.71u | negative |
| D1 B, unders (descriptive) | 33 | 33 | 0.45c | 18-15-0 | +4.54u | 30, 0.42c, +3.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 15 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 15 | 15 | 0.33c | 6-9-0 | -1.21u | 14, 0.32c, -2.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 91 | 91 | -0.2c | 50-39-2 | +3.16u | 47, -0.24c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2338 | 96 | 4.1% | -0.61c | 1.58c | 51-45-0 | +8.23u |  |
| MK novig fair-2c | 2333 | 37 | 1.6% | -0.16c | 2.51c | 23-14-0 | +11.42u |  |
| MK prophetx fair-1c | 5338 | 256 | 4.8% | -1.04c | 1.1c | 123-128-5 | +0.49u |  |
| MK prophetx fair-2c | 5301 | 89 | 1.7% | -0.63c | 2.04c | 43-46-0 | +0.62u |  |
| MK all fair-1c | 7676 | 352 | 4.6% | -0.93c | 1.25c | 174-173-5 | +8.73u | criteria not met (352/50 graded, CLV not positive) |
| MK all fair-2c | 7634 | 126 | 1.7% | -0.49c | 2.19c | 66-60-0 | +12.04u | criteria not met (126/50 graded, CLV not positive) |

A and B on the same side/line: 125.

## Odds API credits (100K/month plan)

Study: 639/day, projected 19157/30 days. All monitors on the key: 2363/day, projected 70878/30 days. Remaining 74483; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-11T09:12:20Z: outside read hours: closes/grades only
- 2026-11-11T09:02:24Z: outside read hours: closes/grades only
- 2026-11-11T08:51:53Z: outside read hours: closes/grades only
- 2026-11-11T08:41:24Z: outside read hours: closes/grades only
- 2026-11-11T08:31:28Z: outside read hours: closes/grades only
- 2026-11-11T08:24:11Z: outside read hours: closes/grades only
- 2026-11-11T08:22:14Z: outside read hours: closes/grades only
- 2026-11-11T08:11:55Z: outside read hours: closes/grades only
- 2026-11-11T08:01:33Z: outside read hours: closes/grades only
- 2026-11-11T07:51:43Z: outside read hours: closes/grades only

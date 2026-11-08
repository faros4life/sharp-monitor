# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T10:51:14Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7500 | 7298 | -1.59c | 23.9% | 3192 | -1.01c | 7299 | 3765-3534-0 | -249.43u | -3.4% |  |  | criteria not met (7299/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1712 | 1625 | -3.13c | 18.2% | 360 | -2.61c | 1625 | 835-790-0 | -123.55u | -7.6% |  |  | criteria not met (1625/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 123 | 123 | -1.01c | 28.5% | 115 | -0.05c | 123 | 54-69-0 | -8.52u | -6.9% |  |  | criteria not met (123/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 72 | 72 | -1.03c | 27.8% | 69 | -0.19c | 72 | 34-38-0 | +0.46u | 0.6% |  |  |  |
| B ref age 5m+ | 42 | 42 | -1.2c | 28.6% | 37 | -0.07c | 42 | 15-27-0 | -10.38u | -24.7% |  |  |  |
| M move-watch: gettable (sightings) | 339 | 330 | -0.62c | 33.9% | 330 | -0.61c | 334 | 170-159-5 | -9.09u | -2.7% | 0.19c | 26s | criteria not met (334/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 176 | 171 | -0.67c | 34.5% | 172 | -0.84c | 173 | 84-85-4 | -8.52u | -4.9% | -0.08c | 28s |  |
| M gettable, price moves | 163 | 159 | -0.56c | 33.3% | 158 | -0.36c | 161 | 86-74-1 | -0.57u | -0.4% | 0.49c | 24s |  |
| M control: not gettable | 1401 | 1107 | -0.81c | 35.7% | 1095 | -1.21c | 1138 | 564-553-21 | -58.22u | -5.1% | 1.78c | 183s |  |
| M all moves | 1740 | 1437 | -0.77c | 35.3% | 1425 | -1.07c | 1472 | 734-712-26 | -67.30u | -4.6% | 1.47c | 121s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1038 | 1031 | 2.73c | 27.1% | 222 | 2.91c | 1032 | 457-575-0 | +281.96u | 27.3% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 75 | 75 | -0.18c | 33-42-0 | -5.88u | 51, -0.43c, -9.22u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 44 | -0.45c | 22-22-0 | +1.86u | 34, -0.76c, +3.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 193 | 188 | -0.68c | 89-96-3 | -12.13u | 109, -0.7c, -13.21u | negative |
| D1 B, unders (descriptive) | 22 | 22 | 0.3c | 13-9-0 | +4.89u | 21, 0.25c, +3.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 10 | 10 | 0.42c | 5-5-0 | +1.71u | 9, 0.42c, +0.56u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 60 | 60 | -0.33c | 34-24-2 | -2.48u | 34, -0.39c, -3.19u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1708 | 73 | 4.3% | -0.65c | 1.59c | 37-36-0 | +2.09u |  |
| MK novig fair-2c | 1706 | 27 | 1.6% | -0.4c | 2.52c | 16-11-0 | +6.65u |  |
| MK prophetx fair-1c | 4435 | 212 | 4.8% | -1.02c | 1.1c | 103-104-5 | +3.78u |  |
| MK prophetx fair-2c | 4408 | 68 | 1.5% | -0.58c | 2.04c | 33-35-0 | +0.84u |  |
| MK all fair-1c | 6143 | 285 | 4.6% | -0.93c | 1.24c | 140-140-5 | +5.87u | criteria not met (285/50 graded, CLV not positive) |
| MK all fair-2c | 6114 | 95 | 1.6% | -0.53c | 2.17c | 49-46-0 | +7.49u | criteria not met (95/50 graded, CLV not positive) |

A and B on the same side/line: 97.

## Odds API credits (100K/month plan)

Study: 632/day, projected 18961/30 days. All monitors on the key: 2146/day, projected 64390/30 days. Remaining 83923; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T10:51:14Z: outside read hours: closes/grades only
- 2026-11-08T10:45:01Z: outside read hours: closes/grades only
- 2026-11-08T10:41:29Z: outside read hours: closes/grades only
- 2026-11-08T10:30:59Z: outside read hours: closes/grades only
- 2026-11-08T10:21:30Z: outside read hours: closes/grades only
- 2026-11-08T10:11:28Z: outside read hours: closes/grades only
- 2026-11-08T10:01:31Z: outside read hours: closes/grades only
- 2026-11-08T09:51:28Z: outside read hours: closes/grades only
- 2026-11-08T09:41:25Z: outside read hours: closes/grades only
- 2026-11-08T09:31:28Z: outside read hours: closes/grades only

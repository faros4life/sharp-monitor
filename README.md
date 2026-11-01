# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T05:20:40Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3555 | 3326 | -2.08c | 21.5% | 1323 | -1.19c | 3225 | 1615-1610-0 | -204.51u | -6.3% |  |  | criteria not met (3225/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 919 | 865 | -3.99c | 14.2% | 204 | -2.98c | 851 | 445-406-0 | -47.11u | -5.5% |  |  | criteria not met (851/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 59 | 59 | -0.68c | 32.2% | 57 | 0.08c | 57 | 25-32-0 | -3.32u | -5.8% |  |  | criteria not met (57/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 38 | 38 | -0.65c | 28.9% | 37 | -0.01c | 36 | 16-20-0 | -1.15u | -3.2% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 16 | 6-10-0 | -3.46u | -21.6% |  |  |  |
| M move-watch: gettable (sightings) | 134 | 131 | -0.58c | 33.6% | 129 | -0.64c | 130 | 64-65-1 | -5.80u | -4.5% | 0.25c | 23s | criteria not met (130/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 72 | 70 | -0.54c | 37.1% | 69 | -0.77c | 70 | 33-36-1 | -5.75u | -8.2% | 0.03c | 27s |  |
| M gettable, price moves | 62 | 61 | -0.63c | 29.5% | 60 | -0.49c | 60 | 31-29-0 | -0.05u | -0.1% | 0.5c | 21s |  |
| M control: not gettable | 513 | 406 | -0.91c | 33.5% | 403 | -1.29c | 396 | 212-179-5 | +9.85u | 2.5% | 1.76c | 25s |  |
| M all moves | 647 | 537 | -0.83c | 33.5% | 532 | -1.13c | 526 | 276-244-6 | +4.06u | 0.8% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 601 | 567 | 4.12c | 28.9% | 110 | 3.07c | 557 | 249-308-0 | +242.64u | 43.6% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 20 | 18 | 0.09c | 8-10-0 | -1.30u | 14, -0.04c, -1.53u | not enough yet |
| J2 B, NBA | 9 | 9 | -0.19c | 4-5-0 | -0.70u | 6, -0.42c, +0.15u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 15 | 13 | -0.24c | 6-7-0 | -0.47u | 10, -0.42c, +0.45u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 42 | 38 | -0.55c | 14-23-1 | -9.66u | 25, -0.66c, -8.42u | not enough yet |
| D1 B, unders (descriptive) | 5 | 5 | 0.76c | 3-2-0 | +1.21u | 5, 0.76c, +1.21u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 6 | -0.99c | 3-3-0 | -1.66u | 5, -1.02c, -2.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 338 | 24 | 7.1% | -0.5c | 1.69c | 13-11-0 | +2.35u |  |
| MK novig fair-2c | 339 | 11 | 3.2% | -0.51c | 2.59c | 6-4-0 | +2.68u |  |
| MK prophetx fair-1c | 1586 | 84 | 5.3% | -0.97c | 1.11c | 34-40-2 | -4.72u |  |
| MK prophetx fair-2c | 1572 | 24 | 1.5% | -0.8c | 2.04c | 8-13-0 | -4.39u |  |
| MK all fair-1c | 1924 | 108 | 5.6% | -0.87c | 1.21c | 47-51-2 | -2.38u | criteria not met (100/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1911 | 35 | 1.8% | -0.71c | 2.14c | 14-17-0 | -1.72u | criteria not met (31/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 49.

## Odds API credits (100K/month plan)

Study: 603/day, projected 18097/30 days. All monitors on the key: 2134/day, projected 64027/30 days. Remaining 99493; guard holds 81000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T05:20:40Z: outside read hours: closes/grades only
- 2026-11-01T05:10:26Z: outside read hours: closes/grades only
- 2026-11-01T05:00:30Z: outside read hours: closes/grades only
- 2026-11-01T04:50:24Z: outside read hours: closes/grades only
- 2026-11-01T04:40:25Z: outside read hours: closes/grades only
- 2026-11-01T04:39:48Z: outside read hours: closes/grades only
- 2026-11-01T04:30:21Z: outside read hours: closes/grades only
- 2026-11-01T04:27:40Z: outside read hours: closes/grades only
- 2026-11-01T04:20:22Z: outside read hours: closes/grades only
- 2026-11-01T04:10:25Z: outside read hours: closes/grades only

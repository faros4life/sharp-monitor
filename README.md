# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T12:40:59Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5570 | 5510 | -1.8c | 23.3% | 2364 | -1.1c | 5510 | 2805-2705-0 | -249.45u | -4.5% |  |  | criteria not met (5510/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1228 | 1221 | -3.75c | 16.4% | 271 | -2.97c | 1221 | 627-594-0 | -91.48u | -7.5% |  |  | criteria not met (1221/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 98 | 98 | -0.79c | 31.6% | 94 | -0.02c | 98 | 39-59-0 | -15.29u | -15.6% |  |  | criteria not met (98/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 8 | 5-3-0 | +2.39u | 29.9% |  |  |  |
| B ref age 1-5m | 57 | 57 | -0.73c | 29.8% | 55 | -0.11c | 57 | 24-33-0 | -5.62u | -9.9% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 237 | 236 | -0.72c | 31.4% | 234 | -0.69c | 237 | 122-112-3 | -4.17u | -1.8% | 0.07c | 26s | criteria not met (237/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 121 | 121 | -0.79c | 33.1% | 120 | -1.0c | 121 | 61-58-2 | -2.35u | -1.9% | -0.27c | 46s |  |
| M gettable, price moves | 116 | 115 | -0.65c | 29.6% | 114 | -0.36c | 116 | 61-54-1 | -1.82u | -1.6% | 0.42c | 22s |  |
| M control: not gettable | 892 | 723 | -0.89c | 34.2% | 717 | -1.29c | 744 | 378-352-14 | -18.58u | -2.5% | 1.77c | 55s |  |
| M all moves | 1129 | 959 | -0.85c | 33.5% | 951 | -1.15c | 981 | 500-464-17 | -22.75u | -2.3% | 1.41c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 912 | 2.34c | 23.1% | 189 | 1.98c | 913 | 403-510-0 | +262.23u | 28.7% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 54 | -0.14c | 20-34-0 | -12.40u | 37, -0.55c, -8.00u | negative |
| J2 B, NBA | 38 | 38 | 0.01c | 14-24-0 | -8.95u | 23, -0.47c, -2.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 32 | -0.39c | 14-18-0 | -2.97u | 25, -0.69c, +1.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 106 | 106 | -0.83c | 50-55-1 | -7.77u | 66, -0.98c, -4.82u | negative |
| D1 B, unders (descriptive) | 12 | 12 | 0.71c | 7-5-0 | +2.46u | 12, 0.71c, +2.46u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 10 | -1.1c | 1-9-0 | -7.81u | 8, -1.51c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 6 | 0.52c | 3-3-0 | +1.46u | 5, 0.53c, +0.31u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 45 | 45 | -0.4c | 25-18-2 | -1.93u | 21, -0.56c, -1.30u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1122 | 51 | 4.5% | -0.49c | 1.6c | 22-29-0 | -6.11u |  |
| MK novig fair-2c | 1123 | 19 | 1.7% | -0.4c | 2.52c | 11-8-0 | +4.14u |  |
| MK prophetx fair-1c | 2746 | 134 | 4.9% | -0.86c | 1.1c | 71-61-2 | +13.30u |  |
| MK prophetx fair-2c | 2728 | 38 | 1.4% | -0.6c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 3868 | 185 | 4.8% | -0.76c | 1.25c | 93-90-2 | +7.20u | criteria not met (185/50 graded, CLV not positive) |
| MK all fair-2c | 3851 | 57 | 1.5% | -0.53c | 2.18c | 27-30-0 | -0.43u | criteria not met (57/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 81.

## Odds API credits (100K/month plan)

Study: 595/day, projected 17851/30 days. All monitors on the key: 2025/day, projected 60754/30 days. Remaining 91253; guard holds 70600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T12:40:59Z: outside read hours: closes/grades only
- 2026-11-05T12:31:11Z: outside read hours: closes/grades only
- 2026-11-05T12:20:50Z: outside read hours: closes/grades only
- 2026-11-05T12:10:47Z: outside read hours: closes/grades only
- 2026-11-05T12:01:15Z: outside read hours: closes/grades only
- 2026-11-05T11:50:54Z: outside read hours: closes/grades only
- 2026-11-05T11:40:57Z: outside read hours: closes/grades only
- 2026-11-05T11:30:42Z: outside read hours: closes/grades only
- 2026-11-05T11:28:51Z: outside read hours: closes/grades only
- 2026-11-05T11:20:52Z: outside read hours: closes/grades only

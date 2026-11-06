# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-06T06:01:08Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5978 | 5803 | -1.75c | 23.6% | 2512 | -1.08c | 5761 | 2952-2809-0 | -239.65u | -4.2% |  |  | criteria not met (5761/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1315 | 1242 | -3.71c | 16.3% | 277 | -2.91c | 1238 | 638-600-0 | -91.46u | -7.4% |  |  | criteria not met (1238/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 107 | 104 | -0.83c | 30.8% | 99 | 0.01c | 103 | 41-62-0 | -16.10u | -15.6% |  |  | criteria not met (103/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 61 | 60 | -0.73c | 30.0% | 58 | -0.09c | 60 | 26-34-0 | -4.43u | -7.4% |  |  |  |
| B ref age 5m+ | 37 | 35 | -1.23c | 31.4% | 32 | -0.1c | 34 | 10-24-0 | -13.06u | -38.4% |  |  |  |
| M move-watch: gettable (sightings) | 261 | 256 | -0.69c | 32.0% | 254 | -0.69c | 256 | 133-120-3 | -2.14u | -0.8% | 0.09c | 26s | criteria not met (256/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 131 | 129 | -0.75c | 33.3% | 128 | -0.98c | 128 | 65-61-2 | -1.65u | -1.3% | -0.24c | 46s |  |
| M gettable, price moves | 130 | 127 | -0.63c | 30.7% | 126 | -0.39c | 128 | 68-59-1 | -0.48u | -0.4% | 0.42c | 22s |  |
| M control: not gettable | 967 | 778 | -0.9c | 34.1% | 772 | -1.27c | 794 | 391-389-14 | -43.96u | -5.5% | 1.76c | 108s |  |
| M all moves | 1228 | 1034 | -0.85c | 33.6% | 1026 | -1.12c | 1050 | 524-509-17 | -46.10u | -4.4% | 1.41c | 64s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 932 | 916 | 2.32c | 23.1% | 190 | 1.97c | 917 | 404-513-0 | +261.89u | 28.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 62 | 58 | -0.11c | 22-36-0 | -12.21u | 40, -0.46c, -8.96u | negative |
| J2 B, NBA | 43 | 39 | 0.03c | 14-25-0 | -9.95u | 24, -0.42c, -3.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 36 | 35 | -0.34c | 16-19-0 | -1.78u | 27, -0.6c, +1.98u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 125 | 120 | -0.8c | 58-61-1 | -6.03u | 69, -0.9c, -5.91u | negative |
| D1 B, unders (descriptive) | 15 | 13 | 0.74c | 7-6-0 | +1.46u | 13, 0.74c, +1.46u | descriptive only |
| D2 B, underdog spreads (descriptive) | 12 | 11 | -1.04c | 2-9-0 | -6.66u | 9, -1.39c, -4.66u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 7 | 7 | 0.61c | 3-4-0 | +0.46u | 6, 0.64c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 50 | 50 | -0.45c | 28-20-2 | -1.64u | 25, -0.66c, -1.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1362 | 59 | 4.3% | -0.61c | 1.59c | 28-30-0 | -1.41u |  |
| MK novig fair-2c | 1362 | 22 | 1.6% | -0.46c | 2.52c | 14-8-0 | +7.49u |  |
| MK prophetx fair-1c | 2963 | 148 | 5.0% | -0.86c | 1.1c | 82-64-2 | +22.05u |  |
| MK prophetx fair-2c | 2942 | 42 | 1.4% | -0.61c | 2.04c | 20-22-0 | -0.22u |  |
| MK all fair-1c | 4325 | 207 | 4.8% | -0.79c | 1.26c | 110-94-2 | +20.64u | criteria not met (206/50 graded, CLV not positive) |
| MK all fair-2c | 4304 | 64 | 1.5% | -0.56c | 2.19c | 34-30-0 | +7.27u | criteria not met (64/50 graded, CLV not positive) |

A and B on the same side/line: 86.

## Odds API credits (100K/month plan)

Study: 622/day, projected 18666/30 days. All monitors on the key: 2119/day, projected 63556/30 days. Remaining 88910; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-06T06:01:08Z: outside read hours: closes/grades only
- 2026-11-06T05:50:40Z: outside read hours: closes/grades only
- 2026-11-06T05:40:43Z: outside read hours: closes/grades only
- 2026-11-06T05:31:06Z: outside read hours: closes/grades only
- 2026-11-06T05:20:43Z: outside read hours: closes/grades only
- 2026-11-06T05:11:02Z: outside read hours: closes/grades only
- 2026-11-06T05:00:49Z: outside read hours: closes/grades only
- 2026-11-06T04:50:54Z: 16 games (16 in 24h), quotes {'prophetx': 1434, 'novig': 710, 'kalshi': 1046, 'polymarket_us': 1636}, 54 unmatched (2 book-games; fuzzy-matched 0), 2367 side/lines, polls [none_due], moves 0, new A 1 B 1, maker posted 0 filled 0, credits used 0 left 88910, 185s
- 2026-11-06T04:40:51Z: 16 games (16 in 24h), quotes {'prophetx': 1434, 'novig': 720, 'kalshi': 1062, 'polymarket_us': 1768}, 70 unmatched (3 book-games; fuzzy-matched 0), 2426 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 88919, 182s
- 2026-11-06T04:31:14Z: 16 games (16 in 24h), quotes {'prophetx': 1434, 'novig': 716, 'kalshi': 1074, 'polymarket_us': 1768}, 82 unmatched (3 book-games; fuzzy-matched 0), 2427 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 4, new A 15 B 0, maker posted 0 filled 0, credits used 6 left 88928, 182s

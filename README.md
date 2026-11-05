# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T18:24:04Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5696 | 5510 | -1.8c | 23.3% | 2364 | -1.1c | 5510 | 2805-2705-0 | -249.45u | -4.5% |  |  | criteria not met (5510/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1235 | 1221 | -3.75c | 16.4% | 271 | -2.97c | 1221 | 627-594-0 | -91.48u | -7.5% |  |  | criteria not met (1221/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 100 | 98 | -0.79c | 31.6% | 94 | -0.02c | 98 | 39-59-0 | -15.29u | -15.6% |  |  | criteria not met (98/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 8 | 5-3-0 | +2.39u | 29.9% |  |  |  |
| B ref age 1-5m | 58 | 57 | -0.73c | 29.8% | 55 | -0.11c | 57 | 24-33-0 | -5.62u | -9.9% |  |  |  |
| B ref age 5m+ | 34 | 33 | -1.1c | 33.3% | 31 | -0.13c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 245 | 236 | -0.72c | 31.4% | 234 | -0.69c | 237 | 122-112-3 | -4.17u | -1.8% | 0.07c | 28s | criteria not met (237/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 123 | 121 | -0.79c | 33.1% | 120 | -1.0c | 121 | 61-58-2 | -2.35u | -1.9% | -0.27c | 64s |  |
| M gettable, price moves | 122 | 115 | -0.65c | 29.6% | 114 | -0.36c | 116 | 61-54-1 | -1.82u | -1.6% | 0.42c | 22s |  |
| M control: not gettable | 919 | 723 | -0.89c | 34.2% | 717 | -1.29c | 744 | 378-352-14 | -18.58u | -2.5% | 1.77c | 106s |  |
| M all moves | 1164 | 959 | -0.85c | 33.5% | 951 | -1.15c | 981 | 500-464-17 | -22.75u | -2.3% | 1.41c | 63s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 916 | 912 | 2.34c | 23.1% | 189 | 1.98c | 913 | 403-510-0 | +262.23u | 28.7% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 56 | 54 | -0.14c | 20-34-0 | -12.40u | 37, -0.55c, -8.00u | negative |
| J2 B, NBA | 38 | 38 | 0.01c | 14-24-0 | -8.95u | 23, -0.47c, -2.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 33 | 32 | -0.39c | 14-18-0 | -2.97u | 25, -0.69c, +1.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 110 | 106 | -0.83c | 50-55-1 | -7.77u | 66, -0.98c, -4.82u | negative |
| D1 B, unders (descriptive) | 13 | 12 | 0.71c | 7-5-0 | +2.46u | 12, 0.71c, +2.46u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 10 | -1.1c | 1-9-0 | -7.81u | 8, -1.51c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 6 | 0.52c | 3-3-0 | +1.46u | 5, 0.53c, +0.31u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 49 | 45 | -0.4c | 25-18-2 | -1.93u | 21, -0.56c, -1.30u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1148 | 51 | 4.5% | -0.49c | 1.6c | 22-29-0 | -6.11u |  |
| MK novig fair-2c | 1149 | 19 | 1.7% | -0.4c | 2.52c | 11-8-0 | +4.14u |  |
| MK prophetx fair-1c | 2764 | 134 | 4.9% | -0.86c | 1.1c | 71-61-2 | +13.30u |  |
| MK prophetx fair-2c | 2746 | 38 | 1.4% | -0.6c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 3912 | 185 | 4.8% | -0.76c | 1.25c | 93-90-2 | +7.20u | criteria not met (185/50 graded, CLV not positive) |
| MK all fair-2c | 3895 | 57 | 1.5% | -0.53c | 2.18c | 27-30-0 | -0.43u | criteria not met (57/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 83.

## Odds API credits (100K/month plan)

Study: 590/day, projected 17688/30 days. All monitors on the key: 2060/day, projected 61800/30 days. Remaining 90463; guard holds 70600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T18:21:01Z: 24 games (16 in 24h), quotes {'prophetx': 990, 'novig': 704, 'kalshi': 984, 'polymarket_us': 1070}, 199 unmatched (4 book-games; fuzzy-matched 0), 2021 side/lines, polls [none_due; NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 2 left 90463, 182s
- 2026-11-05T18:11:04Z: 24 games (16 in 24h), quotes {'prophetx': 990, 'novig': 709, 'kalshi': 980, 'polymarket_us': 1070}, 197 unmatched (4 book-games; fuzzy-matched 0), 2021 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:fast; NHL:fast], moves 1, new A 1 B 0, maker posted 88 filled 0, credits used 10 left 90467, 309s
- 2026-11-05T18:01:00Z: 24 games (16 in 24h), quotes {'prophetx': 990, 'novig': 705, 'kalshi': 986, 'polymarket_us': 1070}, 197 unmatched (4 book-games; fuzzy-matched 0), 2025 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 90510, 181s
- 2026-11-05T17:50:53Z: 24 games (16 in 24h), quotes {'prophetx': 988, 'novig': 707, 'kalshi': 984, 'polymarket_us': 1070}, 197 unmatched (4 book-games; fuzzy-matched 0), 2025 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 6, new A 2 B 0, maker posted 0 filled 0, credits used 8 left 90521, 182s
- 2026-11-05T17:40:59Z: 24 games (16 in 24h), quotes {'prophetx': 988, 'novig': 710, 'kalshi': 986, 'polymarket_us': 1070}, 187 unmatched (4 book-games; fuzzy-matched 0), 2029 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 90542, 183s
- 2026-11-05T17:30:57Z: 24 games (16 in 24h), quotes {'prophetx': 982, 'novig': 714, 'kalshi': 982, 'polymarket_us': 1070}, 181 unmatched (4 book-games; fuzzy-matched 0), 2027 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 90553, 184s
- 2026-11-05T17:21:01Z: 24 games (16 in 24h), quotes {'prophetx': 946, 'novig': 704, 'kalshi': 988, 'polymarket_us': 1070}, 180 unmatched (4 book-games; fuzzy-matched 0), 2015 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 4, new A 5 B 0, maker posted 0 filled 0, credits used 8 left 90566, 182s
- 2026-11-05T17:11:02Z: 24 games (16 in 24h), quotes {'prophetx': 980, 'novig': 714, 'kalshi': 984, 'polymarket_us': 1070}, 179 unmatched (4 book-games; fuzzy-matched 0), 2030 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 90585, 183s
- 2026-11-05T17:00:49Z: 24 games (16 in 24h), quotes {'prophetx': 976, 'novig': 708, 'kalshi': 982, 'polymarket_us': 1070}, 175 unmatched (4 book-games; fuzzy-matched 0), 2027 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 1, new A 6 B 1, maker posted 0 filled 0, credits used 8 left 90596, 183s
- 2026-11-05T16:50:40Z: 24 games (16 in 24h), quotes {'prophetx': 974, 'novig': 716, 'kalshi': 982, 'polymarket_us': 1070}, 173 unmatched (4 book-games; fuzzy-matched 0), 2026 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 90626, 184s

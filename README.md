# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-06T21:56:40Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6184 | 5803 | -1.75c | 23.6% | 2512 | -1.08c | 5803 | 2973-2830-0 | -238.73u | -4.1% |  |  | criteria not met (5803/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1331 | 1242 | -3.71c | 16.3% | 277 | -2.91c | 1242 | 640-602-0 | -91.87u | -7.4% |  |  | criteria not met (1242/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 110 | 104 | -0.83c | 30.8% | 99 | 0.01c | 104 | 42-62-0 | -15.00u | -14.4% |  |  | criteria not met (104/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 63 | 60 | -0.73c | 30.0% | 58 | -0.09c | 60 | 26-34-0 | -4.43u | -7.4% |  |  |  |
| B ref age 5m+ | 38 | 35 | -1.23c | 31.4% | 32 | -0.1c | 35 | 11-24-0 | -11.96u | -34.2% |  |  |  |
| M move-watch: gettable (sightings) | 282 | 256 | -0.69c | 32.0% | 254 | -0.69c | 257 | 133-121-3 | -3.14u | -1.2% | 0.09c | 28s | criteria not met (257/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 141 | 129 | -0.75c | 33.3% | 128 | -0.98c | 129 | 65-62-2 | -2.65u | -2.1% | -0.24c | 44s |  |
| M gettable, price moves | 141 | 127 | -0.63c | 30.7% | 126 | -0.39c | 128 | 68-59-1 | -0.48u | -0.4% | 0.42c | 24s |  |
| M control: not gettable | 1074 | 778 | -0.9c | 34.1% | 772 | -1.27c | 801 | 394-393-14 | -45.42u | -5.7% | 1.76c | 168s |  |
| M all moves | 1356 | 1034 | -0.85c | 33.6% | 1026 | -1.12c | 1058 | 527-514-17 | -48.56u | -4.6% | 1.41c | 108s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 935 | 916 | 2.32c | 23.1% | 190 | 1.97c | 917 | 404-513-0 | +261.89u | 28.6% | 1.1c | 24s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 64 | 59 | -0.11c | 23-36-0 | -11.12u | 41, -0.46c, -7.87u | negative |
| J2 B, NBA | 45 | 40 | 0.03c | 15-25-0 | -8.85u | 25, -0.42c, -2.29u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 37 | 35 | -0.34c | 16-19-0 | -1.78u | 27, -0.6c, +1.98u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 143 | 121 | -0.8c | 58-62-1 | -7.03u | 70, -0.9c, -6.91u | negative |
| D1 B, unders (descriptive) | 16 | 14 | 0.74c | 8-6-0 | +2.56u | 14, 0.74c, +2.56u | descriptive only |
| D2 B, underdog spreads (descriptive) | 13 | 11 | -1.04c | 2-9-0 | -6.66u | 9, -1.39c, -4.66u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 8 | 7 | 0.61c | 3-4-0 | +0.46u | 6, 0.64c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 53 | 50 | -0.45c | 28-20-2 | -1.64u | 25, -0.66c, -1.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1454 | 61 | 4.3% | -0.61c | 1.59c | 29-30-0 | -0.37u |  |
| MK novig fair-2c | 1455 | 22 | 1.5% | -0.46c | 2.52c | 14-8-0 | +7.49u |  |
| MK prophetx fair-1c | 3107 | 151 | 4.9% | -0.86c | 1.1c | 82-64-2 | +22.05u |  |
| MK prophetx fair-2c | 3086 | 42 | 1.4% | -0.61c | 2.04c | 20-22-0 | -0.22u |  |
| MK all fair-1c | 4561 | 212 | 4.7% | -0.79c | 1.26c | 111-94-2 | +21.68u | criteria not met (207/50 graded, CLV not positive) |
| MK all fair-2c | 4541 | 64 | 1.4% | -0.56c | 2.19c | 34-30-0 | +7.27u | criteria not met (64/50 graded, CLV not positive) |

A and B on the same side/line: 88.

## Odds API credits (100K/month plan)

Study: 611/day, projected 18343/30 days. All monitors on the key: 2101/day, projected 63039/30 days. Remaining 87686; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-06T21:51:14Z: 80 games (52 in 24h), quotes {'prophetx': 7672, 'novig': 707, 'kalshi': 2726, 'polymarket_us': 1880}, 2298 unmatched (71 book-games; fuzzy-matched 1), 5231 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 31 filled 0, credits used 12 left 87686, 326s
- 2026-11-06T21:41:10Z: 80 games (52 in 24h), quotes {'prophetx': 5932, 'novig': 711, 'kalshi': 2322, 'polymarket_us': 1642}, 1519 unmatched (49 book-games; fuzzy-matched 1), 4720 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 1 B 0, maker posted 20 filled 0, credits used 6 left 87722, 198s
- 2026-11-06T21:31:17Z: 80 games (52 in 24h), quotes {'prophetx': 9034, 'novig': 717, 'kalshi': 2398, 'polymarket_us': 1672}, 2181 unmatched (65 book-games; fuzzy-matched 2), 6101 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 33 filled 0, credits used 12 left 87739, 302s
- 2026-11-06T21:21:12Z: 80 games (52 in 24h), quotes {'prophetx': 4992, 'novig': 711, 'kalshi': 2280, 'polymarket_us': 1376}, 1130 unmatched (36 book-games; fuzzy-matched 1), 4573 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 12 filled 0, credits used 6 left 87773, 211s
- 2026-11-06T21:12:22Z: 80 games (50 in 24h), quotes {'prophetx': 8150, 'novig': 717, 'kalshi': 3676, 'polymarket_us': 2890}, 3914 unmatched (100 book-games; fuzzy-matched 1), 5747 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 6 B 0, maker posted 20 filled 0, credits used 6 left 87779, 289s
- 2026-11-06T21:07:25Z: 80 games (50 in 24h), quotes {'prophetx': 9858, 'novig': 715, 'kalshi': 2364, 'polymarket_us': 1732}, 2224 unmatched (67 book-games; fuzzy-matched 1), 6771 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 8 filled 0, credits used 6 left 87794, 235s
- 2026-11-06T21:01:17Z: 80 games (50 in 24h), quotes {'prophetx': 2986, 'novig': 713, 'kalshi': 2328, 'polymarket_us': 1666}, 762 unmatched (28 book-games; fuzzy-matched 1), 4073 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 17 filled 1, credits used 12 left 87809, 303s
- 2026-11-06T20:51:00Z: 80 games (46 in 24h), quotes {'prophetx': 9142, 'novig': 715, 'kalshi': 2980, 'polymarket_us': 1858}, 2610 unmatched (81 book-games; fuzzy-matched 1), 6452 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 8 filled 0, credits used 12 left 87835, 324s
- 2026-11-06T20:41:00Z: 80 games (45 in 24h), quotes {'prophetx': 7440, 'novig': 719, 'kalshi': 2296, 'polymarket_us': 1740}, 1955 unmatched (58 book-games; fuzzy-matched 1), 4997 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 6 B 0, maker posted 24 filled 1, credits used 6 left 87868, 279s
- 2026-11-06T20:31:14Z: 80 games (45 in 24h), quotes {'prophetx': 5728, 'novig': 719, 'kalshi': 2662, 'polymarket_us': 1750}, 1646 unmatched (56 book-games; fuzzy-matched 2), 4851 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 2 B 0, maker posted 28 filled 0, credits used 12 left 87883, 302s

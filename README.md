# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T20:25:58Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6793 | 6551 | -1.69c | 23.8% | 2858 | -1.07c | 6397 | 3286-3111-0 | -260.51u | -4.1% |  |  | criteria not met (6397/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1478 | 1399 | -3.55c | 16.4% | 316 | -2.9c | 1360 | 697-663-0 | -114.91u | -8.4% |  |  | criteria not met (1360/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 120 | 119 | -0.97c | 29.4% | 111 | -0.1c | 118 | 51-67-0 | -10.26u | -8.7% |  |  | criteria not met (118/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 70 | 70 | -1.01c | 28.6% | 67 | -0.16c | 69 | 32-37-0 | -0.89u | -1.3% |  |  |  |
| B ref age 5m+ | 41 | 40 | -1.13c | 30.0% | 35 | -0.29c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 319 | 296 | -0.66c | 33.4% | 294 | -0.64c | 287 | 147-136-4 | -5.25u | -1.8% | 0.15c | 27s | criteria not met (287/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 164 | 151 | -0.73c | 35.1% | 151 | -0.9c | 145 | 72-70-3 | -4.18u | -2.9% | -0.17c | 28s |  |
| M gettable, price moves | 155 | 145 | -0.59c | 31.7% | 143 | -0.37c | 142 | 75-66-1 | -1.07u | -0.8% | 0.48c | 26s |  |
| M control: not gettable | 1330 | 935 | -0.85c | 35.1% | 926 | -1.24c | 921 | 446-459-16 | -66.74u | -7.2% | 1.76c | 183s |  |
| M all moves | 1649 | 1231 | -0.8c | 34.7% | 1220 | -1.09c | 1208 | 593-595-20 | -71.99u | -6.0% | 1.42c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 985 | 940 | 2.21c | 23.2% | 198 | 1.86c | 934 | 413-521-0 | +272.46u | 29.2% | 0.75c | 24s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 73 | 71 | -0.27c | 31-40-0 | -6.38u | 47, -0.57c, -9.72u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 43 | 42 | -0.4c | 21-21-0 | +1.76u | 32, -0.7c, +3.29u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 177 | 149 | -0.72c | 71-76-2 | -8.66u | 85, -0.77c, -10.30u | negative |
| D1 B, unders (descriptive) | 21 | 20 | 0.4c | 12-8-0 | +4.79u | 19, 0.36c, +3.70u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 52 | -0.38c | 29-21-2 | -2.11u | 27, -0.5c, -2.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1588 | 72 | 4.6% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1585 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3994 | 199 | 5.2% | -0.97c | 1.11c | 91-75-2 | +20.42u |  |
| MK prophetx fair-2c | 3968 | 64 | 1.7% | -0.57c | 2.04c | 26-25-0 | +3.23u |  |
| MK all fair-1c | 5582 | 271 | 5.0% | -0.87c | 1.26c | 128-110-2 | +23.51u | criteria not met (240/50 graded, CLV not positive) |
| MK all fair-2c | 5553 | 90 | 1.7% | -0.51c | 2.19c | 42-35-0 | +10.88u | criteria not met (77/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 625/day, projected 18738/30 days. All monitors on the key: 2135/day, projected 64055/30 days. Remaining 85343; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T20:20:55Z: 70 games (60 in 24h), quotes {'prophetx': 7106, 'novig': 555, 'kalshi': 2482, 'polymarket_us': 1584}, 2344 unmatched (72 book-games; fuzzy-matched 0), 6534 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 10, new A 21 B 0, maker posted 82 filled 1, credits used 12 left 85343, 301s
- 2026-11-07T20:11:19Z: 70 games (60 in 24h), quotes {'prophetx': 7104, 'novig': 564, 'kalshi': 3684, 'polymarket_us': 3014}, 3301 unmatched (91 book-games; fuzzy-matched 0), 7283 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 44 B 0, maker posted 33 filled 1, credits used 8 left 85387, 182s
- 2026-11-07T20:01:38Z: 72 games (62 in 24h), quotes {'prophetx': 7104, 'novig': 559, 'kalshi': 2386, 'polymarket_us': 1748}, 2441 unmatched (79 book-games; fuzzy-matched 61), 6574 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 18 B 0, maker posted 54 filled 3, credits used 12 left 85408, 394s
- 2026-11-07T19:51:20Z: 73 games (63 in 24h), quotes {'prophetx': 2260, 'novig': 95, 'kalshi': 428, 'polymarket_us': 382}, 1169 unmatched (41 book-games; fuzzy-matched 0), 1394 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 0 B 0, maker posted 4 filled 1, credits used 12 left 85440, 302s
- 2026-11-07T19:42:20Z: 73 games (63 in 24h), quotes {'prophetx': 8202, 'novig': 571, 'kalshi': 2388, 'polymarket_us': 1870}, 4172 unmatched (104 book-games; fuzzy-matched 0), 6378 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 21 filled 2, credits used 8 left 85463, 183s
- 2026-11-07T19:37:19Z: 73 games (63 in 24h), quotes {'prophetx': 7000, 'novig': 576, 'kalshi': 2314, 'polymarket_us': 1808}, 4188 unmatched (104 book-games; fuzzy-matched 0), 5162 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 68 filled 2, credits used 6 left 85482, 212s
- 2026-11-07T19:31:09Z: 73 games (63 in 24h), quotes {'prophetx': 8158, 'novig': 573, 'kalshi': 3528, 'polymarket_us': 3148}, 4696 unmatched (115 book-games; fuzzy-matched 0), 7153 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 12 B 0, maker posted 17 filled 1, credits used 6 left 85500, 255s
- 2026-11-07T19:21:20Z: 74 games (64 in 24h), quotes {'prophetx': 8438, 'novig': 573, 'kalshi': 2976, 'polymarket_us': 2076}, 4297 unmatched (109 book-games; fuzzy-matched 0), 6730 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 8 B 0, maker posted 54 filled 1, credits used 14 left 85510, 302s
- 2026-11-07T19:10:54Z: 74 games (64 in 24h), quotes {'prophetx': 8436, 'novig': 582, 'kalshi': 2740, 'polymarket_us': 2006}, 4263 unmatched (106 book-games; fuzzy-matched 0), 6812 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 5 B 0, maker posted 68 filled 1, credits used 12 left 85539, 301s
- 2026-11-07T19:01:16Z: 74 games (64 in 24h), quotes {'prophetx': 8436, 'novig': 572, 'kalshi': 2374, 'polymarket_us': 1830}, 4261 unmatched (106 book-games; fuzzy-matched 0), 6617 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 5 B 0, maker posted 15 filled 2, credits used 6 left 85575, 258s

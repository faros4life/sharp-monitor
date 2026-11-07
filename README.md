# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T19:56:22Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6722 | 6502 | -1.69c | 23.9% | 2843 | -1.06c | 6357 | 3270-3087-0 | -253.46u | -4.0% |  |  | criteria not met (6357/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1458 | 1381 | -3.57c | 16.5% | 312 | -2.91c | 1351 | 694-657-0 | -110.27u | -8.2% |  |  | criteria not met (1351/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 120 | 119 | -0.97c | 29.4% | 111 | -0.1c | 118 | 51-67-0 | -10.26u | -8.7% |  |  | criteria not met (118/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 70 | 70 | -1.01c | 28.6% | 67 | -0.16c | 69 | 32-37-0 | -0.89u | -1.3% |  |  |  |
| B ref age 5m+ | 41 | 40 | -1.13c | 30.0% | 35 | -0.29c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 318 | 294 | -0.67c | 33.0% | 292 | -0.64c | 282 | 146-132-4 | -2.15u | -0.8% | 0.15c | 27s | criteria not met (282/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 164 | 150 | -0.74c | 34.7% | 150 | -0.9c | 143 | 71-69-3 | -4.08u | -2.9% | -0.16c | 28s |  |
| M gettable, price moves | 154 | 144 | -0.6c | 31.2% | 142 | -0.37c | 139 | 75-63-1 | +1.93u | 1.4% | 0.48c | 25s |  |
| M control: not gettable | 1318 | 930 | -0.85c | 35.3% | 921 | -1.24c | 911 | 441-454-16 | -66.00u | -7.2% | 1.76c | 183s |  |
| M all moves | 1636 | 1224 | -0.81c | 34.7% | 1213 | -1.1c | 1193 | 587-586-20 | -68.14u | -5.7% | 1.43c | 144s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 973 | 939 | 2.22c | 23.2% | 197 | 1.86c | 933 | 412-521-0 | +270.26u | 29.0% | 0.75c | 24s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 73 | 71 | -0.27c | 31-40-0 | -6.38u | 47, -0.57c, -9.72u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 43 | 42 | -0.4c | 21-21-0 | +1.76u | 32, -0.7c, +3.29u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 176 | 144 | -0.72c | 70-72-2 | -5.56u | 82, -0.78c, -7.30u | negative |
| D1 B, unders (descriptive) | 21 | 20 | 0.4c | 12-8-0 | +4.79u | 19, 0.36c, +3.70u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 52 | -0.38c | 29-21-2 | -2.11u | 27, -0.5c, -2.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1577 | 72 | 4.6% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1574 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3921 | 195 | 5.1% | -0.97c | 1.11c | 90-73-2 | +21.40u |  |
| MK prophetx fair-2c | 3894 | 63 | 1.7% | -0.57c | 2.04c | 25-24-0 | +3.17u |  |
| MK all fair-1c | 5498 | 267 | 5.0% | -0.87c | 1.26c | 127-108-2 | +24.49u | criteria not met (237/50 graded, CLV not positive) |
| MK all fair-2c | 5468 | 89 | 1.7% | -0.51c | 2.19c | 41-34-0 | +10.82u | criteria not met (75/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 623/day, projected 18686/30 days. All monitors on the key: 2130/day, projected 63910/30 days. Remaining 85440; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T19:51:20Z: 73 games (63 in 24h), quotes {'prophetx': 2260, 'novig': 95, 'kalshi': 428, 'polymarket_us': 382}, 1169 unmatched (41 book-games; fuzzy-matched 0), 1394 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 0 B 0, maker posted 4 filled 1, credits used 12 left 85440, 302s
- 2026-11-07T19:42:20Z: 73 games (63 in 24h), quotes {'prophetx': 8202, 'novig': 571, 'kalshi': 2388, 'polymarket_us': 1870}, 4172 unmatched (104 book-games; fuzzy-matched 0), 6378 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 21 filled 2, credits used 8 left 85463, 183s
- 2026-11-07T19:37:19Z: 73 games (63 in 24h), quotes {'prophetx': 7000, 'novig': 576, 'kalshi': 2314, 'polymarket_us': 1808}, 4188 unmatched (104 book-games; fuzzy-matched 0), 5162 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 68 filled 2, credits used 6 left 85482, 212s
- 2026-11-07T19:31:09Z: 73 games (63 in 24h), quotes {'prophetx': 8158, 'novig': 573, 'kalshi': 3528, 'polymarket_us': 3148}, 4696 unmatched (115 book-games; fuzzy-matched 0), 7153 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 12 B 0, maker posted 17 filled 1, credits used 6 left 85500, 255s
- 2026-11-07T19:21:20Z: 74 games (64 in 24h), quotes {'prophetx': 8438, 'novig': 573, 'kalshi': 2976, 'polymarket_us': 2076}, 4297 unmatched (109 book-games; fuzzy-matched 0), 6730 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 8 B 0, maker posted 54 filled 1, credits used 14 left 85510, 302s
- 2026-11-07T19:10:54Z: 74 games (64 in 24h), quotes {'prophetx': 8436, 'novig': 582, 'kalshi': 2740, 'polymarket_us': 2006}, 4263 unmatched (106 book-games; fuzzy-matched 0), 6812 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 5 B 0, maker posted 68 filled 1, credits used 12 left 85539, 301s
- 2026-11-07T19:01:16Z: 74 games (64 in 24h), quotes {'prophetx': 8436, 'novig': 572, 'kalshi': 2374, 'polymarket_us': 1830}, 4261 unmatched (106 book-games; fuzzy-matched 0), 6617 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 5 B 0, maker posted 15 filled 2, credits used 6 left 85575, 258s
- 2026-11-07T18:55:55Z: 74 games (64 in 24h), quotes {'prophetx': 8550, 'novig': 580, 'kalshi': 2322, 'polymarket_us': 1882}, 5526 unmatched (115 book-games; fuzzy-matched 0), 5736 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 31 filled 1, credits used 8 left 85592, 184s
- 2026-11-07T18:50:25Z: 74 games (64 in 24h), quotes {'prophetx': 7658, 'novig': 583, 'kalshi': 2346, 'polymarket_us': 1950}, 5351 unmatched (115 book-games; fuzzy-matched 0), 4886 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 9, new A 1 B 1, maker posted 4 filled 1, credits used 6 left 85600, 275s
- 2026-11-07T18:41:29Z: 74 games (64 in 24h), quotes {'prophetx': 9242, 'novig': 581, 'kalshi': 2602, 'polymarket_us': 2256}, 5407 unmatched (118 book-games; fuzzy-matched 0), 6432 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 39 filled 2, credits used 12 left 85619, 302s

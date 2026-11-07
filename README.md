# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T18:16:29Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6569 | 6484 | -1.69c | 24.0% | 2837 | -1.06c | 6357 | 3270-3087-0 | -253.46u | -4.0% |  |  | criteria not met (6357/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1388 | 1372 | -3.58c | 16.6% | 309 | -2.91c | 1351 | 694-657-0 | -110.27u | -8.2% |  |  | criteria not met (1351/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 119 | 119 | -0.97c | 29.4% | 111 | -0.1c | 118 | 51-67-0 | -10.26u | -8.7% |  |  | criteria not met (118/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 70 | 70 | -1.01c | 28.6% | 67 | -0.16c | 69 | 32-37-0 | -0.89u | -1.3% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 314 | 294 | -0.67c | 33.0% | 292 | -0.64c | 282 | 146-132-4 | -2.15u | -0.8% | 0.15c | 27s | criteria not met (282/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 161 | 150 | -0.74c | 34.7% | 150 | -0.9c | 143 | 71-69-3 | -4.08u | -2.9% | -0.16c | 28s |  |
| M gettable, price moves | 153 | 144 | -0.6c | 31.2% | 142 | -0.37c | 139 | 75-63-1 | +1.93u | 1.4% | 0.48c | 26s |  |
| M control: not gettable | 1276 | 926 | -0.85c | 35.3% | 917 | -1.24c | 911 | 441-454-16 | -66.00u | -7.2% | 1.77c | 183s |  |
| M all moves | 1590 | 1220 | -0.81c | 34.8% | 1209 | -1.1c | 1193 | 587-586-20 | -68.14u | -5.7% | 1.43c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 956 | 937 | 2.23c | 23.3% | 196 | 1.88c | 933 | 412-521-0 | +270.26u | 29.0% | 1.01c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 72 | 71 | -0.27c | 31-40-0 | -6.38u | 47, -0.57c, -9.72u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 43 | 42 | -0.4c | 21-21-0 | +1.76u | 32, -0.7c, +3.29u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 172 | 144 | -0.72c | 70-72-2 | -5.56u | 82, -0.78c, -7.30u | negative |
| D1 B, unders (descriptive) | 21 | 20 | 0.4c | 12-8-0 | +4.79u | 19, 0.36c, +3.70u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 52 | -0.38c | 29-21-2 | -2.11u | 27, -0.5c, -2.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1572 | 72 | 4.6% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1569 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3713 | 185 | 5.1% | -0.97c | 1.11c | 90-73-2 | +21.40u |  |
| MK prophetx fair-2c | 3690 | 59 | 1.6% | -0.57c | 2.04c | 25-24-0 | +3.17u |  |
| MK all fair-1c | 5285 | 257 | 4.9% | -0.87c | 1.26c | 127-108-2 | +24.49u | criteria not met (237/50 graded, CLV not positive) |
| MK all fair-2c | 5259 | 85 | 1.6% | -0.51c | 2.19c | 41-34-0 | +10.82u | criteria not met (75/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 617/day, projected 18502/30 days. All monitors on the key: 2120/day, projected 63600/30 days. Remaining 85701; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T18:11:27Z: 74 games (64 in 24h), quotes {'prophetx': 9200, 'novig': 583, 'kalshi': 2710, 'polymarket_us': 2192}, 5981 unmatched (119 book-games; fuzzy-matched 0), 6403 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 53 filled 2, credits used 14 left 85701, 302s
- 2026-11-07T18:01:15Z: 77 games (66 in 24h), quotes {'prophetx': 7716, 'novig': 588, 'kalshi': 2420, 'polymarket_us': 1984}, 5730 unmatched (113 book-games; fuzzy-matched 0), 4910 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 0 B 0, maker posted 27 filled 0, credits used 12 left 85728, 376s
- 2026-11-07T17:50:51Z: 77 games (59 in 24h), quotes {'prophetx': 9666, 'novig': 631, 'kalshi': 2730, 'polymarket_us': 2236}, 7787 unmatched (141 book-games; fuzzy-matched 0), 5061 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 1 B 0, maker posted 21 filled 1, credits used 8 left 85771, 260s
- 2026-11-07T17:41:20Z: 78 games (60 in 24h), quotes {'prophetx': 10592, 'novig': 662, 'kalshi': 3674, 'polymarket_us': 3740}, 8874 unmatched (156 book-games; fuzzy-matched 0), 6506 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 12 B 0, maker posted 0 filled 0, credits used 12 left 85781, 301s
- 2026-11-07T17:31:09Z: 80 games (62 in 24h), quotes {'prophetx': 10174, 'novig': 658, 'kalshi': 2886, 'polymarket_us': 2228}, 7426 unmatched (137 book-games; fuzzy-matched 0), 5792 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 38 filled 2, credits used 6 left 85819, 208s
- 2026-11-07T17:21:20Z: 81 games (63 in 24h), quotes {'prophetx': 6434, 'novig': 638, 'kalshi': 2466, 'polymarket_us': 1958}, 6149 unmatched (123 book-games; fuzzy-matched 0), 3140 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 4 B 0, maker posted 69 filled 1, credits used 14 left 85844, 303s
- 2026-11-07T17:10:49Z: 81 games (63 in 24h), quotes {'prophetx': 9552, 'novig': 634, 'kalshi': 2806, 'polymarket_us': 2268}, 6796 unmatched (136 book-games; fuzzy-matched 0), 5128 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 11 B 0, maker posted 16 filled 0, credits used 6 left 85874, 183s
- 2026-11-07T17:00:57Z: 87 games (69 in 24h), quotes {'prophetx': 8214, 'novig': 635, 'kalshi': 2438, 'polymarket_us': 1688}, 5767 unmatched (123 book-games; fuzzy-matched 0), 4285 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 22 B 0, maker posted 65 filled 2, credits used 12 left 85893, 380s
- 2026-11-07T16:50:50Z: 89 games (71 in 24h), quotes {'prophetx': 6898, 'novig': 660, 'kalshi': 2236, 'polymarket_us': 1888}, 5758 unmatched (108 book-games; fuzzy-matched 4), 3143 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 8 B 0, maker posted 37 filled 3, credits used 14 left 85921, 302s
- 2026-11-07T16:40:52Z: 89 games (71 in 24h), quotes {'prophetx': 12720, 'novig': 658, 'kalshi': 2874, 'polymarket_us': 2018}, 6557 unmatched (127 book-games; fuzzy-matched 2), 7660 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 32 filled 1, credits used 6 left 85963, 183s

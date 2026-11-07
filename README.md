# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T20:55:59Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6842 | 6730 | -1.68c | 23.7% | 2928 | -1.07c | 6425 | 3298-3127-0 | -265.96u | -4.1% |  |  | criteria not met (6425/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1503 | 1455 | -3.46c | 16.6% | 332 | -2.85c | 1365 | 699-666-0 | -117.23u | -8.6% |  |  | criteria not met (1365/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 120 | 120 | -0.98c | 29.2% | 112 | -0.02c | 118 | 51-67-0 | -10.26u | -8.7% |  |  | criteria not met (118/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 70 | 70 | -1.01c | 28.6% | 67 | -0.16c | 69 | 32-37-0 | -0.89u | -1.3% |  |  |  |
| B ref age 5m+ | 41 | 41 | -1.16c | 29.3% | 36 | -0.02c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 319 | 298 | -0.66c | 33.6% | 296 | -0.64c | 293 | 150-139-4 | -5.47u | -1.9% | 0.15c | 27s | criteria not met (293/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 164 | 152 | -0.74c | 34.9% | 152 | -0.9c | 149 | 74-72-3 | -4.44u | -3.0% | -0.17c | 28s |  |
| M gettable, price moves | 155 | 146 | -0.58c | 32.2% | 144 | -0.35c | 144 | 76-67-1 | -1.03u | -0.7% | 0.49c | 26s |  |
| M control: not gettable | 1336 | 968 | -0.82c | 35.6% | 960 | -1.21c | 939 | 457-466-16 | -65.21u | -6.9% | 1.78c | 183s |  |
| M all moves | 1655 | 1266 | -0.79c | 35.2% | 1256 | -1.08c | 1232 | 607-605-20 | -70.69u | -5.7% | 1.45c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 995 | 980 | 2.38c | 24.4% | 204 | 2.06c | 935 | 414-521-0 | +273.33u | 29.2% | 1.03c | 24s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 73 | 71 | -0.12c | 31-40-0 | -6.38u | 47, -0.35c, -9.72u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 43 | 42 | -0.4c | 21-21-0 | +1.76u | 32, -0.7c, +3.29u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 177 | 154 | -0.71c | 74-78-2 | -7.89u | 88, -0.76c, -11.41u | negative |
| D1 B, unders (descriptive) | 21 | 20 | 0.4c | 12-8-0 | +4.79u | 19, 0.36c, +3.70u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 53 | -0.38c | 29-22-2 | -3.11u | 28, -0.5c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1598 | 72 | 4.5% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1595 | 26 | 1.6% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4055 | 200 | 5.1% | -0.95c | 1.11c | 92-79-2 | +17.44u |  |
| MK prophetx fair-2c | 4029 | 64 | 1.6% | -0.46c | 2.04c | 26-28-0 | +0.23u |  |
| MK all fair-1c | 5653 | 272 | 4.9% | -0.86c | 1.25c | 129-114-2 | +20.53u | criteria not met (245/50 graded, CLV not positive) |
| MK all fair-2c | 5624 | 90 | 1.6% | -0.43c | 2.18c | 42-38-0 | +7.88u | criteria not met (80/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 626/day, projected 18789/30 days. All monitors on the key: 2138/day, projected 64143/30 days. Remaining 85266; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T20:50:57Z: 62 games (52 in 24h), quotes {'prophetx': 5890, 'novig': 685, 'kalshi': 2792, 'polymarket_us': 2030}, 3560 unmatched (88 book-games; fuzzy-matched 0), 5418 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 19 B 0, maker posted 8 filled 1, credits used 12 left 85266, 301s
- 2026-11-07T20:41:20Z: 64 games (55 in 24h), quotes {'prophetx': 5994, 'novig': 686, 'kalshi': 2890, 'polymarket_us': 1992}, 3386 unmatched (88 book-games; fuzzy-matched 0), 5687 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 80 filled 0, credits used 6 left 85290, 183s
- 2026-11-07T20:31:27Z: 69 games (59 in 24h), quotes {'prophetx': 5986, 'novig': 685, 'kalshi': 2720, 'polymarket_us': 2206}, 3185 unmatched (82 book-games; fuzzy-matched 60), 5924 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 31 B 0, maker posted 54 filled 0, credits used 14 left 85307, 400s
- 2026-11-07T20:20:55Z: 70 games (60 in 24h), quotes {'prophetx': 7106, 'novig': 555, 'kalshi': 2482, 'polymarket_us': 1584}, 2344 unmatched (72 book-games; fuzzy-matched 0), 6534 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 10, new A 21 B 0, maker posted 82 filled 1, credits used 12 left 85343, 301s
- 2026-11-07T20:11:19Z: 70 games (60 in 24h), quotes {'prophetx': 7104, 'novig': 564, 'kalshi': 3684, 'polymarket_us': 3014}, 3301 unmatched (91 book-games; fuzzy-matched 0), 7283 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 44 B 0, maker posted 33 filled 1, credits used 8 left 85387, 182s
- 2026-11-07T20:01:38Z: 72 games (62 in 24h), quotes {'prophetx': 7104, 'novig': 559, 'kalshi': 2386, 'polymarket_us': 1748}, 2441 unmatched (79 book-games; fuzzy-matched 61), 6574 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 18 B 0, maker posted 54 filled 3, credits used 12 left 85408, 394s
- 2026-11-07T19:51:20Z: 73 games (63 in 24h), quotes {'prophetx': 2260, 'novig': 95, 'kalshi': 428, 'polymarket_us': 382}, 1169 unmatched (41 book-games; fuzzy-matched 0), 1394 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 0 B 0, maker posted 4 filled 1, credits used 12 left 85440, 302s
- 2026-11-07T19:42:20Z: 73 games (63 in 24h), quotes {'prophetx': 8202, 'novig': 571, 'kalshi': 2388, 'polymarket_us': 1870}, 4172 unmatched (104 book-games; fuzzy-matched 0), 6378 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 21 filled 2, credits used 8 left 85463, 183s
- 2026-11-07T19:37:19Z: 73 games (63 in 24h), quotes {'prophetx': 7000, 'novig': 576, 'kalshi': 2314, 'polymarket_us': 1808}, 4188 unmatched (104 book-games; fuzzy-matched 0), 5162 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 68 filled 2, credits used 6 left 85482, 212s
- 2026-11-07T19:31:09Z: 73 games (63 in 24h), quotes {'prophetx': 8158, 'novig': 573, 'kalshi': 3528, 'polymarket_us': 3148}, 4696 unmatched (115 book-games; fuzzy-matched 0), 7153 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 12 B 0, maker posted 17 filled 1, credits used 6 left 85500, 255s

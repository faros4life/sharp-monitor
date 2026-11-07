# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T21:44:02Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6919 | 6818 | -1.68c | 23.7% | 2962 | -1.06c | 6485 | 3322-3163-0 | -272.13u | -4.2% |  |  | criteria not met (6485/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1548 | 1486 | -3.43c | 16.6% | 337 | -2.88c | 1372 | 703-669-0 | -114.82u | -8.4% |  |  | criteria not met (1372/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 120 | 120 | -0.98c | 29.2% | 112 | -0.02c | 119 | 52-67-0 | -9.16u | -7.7% |  |  | criteria not met (119/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 70 | 70 | -1.01c | 28.6% | 67 | -0.16c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 41 | 41 | -1.16c | 29.3% | 36 | -0.02c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 320 | 300 | -0.66c | 33.7% | 298 | -0.63c | 296 | 152-140-4 | -4.57u | -1.5% | 0.15c | 27s | criteria not met (296/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 164 | 154 | -0.73c | 35.1% | 154 | -0.89c | 151 | 75-73-3 | -4.54u | -3.0% | -0.16c | 28s |  |
| M gettable, price moves | 156 | 146 | -0.58c | 32.2% | 144 | -0.35c | 145 | 77-67-1 | -0.03u | -0.0% | 0.49c | 25s |  |
| M control: not gettable | 1341 | 989 | -0.82c | 35.6% | 981 | -1.2c | 952 | 463-473-16 | -67.03u | -7.0% | 1.79c | 183s |  |
| M all moves | 1661 | 1289 | -0.78c | 35.1% | 1279 | -1.07c | 1248 | 615-613-20 | -71.60u | -5.7% | 1.46c | 130s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1027 | 983 | 2.36c | 24.3% | 206 | 2.04c | 938 | 415-523-0 | +272.09u | 29.0% | 1.03c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 73 | 72 | -0.12c | 32-40-0 | -5.27u | 48, -0.35c, -8.62u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 43 | 43 | -0.4c | 22-21-0 | +2.86u | 33, -0.7c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 178 | 157 | -0.7c | 76-79-2 | -6.98u | 90, -0.74c, -11.41u | negative |
| D1 B, unders (descriptive) | 21 | 21 | 0.4c | 13-8-0 | +5.89u | 20, 0.36c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 53 | -0.38c | 29-22-2 | -3.11u | 28, -0.5c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1607 | 72 | 4.5% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1605 | 26 | 1.6% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4147 | 203 | 5.0% | -0.96c | 1.11c | 93-84-2 | +13.51u |  |
| MK prophetx fair-2c | 4121 | 66 | 1.6% | -0.49c | 2.04c | 28-28-0 | +2.47u |  |
| MK all fair-1c | 5754 | 275 | 4.9% | -0.87c | 1.25c | 130-119-2 | +16.60u | criteria not met (251/50 graded, CLV not positive) |
| MK all fair-2c | 5726 | 92 | 1.6% | -0.46c | 2.18c | 44-38-0 | +10.12u | criteria not met (82/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 629/day, projected 18871/30 days. All monitors on the key: 2144/day, projected 64316/30 days. Remaining 85128; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T21:40:58Z: 56 games (50 in 24h), quotes {'prophetx': 5372, 'novig': 591, 'kalshi': 2406, 'polymarket_us': 1680}, 3646 unmatched (77 book-games; fuzzy-matched 1), 4794 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 48 filled 3, credits used 6 left 85128, 183s
- 2026-11-07T21:31:28Z: 56 games (50 in 24h), quotes {'prophetx': 5364, 'novig': 591, 'kalshi': 2970, 'polymarket_us': 2074}, 3799 unmatched (78 book-games; fuzzy-matched 1), 5143 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 9 B 0, maker posted 64 filled 1, credits used 12 left 85149, 392s
- 2026-11-07T21:21:24Z: 55 games (47 in 24h), quotes {'prophetx': 5012, 'novig': 590, 'kalshi': 3634, 'polymarket_us': 3158}, 4128 unmatched (86 book-games; fuzzy-matched 2), 5464 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 24 B 0, maker posted 28 filled 1, credits used 8 left 85185, 232s
- 2026-11-07T21:11:26Z: 57 games (49 in 24h), quotes {'prophetx': 5224, 'novig': 619, 'kalshi': 2714, 'polymarket_us': 2144}, 3713 unmatched (81 book-games; fuzzy-matched 1), 4962 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 36 filled 0, credits used 12 left 85208, 302s
- 2026-11-07T21:01:11Z: 61 games (51 in 24h), quotes {'prophetx': 5128, 'novig': 617, 'kalshi': 2780, 'polymarket_us': 1990}, 3588 unmatched (83 book-games; fuzzy-matched 1), 4995 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 53 B 0, maker posted 27 filled 0, credits used 14 left 85235, 327s
- 2026-11-07T20:50:57Z: 62 games (52 in 24h), quotes {'prophetx': 5890, 'novig': 685, 'kalshi': 2792, 'polymarket_us': 2030}, 3560 unmatched (88 book-games; fuzzy-matched 0), 5418 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 19 B 0, maker posted 8 filled 1, credits used 12 left 85266, 301s
- 2026-11-07T20:41:20Z: 64 games (55 in 24h), quotes {'prophetx': 5994, 'novig': 686, 'kalshi': 2890, 'polymarket_us': 1992}, 3386 unmatched (88 book-games; fuzzy-matched 0), 5687 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 9 B 0, maker posted 80 filled 0, credits used 6 left 85290, 183s
- 2026-11-07T20:31:27Z: 69 games (59 in 24h), quotes {'prophetx': 5986, 'novig': 685, 'kalshi': 2720, 'polymarket_us': 2206}, 3185 unmatched (82 book-games; fuzzy-matched 60), 5924 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 31 B 0, maker posted 54 filled 0, credits used 14 left 85307, 400s
- 2026-11-07T20:20:55Z: 70 games (60 in 24h), quotes {'prophetx': 7106, 'novig': 555, 'kalshi': 2482, 'polymarket_us': 1584}, 2344 unmatched (72 book-games; fuzzy-matched 0), 6534 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 10, new A 21 B 0, maker posted 82 filled 1, credits used 12 left 85343, 301s
- 2026-11-07T20:11:19Z: 70 games (60 in 24h), quotes {'prophetx': 7104, 'novig': 564, 'kalshi': 3684, 'polymarket_us': 3014}, 3301 unmatched (91 book-games; fuzzy-matched 0), 7283 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 44 B 0, maker posted 33 filled 1, credits used 8 left 85387, 182s

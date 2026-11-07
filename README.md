# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T23:44:48Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7027 | 6924 | -1.63c | 24.0% | 3003 | -1.04c | 6542 | 3351-3191-0 | -272.17u | -4.2% |  |  | criteria not met (6542/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1572 | 1542 | -3.2c | 18.6% | 349 | -2.66c | 1395 | 711-684-0 | -123.75u | -8.9% |  |  | criteria not met (1395/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 121 | 120 | -0.98c | 29.2% | 112 | -0.02c | 119 | 52-67-0 | -9.16u | -7.7% |  |  | criteria not met (119/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 71 | 70 | -1.01c | 28.6% | 67 | -0.16c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 41 | 41 | -1.16c | 29.3% | 36 | -0.02c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 326 | 301 | -0.66c | 33.6% | 299 | -0.64c | 298 | 152-142-4 | -6.57u | -2.2% | 0.15c | 26s | criteria not met (298/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 168 | 155 | -0.73c | 34.8% | 155 | -0.9c | 152 | 75-74-3 | -5.54u | -3.6% | -0.16c | 27s |  |
| M gettable, price moves | 158 | 146 | -0.58c | 32.2% | 144 | -0.35c | 146 | 77-68-1 | -1.03u | -0.7% | 0.49c | 24s |  |
| M control: not gettable | 1361 | 1010 | -0.82c | 35.4% | 1002 | -1.2c | 961 | 468-477-16 | -66.18u | -6.9% | 1.79c | 183s |  |
| M all moves | 1687 | 1311 | -0.79c | 35.0% | 1301 | -1.07c | 1259 | 620-619-20 | -72.74u | -5.8% | 1.46c | 139s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1031 | 1028 | 2.74c | 27.1% | 221 | 2.94c | 941 | 417-524-0 | +273.78u | 29.1% | 1.03c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 74 | 72 | -0.12c | 32-40-0 | -5.27u | 48, -0.35c, -8.62u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 43 | -0.4c | 22-21-0 | +2.86u | 33, -0.7c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 184 | 159 | -0.71c | 76-81-2 | -8.98u | 91, -0.75c, -12.41u | negative |
| D1 B, unders (descriptive) | 21 | 21 | 0.4c | 13-8-0 | +5.89u | 20, 0.36c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 53 | -0.38c | 29-22-2 | -3.11u | 28, -0.5c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1634 | 72 | 4.4% | -0.62c | 1.59c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1632 | 26 | 1.6% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4316 | 205 | 4.8% | -0.95c | 1.1c | 93-84-2 | +13.51u |  |
| MK prophetx fair-2c | 4290 | 66 | 1.6% | -0.49c | 2.04c | 28-28-0 | +2.47u |  |
| MK all fair-1c | 5950 | 277 | 4.7% | -0.86c | 1.25c | 130-119-2 | +16.60u | criteria not met (251/50 graded, CLV not positive) |
| MK all fair-2c | 5922 | 92 | 1.6% | -0.46c | 2.18c | 44-38-0 | +10.12u | criteria not met (82/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 636/day, projected 19080/30 days. All monitors on the key: 2161/day, projected 64825/30 days. Remaining 84760; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T23:40:54Z: 55 games (47 in 24h), quotes {'prophetx': 4246, 'novig': 597, 'kalshi': 2322, 'polymarket_us': 1824}, 1982 unmatched (49 book-games; fuzzy-matched 1), 5069 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 9 B 0, maker posted 48 filled 0, credits used 6 left 84760, 234s
- 2026-11-07T23:31:26Z: 55 games (47 in 24h), quotes {'prophetx': 4246, 'novig': 602, 'kalshi': 2654, 'polymarket_us': 2144}, 2212 unmatched (51 book-games; fuzzy-matched 1), 5276 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 7 B 0, maker posted 47 filled 0, credits used 12 left 84777, 331s
- 2026-11-07T23:21:21Z: 55 games (48 in 24h), quotes {'prophetx': 4246, 'novig': 604, 'kalshi': 3262, 'polymarket_us': 2746}, 2294 unmatched (56 book-games; fuzzy-matched 2), 5831 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 10 B 0, maker posted 4 filled 0, credits used 14 left 84808, 353s
- 2026-11-07T23:11:26Z: 55 games (48 in 24h), quotes {'prophetx': 4358, 'novig': 620, 'kalshi': 2224, 'polymarket_us': 1478}, 2131 unmatched (55 book-games; fuzzy-matched 0), 4901 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 6 left 84852, 184s
- 2026-11-07T23:05:35Z: 55 games (47 in 24h), quotes {'prophetx': 3934, 'novig': 618, 'kalshi': 2276, 'polymarket_us': 1794}, 2257 unmatched (56 book-games; fuzzy-matched 0), 4624 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 28 filled 0, credits used 6 left 84858, 262s
- 2026-11-07T23:01:00Z: 55 games (47 in 24h), quotes {'prophetx': 4242, 'novig': 622, 'kalshi': 2230, 'polymarket_us': 1496}, 2166 unmatched (55 book-games; fuzzy-matched 0), 4839 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 14 B 0, maker posted 39 filled 0, credits used 8 left 84879, 186s
- 2026-11-07T22:51:23Z: 54 games (47 in 24h), quotes {'prophetx': 4622, 'novig': 608, 'kalshi': 2270, 'polymarket_us': 1522}, 2746 unmatched (62 book-games; fuzzy-matched 5), 4866 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 5 B 1, maker posted 42 filled 2, credits used 12 left 84893, 329s
- 2026-11-07T22:41:24Z: 54 games (47 in 24h), quotes {'prophetx': 4622, 'novig': 602, 'kalshi': 2588, 'polymarket_us': 2150}, 2893 unmatched (64 book-games; fuzzy-matched 5), 5169 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 8 filled 0, credits used 6 left 84941, 209s
- 2026-11-07T22:32:48Z: 54 games (47 in 24h), quotes {'prophetx': 4614, 'novig': 604, 'kalshi': 3584, 'polymarket_us': 3068}, 3092 unmatched (66 book-games; fuzzy-matched 1), 5982 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 0, maker posted 48 filled 0, credits used 8 left 84958, 247s
- 2026-11-07T22:27:59Z: 54 games (47 in 24h), quotes {'prophetx': 4614, 'novig': 604, 'kalshi': 3620, 'polymarket_us': 3058}, 3101 unmatched (66 book-games; fuzzy-matched 1), 6007 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 24 filled 0, credits used 6 left 84966, 208s

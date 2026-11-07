# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T22:56:51Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6985 | 6881 | -1.65c | 23.9% | 2986 | -1.05c | 6503 | 3332-3171-0 | -273.43u | -4.2% |  |  | criteria not met (6503/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1563 | 1520 | -3.27c | 17.9% | 344 | -2.72c | 1381 | 707-674-0 | -117.10u | -8.5% |  |  | criteria not met (1381/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 121 | 120 | -0.98c | 29.2% | 112 | -0.02c | 119 | 52-67-0 | -9.16u | -7.7% |  |  | criteria not met (119/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 71 | 70 | -1.01c | 28.6% | 67 | -0.16c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 41 | 41 | -1.16c | 29.3% | 36 | -0.02c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 322 | 301 | -0.66c | 33.6% | 299 | -0.64c | 296 | 152-140-4 | -4.57u | -1.5% | 0.15c | 27s | criteria not met (296/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 165 | 155 | -0.73c | 34.8% | 155 | -0.9c | 151 | 75-73-3 | -4.54u | -3.0% | -0.16c | 28s |  |
| M gettable, price moves | 157 | 146 | -0.58c | 32.2% | 144 | -0.35c | 145 | 77-67-1 | -0.03u | -0.0% | 0.49c | 24s |  |
| M control: not gettable | 1355 | 1006 | -0.83c | 35.3% | 998 | -1.2c | 956 | 464-476-16 | -69.04u | -7.2% | 1.79c | 183s |  |
| M all moves | 1677 | 1307 | -0.79c | 34.9% | 1297 | -1.07c | 1252 | 616-616-20 | -73.61u | -5.9% | 1.46c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1030 | 997 | 2.44c | 25.0% | 209 | 2.29c | 940 | 416-524-0 | +272.55u | 29.0% | 1.03c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 74 | 72 | -0.12c | 32-40-0 | -5.27u | 48, -0.35c, -8.62u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 43 | -0.4c | 22-21-0 | +2.86u | 33, -0.7c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 180 | 157 | -0.71c | 76-79-2 | -6.98u | 90, -0.75c, -11.41u | negative |
| D1 B, unders (descriptive) | 21 | 21 | 0.4c | 13-8-0 | +5.89u | 20, 0.36c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 56 | 53 | -0.38c | 29-22-2 | -3.11u | 28, -0.5c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1621 | 72 | 4.5% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1619 | 26 | 1.6% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4246 | 205 | 4.9% | -0.96c | 1.1c | 93-84-2 | +13.51u |  |
| MK prophetx fair-2c | 4220 | 66 | 1.6% | -0.49c | 2.04c | 28-28-0 | +2.47u |  |
| MK all fair-1c | 5867 | 277 | 4.8% | -0.87c | 1.25c | 130-119-2 | +16.60u | criteria not met (251/50 graded, CLV not positive) |
| MK all fair-2c | 5839 | 92 | 1.6% | -0.46c | 2.18c | 44-38-0 | +10.12u | criteria not met (82/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 633/day, projected 18999/30 days. All monitors on the key: 2156/day, projected 64667/30 days. Remaining 84893; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T22:51:23Z: 54 games (47 in 24h), quotes {'prophetx': 4622, 'novig': 608, 'kalshi': 2270, 'polymarket_us': 1522}, 2746 unmatched (62 book-games; fuzzy-matched 5), 4866 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 5 B 1, maker posted 42 filled 2, credits used 12 left 84893, 329s
- 2026-11-07T22:41:24Z: 54 games (47 in 24h), quotes {'prophetx': 4622, 'novig': 602, 'kalshi': 2588, 'polymarket_us': 2150}, 2893 unmatched (64 book-games; fuzzy-matched 5), 5169 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 2 B 0, maker posted 8 filled 0, credits used 6 left 84941, 209s
- 2026-11-07T22:32:48Z: 54 games (47 in 24h), quotes {'prophetx': 4614, 'novig': 604, 'kalshi': 3584, 'polymarket_us': 3068}, 3092 unmatched (66 book-games; fuzzy-matched 1), 5982 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 0, maker posted 48 filled 0, credits used 8 left 84958, 247s
- 2026-11-07T22:27:59Z: 54 games (47 in 24h), quotes {'prophetx': 4614, 'novig': 604, 'kalshi': 3620, 'polymarket_us': 3058}, 3101 unmatched (66 book-games; fuzzy-matched 1), 6007 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 24 filled 0, credits used 6 left 84966, 208s
- 2026-11-07T22:21:26Z: 54 games (47 in 24h), quotes {'prophetx': 4614, 'novig': 598, 'kalshi': 1664, 'polymarket_us': 1768}, 2753 unmatched (60 book-games; fuzzy-matched 0), 4804 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 8 B 0, maker posted 19 filled 0, credits used 12 left 84986, 302s
- 2026-11-07T22:11:26Z: 55 games (48 in 24h), quotes {'prophetx': 4614, 'novig': 610, 'kalshi': 2278, 'polymarket_us': 1504}, 2914 unmatched (66 book-games; fuzzy-matched 0), 4785 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 8 filled 0, credits used 8 left 85031, 185s
- 2026-11-07T22:01:31Z: 56 games (50 in 24h), quotes {'prophetx': 4614, 'novig': 618, 'kalshi': 3628, 'polymarket_us': 3052}, 3034 unmatched (67 book-games; fuzzy-matched 2), 6021 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 28 B 0, maker posted 28 filled 0, credits used 12 left 85050, 329s
- 2026-11-07T21:51:26Z: 56 games (50 in 24h), quotes {'prophetx': 5380, 'novig': 592, 'kalshi': 2278, 'polymarket_us': 1566}, 3432 unmatched (73 book-games; fuzzy-matched 2), 4786 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 6 B 0, maker posted 49 filled 0, credits used 14 left 85075, 302s
- 2026-11-07T21:40:58Z: 56 games (50 in 24h), quotes {'prophetx': 5372, 'novig': 591, 'kalshi': 2406, 'polymarket_us': 1680}, 3646 unmatched (77 book-games; fuzzy-matched 1), 4794 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 8 B 0, maker posted 48 filled 3, credits used 6 left 85128, 183s
- 2026-11-07T21:31:28Z: 56 games (50 in 24h), quotes {'prophetx': 5364, 'novig': 591, 'kalshi': 2970, 'polymarket_us': 2074}, 3799 unmatched (78 book-games; fuzzy-matched 1), 5143 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 9 B 0, maker posted 64 filled 1, credits used 12 left 85149, 392s

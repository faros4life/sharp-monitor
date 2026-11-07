# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T01:54:46Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6359 | 6237 | -1.72c | 23.8% | 2707 | -1.09c | 5803 | 2973-2830-0 | -238.73u | -4.1% |  |  | criteria not met (5803/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1354 | 1329 | -3.65c | 16.4% | 296 | -3.03c | 1242 | 640-602-0 | -91.87u | -7.4% |  |  | criteria not met (1242/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 118 | -0.95c | 29.7% | 110 | -0.08c | 104 | 42-62-0 | -15.00u | -14.4% |  |  | criteria not met (104/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 69 | -0.98c | 29.0% | 66 | -0.13c | 60 | 26-34-0 | -4.43u | -7.4% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 35 | 11-24-0 | -11.96u | -34.2% |  |  |  |
| M move-watch: gettable (sightings) | 294 | 276 | -0.69c | 32.2% | 273 | -0.69c | 257 | 133-121-3 | -3.14u | -1.2% | 0.1c | 26s | criteria not met (257/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 149 | 140 | -0.78c | 33.6% | 139 | -0.96c | 129 | 65-62-2 | -2.65u | -2.1% | -0.23c | 28s |  |
| M gettable, price moves | 145 | 136 | -0.61c | 30.9% | 134 | -0.41c | 128 | 68-59-1 | -0.48u | -0.4% | 0.45c | 24s |  |
| M control: not gettable | 1121 | 857 | -0.92c | 34.3% | 846 | -1.28c | 801 | 394-393-14 | -45.42u | -5.7% | 1.76c | 164s |  |
| M all moves | 1415 | 1133 | -0.87c | 33.8% | 1119 | -1.14c | 1058 | 527-514-17 | -48.56u | -4.6% | 1.41c | 106s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 939 | 929 | 2.26c | 23.3% | 194 | 1.92c | 917 | 404-513-0 | +261.89u | 28.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 59 | -0.24c | 23-36-0 | -11.12u | 41, -0.54c, -7.87u | negative |
| J2 B, NBA | 50 | 40 | -0.2c | 15-25-0 | -8.85u | 25, -0.55c, -2.29u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 35 | -0.36c | 16-19-0 | -1.78u | 27, -0.66c, +1.98u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 154 | 121 | -0.8c | 58-62-1 | -7.03u | 70, -0.89c, -6.91u | negative |
| D1 B, unders (descriptive) | 20 | 14 | 0.53c | 8-6-0 | +2.56u | 14, 0.5c, +2.56u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 11 | -0.87c | 2-9-0 | -6.66u | 9, -1.1c, -4.66u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 7 | 0.44c | 3-4-0 | +0.46u | 6, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 54 | 50 | -0.46c | 28-20-2 | -1.64u | 25, -0.67c, -1.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1550 | 72 | 4.7% | -0.62c | 1.6c | 29-30-0 | -0.37u |  |
| MK novig fair-2c | 1547 | 26 | 1.7% | -0.37c | 2.52c | 14-8-0 | +7.49u |  |
| MK prophetx fair-1c | 3243 | 164 | 5.1% | -0.93c | 1.1c | 82-64-2 | +22.05u |  |
| MK prophetx fair-2c | 3220 | 49 | 1.5% | -0.56c | 2.04c | 20-22-0 | -0.22u |  |
| MK all fair-1c | 4793 | 236 | 5.0% | -0.83c | 1.27c | 111-94-2 | +21.68u | criteria not met (207/50 graded, CLV not positive) |
| MK all fair-2c | 4767 | 75 | 1.6% | -0.49c | 2.2c | 34-30-0 | +7.27u | criteria not met (64/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 624/day, projected 18730/30 days. All monitors on the key: 2131/day, projected 63939/30 days. Remaining 87028; guard holds 68000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T01:51:14Z: 70 games (61 in 24h), quotes {'prophetx': 2616, 'novig': 704, 'kalshi': 3730, 'polymarket_us': 3174}, 3951 unmatched (95 book-games; fuzzy-matched 1), 3699 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 87028, 212s
- 2026-11-07T01:41:15Z: 70 games (61 in 24h), quotes {'prophetx': 11596, 'novig': 699, 'kalshi': 3664, 'polymarket_us': 3122}, 5845 unmatched (141 book-games; fuzzy-matched 1), 7052 side/lines, polls [NCAAF:fast,NBA:fast,NHL:slow; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, maker posted 12 filled 1, credits used 10 left 87041, 337s
- 2026-11-07T01:31:18Z: 70 games (60 in 24h), quotes {'prophetx': 5754, 'novig': 705, 'kalshi': 2718, 'polymarket_us': 1982}, 4284 unmatched (101 book-games; fuzzy-matched 1), 3025 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 87066, 199s
- 2026-11-07T01:26:12Z: 70 games (60 in 24h), quotes {'prophetx': 6982, 'novig': 703, 'kalshi': 2626, 'polymarket_us': 2094}, 4491 unmatched (107 book-games; fuzzy-matched 1), 3509 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, maker posted 1 filled 0, credits used 4 left 87086, 224s
- 2026-11-07T01:20:47Z: 70 games (60 in 24h), quotes {'prophetx': 11588, 'novig': 697, 'kalshi': 3710, 'polymarket_us': 2526}, 5616 unmatched (140 book-games; fuzzy-matched 1), 6858 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 9 B 0, maker posted 1 filled 0, credits used 4 left 87099, 213s
- 2026-11-07T01:15:40Z: 70 games (60 in 24h), quotes {'prophetx': 7784, 'novig': 702, 'kalshi': 2970, 'polymarket_us': 2102}, 4815 unmatched (116 book-games; fuzzy-matched 1), 4256 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 87112, 219s
- 2026-11-07T01:11:08Z: 72 games (62 in 24h), quotes {'prophetx': 876, 'novig': 684, 'kalshi': 830, 'polymarket_us': 1244}, 1774 unmatched (33 book-games; fuzzy-matched 0), 1053 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 11 filled 0, credits used 6 left 87116, 192s
- 2026-11-07T01:01:30Z: 74 games (63 in 24h), quotes {'prophetx': 5146, 'novig': 722, 'kalshi': 2252, 'polymarket_us': 1490}, 2923 unmatched (68 book-games; fuzzy-matched 2), 3142 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 17 B 0, maker posted 17 filled 1, credits used 12 left 87131, 302s
- 2026-11-07T00:51:26Z: 74 games (62 in 24h), quotes {'prophetx': 2156, 'novig': 713, 'kalshi': 2398, 'polymarket_us': 1794}, 1559 unmatched (41 book-games; fuzzy-matched 1), 3257 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 11 B 0, maker posted 35 filled 1, credits used 12 left 87162, 376s
- 2026-11-07T00:40:50Z: 74 games (61 in 24h), quotes {'prophetx': 3688, 'novig': 713, 'kalshi': 2720, 'polymarket_us': 2002}, 2473 unmatched (60 book-games; fuzzy-matched 1), 3564 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 9 B 1, maker posted 0 filled 1, credits used 6 left 87190, 234s

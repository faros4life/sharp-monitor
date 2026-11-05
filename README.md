# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T00:06:10Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5350 | 4997 | -1.86c | 23.6% | 2059 | -1.13c | 4856 | 2467-2389-0 | -226.27u | -4.7% |  |  | criteria not met (4856/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1214 | 1147 | -3.82c | 16.2% | 252 | -3.0c | 1132 | 578-554-0 | -85.70u | -7.6% |  |  | criteria not met (1132/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 95 | 85 | -0.84c | 31.8% | 81 | -0.08c | 82 | 32-50-0 | -13.85u | -16.9% |  |  | criteria not met (82/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 7 | 6 | 0.73c | 50.0% | 6 | 1.64c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 55 | 52 | -0.7c | 30.8% | 50 | -0.16c | 50 | 21-29-0 | -4.81u | -9.6% |  |  |  |
| B ref age 5m+ | 33 | 27 | -1.47c | 29.6% | 25 | -0.36c | 26 | 8-18-0 | -9.33u | -35.9% |  |  |  |
| M move-watch: gettable (sightings) | 230 | 210 | -0.67c | 31.9% | 208 | -0.65c | 204 | 106-95-3 | -0.70u | -0.3% | 0.11c | 27s | criteria not met (204/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 118 | 104 | -0.62c | 34.6% | 103 | -0.9c | 100 | 52-46-2 | +1.51u | 1.5% | -0.15c | 78s |  |
| M gettable, price moves | 112 | 106 | -0.72c | 29.2% | 105 | -0.41c | 104 | 54-49-1 | -2.21u | -2.1% | 0.37c | 22s |  |
| M control: not gettable | 870 | 639 | -0.91c | 34.1% | 630 | -1.29c | 643 | 330-299-14 | -7.51u | -1.2% | 1.77c | 100s |  |
| M all moves | 1100 | 849 | -0.85c | 33.6% | 838 | -1.13c | 847 | 436-394-17 | -8.21u | -1.0% | 1.42c | 33s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 911 | 891 | 2.46c | 23.6% | 186 | 2.03c | 885 | 397-488-0 | +279.27u | 31.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 53 | 41 | -0.23c | 15-26-0 | -9.83u | 28, -0.5c, -5.16u | not enough yet |
| J2 B, NBA | 37 | 28 | -0.05c | 10-18-0 | -7.29u | 16, -0.26c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 31 | 26 | -0.36c | 11-15-0 | -3.13u | 19, -0.7c, +1.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 103 | 80 | -0.73c | 38-41-1 | -4.96u | 49, -0.89c, -3.31u | negative |
| D1 B, unders (descriptive) | 10 | 8 | 0.76c | 4-4-0 | +0.27u | 8, 0.76c, +0.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 8 | -1.14c | 0-8-0 | -8.00u | 6, -1.69c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 4 | 3 | 0.11c | 1-2-0 | +0.33u | 3, 0.11c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 41 | 38 | -0.44c | 21-15-2 | -1.26u | 19, -0.7c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1037 | 48 | 4.7% | -0.44c | 1.61c | 19-25-0 | -5.15u |  |
| MK novig fair-2c | 1039 | 18 | 1.8% | -0.45c | 2.53c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2676 | 129 | 4.9% | -0.88c | 1.1c | 63-55-2 | +11.02u |  |
| MK prophetx fair-2c | 2655 | 37 | 1.4% | -0.59c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3713 | 177 | 4.9% | -0.77c | 1.25c | 82-80-2 | +5.87u | criteria not met (164/50 graded, CLV not positive) |
| MK all fair-2c | 3694 | 55 | 1.5% | -0.55c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 79.

## Odds API credits (100K/month plan)

Study: 610/day, projected 18306/30 days. All monitors on the key: 2085/day, projected 62540/30 days. Remaining 91835; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T00:01:08Z: 35 games (21 in 24h), quotes {'prophetx': 1794, 'novig': 724, 'kalshi': 1780, 'polymarket_us': 1662}, 28 unmatched (1 book-games; fuzzy-matched 0), 3522 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 17 filled 0, credits used 12 left 91835, 302s
- 2026-11-04T23:50:56Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 718, 'kalshi': 1772, 'polymarket_us': 1862}, 28 unmatched (1 book-games; fuzzy-matched 62), 3802 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 5 B 0, maker posted 9 filled 0, credits used 14 left 91865, 350s
- 2026-11-04T23:40:38Z: 35 games (21 in 24h), quotes {'prophetx': 1870, 'novig': 716, 'kalshi': 1778, 'polymarket_us': 1782}, 28 unmatched (1 book-games; fuzzy-matched 4), 3776 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 7 B 0, maker posted 41 filled 1, credits used 12 left 91892, 301s
- 2026-11-04T23:30:57Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 728, 'kalshi': 1770, 'polymarket_us': 2310}, 28 unmatched (1 book-games; fuzzy-matched 2), 4044 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 13 filled 0, credits used 6 left 91932, 184s
- 2026-11-04T23:20:59Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 716, 'kalshi': 1762, 'polymarket_us': 1574}, 28 unmatched (1 book-games; fuzzy-matched 2), 3654 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 2 B 1, maker posted 54 filled 1, credits used 14 left 91953, 359s
- 2026-11-04T23:10:49Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 720, 'kalshi': 1760, 'polymarket_us': 1680}, 28 unmatched (1 book-games; fuzzy-matched 4), 3719 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 6 B 0, maker posted 35 filled 2, credits used 12 left 91988, 326s
- 2026-11-04T23:00:44Z: 35 games (21 in 24h), quotes {'prophetx': 1912, 'novig': 720, 'kalshi': 1758, 'polymarket_us': 1758}, 28 unmatched (1 book-games; fuzzy-matched 2), 3790 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 8 filled 0, credits used 6 left 92024, 183s
- 2026-11-04T22:51:07Z: 35 games (21 in 24h), quotes {'prophetx': 1912, 'novig': 720, 'kalshi': 1766, 'polymarket_us': 1688}, 28 unmatched (1 book-games; fuzzy-matched 4), 3745 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 9 filled 1, credits used 14 left 92041, 327s
- 2026-11-04T22:40:52Z: 35 games (21 in 24h), quotes {'prophetx': 1824, 'novig': 720, 'kalshi': 1764, 'polymarket_us': 1906}, 28 unmatched (1 book-games; fuzzy-matched 2), 3816 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 8 filled 0, credits used 6 left 92077, 182s
- 2026-11-04T22:30:54Z: 35 games (21 in 24h), quotes {'prophetx': 1904, 'novig': 718, 'kalshi': 1770, 'polymarket_us': 1746}, 28 unmatched (1 book-games; fuzzy-matched 2), 3809 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 33 filled 0, credits used 14 left 92096, 302s

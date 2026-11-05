# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T00:45:27Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5408 | 5233 | -1.83c | 23.7% | 2174 | -1.12c | 4856 | 2467-2389-0 | -226.27u | -4.7% |  |  | criteria not met (4856/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1219 | 1186 | -3.76c | 16.5% | 259 | -2.95c | 1132 | 578-554-0 | -85.70u | -7.6% |  |  | criteria not met (1132/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 97 | 95 | -0.74c | 32.6% | 91 | 0.01c | 82 | 32-50-0 | -13.85u | -16.9% |  |  | criteria not met (82/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 7 | 0.55c | 42.9% | 7 | 1.44c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 56 | 55 | -0.68c | 30.9% | 53 | -0.1c | 50 | 21-29-0 | -4.81u | -9.6% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 26 | 8-18-0 | -9.33u | -35.9% |  |  |  |
| M move-watch: gettable (sightings) | 234 | 220 | -0.67c | 31.8% | 218 | -0.65c | 204 | 106-95-3 | -0.70u | -0.3% | 0.1c | 26s | criteria not met (204/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 120 | 110 | -0.67c | 34.5% | 109 | -0.94c | 100 | 52-46-2 | +1.51u | 1.5% | -0.22c | 55s |  |
| M gettable, price moves | 114 | 110 | -0.67c | 29.1% | 109 | -0.37c | 104 | 54-49-1 | -2.21u | -2.1% | 0.42c | 22s |  |
| M control: not gettable | 881 | 665 | -0.91c | 34.3% | 659 | -1.32c | 643 | 330-299-14 | -7.51u | -1.2% | 1.78c | 44s |  |
| M all moves | 1115 | 885 | -0.85c | 33.7% | 877 | -1.15c | 847 | 436-394-17 | -8.21u | -1.0% | 1.43c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 914 | 905 | 2.38c | 23.3% | 189 | 1.98c | 885 | 397-488-0 | +279.27u | 31.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 41 | -0.08c | 15-26-0 | -9.83u | 28, -0.49c, -5.16u | not enough yet |
| J2 B, NBA | 38 | 28 | 0.11c | 10-18-0 | -7.29u | 16, -0.35c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 26 | -0.31c | 11-15-0 | -3.13u | 19, -0.6c, +1.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 105 | 80 | -0.73c | 38-41-1 | -4.96u | 49, -0.87c, -3.31u | negative |
| D1 B, unders (descriptive) | 11 | 8 | 0.7c | 4-4-0 | +0.27u | 8, 0.7c, +0.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 8 | -1.1c | 0-8-0 | -8.00u | 6, -1.51c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 5 | 3 | 0.45c | 1-2-0 | +0.33u | 3, 0.44c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 43 | 38 | -0.46c | 21-15-2 | -1.26u | 19, -0.76c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1068 | 49 | 4.7% | -0.46c | 1.61c | 19-25-0 | -5.15u |  |
| MK novig fair-2c | 1070 | 18 | 1.7% | -0.45c | 2.52c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2699 | 131 | 4.9% | -0.87c | 1.11c | 63-55-2 | +11.02u |  |
| MK prophetx fair-2c | 2682 | 38 | 1.4% | -0.59c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3767 | 180 | 4.8% | -0.76c | 1.25c | 82-80-2 | +5.87u | criteria not met (164/50 graded, CLV not positive) |
| MK all fair-2c | 3752 | 56 | 1.5% | -0.55c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 80.

## Odds API credits (100K/month plan)

Study: 612/day, projected 18368/30 days. All monitors on the key: 2090/day, projected 62706/30 days. Remaining 91732; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T00:40:55Z: 27 games (23 in 24h), quotes {'prophetx': 1366, 'novig': 721, 'kalshi': 1726, 'polymarket_us': 1596}, 472 unmatched (10 book-games; fuzzy-matched 0), 2790 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 5, new A 17 B 0, maker posted 23 filled 3, credits used 4 left 91732, 272s
- 2026-11-05T00:31:00Z: 31 games (27 in 24h), quotes {'prophetx': 1322, 'novig': 724, 'kalshi': 1742, 'polymarket_us': 1596}, 302 unmatched (6 book-games; fuzzy-matched 0), 3025 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 31 filled 0, credits used 10 left 91751, 301s
- 2026-11-05T00:20:57Z: 31 games (26 in 24h), quotes {'prophetx': 1794, 'novig': 718, 'kalshi': 1742, 'polymarket_us': 2042}, 302 unmatched (5 book-games; fuzzy-matched 0), 3454 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 12 B 1, maker posted 34 filled 0, credits used 14 left 91782, 392s
- 2026-11-05T00:10:48Z: 33 games (28 in 24h), quotes {'prophetx': 1794, 'novig': 718, 'kalshi': 1764, 'polymarket_us': 1726}, 168 unmatched (3 book-games; fuzzy-matched 0), 3462 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 18 B 1, maker posted 24 filled 1, credits used 6 left 91818, 213s
- 2026-11-05T00:01:08Z: 35 games (21 in 24h), quotes {'prophetx': 1794, 'novig': 724, 'kalshi': 1780, 'polymarket_us': 1662}, 28 unmatched (1 book-games; fuzzy-matched 0), 3522 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 17 filled 0, credits used 12 left 91835, 302s
- 2026-11-04T23:50:56Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 718, 'kalshi': 1772, 'polymarket_us': 1862}, 28 unmatched (1 book-games; fuzzy-matched 62), 3802 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 5 B 0, maker posted 9 filled 0, credits used 14 left 91865, 350s
- 2026-11-04T23:40:38Z: 35 games (21 in 24h), quotes {'prophetx': 1870, 'novig': 716, 'kalshi': 1778, 'polymarket_us': 1782}, 28 unmatched (1 book-games; fuzzy-matched 4), 3776 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 7 B 0, maker posted 41 filled 1, credits used 12 left 91892, 301s
- 2026-11-04T23:30:57Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 728, 'kalshi': 1770, 'polymarket_us': 2310}, 28 unmatched (1 book-games; fuzzy-matched 2), 4044 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 13 filled 0, credits used 6 left 91932, 184s
- 2026-11-04T23:20:59Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 716, 'kalshi': 1762, 'polymarket_us': 1574}, 28 unmatched (1 book-games; fuzzy-matched 2), 3654 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 2 B 1, maker posted 54 filled 1, credits used 14 left 91953, 359s
- 2026-11-04T23:10:49Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 720, 'kalshi': 1760, 'polymarket_us': 1680}, 28 unmatched (1 book-games; fuzzy-matched 4), 3719 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 6 B 0, maker posted 35 filled 2, credits used 12 left 91988, 326s

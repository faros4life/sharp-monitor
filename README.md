# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T01:26:29Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5464 | 5309 | -1.83c | 23.6% | 2230 | -1.13c | 4856 | 2467-2389-0 | -226.27u | -4.7% |  |  | criteria not met (4856/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1221 | 1204 | -3.78c | 16.4% | 267 | -3.02c | 1132 | 578-554-0 | -85.70u | -7.6% |  |  | criteria not met (1132/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 97 | 96 | -0.76c | 32.3% | 92 | -0.01c | 82 | 32-50-0 | -13.85u | -16.9% |  |  | criteria not met (82/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 56 | 55 | -0.68c | 30.9% | 53 | -0.1c | 50 | 21-29-0 | -4.81u | -9.6% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 26 | 8-18-0 | -9.33u | -35.9% |  |  |  |
| M move-watch: gettable (sightings) | 234 | 224 | -0.69c | 31.7% | 222 | -0.68c | 204 | 106-95-3 | -0.70u | -0.3% | 0.08c | 26s | criteria not met (204/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 120 | 113 | -0.72c | 34.5% | 112 | -0.98c | 100 | 52-46-2 | +1.51u | 1.5% | -0.26c | 55s |  |
| M gettable, price moves | 114 | 111 | -0.67c | 28.8% | 110 | -0.37c | 104 | 54-49-1 | -2.21u | -2.1% | 0.42c | 22s |  |
| M control: not gettable | 885 | 685 | -0.91c | 34.5% | 679 | -1.31c | 643 | 330-299-14 | -7.51u | -1.2% | 1.77c | 44s |  |
| M all moves | 1119 | 909 | -0.85c | 33.8% | 901 | -1.16c | 847 | 436-394-17 | -8.21u | -1.0% | 1.42c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 911 | 2.34c | 23.2% | 189 | 1.98c | 885 | 397-488-0 | +279.27u | 31.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 41 | -0.12c | 15-26-0 | -9.83u | 28, -0.52c, -5.16u | not enough yet |
| J2 B, NBA | 38 | 28 | 0.05c | 10-18-0 | -7.29u | 16, -0.42c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 26 | -0.35c | 11-15-0 | -3.13u | 19, -0.65c, +1.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 105 | 80 | -0.78c | 38-41-1 | -4.96u | 49, -0.95c, -3.31u | negative |
| D1 B, unders (descriptive) | 11 | 8 | 0.7c | 4-4-0 | +0.27u | 8, 0.7c, +0.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 8 | -1.1c | 0-8-0 | -8.00u | 6, -1.51c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 5 | 3 | 0.45c | 1-2-0 | +0.33u | 3, 0.44c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 43 | 38 | -0.46c | 21-15-2 | -1.26u | 19, -0.76c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1087 | 50 | 4.7% | -0.47c | 1.6c | 19-25-0 | -5.15u |  |
| MK novig fair-2c | 1088 | 18 | 1.7% | -0.45c | 2.52c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2719 | 133 | 4.9% | -0.88c | 1.11c | 63-55-2 | +11.02u |  |
| MK prophetx fair-2c | 2700 | 38 | 1.4% | -0.6c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3806 | 183 | 4.9% | -0.77c | 1.25c | 82-80-2 | +5.87u | criteria not met (164/50 graded, CLV not positive) |
| MK all fair-2c | 3788 | 56 | 1.5% | -0.55c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 80.

## Odds API credits (100K/month plan)

Study: 615/day, projected 18437/30 days. All monitors on the key: 2094/day, projected 62832/30 days. Remaining 91639; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T01:21:06Z: 22 games (21 in 24h), quotes {'prophetx': 1272, 'novig': 725, 'kalshi': 1628, 'polymarket_us': 1514}, 748 unmatched (15 book-games; fuzzy-matched 0), 2371 side/lines, polls [NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 10 B 0, maker posted 4 filled 0, credits used 10 left 91639, 323s
- 2026-11-05T01:11:01Z: 24 games (22 in 24h), quotes {'prophetx': 1152, 'novig': 717, 'kalshi': 1640, 'polymarket_us': 1374}, 614 unmatched (13 book-games; fuzzy-matched 0), 2354 side/lines, polls [NFL:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 2, new A 12 B 0, maker posted 26 filled 2, credits used 10 left 91662, 301s
- 2026-11-05T01:00:43Z: 25 games (22 in 24h), quotes {'prophetx': 1242, 'novig': 721, 'kalshi': 1682, 'polymarket_us': 1374}, 582 unmatched (12 book-games; fuzzy-matched 0), 2525 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 28 B 0, maker posted 25 filled 1, credits used 6 left 91692, 184s
- 2026-11-05T00:50:55Z: 25 games (21 in 24h), quotes {'prophetx': 1402, 'novig': 714, 'kalshi': 1706, 'polymarket_us': 1596}, 600 unmatched (12 book-games; fuzzy-matched 0), 2666 side/lines, polls [NFL:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 7 B 0, maker posted 20 filled 0, credits used 10 left 91711, 308s
- 2026-11-05T00:40:55Z: 27 games (23 in 24h), quotes {'prophetx': 1366, 'novig': 721, 'kalshi': 1726, 'polymarket_us': 1596}, 472 unmatched (10 book-games; fuzzy-matched 0), 2790 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 5, new A 17 B 0, maker posted 23 filled 3, credits used 4 left 91732, 272s
- 2026-11-05T00:31:00Z: 31 games (27 in 24h), quotes {'prophetx': 1322, 'novig': 724, 'kalshi': 1742, 'polymarket_us': 1596}, 302 unmatched (6 book-games; fuzzy-matched 0), 3025 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 31 filled 0, credits used 10 left 91751, 301s
- 2026-11-05T00:20:57Z: 31 games (26 in 24h), quotes {'prophetx': 1794, 'novig': 718, 'kalshi': 1742, 'polymarket_us': 2042}, 302 unmatched (5 book-games; fuzzy-matched 0), 3454 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 12 B 1, maker posted 34 filled 0, credits used 14 left 91782, 392s
- 2026-11-05T00:10:48Z: 33 games (28 in 24h), quotes {'prophetx': 1794, 'novig': 718, 'kalshi': 1764, 'polymarket_us': 1726}, 168 unmatched (3 book-games; fuzzy-matched 0), 3462 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 18 B 1, maker posted 24 filled 1, credits used 6 left 91818, 213s
- 2026-11-05T00:01:08Z: 35 games (21 in 24h), quotes {'prophetx': 1794, 'novig': 724, 'kalshi': 1780, 'polymarket_us': 1662}, 28 unmatched (1 book-games; fuzzy-matched 0), 3522 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 17 filled 0, credits used 12 left 91835, 302s
- 2026-11-04T23:50:56Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 718, 'kalshi': 1772, 'polymarket_us': 1862}, 28 unmatched (1 book-games; fuzzy-matched 62), 3802 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 5 B 0, maker posted 9 filled 0, credits used 14 left 91865, 350s

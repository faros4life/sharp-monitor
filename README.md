# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-04T20:44:33Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5276 | 4856 | -1.89c | 23.4% | 2008 | -1.14c | 4856 | 2467-2389-0 | -226.27u | -4.7% |  |  | criteria not met (4856/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1200 | 1132 | -3.84c | 16.1% | 251 | -3.01c | 1132 | 578-554-0 | -85.70u | -7.6% |  |  | criteria not met (1132/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 94 | 82 | -0.84c | 31.7% | 78 | -0.05c | 82 | 32-50-0 | -13.85u | -16.9% |  |  | criteria not met (82/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 7 | 6 | 0.73c | 50.0% | 6 | 1.64c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 54 | 50 | -0.67c | 30.0% | 48 | -0.1c | 50 | 21-29-0 | -4.81u | -9.6% |  |  |  |
| B ref age 5m+ | 33 | 26 | -1.52c | 30.8% | 24 | -0.37c | 26 | 8-18-0 | -9.33u | -35.9% |  |  |  |
| M move-watch: gettable (sightings) | 221 | 204 | -0.68c | 32.4% | 201 | -0.67c | 204 | 106-95-3 | -0.70u | -0.3% | 0.11c | 28s | criteria not met (204/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 114 | 100 | -0.59c | 36.0% | 99 | -0.88c | 100 | 52-46-2 | +1.51u | 1.5% | -0.11c | 97s |  |
| M gettable, price moves | 107 | 104 | -0.77c | 28.8% | 102 | -0.46c | 104 | 54-49-1 | -2.21u | -2.1% | 0.32c | 22s |  |
| M control: not gettable | 852 | 626 | -0.91c | 34.2% | 617 | -1.3c | 643 | 330-299-14 | -7.51u | -1.2% | 1.78c | 102s |  |
| M all moves | 1073 | 830 | -0.86c | 33.7% | 818 | -1.15c | 847 | 436-394-17 | -8.21u | -1.0% | 1.43c | 44s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 906 | 884 | 2.28c | 23.1% | 183 | 1.69c | 885 | 397-488-0 | +279.27u | 31.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 52 | 41 | -0.17c | 15-26-0 | -9.83u | 28, -0.42c, -5.16u | not enough yet |
| J2 B, NBA | 37 | 28 | -0.13c | 10-18-0 | -7.29u | 16, -0.43c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 30 | 26 | -0.26c | 11-15-0 | -3.13u | 19, -0.61c, +1.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 96 | 80 | -0.78c | 38-41-1 | -4.96u | 49, -1.0c, -3.31u | negative |
| D1 B, unders (descriptive) | 10 | 8 | 0.61c | 4-4-0 | +0.27u | 8, 0.61c, +0.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 9 | 8 | -1.14c | 0-8-0 | -8.00u | 6, -1.69c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 4 | 3 | 0.11c | 1-2-0 | +0.33u | 3, 0.11c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 39 | 38 | -0.44c | 21-15-2 | -1.26u | 19, -0.7c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 971 | 45 | 4.7% | -0.48c | 1.61c | 19-25-0 | -5.15u |  |
| MK novig fair-2c | 973 | 18 | 1.9% | -0.45c | 2.53c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2493 | 122 | 5.0% | -0.93c | 1.1c | 63-55-2 | +11.02u |  |
| MK prophetx fair-2c | 2475 | 36 | 1.5% | -0.61c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3464 | 167 | 4.9% | -0.81c | 1.25c | 82-80-2 | +5.87u | criteria not met (164/50 graded, CLV not positive) |
| MK all fair-2c | 3448 | 54 | 1.6% | -0.56c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 78.

## Odds API credits (100K/month plan)

Study: 593/day, projected 17801/30 days. All monitors on the key: 2053/day, projected 61581/30 days. Remaining 92382; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-04T20:40:40Z: 35 games (21 in 24h), quotes {'prophetx': 1764, 'novig': 718, 'kalshi': 1778, 'polymarket_us': 1814}, 28 unmatched (1 book-games; fuzzy-matched 2), 3745 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 4 B 0, maker posted 8 filled 0, credits used 6 left 92382, 233s
- 2026-11-04T20:31:00Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 726, 'kalshi': 1770, 'polymarket_us': 1938}, 28 unmatched (1 book-games; fuzzy-matched 2), 3863 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 9 filled 0, credits used 14 left 92399, 302s
- 2026-11-04T20:20:50Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 720, 'kalshi': 1780, 'polymarket_us': 1216}, 28 unmatched (1 book-games; fuzzy-matched 2), 3556 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 3 B 0, maker posted 28 filled 0, credits used 12 left 92422, 331s
- 2026-11-04T20:10:56Z: 35 games (21 in 24h), quotes {'prophetx': 1860, 'novig': 724, 'kalshi': 1784, 'polymarket_us': 2308}, 28 unmatched (1 book-games; fuzzy-matched 2), 4047 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 1 B 0, maker posted 24 filled 0, credits used 8 left 92454, 207s
- 2026-11-04T20:01:08Z: 35 games (21 in 24h), quotes {'prophetx': 1826, 'novig': 726, 'kalshi': 1780, 'polymarket_us': 2308}, 28 unmatched (1 book-games; fuzzy-matched 2), 4026 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 1, maker posted 11 filled 2, credits used 12 left 92471, 301s
- 2026-11-04T19:50:55Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 722, 'kalshi': 1760, 'polymarket_us': 2308}, 28 unmatched (1 book-games; fuzzy-matched 2), 4045 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 36 filled 0, credits used 14 left 92492, 301s
- 2026-11-04T19:40:53Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 718, 'kalshi': 1758, 'polymarket_us': 1842}, 28 unmatched (1 book-games; fuzzy-matched 4), 3808 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 0 B 0, maker posted 19 filled 0, credits used 12 left 92515, 302s
- 2026-11-04T19:30:41Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 720, 'kalshi': 1762, 'polymarket_us': 1734}, 28 unmatched (1 book-games; fuzzy-matched 2), 3778 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 9 filled 1, credits used 14 left 92545, 302s
- 2026-11-04T19:20:38Z: 35 games (21 in 24h), quotes {'prophetx': 1816, 'novig': 716, 'kalshi': 1760, 'polymarket_us': 1602}, 28 unmatched (1 book-games; fuzzy-matched 1), 3654 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 1 B 0, maker posted 0 filled 0, credits used 12 left 92570, 326s
- 2026-11-04T19:10:36Z: 35 games (21 in 24h), quotes {'prophetx': 1896, 'novig': 720, 'kalshi': 1762, 'polymarket_us': 1862}, 28 unmatched (1 book-games; fuzzy-matched 2), 3838 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 44 filled 0, credits used 6 left 92600, 208s

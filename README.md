# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T02:36:33Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7392 | 7244 | -1.6c | 23.8% | 3162 | -1.01c | 6903 | 3559-3344-0 | -262.33u | -3.8% |  |  | criteria not met (6903/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1679 | 1618 | -3.14c | 18.1% | 359 | -2.62c | 1524 | 785-739-0 | -122.35u | -8.0% |  |  | criteria not met (1524/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 123 | 123 | -1.01c | 28.5% | 115 | -0.05c | 120 | 53-67-0 | -7.77u | -6.5% |  |  | criteria not met (120/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 72 | 72 | -1.03c | 27.8% | 69 | -0.19c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 42 | 42 | -1.2c | 28.6% | 37 | -0.07c | 41 | 15-26-0 | -9.38u | -22.9% |  |  |  |
| M move-watch: gettable (sightings) | 335 | 327 | -0.62c | 33.6% | 326 | -0.61c | 303 | 154-145-4 | -7.72u | -2.5% | 0.18c | 26s | criteria not met (303/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 173 | 169 | -0.67c | 34.3% | 170 | -0.84c | 156 | 76-77-3 | -7.69u | -4.9% | -0.09c | 27s |  |
| M gettable, price moves | 162 | 158 | -0.57c | 32.9% | 156 | -0.37c | 147 | 78-68-1 | -0.03u | -0.0% | 0.47c | 24s |  |
| M control: not gettable | 1389 | 1094 | -0.82c | 35.7% | 1082 | -1.22c | 1037 | 506-512-19 | -67.44u | -6.5% | 1.78c | 183s |  |
| M all moves | 1724 | 1421 | -0.77c | 35.3% | 1408 | -1.08c | 1340 | 660-657-23 | -75.15u | -5.6% | 1.47c | 115s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1035 | 1031 | 2.73c | 27.1% | 222 | 2.91c | 998 | 438-560-0 | +263.39u | 26.4% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 75 | 73 | -0.18c | 33-40-0 | -3.88u | 49, -0.43c, -7.23u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 43 | -0.45c | 22-21-0 | +2.86u | 33, -0.76c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 189 | 164 | -0.68c | 78-84-2 | -10.13u | 96, -0.71c, -13.56u | negative |
| D1 B, unders (descriptive) | 22 | 21 | 0.3c | 13-8-0 | +5.89u | 20, 0.25c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 10 | 9 | 0.42c | 4-5-0 | +0.46u | 8, 0.42c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 60 | 53 | -0.34c | 29-22-2 | -3.11u | 28, -0.4c, -3.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1702 | 73 | 4.3% | -0.65c | 1.59c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1700 | 27 | 1.6% | -0.4c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4426 | 210 | 4.8% | -1.0c | 1.1c | 98-94-4 | +8.60u |  |
| MK prophetx fair-2c | 4400 | 68 | 1.5% | -0.58c | 2.04c | 31-32-0 | +1.63u |  |
| MK all fair-1c | 6128 | 283 | 4.6% | -0.91c | 1.24c | 135-129-4 | +11.69u | criteria not met (268/50 graded, CLV not positive) |
| MK all fair-2c | 6100 | 95 | 1.6% | -0.53c | 2.17c | 47-42-0 | +9.28u | criteria not met (89/50 graded, CLV not positive) |

A and B on the same side/line: 97.

## Odds API credits (100K/month plan)

Study: 646/day, projected 19369/30 days. All monitors on the key: 2189/day, projected 65671/30 days. Remaining 84186; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T02:31:30Z: 31 games (31 in 24h), quotes {'prophetx': 2470, 'novig': 668, 'kalshi': 2222, 'polymarket_us': 1400}, 919 unmatched (30 book-games; fuzzy-matched 1), 3812 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 14 left 84186, 302s
- 2026-11-08T02:21:25Z: 32 games (32 in 24h), quotes {'prophetx': 2794, 'novig': 658, 'kalshi': 2604, 'polymarket_us': 1936}, 911 unmatched (29 book-games; fuzzy-matched 4), 4442 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 40 B 0, maker posted 24 filled 0, credits used 12 left 84217, 301s
- 2026-11-08T02:11:24Z: 32 games (32 in 24h), quotes {'prophetx': 2330, 'novig': 664, 'kalshi': 2286, 'polymarket_us': 1688}, 974 unmatched (31 book-games; fuzzy-matched 2), 3854 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 9 B 0, maker posted 4 filled 2, credits used 8 left 84260, 214s
- 2026-11-08T02:01:30Z: 35 games (33 in 24h), quotes {'prophetx': 2414, 'novig': 654, 'kalshi': 2696, 'polymarket_us': 2030}, 890 unmatched (28 book-games; fuzzy-matched 2), 4387 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 6, new A 41 B 0, maker posted 8 filled 0, credits used 12 left 84283, 362s
- 2026-11-08T01:51:09Z: 35 games (33 in 24h), quotes {'prophetx': 2482, 'novig': 664, 'kalshi': 2816, 'polymarket_us': 2642}, 919 unmatched (28 book-games; fuzzy-matched 2), 4829 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 8 filled 0, credits used 12 left 84314, 301s
- 2026-11-08T01:42:07Z: 36 games (34 in 24h), quotes {'prophetx': 2480, 'novig': 656, 'kalshi': 2822, 'polymarket_us': 1866}, 915 unmatched (27 book-games; fuzzy-matched 2), 4434 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 7 B 1, maker posted 24 filled 0, credits used 8 left 84352, 182s
- 2026-11-08T01:35:43Z: 36 games (34 in 24h), quotes {'prophetx': 2480, 'novig': 668, 'kalshi': 2938, 'polymarket_us': 2886}, 954 unmatched (27 book-games; fuzzy-matched 2), 5044 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 16 B 1, maker posted 24 filled 1, credits used 6 left 84364, 305s
- 2026-11-08T01:31:20Z: 36 games (34 in 24h), quotes {'prophetx': 2432, 'novig': 694, 'kalshi': 2404, 'polymarket_us': 1996}, 958 unmatched (27 book-games; fuzzy-matched 2), 4172 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 4 filled 3, credits used 6 left 84381, 184s
- 2026-11-08T01:21:29Z: 36 games (34 in 24h), quotes {'prophetx': 2478, 'novig': 686, 'kalshi': 2554, 'polymarket_us': 2038}, 1024 unmatched (28 book-games; fuzzy-matched 2), 4198 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 21 B 0, maker posted 12 filled 0, credits used 14 left 84400, 328s
- 2026-11-08T01:11:16Z: 37 games (34 in 24h), quotes {'prophetx': 2310, 'novig': 690, 'kalshi': 2124, 'polymarket_us': 1748}, 1031 unmatched (28 book-games; fuzzy-matched 2), 3776 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 20 filled 0, credits used 6 left 84440, 185s

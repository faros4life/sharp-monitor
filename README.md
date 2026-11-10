# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-10T23:44:48Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8700 | 8299 | -1.6c | 24.1% | 3641 | -1.03c | 8300 | 4291-4009-0 | -277.65u | -3.3% |  |  | criteria not met (8300/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1932 | 1827 | -3.11c | 18.7% | 401 | -2.68c | 1827 | 940-887-0 | -143.32u | -7.8% |  |  | criteria not met (1827/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 149 | 143 | -0.84c | 28.7% | 133 | 0.06c | 143 | 65-78-0 | -5.23u | -3.7% |  |  | criteria not met (143/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 13 | 13 | -0.03c | 30.8% | 13 | 1.15c | 13 | 7-6-0 | +1.63u | 12.5% |  |  |  |
| B ref age 1-5m | 84 | 81 | -1.01c | 27.2% | 77 | -0.1c | 81 | 37-44-0 | -2.25u | -2.8% |  |  |  |
| B ref age 5m+ | 52 | 49 | -0.77c | 30.6% | 43 | 0.01c | 49 | 21-28-0 | -4.61u | -9.4% |  |  |  |
| M move-watch: gettable (sightings) | 415 | 381 | -0.65c | 34.9% | 379 | -0.55c | 385 | 201-179-5 | +3.19u | 0.8% | 0.17c | 27s | criteria not met (385/50 graded, CLV not positive) |
| M gettable, line moves | 213 | 201 | -0.81c | 33.8% | 200 | -0.81c | 203 | 103-96-4 | -2.26u | -1.1% | -0.19c | 28s |  |
| M gettable, price moves | 202 | 180 | -0.48c | 36.1% | 179 | -0.25c | 182 | 98-83-1 | +5.45u | 3.0% | 0.57c | 26s |  |
| M control: not gettable | 1667 | 1281 | -0.77c | 36.3% | 1252 | -1.19c | 1317 | 656-640-21 | -60.41u | -4.6% | 1.9c | 184s |  |
| M all moves | 2082 | 1662 | -0.74c | 36.0% | 1631 | -1.04c | 1702 | 857-819-26 | -57.22u | -3.4% | 1.57c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1068 | 1057 | 2.6c | 27.0% | 224 | 2.85c | 1058 | 473-585-0 | +285.80u | 27.0% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 97 | 92 | -0.04c | 43-49-0 | -1.68u | 63, -0.22c, -6.36u | negative |
| J2 B, NBA | 66 | 63 | 0.05c | 30-33-0 | -0.21u | 39, -0.18c, +0.64u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 57 | 54 | -0.23c | 26-28-0 | +0.30u | 43, -0.5c, +0.75u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 240 | 226 | -0.64c | 115-108-3 | -0.42u | 133, -0.62c, -8.55u | negative |
| D1 B, unders (descriptive) | 32 | 29 | 0.49c | 18-11-0 | +8.54u | 27, 0.47c, +6.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 20 | 19 | -0.69c | 7-12-0 | -4.02u | 17, -0.85c, -2.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 14 | 13 | 0.6c | 6-7-0 | +0.79u | 12, 0.61c, -0.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 89 | 73 | -0.14c | 39-32-2 | -1.92u | 41, -0.17c, -1.61u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2273 | 93 | 4.1% | -0.62c | 1.58c | 47-42-0 | +6.98u |  |
| MK novig fair-2c | 2269 | 34 | 1.5% | -0.33c | 2.51c | 20-11-0 | +11.08u |  |
| MK prophetx fair-1c | 5274 | 248 | 4.7% | -1.04c | 1.1c | 116-122-5 | -0.76u |  |
| MK prophetx fair-2c | 5235 | 83 | 1.6% | -0.66c | 2.04c | 39-42-0 | +0.30u |  |
| MK all fair-1c | 7547 | 341 | 4.6% | -0.93c | 1.24c | 163-164-5 | +6.22u | criteria not met (332/50 graded, CLV not positive) |
| MK all fair-2c | 7504 | 117 | 1.6% | -0.57c | 2.18c | 59-53-0 | +11.38u | criteria not met (112/50 graded, CLV not positive) |

A and B on the same side/line: 120.

## Odds API credits (100K/month plan)

Study: 641/day, projected 19236/30 days. All monitors on the key: 2374/day, projected 71211/30 days. Remaining 75262; guard holds 57600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-10T23:41:46Z: 30 games (16 in 24h), quotes {'prophetx': 1152, 'novig': 693, 'kalshi': 1440, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2821 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 17 filled 2, credits used 6 left 75262, 182s
- 2026-11-10T23:32:15Z: 30 games (16 in 24h), quotes {'prophetx': 1152, 'novig': 701, 'kalshi': 1450, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2833 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 7, new A 2 B 0, maker posted 27 filled 0, credits used 12 left 75289, 325s
- 2026-11-10T23:22:30Z: 30 games (16 in 24h), quotes {'prophetx': 1152, 'novig': 697, 'kalshi': 1442, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2823 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 7 filled 0, credits used 6 left 75344, 183s
- 2026-11-10T23:16:24Z: 30 games (16 in 24h), quotes {'prophetx': 1160, 'novig': 691, 'kalshi': 1446, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 63), 2831 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 2 B 2, maker posted 6 filled 11, credits used 6 left 75363, 232s
- 2026-11-10T23:11:08Z: 30 games (16 in 24h), quotes {'prophetx': 1160, 'novig': 701, 'kalshi': 1422, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2812 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 4 filled 0, credits used 6 left 75380, 181s
- 2026-11-10T23:02:15Z: 30 games (16 in 24h), quotes {'prophetx': 1160, 'novig': 691, 'kalshi': 1444, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 62), 2836 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 2 B 0, maker posted 16 filled 1, credits used 12 left 75395, 352s
- 2026-11-10T22:51:47Z: 30 games (16 in 24h), quotes {'prophetx': 1160, 'novig': 694, 'kalshi': 1420, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2813 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 3 B 1, maker posted 8 filled 0, credits used 12 left 75424, 301s
- 2026-11-10T22:42:07Z: 30 games (16 in 24h), quotes {'prophetx': 1160, 'novig': 702, 'kalshi': 1424, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2815 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 2 B 0, maker posted 72 filled 0, credits used 6 left 75445, 184s
- 2026-11-10T22:32:12Z: 30 games (16 in 24h), quotes {'prophetx': 1126, 'novig': 690, 'kalshi': 1420, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2791 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 0 B 0, maker posted 12 filled 0, credits used 12 left 75460, 339s
- 2026-11-10T22:21:50Z: 30 games (16 in 24h), quotes {'prophetx': 1126, 'novig': 691, 'kalshi': 1420, 'polymarket_us': 1362}, 0 unmatched (0 book-games; fuzzy-matched 0), 2785 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 34 filled 0, credits used 12 left 75487, 302s

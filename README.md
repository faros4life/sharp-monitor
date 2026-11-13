# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-13T01:23:08Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9896 | 9705 | -1.62c | 24.5% | 4203 | -1.09c | 9410 | 4896-4514-0 | -289.07u | -3.1% |  |  | criteria not met (9410/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2258 | 2186 | -3.1c | 19.6% | 494 | -2.84c | 2100 | 1085-1015-0 | -162.54u | -7.7% |  |  | criteria not met (2100/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 175 | 174 | -0.8c | 31.6% | 163 | 0.14c | 161 | 67-94-0 | -18.81u | -11.7% |  |  | criteria not met (161/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 16 | 16 | -0.11c | 31.2% | 16 | 1.04c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 96 | 96 | -0.86c | 32.3% | 91 | 0.08c | 89 | 38-51-0 | -7.87u | -8.8% |  |  |  |
| B ref age 5m+ | 63 | 62 | -0.89c | 30.6% | 56 | -0.03c | 57 | 22-35-0 | -10.57u | -18.5% |  |  |  |
| M move-watch: gettable (sightings) | 467 | 459 | -0.6c | 35.3% | 457 | -0.54c | 439 | 223-211-5 | -7.21u | -1.6% | 0.21c | 28s | criteria not met (439/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 240 | 237 | -0.74c | 35.4% | 236 | -0.79c | 226 | 108-114-4 | -15.80u | -7.0% | -0.16c | 28s |  |
| M gettable, price moves | 227 | 222 | -0.45c | 35.1% | 221 | -0.28c | 213 | 115-97-1 | +8.59u | 4.0% | 0.6c | 26s |  |
| M control: not gettable | 1850 | 1479 | -0.82c | 35.6% | 1450 | -1.24c | 1484 | 740-720-24 | -64.98u | -4.4% | 1.88c | 184s |  |
| M all moves | 2317 | 1938 | -0.77c | 35.5% | 1907 | -1.07c | 1923 | 963-931-29 | -72.19u | -3.8% | 1.55c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1110 | 1095 | 2.41c | 27.2% | 234 | 2.42c | 1084 | 488-596-0 | +293.23u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 118 | 107 | 0.12c | 45-62-0 | -12.26u | 73, -0.14c, -14.32u | negative |
| J2 B, NBA | 84 | 75 | 0.26c | 31-44-0 | -9.82u | 47, 0.01c, -7.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 68 | 62 | 0.04c | 27-35-0 | -5.32u | 48, -0.4c, -4.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 276 | 258 | -0.6c | 123-132-3 | -17.00u | 148, -0.69c, -13.93u | negative |
| D1 B, unders (descriptive) | 43 | 36 | 0.5c | 18-18-0 | +1.54u | 33, 0.45c, +0.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.3c | 9-5-1 | +0.53u | 11, -0.47c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 19 | 16 | 0.41c | 6-10-0 | -2.21u | 15, 0.41c, -3.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 105 | 95 | -0.3c | 53-40-2 | +4.26u | 50, -0.39c, +0.46u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2738 | 116 | 4.3% | -0.56c | 1.58c | 54-54-0 | +2.40u |  |
| MK novig fair-2c | 2727 | 47 | 1.7% | -0.08c | 2.52c | 25-20-0 | +7.63u |  |
| MK prophetx fair-1c | 5906 | 280 | 4.8% | -1.07c | 1.1c | 129-138-5 | -3.19u |  |
| MK prophetx fair-2c | 5866 | 102 | 1.7% | -0.56c | 2.04c | 47-53-0 | -2.00u |  |
| MK all fair-1c | 8644 | 396 | 4.6% | -0.92c | 1.25c | 183-192-5 | -0.79u | criteria not met (380/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 8593 | 149 | 1.7% | -0.41c | 2.19c | 72-73-0 | +5.63u | criteria not met (145/50 graded, CLV not positive) |

A and B on the same side/line: 145.

## Odds API credits (100K/month plan)

Study: 653/day, projected 19583/30 days. All monitors on the key: 2444/day, projected 73325/30 days. Remaining 69209; guard holds 52400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-13T01:20:06Z: 18 games (10 in 24h), quotes {'prophetx': 918, 'novig': 694, 'kalshi': 1508, 'polymarket_us': 1080}, 464 unmatched (14 book-games; fuzzy-matched 2), 2220 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 36 B 0, maker posted 12 filled 0, credits used 6 left 69209, 183s
- 2026-11-13T01:12:20Z: 19 games (11 in 24h), quotes {'prophetx': 562, 'novig': 696, 'kalshi': 1518, 'polymarket_us': 1220}, 406 unmatched (13 book-games; fuzzy-matched 2), 2187 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 34 B 0, maker posted 1 filled 1, credits used 6 left 69219, 182s
- 2026-11-13T01:02:49Z: 22 games (11 in 24h), quotes {'prophetx': 766, 'novig': 692, 'kalshi': 1546, 'polymarket_us': 1220}, 308 unmatched (10 book-games; fuzzy-matched 4), 2424 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 40 B 0, maker posted 8 filled 0, credits used 16 left 69259, 301s
- 2026-11-13T00:52:23Z: 23 games (12 in 24h), quotes {'prophetx': 992, 'novig': 699, 'kalshi': 1588, 'polymarket_us': 1160}, 248 unmatched (9 book-games; fuzzy-matched 4), 2584 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 8 B 1, maker posted 43 filled 2, credits used 16 left 69296, 302s
- 2026-11-13T00:41:44Z: 23 games (12 in 24h), quotes {'prophetx': 978, 'novig': 697, 'kalshi': 1588, 'polymarket_us': 1160}, 250 unmatched (9 book-games; fuzzy-matched 2), 2562 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 23 filled 2, credits used 8 left 69345, 183s
- 2026-11-13T00:32:50Z: 24 games (13 in 24h), quotes {'prophetx': 978, 'novig': 701, 'kalshi': 1590, 'polymarket_us': 1160}, 236 unmatched (8 book-games; fuzzy-matched 7), 2574 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 2 B 0, maker posted 13 filled 0, credits used 16 left 69372, 376s
- 2026-11-13T00:22:20Z: 24 games (13 in 24h), quotes {'prophetx': 1008, 'novig': 701, 'kalshi': 1608, 'polymarket_us': 1188}, 250 unmatched (8 book-games; fuzzy-matched 2), 2576 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 22 B 1, maker posted 4 filled 1, credits used 8 left 69411, 192s
- 2026-11-13T00:12:48Z: 25 games (14 in 24h), quotes {'prophetx': 800, 'novig': 699, 'kalshi': 1622, 'polymarket_us': 1188}, 184 unmatched (7 book-games; fuzzy-matched 2), 2614 side/lines, polls [NFL:fast,NCAAF:fast,NBA:fast,NHL:fast; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 12 filled 0, credits used 16 left 69443, 302s
- 2026-11-13T00:03:18Z: 31 games (18 in 24h), quotes {'prophetx': 800, 'novig': 695, 'kalshi': 1626, 'polymarket_us': 1188}, 28 unmatched (1 book-games; fuzzy-matched 2), 2831 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 8 B 0, maker posted 6 filled 0, credits used 8 left 69474, 196s
- 2026-11-12T23:58:22Z: 31 games (17 in 24h), quotes {'prophetx': 1102, 'novig': 723, 'kalshi': 1584, 'polymarket_us': 1206}, 28 unmatched (1 book-games; fuzzy-matched 2), 2858 side/lines, polls [none_due; NFL:fast,NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 14 filled 1, credits used 8 left 69482, 184s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-09T17:44:45Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8146 | 7858 | -1.61c | 23.7% | 3453 | -1.03c | 7859 | 4053-3806-0 | -279.14u | -3.6% |  |  | criteria not met (7859/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1807 | 1740 | -3.1c | 18.3% | 384 | -2.64c | 1740 | 895-845-0 | -133.38u | -7.7% |  |  | criteria not met (1740/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 136 | 132 | -1.07c | 26.5% | 123 | -0.09c | 132 | 58-74-0 | -9.06u | -6.9% |  |  | criteria not met (132/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 79 | 78 | -1.13c | 25.6% | 74 | -0.19c | 78 | 36-42-0 | -1.33u | -1.7% |  |  |  |
| B ref age 5m+ | 48 | 45 | -1.21c | 26.7% | 40 | -0.15c | 45 | 17-28-0 | -9.12u | -20.3% |  |  |  |
| M move-watch: gettable (sightings) | 371 | 362 | -0.59c | 35.1% | 362 | -0.56c | 366 | 190-171-5 | -0.88u | -0.2% | 0.23c | 26s | criteria not met (366/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 196 | 189 | -0.69c | 34.4% | 190 | -0.82c | 191 | 96-91-4 | -3.71u | -1.9% | -0.08c | 26s |  |
| M gettable, price moves | 175 | 173 | -0.49c | 35.8% | 172 | -0.28c | 175 | 94-80-1 | +2.83u | 1.6% | 0.56c | 23s |  |
| M control: not gettable | 1528 | 1208 | -0.77c | 36.3% | 1190 | -1.18c | 1240 | 615-604-21 | -60.01u | -4.8% | 1.84c | 183s |  |
| M all moves | 1899 | 1570 | -0.73c | 36.0% | 1552 | -1.04c | 1606 | 805-775-26 | -60.88u | -3.8% | 1.52c | 151s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1057 | 1038 | 2.7c | 27.3% | 222 | 2.91c | 1039 | 461-578-0 | +281.38u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 87 | 83 | -0.24c | 37-46-0 | -5.42u | 57, -0.46c, -11.02u | negative |
| J2 B, NBA | 58 | 54 | -0.26c | 24-30-0 | -3.95u | 33, -0.63c, -4.02u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 50 | 49 | -0.46c | 24-25-0 | +1.07u | 39, -0.73c, +2.60u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 219 | 214 | -0.64c | 107-104-3 | -3.87u | 125, -0.65c, -10.14u | negative |
| D1 B, unders (descriptive) | 27 | 25 | 0.11c | 15-10-0 | +6.16u | 23, 0.06c, +3.95u | descriptive only |
| D2 B, underdog spreads (descriptive) | 18 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 11 | 0.45c | 5-6-0 | +0.71u | 10, 0.44c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 66 | 66 | -0.21c | 36-28-2 | -2.54u | 38, -0.28c, -1.24u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2023 | 82 | 4.1% | -0.62c | 1.58c | 42-40-0 | +3.52u |  |
| MK novig fair-2c | 2019 | 30 | 1.5% | -0.35c | 2.51c | 19-11-0 | +9.90u |  |
| MK prophetx fair-1c | 4873 | 231 | 4.7% | -1.02c | 1.1c | 111-115-5 | +1.02u |  |
| MK prophetx fair-2c | 4840 | 76 | 1.6% | -0.59c | 2.04c | 37-39-0 | +1.11u |  |
| MK all fair-1c | 6896 | 313 | 4.5% | -0.92c | 1.24c | 153-155-5 | +4.54u | criteria not met (313/50 graded, CLV not positive) |
| MK all fair-2c | 6859 | 106 | 1.5% | -0.52c | 2.18c | 56-50-0 | +11.01u | criteria not met (106/50 graded, CLV not positive) |

A and B on the same side/line: 108.

## Odds API credits (100K/month plan)

Study: 631/day, projected 18937/30 days. All monitors on the key: 2359/day, projected 70763/30 days. Remaining 78422; guard holds 60200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-09T17:41:44Z: 23 games (12 in 24h), quotes {'prophetx': 1088, 'novig': 720, 'kalshi': 1118, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2465 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 78422, 182s
- 2026-11-09T17:31:40Z: 23 games (12 in 24h), quotes {'prophetx': 952, 'novig': 720, 'kalshi': 1116, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2393 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 78431, 181s
- 2026-11-09T17:21:47Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 718, 'kalshi': 1118, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2466 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 8 left 78440, 182s
- 2026-11-09T17:12:01Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 722, 'kalshi': 1118, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2465 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 78459, 183s
- 2026-11-09T17:01:42Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 726, 'kalshi': 1120, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2467 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 8 left 78470, 184s
- 2026-11-09T16:51:41Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 722, 'kalshi': 1118, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2465 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 78496, 182s
- 2026-11-09T16:41:08Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 728, 'kalshi': 1120, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2464 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 1, new A 0 B 0, maker posted 0 filled 0, credits used 8 left 78514, 184s
- 2026-11-09T16:31:35Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 728, 'kalshi': 1120, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2465 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 78533, 181s
- 2026-11-09T16:21:45Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 726, 'kalshi': 1116, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2461 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 78562, 183s
- 2026-11-09T16:12:02Z: 23 games (12 in 24h), quotes {'prophetx': 1084, 'novig': 728, 'kalshi': 1116, 'polymarket_us': 1244}, 0 unmatched (0 book-games; fuzzy-matched 0), 2461 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:slow], moves 3, new A 1 B 0, maker posted 0 filled 0, credits used 8 left 78573, 184s

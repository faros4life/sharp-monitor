# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-10T05:31:34Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 8545 | 8299 | -1.6c | 24.1% | 3641 | -1.03c | 8264 | 4271-3993-0 | -275.53u | -3.3% |  |  | criteria not met (8264/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1908 | 1827 | -3.11c | 18.7% | 401 | -2.68c | 1825 | 938-887-0 | -144.24u | -7.9% |  |  | criteria not met (1825/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 143 | 143 | -0.84c | 28.7% | 133 | 0.06c | 142 | 65-77-0 | -4.23u | -3.0% |  |  | criteria not met (142/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 13 | 13 | -0.03c | 30.8% | 13 | 1.15c | 12 | 7-5-0 | +2.63u | 21.9% |  |  |  |
| B ref age 1-5m | 81 | 81 | -1.01c | 27.2% | 77 | -0.1c | 81 | 37-44-0 | -2.25u | -2.8% |  |  |  |
| B ref age 5m+ | 49 | 49 | -0.77c | 30.6% | 43 | 0.01c | 49 | 21-28-0 | -4.61u | -9.4% |  |  |  |
| M move-watch: gettable (sightings) | 389 | 381 | -0.65c | 34.9% | 379 | -0.55c | 380 | 199-176-5 | +3.33u | 0.9% | 0.17c | 26s | criteria not met (380/50 graded, CLV not positive) |
| M gettable, line moves | 203 | 201 | -0.81c | 33.8% | 200 | -0.81c | 201 | 102-95-4 | -2.18u | -1.1% | -0.19c | 26s |  |
| M gettable, price moves | 186 | 180 | -0.48c | 36.1% | 179 | -0.25c | 179 | 97-81-1 | +5.51u | 3.1% | 0.57c | 24s |  |
| M control: not gettable | 1602 | 1281 | -0.77c | 36.3% | 1252 | -1.19c | 1302 | 645-636-21 | -66.80u | -5.1% | 1.9c | 184s |  |
| M all moves | 1991 | 1662 | -0.74c | 36.0% | 1631 | -1.04c | 1682 | 844-812-26 | -63.47u | -3.8% | 1.57c | 164s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1067 | 1057 | 2.6c | 27.0% | 224 | 2.85c | 1057 | 473-584-0 | +286.80u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 92 | 92 | -0.04c | 43-49-0 | -1.68u | 63, -0.22c, -6.36u | negative |
| J2 B, NBA | 63 | 63 | 0.05c | 30-33-0 | -0.21u | 39, -0.18c, +0.64u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 54 | 54 | -0.23c | 26-28-0 | +0.30u | 43, -0.5c, +0.75u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 226 | 225 | -0.64c | 114-108-3 | -1.33u | 132, -0.62c, -9.47u | negative |
| D1 B, unders (descriptive) | 29 | 29 | 0.49c | 18-11-0 | +8.54u | 27, 0.47c, +6.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 19 | 19 | -0.69c | 7-12-0 | -4.02u | 17, -0.85c, -2.02u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 13 | 12 | 0.6c | 6-6-0 | +1.79u | 11, 0.61c, +0.64u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 77 | 69 | -0.14c | 38-29-2 | -0.86u | 39, -0.17c, +0.39u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2138 | 89 | 4.2% | -0.62c | 1.58c | 47-42-0 | +6.98u |  |
| MK novig fair-2c | 2135 | 31 | 1.5% | -0.33c | 2.51c | 20-11-0 | +11.08u |  |
| MK prophetx fair-1c | 5073 | 243 | 4.8% | -1.04c | 1.1c | 116-119-5 | +2.24u |  |
| MK prophetx fair-2c | 5036 | 81 | 1.6% | -0.66c | 2.04c | 39-40-0 | +2.30u |  |
| MK all fair-1c | 7211 | 332 | 4.6% | -0.93c | 1.24c | 163-161-5 | +9.22u | criteria not met (329/50 graded, CLV not positive) |
| MK all fair-2c | 7171 | 112 | 1.6% | -0.57c | 2.18c | 59-51-0 | +13.38u | criteria not met (110/50 graded, CLV not positive) |

A and B on the same side/line: 115.

## Odds API credits (100K/month plan)

Study: 648/day, projected 19432/30 days. All monitors on the key: 2393/day, projected 71791/30 days. Remaining 76800; guard holds 57600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-10T05:31:34Z: outside read hours: closes/grades only
- 2026-11-10T05:21:54Z: outside read hours: closes/grades only
- 2026-11-10T05:11:34Z: outside read hours: closes/grades only
- 2026-11-10T05:02:01Z: outside read hours: closes/grades only
- 2026-11-10T04:51:10Z: 16 games (16 in 24h), quotes {'prophetx': 1062, 'novig': 691, 'kalshi': 828, 'polymarket_us': 1356}, 52 unmatched (3 book-games; fuzzy-matched 0), 2004 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 3, new A 6 B 0, maker posted 0 filled 0, credits used 6 left 76800, 182s
- 2026-11-10T04:41:10Z: 16 games (16 in 24h), quotes {'prophetx': 1028, 'novig': 699, 'kalshi': 820, 'polymarket_us': 1356}, 58 unmatched (3 book-games; fuzzy-matched 0), 2000 side/lines, polls [none_due], moves 0, new A 14 B 0, maker posted 0 filled 0, credits used 0 left 76815, 181s
- 2026-11-10T04:31:13Z: 16 games (16 in 24h), quotes {'prophetx': 1014, 'novig': 693, 'kalshi': 770, 'polymarket_us': 1356}, 64 unmatched (3 book-games; fuzzy-matched 0), 1978 side/lines, polls [none_due], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 0 left 76828, 181s
- 2026-11-10T04:21:50Z: 15 games (15 in 24h), quotes {'prophetx': 1014, 'novig': 697, 'kalshi': 786, 'polymarket_us': 1356}, 217 unmatched (6 book-games; fuzzy-matched 0), 1856 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 6 left 76846, 183s
- 2026-11-10T04:11:35Z: 15 games (15 in 24h), quotes {'prophetx': 970, 'novig': 693, 'kalshi': 814, 'polymarket_us': 1356}, 241 unmatched (7 book-games; fuzzy-matched 0), 1812 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 76861, 181s
- 2026-11-10T04:01:14Z: 15 games (14 in 24h), quotes {'prophetx': 970, 'novig': 699, 'kalshi': 850, 'polymarket_us': 1356}, 272 unmatched (7 book-games; fuzzy-matched 0), 1812 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 76874, 181s

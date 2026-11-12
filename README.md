# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-12T04:24:09Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9614 | 9405 | -1.62c | 24.4% | 4076 | -1.07c | 9301 | 4833-4468-0 | -290.85u | -3.1% |  |  | criteria not met (9301/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2179 | 2100 | -3.08c | 19.5% | 470 | -2.73c | 2092 | 1078-1014-0 | -164.52u | -7.9% |  |  | criteria not met (2092/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 164 | 161 | -0.76c | 31.1% | 151 | 0.14c | 161 | 67-94-0 | -18.81u | -11.7% |  |  | criteria not met (161/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 15 | 15 | -0.15c | 26.7% | 15 | 1.01c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 91 | 89 | -0.82c | 31.5% | 85 | 0.05c | 89 | 38-51-0 | -7.87u | -8.8% |  |  |  |
| B ref age 5m+ | 58 | 57 | -0.83c | 31.6% | 51 | 0.04c | 57 | 22-35-0 | -10.57u | -18.5% |  |  |  |
| M move-watch: gettable (sightings) | 440 | 434 | -0.62c | 34.8% | 432 | -0.54c | 433 | 220-208-5 | -6.31u | -1.5% | 0.2c | 27s | criteria not met (433/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 227 | 224 | -0.79c | 34.8% | 223 | -0.82c | 223 | 108-111-4 | -12.80u | -5.7% | -0.19c | 28s |  |
| M gettable, price moves | 213 | 210 | -0.45c | 34.8% | 209 | -0.24c | 210 | 112-97-1 | +6.49u | 3.1% | 0.61c | 25s |  |
| M control: not gettable | 1803 | 1445 | -0.83c | 35.5% | 1413 | -1.25c | 1457 | 724-710-23 | -71.10u | -4.9% | 1.87c | 184s |  |
| M all moves | 2243 | 1879 | -0.78c | 35.3% | 1845 | -1.08c | 1890 | 944-918-28 | -77.41u | -4.1% | 1.54c | 182s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1100 | 1083 | 2.45c | 27.1% | 232 | 2.44c | 1084 | 488-596-0 | +293.23u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 110 | 107 | 0.13c | 45-62-0 | -12.26u | 73, -0.08c, -14.32u | negative |
| J2 B, NBA | 78 | 75 | 0.3c | 31-44-0 | -9.82u | 47, 0.08c, -7.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 64 | 62 | -0.01c | 27-35-0 | -5.32u | 48, -0.3c, -4.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 259 | 256 | -0.6c | 123-130-3 | -15.00u | 146, -0.65c, -11.93u | negative |
| D1 B, unders (descriptive) | 37 | 36 | 0.63c | 18-18-0 | +1.54u | 33, 0.63c, +0.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 16 | 16 | 0.34c | 6-10-0 | -2.21u | 15, 0.33c, -3.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 95 | 91 | -0.27c | 50-39-2 | +3.16u | 47, -0.36c, -0.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2472 | 108 | 4.4% | -0.57c | 1.58c | 54-53-0 | +3.40u |  |
| MK novig fair-2c | 2466 | 45 | 1.8% | -0.08c | 2.52c | 25-18-0 | +9.63u |  |
| MK prophetx fair-1c | 5633 | 272 | 4.8% | -1.05c | 1.1c | 129-136-5 | -1.19u |  |
| MK prophetx fair-2c | 5595 | 100 | 1.8% | -0.56c | 2.05c | 46-52-0 | -2.10u |  |
| MK all fair-1c | 8105 | 380 | 4.7% | -0.91c | 1.25c | 183-189-5 | +2.21u | criteria not met (377/50 graded, CLV not positive) |
| MK all fair-2c | 8061 | 145 | 1.8% | -0.41c | 2.19c | 71-70-0 | +7.53u | criteria not met (141/50 graded, CLV not positive) |

A and B on the same side/line: 134.

## Odds API credits (100K/month plan)

Study: 645/day, projected 19342/30 days. All monitors on the key: 2426/day, projected 72768/30 days. Remaining 71631; guard holds 55000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-12T04:21:07Z: 18 games (18 in 24h), quotes {'prophetx': 1034, 'novig': 695, 'kalshi': 816, 'polymarket_us': 1222}, 170 unmatched (7 book-games; fuzzy-matched 2), 1863 side/lines, polls [none_due], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 0 left 71631, 182s
- 2026-11-12T04:15:53Z: 18 games (18 in 24h), quotes {'prophetx': 1064, 'novig': 701, 'kalshi': 842, 'polymarket_us': 1222}, 192 unmatched (7 book-games; fuzzy-matched 4), 1869 side/lines, polls [NBA:slow,NHL:slow], moves 3, new A 22 B 2, maker posted 0 filled 0, credits used 4 left 71642, 184s
- 2026-11-12T04:10:38Z: 18 games (18 in 24h), quotes {'prophetx': 912, 'novig': 701, 'kalshi': 846, 'polymarket_us': 1222}, 198 unmatched (7 book-games; fuzzy-matched 2), 1805 side/lines, polls [NFL:slow,NCAAF:slow], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 4 left 71648, 184s
- 2026-11-12T04:02:12Z: 18 games (18 in 24h), quotes {'prophetx': 942, 'novig': 693, 'kalshi': 798, 'polymarket_us': 1222}, 210 unmatched (7 book-games; fuzzy-matched 2), 1825 side/lines, polls [none_due], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 0 left 71663, 182s
- 2026-11-12T03:52:07Z: 17 games (17 in 24h), quotes {'prophetx': 858, 'novig': 699, 'kalshi': 812, 'polymarket_us': 1222}, 394 unmatched (10 book-games; fuzzy-matched 2), 1613 side/lines, polls [NBA:slow,NHL:slow], moves 0, new A 3 B 1, maker posted 0 filled 0, credits used 4 left 71681, 184s
- 2026-11-12T03:42:30Z: 17 games (17 in 24h), quotes {'prophetx': 858, 'novig': 693, 'kalshi': 836, 'polymarket_us': 1222}, 402 unmatched (11 book-games; fuzzy-matched 2), 1615 side/lines, polls [NFL:slow,NCAAF:slow], moves 0, new A 12 B 0, maker posted 0 filled 0, credits used 4 left 71706, 181s
- 2026-11-12T03:31:45Z: 17 games (17 in 24h), quotes {'prophetx': 858, 'novig': 685, 'kalshi': 898, 'polymarket_us': 1222}, 462 unmatched (13 book-games; fuzzy-matched 2), 1605 side/lines, polls [NBA:slow,NHL:slow], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 4 left 71721, 182s
- 2026-11-12T03:22:07Z: 17 games (17 in 24h), quotes {'prophetx': 856, 'novig': 693, 'kalshi': 966, 'polymarket_us': 1222}, 532 unmatched (15 book-games; fuzzy-matched 2), 1605 side/lines, polls [NFL:slow,NCAAF:slow], moves 0, new A 21 B 0, maker posted 0 filled 0, credits used 4 left 71748, 182s
- 2026-11-12T03:11:38Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 695, 'kalshi': 1032, 'polymarket_us': 1222}, 528 unmatched (16 book-games; fuzzy-matched 2), 1677 side/lines, polls [NBA:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 2 left 71767, 183s
- 2026-11-12T03:01:42Z: 20 games (20 in 24h), quotes {'prophetx': 816, 'novig': 710, 'kalshi': 1082, 'polymarket_us': 1222}, 544 unmatched (14 book-games; fuzzy-matched 2), 1714 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 16 B 0, maker posted 0 filled 0, credits used 8 left 71788, 182s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-09T02:08:35Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7920 | 7766 | -1.59c | 23.8% | 3418 | -1.02c | 7562 | 3892-3670-0 | -274.09u | -3.6% |  |  | criteria not met (7562/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1755 | 1708 | -3.08c | 18.2% | 378 | -2.62c | 1648 | 846-802-0 | -131.89u | -8.0% |  |  | criteria not met (1648/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 132 | 132 | -1.07c | 26.5% | 123 | -0.09c | 129 | 55-74-0 | -12.39u | -9.6% |  |  | criteria not met (129/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 78 | 78 | -1.13c | 25.6% | 74 | -0.19c | 76 | 34-42-0 | -3.54u | -4.7% |  |  |  |
| B ref age 5m+ | 45 | 45 | -1.21c | 26.7% | 40 | -0.15c | 44 | 16-28-0 | -10.25u | -23.3% |  |  |  |
| M move-watch: gettable (sightings) | 366 | 361 | -0.59c | 35.2% | 361 | -0.56c | 349 | 181-163-5 | -1.91u | -0.5% | 0.23c | 25s | criteria not met (349/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 191 | 188 | -0.69c | 34.6% | 189 | -0.83c | 180 | 89-87-4 | -6.13u | -3.4% | -0.08c | 26s |  |
| M gettable, price moves | 175 | 173 | -0.49c | 35.8% | 172 | -0.28c | 169 | 92-76-1 | +4.22u | 2.5% | 0.56c | 23s |  |
| M control: not gettable | 1495 | 1190 | -0.79c | 36.0% | 1174 | -1.19c | 1174 | 585-568-21 | -52.33u | -4.5% | 1.82c | 183s |  |
| M all moves | 1861 | 1551 | -0.74c | 35.8% | 1535 | -1.04c | 1523 | 766-731-26 | -54.24u | -3.6% | 1.51c | 119s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1042 | 1038 | 2.7c | 27.3% | 222 | 2.91c | 1033 | 457-576-0 | +280.96u | 27.2% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 83 | 80 | -0.24c | 34-46-0 | -8.75u | 55, -0.46c, -13.22u | negative |
| J2 B, NBA | 54 | 51 | -0.26c | 21-30-0 | -7.28u | 31, -0.63c, -6.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 49 | 47 | -0.46c | 22-25-0 | -1.14u | 37, -0.73c, +0.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 214 | 202 | -0.64c | 99-100-3 | -7.23u | 119, -0.65c, -11.80u | negative |
| D1 B, unders (descriptive) | 25 | 23 | 0.11c | 13-10-0 | +3.89u | 22, 0.06c, +2.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 17 | 17 | -0.84c | 5-12-0 | -6.30u | 15, -1.04c, -4.30u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 11 | 11 | 0.45c | 5-6-0 | +0.71u | 10, 0.44c, -0.44u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 66 | 61 | -0.21c | 35-24-2 | -0.20u | 35, -0.28c, -0.91u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2023 | 82 | 4.1% | -0.62c | 1.58c | 40-39-0 | +2.40u |  |
| MK novig fair-2c | 2019 | 30 | 1.5% | -0.35c | 2.51c | 18-11-0 | +8.82u |  |
| MK prophetx fair-1c | 4873 | 231 | 4.7% | -1.01c | 1.1c | 106-112-5 | -1.18u |  |
| MK prophetx fair-2c | 4840 | 76 | 1.6% | -0.59c | 2.04c | 35-39-0 | -1.12u |  |
| MK all fair-1c | 6896 | 313 | 4.5% | -0.91c | 1.24c | 146-151-5 | +1.21u | criteria not met (302/50 graded, CLV not positive) |
| MK all fair-2c | 6859 | 106 | 1.5% | -0.52c | 2.18c | 53-50-0 | +7.70u | criteria not met (103/50 graded, CLV not positive) |

A and B on the same side/line: 104.

## Odds API credits (100K/month plan)

Study: 656/day, projected 19677/30 days. All monitors on the key: 2399/day, projected 71977/30 days. Remaining 79459; guard holds 62800 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-09T02:05:43Z: 9 games (6 in 24h), quotes {'prophetx': 354, 'novig': 420, 'kalshi': 714, 'polymarket_us': 920}, 681 unmatched (13 book-games; fuzzy-matched 0), 831 side/lines, polls [none_due; NBA:fast], moves 0, new A 13 B 0, maker posted 0 filled 0, credits used 2 left 79459, 172s
- 2026-11-09T02:01:27Z: 9 games (6 in 24h), quotes {'prophetx': 250, 'novig': 516, 'kalshi': 718, 'polymarket_us': 920}, 688 unmatched (13 book-games; fuzzy-matched 0), 875 side/lines, polls [NFL:slow,NHL:slow; NBA:fast], moves 2, new A 30 B 0, maker posted 4 filled 0, credits used 6 left 79461, 155s
- 2026-11-09T01:51:37Z: 9 games (6 in 24h), quotes {'prophetx': 440, 'novig': 428, 'kalshi': 682, 'polymarket_us': 1052}, 656 unmatched (11 book-games; fuzzy-matched 0), 1053 side/lines, polls [none_due; NBA:fast; NBA:fast], moves 0, new A 9 B 0, maker posted 0 filled 0, credits used 4 left 79476, 406s
- 2026-11-09T01:41:22Z: 8 games (5 in 24h), quotes {'prophetx': 322, 'novig': 418, 'kalshi': 692, 'polymarket_us': 678}, 420 unmatched (9 book-games; fuzzy-matched 0), 925 side/lines, polls [NFL:slow; NBA:fast; NBA:fast], moves 1, new A 15 B 0, maker posted 0 filled 1, credits used 6 left 79493, 429s
- 2026-11-09T01:31:40Z: 8 games (4 in 24h), quotes {'prophetx': 250, 'novig': 332, 'kalshi': 704, 'polymarket_us': 0}, 312 unmatched (9 book-games; fuzzy-matched 0), 612 side/lines, polls [NHL:slow; NBA:fast; NBA:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 6 left 79517, 386s
- 2026-11-09T01:24:44Z: 8 games (4 in 24h), quotes {'prophetx': 308, 'novig': 328, 'kalshi': 736, 'polymarket_us': 554}, 466 unmatched (11 book-games; fuzzy-matched 0), 871 side/lines, polls [none_due; NBA:fast], moves 0, new A 4 B 0, maker posted 4 filled 0, credits used 2 left 79534, 201s
- 2026-11-09T01:20:07Z: 9 games (5 in 24h), quotes {'prophetx': 308, 'novig': 314, 'kalshi': 754, 'polymarket_us': 554}, 419 unmatched (10 book-games; fuzzy-matched 0), 929 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, maker posted 8 filled 0, credits used 2 left 79545, 178s
- 2026-11-09T01:11:36Z: 10 games (5 in 24h), quotes {'prophetx': 336, 'novig': 314, 'kalshi': 776, 'polymarket_us': 554}, 363 unmatched (9 book-games; fuzzy-matched 0), 1018 side/lines, polls [none_due; NFL:fast,NBA:fast; NFL:fast,NBA:fast], moves 2, new A 2 B 0, maker posted 7 filled 1, credits used 8 left 79549, 412s
- 2026-11-09T01:01:27Z: 11 games (6 in 24h), quotes {'prophetx': 336, 'novig': 396, 'kalshi': 788, 'polymarket_us': 554}, 344 unmatched (7 book-games; fuzzy-matched 0), 1054 side/lines, polls [none_due; NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 1, new A 5 B 1, maker posted 0 filled 1, credits used 12 left 79579, 398s
- 2026-11-09T00:51:50Z: 11 games (5 in 24h), quotes {'prophetx': 482, 'novig': 410, 'kalshi': 796, 'polymarket_us': 560}, 224 unmatched (6 book-games; fuzzy-matched 0), 1218 side/lines, polls [NFL:fast,NBA:fast,NHL:fast; NFL:fast,NBA:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 24 filled 0, credits used 12 left 79605, 301s

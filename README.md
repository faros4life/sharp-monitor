# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-08T03:46:24Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 7469 | 7298 | -1.59c | 23.9% | 3192 | -1.01c | 7015 | 3614-3401-0 | -269.25u | -3.8% |  |  | criteria not met (7015/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1704 | 1625 | -3.13c | 18.2% | 360 | -2.61c | 1576 | 808-768-0 | -132.27u | -8.4% |  |  | criteria not met (1576/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 123 | 123 | -1.01c | 28.5% | 115 | -0.05c | 120 | 53-67-0 | -7.77u | -6.5% |  |  | criteria not met (120/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 72 | 72 | -1.03c | 27.8% | 69 | -0.19c | 70 | 33-37-0 | +0.22u | 0.3% |  |  |  |
| B ref age 5m+ | 42 | 42 | -1.2c | 28.6% | 37 | -0.07c | 41 | 15-26-0 | -9.38u | -22.9% |  |  |  |
| M move-watch: gettable (sightings) | 339 | 330 | -0.62c | 33.9% | 330 | -0.61c | 307 | 155-148-4 | -10.27u | -3.3% | 0.19c | 26s | criteria not met (307/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 176 | 171 | -0.67c | 34.5% | 172 | -0.84c | 157 | 76-78-3 | -8.69u | -5.5% | -0.08c | 28s |  |
| M gettable, price moves | 163 | 159 | -0.56c | 33.3% | 158 | -0.36c | 150 | 79-70-1 | -1.58u | -1.1% | 0.49c | 24s |  |
| M control: not gettable | 1394 | 1107 | -0.81c | 35.7% | 1095 | -1.21c | 1070 | 522-529-19 | -69.97u | -6.5% | 1.78c | 183s |  |
| M all moves | 1733 | 1437 | -0.77c | 35.3% | 1425 | -1.07c | 1377 | 677-677-23 | -80.23u | -5.8% | 1.47c | 119s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1035 | 1031 | 2.73c | 27.1% | 222 | 2.91c | 1030 | 455-575-0 | +279.38u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 75 | 73 | -0.18c | 33-40-0 | -3.88u | 49, -0.43c, -7.23u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 44 | 43 | -0.45c | 22-21-0 | +2.86u | 33, -0.76c, +4.40u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 193 | 166 | -0.68c | 78-86-2 | -12.13u | 97, -0.7c, -14.56u | negative |
| D1 B, unders (descriptive) | 22 | 21 | 0.3c | 13-8-0 | +5.89u | 20, 0.25c, +4.81u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 10 | 9 | 0.42c | 4-5-0 | +0.46u | 8, 0.42c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 60 | 55 | -0.33c | 30-23-2 | -3.66u | 30, -0.39c, -3.93u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1708 | 73 | 4.3% | -0.65c | 1.59c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1706 | 27 | 1.6% | -0.4c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 4435 | 212 | 4.8% | -1.02c | 1.1c | 99-98-4 | +5.63u |  |
| MK prophetx fair-2c | 4408 | 68 | 1.5% | -0.58c | 2.04c | 31-34-0 | -0.37u |  |
| MK all fair-1c | 6143 | 285 | 4.6% | -0.93c | 1.24c | 136-133-4 | +8.72u | criteria not met (273/50 graded, CLV not positive) |
| MK all fair-2c | 6114 | 95 | 1.6% | -0.53c | 2.17c | 47-44-0 | +7.28u | criteria not met (91/50 graded, CLV not positive) |

A and B on the same side/line: 97.

## Odds API credits (100K/month plan)

Study: 647/day, projected 19413/30 days. All monitors on the key: 2192/day, projected 65755/30 days. Remaining 84048; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-08T03:41:23Z: 26 games (26 in 24h), quotes {'prophetx': 2176, 'novig': 722, 'kalshi': 1982, 'polymarket_us': 2894}, 696 unmatched (17 book-games; fuzzy-matched 0), 4165 side/lines, polls [NCAAF:fast; none_due], moves 1, new A 17 B 0, maker posted 0 filled 0, credits used 2 left 84048, 301s
- 2026-11-08T03:31:27Z: 27 games (27 in 24h), quotes {'prophetx': 2176, 'novig': 720, 'kalshi': 2058, 'polymarket_us': 2254}, 618 unmatched (21 book-games; fuzzy-matched 0), 3949 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow,NHL:slow; none_due], moves 2, new A 20 B 0, maker posted 0 filled 0, credits used 8 left 84061, 301s
- 2026-11-08T03:20:59Z: 27 games (27 in 24h), quotes {'prophetx': 2318, 'novig': 670, 'kalshi': 2158, 'polymarket_us': 1490}, 674 unmatched (22 book-games; fuzzy-matched 0), 3702 side/lines, polls [none_due; NCAAF:fast], moves 2, new A 3 B 0, maker posted 4 filled 1, credits used 2 left 84080, 213s
- 2026-11-08T03:11:26Z: 28 games (28 in 24h), quotes {'prophetx': 2222, 'novig': 670, 'kalshi': 2284, 'polymarket_us': 1600}, 736 unmatched (25 book-games; fuzzy-matched 0), 3788 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast], moves 3, new A 12 B 0, maker posted 8 filled 0, credits used 6 left 84095, 302s
- 2026-11-08T03:01:20Z: 29 games (29 in 24h), quotes {'prophetx': 2326, 'novig': 660, 'kalshi': 2344, 'polymarket_us': 1696}, 802 unmatched (24 book-games; fuzzy-matched 0), 3890 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 0, new A 7 B 0, maker posted 5 filled 1, credits used 12 left 84115, 302s
- 2026-11-08T02:51:12Z: 29 games (29 in 24h), quotes {'prophetx': 2470, 'novig': 658, 'kalshi': 2264, 'polymarket_us': 1726}, 894 unmatched (27 book-games; fuzzy-matched 0), 3916 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 84140, 209s
- 2026-11-08T02:45:12Z: 29 games (29 in 24h), quotes {'prophetx': 2470, 'novig': 664, 'kalshi': 2334, 'polymarket_us': 1726}, 932 unmatched (29 book-games; fuzzy-matched 0), 3932 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 6 left 84159, 225s
- 2026-11-08T02:40:54Z: 29 games (29 in 24h), quotes {'prophetx': 2470, 'novig': 664, 'kalshi': 2536, 'polymarket_us': 1840}, 959 unmatched (30 book-games; fuzzy-matched 0), 4064 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 12 filled 0, credits used 6 left 84165, 183s
- 2026-11-08T02:31:30Z: 31 games (31 in 24h), quotes {'prophetx': 2470, 'novig': 668, 'kalshi': 2222, 'polymarket_us': 1400}, 919 unmatched (30 book-games; fuzzy-matched 1), 3812 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 0 filled 0, credits used 14 left 84186, 302s
- 2026-11-08T02:21:25Z: 32 games (32 in 24h), quotes {'prophetx': 2794, 'novig': 658, 'kalshi': 2604, 'polymarket_us': 1936}, 911 unmatched (29 book-games; fuzzy-matched 4), 4442 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 1, new A 40 B 0, maker posted 24 filled 0, credits used 12 left 84217, 301s

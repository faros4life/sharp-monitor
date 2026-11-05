# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T03:13:43Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5562 | 5485 | -1.81c | 23.3% | 2346 | -1.11c | 4948 | 2517-2431-0 | -228.70u | -4.6% |  |  | criteria not met (4948/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1228 | 1221 | -3.75c | 16.4% | 271 | -2.97c | 1152 | 590-562-0 | -89.55u | -7.8% |  |  | criteria not met (1152/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 98 | 98 | -0.79c | 31.6% | 94 | -0.02c | 84 | 33-51-0 | -13.78u | -16.4% |  |  | criteria not met (84/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 57 | 57 | -0.73c | 29.8% | 55 | -0.11c | 51 | 22-29-0 | -3.75u | -7.4% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 27 | 8-19-0 | -10.33u | -38.2% |  |  |  |
| M move-watch: gettable (sightings) | 237 | 235 | -0.72c | 31.5% | 233 | -0.68c | 211 | 110-98-3 | +0.11u | 0.1% | 0.07c | 26s | criteria not met (211/50 graded, CLV not positive) |
| M gettable, line moves | 121 | 120 | -0.78c | 33.3% | 119 | -0.99c | 104 | 53-49-2 | -0.57u | -0.5% | -0.27c | 46s |  |
| M gettable, price moves | 116 | 115 | -0.65c | 29.6% | 114 | -0.36c | 107 | 57-49-1 | +0.68u | 0.6% | 0.42c | 22s |  |
| M control: not gettable | 890 | 721 | -0.89c | 34.3% | 715 | -1.3c | 655 | 338-303-14 | -4.70u | -0.7% | 1.77c | 55s |  |
| M all moves | 1127 | 956 | -0.85c | 33.6% | 948 | -1.14c | 866 | 448-401-17 | -4.60u | -0.5% | 1.41c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 912 | 2.34c | 23.1% | 189 | 1.98c | 887 | 397-490-0 | +277.27u | 31.3% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 43 | -0.14c | 16-27-0 | -9.77u | 30, -0.55c, -5.10u | not enough yet |
| J2 B, NBA | 38 | 30 | 0.01c | 11-19-0 | -7.23u | 18, -0.47c, -1.48u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 27 | -0.39c | 12-15-0 | -2.07u | 20, -0.69c, +2.85u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 106 | 87 | -0.82c | 42-44-1 | -4.16u | 51, -0.97c, -3.31u | negative |
| D1 B, unders (descriptive) | 12 | 9 | 0.71c | 5-4-0 | +1.33u | 9, 0.71c, +1.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 8 | -1.1c | 0-8-0 | -8.00u | 6, -1.51c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 3 | 0.52c | 1-2-0 | +0.33u | 3, 0.53c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 45 | 38 | -0.4c | 21-15-2 | -1.26u | 19, -0.56c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1119 | 51 | 4.6% | -0.49c | 1.6c | 20-26-0 | -5.11u |  |
| MK novig fair-2c | 1121 | 19 | 1.7% | -0.4c | 2.52c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2746 | 134 | 4.9% | -0.86c | 1.1c | 64-56-2 | +11.06u |  |
| MK prophetx fair-2c | 2728 | 38 | 1.4% | -0.6c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3865 | 185 | 4.8% | -0.76c | 1.25c | 84-82-2 | +5.95u | criteria not met (168/50 graded, CLV not positive) |
| MK all fair-2c | 3849 | 57 | 1.5% | -0.53c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 81.

## Odds API credits (100K/month plan)

Study: 620/day, projected 18593/30 days. All monitors on the key: 2105/day, projected 63140/30 days. Remaining 91394; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T03:10:54Z: 16 games (16 in 24h), quotes {'prophetx': 808, 'novig': 664, 'kalshi': 1000, 'polymarket_us': 1090}, 746 unmatched (21 book-games; fuzzy-matched 0), 1407 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 91394, 169s
- 2026-11-05T03:01:01Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 716, 'kalshi': 1068, 'polymarket_us': 1090}, 769 unmatched (18 book-games; fuzzy-matched 0), 1462 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 7 filled 0, credits used 8 left 91398, 301s
- 2026-11-05T02:51:56Z: 18 games (18 in 24h), quotes {'prophetx': 1018, 'novig': 710, 'kalshi': 1190, 'polymarket_us': 1154}, 766 unmatched (20 book-games; fuzzy-matched 0), 1670 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 3, new A 3 B 1, maker posted 1 filled 2, credits used 8 left 91429, 296s
- 2026-11-05T02:46:43Z: 19 games (19 in 24h), quotes {'prophetx': 1008, 'novig': 711, 'kalshi': 1220, 'polymarket_us': 1154}, 723 unmatched (19 book-games; fuzzy-matched 0), 1742 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 91445, 258s
- 2026-11-05T02:40:59Z: 19 games (19 in 24h), quotes {'prophetx': 1008, 'novig': 713, 'kalshi': 1272, 'polymarket_us': 1154}, 773 unmatched (19 book-games; fuzzy-matched 0), 1728 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 4, new A 11 B 0, maker posted 12 filled 0, credits used 8 left 91454, 302s
- 2026-11-05T02:30:59Z: 19 games (18 in 24h), quotes {'prophetx': 1006, 'novig': 707, 'kalshi': 1322, 'polymarket_us': 1154}, 821 unmatched (19 book-games; fuzzy-matched 0), 1748 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 8 filled 0, credits used 12 left 91479, 301s
- 2026-11-05T02:20:55Z: 19 games (18 in 24h), quotes {'prophetx': 1110, 'novig': 716, 'kalshi': 1384, 'polymarket_us': 1256}, 880 unmatched (20 book-games; fuzzy-matched 0), 1847 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 0, credits used 8 left 91507, 301s
- 2026-11-05T02:10:52Z: 21 games (20 in 24h), quotes {'prophetx': 1108, 'novig': 714, 'kalshi': 1416, 'polymarket_us': 1256}, 765 unmatched (18 book-games; fuzzy-matched 0), 1992 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 17 B 0, maker posted 8 filled 0, credits used 6 left 91530, 184s
- 2026-11-05T02:01:05Z: 21 games (20 in 24h), quotes {'prophetx': 1108, 'novig': 710, 'kalshi': 1460, 'polymarket_us': 1256}, 805 unmatched (18 book-games; fuzzy-matched 0), 2022 side/lines, polls [NFL:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 12 B 0, maker posted 16 filled 0, credits used 10 left 91547, 301s
- 2026-11-05T01:50:57Z: 21 games (20 in 24h), quotes {'prophetx': 1254, 'novig': 713, 'kalshi': 1508, 'polymarket_us': 1384}, 727 unmatched (17 book-games; fuzzy-matched 0), 2234 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 21 filled 1, credits used 4 left 91582, 183s

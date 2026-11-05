# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T03:06:03Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5559 | 5439 | -1.81c | 23.4% | 2315 | -1.11c | 4900 | 2494-2406-0 | -223.34u | -4.6% |  |  | criteria not met (4900/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1228 | 1220 | -3.75c | 16.4% | 271 | -2.97c | 1142 | 584-558-0 | -88.24u | -7.7% |  |  | criteria not met (1142/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 98 | 97 | -0.79c | 32.0% | 93 | -0.03c | 83 | 33-50-0 | -12.78u | -15.4% |  |  | criteria not met (83/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 57 | 56 | -0.73c | 30.4% | 54 | -0.13c | 51 | 22-29-0 | -3.75u | -7.4% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 26 | 8-18-0 | -9.33u | -35.9% |  |  |  |
| M move-watch: gettable (sightings) | 237 | 229 | -0.72c | 31.4% | 227 | -0.7c | 208 | 109-96-3 | +1.15u | 0.6% | 0.06c | 26s | criteria not met (208/50 graded, CLV not positive) |
| M gettable, line moves | 121 | 117 | -0.78c | 33.3% | 116 | -1.02c | 102 | 53-47-2 | +1.43u | 1.4% | -0.29c | 46s |  |
| M gettable, price moves | 116 | 112 | -0.66c | 29.5% | 111 | -0.36c | 106 | 56-49-1 | -0.28u | -0.3% | 0.43c | 22s |  |
| M control: not gettable | 890 | 706 | -0.91c | 34.0% | 700 | -1.31c | 647 | 332-301-14 | -7.75u | -1.2% | 1.77c | 55s |  |
| M all moves | 1127 | 935 | -0.86c | 33.4% | 927 | -1.16c | 855 | 441-397-17 | -6.61u | -0.8% | 1.41c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 912 | 2.34c | 23.1% | 189 | 1.98c | 885 | 397-488-0 | +279.27u | 31.6% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 42 | -0.14c | 16-26-0 | -8.77u | 29, -0.55c, -4.10u | not enough yet |
| J2 B, NBA | 38 | 29 | 0.01c | 11-18-0 | -6.23u | 17, -0.47c, -0.48u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 27 | -0.39c | 12-15-0 | -2.07u | 20, -0.69c, +2.85u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 106 | 84 | -0.82c | 41-42-1 | -3.12u | 50, -0.97c, -2.31u | negative |
| D1 B, unders (descriptive) | 12 | 9 | 0.7c | 5-4-0 | +1.33u | 9, 0.7c, +1.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 8 | -1.1c | 0-8-0 | -8.00u | 6, -1.51c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 3 | 0.45c | 1-2-0 | +0.33u | 3, 0.44c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 45 | 38 | -0.46c | 21-15-2 | -1.26u | 19, -0.76c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1119 | 51 | 4.6% | -0.47c | 1.6c | 20-25-0 | -4.11u |  |
| MK novig fair-2c | 1121 | 19 | 1.7% | -0.4c | 2.52c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2746 | 134 | 4.9% | -0.87c | 1.1c | 64-55-2 | +12.06u |  |
| MK prophetx fair-2c | 2728 | 38 | 1.4% | -0.6c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3865 | 185 | 4.8% | -0.76c | 1.25c | 84-80-2 | +7.95u | criteria not met (166/50 graded, CLV not positive) |
| MK all fair-2c | 3849 | 57 | 1.5% | -0.53c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 81.

## Odds API credits (100K/month plan)

Study: 620/day, projected 18601/30 days. All monitors on the key: 2106/day, projected 63178/30 days. Remaining 91398; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T03:01:01Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 716, 'kalshi': 1068, 'polymarket_us': 1090}, 769 unmatched (18 book-games; fuzzy-matched 0), 1462 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 7 filled 0, credits used 8 left 91398, 301s
- 2026-11-05T02:51:56Z: 18 games (18 in 24h), quotes {'prophetx': 1018, 'novig': 710, 'kalshi': 1190, 'polymarket_us': 1154}, 766 unmatched (20 book-games; fuzzy-matched 0), 1670 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 3, new A 3 B 1, maker posted 1 filled 2, credits used 8 left 91429, 296s
- 2026-11-05T02:46:43Z: 19 games (19 in 24h), quotes {'prophetx': 1008, 'novig': 711, 'kalshi': 1220, 'polymarket_us': 1154}, 723 unmatched (19 book-games; fuzzy-matched 0), 1742 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 91445, 258s
- 2026-11-05T02:40:59Z: 19 games (19 in 24h), quotes {'prophetx': 1008, 'novig': 713, 'kalshi': 1272, 'polymarket_us': 1154}, 773 unmatched (19 book-games; fuzzy-matched 0), 1728 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 4, new A 11 B 0, maker posted 12 filled 0, credits used 8 left 91454, 302s
- 2026-11-05T02:30:59Z: 19 games (18 in 24h), quotes {'prophetx': 1006, 'novig': 707, 'kalshi': 1322, 'polymarket_us': 1154}, 821 unmatched (19 book-games; fuzzy-matched 0), 1748 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 8 filled 0, credits used 12 left 91479, 301s
- 2026-11-05T02:20:55Z: 19 games (18 in 24h), quotes {'prophetx': 1110, 'novig': 716, 'kalshi': 1384, 'polymarket_us': 1256}, 880 unmatched (20 book-games; fuzzy-matched 0), 1847 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 0, credits used 8 left 91507, 301s
- 2026-11-05T02:10:52Z: 21 games (20 in 24h), quotes {'prophetx': 1108, 'novig': 714, 'kalshi': 1416, 'polymarket_us': 1256}, 765 unmatched (18 book-games; fuzzy-matched 0), 1992 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 17 B 0, maker posted 8 filled 0, credits used 6 left 91530, 184s
- 2026-11-05T02:01:05Z: 21 games (20 in 24h), quotes {'prophetx': 1108, 'novig': 710, 'kalshi': 1460, 'polymarket_us': 1256}, 805 unmatched (18 book-games; fuzzy-matched 0), 2022 side/lines, polls [NFL:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 1, new A 12 B 0, maker posted 16 filled 0, credits used 10 left 91547, 301s
- 2026-11-05T01:50:57Z: 21 games (20 in 24h), quotes {'prophetx': 1254, 'novig': 713, 'kalshi': 1508, 'polymarket_us': 1384}, 727 unmatched (17 book-games; fuzzy-matched 0), 2234 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 21 filled 1, credits used 4 left 91582, 183s
- 2026-11-05T01:42:23Z: 21 games (20 in 24h), quotes {'prophetx': 1284, 'novig': 717, 'kalshi': 1552, 'polymarket_us': 1384}, 763 unmatched (17 book-games; fuzzy-matched 0), 2244 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 6 left 91586, 241s

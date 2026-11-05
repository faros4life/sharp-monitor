# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T04:23:22Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5570 | 5510 | -1.8c | 23.3% | 2364 | -1.1c | 5309 | 2701-2608-0 | -241.39u | -4.5% |  |  | criteria not met (5309/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1228 | 1221 | -3.75c | 16.4% | 271 | -2.97c | 1204 | 619-585-0 | -86.17u | -7.2% |  |  | criteria not met (1204/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 98 | 98 | -0.79c | 31.6% | 94 | -0.02c | 96 | 38-58-0 | -15.27u | -15.9% |  |  | criteria not met (96/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 8 | 5-3-0 | +2.39u | 29.9% |  |  |  |
| B ref age 1-5m | 57 | 57 | -0.73c | 29.8% | 55 | -0.11c | 55 | 23-32-0 | -5.60u | -10.2% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 237 | 236 | -0.72c | 31.4% | 234 | -0.69c | 225 | 115-107-3 | -4.67u | -2.1% | 0.07c | 26s | criteria not met (225/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 121 | 121 | -0.79c | 33.1% | 120 | -1.0c | 113 | 56-55-2 | -3.83u | -3.4% | -0.27c | 46s |  |
| M gettable, price moves | 116 | 115 | -0.65c | 29.6% | 114 | -0.36c | 112 | 59-52-1 | -0.84u | -0.8% | 0.42c | 22s |  |
| M control: not gettable | 891 | 723 | -0.89c | 34.2% | 717 | -1.29c | 706 | 363-329-14 | -8.80u | -1.2% | 1.77c | 46s |  |
| M all moves | 1128 | 959 | -0.85c | 33.5% | 951 | -1.15c | 931 | 478-436-17 | -13.47u | -1.4% | 1.41c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 912 | 2.34c | 23.1% | 189 | 1.98c | 912 | 403-509-0 | +263.23u | 28.9% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 53 | -0.14c | 20-33-0 | -11.40u | 36, -0.55c, -7.00u | negative |
| J2 B, NBA | 38 | 37 | 0.01c | 14-23-0 | -7.95u | 22, -0.47c, -1.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 31 | -0.39c | 14-17-0 | -1.97u | 24, -0.69c, +2.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 106 | 99 | -0.83c | 46-52-1 | -8.39u | 60, -0.98c, -6.44u | negative |
| D1 B, unders (descriptive) | 12 | 11 | 0.71c | 6-5-0 | +1.48u | 11, 0.71c, +1.48u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 10 | -1.1c | 1-9-0 | -7.81u | 8, -1.51c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 5 | 0.52c | 2-3-0 | +0.48u | 4, 0.53c, -0.67u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 45 | 40 | -0.4c | 22-16-2 | -1.80u | 20, -0.56c, -0.30u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1122 | 51 | 4.5% | -0.49c | 1.6c | 20-29-0 | -8.11u |  |
| MK novig fair-2c | 1123 | 19 | 1.7% | -0.4c | 2.52c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2746 | 134 | 4.9% | -0.86c | 1.1c | 68-60-2 | +11.34u |  |
| MK prophetx fair-2c | 2728 | 38 | 1.4% | -0.6c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 3868 | 185 | 4.8% | -0.76c | 1.25c | 88-89-2 | +3.24u | criteria not met (179/50 graded, CLV not positive) |
| MK all fair-2c | 3851 | 57 | 1.5% | -0.53c | 2.18c | 26-30-0 | -1.47u | criteria not met (56/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 81.

## Odds API credits (100K/month plan)

Study: 619/day, projected 18571/30 days. All monitors on the key: 2105/day, projected 63160/30 days. Remaining 91286; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T04:20:58Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 566, 'kalshi': 662, 'polymarket_us': 962}, 559 unmatched (14 book-games; fuzzy-matched 0), 1111 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 91286, 143s
- 2026-11-05T04:11:06Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 570, 'kalshi': 698, 'polymarket_us': 962}, 595 unmatched (14 book-games; fuzzy-matched 0), 1111 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 91297, 145s
- 2026-11-05T04:01:05Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 566, 'kalshi': 746, 'polymarket_us': 962}, 642 unmatched (16 book-games; fuzzy-matched 0), 1111 side/lines, polls [NFL:slow,NCAAF:slow,NHL:slow], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 91308, 143s
- 2026-11-05T03:50:49Z: 14 games (14 in 24h), quotes {'prophetx': 674, 'novig': 566, 'kalshi': 804, 'polymarket_us': 962}, 701 unmatched (16 book-games; fuzzy-matched 0), 1097 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 91323, 144s
- 2026-11-05T03:41:00Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 572, 'kalshi': 842, 'polymarket_us': 962}, 739 unmatched (17 book-games; fuzzy-matched 0), 1111 side/lines, polls [NFL:slow,NCAAF:slow], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 91332, 146s
- 2026-11-05T03:30:59Z: 15 games (15 in 24h), quotes {'prophetx': 704, 'novig': 660, 'kalshi': 854, 'polymarket_us': 962}, 678 unmatched (16 book-games; fuzzy-matched 0), 1205 side/lines, polls [NBA:fast,NHL:slow; NBA:fast], moves 0, new A 5 B 0, maker posted 4 filled 0, credits used 6 left 91345, 301s
- 2026-11-05T03:20:57Z: 15 games (15 in 24h), quotes {'prophetx': 808, 'novig': 660, 'kalshi': 950, 'polymarket_us': 1090}, 771 unmatched (19 book-games; fuzzy-matched 0), 1331 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 1 B 0, maker posted 1 filled 0, credits used 8 left 91362, 343s
- 2026-11-05T03:10:54Z: 16 games (16 in 24h), quotes {'prophetx': 808, 'novig': 664, 'kalshi': 1000, 'polymarket_us': 1090}, 746 unmatched (21 book-games; fuzzy-matched 0), 1407 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 91394, 169s
- 2026-11-05T03:01:01Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 716, 'kalshi': 1068, 'polymarket_us': 1090}, 769 unmatched (18 book-games; fuzzy-matched 0), 1462 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 7 filled 0, credits used 8 left 91398, 301s
- 2026-11-05T02:51:56Z: 18 games (18 in 24h), quotes {'prophetx': 1018, 'novig': 710, 'kalshi': 1190, 'polymarket_us': 1154}, 766 unmatched (20 book-games; fuzzy-matched 0), 1670 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 3, new A 3 B 1, maker posted 1 filled 2, credits used 8 left 91429, 296s

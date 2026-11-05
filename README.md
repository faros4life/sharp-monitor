# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T05:30:47Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5570 | 5510 | -1.8c | 23.3% | 2364 | -1.1c | 5427 | 2756-2671-0 | -251.68u | -4.6% |  |  | criteria not met (5427/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1228 | 1221 | -3.75c | 16.4% | 271 | -2.97c | 1218 | 625-593-0 | -91.21u | -7.5% |  |  | criteria not met (1218/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 98 | 98 | -0.79c | 31.6% | 94 | -0.02c | 97 | 38-59-0 | -16.27u | -16.8% |  |  | criteria not met (97/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 8 | 5-3-0 | +2.39u | 29.9% |  |  |  |
| B ref age 1-5m | 57 | 57 | -0.73c | 29.8% | 55 | -0.11c | 56 | 23-33-0 | -6.60u | -11.8% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 33 | 10-23-0 | -12.06u | -36.5% |  |  |  |
| M move-watch: gettable (sightings) | 237 | 236 | -0.72c | 31.4% | 234 | -0.69c | 230 | 118-109-3 | -3.97u | -1.7% | 0.07c | 26s | criteria not met (230/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 121 | 121 | -0.79c | 33.1% | 120 | -1.0c | 117 | 59-56-2 | -2.13u | -1.8% | -0.27c | 46s |  |
| M gettable, price moves | 116 | 115 | -0.65c | 29.6% | 114 | -0.36c | 113 | 59-53-1 | -1.84u | -1.6% | 0.42c | 22s |  |
| M control: not gettable | 892 | 723 | -0.89c | 34.2% | 717 | -1.29c | 726 | 368-344-14 | -19.53u | -2.7% | 1.77c | 55s |  |
| M all moves | 1129 | 959 | -0.85c | 33.5% | 951 | -1.15c | 956 | 486-453-17 | -23.50u | -2.5% | 1.41c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 912 | 2.34c | 23.1% | 189 | 1.98c | 913 | 403-510-0 | +262.23u | 28.7% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 54 | -0.14c | 20-34-0 | -12.40u | 37, -0.55c, -8.00u | negative |
| J2 B, NBA | 38 | 38 | 0.01c | 14-24-0 | -8.95u | 23, -0.47c, -2.38u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 32 | -0.39c | 14-18-0 | -2.97u | 25, -0.69c, +1.94u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 106 | 104 | -0.83c | 49-54-1 | -7.69u | 64, -0.98c, -4.74u | negative |
| D1 B, unders (descriptive) | 12 | 11 | 0.71c | 6-5-0 | +1.48u | 11, 0.71c, +1.48u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 10 | -1.1c | 1-9-0 | -7.81u | 8, -1.51c, -5.81u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 5 | 0.52c | 2-3-0 | +0.48u | 4, 0.53c, -0.67u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 45 | 40 | -0.4c | 22-16-2 | -1.80u | 20, -0.56c, -0.30u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1122 | 51 | 4.5% | -0.49c | 1.6c | 21-29-0 | -7.11u |  |
| MK novig fair-2c | 1123 | 19 | 1.7% | -0.4c | 2.52c | 11-8-0 | +4.14u |  |
| MK prophetx fair-1c | 2746 | 134 | 4.9% | -0.86c | 1.1c | 70-61-2 | +12.35u |  |
| MK prophetx fair-2c | 2728 | 38 | 1.4% | -0.6c | 2.04c | 16-22-0 | -4.58u |  |
| MK all fair-1c | 3868 | 185 | 4.8% | -0.76c | 1.25c | 91-90-2 | +5.24u | criteria not met (183/50 graded, CLV not positive) |
| MK all fair-2c | 3851 | 57 | 1.5% | -0.53c | 2.18c | 27-30-0 | -0.43u | criteria not met (57/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 81.

## Odds API credits (100K/month plan)

Study: 616/day, projected 18485/30 days. All monitors on the key: 2097/day, projected 62914/30 days. Remaining 91253; guard holds 70600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T05:30:47Z: outside read hours: closes/grades only
- 2026-11-05T05:20:46Z: outside read hours: closes/grades only
- 2026-11-05T05:10:36Z: outside read hours: closes/grades only
- 2026-11-05T05:00:52Z: outside read hours: closes/grades only
- 2026-11-05T04:50:53Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 564, 'kalshi': 596, 'polymarket_us': 962}, 493 unmatched (12 book-games; fuzzy-matched 0), 1111 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 91253, 143s
- 2026-11-05T04:40:46Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 566, 'kalshi': 626, 'polymarket_us': 962}, 523 unmatched (13 book-games; fuzzy-matched 0), 1111 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 91262, 145s
- 2026-11-05T04:30:58Z: 14 games (14 in 24h), quotes {'prophetx': 674, 'novig': 564, 'kalshi': 640, 'polymarket_us': 962}, 537 unmatched (13 book-games; fuzzy-matched 0), 1103 side/lines, polls [NFL:slow,NCAAF:slow,NHL:slow], moves 1, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 91271, 144s
- 2026-11-05T04:20:58Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 566, 'kalshi': 662, 'polymarket_us': 962}, 559 unmatched (14 book-games; fuzzy-matched 0), 1111 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 91286, 143s
- 2026-11-05T04:11:06Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 570, 'kalshi': 698, 'polymarket_us': 962}, 595 unmatched (14 book-games; fuzzy-matched 0), 1111 side/lines, polls [none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 0 left 91297, 145s
- 2026-11-05T04:01:05Z: 14 games (14 in 24h), quotes {'prophetx': 704, 'novig': 566, 'kalshi': 746, 'polymarket_us': 962}, 642 unmatched (16 book-games; fuzzy-matched 0), 1111 side/lines, polls [NFL:slow,NCAAF:slow,NHL:slow], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 91308, 143s

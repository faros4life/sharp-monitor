# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-07T15:25:50Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 6467 | 6356 | -1.71c | 23.9% | 2775 | -1.07c | 6357 | 3270-3087-0 | -253.46u | -4.0% |  |  | criteria not met (6357/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1370 | 1351 | -3.61c | 16.7% | 306 | -2.92c | 1351 | 694-657-0 | -110.27u | -8.2% |  |  | criteria not met (1351/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 118 | 118 | -0.95c | 29.7% | 110 | -0.08c | 118 | 51-67-0 | -10.26u | -8.7% |  |  | criteria not met (118/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 9 | 9 | 0.06c | 33.3% | 9 | 1.06c | 9 | 5-4-0 | +1.39u | 15.5% |  |  |  |
| B ref age 1-5m | 69 | 69 | -0.98c | 29.0% | 66 | -0.13c | 69 | 32-37-0 | -0.89u | -1.3% |  |  |  |
| B ref age 5m+ | 40 | 40 | -1.13c | 30.0% | 35 | -0.29c | 40 | 14-26-0 | -10.77u | -26.9% |  |  |  |
| M move-watch: gettable (sightings) | 306 | 281 | -0.68c | 32.4% | 278 | -0.67c | 282 | 146-132-4 | -2.15u | -0.8% | 0.12c | 27s | criteria not met (282/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 158 | 143 | -0.76c | 33.6% | 142 | -0.92c | 143 | 71-69-3 | -4.08u | -2.9% | -0.21c | 28s |  |
| M gettable, price moves | 148 | 138 | -0.59c | 31.2% | 136 | -0.4c | 139 | 75-63-1 | +1.93u | 1.4% | 0.46c | 24s |  |
| M control: not gettable | 1206 | 886 | -0.89c | 34.9% | 876 | -1.27c | 911 | 441-454-16 | -66.00u | -7.2% | 1.76c | 184s |  |
| M all moves | 1512 | 1167 | -0.84c | 34.3% | 1154 | -1.12c | 1193 | 587-586-20 | -68.14u | -5.7% | 1.42c | 163s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 953 | 932 | 2.26c | 23.3% | 194 | 1.92c | 933 | 412-521-0 | +270.26u | 29.0% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 71 | 71 | -0.24c | 31-40-0 | -6.38u | 47, -0.54c, -9.72u | negative |
| J2 B, NBA | 50 | 50 | -0.2c | 21-29-0 | -6.28u | 30, -0.55c, -5.23u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 42 | 42 | -0.36c | 21-21-0 | +1.76u | 32, -0.66c, +3.29u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 165 | 144 | -0.75c | 70-72-2 | -5.56u | 82, -0.82c, -7.30u | negative |
| D1 B, unders (descriptive) | 20 | 20 | 0.53c | 12-8-0 | +4.79u | 19, 0.5c, +3.70u | descriptive only |
| D2 B, underdog spreads (descriptive) | 15 | 15 | -0.87c | 4-11-0 | -6.43u | 13, -1.1c, -4.43u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 9 | 9 | 0.44c | 4-5-0 | +0.46u | 8, 0.44c, -0.69u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 55 | 52 | -0.46c | 29-21-2 | -2.11u | 27, -0.67c, -2.38u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1560 | 72 | 4.6% | -0.62c | 1.6c | 37-35-0 | +3.09u |  |
| MK novig fair-2c | 1557 | 26 | 1.7% | -0.37c | 2.52c | 16-10-0 | +7.65u |  |
| MK prophetx fair-1c | 3420 | 166 | 5.0% | -0.95c | 1.11c | 90-73-2 | +21.40u |  |
| MK prophetx fair-2c | 3397 | 50 | 1.5% | -0.56c | 2.04c | 25-24-0 | +3.17u |  |
| MK all fair-1c | 4980 | 238 | 4.9% | -0.85c | 1.27c | 127-108-2 | +24.49u | criteria not met (237/50 graded, CLV not positive) |
| MK all fair-2c | 4954 | 76 | 1.6% | -0.49c | 2.19c | 41-34-0 | +10.82u | criteria not met (75/50 graded, CLV not positive) |

A and B on the same side/line: 96.

## Odds API credits (100K/month plan)

Study: 607/day, projected 18222/30 days. All monitors on the key: 2098/day, projected 62948/30 days. Remaining 86187; guard holds 65400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-07T15:20:49Z: 83 games (71 in 24h), quotes {'prophetx': 6220, 'novig': 667, 'kalshi': 2808, 'polymarket_us': 2090}, 6113 unmatched (112 book-games; fuzzy-matched 4), 2963 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow,NHL:fast; NCAAF:fast,NHL:fast], moves 15, new A 7 B 0, maker posted 4 filled 0, credits used 12 left 86187, 301s
- 2026-11-07T15:11:15Z: 83 games (71 in 24h), quotes {'prophetx': 11484, 'novig': 663, 'kalshi': 2756, 'polymarket_us': 2076}, 6814 unmatched (127 book-games; fuzzy-matched 2), 6446 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 5 B 0, maker posted 16 filled 2, credits used 4 left 86223, 246s
- 2026-11-07T15:06:52Z: 83 games (71 in 24h), quotes {'prophetx': 5164, 'novig': 665, 'kalshi': 2500, 'polymarket_us': 1864}, 5551 unmatched (104 book-games; fuzzy-matched 2), 2587 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 0 B 0, maker posted 96 filled 0, credits used 4 left 86235, 210s
- 2026-11-07T15:01:10Z: 83 games (71 in 24h), quotes {'prophetx': 9472, 'novig': 661, 'kalshi': 3288, 'polymarket_us': 3072}, 7066 unmatched (128 book-games; fuzzy-matched 2), 5407 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 2, new A 8 B 0, maker posted 34 filled 0, credits used 4 left 86250, 240s
- 2026-11-07T14:51:17Z: 83 games (71 in 24h), quotes {'prophetx': 12718, 'novig': 669, 'kalshi': 3698, 'polymarket_us': 3512}, 7825 unmatched (140 book-games; fuzzy-matched 4), 8291 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow,NHL:fast; NCAAF:fast,NHL:fast], moves 10, new A 3 B 0, maker posted 4 filled 0, credits used 12 left 86279, 301s
- 2026-11-07T14:41:16Z: 83 games (71 in 24h), quotes {'prophetx': 11252, 'novig': 664, 'kalshi': 3764, 'polymarket_us': 3544}, 7888 unmatched (140 book-games; fuzzy-matched 2), 6851 side/lines, polls [NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 0, new A 21 B 0, maker posted 0 filled 0, credits used 8 left 86304, 301s
- 2026-11-07T14:30:54Z: 83 games (71 in 24h), quotes {'prophetx': 12406, 'novig': 665, 'kalshi': 2780, 'polymarket_us': 2128}, 6855 unmatched (127 book-games; fuzzy-matched 2), 7342 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 3, new A 1 B 0, maker posted 54 filled 0, credits used 4 left 86325, 238s
- 2026-11-07T14:24:06Z: 83 games (70 in 24h), quotes {'prophetx': 8026, 'novig': 660, 'kalshi': 2446, 'polymarket_us': 1832}, 6137 unmatched (114 book-games; fuzzy-matched 4), 4152 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast,NHL:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 8 left 86344, 208s
- 2026-11-07T14:17:50Z: 83 games (70 in 24h), quotes {'prophetx': 4882, 'novig': 658, 'kalshi': 2292, 'polymarket_us': 1840}, 5555 unmatched (98 book-games; fuzzy-matched 2), 2297 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 3, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 86372, 296s
- 2026-11-07T14:11:29Z: 83 games (70 in 24h), quotes {'prophetx': 11642, 'novig': 668, 'kalshi': 2366, 'polymarket_us': 1872}, 6666 unmatched (125 book-games; fuzzy-matched 2), 6382 side/lines, polls [NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 1, new A 6 B 0, maker posted 0 filled 0, credits used 8 left 86376, 311s

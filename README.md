# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-12T16:43:23Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 9663 | 9405 | -1.62c | 24.4% | 4076 | -1.07c | 9406 | 4895-4511-0 | -287.10u | -3.1% |  |  | criteria not met (9406/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 2187 | 2100 | -3.08c | 19.5% | 470 | -2.73c | 2100 | 1085-1015-0 | -162.54u | -7.7% |  |  | criteria not met (2100/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 168 | 161 | -0.76c | 31.1% | 151 | 0.14c | 161 | 67-94-0 | -18.81u | -11.7% |  |  | criteria not met (161/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 15 | 15 | -0.15c | 26.7% | 15 | 1.01c | 15 | 7-8-0 | -0.37u | -2.5% |  |  |  |
| B ref age 1-5m | 92 | 89 | -0.82c | 31.5% | 85 | 0.05c | 89 | 38-51-0 | -7.87u | -8.8% |  |  |  |
| B ref age 5m+ | 61 | 57 | -0.83c | 31.6% | 51 | 0.04c | 57 | 22-35-0 | -10.57u | -18.5% |  |  |  |
| M move-watch: gettable (sightings) | 445 | 434 | -0.62c | 34.8% | 432 | -0.54c | 438 | 222-211-5 | -8.11u | -1.9% | 0.2c | 28s | criteria not met (438/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 230 | 224 | -0.79c | 34.8% | 223 | -0.82c | 226 | 108-114-4 | -15.80u | -7.0% | -0.19c | 28s |  |
| M gettable, price moves | 215 | 210 | -0.45c | 34.8% | 209 | -0.24c | 212 | 114-97-1 | +7.68u | 3.6% | 0.61c | 26s |  |
| M control: not gettable | 1821 | 1445 | -0.83c | 35.5% | 1413 | -1.25c | 1484 | 740-720-24 | -64.98u | -4.4% | 1.87c | 184s |  |
| M all moves | 2266 | 1879 | -0.78c | 35.3% | 1845 | -1.08c | 1922 | 962-931-29 | -73.10u | -3.8% | 1.54c | 183s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 1104 | 1083 | 2.45c | 27.1% | 232 | 2.44c | 1084 | 488-596-0 | +293.23u | 27.1% | 0.62c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 113 | 107 | 0.13c | 45-62-0 | -12.26u | 73, -0.08c, -14.32u | negative |
| J2 B, NBA | 81 | 75 | 0.3c | 31-44-0 | -9.82u | 47, 0.08c, -7.36u | negative |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 64 | 62 | -0.01c | 27-35-0 | -5.32u | 48, -0.3c, -4.25u | negative |
| J4 Move-watch gettable, all lags (ex-NHL) | 263 | 258 | -0.6c | 123-132-3 | -17.00u | 148, -0.65c, -13.93u | negative |
| D1 B, unders (descriptive) | 39 | 36 | 0.63c | 18-18-0 | +1.54u | 33, 0.63c, +0.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 21 | 21 | -0.24c | 8-13-0 | -3.64u | 19, -0.33c, -1.64u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 16 | 15 | -0.39c | 9-5-1 | +0.53u | 11, -0.59c, +1.67u | descriptive only |
| D4 B, NHL (descriptive) | 17 | 16 | 0.34c | 6-10-0 | -2.21u | 15, 0.33c, -3.36u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 96 | 94 | -0.27c | 52-40-2 | +3.36u | 49, -0.36c, -0.45u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 2484 | 108 | 4.4% | -0.57c | 1.58c | 54-54-0 | +2.40u |  |
| MK novig fair-2c | 2478 | 45 | 1.8% | -0.08c | 2.52c | 25-20-0 | +7.63u |  |
| MK prophetx fair-1c | 5639 | 272 | 4.8% | -1.05c | 1.1c | 129-138-5 | -3.19u |  |
| MK prophetx fair-2c | 5601 | 100 | 1.8% | -0.56c | 2.05c | 47-53-0 | -2.00u |  |
| MK all fair-1c | 8123 | 380 | 4.7% | -0.91c | 1.25c | 183-192-5 | -0.79u | criteria not met (380/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 8079 | 145 | 1.8% | -0.41c | 2.19c | 72-73-0 | +5.63u | criteria not met (145/50 graded, CLV not positive) |

A and B on the same side/line: 137.

## Odds API credits (100K/month plan)

Study: 630/day, projected 18915/30 days. All monitors on the key: 2403/day, projected 72089/30 days. Remaining 70748; guard holds 52400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-12T16:38:21Z: 23 games (18 in 24h), quotes {'prophetx': 1150, 'novig': 693, 'kalshi': 942, 'polymarket_us': 1230}, 28 unmatched (1 book-games; fuzzy-matched 2), 2241 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 70748, 302s
- 2026-11-12T16:26:03Z: 23 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 694, 'kalshi': 942, 'polymarket_us': 1230}, 28 unmatched (1 book-games; fuzzy-matched 2), 2241 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow,NHL:fast; NHL:fast], moves 0, new A 3 B 0, maker posted 12 filled 0, credits used 10 left 70769, 302s
- 2026-11-12T16:12:46Z: 23 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 700, 'kalshi': 938, 'polymarket_us': 1230}, 28 unmatched (1 book-games; fuzzy-matched 2), 2243 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 70810, 301s
- 2026-11-12T16:01:53Z: 21 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 694, 'kalshi': 940, 'polymarket_us': 1230}, 64 unmatched (3 book-games; fuzzy-matched 4), 2206 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow; NHL:fast], moves 2, new A 3 B 0, maker posted 0 filled 0, credits used 8 left 70838, 189s
- 2026-11-12T15:56:49Z: 21 games (18 in 24h), quotes {'prophetx': 1110, 'novig': 698, 'kalshi': 934, 'polymarket_us': 1230}, 64 unmatched (3 book-games; fuzzy-matched 2), 2182 side/lines, polls [none_due; NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 70861, 183s
- 2026-11-12T15:51:00Z: 21 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 699, 'kalshi': 934, 'polymarket_us': 1230}, 64 unmatched (3 book-games; fuzzy-matched 2), 2202 side/lines, polls [none_due; NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 70865, 184s
- 2026-11-12T15:44:11Z: 21 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 697, 'kalshi': 934, 'polymarket_us': 1230}, 64 unmatched (3 book-games; fuzzy-matched 2), 2203 side/lines, polls [none_due; NHL:fast], moves 0, new A 1 B 1, maker posted 0 filled 0, credits used 2 left 70880, 184s
- 2026-11-12T15:38:25Z: 21 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 698, 'kalshi': 936, 'polymarket_us': 0}, 64 unmatched (3 book-games; fuzzy-matched 2), 1729 side/lines, polls [NFL:slow,NCAAF:slow,NBA:slow; NHL:fast], moves 1, new A 5 B 0, maker posted 0 filled 0, credits used 8 left 70882, 183s
- 2026-11-12T15:30:37Z: 21 games (18 in 24h), quotes {'prophetx': 1146, 'novig': 698, 'kalshi': 936, 'polymarket_us': 1230}, 64 unmatched (3 book-games; fuzzy-matched 2), 2205 side/lines, polls [NHL:fast; NHL:fast], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 70901, 301s
- 2026-11-12T15:22:15Z: 21 games (18 in 24h), quotes {'prophetx': 1006, 'novig': 697, 'kalshi': 936, 'polymarket_us': 1230}, 64 unmatched (3 book-games; fuzzy-matched 2), 2133 side/lines, polls [none_due; NHL:fast], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 70931, 182s

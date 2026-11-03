# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-03T04:42:12Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 4927 | 4850 | -1.95c | 22.6% | 1942 | -1.21c | 4685 | 2362-2323-0 | -267.68u | -5.7% |  |  | criteria not met (4685/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1262 | 1227 | -3.79c | 14.9% | 276 | -3.08c | 1190 | 606-584-0 | -95.45u | -8.0% |  |  | criteria not met (1190/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 78 | 78 | -0.79c | 32.1% | 74 | 0.04c | 75 | 31-44-0 | -8.90u | -11.9% |  |  | criteria not met (75/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 48 | 48 | -0.56c | 31.2% | 46 | 0.07c | 46 | 20-26-0 | -2.87u | -6.2% |  |  |  |
| B ref age 5m+ | 25 | 25 | -1.49c | 32.0% | 23 | -0.37c | 24 | 8-16-0 | -7.33u | -30.5% |  |  |  |
| M move-watch: gettable (sightings) | 177 | 177 | -0.71c | 32.8% | 174 | -0.68c | 176 | 89-86-1 | -4.79u | -2.7% | 0.06c | 25s | criteria not met (176/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 94 | 94 | -0.58c | 35.1% | 93 | -0.84c | 93 | 47-45-1 | -1.78u | -1.9% | -0.1c | 28s |  |
| M gettable, price moves | 83 | 83 | -0.87c | 30.1% | 81 | -0.49c | 83 | 42-41-0 | -3.01u | -3.6% | 0.25c | 22s |  |
| M control: not gettable | 732 | 593 | -0.91c | 34.2% | 583 | -1.31c | 587 | 306-270-11 | +1.66u | 0.3% | 1.82c | 28s |  |
| M all moves | 909 | 770 | -0.86c | 33.9% | 757 | -1.17c | 763 | 395-356-12 | -3.13u | -0.4% | 1.47c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 686 | 677 | 3.62c | 27.9% | 128 | 3.72c | 669 | 293-376-0 | +317.05u | 47.4% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 39 | 36 | 0.0c | 14-22-0 | -6.88u | 25, -0.17c, -4.21u | not enough yet |
| J2 B, NBA | 28 | 25 | -0.13c | 9-16-0 | -6.34u | 15, -0.43c, -2.59u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 25 | 23 | -0.01c | 10-13-0 | -2.18u | 17, -0.27c, +1.73u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 77 | 76 | -0.74c | 34-41-1 | -8.82u | 46, -0.92c, -6.17u | negative |
| D1 B, unders (descriptive) | 6 | 6 | 0.63c | 4-2-0 | +2.27u | 6, 0.63c, +2.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 6 | -1.14c | 0-6-0 | -6.00u | 5, -1.69c, -5.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 14 | 14 | -0.49c | 8-6-0 | -1.50u | 9, -0.66c, -0.87u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 736 | 40 | 5.4% | -0.4c | 1.63c | 18-20-0 | -1.23u |  |
| MK novig fair-2c | 738 | 18 | 2.4% | -0.45c | 2.55c | 10-7-0 | +4.10u |  |
| MK prophetx fair-1c | 2225 | 112 | 5.0% | -0.92c | 1.1c | 56-53-2 | +5.55u |  |
| MK prophetx fair-2c | 2209 | 35 | 1.6% | -0.6c | 2.04c | 15-20-0 | -3.70u |  |
| MK all fair-1c | 2961 | 152 | 5.1% | -0.78c | 1.23c | 74-73-2 | +4.32u | criteria not met (149/50 graded, CLV not positive) |
| MK all fair-2c | 2947 | 53 | 1.8% | -0.55c | 2.17c | 25-27-0 | +0.40u | criteria not met (52/50 graded, CLV not positive) |

A and B on the same side/line: 66.

## Odds API credits (100K/month plan)

Study: 635/day, projected 19060/30 days. All monitors on the key: 2155/day, projected 64650/30 days. Remaining 95152; guard holds 78400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-03T04:40:26Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 484, 'polymarket_us': 660}, 150 unmatched (3 book-games; fuzzy-matched 0), 876 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 95152, 105s
- 2026-11-03T04:30:38Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 399, 'kalshi': 502, 'polymarket_us': 660}, 168 unmatched (4 book-games; fuzzy-matched 0), 876 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 95159, 106s
- 2026-11-03T04:20:39Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 387, 'kalshi': 520, 'polymarket_us': 660}, 186 unmatched (5 book-games; fuzzy-matched 0), 874 side/lines, polls [NCAAF:slow,NHL:slow], moves 1, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 95167, 126s
- 2026-11-03T04:10:33Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 399, 'kalshi': 550, 'polymarket_us': 660}, 216 unmatched (6 book-games; fuzzy-matched 0), 874 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 95180, 105s
- 2026-11-03T04:00:44Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 399, 'kalshi': 624, 'polymarket_us': 660}, 290 unmatched (7 book-games; fuzzy-matched 0), 874 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 95189, 105s
- 2026-11-03T03:50:39Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 666, 'polymarket_us': 660}, 332 unmatched (8 book-games; fuzzy-matched 0), 872 side/lines, polls [NCAAF:slow,NHL:slow], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 4 left 95196, 107s
- 2026-11-03T03:40:40Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 403, 'kalshi': 722, 'polymarket_us': 660}, 390 unmatched (9 book-games; fuzzy-matched 0), 872 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 95214, 106s
- 2026-11-03T03:30:33Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 748, 'polymarket_us': 660}, 416 unmatched (10 book-games; fuzzy-matched 0), 872 side/lines, polls [NCAAF:slow,NHL:slow], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 4 left 95221, 105s
- 2026-11-03T03:20:38Z: 13 games (13 in 24h), quotes {'prophetx': 552, 'novig': 401, 'kalshi': 820, 'polymarket_us': 660}, 487 unmatched (12 book-games; fuzzy-matched 0), 874 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 95232, 106s
- 2026-11-03T03:10:37Z: 16 games (16 in 24h), quotes {'prophetx': 552, 'novig': 397, 'kalshi': 896, 'polymarket_us': 660}, 342 unmatched (9 book-games; fuzzy-matched 0), 1096 side/lines, polls [none_due; NBA:fast; none_due], moves 0, new A 1 B 0, maker posted 0 filled 0, credits used 2 left 95239, 404s

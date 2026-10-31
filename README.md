# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T19:46:38Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2773 | 2630 | -2.39c | 21.2% | 1013 | -1.37c | 2143 | 1080-1063-0 | -124.62u | -5.8% |  |  | criteria not met (2143/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 782 | 723 | -4.48c | 13.3% | 166 | -3.35c | 523 | 264-259-0 | -31.89u | -6.1% |  |  | criteria not met (523/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 46 | 43 | -0.79c | 34.9% | 41 | 0.01c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 3 | 3 | 1.12c | 66.7% | 3 | 1.88c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 30 | 28 | -0.53c | 32.1% | 27 | 0.13c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 13 | 12 | -1.87c | 33.3% | 11 | -0.81c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 112 | 98 | -0.65c | 32.7% | 97 | -0.77c | 78 | 44-34-0 | +7.79u | 10.0% | 0.13c | 26s | criteria not met (78/50 graded, CLV not positive) |
| M gettable, line moves | 61 | 54 | -0.54c | 35.2% | 53 | -0.9c | 43 | 24-19-0 | +3.01u | 7.0% | 0.03c | 28s |  |
| M gettable, price moves | 51 | 44 | -0.78c | 29.5% | 44 | -0.61c | 35 | 20-15-0 | +4.78u | 13.7% | 0.26c | 20s |  |
| M control: not gettable | 444 | 288 | -0.76c | 34.7% | 288 | -1.24c | 225 | 122-100-3 | +7.61u | 3.4% | 1.84c | 28s |  |
| M all moves | 556 | 386 | -0.73c | 34.2% | 385 | -1.12c | 303 | 166-134-3 | +15.40u | 5.1% | 1.47c | 27s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 514 | 448 | 2.6c | 26.3% | 92 | 2.04c | 251 | 109-142-0 | +112.11u | 44.7% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 7 | 0 | -0.24c | 0-0-0 | +0.00u | 0, -0.31c, +0.00u | not enough yet |
| J2 B, NBA | 4 | 0 | -1.49c | 0-0-0 | +0.00u | 0, -3.03c, +0.00u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 5 | 0 | -0.26c | 0-0-0 | +0.00u | 0, -0.36c, +0.00u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 21 | 2 | -0.84c | 0-2-0 | -2.00u | 2, -1.2c, -2.00u | not enough yet |
| D1 B, unders (descriptive) | 1 | 0 | 0.76c | 0-0-0 | +0.00u | 0, 0.76c, +0.00u | descriptive only |
| D2 B, underdog spreads (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 0 | 0.36c | 0-0-0 | +0.00u | 0, 0.36c, +0.00u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 5 | 0 | -1.47c | 0-0-0 | +0.00u | 0, -1.47c, +0.00u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 230 | 17 | 7.8% | -0.5c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 227 | 7 | 3.3% | -0.86c | 2.62c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 1231 | 63 | 5.6% | -0.84c | 1.11c | 13-15-0 | -1.42u |  |
| MK prophetx fair-2c | 1220 | 16 | 1.4% | -0.64c | 2.05c | 1-6-0 | -4.95u |  |
| MK all fair-1c | 1461 | 80 | 5.9% | -0.76c | 1.22c | 21-21-0 | +0.83u | criteria not met (42/50 graded, CLV not positive) |
| MK all fair-2c | 1447 | 23 | 1.7% | -0.71c | 2.15c | 5-8-0 | -2.52u | criteria not met (13/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 35.

## Odds API credits (100K/month plan)

Study: 550/day, projected 16497/30 days. All monitors on the key: 2031/day, projected 60918/30 days. Remaining 63076; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T19:40:21Z: 50 games (42 in 24h), quotes {'prophetx': 4336, 'novig': 568, 'kalshi': 3700, 'polymarket_us': 3332}, 3127 unmatched (89 book-games; fuzzy-matched 2), 5550 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 4, new A 15 B 0, maker posted 28 filled 1, credits used 12 left 63076, 377s
- 2026-10-31T19:30:25Z: 57 games (49 in 24h), quotes {'prophetx': 4340, 'novig': 565, 'kalshi': 3666, 'polymarket_us': 3318}, 2749 unmatched (86 book-games; fuzzy-matched 2), 5966 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 5, new A 68 B 0, maker posted 25 filled 1, credits used 8 left 63115, 248s
- 2026-10-31T19:24:00Z: 58 games (50 in 24h), quotes {'prophetx': 5476, 'novig': 656, 'kalshi': 2408, 'polymarket_us': 1751}, 1767 unmatched (74 book-games; fuzzy-matched 2), 5712 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 0, credits used 6 left 63136, 282s
- 2026-10-31T19:18:41Z: 58 games (50 in 24h), quotes {'prophetx': 5466, 'novig': 662, 'kalshi': 3548, 'polymarket_us': 3273}, 2503 unmatched (85 book-games; fuzzy-matched 4), 6358 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 8, new A 98 B 0, maker posted 57 filled 2, credits used 12 left 63143, 301s
- 2026-10-31T19:10:22Z: 59 games (51 in 24h), quotes {'prophetx': 5598, 'novig': 650, 'kalshi': 2352, 'polymarket_us': 1729}, 2225 unmatched (83 book-games; fuzzy-matched 2), 5640 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 26 B 2, maker posted 93 filled 3, credits used 8 left 63169, 231s
- 2026-10-31T19:00:22Z: 62 games (54 in 24h), quotes {'prophetx': 5454, 'novig': 660, 'kalshi': 2516, 'polymarket_us': 1561}, 1799 unmatched (80 book-games; fuzzy-matched 4), 5318 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 39 B 0, maker posted 27 filled 1, credits used 12 left 63188, 303s
- 2026-10-31T18:50:21Z: 63 games (55 in 24h), quotes {'prophetx': 5620, 'novig': 653, 'kalshi': 3746, 'polymarket_us': 3327}, 3759 unmatched (120 book-games; fuzzy-matched 4), 6431 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 2, new A 49 B 0, maker posted 24 filled 1, credits used 6 left 63232, 273s
- 2026-10-31T18:45:59Z: 63 games (55 in 24h), quotes {'prophetx': 6270, 'novig': 655, 'kalshi': 2950, 'polymarket_us': 2196}, 3647 unmatched (117 book-games; fuzzy-matched 4), 6022 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast,NHL:fast], moves 0, new A 5 B 1, maker posted 42 filled 1, credits used 8 left 63244, 185s
- 2026-10-31T18:39:03Z: 63 games (55 in 24h), quotes {'prophetx': 3430, 'novig': 651, 'kalshi': 2704, 'polymarket_us': 1880}, 3401 unmatched (108 book-games; fuzzy-matched 8), 3145 side/lines, polls [NCAAF:fast,NBA:fast,NHL:fast; NCAAF:fast,NBA:fast,NHL:fast], moves 9, new A 13 B 0, maker posted 47 filled 1, credits used 12 left 63265, 392s
- 2026-10-31T18:30:20Z: 63 games (55 in 24h), quotes {'prophetx': 3952, 'novig': 663, 'kalshi': 2602, 'polymarket_us': 1612}, 3476 unmatched (106 book-games; fuzzy-matched 67), 3455 side/lines, polls [none_due; NCAAF:fast,NBA:fast,NHL:fast], moves 3, new A 10 B 0, maker posted 12 filled 1, credits used 6 left 63288, 264s

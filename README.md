# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T13:41:17Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2238 | 1881 | -2.53c | 25.4% | 734 | -1.22c | 1881 | 941-940-0 | -117.27u | -6.2% |  |  | criteria not met (1881/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 563 | 397 | -5.93c | 18.6% | 79 | -3.91c | 397 | 194-203-0 | -31.33u | -7.9% |  |  | criteria not met (397/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 38 | 37 | -0.72c | 37.8% | 35 | 0.03c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 25 | 24 | -0.48c | 33.3% | 23 | 0.22c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 82 | 71 | -0.71c | 35.2% | 70 | -0.69c | 71 | 41-30-0 | +8.93u | 12.6% | 0.22c | 36s | criteria not met (71/50 graded, CLV not positive) |
| M gettable, line moves | 48 | 40 | -0.66c | 37.5% | 39 | -0.89c | 40 | 23-17-0 | +4.09u | 10.2% | 0.09c | 78s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 31 | 18-13-0 | +4.84u | 15.6% | 0.39c | 28s |  |
| M control: not gettable | 323 | 184 | -0.64c | 33.2% | 180 | -1.17c | 189 | 97-89-3 | -3.24u | -1.7% | 1.82c | 164s |  |
| M all moves | 405 | 255 | -0.66c | 33.7% | 250 | -1.03c | 260 | 138-119-3 | +5.69u | 2.2% | 1.45c | 148s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 288 | 145 | -0.09c | 22.1% | 18 | -0.21c | 146 | 69-77-0 | +97.83u | 67.0% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 177 | 14 | 7.9% | -0.47c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 176 | 6 | 3.4% | -0.95c | 2.63c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 513 | 21 | 5.0% | -0.91c | 1.09c | 10-9-0 | +1.49u |  |
| MK prophetx fair-2c | 508 | 6 | 1.5% | -1.98c | 2.06c | 1-4-0 | -2.95u |  |
| MK all fair-1c | 690 | 35 | 5.9% | -0.73c | 1.26c | 18-15-0 | +3.73u | criteria not met (33/50 graded, CLV not positive) |
| MK all fair-2c | 684 | 12 | 2.0% | -1.42c | 2.23c | 5-6-0 | -0.52u | criteria not met (11/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 30.

## Odds API credits (100K/month plan)

Study: 478/day, projected 14355/30 days. All monitors on the key: 1908/day, projected 57226/30 days. Remaining 64049; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T13:36:52Z: 66 games (54 in 24h), quotes {'prophetx': 6952, 'novig': 632, 'kalshi': 2200, 'polymarket_us': 1550}, 3383 unmatched, 5718 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 3 B 1, maker posted 0 filled 0, credits used 4 left 64049, 264s
- 2026-10-31T13:30:23Z: 66 games (54 in 24h), quotes {'prophetx': 7378, 'novig': 644, 'kalshi': 2576, 'polymarket_us': 1950}, 3631 unmatched, 6395 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 5, new A 2 B 0, maker posted 68 filled 1, credits used 10 left 64064, 303s
- 2026-10-31T13:20:21Z: 66 games (54 in 24h), quotes {'prophetx': 7376, 'novig': 646, 'kalshi': 2370, 'polymarket_us': 2226}, 3521 unmatched, 6480 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 2 B 1, maker posted 16 filled 2, credits used 8 left 64085, 349s
- 2026-10-31T13:10:16Z: 66 games (54 in 24h), quotes {'prophetx': 7314, 'novig': 640, 'kalshi': 2910, 'polymarket_us': 2282}, 3614 unmatched, 6712 side/lines, polls [NBA:fast; NCAAF:fast; NBA:fast], moves 6, new A 9 B 0, maker posted 8 filled 0, credits used 6 left 64111, 301s
- 2026-10-31T13:00:26Z: 66 games (54 in 24h), quotes {'prophetx': 7268, 'novig': 640, 'kalshi': 3352, 'polymarket_us': 3160}, 3826 unmatched, 7234 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow; NCAAF:fast], moves 23, new A 46 B 0, maker posted 100 filled 0, credits used 8 left 64128, 308s
- 2026-10-31T12:59:23Z: outside read hours: closes/grades only
- 2026-10-31T12:57:12Z: outside read hours: closes/grades only
- 2026-10-31T12:50:20Z: outside read hours: closes/grades only
- 2026-10-31T12:40:21Z: outside read hours: closes/grades only
- 2026-10-31T12:30:26Z: outside read hours: closes/grades only

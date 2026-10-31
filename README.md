# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T04:40:20Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2188 | 1881 | -2.53c | 25.4% | 734 | -1.22c | 1792 | 892-900-0 | -123.08u | -6.9% |  |  | criteria not met (1792/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 547 | 397 | -5.93c | 18.6% | 79 | -3.91c | 384 | 186-198-0 | -32.90u | -8.6% |  |  | criteria not met (384/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 78 | 71 | -0.71c | 35.2% | 70 | -0.69c | 66 | 39-27-0 | +10.12u | 15.3% | 0.22c | 28s | criteria not met (66/50 graded, CLV not positive) |
| M gettable, line moves | 44 | 40 | -0.66c | 37.5% | 39 | -0.89c | 35 | 21-14-0 | +5.28u | 15.1% | 0.09c | 54s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 31 | 18-13-0 | +4.84u | 15.6% | 0.39c | 28s |  |
| M control: not gettable | 287 | 184 | -0.64c | 33.2% | 180 | -1.17c | 179 | 93-83-3 | -0.79u | -0.4% | 1.82c | 148s |  |
| M all moves | 365 | 255 | -0.66c | 33.7% | 250 | -1.03c | 245 | 132-110-3 | +9.34u | 3.8% | 1.45c | 63s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 275 | 145 | -0.09c | 22.1% | 18 | -0.21c | 138 | 67-71-0 | +97.93u | 71.0% |  |  |  |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 177 | 14 | 7.9% | -0.47c | 1.69c | 8-6-0 | +2.25u |  |
| MK novig fair-2c | 176 | 6 | 3.4% | -0.95c | 2.63c | 4-2-0 | +2.42u |  |
| MK prophetx fair-1c | 417 | 19 | 4.6% | -0.91c | 1.09c | 10-9-0 | +1.49u |  |
| MK prophetx fair-2c | 412 | 5 | 1.2% | -1.98c | 2.06c | 1-4-0 | -2.95u |  |
| MK all fair-1c | 594 | 33 | 5.6% | -0.73c | 1.26c | 18-15-0 | +3.73u | criteria not met (33/50 graded, CLV not positive) |
| MK all fair-2c | 588 | 11 | 1.9% | -1.42c | 2.23c | 5-6-0 | -0.52u | criteria not met (11/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 29.

## Odds API credits (100K/month plan)

Study: 521/day, projected 15622/30 days. All monitors on the key: 2013/day, projected 60403/30 days. Remaining 64403; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T04:40:20Z: outside read hours: closes/grades only
- 2026-10-31T04:30:20Z: outside read hours: closes/grades only
- 2026-10-31T04:24:26Z: outside read hours: closes/grades only
- 2026-10-31T04:20:21Z: outside read hours: closes/grades only
- 2026-10-31T04:16:39Z: outside read hours: closes/grades only
- 2026-10-31T04:10:16Z: outside read hours: closes/grades only
- 2026-10-31T04:00:23Z: outside read hours: closes/grades only
- 2026-10-31T03:50:18Z: 54 games (54 in 24h), quotes {'prophetx': 7030, 'novig': 637, 'kalshi': 2790, 'polymarket_us': 2264}, 3636 unmatched, 6228 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 64403, 191s
- 2026-10-31T03:45:03Z: 53 games (53 in 24h), quotes {'prophetx': 4348, 'novig': 637, 'kalshi': 2822, 'polymarket_us': 2214}, 3601 unmatched, 4271 side/lines, polls [none_due], moves 0, new A 0 B 0, maker posted 0 filled 0, credits used 0 left 64410, 203s
- 2026-10-31T03:40:19Z: 53 games (53 in 24h), quotes {'prophetx': 7030, 'novig': 639, 'kalshi': 2330, 'polymarket_us': 1510}, 3458 unmatched, 5729 side/lines, polls [NCAAF:slow,NBA:slow], moves 2, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 64410, 199s

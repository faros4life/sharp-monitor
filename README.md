# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-04T05:40:46Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5211 | 5045 | -1.92c | 22.7% | 2059 | -1.18c | 5045 | 2564-2481-0 | -256.66u | -5.1% |  |  | criteria not met (5045/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1310 | 1269 | -3.76c | 15.1% | 289 | -3.08c | 1269 | 655-614-0 | -97.83u | -7.7% |  |  | criteria not met (1269/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 82 | 82 | -0.84c | 31.7% | 78 | -0.05c | 82 | 32-50-0 | -13.85u | -16.9% |  |  | criteria not met (82/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 6 | 6 | 0.73c | 50.0% | 6 | 1.64c | 6 | 3-3-0 | +0.29u | 4.9% |  |  |  |
| B ref age 1-5m | 50 | 50 | -0.67c | 30.0% | 48 | -0.1c | 50 | 21-29-0 | -4.81u | -9.6% |  |  |  |
| B ref age 5m+ | 26 | 26 | -1.52c | 30.8% | 24 | -0.37c | 26 | 8-18-0 | -9.33u | -35.9% |  |  |  |
| M move-watch: gettable (sightings) | 206 | 204 | -0.68c | 32.4% | 201 | -0.67c | 204 | 106-95-3 | -0.70u | -0.3% | 0.11c | 26s | criteria not met (204/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 101 | 100 | -0.59c | 36.0% | 99 | -0.88c | 100 | 52-46-2 | +1.51u | 1.5% | -0.11c | 28s |  |
| M gettable, price moves | 105 | 104 | -0.77c | 28.8% | 102 | -0.46c | 104 | 54-49-1 | -2.21u | -2.1% | 0.32c | 22s |  |
| M control: not gettable | 783 | 628 | -0.91c | 34.2% | 619 | -1.3c | 645 | 331-300-14 | -7.61u | -1.2% | 1.78c | 28s |  |
| M all moves | 989 | 832 | -0.86c | 33.8% | 820 | -1.15c | 849 | 437-395-17 | -8.31u | -1.0% | 1.43c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 705 | 693 | 3.69c | 28.0% | 130 | 3.61c | 694 | 299-395-0 | +309.76u | 44.6% | 1.49c | 12s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 41 | 41 | -0.17c | 15-26-0 | -9.83u | 28, -0.42c, -5.16u | not enough yet |
| J2 B, NBA | 28 | 28 | -0.13c | 10-18-0 | -7.29u | 16, -0.43c, -1.54u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 26 | 26 | -0.26c | 11-15-0 | -3.13u | 19, -0.61c, +1.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 82 | 80 | -0.78c | 38-41-1 | -4.96u | 49, -1.0c, -3.31u | negative |
| D1 B, unders (descriptive) | 8 | 8 | 0.61c | 4-4-0 | +0.27u | 8, 0.61c, +0.27u | descriptive only |
| D2 B, underdog spreads (descriptive) | 8 | 8 | -1.14c | 0-8-0 | -8.00u | 6, -1.69c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 3 | 3 | 0.11c | 1-2-0 | +0.33u | 3, 0.11c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 38 | 38 | -0.44c | 21-15-2 | -1.26u | 19, -0.7c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 922 | 44 | 4.8% | -0.48c | 1.61c | 19-25-0 | -5.15u |  |
| MK novig fair-2c | 923 | 18 | 2.0% | -0.45c | 2.53c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2397 | 120 | 5.0% | -0.93c | 1.1c | 63-55-2 | +11.02u |  |
| MK prophetx fair-2c | 2379 | 36 | 1.5% | -0.61c | 2.04c | 16-20-0 | -2.58u |  |
| MK all fair-1c | 3319 | 164 | 4.9% | -0.81c | 1.25c | 82-80-2 | +5.87u | criteria not met (164/50 graded, CLV not positive) |
| MK all fair-2c | 3302 | 54 | 1.6% | -0.56c | 2.18c | 26-28-0 | +0.53u | criteria not met (54/50 graded, CLV not positive) |

A and B on the same side/line: 69.

## Odds API credits (100K/month plan)

Study: 609/day, projected 18258/30 days. All monitors on the key: 2084/day, projected 62515/30 days. Remaining 93434; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-04T05:40:46Z: outside read hours: closes/grades only
- 2026-11-04T05:30:51Z: outside read hours: closes/grades only
- 2026-11-04T05:20:47Z: outside read hours: closes/grades only
- 2026-11-04T05:10:47Z: outside read hours: closes/grades only
- 2026-11-04T05:00:49Z: outside read hours: closes/grades only
- 2026-11-04T04:50:48Z: 21 games (21 in 24h), quotes {'prophetx': 1846, 'novig': 720, 'kalshi': 1312, 'polymarket_us': 2416}, 14 unmatched (1 book-games; fuzzy-matched 2), 3570 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 93434, 182s
- 2026-11-04T04:40:42Z: 21 games (21 in 24h), quotes {'prophetx': 1714, 'novig': 726, 'kalshi': 1328, 'polymarket_us': 2416}, 32 unmatched (2 book-games; fuzzy-matched 2), 3502 side/lines, polls [none_due], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 0 left 93454, 184s
- 2026-11-04T04:30:52Z: 21 games (21 in 24h), quotes {'prophetx': 1846, 'novig': 718, 'kalshi': 1326, 'polymarket_us': 1780}, 30 unmatched (2 book-games; fuzzy-matched 4), 3250 side/lines, polls [NCAAF:slow,NBA:slow,NHL:slow], moves 2, new A 0 B 0, maker posted 0 filled 0, credits used 6 left 93463, 182s
- 2026-11-04T04:20:43Z: 21 games (21 in 24h), quotes {'prophetx': 1846, 'novig': 712, 'kalshi': 1328, 'polymarket_us': 1922}, 34 unmatched (2 book-games; fuzzy-matched 2), 3299 side/lines, polls [none_due], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 0 left 93489, 181s
- 2026-11-04T04:10:49Z: 21 games (21 in 24h), quotes {'prophetx': 1846, 'novig': 718, 'kalshi': 1340, 'polymarket_us': 2322}, 42 unmatched (2 book-games; fuzzy-matched 2), 3396 side/lines, polls [none_due], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 0 left 93498, 182s

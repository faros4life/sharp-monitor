# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-31T05:50:20Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 2188 | 1881 | -2.53c | 25.4% | 734 | -1.22c | 1851 | 925-926-0 | -119.76u | -6.5% |  |  | criteria not met (1851/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 547 | 397 | -5.93c | 18.6% | 79 | -3.91c | 391 | 190-201-0 | -32.17u | -8.2% |  |  | criteria not met (391/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 37 | 37 | -0.72c | 37.8% | 35 | 0.03c | 37 | 16-21-0 | -3.35u | -9.1% |  |  | criteria not met (37/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 2 | 2 | 2.69c | 100.0% | 2 | 2.44c | 2 | 1-1-0 | +0.11u | 5.3% |  |  |  |
| B ref age 1-5m | 24 | 24 | -0.48c | 33.3% | 23 | 0.22c | 24 | 11-13-0 | -0.83u | -3.4% |  |  |  |
| B ref age 5m+ | 11 | 11 | -1.87c | 36.4% | 10 | -0.88c | 11 | 4-7-0 | -2.63u | -23.9% |  |  |  |
| M move-watch: gettable (sightings) | 78 | 71 | -0.71c | 35.2% | 70 | -0.69c | 68 | 40-28-0 | +10.05u | 14.8% | 0.22c | 28s | criteria not met (68/50 graded, CLV not positive) |
| M gettable, line moves | 44 | 40 | -0.66c | 37.5% | 39 | -0.89c | 37 | 22-15-0 | +5.21u | 14.1% | 0.09c | 54s |  |
| M gettable, price moves | 34 | 31 | -0.76c | 32.3% | 31 | -0.44c | 31 | 18-13-0 | +4.84u | 15.6% | 0.39c | 28s |  |
| M control: not gettable | 287 | 184 | -0.64c | 33.2% | 180 | -1.17c | 187 | 95-89-3 | -4.96u | -2.6% | 1.82c | 148s |  |
| M all moves | 365 | 255 | -0.66c | 33.7% | 250 | -1.03c | 255 | 135-117-3 | +5.09u | 2.0% | 1.45c | 63s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 275 | 145 | -0.09c | 22.1% | 18 | -0.21c | 139 | 68-71-0 | +98.53u | 70.9% |  |  |  |

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

Study: 513/day, projected 15400/30 days. All monitors on the key: 1985/day, projected 59544/30 days. Remaining 64403; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-31T05:50:19Z: outside read hours: closes/grades only
- 2026-10-31T05:40:28Z: outside read hours: closes/grades only
- 2026-10-31T05:40:06Z: outside read hours: closes/grades only
- 2026-10-31T05:30:18Z: outside read hours: closes/grades only
- 2026-10-31T05:26:31Z: outside read hours: closes/grades only
- 2026-10-31T05:20:19Z: outside read hours: closes/grades only
- 2026-10-31T05:10:18Z: outside read hours: closes/grades only
- 2026-10-31T05:05:00Z: outside read hours: closes/grades only
- 2026-10-31T05:00:24Z: outside read hours: closes/grades only
- 2026-10-31T04:56:06Z: outside read hours: closes/grades only

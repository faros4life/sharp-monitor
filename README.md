# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T05:00:19Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 684 | 316 | -0.3c | 25.9% | 316 | -0.38c | 261 | 144-117-0 | +32.12u | 12.3% |  |  | criteria not met (261/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 257 | 71 | 1.02c | 18.3% | 71 | 1.51c | 62 | 32-30-0 | +18.39u | 29.7% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 3 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 2 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 11 | 11 | -0.24c | 45.5% | 11 | -0.31c | 9 | 5-4-0 | +0.83u | 9.2% | 0.6c | 26s | criteria not met (9/50 graded, CLV not positive) |
| M gettable, line moves | 4 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 31s |  |
| M gettable, price moves | 7 | 7 | -0.16c | 42.9% | 7 | -0.09c | 5 | 3-2-0 | +1.00u | 20.0% | 0.79c | 26s |  |
| M control: not gettable | 27 | 13 | -1.12c | 15.4% | 15 | -1.57c | 12 | 7-5-0 | +1.50u | 12.5% | 0.87c | 23s |  |
| M all moves | 38 | 24 | -0.72c | 29.2% | 26 | -1.03c | 21 | 12-9-0 | +2.33u | 11.1% | 0.78c | 23s |  |

A and B on the same side/line: 2.

## Odds API credits (100K/month plan)

Study: 722/day, projected 21660/30 days. All monitors on the key: 2611/day, projected 78322/30 days. Remaining 70187; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T05:00:19Z: outside read hours: closes/grades only
- 2026-10-28T04:50:10Z: outside read hours: closes/grades only
- 2026-10-28T04:40:11Z: outside read hours: closes/grades only
- 2026-10-28T04:30:15Z: outside read hours: closes/grades only
- 2026-10-28T04:29:44Z: outside read hours: closes/grades only
- 2026-10-28T04:23:26Z: outside read hours: closes/grades only
- 2026-10-28T04:20:14Z: outside read hours: closes/grades only
- 2026-10-28T04:10:11Z: outside read hours: closes/grades only
- 2026-10-28T04:00:16Z: outside read hours: closes/grades only
- 2026-10-28T03:56:21Z: 14 games (14 in 24h), quotes {'prophetx': 1352, 'novig': 700, 'kalshi': 1080, 'polymarket_us': 1898}, 244 unmatched, 2563 side/lines, polls [none_due], moves 0, new A 1 B 0, credits used 0 left 70187, 181s

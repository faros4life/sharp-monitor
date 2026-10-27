# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-27T23:14:28Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 298 | 39 | 0.18c | 20.5% | 39 | -0.97c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, record not positive) |
| A qualifying (>= 3c) | 79 | 10 | 4.04c | 20.0% | 10 | 2.28c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, record not positive) |
| B Pinnacle (>= 3% EV) | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 8 | 1 | -0.25c | 0.0% | 1 | 0.96c | 0 | 0-0-0 | +0.00u |  | 1.3c | 22s | criteria not met (0/50 graded, record not positive) |
| M gettable, line moves | 4 | 1 | -0.25c | 0.0% | 1 | 0.96c | 0 | 0-0-0 | +0.00u |  | 1.3c | 31s |  |
| M gettable, price moves | 4 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  | 20s |  |
| M control: not gettable | 8 | 1 | -0.5c | 0.0% | 1 | -0.56c | 0 | 0-0-0 | +0.00u |  | 1.11c | 10s |  |
| M all moves | 16 | 2 | -0.38c | 0.0% | 2 | 0.2c | 0 | 0-0-0 | +0.00u |  | 1.21c | 16s |  |

A and B on the same side/line: 0.

## Odds API credits (100K/month plan)

Study: 1093/day, projected 32777/30 days. All monitors on the key: 3903/day, projected 117093/30 days. Remaining 70642; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-27T23:10:11Z: 16 games (10 in 24h), quotes {'prophetx': 592, 'novig': 691, 'kalshi': 1100, 'polymarket_us': 1384}, 72 unmatched, 2135 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 8 B 0, credits used 4 left 70642, 257s
- 2026-10-27T23:00:27Z: 16 games (7 in 24h), quotes {'prophetx': 624, 'novig': 561, 'kalshi': 1110, 'polymarket_us': 1384}, 0 unmatched, 2219 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 26 B 0, credits used 4 left 70746, 289s
- 2026-10-27T22:56:43Z: 15 games (6 in 24h), quotes {'prophetx': 616, 'novig': 565, 'kalshi': 1024, 'polymarket_us': 870}, 0 unmatched, 1814 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, credits used 4 left 70762, 213s
- 2026-10-27T22:50:14Z: 15 games (6 in 24h), quotes {'prophetx': 644, 'novig': 567, 'kalshi': 1022, 'polymarket_us': 870}, 0 unmatched, 1803 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 3, new A 6 B 0, credits used 8 left 70766, 377s
- 2026-10-27T22:40:11Z: 15 games (6 in 24h), quotes {'prophetx': 624, 'novig': 567, 'kalshi': 1014, 'polymarket_us': 870}, 0 unmatched, 1808 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 8 B 0, credits used 4 left 70798, 200s
- 2026-10-27T22:31:44Z: 15 games (6 in 24h), quotes {'prophetx': 592, 'novig': 564, 'kalshi': 958, 'polymarket_us': 870}, 0 unmatched, 1739 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 3 B 0, credits used 4 left 70814, 313s
- 2026-10-27T22:27:11Z: 15 games (6 in 24h), quotes {'prophetx': 608, 'novig': 564, 'kalshi': 956, 'polymarket_us': 870}, 0 unmatched, 1740 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 1, credits used 4 left 70822, 263s
- 2026-10-27T22:22:12Z: 14 games (6 in 24h), quotes {'prophetx': 620, 'novig': 566, 'kalshi': 894, 'polymarket_us': 870}, 0 unmatched, 1684 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 4 B 0, credits used 4 left 70838, 287s
- 2026-10-27T22:19:04Z: 14 games (6 in 24h), quotes {'prophetx': 608, 'novig': 566, 'kalshi': 882, 'polymarket_us': 870}, 0 unmatched, 1650 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 3 B 0, credits used 4 left 70842, 176s
- 2026-10-27T22:10:12Z: 12 games (6 in 24h), quotes {'prophetx': 584, 'novig': 568, 'kalshi': 880, 'polymarket_us': 870}, 0 unmatched, 1655 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 1, new A 7 B 0, credits used 8 left 70856, 301s

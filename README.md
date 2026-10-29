# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T02:52:17Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1265 | 1159 | -3.63c | 22.8% | 1160 | -3.96c | 744 | 367-377-0 | -20.94u | -2.8% |  |  | criteria not met (744/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 412 | 376 | -6.71c | 15.4% | 377 | -7.19c | 217 | 96-121-0 | +3.05u | 1.4% |  |  | criteria not met (217/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 20 | 18 | -0.67c | 33.3% | 18 | -0.34c | 12 | 2-10-0 | -7.59u | -63.2% |  |  | criteria not met (12/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 15 | 15 | -0.9c | 26.7% | 15 | -0.27c | 10 | 2-8-0 | -5.59u | -55.9% |  |  |  |
| B ref age 5m+ | 4 | 2 | -1.25c | 50.0% | 2 | -2.54c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 38 | 35 | -0.69c | 31.4% | 35 | -0.58c | 25 | 15-10-0 | +4.47u | 17.9% | 0.33c | 145s | criteria not met (25/50 graded, CLV not positive) |
| M gettable, line moves | 16 | 14 | -0.61c | 35.7% | 14 | -0.74c | 9 | 5-4-0 | +0.62u | 6.9% | 0.05c | 145s |  |
| M gettable, price moves | 22 | 21 | -0.74c | 28.6% | 21 | -0.47c | 16 | 10-6-0 | +3.85u | 24.1% | 0.51c | 105s |  |
| M control: not gettable | 118 | 90 | -0.91c | 32.2% | 93 | -1.13c | 38 | 26-10-2 | +12.97u | 34.1% | 1.65c | 28s |  |
| M all moves | 156 | 125 | -0.85c | 32.0% | 128 | -0.98c | 63 | 41-20-2 | +17.43u | 27.7% | 1.33c | 28s |  |

A and B on the same side/line: 17.

## Odds API credits (100K/month plan)

Study: 588/day, projected 17648/30 days. All monitors on the key: 2316/day, projected 69479/30 days. Remaining 68193; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T02:50:12Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 492, 'kalshi': 542, 'polymarket_us': 946}, 202 unmatched, 1157 side/lines, polls [NFL:slow], moves 0, new A 3 B 0, credits used 2 left 68193, 125s
- 2026-10-29T02:41:16Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 498, 'kalshi': 562, 'polymarket_us': 946}, 223 unmatched, 1160 side/lines, polls [NCAAF:slow], moves 0, new A 2 B 0, credits used 2 left 68206, 126s
- 2026-10-29T02:36:15Z: 7 games (7 in 24h), quotes {'prophetx': 358, 'novig': 481, 'kalshi': 598, 'polymarket_us': 946}, 184 unmatched, 1227 side/lines, polls [none_due; none_due], moves 0, new A 14 B 0, credits used 0 left 68217, 288s
- 2026-10-29T02:31:15Z: 7 games (7 in 24h), quotes {'prophetx': 358, 'novig': 539, 'kalshi': 604, 'polymarket_us': 946}, 209 unmatched, 1237 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 68217, 288s
- 2026-10-29T02:28:45Z: 7 games (7 in 24h), quotes {'prophetx': 434, 'novig': 536, 'kalshi': 604, 'polymarket_us': 1078}, 212 unmatched, 1312 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 3 B 0, credits used 4 left 68223, 138s
- 2026-10-29T02:20:12Z: 7 games (7 in 24h), quotes {'prophetx': 434, 'novig': 531, 'kalshi': 668, 'polymarket_us': 1078}, 278 unmatched, 1311 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 5 B 0, credits used 6 left 68236, 301s
- 2026-10-29T02:10:12Z: 7 games (7 in 24h), quotes {'prophetx': 434, 'novig': 541, 'kalshi': 738, 'polymarket_us': 1078}, 353 unmatched, 1312 side/lines, polls [none_due; NBA:fast], moves 0, new A 10 B 0, credits used 2 left 68260, 136s
- 2026-10-29T02:02:32Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 462, 'kalshi': 762, 'polymarket_us': 1078}, 523 unmatched, 1173 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 6 B 0, credits used 4 left 68273, 277s
- 2026-10-29T01:57:21Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 459, 'kalshi': 794, 'polymarket_us': 948}, 549 unmatched, 1106 side/lines, polls [none_due; NBA:fast], moves 1, new A 1 B 0, credits used 2 left 68277, 300s
- 2026-10-29T01:52:21Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 466, 'kalshi': 830, 'polymarket_us': 948}, 589 unmatched, 1109 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 1 B 0, credits used 4 left 68288, 287s

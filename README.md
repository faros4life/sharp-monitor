# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T03:32:31Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1274 | 1159 | -3.63c | 22.8% | 1160 | -3.96c | 978 | 491-487-0 | -12.69u | -1.3% |  |  | criteria not met (978/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 415 | 376 | -6.71c | 15.4% | 377 | -7.19c | 308 | 149-159-0 | +21.52u | 7.0% |  |  | criteria not met (308/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 20 | 18 | -0.67c | 33.3% | 18 | -0.34c | 16 | 4-12-0 | -7.42u | -46.4% |  |  | criteria not met (16/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 1-5m | 15 | 15 | -0.9c | 26.7% | 15 | -0.27c | 13 | 4-9-0 | -4.42u | -34.0% |  |  |  |
| B ref age 5m+ | 4 | 2 | -1.25c | 50.0% | 2 | -2.54c | 2 | 0-2-0 | -2.00u | -100.0% |  |  |  |
| M move-watch: gettable (sightings) | 38 | 35 | -0.69c | 31.4% | 35 | -0.58c | 31 | 17-14-0 | +2.32u | 7.5% | 0.33c | 145s | criteria not met (31/50 graded, CLV not positive) |
| M gettable, line moves | 16 | 14 | -0.61c | 35.7% | 14 | -0.74c | 11 | 6-5-0 | +0.51u | 4.6% | 0.05c | 145s |  |
| M gettable, price moves | 22 | 21 | -0.74c | 28.6% | 21 | -0.47c | 20 | 11-9-0 | +1.81u | 9.0% | 0.51c | 105s |  |
| M control: not gettable | 118 | 90 | -0.91c | 32.2% | 93 | -1.13c | 69 | 39-28-2 | +6.24u | 9.0% | 1.65c | 28s |  |
| M all moves | 156 | 125 | -0.85c | 32.0% | 128 | -0.98c | 100 | 56-42-2 | +8.55u | 8.6% | 1.33c | 28s |  |

A and B on the same side/line: 17.

## Odds API credits (100K/month plan)

Study: 583/day, projected 17504/30 days. All monitors on the key: 2317/day, projected 69514/30 days. Remaining 68127; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T03:30:16Z: 6 games (6 in 24h), quotes {'prophetx': 604, 'novig': 533, 'kalshi': 480, 'polymarket_us': 948}, 143 unmatched, 1174 side/lines, polls [NCAAF:slow], moves 0, new A 3 B 0, credits used 2 left 68127, 136s
- 2026-10-29T03:21:43Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 530, 'kalshi': 488, 'polymarket_us': 948}, 148 unmatched, 1166 side/lines, polls [NBA:slow], moves 0, new A 0 B 0, credits used 2 left 68140, 133s
- 2026-10-29T03:19:18Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 516, 'kalshi': 486, 'polymarket_us': 948}, 147 unmatched, 1164 side/lines, polls [none_due], moves 0, new A 1 B 0, credits used 0 left 68151, 131s
- 2026-10-29T03:16:52Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 525, 'kalshi': 486, 'polymarket_us': 948}, 149 unmatched, 1162 side/lines, polls [NFL:slow], moves 0, new A 2 B 0, credits used 2 left 68151, 132s
- 2026-10-29T03:10:11Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 519, 'kalshi': 500, 'polymarket_us': 948}, 161 unmatched, 1167 side/lines, polls [NCAAF:slow], moves 0, new A 3 B 0, credits used 2 left 68162, 130s
- 2026-10-29T03:00:17Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 493, 'kalshi': 532, 'polymarket_us': 948}, 191 unmatched, 1164 side/lines, polls [NBA:slow], moves 0, new A 0 B 0, credits used 2 left 68173, 124s
- 2026-10-29T02:50:12Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 492, 'kalshi': 542, 'polymarket_us': 946}, 202 unmatched, 1157 side/lines, polls [NFL:slow], moves 0, new A 3 B 0, credits used 2 left 68193, 125s
- 2026-10-29T02:41:16Z: 6 games (6 in 24h), quotes {'prophetx': 358, 'novig': 498, 'kalshi': 562, 'polymarket_us': 946}, 223 unmatched, 1160 side/lines, polls [NCAAF:slow], moves 0, new A 2 B 0, credits used 2 left 68206, 126s
- 2026-10-29T02:36:15Z: 7 games (7 in 24h), quotes {'prophetx': 358, 'novig': 481, 'kalshi': 598, 'polymarket_us': 946}, 184 unmatched, 1227 side/lines, polls [none_due; none_due], moves 0, new A 14 B 0, credits used 0 left 68217, 288s
- 2026-10-29T02:31:15Z: 7 games (7 in 24h), quotes {'prophetx': 358, 'novig': 539, 'kalshi': 604, 'polymarket_us': 946}, 209 unmatched, 1237 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 68217, 288s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T03:33:17Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 675 | 316 | -0.3c | 25.9% | 316 | -0.38c | 261 | 144-117-0 | +32.12u | 12.3% |  |  | criteria not met (261/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 253 | 71 | 1.02c | 18.3% | 71 | 1.51c | 62 | 32-30-0 | +18.39u | 29.7% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 3 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 2 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 11 | 11 | -0.24c | 45.5% | 11 | -0.31c | 9 | 5-4-0 | +0.83u | 9.2% | 0.6c | 26s | criteria not met (9/50 graded, CLV not positive) |
| M gettable, line moves | 4 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 31s |  |
| M gettable, price moves | 7 | 7 | -0.16c | 42.9% | 7 | -0.09c | 5 | 3-2-0 | +1.00u | 20.0% | 0.79c | 26s |  |
| M control: not gettable | 26 | 13 | -1.12c | 15.4% | 15 | -1.57c | 12 | 7-5-0 | +1.50u | 12.5% | 0.87c | 23s |  |
| M all moves | 37 | 24 | -0.72c | 29.2% | 26 | -1.03c | 21 | 12-9-0 | +2.33u | 11.1% | 0.78c | 23s |  |

A and B on the same side/line: 2.

## Odds API credits (100K/month plan)

Study: 851/day, projected 25523/30 days. All monitors on the key: 3025/day, projected 90738/30 days. Remaining 70218; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T03:30:14Z: 14 games (14 in 24h), quotes {'prophetx': 1376, 'novig': 696, 'kalshi': 1098, 'polymarket_us': 1738}, 248 unmatched, 2446 side/lines, polls [none_due], moves 0, new A 4 B 0, credits used 0 left 70218, 182s
- 2026-10-28T03:20:10Z: 14 games (14 in 24h), quotes {'prophetx': 1286, 'novig': 698, 'kalshi': 1116, 'polymarket_us': 1896}, 266 unmatched, 2514 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 70233, 181s
- 2026-10-28T03:15:52Z: 14 games (14 in 24h), quotes {'prophetx': 1242, 'novig': 702, 'kalshi': 1114, 'polymarket_us': 1896}, 264 unmatched, 2514 side/lines, polls [none_due], moves 0, new A 2 B 0, credits used 0 left 70233, 184s
- 2026-10-28T03:10:26Z: 15 games (15 in 24h), quotes {'prophetx': 1250, 'novig': 698, 'kalshi': 1116, 'polymarket_us': 1894}, 190 unmatched, 2538 side/lines, polls [NCAAF:slow,NBA:fast], moves 3, new A 0 B 0, credits used 4 left 70235, 183s
- 2026-10-28T03:06:18Z: 15 games (15 in 24h), quotes {'prophetx': 1258, 'novig': 704, 'kalshi': 1118, 'polymarket_us': 1894}, 192 unmatched, 2539 side/lines, polls [none_due; none_due], moves 0, new A 7 B 0, credits used 0 left 70246, 238s
- 2026-10-28T03:00:15Z: 15 games (15 in 24h), quotes {'prophetx': 1252, 'novig': 710, 'kalshi': 1128, 'polymarket_us': 1894}, 204 unmatched, 2543 side/lines, polls [NBA:fast; NBA:fast], moves 0, new A 17 B 1, credits used 4 left 70246, 301s
- 2026-10-28T02:50:11Z: 15 games (15 in 24h), quotes {'prophetx': 1326, 'novig': 709, 'kalshi': 1124, 'polymarket_us': 2022}, 207 unmatched, 2592 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 3, new A 6 B 0, credits used 6 left 70259, 374s
- 2026-10-28T02:40:11Z: 15 games (15 in 24h), quotes {'prophetx': 1242, 'novig': 703, 'kalshi': 1144, 'polymarket_us': 1782}, 234 unmatched, 2441 side/lines, polls [none_due; NBA:fast], moves 0, new A 8 B 0, credits used 2 left 70278, 182s
- 2026-10-28T02:33:24Z: 15 games (14 in 24h), quotes {'prophetx': 1218, 'novig': 708, 'kalshi': 1144, 'polymarket_us': 2022}, 236 unmatched, 2546 side/lines, polls [none_due; NBA:fast], moves 4, new A 8 B 1, credits used 2 left 70289, 357s
- 2026-10-28T02:29:56Z: 15 games (14 in 24h), quotes {'prophetx': 1216, 'novig': 711, 'kalshi': 1144, 'polymarket_us': 1640}, 242 unmatched, 2348 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 70291, 196s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T03:13:30Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 667 | 316 | -0.3c | 25.9% | 316 | -0.38c | 206 | 117-89-0 | +23.66u | 11.5% |  |  | criteria not met (206/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 250 | 71 | 1.02c | 18.3% | 71 | 1.51c | 37 | 20-17-0 | +11.43u | 30.9% |  |  | criteria not met (37/50 graded) |
| B Pinnacle (>= 3% EV) | 3 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 2 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 11 | 11 | -0.24c | 45.5% | 11 | -0.31c | 3 | 2-1-0 | +0.90u | 30.1% | 0.6c | 26s | criteria not met (3/50 graded, CLV not positive) |
| M gettable, line moves | 4 | 4 | -0.38c | 50.0% | 4 | -0.69c | 2 | 1-1-0 | -0.06u | -2.9% | 0.29c | 31s |  |
| M gettable, price moves | 7 | 7 | -0.16c | 42.9% | 7 | -0.09c | 1 | 1-0-0 | +0.96u | 96.1% | 0.79c | 26s |  |
| M control: not gettable | 26 | 12 | -1.03c | 16.7% | 14 | -1.41c | 8 | 4-4-0 | -0.28u | -3.5% | 0.86c | 23s |  |
| M all moves | 37 | 23 | -0.65c | 30.4% | 25 | -0.93c | 11 | 6-5-0 | +0.63u | 5.7% | 0.76c | 23s |  |

A and B on the same side/line: 2.

## Odds API credits (100K/month plan)

Study: 889/day, projected 26670/30 days. All monitors on the key: 3105/day, projected 93149/30 days. Remaining 70235; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T03:10:26Z: 15 games (15 in 24h), quotes {'prophetx': 1250, 'novig': 698, 'kalshi': 1116, 'polymarket_us': 1894}, 190 unmatched, 2538 side/lines, polls [NCAAF:slow,NBA:fast], moves 3, new A 0 B 0, credits used 4 left 70235, 183s
- 2026-10-28T03:06:18Z: 15 games (15 in 24h), quotes {'prophetx': 1258, 'novig': 704, 'kalshi': 1118, 'polymarket_us': 1894}, 192 unmatched, 2539 side/lines, polls [none_due; none_due], moves 0, new A 7 B 0, credits used 0 left 70246, 238s
- 2026-10-28T03:00:15Z: 15 games (15 in 24h), quotes {'prophetx': 1252, 'novig': 710, 'kalshi': 1128, 'polymarket_us': 1894}, 204 unmatched, 2543 side/lines, polls [NBA:fast; NBA:fast], moves 0, new A 17 B 1, credits used 4 left 70246, 301s
- 2026-10-28T02:50:11Z: 15 games (15 in 24h), quotes {'prophetx': 1326, 'novig': 709, 'kalshi': 1124, 'polymarket_us': 2022}, 207 unmatched, 2592 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 3, new A 6 B 0, credits used 6 left 70259, 374s
- 2026-10-28T02:40:11Z: 15 games (15 in 24h), quotes {'prophetx': 1242, 'novig': 703, 'kalshi': 1144, 'polymarket_us': 1782}, 234 unmatched, 2441 side/lines, polls [none_due; NBA:fast], moves 0, new A 8 B 0, credits used 2 left 70278, 182s
- 2026-10-28T02:33:24Z: 15 games (14 in 24h), quotes {'prophetx': 1218, 'novig': 708, 'kalshi': 1144, 'polymarket_us': 2022}, 236 unmatched, 2546 side/lines, polls [none_due; NBA:fast], moves 4, new A 8 B 1, credits used 2 left 70289, 357s
- 2026-10-28T02:29:56Z: 15 games (14 in 24h), quotes {'prophetx': 1216, 'novig': 711, 'kalshi': 1144, 'polymarket_us': 1640}, 242 unmatched, 2348 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 70291, 196s
- 2026-10-28T02:24:25Z: 15 games (14 in 24h), quotes {'prophetx': 1204, 'novig': 715, 'kalshi': 1156, 'polymarket_us': 1896}, 256 unmatched, 2472 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 1 B 0, credits used 4 left 70300, 228s
- 2026-10-28T02:20:10Z: 15 games (14 in 24h), quotes {'prophetx': 1232, 'novig': 717, 'kalshi': 1178, 'polymarket_us': 1896}, 278 unmatched, 2484 side/lines, polls [none_due; NBA:fast], moves 0, new A 20 B 0, credits used 2 left 70311, 182s
- 2026-10-28T02:10:12Z: 15 games (14 in 24h), quotes {'prophetx': 1232, 'novig': 723, 'kalshi': 1194, 'polymarket_us': 1596}, 308 unmatched, 2309 side/lines, polls [NBA:fast; NBA:fast], moves 1, new A 17 B 0, credits used 4 left 70320, 301s

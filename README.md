# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T03:05:16Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 660 | 261 | -0.23c | 22.6% | 261 | -0.35c | 99 | 58-41-0 | +27.89u | 28.2% |  |  | criteria not met (99/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 248 | 62 | 1.23c | 12.9% | 62 | 1.77c | 26 | 16-10-0 | +16.04u | 61.7% |  |  | criteria not met (26/50 graded) |
| B Pinnacle (>= 3% EV) | 3 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  | criteria not met (0/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 2 | 1 | -2.12c | 0.0% | 1 | -0.5c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 5m+ | 0 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 11 | 9 | -0.29c | 44.4% | 9 | -0.38c | 2 | 1-1-0 | -0.04u | -2.0% | 0.61c | 26s | criteria not met (2/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 4 | 4 | -0.38c | 50.0% | 4 | -0.69c | 1 | 0-1-0 | -1.00u | -100.0% | 0.29c | 31s |  |
| M gettable, price moves | 7 | 5 | -0.23c | 40.0% | 5 | -0.13c | 1 | 1-0-0 | +0.96u | 96.1% | 0.87c | 26s |  |
| M control: not gettable | 23 | 10 | -0.91c | 10.0% | 12 | -1.38c | 6 | 3-3-0 | -0.17u | -2.9% | 0.94c | 16s |  |
| M all moves | 34 | 19 | -0.62c | 26.3% | 21 | -0.95c | 8 | 4-4-0 | -0.21u | -2.6% | 0.8c | 20s |  |

A and B on the same side/line: 2.

## Odds API credits (100K/month plan)

Study: 897/day, projected 26900/30 days. All monitors on the key: 3142/day, projected 94249/30 days. Remaining 70246; guard holds 16000 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T03:00:15Z: 15 games (15 in 24h), quotes {'prophetx': 1252, 'novig': 710, 'kalshi': 1128, 'polymarket_us': 1894}, 204 unmatched, 2543 side/lines, polls [NBA:fast; NBA:fast], moves 0, new A 17 B 1, credits used 4 left 70246, 301s
- 2026-10-28T02:50:11Z: 15 games (15 in 24h), quotes {'prophetx': 1326, 'novig': 709, 'kalshi': 1124, 'polymarket_us': 2022}, 207 unmatched, 2592 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 3, new A 6 B 0, credits used 6 left 70259, 374s
- 2026-10-28T02:40:11Z: 15 games (15 in 24h), quotes {'prophetx': 1242, 'novig': 703, 'kalshi': 1144, 'polymarket_us': 1782}, 234 unmatched, 2441 side/lines, polls [none_due; NBA:fast], moves 0, new A 8 B 0, credits used 2 left 70278, 182s
- 2026-10-28T02:33:24Z: 15 games (14 in 24h), quotes {'prophetx': 1218, 'novig': 708, 'kalshi': 1144, 'polymarket_us': 2022}, 236 unmatched, 2546 side/lines, polls [none_due; NBA:fast], moves 4, new A 8 B 1, credits used 2 left 70289, 357s
- 2026-10-28T02:29:56Z: 15 games (14 in 24h), quotes {'prophetx': 1216, 'novig': 711, 'kalshi': 1144, 'polymarket_us': 1640}, 242 unmatched, 2348 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 70291, 196s
- 2026-10-28T02:24:25Z: 15 games (14 in 24h), quotes {'prophetx': 1204, 'novig': 715, 'kalshi': 1156, 'polymarket_us': 1896}, 256 unmatched, 2472 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 1 B 0, credits used 4 left 70300, 228s
- 2026-10-28T02:20:10Z: 15 games (14 in 24h), quotes {'prophetx': 1232, 'novig': 717, 'kalshi': 1178, 'polymarket_us': 1896}, 278 unmatched, 2484 side/lines, polls [none_due; NBA:fast], moves 0, new A 20 B 0, credits used 2 left 70311, 182s
- 2026-10-28T02:10:12Z: 15 games (14 in 24h), quotes {'prophetx': 1232, 'novig': 723, 'kalshi': 1194, 'polymarket_us': 1596}, 308 unmatched, 2309 side/lines, polls [NBA:fast; NBA:fast], moves 1, new A 17 B 0, credits used 4 left 70320, 301s
- 2026-10-28T02:00:15Z: 15 games (14 in 24h), quotes {'prophetx': 1220, 'novig': 716, 'kalshi': 1220, 'polymarket_us': 1896}, 346 unmatched, 2435 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 2 B 0, credits used 4 left 70333, 184s
- 2026-10-28T01:53:24Z: 15 games (14 in 24h), quotes {'prophetx': 1230, 'novig': 713, 'kalshi': 1238, 'polymarket_us': 1896}, 364 unmatched, 2455 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 70344, 290s

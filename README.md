# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T23:50:22Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1111 | 743 | -3.27c | 23.7% | 744 | -3.58c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 379 | 216 | -5.7c | 17.1% | 217 | -6.12c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria not met (71/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 19 | 12 | -1.08c | 33.3% | 12 | -0.83c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 15 | 10 | -1.04c | 30.0% | 10 | -0.49c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 3 | 2 | -1.25c | 50.0% | 2 | -2.54c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 33 | 25 | -0.51c | 36.0% | 25 | -0.39c | 11 | 6-5-0 | +0.85u | 7.7% | 0.52c | 91s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 12 | 9 | -0.95c | 33.3% | 9 | -1.04c | 4 | 2-2-0 | -0.17u | -4.3% | -0.23c | 137s |  |
| M gettable, price moves | 21 | 16 | -0.26c | 37.5% | 16 | -0.02c | 7 | 4-3-0 | +1.02u | 14.6% | 0.94c | 49s |  |
| M control: not gettable | 109 | 36 | -0.45c | 33.3% | 38 | -0.83c | 15 | 9-6-0 | +2.19u | 14.6% | 1.8c | 28s |  |
| M all moves | 142 | 61 | -0.47c | 34.4% | 63 | -0.65c | 26 | 15-11-0 | +3.04u | 11.7% | 1.35c | 28s |  |

A and B on the same side/line: 16.

## Odds API credits (100K/month plan)

Study: 575/day, projected 17264/30 days. All monitors on the key: 2270/day, projected 68103/30 days. Remaining 68542; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T23:46:23Z: 12 games (10 in 24h), quotes {'prophetx': 1102, 'novig': 695, 'kalshi': 1274, 'polymarket_us': 1442}, 577 unmatched, 2192 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 9 B 0, credits used 4 left 68542, 239s
- 2026-10-28T23:40:33Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 702, 'kalshi': 1288, 'polymarket_us': 1442}, 513 unmatched, 2219 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 3, new A 10 B 2, credits used 6 left 68548, 338s
- 2026-10-28T23:35:34Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 698, 'kalshi': 1308, 'polymarket_us': 1442}, 527 unmatched, 2228 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 11 B 0, credits used 4 left 68564, 288s
- 2026-10-28T23:30:16Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 696, 'kalshi': 1314, 'polymarket_us': 1442}, 537 unmatched, 2241 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 16 B 0, credits used 8 left 68583, 306s
- 2026-10-28T23:20:13Z: 13 games (9 in 24h), quotes {'prophetx': 942, 'novig': 704, 'kalshi': 1324, 'polymarket_us': 1216}, 551 unmatched, 2013 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, credits used 6 left 68614, 184s
- 2026-10-28T23:13:26Z: 13 games (9 in 24h), quotes {'prophetx': 934, 'novig': 697, 'kalshi': 1330, 'polymarket_us': 1216}, 558 unmatched, 2016 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 10 B 1, credits used 4 left 68622, 380s
- 2026-10-28T23:10:12Z: 17 games (13 in 24h), quotes {'prophetx': 934, 'novig': 695, 'kalshi': 1328, 'polymarket_us': 1216}, 254 unmatched, 2312 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 24 B 0, credits used 4 left 68636, 182s
- 2026-10-28T23:02:13Z: 17 games (13 in 24h), quotes {'prophetx': 934, 'novig': 693, 'kalshi': 1332, 'polymarket_us': 1216}, 256 unmatched, 2380 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 8 B 0, credits used 4 left 68652, 216s
- 2026-10-28T22:57:46Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 695, 'kalshi': 1346, 'polymarket_us': 1918}, 182 unmatched, 2993 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 4, new A 5 B 1, credits used 6 left 68656, 256s
- 2026-10-28T22:50:11Z: 18 games (14 in 24h), quotes {'prophetx': 1452, 'novig': 701, 'kalshi': 1350, 'polymarket_us': 1918}, 184 unmatched, 2981 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 4 B 0, credits used 8 left 68674, 301s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T00:08:23Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1157 | 782 | -3.17c | 24.0% | 783 | -3.53c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 389 | 228 | -5.52c | 17.1% | 229 | -5.93c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria not met (71/50 graded, CLV not positive) |
| B Pinnacle (>= 3% EV) | 19 | 13 | -0.99c | 38.5% | 13 | -0.58c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 15 | 11 | -0.94c | 36.4% | 11 | -0.23c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 3 | 2 | -1.25c | 50.0% | 2 | -2.54c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 34 | 27 | -0.54c | 33.3% | 27 | -0.42c | 11 | 6-5-0 | +0.85u | 7.7% | 0.52c | 70s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 13 | 9 | -0.95c | 33.3% | 9 | -1.04c | 4 | 2-2-0 | -0.17u | -4.3% | -0.23c | 91s |  |
| M gettable, price moves | 21 | 18 | -0.33c | 33.3% | 18 | -0.11c | 7 | 4-3-0 | +1.02u | 14.6% | 0.89c | 49s |  |
| M control: not gettable | 112 | 37 | -0.45c | 32.4% | 39 | -0.88c | 15 | 9-6-0 | +2.19u | 14.6% | 1.74c | 28s |  |
| M all moves | 146 | 64 | -0.49c | 32.8% | 66 | -0.69c | 26 | 15-11-0 | +3.04u | 11.7% | 1.31c | 28s |  |

A and B on the same side/line: 16.

## Odds API credits (100K/month plan)

Study: 577/day, projected 17318/30 days. All monitors on the key: 2273/day, projected 68175/30 days. Remaining 68508; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T00:06:10Z: 11 games (9 in 24h), quotes {'prophetx': 578, 'novig': 517, 'kalshi': 1230, 'polymarket_us': 996}, 703 unmatched, 1494 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 15 B 0, credits used 4 left 68508, 133s
- 2026-10-29T00:00:19Z: 11 games (9 in 24h), quotes {'prophetx': 578, 'novig': 719, 'kalshi': 1242, 'polymarket_us': 996}, 711 unmatched, 1580 side/lines, polls [none_due; NBA:fast], moves 4, new A 28 B 0, credits used 2 left 68512, 274s
- 2026-10-28T23:50:35Z: 12 games (10 in 24h), quotes {'prophetx': 1102, 'novig': 701, 'kalshi': 1262, 'polymarket_us': 1442}, 567 unmatched, 2192 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 3 B 0, credits used 4 left 68526, 288s
- 2026-10-28T23:46:23Z: 12 games (10 in 24h), quotes {'prophetx': 1102, 'novig': 695, 'kalshi': 1274, 'polymarket_us': 1442}, 577 unmatched, 2192 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 9 B 0, credits used 4 left 68542, 239s
- 2026-10-28T23:40:33Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 702, 'kalshi': 1288, 'polymarket_us': 1442}, 513 unmatched, 2219 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 3, new A 10 B 2, credits used 6 left 68548, 338s
- 2026-10-28T23:35:34Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 698, 'kalshi': 1308, 'polymarket_us': 1442}, 527 unmatched, 2228 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 11 B 0, credits used 4 left 68564, 288s
- 2026-10-28T23:30:16Z: 13 games (11 in 24h), quotes {'prophetx': 1102, 'novig': 696, 'kalshi': 1314, 'polymarket_us': 1442}, 537 unmatched, 2241 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 16 B 0, credits used 8 left 68583, 306s
- 2026-10-28T23:20:13Z: 13 games (9 in 24h), quotes {'prophetx': 942, 'novig': 704, 'kalshi': 1324, 'polymarket_us': 1216}, 551 unmatched, 2013 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 6 B 0, credits used 6 left 68614, 184s
- 2026-10-28T23:13:26Z: 13 games (9 in 24h), quotes {'prophetx': 934, 'novig': 697, 'kalshi': 1330, 'polymarket_us': 1216}, 558 unmatched, 2016 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 4, new A 10 B 1, credits used 4 left 68622, 380s
- 2026-10-28T23:10:12Z: 17 games (13 in 24h), quotes {'prophetx': 934, 'novig': 695, 'kalshi': 1328, 'polymarket_us': 1216}, 254 unmatched, 2312 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 24 B 0, credits used 4 left 68636, 182s

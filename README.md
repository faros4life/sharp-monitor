# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-29T02:36:04Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 1246 | 1097 | -3.68c | 23.0% | 1098 | -4.02c | 603 | 307-296-0 | -24.45u | -4.1% |  |  | criteria not met (603/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 408 | 349 | -6.87c | 15.2% | 350 | -7.38c | 164 | 73-91-0 | -11.26u | -6.9% |  |  | criteria not met (164/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 20 | 17 | -0.62c | 35.3% | 17 | -0.31c | 10 | 2-8-0 | -5.59u | -55.9% |  |  | criteria not met (10/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 1 | 4.01c | 100.0% | 1 | 3.07c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 15 | 14 | -0.86c | 28.6% | 14 | -0.23c | 10 | 2-8-0 | -5.59u | -55.9% |  |  |  |
| B ref age 5m+ | 4 | 2 | -1.25c | 50.0% | 2 | -2.54c | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 38 | 34 | -0.71c | 29.4% | 34 | -0.59c | 18 | 13-5-0 | +7.56u | 42.0% | 0.34c | 145s | criteria not met (18/50 graded, CLV not positive) |
| M gettable, line moves | 16 | 13 | -0.68c | 30.8% | 13 | -0.78c | 6 | 4-2-0 | +1.75u | 29.2% | 0.06c | 145s |  |
| M gettable, price moves | 22 | 21 | -0.74c | 28.6% | 21 | -0.47c | 12 | 9-3-0 | +5.81u | 48.4% | 0.51c | 105s |  |
| M control: not gettable | 118 | 85 | -0.94c | 32.9% | 88 | -1.26c | 32 | 20-10-2 | +7.84u | 24.5% | 1.53c | 28s |  |
| M all moves | 156 | 119 | -0.88c | 31.9% | 122 | -1.08c | 50 | 33-15-2 | +15.40u | 30.8% | 1.23c | 28s |  |

A and B on the same side/line: 17.

## Odds API credits (100K/month plan)

Study: 591/day, projected 17736/30 days. All monitors on the key: 2321/day, projected 69630/30 days. Remaining 68217; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-29T02:31:15Z: 7 games (7 in 24h), quotes {'prophetx': 358, 'novig': 539, 'kalshi': 604, 'polymarket_us': 946}, 209 unmatched, 1237 side/lines, polls [none_due; NBA:fast], moves 0, new A 5 B 0, credits used 2 left 68217, 288s
- 2026-10-29T02:28:45Z: 7 games (7 in 24h), quotes {'prophetx': 434, 'novig': 536, 'kalshi': 604, 'polymarket_us': 1078}, 212 unmatched, 1312 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 3 B 0, credits used 4 left 68223, 138s
- 2026-10-29T02:20:12Z: 7 games (7 in 24h), quotes {'prophetx': 434, 'novig': 531, 'kalshi': 668, 'polymarket_us': 1078}, 278 unmatched, 1311 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 5 B 0, credits used 6 left 68236, 301s
- 2026-10-29T02:10:12Z: 7 games (7 in 24h), quotes {'prophetx': 434, 'novig': 541, 'kalshi': 738, 'polymarket_us': 1078}, 353 unmatched, 1312 side/lines, polls [none_due; NBA:fast], moves 0, new A 10 B 0, credits used 2 left 68260, 136s
- 2026-10-29T02:02:32Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 462, 'kalshi': 762, 'polymarket_us': 1078}, 523 unmatched, 1173 side/lines, polls [NFL:slow; NBA:fast], moves 0, new A 6 B 0, credits used 4 left 68273, 277s
- 2026-10-29T01:57:21Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 459, 'kalshi': 794, 'polymarket_us': 948}, 549 unmatched, 1106 side/lines, polls [none_due; NBA:fast], moves 1, new A 1 B 0, credits used 2 left 68277, 300s
- 2026-10-29T01:52:21Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 466, 'kalshi': 830, 'polymarket_us': 948}, 589 unmatched, 1109 side/lines, polls [NCAAF:slow; NBA:fast], moves 0, new A 1 B 0, credits used 4 left 68288, 287s
- 2026-10-29T01:47:21Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 466, 'kalshi': 852, 'polymarket_us': 948}, 604 unmatched, 1112 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, credits used 2 left 68292, 287s
- 2026-10-29T01:40:13Z: 6 games (5 in 24h), quotes {'prophetx': 434, 'novig': 452, 'kalshi': 886, 'polymarket_us': 948}, 626 unmatched, 1109 side/lines, polls [NFL:slow; NBA:fast; NBA:fast], moves 0, new A 5 B 0, credits used 6 left 68303, 415s
- 2026-10-29T01:30:15Z: 7 games (6 in 24h), quotes {'prophetx': 358, 'novig': 541, 'kalshi': 976, 'polymarket_us': 948}, 624 unmatched, 1186 side/lines, polls [NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 3 B 0, credits used 6 left 68327, 301s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T20:28:19Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 959 | 316 | -0.3c | 25.9% | 316 | -0.38c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 333 | 71 | 1.02c | 18.3% | 71 | 1.51c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 11 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 8 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 2 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 27 | 11 | -0.24c | 45.5% | 11 | -0.31c | 11 | 6-5-0 | +0.85u | 7.7% | 0.6c | 183s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 10 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 137s |  |
| M gettable, price moves | 17 | 7 | -0.16c | 42.9% | 7 | -0.09c | 7 | 4-3-0 | +1.02u | 14.6% | 0.79c | 187s |  |
| M control: not gettable | 86 | 13 | -1.12c | 15.4% | 15 | -1.57c | 15 | 9-6-0 | +2.19u | 14.6% | 0.87c | 186s |  |
| M all moves | 113 | 24 | -0.72c | 29.2% | 26 | -1.03c | 26 | 15-11-0 | +3.04u | 11.7% | 0.78c | 186s |  |

A and B on the same side/line: 8.

## Odds API credits (100K/month plan)

Study: 492/day, projected 14774/30 days. All monitors on the key: 2114/day, projected 63433/30 days. Remaining 69021; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T20:23:36Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 689, 'kalshi': 1274, 'polymarket_us': 1746}, 180 unmatched, 2853 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 69021, 283s
- 2026-10-28T20:20:14Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 701, 'kalshi': 1274, 'polymarket_us': 1778}, 180 unmatched, 2880 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 1, credits used 4 left 69037, 185s
- 2026-10-28T20:13:35Z: 17 games (14 in 24h), quotes {'prophetx': 1428, 'novig': 695, 'kalshi': 1274, 'polymarket_us': 1762}, 180 unmatched, 2816 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 2, new A 1 B 0, credits used 4 left 69053, 309s
- 2026-10-28T20:10:13Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 699, 'kalshi': 1274, 'polymarket_us': 1914}, 180 unmatched, 2910 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 8 B 0, credits used 6 left 69059, 184s
- 2026-10-28T20:00:18Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 695, 'kalshi': 1266, 'polymarket_us': 1914}, 180 unmatched, 2927 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 0, new A 12 B 0, credits used 8 left 69075, 301s
- 2026-10-28T19:50:12Z: 17 games (14 in 24h), quotes {'prophetx': 1456, 'novig': 697, 'kalshi': 1266, 'polymarket_us': 1914}, 180 unmatched, 2954 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 6 left 69108, 259s
- 2026-10-28T19:45:07Z: 17 games (14 in 24h), quotes {'prophetx': 1456, 'novig': 703, 'kalshi': 1268, 'polymarket_us': 1880}, 180 unmatched, 2932 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 69114, 263s
- 2026-10-28T19:40:14Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 699, 'kalshi': 1272, 'polymarket_us': 1912}, 182 unmatched, 2953 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, credits used 4 left 69128, 280s
- 2026-10-28T19:34:45Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 701, 'kalshi': 1270, 'polymarket_us': 1806}, 182 unmatched, 2918 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 69144, 286s
- 2026-10-28T19:29:29Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 695, 'kalshi': 1264, 'polymarket_us': 1908}, 178 unmatched, 2946 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 3, new A 3 B 0, credits used 10 left 69148, 301s

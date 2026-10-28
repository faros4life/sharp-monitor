# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-10-28T19:54:31Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held).

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 934 | 316 | -0.3c | 25.9% | 316 | -0.38c | 316 | 172-144-0 | +29.43u | 9.3% |  |  | criteria not met (316/50 graded, CLV not positive) |
| A qualifying (>= 3c) | 324 | 71 | 1.02c | 18.3% | 71 | 1.51c | 71 | 39-32-0 | +21.22u | 29.9% |  |  | criteria met - eligible for discussion at the scheduled review only |
| B Pinnacle (>= 3% EV) | 10 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  | criteria not met (1/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 1 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| B ref age 1-5m | 7 | 1 | -2.12c | 0.0% | 1 | -0.5c | 1 | 0-1-0 | -1.00u | -100.0% |  |  |  |
| B ref age 5m+ | 2 | 0 |  |  | 0 |  | 0 | 0-0-0 | +0.00u |  |  |  |  |
| M move-watch: gettable (sightings) | 27 | 11 | -0.24c | 45.5% | 11 | -0.31c | 11 | 6-5-0 | +0.85u | 7.7% | 0.6c | 183s | criteria not met (11/50 graded, CLV not positive) |
| M gettable, line moves | 10 | 4 | -0.38c | 50.0% | 4 | -0.69c | 4 | 2-2-0 | -0.17u | -4.3% | 0.29c | 137s |  |
| M gettable, price moves | 17 | 7 | -0.16c | 42.9% | 7 | -0.09c | 7 | 4-3-0 | +1.02u | 14.6% | 0.79c | 187s |  |
| M control: not gettable | 84 | 13 | -1.12c | 15.4% | 15 | -1.57c | 15 | 9-6-0 | +2.19u | 14.6% | 0.87c | 186s |  |
| M all moves | 111 | 24 | -0.72c | 29.2% | 26 | -1.03c | 26 | 15-11-0 | +3.04u | 11.7% | 0.78c | 186s |  |

A and B on the same side/line: 8.

## Odds API credits (100K/month plan)

Study: 478/day, projected 14337/30 days. All monitors on the key: 2076/day, projected 62295/30 days. Remaining 69108; guard holds 13400 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-10-28T19:50:12Z: 17 games (14 in 24h), quotes {'prophetx': 1456, 'novig': 697, 'kalshi': 1266, 'polymarket_us': 1914}, 180 unmatched, 2954 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 6 left 69108, 259s
- 2026-10-28T19:45:07Z: 17 games (14 in 24h), quotes {'prophetx': 1456, 'novig': 703, 'kalshi': 1268, 'polymarket_us': 1880}, 180 unmatched, 2932 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 69114, 263s
- 2026-10-28T19:40:14Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 699, 'kalshi': 1272, 'polymarket_us': 1912}, 182 unmatched, 2953 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 0 B 0, credits used 4 left 69128, 280s
- 2026-10-28T19:34:45Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 701, 'kalshi': 1270, 'polymarket_us': 1806}, 182 unmatched, 2918 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 2 B 0, credits used 4 left 69144, 286s
- 2026-10-28T19:29:29Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 695, 'kalshi': 1264, 'polymarket_us': 1908}, 178 unmatched, 2946 side/lines, polls [NFL:slow,NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 3, new A 3 B 0, credits used 10 left 69148, 301s
- 2026-10-28T19:20:13Z: 17 games (14 in 24h), quotes {'prophetx': 1456, 'novig': 701, 'kalshi': 1266, 'polymarket_us': 1912}, 178 unmatched, 2958 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 1, new A 2 B 1, credits used 4 left 69179, 211s
- 2026-10-28T19:10:36Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 689, 'kalshi': 1264, 'polymarket_us': 1912}, 178 unmatched, 2945 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 3, new A 4 B 0, credits used 4 left 69187, 355s
- 2026-10-28T19:06:01Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 701, 'kalshi': 1266, 'polymarket_us': 1674}, 178 unmatched, 2862 side/lines, polls [NFL:slow; NCAAF:fast,NBA:fast], moves 1, new A 2 B 0, credits used 6 left 69201, 258s
- 2026-10-28T19:00:18Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 703, 'kalshi': 1260, 'polymarket_us': 1912}, 178 unmatched, 2944 side/lines, polls [NCAAF:fast,NBA:fast; NCAAF:fast,NBA:fast], moves 2, new A 0 B 0, credits used 8 left 69217, 327s
- 2026-10-28T18:50:30Z: 17 games (14 in 24h), quotes {'prophetx': 1448, 'novig': 697, 'kalshi': 1260, 'polymarket_us': 1818}, 178 unmatched, 2920 side/lines, polls [none_due; NCAAF:fast,NBA:fast], moves 0, new A 0 B 1, credits used 4 left 69235, 284s

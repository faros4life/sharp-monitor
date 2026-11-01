# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T03:33:33Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3540 | 3326 | -2.08c | 21.5% | 1323 | -1.19c | 3187 | 1594-1593-0 | -209.83u | -6.6% |  |  | criteria not met (3187/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 913 | 865 | -3.99c | 14.2% | 204 | -2.98c | 849 | 443-406-0 | -48.45u | -5.7% |  |  | criteria not met (849/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 59 | 59 | -0.68c | 32.2% | 57 | 0.08c | 56 | 24-32-0 | -4.34u | -7.7% |  |  | criteria not met (56/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 5 | 3-2-0 | +1.29u | 25.9% |  |  |  |
| B ref age 1-5m | 38 | 38 | -0.65c | 28.9% | 37 | -0.01c | 36 | 16-20-0 | -1.15u | -3.2% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 15 | 5-10-0 | -4.48u | -29.9% |  |  |  |
| M move-watch: gettable (sightings) | 132 | 131 | -0.58c | 33.6% | 129 | -0.64c | 127 | 62-64-1 | -6.84u | -5.4% | 0.25c | 23s | criteria not met (127/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 71 | 70 | -0.54c | 37.1% | 69 | -0.77c | 69 | 33-35-1 | -4.75u | -6.9% | 0.03c | 26s |  |
| M gettable, price moves | 61 | 61 | -0.63c | 29.5% | 60 | -0.49c | 58 | 29-29-0 | -2.09u | -3.6% | 0.5c | 20s |  |
| M control: not gettable | 513 | 406 | -0.91c | 33.5% | 403 | -1.29c | 388 | 210-173-5 | +14.16u | 3.6% | 1.76c | 25s |  |
| M all moves | 645 | 537 | -0.83c | 33.5% | 532 | -1.13c | 515 | 272-237-6 | +7.32u | 1.4% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 597 | 567 | 4.12c | 28.9% | 110 | 3.07c | 556 | 249-307-0 | +243.64u | 43.8% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 20 | 17 | 0.09c | 7-10-0 | -2.32u | 13, -0.04c, -2.55u | not enough yet |
| J2 B, NBA | 9 | 8 | -0.19c | 3-5-0 | -1.72u | 5, -0.42c, -0.87u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 15 | 13 | -0.24c | 6-7-0 | -0.47u | 10, -0.42c, +0.45u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 40 | 35 | -0.55c | 12-22-1 | -10.70u | 24, -0.66c, -9.46u | not enough yet |
| D1 B, unders (descriptive) | 5 | 4 | 0.76c | 2-2-0 | +0.19u | 4, 0.76c, +0.19u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 2 | -0.8c | 0-2-0 | -2.00u | 2, -0.8c, -2.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 6 | -0.99c | 3-3-0 | -1.66u | 5, -1.02c, -2.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 338 | 24 | 7.1% | -0.5c | 1.69c | 13-10-0 | +3.35u |  |
| MK novig fair-2c | 339 | 11 | 3.2% | -0.51c | 2.59c | 6-4-0 | +2.68u |  |
| MK prophetx fair-1c | 1586 | 84 | 5.3% | -0.97c | 1.11c | 34-40-2 | -4.72u |  |
| MK prophetx fair-2c | 1572 | 24 | 1.5% | -0.8c | 2.04c | 8-13-0 | -4.39u |  |
| MK all fair-1c | 1924 | 108 | 5.6% | -0.87c | 1.21c | 47-50-2 | -1.38u | criteria not met (99/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1911 | 35 | 1.8% | -0.71c | 2.14c | 14-17-0 | -1.72u | criteria not met (31/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 49.

## Odds API credits (100K/month plan)

Study: 613/day, projected 18375/30 days. All monitors on the key: 2166/day, projected 64980/30 days. Remaining 99519; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T03:30:32Z: 21 games (21 in 24h), quotes {'prophetx': 1688, 'novig': 716, 'kalshi': 1296, 'polymarket_us': 3146}, 184 unmatched (5 book-games; fuzzy-matched 0), 3630 side/lines, polls [none_due], moves 0, new A 8 B 0, maker posted 0 filled 0, credits used 0 left 99519, 181s
- 2026-11-01T03:23:58Z: 21 games (21 in 24h), quotes {'prophetx': 1692, 'novig': 722, 'kalshi': 1328, 'polymarket_us': 2092}, 220 unmatched (7 book-games; fuzzy-matched 0), 3059 side/lines, polls [NFL:slow,NBA:slow], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 4 left 99528, 184s
- 2026-11-01T03:20:25Z: 21 games (21 in 24h), quotes {'prophetx': 1692, 'novig': 724, 'kalshi': 1336, 'polymarket_us': 1490}, 230 unmatched (8 book-games; fuzzy-matched 0), 2783 side/lines, polls [none_due], moves 0, new A 7 B 0, maker posted 0 filled 0, credits used 0 left 99532, 184s
- 2026-11-01T03:12:03Z: 21 games (21 in 24h), quotes {'prophetx': 1620, 'novig': 722, 'kalshi': 1276, 'polymarket_us': 3142}, 228 unmatched (7 book-games; fuzzy-matched 0), 3457 side/lines, polls [NHL:slow], moves 0, new A 17 B 0, maker posted 0 filled 0, credits used 2 left 99541, 183s
- 2026-11-01T03:08:32Z: 22 games (22 in 24h), quotes {'prophetx': 1622, 'novig': 724, 'kalshi': 1300, 'polymarket_us': 2048}, 178 unmatched (8 book-games; fuzzy-matched 0), 2890 side/lines, polls [NCAAF:fast], moves 1, new A 16 B 0, maker posted 0 filled 0, credits used 2 left 99552, 184s
- 2026-11-01T03:00:30Z: 21 games (21 in 24h), quotes {'prophetx': 1622, 'novig': 694, 'kalshi': 1362, 'polymarket_us': 0}, 245 unmatched (11 book-games; fuzzy-matched 0), 1920 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow; none_due], moves 1, new A 22 B 0, maker posted 0 filled 0, credits used 6 left 99554, 301s
- 2026-11-01T02:50:21Z: 21 games (21 in 24h), quotes {'prophetx': 1572, 'novig': 696, 'kalshi': 1408, 'polymarket_us': 1824}, 291 unmatched (12 book-games; fuzzy-matched 0), 2817 side/lines, polls [NCAAF:fast,NHL:slow; NCAAF:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 6 left 99571, 301s
- 2026-11-01T02:40:20Z: 21 games (21 in 24h), quotes {'prophetx': 1572, 'novig': 691, 'kalshi': 1506, 'polymarket_us': 1868}, 389 unmatched (15 book-games; fuzzy-matched 0), 2823 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 2 left 99592, 183s
- 2026-11-01T02:30:47Z: 22 games (22 in 24h), quotes {'prophetx': 1574, 'novig': 697, 'kalshi': 1596, 'polymarket_us': 1806}, 412 unmatched (16 book-games; fuzzy-matched 0), 2857 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast], moves 0, new A 17 B 0, maker posted 4 filled 0, credits used 6 left 99607, 278s
- 2026-11-01T02:25:48Z: 22 games (22 in 24h), quotes {'prophetx': 1706, 'novig': 695, 'kalshi': 1632, 'polymarket_us': 2082}, 454 unmatched (17 book-games; fuzzy-matched 0), 3110 side/lines, polls [NHL:slow; NCAAF:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 99617, 277s

# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-01T03:05:32Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 3509 | 3326 | -2.08c | 21.5% | 1323 | -1.19c | 2902 | 1454-1448-0 | -194.04u | -6.7% |  |  | criteria not met (2902/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 894 | 865 | -3.99c | 14.2% | 204 | -2.98c | 797 | 410-387-0 | -54.48u | -6.8% |  |  | criteria not met (797/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 59 | 59 | -0.68c | 32.2% | 57 | 0.08c | 46 | 19-27-0 | -4.79u | -10.4% |  |  | criteria not met (46/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 5 | 5 | 0.57c | 40.0% | 5 | 1.69c | 3 | 2-1-0 | +1.23u | 41.1% |  |  |  |
| B ref age 1-5m | 38 | 38 | -0.65c | 28.9% | 37 | -0.01c | 30 | 13-17-0 | -1.40u | -4.7% |  |  |  |
| B ref age 5m+ | 16 | 16 | -1.14c | 37.5% | 15 | -0.23c | 13 | 4-9-0 | -4.63u | -35.6% |  |  |  |
| M move-watch: gettable (sightings) | 132 | 131 | -0.58c | 33.6% | 129 | -0.64c | 110 | 56-53-1 | -1.49u | -1.4% | 0.25c | 23s | criteria not met (110/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 71 | 70 | -0.54c | 37.1% | 69 | -0.77c | 60 | 30-29-1 | -1.53u | -2.5% | 0.03c | 26s |  |
| M gettable, price moves | 61 | 61 | -0.63c | 29.5% | 60 | -0.49c | 50 | 26-24-0 | +0.03u | 0.1% | 0.5c | 20s |  |
| M control: not gettable | 512 | 406 | -0.91c | 33.5% | 403 | -1.29c | 344 | 188-151-5 | +16.26u | 4.7% | 1.76c | 25s |  |
| M all moves | 644 | 537 | -0.83c | 33.5% | 532 | -1.13c | 454 | 244-204-6 | +14.77u | 3.3% | 1.45c | 25s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 577 | 567 | 4.12c | 28.9% | 110 | 3.07c | 525 | 237-288-0 | +235.49u | 44.9% | 1.17c | 15s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 20 | 8 | 0.09c | 2-6-0 | -3.78u | 7, -0.04c, -2.78u | not enough yet |
| J2 B, NBA | 9 | 4 | -0.19c | 1-3-0 | -1.90u | 3, -0.42c, -0.90u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 15 | 6 | -0.24c | 2-4-0 | -1.78u | 5, -0.42c, -0.78u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 40 | 23 | -0.55c | 8-14-1 | -6.49u | 17, -0.66c, -6.37u | not enough yet |
| D1 B, unders (descriptive) | 5 | 1 | 0.76c | 1-0-0 | +1.13u | 1, 0.76c, +1.13u | descriptive only |
| D2 B, underdog spreads (descriptive) | 2 | 1 | -0.8c | 0-1-0 | -1.00u | 1, -0.8c, -1.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 0 | 0 |  | 0-0-0 | +0.00u | 0, , +0.00u | descriptive only |
| D4 B, NHL (descriptive) | 1 | 1 | 0.36c | 1-0-0 | +2.33u | 1, 0.36c, +2.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 6 | 5 | -0.99c | 3-2-0 | -0.66u | 4, -1.02c, -1.13u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 338 | 24 | 7.1% | -0.5c | 1.69c | 10-9-0 | +1.14u |  |
| MK novig fair-2c | 339 | 11 | 3.2% | -0.51c | 2.59c | 4-3-0 | +1.42u |  |
| MK prophetx fair-1c | 1586 | 84 | 5.3% | -0.97c | 1.11c | 28-37-2 | -7.89u |  |
| MK prophetx fair-2c | 1572 | 24 | 1.5% | -0.8c | 2.04c | 5-12-0 | -6.57u |  |
| MK all fair-1c | 1924 | 108 | 5.6% | -0.87c | 1.21c | 38-46-2 | -6.75u | criteria not met (86/50 graded, CLV not positive, record not positive) |
| MK all fair-2c | 1911 | 35 | 1.8% | -0.71c | 2.14c | 9-15-0 | -5.15u | criteria not met (24/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 49.

## Odds API credits (100K/month plan)

Study: 614/day, projected 18409/30 days. All monitors on the key: 2168/day, projected 65051/30 days. Remaining 99554; guard holds 5600 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-01T03:00:30Z: 21 games (21 in 24h), quotes {'prophetx': 1622, 'novig': 694, 'kalshi': 1362, 'polymarket_us': 0}, 245 unmatched (11 book-games; fuzzy-matched 0), 1920 side/lines, polls [NFL:slow,NCAAF:fast,NBA:slow; none_due], moves 1, new A 22 B 0, maker posted 0 filled 0, credits used 6 left 99554, 301s
- 2026-11-01T02:50:21Z: 21 games (21 in 24h), quotes {'prophetx': 1572, 'novig': 696, 'kalshi': 1408, 'polymarket_us': 1824}, 291 unmatched (12 book-games; fuzzy-matched 0), 2817 side/lines, polls [NCAAF:fast,NHL:slow; NCAAF:fast], moves 1, new A 4 B 0, maker posted 0 filled 0, credits used 6 left 99571, 301s
- 2026-11-01T02:40:20Z: 21 games (21 in 24h), quotes {'prophetx': 1572, 'novig': 691, 'kalshi': 1506, 'polymarket_us': 1868}, 389 unmatched (15 book-games; fuzzy-matched 0), 2823 side/lines, polls [none_due; NCAAF:fast], moves 0, new A 6 B 0, maker posted 0 filled 0, credits used 2 left 99592, 183s
- 2026-11-01T02:30:47Z: 22 games (22 in 24h), quotes {'prophetx': 1574, 'novig': 697, 'kalshi': 1596, 'polymarket_us': 1806}, 412 unmatched (16 book-games; fuzzy-matched 0), 2857 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast], moves 0, new A 17 B 0, maker posted 4 filled 0, credits used 6 left 99607, 278s
- 2026-11-01T02:25:48Z: 22 games (22 in 24h), quotes {'prophetx': 1706, 'novig': 695, 'kalshi': 1632, 'polymarket_us': 2082}, 454 unmatched (17 book-games; fuzzy-matched 0), 3110 side/lines, polls [NHL:slow; NCAAF:fast], moves 0, new A 2 B 0, maker posted 0 filled 0, credits used 4 left 99617, 277s
- 2026-11-01T02:20:24Z: 22 games (22 in 24h), quotes {'prophetx': 1706, 'novig': 691, 'kalshi': 1682, 'polymarket_us': 2980}, 503 unmatched (17 book-games; fuzzy-matched 0), 3583 side/lines, polls [NCAAF:fast; NCAAF:fast], moves 0, new A 3 B 0, maker posted 5 filled 0, credits used 4 left 99633, 301s
- 2026-11-01T02:10:22Z: 23 games (23 in 24h), quotes {'prophetx': 1706, 'novig': 693, 'kalshi': 1760, 'polymarket_us': 1494}, 507 unmatched (18 book-games; fuzzy-matched 0), 2909 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast], moves 0, new A 10 B 0, maker posted 7 filled 0, credits used 6 left 99665, 183s
- 2026-11-01T02:00:25Z: 24 games (23 in 24h), quotes {'prophetx': 1706, 'novig': 688, 'kalshi': 1768, 'polymarket_us': 2044}, 594 unmatched (18 book-games; fuzzy-matched 0), 3062 side/lines, polls [NCAAF:fast,NHL:fast; NCAAF:fast,NHL:fast], moves 3, new A 18 B 0, maker posted 2 filled 3, credits used 8 left 99682, 350s
- 2026-11-01T01:50:19Z: 24 games (23 in 24h), quotes {'prophetx': 1836, 'novig': 663, 'kalshi': 1728, 'polymarket_us': 1842}, 673 unmatched (20 book-games; fuzzy-matched 0), 3002 side/lines, polls [none_due; NCAAF:fast,NHL:fast], moves 0, new A 1 B 0, maker posted 1 filled 1, credits used 4 left 99710, 186s
- 2026-11-01T01:43:49Z: 22 games (22 in 24h), quotes {'prophetx': 1836, 'novig': 671, 'kalshi': 1784, 'polymarket_us': 3290}, 868 unmatched (22 book-games; fuzzy-matched 0), 3621 side/lines, polls [NFL:slow,NBA:slow; NCAAF:fast,NHL:fast], moves 2, new A 1 B 0, maker posted 4 filled 0, credits used 8 left 99727, 302s

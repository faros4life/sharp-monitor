# EV sightings study (paper, measurement only)

Started 2026-10-27T16:06:50Z. Updated 2026-11-05T03:36:00Z. Sightings are a record, never bets. CLV = close fair - sighting after-fee cost, in cents (+ = beat the close). Gate: >= 50 graded, positive average CLV and positive flat record; reviewed only at a scheduled review. A/B gate on consensus CLV; move-watch (A1) gate on Pinnacle CLV. Held = Pinnacle close minus Pinnacle's pre-move fair at the old number (+ = the move held). Rows exclude suspect sightings (best price 10c+ under the other books, or a crossed quote: usually a misread line); Pinnacle CLV only within 3 points of Pinnacle's number.

| Bucket | Sightings | Closed | CLV vs consensus | Beat % | Pin-closed | CLV vs Pinnacle | Graded | Record | Units | ROI | Held | Lag (med) | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A cross-book (>= 2c) | 5568 | 5485 | -1.81c | 23.3% | 2346 | -1.11c | 5071 | 2584-2487-0 | -221.57u | -4.4% |  |  | criteria not met (5071/50 graded, CLV not positive, record not positive) |
| A qualifying (>= 3c) | 1228 | 1221 | -3.75c | 16.4% | 271 | -2.97c | 1161 | 597-564-0 | -86.58u | -7.5% |  |  | criteria not met (1161/50 graded, CLV not positive, record not positive) |
| B Pinnacle (>= 3% EV) | 98 | 98 | -0.79c | 31.6% | 94 | -0.02c | 87 | 35-52-0 | -12.71u | -14.6% |  |  | criteria not met (87/50 graded, CLV not positive, record not positive) |
| B ref age <60s | 8 | 8 | 0.07c | 37.5% | 8 | 1.04c | 7 | 4-3-0 | +1.28u | 18.3% |  |  |  |
| B ref age 1-5m | 57 | 57 | -0.73c | 29.8% | 55 | -0.11c | 52 | 22-30-0 | -4.75u | -9.1% |  |  |  |
| B ref age 5m+ | 33 | 33 | -1.1c | 33.3% | 31 | -0.13c | 28 | 9-19-0 | -9.24u | -33.0% |  |  |  |
| M move-watch: gettable (sightings) | 237 | 235 | -0.72c | 31.5% | 233 | -0.68c | 216 | 111-102-3 | -2.99u | -1.4% | 0.07c | 26s | criteria not met (216/50 graded, CLV not positive, record not positive) |
| M gettable, line moves | 121 | 120 | -0.78c | 33.3% | 119 | -0.99c | 108 | 54-52-2 | -2.67u | -2.5% | -0.27c | 46s |  |
| M gettable, price moves | 116 | 115 | -0.65c | 29.6% | 114 | -0.36c | 108 | 57-50-1 | -0.32u | -0.3% | 0.42c | 22s |  |
| M control: not gettable | 891 | 721 | -0.89c | 34.3% | 715 | -1.3c | 669 | 344-311-14 | -7.34u | -1.1% | 1.77c | 46s |  |
| M all moves | 1128 | 956 | -0.85c | 33.6% | 948 | -1.14c | 885 | 455-413-17 | -10.34u | -1.2% | 1.41c | 28s |  |
| Suspect (10c+ gap / crossed), all legs - excluded above | 915 | 912 | 2.34c | 23.1% | 189 | 1.98c | 895 | 398-497-0 | +272.45u | 30.4% | 1.1c | 22s |  |

## Pre-registered buckets (locked Oct 31, amended 2026-10-31T14:45:00Z before any forward data was read; judged only on sightings after 2026-10-31T14:35:00Z; J = judged, D = descriptive)

| Bucket | Sightings | Graded | CLV vs Pinnacle | Record | Units | One per game (graded, CLV, units) | Verdict |
|---|---|---|---|---|---|---|---|
| J1 B overall (ex-NHL) | 54 | 46 | -0.14c | 18-28-0 | -8.69u | 32, -0.55c, -5.11u | not enough yet |
| J2 B, NBA | 38 | 31 | 0.01c | 12-19-0 | -6.24u | 19, -0.47c, -0.49u | not enough yet |
| J3 B, fresh Pinnacle reference (< 5 min old, ex-NHL) | 32 | 29 | -0.39c | 13-16-0 | -2.08u | 22, -0.69c, +2.84u | not enough yet |
| J4 Move-watch gettable, all lags (ex-NHL) | 106 | 92 | -0.82c | 43-48-1 | -7.26u | 54, -0.97c, -6.31u | negative |
| D1 B, unders (descriptive) | 12 | 9 | 0.71c | 5-4-0 | +1.33u | 9, 0.71c, +1.33u | descriptive only |
| D2 B, underdog spreads (descriptive) | 10 | 8 | -1.1c | 0-8-0 | -8.00u | 6, -1.51c, -6.00u | descriptive only |
| D3 Move-watch gettable, caught 60-180 s (descriptive) | 14 | 14 | -0.33c | 8-5-1 | +0.03u | 10, -0.53c, +1.17u | descriptive only |
| D4 B, NHL (descriptive) | 6 | 3 | 0.52c | 1-2-0 | +0.33u | 3, 0.53c, +0.33u | descriptive only |
| D5 Move-watch gettable, NHL (descriptive) | 45 | 38 | -0.4c | 21-15-2 | -1.26u | 19, -0.56c, -0.76u | descriptive only |

## A2 maker test (paper resting orders, Novig + ProphetX, main lines)

Filled = the book later traded through our bid (lower bound). Unfilled CLV = what the orders that never filled would have gained; if fills do much worse than unfilled, that is adverse selection.

| Orders | Posted | Filled | Fill rate | Fill CLV vs Pinnacle | Unfilled CLV | Record | Units | Gate |
|---|---|---|---|---|---|---|---|---|
| MK novig fair-1c | 1122 | 51 | 4.6% | -0.49c | 1.6c | 20-27-0 | -6.11u |  |
| MK novig fair-2c | 1123 | 19 | 1.7% | -0.4c | 2.52c | 10-8-0 | +3.10u |  |
| MK prophetx fair-1c | 2746 | 134 | 4.9% | -0.86c | 1.1c | 65-58-2 | +10.12u |  |
| MK prophetx fair-2c | 2728 | 38 | 1.4% | -0.6c | 2.04c | 16-21-0 | -3.58u |  |
| MK all fair-1c | 3868 | 185 | 4.8% | -0.76c | 1.25c | 85-85-2 | +4.01u | criteria not met (172/50 graded, CLV not positive) |
| MK all fair-2c | 3851 | 57 | 1.5% | -0.53c | 2.18c | 26-29-0 | -0.47u | criteria not met (55/50 graded, CLV not positive, record not positive) |

A and B on the same side/line: 81.

## Odds API credits (100K/month plan)

Study: 620/day, projected 18612/30 days. All monitors on the key: 2107/day, projected 63211/30 days. Remaining 91345; guard holds 73200 for the sharp monitor; polls skipped by the guard: 0.

## Last runs

- 2026-11-05T03:30:59Z: 15 games (15 in 24h), quotes {'prophetx': 704, 'novig': 660, 'kalshi': 854, 'polymarket_us': 962}, 678 unmatched (16 book-games; fuzzy-matched 0), 1205 side/lines, polls [NBA:fast,NHL:slow; NBA:fast], moves 0, new A 5 B 0, maker posted 4 filled 0, credits used 6 left 91345, 301s
- 2026-11-05T03:20:57Z: 15 games (15 in 24h), quotes {'prophetx': 808, 'novig': 660, 'kalshi': 950, 'polymarket_us': 1090}, 771 unmatched (19 book-games; fuzzy-matched 0), 1331 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast; NBA:fast], moves 1, new A 1 B 0, maker posted 1 filled 0, credits used 8 left 91362, 343s
- 2026-11-05T03:10:54Z: 16 games (16 in 24h), quotes {'prophetx': 808, 'novig': 664, 'kalshi': 1000, 'polymarket_us': 1090}, 746 unmatched (21 book-games; fuzzy-matched 0), 1407 side/lines, polls [none_due; NBA:fast], moves 0, new A 3 B 0, maker posted 0 filled 0, credits used 2 left 91394, 169s
- 2026-11-05T03:01:01Z: 18 games (18 in 24h), quotes {'prophetx': 816, 'novig': 716, 'kalshi': 1068, 'polymarket_us': 1090}, 769 unmatched (18 book-games; fuzzy-matched 0), 1462 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 10 B 0, maker posted 7 filled 0, credits used 8 left 91398, 301s
- 2026-11-05T02:51:56Z: 18 games (18 in 24h), quotes {'prophetx': 1018, 'novig': 710, 'kalshi': 1190, 'polymarket_us': 1154}, 766 unmatched (20 book-games; fuzzy-matched 0), 1670 side/lines, polls [NFL:slow,NCAAF:slow; NBA:fast,NHL:fast], moves 3, new A 3 B 1, maker posted 1 filled 2, credits used 8 left 91429, 296s
- 2026-11-05T02:46:43Z: 19 games (19 in 24h), quotes {'prophetx': 1008, 'novig': 711, 'kalshi': 1220, 'polymarket_us': 1154}, 723 unmatched (19 book-games; fuzzy-matched 0), 1742 side/lines, polls [none_due; NBA:fast,NHL:fast], moves 0, new A 4 B 0, maker posted 0 filled 0, credits used 4 left 91445, 258s
- 2026-11-05T02:40:59Z: 19 games (19 in 24h), quotes {'prophetx': 1008, 'novig': 713, 'kalshi': 1272, 'polymarket_us': 1154}, 773 unmatched (19 book-games; fuzzy-matched 0), 1728 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 4, new A 11 B 0, maker posted 12 filled 0, credits used 8 left 91454, 302s
- 2026-11-05T02:30:59Z: 19 games (18 in 24h), quotes {'prophetx': 1006, 'novig': 707, 'kalshi': 1322, 'polymarket_us': 1154}, 821 unmatched (19 book-games; fuzzy-matched 0), 1748 side/lines, polls [NFL:slow,NCAAF:slow,NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 14 B 0, maker posted 8 filled 0, credits used 12 left 91479, 301s
- 2026-11-05T02:20:55Z: 19 games (18 in 24h), quotes {'prophetx': 1110, 'novig': 716, 'kalshi': 1384, 'polymarket_us': 1256}, 880 unmatched (20 book-games; fuzzy-matched 0), 1847 side/lines, polls [NBA:fast,NHL:fast; NBA:fast,NHL:fast], moves 0, new A 6 B 0, maker posted 24 filled 0, credits used 8 left 91507, 301s
- 2026-11-05T02:10:52Z: 21 games (20 in 24h), quotes {'prophetx': 1108, 'novig': 714, 'kalshi': 1416, 'polymarket_us': 1256}, 765 unmatched (18 book-games; fuzzy-matched 0), 1992 side/lines, polls [NCAAF:slow; NBA:fast,NHL:fast], moves 0, new A 17 B 0, maker posted 8 filled 0, credits used 6 left 91530, 184s

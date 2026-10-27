# Paper splits (updated 2026-10-27T12:20:14Z)

Units only, 1u flat after fees. Promotions happen only at scheduled reviews. Kill bar: 30+ resulted at -0.10u/play or worse closes a split.

| Split | Type | Start | W-L-P | Units | u/play | True close % | Status |
|---|---|---|---|---|---|---|---|
| Phase-1 live filter (paper view) | a-priori | 2026-10-26 | 2-2-0 | -0.30 | -0.075 | -3.95 | OPEN |
| Phase-1 control group | control | 2026-10-26 | 1-1-0 | -0.21 | -0.105 | -1.60 | OPEN |
| Hard Rock-priced, routed | a-priori | 2026-10-26 | 4-2-0 | +1.60 | +0.267 | -0.32 | OPEN |
| Fade Hard Rock-priced | scan | 2026-10-26 | 4-2-0 | -2.12 | -0.353 | -0.32 | OPEN |
| PM-global-priced, routed | a-priori | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Unders only | scan | 2026-10-26 | 3-3-0 | -0.33 | -0.055 | -2.60 | OPEN |
| Combined filter | scan | 2026-10-26 | 4-3-0 | +0.46 | +0.066 | -3.16 | OPEN |
| Priced -125 or worse | scan | 2026-10-26 | 1-0-0 | +0.79 | +0.790 | -1.40 | OPEN |
| College basketball | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Fade alerts sent 12-24h out | scan | 2026-10-26 | 3-0-0 | -3.00 | -1.000 | +2.53 | OPEN |
| Evening sends, ex-Hard Rock | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Muted midday (11 AM-2 PM ET) | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Liquidity totals, no sharp agree | scan | 2026-10-22 | 57-44-0 | +9.79 | +0.097 |  | OPEN |
| Liquidity vs sharp (oppose) | scan | 2026-10-22 | 44-42-0 | -1.93 | -0.022 |  | OPEN |
| Liquidity spreads | scan | 2026-10-22 | 96-116-0 | -30.69 | -0.145 |  | CLOSED (by decision, 2026-10-27) |
| Liquidity overnight (12-5 AM ET) | scan | 2026-10-26 | 1-0-0 | +0.87 | +0.870 |  | OPEN |
| Liquidity evening (5-8 PM ET) | scan | 2026-10-26 | 7-8-0 | +0.97 | +0.065 |  | OPEN |

**Time splits, all-history reference (every resulted play in the feed, not forward; read only):** Evening sends, ex-Hard Rock 8-11-1, -4.32u (-0.216/play); Muted midday (11 AM-2 PM ET) 24-8-0, +12.60u (+0.394/play); Liquidity overnight (12-5 AM ET) 36-21-0, +5.48u (+0.096/play); Liquidity evening (5-8 PM ET) 55-65-0, -23.38u (-0.195/play)

**Muted midday (11 AM-2 PM ET): breakdowns** (resulted plays only)

| Cut | Group | Forward | All history |
|---|---|---|---|
| Book | prophetx | - | 16-1-0, +12.67u (+0.745/play), n=17 |
| Book | kalshi | - | 6-3-0, +2.10u (+0.233/play), n=9 |
| Book | fanduel | - | 1-0-0, +0.87u (+0.870/play), n=1 |
| Book | novig | - | 1-1-0, -0.04u (-0.020/play), n=2 |
| Book | hardrockbet | - | 0-3-0, -3.00u (-1.000/play), n=3 |
| Market | spread | - | 16-5-0, +8.74u (+0.416/play), n=21 |
| Market | total over | - | 6-3-0, +2.05u (+0.228/play), n=9 |
| Market | total under | - | 2-0-0, +1.81u (+0.905/play), n=2 |

**Closed by decision:** Liquidity spreads: Closed by Peter, Oct 27, on Muse's complete-log read: 191 resulted, -32.15u (-0.17/play), negative in every time block and every lead window.

**ProphetX tripwire:** 6/30 resulted, -0.085u/play - counting.

**Price gaps (measurement only):** {"gaps": 8, "per_day": 8.0, "edge_pct_median": 0.7, "edge_pct_p90": 4.54, "size_est_median_upper_bound": 12356.0, "seen_once_share": 1.0, "lifetime_min_median": 0.0, "lived_10min_plus": 0, "with_200_both_legs_upper_bound": 8, "scan_sec_median": 320}

**Counting rules:** resulted = W, L or P with a unit value (pushes count, at 0u); liquidity artifacts excluded; pending/ungraded plays don't count. Times are America/New_York (DST-aware). Lead = start minus alert time. Streams: SENT (pushed), MUTED (logged, never pushed), LIVE (phase-1 subset of SENT), LIQ-MAIN, LIQ-EXTRA; paper = never bet. ALL PLAYS = every resulted play in a stream; GRADED ERA = Oct 20+ only.

**Untimed entries** (stay in their stream's record, left out of time splits): ntfy_evening 0, muted_midday 0, liq_overnight 0, liq_evening 0.

## Definitions

- **Phase-1 live filter (paper view)** (a-priori; promote >= 20 resulted AND positive; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts priced on ProphetX at alert time, Grade A/B, NCAAF/NBA spreads or unders, NFL unders only, not sent 12-24h before start, not late. Muse AGREE is applied in the executor ledger, not here.
- **Phase-1 control group** (control; promote none (comparison only); kill none): Sent ProphetX-priced Grade A/B alerts that phase 1 EXCLUDES (overs, moneylines, NHL, NFL, MLB, or 12-24h before start). Shows whether the cuts help forward. No promotion bar; kill bar not applied.
- **Hard Rock-priced, routed** (a-priori; promote >= 20 resulted AND positive; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts priced on Hard Rock, graded at the alert price (the executor routes them to the best exchange).
- **Fade Hard Rock-priced** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Same alerts as 'Hard Rock-priced, routed' (sent, priced on Hard Rock), graded on the OTHER side at the real opposite-side price logged when the alert fired (fade_units, 1u after fees). Plays without a logged fade price do not count. Read next to HR-routed: both directions of every Hard Rock-priced alert.
- **PM-global-priced, routed** (a-priori; promote >= 20 resulted AND positive; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts priced on global Polymarket, graded at the alert price (routed to the best exchange). Closing population: global PM left RETAIL_BOOKS on Oct 25.
- **Unders only** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts on unders (any book, any sport).
- **Combined filter** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts NOT priced on Hard Rock, NOT sent 12-24h before start, NOT overs.
- **Priced -125 or worse** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts with price after fee at -125 or worse.
- **College basketball** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Every NCAAB alert, sent or log-only (the AP Top 25 rule mutes the rest). November Pinnacle numbers are softer (preseason ratings): early reads carry a signal-quality discount.
- **Fade alerts sent 12-24h out** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Sent alerts 12-24h before start, graded on the OTHER side at the real opposite-side price logged when the alert fired (fade_units). Plays without a logged opposite price do not count.
- **Evening sends, ex-Hard Rock** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): SENT alerts whose pricing book is not Hard Rock, sent 8:00 PM-11:59 PM ET (alert_utc, DST-aware). Watch split, not a cut: overlaps the 12-24h lead band heavily. Historical read (Muse, ex-HR): -0.22/play, n=20.
- **Muted midday (11 AM-2 PM ET)** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): MUTED alerts only (sent_to_phone false), alerted 11:00 AM-1:59 PM ET (alert_utc, DST-aware), all books, all markets. Forward watch, NOT an unmute: if it holds >= +0.10/play at 30 forward resulted, unmuting midday non-Top 25 alerts becomes a review question for Peter. Historical read (Muse, ALL PLAYS): 24-8, +12.60u, +0.39/play, n=32, concentrated (ProphetX-priced 16-1, +12.67u; +10.90u from the week of Oct 12); graded era +1.70u on 13.
- **Liquidity totals, no sharp agree** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Liquidity main feed, market = total, sharp_agree empty, artifacts excluded, alerted from Oct 22 10:30 AM ET.
- **Liquidity vs sharp (oppose)** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Liquidity main feed, sharp_oppose not empty (a Pinnacle-move alert on the other side), artifacts excluded, alerted from Oct 22 10:30 AM ET.
- **Liquidity spreads** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Liquidity main feed, market = spread, artifacts excluded, alerted from Oct 22 10:30 AM ET. CLOSED as a promotion candidate (status only: spread prints still appear in the feed and log and grade exactly as before).
- **Liquidity overnight (12-5 AM ET)** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): LIQ-MAIN prints alerted 12:00-4:59 AM ET (alerted_utc, fallback first_seen_utc; DST-aware), artifacts excluded. Historical read (Muse): +9.11u, +0.14/play, n=65 - the only positive liquidity time block.
- **Liquidity evening (5-8 PM ET)** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): LIQ-MAIN prints alerted 5:00-7:59 PM ET (alerted_utc, fallback first_seen_utc; DST-aware), artifacts excluded. Negative watch: historical read (Muse) -20.99u, -0.17/play, n=125; if it holds forward it becomes a skip window.

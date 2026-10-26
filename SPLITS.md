# Paper splits (updated 2026-10-26T13:25:10Z)

Units only, 1u flat after fees. Promotions happen only at scheduled reviews. Kill bar: 30+ resulted at -0.10u/play or worse closes a split.

| Split | Type | Start | W-L-P | Units | u/play | True close % | Status |
|---|---|---|---|---|---|---|---|
| Phase-1 live filter (paper view) | a-priori | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Phase-1 control group | control | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Hard Rock-priced, routed | a-priori | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Fade Hard Rock-priced | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| PM-global-priced, routed | a-priori | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Unders only | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Combined filter | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Priced -125 or worse | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| College basketball | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Fade alerts sent 12-24h out | scan | 2026-10-26 | 0-0-0 | +0.00 |  |  | OPEN |
| Liquidity totals, no sharp agree | scan | 2026-10-22 | 48-38-0 | +7.53 | +0.088 |  | OPEN |
| Liquidity vs sharp (oppose) | scan | 2026-10-22 | 36-35-0 | -2.76 | -0.039 |  | OPEN |

**ProphetX tripwire:** 0/30 resulted, -u/play - counting.

**Price gaps (measurement only):** {"gaps": 1, "per_day": 1.0, "edge_pct_median": 0.51, "edge_pct_p90": 0.51, "size_est_median_upper_bound": 4444, "seen_once_share": 1.0, "lifetime_min_median": 0, "lived_10min_plus": 0, "with_200_both_legs_upper_bound": 1, "scan_sec_median": 0}

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
- **Liquidity totals, no sharp agree** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Liquidity main feed, market = total, sharp_agree empty, artifacts excluded, alerted from Oct 22 10:30 AM ET.
- **Liquidity vs sharp (oppose)** (scan; promote >= 30 forward resulted AND >= +0.10u/play; kill >= 30 resulted at <= -0.1u/play -> CLOSED): Liquidity main feed, sharp_oppose not empty (a Pinnacle-move alert on the other side), artifacts excluded, alerted from Oct 22 10:30 AM ET.

# Standard test buckets (Nov 2, 2026; Peter + Muse)

Reference list for every model, backtest and lane. Registered by Muse 15:52 / 15:57 ET on the SLOW-HR backtest; Peter asked
to keep it as the standard for future models.

## Rules
- Grade on **CLV vs Pinnacle's no-vig close**, after fees. W/L is secondary.
- **FIT / CHECK**: first half of game dates vs second half. A result only counts if it holds in **both** halves.
- **PRIMARY** buckets may trigger a rule or alert, and only with **>= 15 per half** and CLV > 0 plus beat-close >= 53% in both.
- **SECONDARY** buckets can only refine a primary one, never trigger on their own.
- House bar for promotion: >= 100 graded, CLV > 0 and beat-close >= 53% in both halves, then a gettable-price audit and Peter's yes.
- Do **not** add finer cuts, team buckets or time-of-day buckets: thin cells are where false winners come from.
- Every cut must be recomputable: log the raw value and state the cut point in the report.

## PRIMARY
1. **Market**: total / spread / moneyline.
2. **Side**: over vs under; favorite vs underdog **by points** (never by price sign; moneyline uses the main spread); and market x side (e.g. totals x under, spreads x dog).
3. **Still bettable**: the price was still up at the book 1 minute and 5 minutes after detection, vs gone.

## SECONDARY
4. Kind of move: line moved (Type L) vs price only (Type P).
5. Move size: L = 0.5 / 1 / 1.5 / 2-2.5 / 3+ points; P = 8-11 / 12-19 / 20-29 / 30+ cents. Split by league.
6. Football spread key numbers: move crosses or lands on 3/7/10/14; line on or next to a key; no key.
7. Market-wide vs lone: did the other books (Novig, ProphetX, Kalshi, Polymarket US) move with Pinnacle between 15 min before the move and the confirmation read (line changed, or price shortened >= 4c)? Print this definition with the result.
8. Time before start: 30 min-2 h / 2-6 h / 6-24 h / 24 h+. The final 30 minutes (LATE) are graded separately, never mixed in.
9. Edge at detection vs Pinnacle fair: 2-4% / 4-8% / 8%+.
10. League x market.
11. Pinnacle's limit when it moved: raw limit logged on every sighting; high vs low cut at the league median (stated).
12. Book's price on the bet side: better than -110 vs -110 or worse.

# THE ONE LIST — official registry

**Agreed 7 November 2026. Supplied by Peter 9 November 2026 as the authoritative registry.**

This file exists so the registry is versioned with the code it governs rather than living only in
chat. If a name here and a name in the code disagree, this file wins and the code gets corrected.

**Standing rules**
- One name per thing.
- A new test registers here first, or it does not exist.
- Nothing renamed, merged, deleted, activated or promoted without Peter's approval.
- MISPRICE-ALL is an umbrella VIEW over SLOW-HR / RETAIL LAG / PLIMIT-CUT / EXCHANGE MISPRICE / EV.
  Never pooled.

Totals: 7 live/manual channels, 16 paper tests, 3 lenses, 6 research tracks.

---

## LIVE — real money (bot)

| # | Name | Definition |
| --- | --- | --- |
| 1 | **LANE 1** | ProphetX-priced totals (NBA/NFL unders, NCAAF unders + Top-25 overs), $200 unit, −130 cap, T-60 cutoff. **KEPT UNCHANGED.** |
| 2 | **RESTING BIDS** | Lane 1's resting-order lane, Novig GTT / Kalshi GTC, expires T-30, graded separately. KEPT. |

## MANUAL — Peter bets by hand

| # | Name | Definition |
| --- | --- | --- |
| 3 | **PETER — FEED PLAYS** | Hand bets off the alert feed (spreads, MLs, out-of-scope totals, non-Top-25 college). KEPT. |
| 4 | **HR SCANNER FLAGS** | Hard Rock flags passing the full qualification chain, pushed to the phone. KEPT. |
| 5 | **STREET VALUE** | NFL + CFB Top-25 spread cards (TAKE/FADE, QB rule, bye rule). KEPT. |
| 6 | **STEAM** | Steam-move alerts, manual only, NO BOT, judged at 50 playable plays. KEPT + ON. |
| 7 | **BETS BOARD PLAYS** | The board's PLAY calls, bet by hand. Keep/delete still open as a lane; chat alerts ON (8 Nov), Telegram confirmed live 9 Nov. |

## PAPER TESTS — registered, judged at their own bars

| # | Name | Definition |
| --- | --- | --- |
| 8 | **LANE 2** | LOW-limit sharp alerts. Paper + dry-run. Friday go-live package still owed. |
| 9 | **LIQ-BOT** | NBA totals 4h+ liquidity lane. Approved as a bot, HELD OFF; shadow logging on. |
| 10 | **POST & WAIT** | Rests board plays at the fee-equivalent price on Novig. **NOT Lane 3 — that name is retired.** |
| 11 | **SLOW-HR** | Hard Rock ≥ +2% EV; decisive cell = Type P ML underdogs. Diagnostic at 64 of 100. KEPT. |
| 12 | **DOG BAND** | Subgroup of SLOW-HR: ML dogs +100 to +299 only, forward from 7 Nov, tracked separately. Paper. |
| 13 | **LIQ-SMALL** | $25–50k-print NBA totals subset. Paper. |
| 14 | **BOARD v2** | The board's earlier rule, graded in parallel (+15-min gettable basis). |
| 15 | **P-NHL-DOGS** | NHL ML dogs. Checkpoint 50, judged 100. |
| 16 | **P-CFB-OVER / P-NFL-OVER** | NCAAF and NFL totals overs. Same bars as P-NHL-DOGS. |
| 17 | **HR-A** | Hard Rock ≥ +4% EV with +1-min recheck. Judged at 100 sightings. |
| 18 | **EXCHANGE MISPRICE** | A SENT alert offered by an exchange at ≥ +2% EV vs Pinnacle fair. EDGE2 is the broad build inside it, not part of the name. Readout at 100. |
| 19 | **PLIMIT-CUT MISPRICE** | Pinnacle limit cut ≥ 25% triggers a stale-price check. Readout at 100 gettable. |
| 20 | **EX-B** | Exchange after-fee price beats Pinnacle fair by ≥ +1.5%, $100 half unit. Judged at 100. |
| 21 | **EV TRIGGER B / B-TOTALS** | EV study sightings; judged at the EV final report, due 10 Nov. |
| 22 | **RETAIL LAG** | FanDuel/DraftKings lag slices. *Muse recommends delete — unadopted.* |
| 23 | **NCAAB OPENERS** | Our frozen openers vs Pinnacle's open. First read early December. |

## LENSES — slices inside other tests, NOT standalone strategies

| # | Name | Definition |
| --- | --- | --- |
| 24 | **ML_STAY** | $100k+ ML money that stays posted (lanes.json). |
| 25 | **PULL_FADE** | Fade after a pull (lanes.json). *Muse recommends retiring as a candidate — unadopted.* |
| 26 | **SOLO** | Unconfirmed single-book money that stays (lanes.json). |

## RESEARCH / MEASUREMENT — not betting lanes

| # | Name | Definition |
| --- | --- | --- |
| 27 | **MODEL LAB** | One fixed model per league vs Pinnacle's opener. |
| 28 | **NBA TOTALS MODEL** | Own-number NBA totals model, paper. |
| 29 | **SMALL-BOOK SURGE** | Relative-liquidity backtest. *Muse recommends closing — unadopted.* |
| 30 | **CLV-WORKS** | Does beating the close sort plays into beating expectation? Per-row export landed 9 Nov. |
| 31 | **TOTALS STUDY** | Pre-registration draft ready; ratification outstanding. |
| 32 | **CLOSE-VS-CLOSE / DECAY CURVE** | Benchmark test (Run 2 owed) and the scorecard row. |

## CLOSED — names retired, never reuse

**EV-LANE A** · **EXCHANGE-LAG ×4** · **GATE 1** · **LANE 3 (live)**

---

## Naming corrections this registry settles

- **LANE 3 is retired.** `post_test.py` called itself "LANE 3" in its docstring, report header and
  email subject; it is **POST & WAIT** (10). Corrected 9 Nov. The live Lane 3 board shadow in
  `executor.py` belongs to a retired name and should not be extended under it.
- **"Lane 2: Hard Rock moneyline underdogs" is not Lane 2.** The 9 Nov work list used that heading
  for Hard Rock slow-price Type P ML underdogs with a 64-observation diagnostic and a +100–299
  band. Those are **SLOW-HR** (11) and **DOG BAND** (12). Lane 2 (8) is the LOW-limit sharp-alert
  lane in `lane2.py`. Building the Type P work as "lane2" would repeat the Lane 3 collision.
- **Circa / ps3838 close capture** is measurement serving the CLV basis, not a betting lane. It is
  not a registry entry; it is infrastructure under the CLV standard (see `CLV_STANDARD.md`). Noted
  here only so nobody later registers it as a lane.

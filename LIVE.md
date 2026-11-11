# WHAT IS LIVE

Confirmed from code and repo variables on **11 Nov 2026, 09:10 ET**. This file is the inventory of
what can place real money, what only reaches the phone, and what is still paper. Every line below
was read out of the code or the GitHub variables page, not from memory.

No balances or account figures live in this repo (CLAUDE.md). Units and limits appear here because
they are already committed constants; dollar balances go by private email.

---

## 1. MASTER SWITCHES (GitHub repo variables — only Peter can change these)

| Variable | Value | Effect |
|---|---|---|
| `EXEC_LIVE` | `on` | Master gate. **Nothing places on any lane without it.** |
| `EXEC_BOARD_LIVE` | `ON` | Board v3 (Lane 3) money switch |
| `EXEC_R1_LIVE` | `ON` | R1 money switch |

All three switches read `.strip().lower() == "on"`, so `ON` and `on` both work (verified by running it).

Board v3 and R1 both require `EXEC_LIVE` as well: `book_live.preflight()` calls
`px_live.preflight()`, which refuses when `EXEC_LIVE` is not on. **Both lanes or neither.**

### The brake, which overrides all three
An ntfy **`STOP`** refuses every order on every venue, re-checked on each individual order, so it
bites mid-run. Send **`GO`** to release. The poll window is `since=12h`, so a STOP **silently
expires about 12 hours after it was sent** and live re-arms with no notification. The variables are
the only permanent off switch.

---

## 2. BOT LANES THAT PLACE MONEY

### Lane 1 — PHASE 1 · unit $300
Live scope (`agree_rules.phase1`):
- **NCAAF, NBA, NFL only**
- **Totals UNDERS only, plus NCAAF totals OVERS** (Nov 4). Spreads, other overs and moneylines stay paper
- NFL: unders only
- Must be **ProphetX-priced** at alert time
- **Hard Rock-priced alerts are never live**
- Retail deadband: non-ProphetX at −119 to −110 after fee is never live
- **Matchbook-only confirmations are never live**
- The **12–24h** lead window is paper
- Late alerts excluded
- Monitor grade is **not** a gate (dropped Nov 3); it stays a label only

### Lane 3 — BOARD V3 / LIQ-BOT · unit $200
- **NBA totals only**, overs and unders
- PLAY alert **4h+** before tip
- Qualifying money must still be present; **15-minute** confirmation (`BOARD_CONFIRM_MIN = 15`)
- Max **10 plays/day**, **$1,500** daily risk (`EXEC_BOARD_MAX_PLAYS`, `EXEC_BOARD_DAILY_RISK`)
- One play per game; never duplicates or opposes an existing position in any lane

### R1 · unit $200
Live scope (`agree_rules.r1`):
- **Non-Top-25 college only** — NCAAF + NCAAB, explicitly tagged non-Top-25
- **Spreads plus totals UNDERS** — no overs, no moneylines
- Must be **ProphetX-priced** at alert time
- **4h+** lead, not late
- After-fee price **−119 or better**
- **Matchbook-only confirmations excluded**
- **First alert per game+market+side only** — a repeat never bets
- Max **10 plays/day**, **$1,500** daily risk
- Lane 1's 12–24h paper window does **not** apply here
- R1's negative provisional CLV is **unverified** and was not used to alter these rules

---

## 3. SHARED PROTECTIONS (every lane, every order)

- **Global daily stop $2,250** (`px_live.DAILY_STOP`) — counts the bot's own orders only, never Peter's manual bets
- **Per-order guard $415** (`px_live.MAX_ORDER`)
- **−130 after-fee cap** on spreads and totals
- Fill venues: **ProphetX, Kalshi, Polymarket US, Novig** — best net price after fees. **Polymarket Global is never bettable**
- **ProphetX and Novig** may fill up to **2 probability cents** worse than the alert; Kalshi and Polymarket US get **zero** tolerance
- **Original alert line or strictly better** — a worse line is blocked before price is even considered
- Order-time **venue revalidation**: price, depth, line and market status re-read immediately before submitting; fails closed
- **Write-ahead order record**: the durable registry row is written *before* the order and read back; if it cannot be stored, nothing is submitted
- An unresolved order intent **refuses all further live orders** until cleared by an email Peter sends himself (subject `INTENT CLEARED <id>`, verified by Gmail's `\Sent` label)
- Duplicate and opposite-side blocking **across all lanes** and against Peter's manual bets
- ProphetX orders are **fill-or-kill** — they fill instantly or not at all, and never rest
- Only one executor run can execute at a time (`concurrency: group: executor`, `cancel-in-progress: false`)

### Resting bids
- Venues: **Novig and Kalshi** only (`REST_BOOKS`). Polymarket US is **not** in the default set
- Rest at the alert's after-fee number — **no 2¢ allowance**
- Priced as **taker**; the Polymarket US maker rebate is recorded but **unused and unproven**
- Come off at **T-30**

---

## 4. PUSH (reaches Peter's phone)

| Stream | Phone | Notes |
|---|---|---|
| Lane 1 sharp alerts | **Yes** | ntfy, mirrored to Telegram |
| R1 alerts | **MUTED** | Non-Top-25 filter silences them; the bot reads them straight from `alerts.json` |
| Board v3 / liquidity signals | **Yes** | separate signal emails |
| Bot fills, no-fills, partials, refusals, errors, resting bids, cancellations | **Yes** | Telegram, labelled `[PHASE 1]` / `[BOARD V3]` / `[R1]`, with game, bet, line, after-fee execution odds, exchange, stake, fill status and order id. One message per event |
| Balances | Email | hourly, and right after any live bot order |

`NCAAF_TOP25 = filter` — non-Top-25 college alerts are scored silently rather than pushed. That is
why R1's alerts are muted and why R1 needs its own executor path.

---

## 5. MANUAL (Peter's own bets)

- Logged as private **`Bets manual:`** notes in the Bets mailbox, body line `MANUAL: {json}`
- Read into `MANUAL_HELD`, which **blocks the bot** from duplicating or opposing them
- Hard Rock has no read path, so manual Hard Rock positions are known only from these notes
- Peter's manual ProphetX bets are **excluded** from the bot's daily stop — attribution comes from the Gmail ledger registry

---

## 6. PAPER / NOT LIVE

| Lane | Status |
|---|---|
| Lane 2 (low-limit sharp alerts) | **Dry run only** — Peter, Nov 4: "no live play" |
| Lane 1 spreads, non-NCAAF overs, moneylines | paper |
| Lane 1 12–24h lead window | paper |
| Hard Rock-priced alerts | never live |
| Matchbook-only confirmations | never live |
| Polymarket Global | never bettable (`clv_std` refuses to price it) |
| Liquidity board forward test ($25–50k NBA) | paper |
| SLOW-HR, MODEL LAB, EV sightings, bucket studies | paper / research only |

---

## 7. KNOWN LIMITATION

**ProphetX bot orders cannot be identified at the venue.** `EXT_PREFIX` is empty and a ProphetX
trade carries no `external_id` (measured over 100 real trades), so the venue's own order list
cannot separate a bot order from one of Peter's. Gmail is the sole attribution source. The
write-ahead record and the refusal latch bound the damage — at most one order per run, and the
second incident cannot happen — but they do not eliminate it.

---

## 8. HOW TO STOP

1. **Fast, from the phone:** send `STOP` on ntfy. Checked on every order, bites mid-run, all venues.
2. **Permanent:** set `EXEC_LIVE` to `off` in repo variables. Or set `EXEC_BOARD_LIVE` / `EXEC_R1_LIVE`
   to `off` to stop one lane while leaving Phase 1 running.

Do not send `GO` after a `STOP` unless you intend to re-arm everything.

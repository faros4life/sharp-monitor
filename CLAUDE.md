# Working rules for this repo

Peter's standing habit, which governs everything below: identify a measurable problem, make the
smallest necessary fix, test it, move on. No expanding scope, no extra audits without evidence of
another problem.

## When a measurement returns nothing, the measurement is the first suspect

Written on Nov 10, 2026 after making this exact mistake four times in one session. Every instance
had the same shape: an instrument returned nothing or something odd, and I explained it with the
world instead of the instrument. Each explanation was plausible, which is precisely why none of
them was challenged.

- `board_clv_check` reported **0 of 54** verified closes since the day it was written. I said the
  history cache never persisted and told Peter so. The real cause was one token in my own
  code: `close_verified(why)` where every other caller in the repo passes `close_verified(c.get("how"))`.
  `close_for` returns `(close, ERROR)`, so on success the error is `None`, and `close_verified(None)`
  is `False` *by design* — asserted in `clv_std`'s own test. 100% of good closes were discarded.
  **The script's own counters disproved me and I had not read them**: the "not in cache" bucket was
  empty while a different bucket held 50.
- Fixing that exposed a second bug one line later (`net_clv(c)` instead of `net_clv(c["p"])`) that
  had **never executed**, because the first bug made it unreachable. A file reporting 0/54 was not
  a file with a coverage problem; it was a file whose second half had never run.
- The Circa comparison printed "no comparable pair yet" and I had *pre-written* the explanation
  "expected this early, capture only began Nov 9." The 25 games were there. My reader passed
  `{"bet": None}`, and `close_for`'s first guard returns "bet text not parsed".
- I claimed Circa history could only ever be forward-only. That came from reading a 36-hour config
  default (`CC_BACK_HOURS`) as a hard limit. `/historical-odds` is a free path; backfill works, at
  roughly 40% Circa coverage on three-week-old games.

**The rule:** before explaining a null or surprising result with the data, the venue, the cache or
the sample, rule out the reader. Check the tool's own counters first — they are usually already
printing the answer. Prefer the explanation that is closest to the code you just touched.

## `cancelled` in a GitHub Actions run list means nothing on its own

Two conditions produce it and they need opposite fixes.

**Do not judge it by `updatedAt - createdAt`.** That is WALL time and includes QUEUE time, so a
queued-then-dropped run and a long-executing one look alike - a *successful* executor run showed 23
minutes against a 20-minute timeout purely from queueing. I wrote this section with that wrong test
in it and caught it an hour later.

**The reliable tell is whether Python was killed mid-work:** `Terminate orphan process: pid (python)`
in the log. Combined with the concurrency setting it is decisive - under `cancel-in-progress: false`
concurrency cancels the QUEUED run and never the running one, so a job that dies while Python is
executing can only be the timeout. No orphan-process line and a short run means it was dropped from
the queue, which is the safe path working.

Then, with that established:

- Duration ≈ timeout → the job was **killed mid-work**. `liquidity-extra` had not completed a run
  for nine hours this way, and the tell is `Terminate orphan process: pid (python)` in the log.
  Fix by removing work that should not happen (it was enumerating MLB in November), not by raising
  the timeout — it is on a 10-minute schedule, so a longer run merely collides with the next firing.
- Duration well under timeout → **concurrency protection**, working as intended. `executor-dry-run`
  has `cancel-in-progress: false`, so a queued run is dropped while one is in flight. That is
  correct: never kill a half-finished order pass so a newer one can start.

A timed-out job reports as `cancelled`, not `failure`, which is why nine hours of a dead feed looked
benign. I then set a 10-minute timeout on my own report an hour after diagnosing this, and read its
`cancelled` as a result.

**Known live instance (Nov 10):** `executor-dry-run` has `timeout-minutes: 20` and re-runs up to 3
catch-up passes when a newer `alerts.json` lands mid-run. Passes take 6-15 minutes each, so when
several fire the run exceeds 20 minutes and is killed. One was killed during pass 2. That run had
placed nothing, but a kill can land anywhere - including AFTER an order is placed and BEFORE the
ledger email that is the bot-order registry. An order missing from that registry means the daily
stop undercounts, so this is a correctness risk and not merely a lost run.

**Dropping MLB did NOT fix `liquidity-extra`** - five consecutive runs still die at exactly 9
minutes. The work genuinely does not fit; the league list was a guess and it was wrong. Diagnose
where the time actually goes before changing anything else there.

## Verifying a finding's arithmetic is not verifying that the behaviour is unintended

`live_stake` sizes to win $300 at minus money and risks $300 at plus money. A review called that
"inconsistent"; the mechanics were exactly as described, so I changed it. It was not a defect —
it is Peter's rule ("If + money we bet 300"). Reverted within minutes.

On a live-money default, state the mechanics and ask which behaviour is intended. Do not infer
intent from a review's word choice. Contrast the daily-stop fix in the same commit, which was a
genuine defect: two preflights applying the same stop to different numbers, with no possible intent
behind it.

## Do not collapse two states with opposite remedies into one message

- `board_clv_check` merged "no close found" with "close found but not same-line" into one counter.
  One bucket cannot distinguish them, and they have opposite fixes — which is what made the bug
  invisible for weeks.
- A `501` with gRPC code 12 is an UNIMPLEMENTED stub, not a live route. My cancel probe tagged
  anything that was not a 404 as "ROUTE EXISTS" and reported a stub as a real cancel endpoint.
- My resting report read "0 resting attempts" as "the resting lane is not firing, worth a look"
  without checking whether the live orders had *filled*. All three had. Resting correctly never
  fires when everything fills, so the zero was the design working.

## Bound a claim, do not assert it

"No material difference" from a mean with no spread is an overcall. At n=20 a null result means a
difference was not **detected**, never that none exists. Print the standard error and the implied
range so the claim says what the sample can and cannot support.

## Money, keys and the public repo

- Nothing financial in the repo or in Actions logs. Logs print **counts only**. Balances and dollar
  figures go by private email; units in chat.
- `ODDSPAPI_KEY`, `ODDSPAPI_FREE_KEY`, `PMUS_*`, `TRACKER_PASSPHRASE` and the rest are GitHub
  Secrets only. Never copied, never printed, never committed.
- Exports carry no API keys, account information or stakes.
- No live-betting change without Peter's explicit yes. Claude cannot move money, place bets, create
  accounts, or enter keys or payment details.
- Claude cannot write repo **variables** (`EXEC_LIVE`, `EXEC_REST_BOOKS`, `LIQ_BOOKS`...). Peter
  flips those. Claude may edit workflow `yml` defaults — but an explicit env override in a workflow
  **beats** a code default, which is why removing global Polymarket from `liquidity_monitor.BOOKS`
  did not stop `liquidity-extra` generating global alerts.

## Adding a venue or lane is not a config change

`REST_BOOKS` and `LIQ_BOOKS` are filtered against **hardcoded dispatch tuples**. A name that has no
branch is silently dropped:

- `rest_bid` handled `kalshi` and `novig` then `else: continue`. Adding `polymarket_us` to
  `EXEC_REST_BOOKS` would have placed nothing and logged nothing — the bid would have gone to
  Kalshi while we believed it was resting on Polymarket.
- `liquidity_monitor`'s fetch list is a four-name tuple. Adding `polymarket_us` to `LIQ_BOOKS`
  matches no job and is dropped without a word.

A no-op that looks like success is the worst failure available. Check the caller, not just the list.

## Polymarket US is not Polymarket Global

Different venues, different APIs, different fees. `polymarket.us` (0.06 taker) is ours;
`polymarket` / `polymarket.global` (0.03) is the crypto CLOB and is **not bettable from the US** —
`clv_std` refuses to price it at all (`NotTradeable`). `canon("polymarket")` resolves to
`polymarket.global`, which is correct and must not be "fixed" to 0.06: that would mis-price the
global book. Global stays in the registry so historical rows resolve instead of raising
`UnknownVenue`; removing it breaks the past rather than cleaning it.

The US venue's order API is gRPC-transcoded and **silently rewrites what it accepts**: it took
`tif: TIME_IN_FORCE_GOOD_TILL_TIME` plus `goodTillTime` and stored `TIME_IN_FORCE_DAY` with
`goodTillTime: null`, turning a 3-minute order into a day order. It drops
`participateDontInitiate` the same way, so maker pricing there is an assumption, not a fact.
**Acceptance is never proof on this venue — read the order back.** Cancel is
`POST /v1/order/{orderId}/cancel` and `marketSlug` is **required** despite the docs calling it
optional; the id-only route returns code 3. Never `/v1/orders/open/cancel` — that is cancel-ALL and
would kill Peter's own resting orders.

## Infrastructure quirks

- `git push` works; the GitHub REST contents-write API, GraphQL, the Actions caches API and the
  variables API are all blocked through the proxy. Use `gh api repos/{owner}/{repo}/...`; dispatch a
  workflow with `gh api -X POST .../actions/workflows/{file}/dispatches -f ref=main`.
- Gmail is the registry for anything that must survive a run and cannot go in a public repo
  (`bot_orders`, the Muse watchdog, resting-bid records). IMAP `SUBJECT` search is a **substring**
  match, so always re-check the real header prefix before trusting a body — reading dry-run mail as
  live was a real bug on Oct 27.
- The ledger JSON in an executor email is extracted with `rfind("LEDGER (machine-readable")` then
  `raw_decode` from the first bracket. Do not invent a second way.
- `/account` and `/historical-odds` are free (`credit_gate.FREE_PATHS`); everything else on
  OddsPapi bills. The free tier returns no quota header, so a job's own call count is the only meter.
- Email bodies truncate silently. `clv_report` was sending per-row detail as
  `json.dumps(head, indent=1)[:900000]`, which cut ~1.1MB of JSON mid-object and delivered
  unparseable output for months. Attach a CSV instead: it cannot be half-valid.

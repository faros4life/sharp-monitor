# Per-play one-unit exposure guard — review-only integration plan

## Decision
Preserve current asymmetric units: **negative odds → gross to-win / lane unit**; **positive odds → stake-at-risk / lane unit**. Lane 1 unit 300, R1 and Board units 200. Never reinterpret all plus-money orders as a 300-to-win cap. This branch is a reference calculator plus offline tests ONLY. Production executor is UNCHANGED.

## Inspected current executor (main, Nov 22)
- `live_stake()` preserves the requested plus/minus sizing convention (around lines 1983–2004).
- `committed_risk()` (around 4856) groups historical registry legs and takes max recorded stake across snapshots, but measures stake DOLLARS rather than mixed-price unit fractions. Only its resting path call at ~5035 was found.
- `rest_bid()` uses cross-run committed STAKE to trim a resting bid. `live_order()` (around 4304) does NOT use the same historical committed-risk check before taker dispatch. `live_remainder()` (around 4402) uses the current run's first order only; `stack_cap_report()` is REPORT ONLY.
- Board and R1 both reach common `live_order()`, `live_remainder()`, and `rest_bid()` dispatch; their units remain 200.
- These findings support a vulnerability hypothesis, NOT verification of the MIN @ SF ledger/venue incident.

## Required guarded integration (NOT implemented here)
1. Use a durable, canonical event+market+side play identity (remove lane namespace, tolerate adjacent lines only where economically overlapping). Preserve distinct order identity; don't confuse separate bets.
2. Merge snapshots by EITHER order_id or client_id with bridge records, preserving **maximum** safe exposure. Prototype currently groups on a single preferred ID; this is insufficient for production bridging. Do not assume one order appears under the same identifier at every stage.
3. Express exposure for each leg with its OWN validated limit/actual price, not the newest bet's price. Open and unknown-fill orders reserve full possible win/risk. Verified terminal cancellation or expiry may release only the unfilled remainder; matched portions remain exposed. Do not infer expiration solely from time.
4. Atomically reserve the remaining unit **before any taker or resting order**, persist the intent before dispatch, and make overlapping runs/venues conflict or fail closed. Existing journal/submission claims must be inspected for use as lock, but same-run TAKE+POST may require a shared reservation mechanism. The pure function is NOT a lock and must not be called alone to authorize venue submission.
5. Apply to taker, other-venue remainder, resting, adjacent-line, split/partial fills, and cross-lane overlaps. On an existing live resting order, reserve its worst-case outstanding amount; proposed cancel/shrink requires separate trading authorization and explicit confirmed venue terminal evidence before any capacity release.
6. Fail closed on unreadable ledger, ambiguous identity, unknown price, or unverified order status. Do not blindly add all same-event bets or misapply lane units where different lanes target the same underlying exposure.
7. Reconcile these decisions with actual MIN @ SF order/venue records IN PRIVATE. Claimed remaining $259.76 gross to win presumes the first fill was $40.24 gross-to-win at negative odds and that no other resting reservation exists.
8. Test concurrent branches against a simulated durable registry optimistic lock, and actual production record shapes incl. all order/readback pathways. Tests in this branch are **pure-function unit tests**; they do not prove end-to-end safety.

## Deployment / risk status
NO execution path changed, NO feature toggle changed, NO real order or cancel, NO live deploy authorized. Requires separate explicit user approval, PR review, demonstrated end-to-end fail-closed regression suite and evidence that venue/registry snapshots are complete.

Suggested audit command for pure tests: `python -m unittest -v test_review_unit_exposure`.

Potential issue: plus-money sizing may legally generate gross profit above 1x unit. The total budget is **1.0 unit calculated according to each leg's sizing convention**, NOT a hard cash to-win ceiling.


## Additional source-verified registry/dispatch audit — November 22

This review was performed through the connected GitHub repository, NOT Claude's independent scheduled-task session.

### Current registry API (registry.py)
- `rows()` returns private registry `orders` rows, or None if unreadable (around line 244).
- `claim_submission(key,cid)` uses a durable SHA-conflict/optimistic write to claim a key. It has **no TTL**; unknown order outcomes stay blocked (around line 871).
- `submission_held(key)` reads the claim table and raises when store unreadable (~905).
- `release_submission(key,cid)` can release only the owner's claim (~923).
- Production `journal_intent()` (~6098 executor) calls `claim_submission()` for a lane-stripped play key BEFORE posting takers, preserving a write-ahead record. A distinct `|rest` claim is used for resting path.

### Actual submission paths
- `live_order()` (~4304) is shared by all lanes. It performs static/live guards, venue revalidation, `journal_intent()`, then routes to `px_live.place()` or `live_order_other()`.
- `live_order_other()` (~4450) routes to `book_live.kalshi_place()`, `book_live.pmus_place()`, and `book_live.novig_place()` for respective venues.
- `live_remainder()` (~4402) computes current-run risk remaining from first order and additional legs and recursively calls `live_order()` for extra venues; it does NOT reconcile earlier runs' committed units.
- `rest_bid()` (~4946) includes `registry.claim_submission(pkey+'|rest')` and `committed_risk(pkey)`, but the guard is stake-dollar-based, not fraction-of-unit at each order's odds. Its `submission_held(pkey)` check is a read; it does not turn two independent claim names into a single atomic unit reservation.
- `r1` and `board` live decisions (~6800–6850) set different units but dispatch using shared `live_order()`, `live_remainder()`, `rest_bid()` (~6917–6953).
- `.github/workflows/executor-dry-run.yml` uses `concurrency: {group: executor, cancel-in-progress: false}` for its own workflow, but this does NOT prevent outstanding venue orders or external runner dispatch from double claiming the unit.

### Why this is NOT an executable fix
The existing `claim_submission()` is an exclusive key claim used for duplicate prevention, not an atomic fractional capacity reservation. Claims for taker and rest use different names. Even two serialized runs can exceed the unit if the later taker does not debit the earlier resting fill/reservation. To authorize money safely, the order writer must atomically commit a normalized reserved-fraction state in the same durable transaction as the claim and re-evaluate remaining capacity on every new order leg. New code must reconcile clients and order IDs across stored projections and report any uncertain order as committed. This cannot be proven from the public repository alone without authorized private venue/registry outcome evidence.

### Reviewer evidence distinction
Current public source confirms control flow, registry field projections and workflow concurrency only. Private, real MIN @ SF registry rows and venue fills are NOT accessible to this connection; all sample values in tests are fixtures, not a private-data replay. Tests in PR #10 are isolated and currently NOT an end-to-end order-block test. **NO-GO for merge or deployment** until all production paths, atomic reservations, private reconciliation and production-grade tests are verified.

---

# Two-repository architecture — November 22, approved as REVIEW ONLY

Peter, Nov 22: "Both execution systems use one authoritative per-play exposure budget. Every order
reserves capacity atomically before submission. Open orders remain reserved until their status is
verified. Unknown exposure blocks additional orders. A failed reservation cannot be bypassed by
either runner." Plus: do not auto-cancel existing venue orders.

Scope approved: expand this draft to cover BOTH repositories, review-only. No merge, no deployment,
no real orders, no live setting changes. STOP remains Peter's control and was not touched.

## The finding that forced the scope change

`faros4life/novig-runner` — the home runner — **does not share the exposure count**:

| evidence | what it means |
|---|---|
| `registry/bot_registry.json` | its own registry file, not this repo's durable store |
| `novig_live_order.py` contains no `registry.` reference at all | no `committed_risk`, no `claim_submission`, no `submission_held` |
| it journals through its own `novig_order_journal` | separate write-ahead record |
| `MAX_COST = 275.0`; bundled `executor.py` has `LIVE_UNIT = 50.0` | limits disagree with this repo's 300 / 200 |

So a guard added to `executor.py` alone would be blind to every order the home runner places. It
would pass its own tests and still let a play exceed its unit — the no-op that looks like success.
New Mexico −7.5 on Nov 20 is consistent with exactly this shape: **$348.20 on one side across
ProphetX and Novig, 1.49 R1 units**.

## What this branch now contains

- `review_unit_exposure.py` — the pure calculator (unchanged). Says itself it "DOES NOT provide
  atomic locking or authorize a new order".
- `review_unit_reservation.py` — **new**: the protocol that makes one of two racing runners lose.
- `test_review_unit_reservation.py` — one named test per requirement, including a racing store
  that always snipes the write, and a check that no production module imports any of it.

## The protocol

1. **One budget, keyed by canonical play identity** — event + market + side + line, lane-stripped
   and venue-agnostic. Both runners key the same way or requirement 1 is not met.
2. **Reserve before submit, under compare-and-swap.** Read `(state, version)`, evaluate remaining,
   write back with the version. A lost write never proceeds on the stale answer: it re-reads, and
   if it still cannot win, it refuses.
3. **Open and unknown-fill legs hold their FULL asked exposure.** Capacity is released only on
   `terminal_verified=True` with a fill amount — explicit venue evidence. Time passing is not
   evidence; a missing fill report is not evidence.
4. **Every failure path refuses.** Unreadable store, unknown order state, missing identity,
   unreadable price, lost compare-and-swap. Refusal is never "proceed with less".
5. **A `Grant` is the only thing that converts a stake into permission.** `authorize()` accepts
   nothing else, and a stake above the grant is refused rather than trimmed — a trimmed order would
   make the reservation and the submission disagree, which is the condition this exists to prevent.
   A runner that skips `reserve()` has no Grant and no code path that returns permission.
6. **There is no cancel or shrink path in the module.** Releasing capacity and cancelling an order
   are different actions; the second is not authorized.

## What is still NOT done, and cannot be done from here

- **Wiring.** Nothing imports this. `live_order()`, `live_remainder()`, `rest_bid()` and the home
  runner's `place()` are all unchanged. Wiring is a production change and needs separate approval.
- **The shared store.** The protocol is correct only if both runners read and write ONE store. That
  is an infrastructure decision — which store, reachable by a home runner and by Actions, with
  compare-and-swap. The code takes it as an injected dependency and does not choose.
- **The MIN @ SF replay.** It needs private registry rows and venue fills. The ledger is encrypted
  with `TRACKER_PASSPHRASE` and venue reads need trading keys — both GitHub Secrets. Not available
  to this session and not to be used by it. Muse or a dispatch-only workflow can do it.
- **End-to-end proof.** These remain pure-function tests against a fixture store. They do not prove
  that a real order is blocked.

**NO-GO for merge or deployment.** Unchanged.

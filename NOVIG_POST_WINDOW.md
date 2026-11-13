# The POST-to-record window on the home runner

Audit, Nov 13 2026. **No code change made.** `novig_live_order.place()` is live order placement and
is not touched without Peter's explicit approval. This records the defect, its real size, what it
can and cannot cause, and the smallest fix that would close it.

## The defect

`place()` writes its record *after* the venue call, not before:

```python
st, resp = call("POST", "/v3/orders", body=order)   # <- a venue order may exist from here
...
if rec["order_id"]:
    time.sleep(2)
    settle(rec)                                      # up to ~20s of further venue reads
doc, sha, api = load()                               # GitHub read
doc.setdefault("orders", []).append(rec)
save(doc, sha, api, f"Novig order {rec['status']}")  # <- the record is durable only here
```

Between those two points the venue may hold an order that nothing on our side has recorded. The
cloud's intent journal is write-ahead and correct; this is the one leg that is not.

## How big the window actually is

Measured from the six most recent successful place dispatches, step start to the post-save log
line: **4.2, 4.3, 8.4, 8.4, 8.5, 8.7 seconds** (n=6). The two short ones are GTT orders that settle
immediately; the four long ones are FOK orders that pay `sleep(2)` plus fill polling.

Subtracting the pre-POST portion (interpreter start, key load, signing, the POST itself), the
**exposed window is roughly 3-7 seconds per order**. At n=6 this bounds the typical case only; it
says nothing about a pathological `settle()` that polls its full 20s, which would push the window
past 20 seconds.

The job timeout is 5 minutes, so a timeout kill is not a plausible cause here. What lands in this
window is a machine-level event: power loss, reboot, the Actions runner service being stopped, or
the runner process being killed.

## What it can and cannot cause

It **cannot** cause a duplicate bet on its own. The cloud holds a durable submission claim and a
verified intent before any dispatch, and an intent with no confirmed order latches
`live_guards()` shut across every venue. That is why the two Nov 12 failures cost nothing but a
blocked lane. The defect costs *attribution*, not money.

What it **can** cause is an order that is invisible to every automated path at once:

1. The runner has no record, so there is no `order_id`.
2. `novig_open_orders.py` can only ask about ids it already holds, so it cannot see it.
3. `GET /v3/portfolio/orders` answers 401 on every key from both the cloud and the home PC, so
   there is no enumeration to fall back on.

One recovery route survives: **fills carry `clientId`**, and `place()` sends
`"clientId": rec["client_id"]` on the order. The cloud's fills read works and is complete (154 rows
on the last run). So a lost order that **filled** is still recoverable by client id. A lost order
that is **resting or cancelled** is not recoverable by any route we currently have.

That asymmetry is the whole risk: the money-moving case is recoverable, the open-exposure case is
not.

## Forensic discriminator that already exists

A dispatch that died *before* execution and one that died *inside* the window look different in the
run log, and the difference is decisive:

- **Before execution:** the log ends at `'python' is not recognized as an internal or external
  command` with exit code 1 and no script output at all. Nothing ran; no POST was issued. Both
  Nov 12 failures are this.
- **Inside the window:** the env block is present, the script produced no `Novig order:` line, and
  the run ended abruptly. A POST may have been issued.

`Novig order:` is printed only after `save()` returns, so its presence is proof the record is
durable and its absence is the alarm. Any dispatch whose conclusion is not `success` should be read
with that test before anything else.

## Recommended fix, smallest first

**1. Pre-POST journal (the actual fix).** Before the POST, append the row with
`status: "SENDING"` and `order_id: None` and `save()` it. POST. Then update that same row in place
with the result. If the pre-write fails, **refuse to POST** - fail closed, the same way the cloud's
`intent_verified()` refuses when its readback fails. This mirrors the write-ahead discipline the
cloud already uses and that has already proved itself here.

Cost: one extra GitHub write per order, measured elsewhere in this repo at roughly 0.5-1s. That
lengthens each placement by about a second and shrinks the unrecorded window to zero: after the
fix, every order that could possibly exist at the venue has a durable row naming its client id
before the venue is ever called.

**2. A `recover` mode.** For any row left in `SENDING`, scan `GET /v3/portfolio/fills` for that
client id. A match resolves it. No match leaves it `SENDING` and therefore blocked - which is the
correct outcome, and is strictly better than today, where the same situation leaves nothing at all
to point at.

**3. Ask Novig two questions.** Whether `GET /v3/orders` accepts a `clientId` filter, and whether
`POST /v3/orders` honours an idempotency key. Either would close the remaining gap: a clientId
lookup makes a resting lost order recoverable, and an idempotency key makes a retry return the
original order instead of placing a second one. Neither can be tested from here without issuing a
POST, which will not be done.

**4. Detection now, with no change to placement.** Compare the count of `novig-live-order`
workflow_dispatch runs against the count of rows in `snapshot/novig_orders.json` and flag any gap.
That census is what resolved the Nov 12 failures today (36 dispatches, 34 records, 2 accounted
for), it is entirely read-only, and it would have surfaced the gap the same day rather than a day
later. This is the only item here that touches nothing live.

## Status

Items 1-3 need Peter's approval because they change live order placement or require a venue
question. Item 4 does not touch placement and can be added to the existing read-only
reconciliation whenever he wants it.

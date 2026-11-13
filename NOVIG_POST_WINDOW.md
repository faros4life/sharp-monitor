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

**Update, same day: point 3 above is wrong, and the asymmetry it created is now closed.** A
read-only probe found that an orders collection does exist - it is `GET /v3/orders`, not the
`/v3/portfolio/orders` that 401s on every key. Three measured properties of it:

- It returns **open orders only**. A known CANCELED order is absent from it. So absence there
  means "not resting", never "never placed".
- **`?clientId` is ignored, not honoured.** Asking for one client id returned rows carrying two
  different ones. Any match on client id must be made client-side; a recovery that trusted that
  parameter would confirm an unrelated order.
- `?keyId` answers `403 SCOPE_INSUFFICIENT`, so the listing cannot be scoped per wallet.

Both recovery halves therefore exist now. Fills carry `clientId` and `place()` sends
`"clientId": rec["client_id"]`, so a lost order that **filled** is recoverable. The open-orders
listing carries `clientId` too, so a lost order left **resting** is recoverable as well - including
one whose id was never recorded, which is precisely what the POST window strands.

What remains unrecoverable is narrow: an order that was accepted, then cancelled or expired, with
its record lost. It is not resting, so it carries no exposure; it only leaves the ledger short.

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

**2. A `recover` mode.** Built and tested in `novig-runner/novig_order_journal.py`. For any row
left in `SENDING`, match its client id against the fills (catches a filled order) and against
`GET /v3/orders` (catches a resting one), both filtered client-side. A row resolves only on a
match, and only when the listing actually succeeded: a failed listing proves nothing and the row
stays `SENDING` and blocked. Even a complete listing with no match does not clear the row, since
the listing shows open orders only.

**3. One question left for Novig.** The `clientId` half is answered: the filter is ignored, but
the listing returns `clientId` so client-side matching works. What remains unanswered is whether
`POST /v3/orders` honours an **idempotency key**. That cannot be probed read-only - testing it
means placing a real order - so it needs Novig support. It would close the last gap by making a
retry return the original order instead of placing a second one.

**4. Detection now, with no change to placement.** Compare the count of `novig-live-order`
workflow_dispatch runs against the count of rows in `snapshot/novig_orders.json` and flag any gap.
That census is what resolved the Nov 12 failures today (36 dispatches, 34 records, 2 accounted
for), it is entirely read-only, and it would have surfaced the gap the same day rather than a day
later. This is the only item here that touches nothing live.

## Status

Items 1-3 need Peter's approval because they change live order placement or require a venue
question. Item 4 does not touch placement and can be added to the existing read-only
reconciliation whenever he wants it.

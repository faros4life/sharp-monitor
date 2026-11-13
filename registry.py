"""The bot's own durable registry, in a PRIVATE GitHub repo instead of Gmail.

Nov 11 (Peter: "we need to get rid of checking emails", "private on github", "only important
things go in it", "lets keep it the same so we can compare apples to apples").

WHY THIS EXISTS. Gmail became the registry because sharp-monitor is public and the repo rules keep
money out of it. The cost, measured on Nov 11: bot_orders() spent 79.3s - 90% of everything PERF
could see - doing one SEARCH plus a full RFC822 fetch per email across four days of ~200 run
emails, and already_handled() spent roughly 30s per candidate on unbounded X-GM-RAW searches. All
four exchanges together took 5s. Gmail was never a database and it was the entire bottleneck.

WHAT IS STORED - only what must survive a run, nothing else:
  orders   placed orders: client_id, order_id, book, stake, filled_stake, et_day, key
  intents  write-ahead records: client_id, book, stake, et_day, key, ts, cleared
  handled  dedupe: token -> {outcome, ts}
No prices, no fee models, no ledger detail, no run reports. Those stay in email, where Peter reads
them and no machine depends on them.

WINDOW: KEEP_DAYS = 4
STRIKE_KEEP_DAYS = 30   # identities are immutable; this only bounds the file size, the same window bot_orders() uses on Gmail. Peter asked for a week and then
chose to keep it at four so the before/after speed comparison stays apples to apples; in this store
the window costs nothing, so widening it later is a one-line change with no performance effect.

SAFETY. Nothing here can place or price a bet. It is a store.
  - Absent token  -> enabled() is False and every read returns None, which callers must treat
                     exactly as an unreadable Gmail registry: fail closed. Shipping this module
                     before the secret exists therefore changes no behaviour at all.
  - Unreadable    -> load() returns None. Never an empty registry, because an empty registry reads
                     as "no exposure today" and that is fail-OPEN on money.
  - Concurrent    -> writes use the blob sha as an optimistic lock and retry on conflict, because
                     overlapping executor runs are normal here (cancel-in-progress is false).
  - Lossless      -> a write merges into what is already there; it never replaces the file wholesale.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

REPO = os.environ.get("REGISTRY_REPO") or "faros4life/novig-runner"
PATH = os.environ.get("REGISTRY_PATH") or "registry/bot_registry.json"
KEEP_DAYS = 4
STRIKE_KEEP_DAYS = 30   # identities are immutable; this only bounds the file size
API = "https://api.github.com"
EMPTY = {"orders": [], "intents": [], "handled": {}, "strikes": {}, "manual": []}


def token():
    return (os.environ.get("REGISTRY_TOKEN") or "").strip()


def enabled():
    """False until Peter creates the secret. Callers then stay on the Gmail path unchanged."""
    return bool(token())


def _call(method, url, body=None, timeout=20):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sharp-monitor",
                 # Nov 12 (Peter, Priority 1): the contents API is served through a cache, and this
                 # GET carried no cache directive, so a read taken straight after a PUT could be
                 # answered with the PRE-WRITE blob. That is a candidate cause of the intermittent
                 # "read-back FAILED", and it is strictly a STRENGTHENING of the read: it can only
                 # make the store harder to believe, never easier. The read-back requirement itself
                 # is untouched - a probe that does not come back still FAILS.
                 "Cache-Control": "no-cache",
                 **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except Exception:
            return e.code, {}
    except Exception:
        return 0, {}


def _fetch():
    """(data, sha). (None, None) if the store cannot be read - NEVER ({}, None)."""
    st, r = _call("GET", f"{API}/repos/{REPO}/contents/{PATH}")
    if st == 404:
        return dict(EMPTY), None          # not created yet: a genuinely empty store, no sha
    if st != 200 or not isinstance(r, dict) or "content" in r and not isinstance(r.get("content"), str):
        return None, None
    try:
        data = json.loads(base64.b64decode(r["content"]).decode())
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None
    for k, v in EMPTY.items():
        data.setdefault(k, type(v)())
    return data, r.get("sha")


def _cutoff():
    return (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")


def _row_day(r):
    """The day a stored row belongs to. Ledger rows carry decided_utc (an ISO timestamp); the
    narrower order and intent records carry et_day. Accepting both matters: pruning on et_day alone
    silently dropped every backfilled ledger row the moment it was written."""
    for k in ("et_day", "decided_utc"):
        v = str((r or {}).get(k) or "")
        if v:
            return v[:10]
    return ""


def _prune(data):
    """Drop rows outside the window. Small and bounded: ~10 orders a day keeps this a few KB.

    A row with NO usable date is KEPT, not dropped: losing a row under-counts exposure, and
    over-keeping only costs a few bytes."""
    cut = _cutoff()
    data["orders"] = [o for o in data.get("orders") or [] if _row_day(o) == "" or _row_day(o) >= cut]
    data["intents"] = [i for i in data.get("intents") or [] if _row_day(i) == "" or _row_day(i) >= cut]
    data["handled"] = {k: v for k, v in (data.get("handled") or {}).items()
                       if str((v or {}).get("ts") or "")[:10] >= cut}
    # Strike identities never go stale - a strike_id means one selection in one market forever - so
    # they are kept far longer than the order window; the cap exists only to bound the file.
    scut = (datetime.now(timezone.utc) - timedelta(days=STRIKE_KEEP_DAYS)).strftime("%Y-%m-%d")
    data["strikes"] = {k: v for k, v in (data.get("strikes") or {}).items()
                       if str((v or {}).get("ts") or "")[:10] >= scut}
    return data


def load():
    """The whole registry, pruned. None if unreadable or not configured - callers FAIL CLOSED."""
    if not enabled():
        return None
    data, _ = _fetch()
    return None if data is None else _prune(data)


def _commit(merge, tries=4):
    """Read, merge, write, with the sha as an optimistic lock. True only on a confirmed write.

    Overlapping runs are routine here, so a conflict is expected rather than exceptional: on 409
    or 422 the file is re-read and the merge re-applied to whatever is there now. The merge
    function must be additive - it is called again on retry, so it has to be safe to repeat."""
    if not enabled():
        return False
    for attempt in range(tries):
        data, sha = _fetch()
        if data is None:
            return False                   # unreadable: never write over what we cannot see
        # Nov 12 (Peter): a merge may return False to mean "nothing to change" - the PUT is then
        # skipped and the call still succeeds. claim_token() asks about up to 30 tokens a run and
        # wrote the file EVERY time, winner or not: ~60 read-modify-writes a run against the one
        # file duplicate blocking reads, which is contention it does not need. Atomicity is intact
        # because a claim that does not win has nothing to store.
        if merge(data) is False:
            return True
        _prune(data)
        body = {"message": "registry update", "branch": os.environ.get("REGISTRY_BRANCH") or "main",
                "content": base64.b64encode(json.dumps(data, separators=(",", ":"),
                                                       sort_keys=True).encode()).decode()}
        if sha:
            body["sha"] = sha
        st, _ = _call("PUT", f"{API}/repos/{REPO}/contents/{PATH}", body)
        if st in (200, 201):
            return True
        if st not in (409, 422):
            return False
        time.sleep(0.4 * (attempt + 1))
    return False


def _upsert(rows, row, key="client_id"):
    """Replace the row with the same money identity, else append. Keeps one row per order."""
    ident = row.get(key)
    for i, existing in enumerate(rows):
        if ident is not None and existing.get(key) == ident:
            rows[i] = {**existing, **row}
            return
    rows.append(row)


def _rid(row):
    """Stable identity of a ledger row: the money identity (client_id) when there is one, else the
    venue order id. Matches bot_orders()'s own `cid or oid` rule, so dedupe agrees across stores."""
    for key in ("live_order", "live_rest"):
        lo = row.get(key) or {}
        if lo.get("order_id") or lo.get("client_id"):
            return str(lo.get("client_id") or lo.get("order_id"))
    for x in row.get("live_more") or []:
        x = x or {}
        if x.get("order_id") or x.get("client_id"):
            return str(x.get("client_id") or x.get("order_id"))
    return None


def put_rows(rows):
    """Store LEDGER ROWS verbatim - the same shape bot_orders() already parses out of Gmail.

    Stored rather than a narrower schema on purpose: no translation layer means no second place for
    the accounting rules to drift. A row carries exactly what the daily stop and duplicate blocking
    need (key, source, decided_utc and the live_order / live_rest / live_more records with their
    status, book, stakes, order_id and client_id) and nothing else."""
    keep = [r for r in rows if _rid(r)]
    if not keep:
        return True

    def merge(d):
        cur = d.setdefault("orders", [])
        for r in keep:
            _upsert(cur, dict(r, _rid=_rid(r)), key="_rid")
    return _commit(merge)


def rows():
    """The stored ledger rows, or None if the store cannot be read."""
    d = load()
    return None if d is None else (d.get("orders") or [])


FRESH_MIN = 12   # a completeness claim older than this is not trusted (schedule fires every ~5 min)


def complete_through():
    """The date through which this store is known to hold EVERY row Gmail holds, or '' if unknown."""
    d = load()
    return "" if d is None else str((d.get("meta") or {}).get("complete_through") or "")


def is_complete(cut, now=None):
    """True only if the store claims completeness for `cut` AND that claim was refreshed recently.

    The freshness half exists because invalidate() is itself a WRITE. When writes are failing - the
    exact situation in which a newly placed order is missing from the store - invalidate() fails too
    and a stale marker would survive, sending the next run down the fast path on an incomplete store
    and UNDER-COUNTING exposure. A claim that must be re-asserted every run cannot outlive the
    ability to write it: one failed refresh and the next run is back on Gmail, which is always
    complete. Worst case is a single run on a store that is at most one run behind, and that run's
    own read happened before it placed anything."""
    d = load()
    if d is None:
        return False
    meta = d.get("meta") or {}
    if str(meta.get("complete_through") or "") < cut:
        return False
    stamp = str(meta.get("complete_at") or "")
    if not stamp:
        return False
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:
        return False
    age = ((now or datetime.now(timezone.utc)) - at).total_seconds()
    return 0 <= age <= FRESH_MIN * 60


def set_complete_through(day):
    """Assert completeness through `day`, stamped now. Must be re-asserted by every run that uses
    the fast path, or is_complete() stops trusting it."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def merge(d):
        d.setdefault("meta", {}).update({"complete_through": day, "complete_at": stamp})
    return _commit(merge)


def invalidate():
    """Clear the completeness marker, forcing the next run back onto Gmail.

    Called whenever a write to this store fails. Without it a failed write would leave an order
    missing from a store that still claimed to be complete, and the daily stop would UNDERCOUNT -
    fail-open on the one guard that caps a losing day. Falling back to a slow, complete Gmail read
    is always the right trade against that."""
    return _commit(lambda d: d.setdefault("meta", {}).update({"complete_through": ""}))


STRIKE_FIELDS = ("book", "game", "date", "mtype", "label")


def strike_map():
    """{strike_id: {book, game, date, mtype, label, ...}} previously resolved, or {} if unreadable.

    Nov 11 (Peter): px_positions resolved every open strike_id on EVERY run by walking the whole
    ProphetX catalogue - one px_markets call per event across six leagues. Measured at 177.4s for
    45 calls when ProphetX was answering at 3.94s each, and it is pure repeated work: a strike_id
    names one selection in one market and never changes meaning.

    An ENTITY MAP ONLY. It answers "what IS this strike", never "what do you hold" or "what is it
    worth" - open trades and prices are always read live. A malformed entry is treated as a miss,
    so a corrupt cache degrades to the walk rather than to a wrong identity.

    Unreadable returns {} rather than None on purpose: here a miss costs a lookup, not safety, and
    the caller still blinds the venue if a strike ends up unresolved by an incomplete walk."""
    d = load()
    if d is None:
        return {}
    out = {}
    for sid, rec in (d.get("strikes") or {}).items():
        if isinstance(rec, dict) and all(rec.get(f) is not None for f in STRIKE_FIELDS):
            out[str(sid)] = rec
    return out


def put_strikes(newly):
    """Store newly resolved strike identities. Only complete records are written."""
    keep = {str(k): {f: v.get(f) for f in STRIKE_FIELDS}
            for k, v in (newly or {}).items()
            if isinstance(v, dict) and all(v.get(f) is not None for f in STRIKE_FIELDS)}
    if not keep:
        return True
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for v in keep.values():
        v["ts"] = ts

    def merge(d):
        d.setdefault("strikes", {}).update(keep)
    return _commit(merge)


def tokens_complete(now=None):
    """True when the token store (xpid dedupe, xrty retry, xwp side-taken) is known to hold
    everything Gmail holds for the window AND that claim was refreshed recently.

    Same two-part rule as is_complete() for orders, and for the same reason: invalidate() is itself
    a write, so a claim that must be re-asserted every run cannot outlive the ability to write it.
    One failed refresh and the next run reads Gmail, which is always complete."""
    d = load()
    if d is None:
        return False
    meta = d.get("meta") or {}
    cut = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    if str(meta.get("tok_complete_through") or "") < cut:
        return False
    stamp = str(meta.get("tok_complete_at") or "")
    if not stamp:
        return False
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:
        return False
    age = ((now or datetime.now(timezone.utc)) - at).total_seconds()
    return 0 <= age <= FRESH_MIN * 60


def set_tokens_complete():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def merge(d):
        d.setdefault("meta", {}).update({"tok_complete_through": day, "tok_complete_at": stamp})
    return _commit(merge)


def _stamp_fresh(stamp, now=None):
    """True when a completeness stamp is present, parseable and still inside FRESH_MIN.

    Nov 12 (Peter): the single freshness test, so touch_complete() and touch_tokens_complete()
    cannot disagree with is_complete() and tokens_complete() about what "still valid" means. A
    future stamp (negative age) is rejected too - a clock skew must not extend a claim.
    """
    stamp = str(stamp or "")
    if not stamp:
        return False
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:
        return False
    age = ((now or datetime.now(timezone.utc)) - at).total_seconds()
    return 0 <= age <= FRESH_MIN * 60


def touch_complete(now=None):
    """ORDERS twin of touch_tokens_complete(): refresh an ALREADY VALID claim, never create one.

    Nov 12 (Peter). bot_orders() re-asserts completeness at the end of its FAST path, so the claim
    stays alive while it is being used - but nothing refreshes it once it has gone stale, and only
    the Gmail backfill can set it again. That backfill lives in the run that is being killed for
    taking too long, so a single stale minute put the system on Gmail indefinitely: 495.6s inside
    held_sides(), ~79s in the executor.

    SAFETY. This is the claim the $2,000 per-lane daily risk and the global stop read through, so a
    falsely complete store is fail-OPEN on exposure, not merely slow. Three things make that
    impossible here: it refuses when no valid claim exists (which is exactly what invalidate()
    leaves behind after ANY failed order write), it re-checks under the optimistic lock in case
    another run invalidated in between, and it never touches complete_through - so it cannot widen
    the window the claim covers. An incomplete store still answers "not complete" and the caller
    still reads Gmail.
    """
    # Nov 12 (Peter, second pass). TWO DEFECTS, both fail-OPEN on exposure.
    #
    # 1. This checked only the WINDOW half (complete_through) and never the FRESHNESS half
    #    (complete_at), so a claim whose stamp had expired hours ago was re-stamped to now -
    #    resurrecting a claim nothing had re-verified. is_complete()'s own docstring names the
    #    scenario that makes this dangerous: when writes are failing, a newly placed order is
    #    missing from the store AND invalidate() fails too, so complete_through survives while the
    #    stamp goes stale. is_complete() then correctly answers "not complete" - and re-stamping
    #    undoes exactly that protection, declaring a store complete that is missing an order. The
    #    $2,000 per-lane risk and the global stop read through this, so that is fail-open, not slow.
    #
    # 2. _commit() treats a merge returning False as "nothing to change" and returns True, so the
    #    concurrent-invalidation branch reported SUCCESS to the caller. An aborted refresh must not
    #    look like a completed one, so the abort is recorded and returned as False.
    d = load()
    if d is None:
        return False                      # unreadable: assert nothing about it
    meta = d.get("meta") or {}
    cut = ((now or datetime.now(timezone.utc)) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    if str(meta.get("complete_through") or "") < cut:
        return False                      # no valid claim - a refresh must never create one
    if not _stamp_fresh(meta.get("complete_at"), now):
        return False                      # EXPIRED: only the backfill may assert completeness again
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    aborted = []

    def merge(d2):
        m2 = d2.setdefault("meta", {})
        # Re-checked under the optimistic lock: another run may have invalidated the claim, or let
        # it expire, between the pre-check and this write.
        if str(m2.get("complete_through") or "") < cut:
            aborted.append("invalidated")
            return False
        if not _stamp_fresh(m2.get("complete_at"), now):
            aborted.append("expired")
            return False
        m2["complete_at"] = stamp
    ok = _commit(merge)
    return bool(ok) and not aborted


def touch_tokens_complete(now=None):
    """Refresh the freshness stamp on an ALREADY VALID completeness claim. Never creates one.

    Nov 12 (Peter). set_tokens_complete() is only reachable inside bot_orders()' backfill, which
    main() reaches ~150 lines AFTER handled_pids() - the one caller that would use the claim. So the
    claim could only ever be consumed by the NEXT run, and FRESH_MIN is 12 minutes while the gap
    between the two points is the tail of one run plus up to a 10-minute schedule gap plus ~90s of
    the next. It was reliably stale, so every run fell back to Gmail (110.7s), which made runs slower
    and likelier to be killed, which meant the backfill never ran to set the claim. A loop that fed
    itself.

    The fix is NOT a longer window - FRESH_MIN stays 12. This only re-stamps a claim that is already
    valid for the window, after this run has durably written its own tokens. It cannot manufacture
    completeness: if tok_complete_through is missing or older than the window (which is what
    invalidate_tokens() leaves behind, and what a failed backfill causes), this returns False and
    changes nothing, so the next run reads Gmail exactly as it does today.
    """
    # Nov 12 (Peter, second pass): same two defects as touch_complete(), same fixes. The freshness
    # half was never checked, so an expired claim was resurrected; and the concurrent-abort branch
    # reported success because _commit() reads a False merge as "nothing to change".
    d = load()
    if d is None:
        return False                      # unreadable: never assert anything about it
    meta = d.get("meta") or {}
    cut = ((now or datetime.now(timezone.utc)) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    if str(meta.get("tok_complete_through") or "") < cut:
        return False                      # no valid claim to refresh - do not create one
    if not _stamp_fresh(meta.get("tok_complete_at"), now):
        return False                      # EXPIRED: only the backfill may assert completeness again
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    aborted = []

    def merge(d2):
        m2 = d2.setdefault("meta", {})
        if str(m2.get("tok_complete_through") or "") < cut:
            aborted.append("invalidated")
            return False
        if not _stamp_fresh(m2.get("tok_complete_at"), now):
            aborted.append("expired")
            return False
        m2["tok_complete_at"] = stamp
    ok = _commit(merge)
    return bool(ok) and not aborted


def invalidate_tokens():
    return _commit(lambda d: d.setdefault("meta", {}).update({"tok_complete_through": ""}))


# ------------------------------------------------------- manual notes (Nov 12, Peter: "Phase 1 only")
# Peter's Hard Rock bets, which the bot has no read path for, arrive as "Bets manual:" notes and are
# the only thing standing between a manual position and a duplicate or opposite bot bet. Mirrored
# here so the Gmail read can eventually move off the pre-order path - but Gmail stays AUTHORITATIVE
# until the two are independently proven to agree. Nothing in this section gates a bet yet.
MANUAL_DAYS = 3   # read_manual()'s own Gmail window. NOT KEEP_DAYS, and the claim is tested against this.


def manual_notes():
    """The mirrored notes, in the order Gmail returned them.

    None - never [] - when the store cannot be read, because the caller must fall back to Gmail
    rather than read an empty result as "Peter holds no manual positions"."""
    d = load()
    return None if d is None else list(d.get("manual") or [])


def put_manual(notes):
    """Mirror read_manual()'s parsed notes as a WHOLE-WINDOW SNAPSHOT, replacing what was stored.

    Deliberately NOT an upsert like put_rows(). A manual note carries no id, and Peter can correct
    or DELETE one: an additive mirror would keep a deleted note alive for the length of the window
    and report a conflict Gmail no longer reports - a phantom position blocking a real bet. The
    snapshot reproduces corrections and deletions exactly, because it is whatever Gmail's window
    held at the moment of the scan.

    Order is preserved, and it matters: replay order decides the outcome, since MANUAL_HELD[k]
    OVERWRITES for the bet's own side while setdefault() does NOT for the opposite side."""
    keep = [n for n in (notes or []) if isinstance(n, dict)]

    def merge(d):
        d["manual"] = keep
    return _commit(merge)


def manual_complete(now=None):
    """Same two-part rule as is_complete() and tokens_complete(), tested against MANUAL_DAYS: the
    snapshot covers the manual window AND the claim was refreshed inside FRESH_MIN. One failed
    refresh and the next run reads Gmail, which is always complete."""
    d = load()
    if d is None:
        return False
    meta = d.get("meta") or {}
    cut = (datetime.now(timezone.utc) - timedelta(days=MANUAL_DAYS)).strftime("%Y-%m-%d")
    if str(meta.get("man_complete_through") or "") < cut:
        return False
    stamp = str(meta.get("man_complete_at") or "")
    if not stamp:
        return False
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:
        return False
    age = ((now or datetime.now(timezone.utc)) - at).total_seconds()
    return 0 <= age <= FRESH_MIN * 60


def set_manual_complete():
    """Only reachable from a SUCCESSFUL full-window read_manual() scan. A failed Gmail search proves
    nothing about the window, so that path invalidates instead."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def merge(d):
        d.setdefault("meta", {}).update({"man_complete_through": day, "man_complete_at": stamp})
    return _commit(merge)


def invalidate_manual():
    return _commit(lambda d: d.setdefault("meta", {}).update({"man_complete_through": ""}))


def token_set():
    """Every stored token. {} if unreadable - the caller then falls back to Gmail."""
    d = load()
    return set() if d is None else set((d.get("handled") or {}).keys())


def put_tokens(toks, outcome="seen"):
    """Record tokens (xpid / xrty / xwp). Additive; an existing token keeps its first outcome."""
    keep = sorted({str(t) for t in toks if t})
    if not keep:
        return True
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def merge(d):
        h = d.setdefault("handled", {})
        for t in keep:
            if t not in h:
                h[t] = {"outcome": outcome, "ts": ts}
    return _commit(merge)


NOTIFY_STALE_MIN = 15   # a 'pending' claim older than this is an interrupted send, not a live one


def _age_min(ts, now):
    """Minutes since an ISO stamp, or None when it cannot be read. None means 'treat as stale':
    an unreadable stamp must not pin a notification shut forever."""
    try:
        t = datetime.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None
    return (now - t).total_seconds() / 60.0


def claim_token(tok, stale_min=NOTIFY_STALE_MIN):
    """Atomically claim a notification token. True means THIS caller owns the send.

    Nov 11: Novig fill reports were deduped against a Gmail token email, and Gmail does not index
    a just-sent message in time for the next catch-up pass. 27 fills went out 70+ times in one
    afternoon that way. The claim has to be a WRITE, not a search: the store is read-modify-write
    under a sha lock, so two overlapping passes cannot both win the same token.

    False when another pass holds it ('pending' and fresh) or it has already been sent
    ('reported'). A 'pending' claim older than stale_min is a send that died mid-flight and is
    re-claimed - one repeat beats silently losing a fill notice, which is money information.

    RAISES when the store cannot be read or written, so the caller falls back to the Gmail record
    rather than sending blind. Never returns False on a failure: that would drop the notice."""
    tok = str(tok or "")
    if not tok:
        raise ValueError("claim_token: empty token")
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    won = {"v": False}

    def merge(d):
        h = d.setdefault("handled", {})
        cur = h.get(tok) or {}
        out = str(cur.get("outcome") or "")
        if out == "reported":
            won["v"] = False            # already told him
            return False                # nothing to store: skip the write entirely
        if out == "pending":
            age = _age_min(cur.get("ts"), now)
            if age is not None and age < stale_min:
                won["v"] = False        # another pass is mid-send right now
                return False
        h[tok] = {"outcome": "pending", "ts": ts}
        won["v"] = True

    if not _commit(merge):
        raise RuntimeError("registry claim write failed")
    return won["v"]


def release_token(tok):
    """Drop a claim whose send failed, so the next pass retries at once instead of waiting out
    stale_min. Best-effort: a failure here only costs the stale window."""
    def merge(d):
        h = d.setdefault("handled", {})
        if str((h.get(str(tok)) or {}).get("outcome") or "") == "pending":
            h.pop(str(tok), None)
    try:
        return _commit(merge)
    except Exception:
        return False


def put_venue_ids(pairs):
    """Store client_id -> venue order id for Novig submissions.

    Nov 12 (Peter): "store both IDs from the submission response and use the venue ID to
    reconcile fills." A Novig submission is dispatched to the home runner, so at dispatch time the
    venue's own id does not exist yet and a locally generated uuid4 stands in for it. Fills carry
    the venue's id. So the bot could not reconcile its own submissions against its own fills -
    even one known to have filled was absent from 152 fill rows.

    The home runner's result rows carry BOTH (client_id and order_id), so the mapping is recorded
    the first time a result is read, and is then durable. Additive: a mapping already stored is
    never overwritten, so a later row cannot repoint a client id at a different venue order."""
    keep = {str(c): str(v) for c, v in (pairs or {}).items() if c and v}
    if not keep:
        return True
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def merge(d):
        m = d.setdefault("venue_ids", {})
        added = False
        for c, v in keep.items():
            if c not in m:
                m[c] = {"venue_order_id": v, "ts": ts}
                added = True
        if not added:
            return False            # nothing new: skip the write
    return _commit(merge)


def venue_ids():
    """{client_id: venue_order_id}. {} when the store is unreadable or not configured - callers
    treat a missing mapping as UNRESOLVED, never as 'no fill'."""
    d = load()
    if d is None:
        return {}
    return {c: (v or {}).get("venue_order_id") for c, v in (d.get("venue_ids") or {}).items()
            if (v or {}).get("venue_order_id")}


def claim_submission(key, cid):
    """Atomically claim ONE play key for ONE submission. True only for the caller that wins it.

    Nov 12 (Peter): "Make the claim durable and atomic before submission ... prove two concurrent
    attempts produce exactly one dispatch." The lane-key fix closed the SEQUENTIAL duplicate - two
    runs five minutes apart, which is what happened - but two runs that both read LIVEKEYS before
    either wrote an intent would still both submit. LIVEKEYS is a read; this is a write under the
    store's sha lock, so exactly one caller can win a key.

    There is deliberately NO staleness expiry. An unclaimed-but-unconfirmed submission means the
    venue outcome is unknown, and an unknown outcome must keep blocking retries until it is
    reconciled - so the claim is cleared only by release_submission() on a refusal that never
    reached the venue, or by Peter clearing it.

    RAISES when the store cannot be read or written: no durable claim, no submission."""
    k, c = str(key or ""), str(cid or "")
    if not k or not c:
        raise ValueError("claim_submission: key and cid are required")
    won = {"v": False}

    def merge(d):
        subs = d.setdefault("submissions", {})
        cur = subs.get(k)
        if isinstance(cur, dict) and cur.get("cid") and cur.get("cid") != c:
            won["v"] = False
            return False            # someone else owns this key: nothing to write
        subs[k] = {"cid": c, "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        won["v"] = True

    if not _commit(merge):
        raise RuntimeError("submission claim write failed")
    return won["v"]


def release_submission(key, cid):
    """Give a claim back when the submission never reached the venue. Only the owner may release,
    so a losing caller cannot free the winner's key."""
    k, c = str(key or ""), str(cid or "")

    def merge(d):
        subs = d.setdefault("submissions", {})
        cur = subs.get(k)
        if not isinstance(cur, dict) or cur.get("cid") != c:
            return False
        subs.pop(k, None)
    try:
        return _commit(merge)
    except Exception:
        return False


def switch_state():
    """The latched STOP/GO, or None. RAISES when the store cannot be read, so a caller can refuse
    rather than read an unreadable latch as 'not paused'."""
    d = load()
    if d is None:
        raise RuntimeError("registry unreadable - switch latch unknown")
    s = d.get("switch")
    return s if isinstance(s, dict) else None


def put_switch(word, when=None):
    """Latch STOP or GO so the pause outlives ntfy's ~12 hour retention (Peter, Nov 12: "message
    expiration must not resume trading")."""
    w = str(word or "").strip().upper()
    if w not in ("STOP", "GO"):
        return False

    def merge(d):
        cur = d.get("switch")
        if isinstance(cur, dict) and cur.get("word") == w:
            return False            # already latched the same way: no write
        d["switch"] = {"word": w, "when": when,
                       "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return _commit(merge)


def bump_streak(name):
    """Count consecutive occurrences of a recurring condition. Returns the new count.

    Nov 11 (Peter: "if it happens 5 times in a row then telegram me"): a venue that blips and
    recovers is not worth a message, a venue that stays blind is. The count has to outlive the
    run, so it lives here.

    RAISES when the store cannot be written, so the caller treats an uncountable streak as
    noteworthy and notifies rather than going quiet on a failure."""
    out = {"n": 0}
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def merge(d):
        s = d.setdefault("streaks", {})
        cur = int((s.get(str(name)) or {}).get("n") or 0) + 1
        s[str(name)] = {"n": cur, "ts": ts}
        out["n"] = cur

    if not _commit(merge):
        raise RuntimeError("streak write failed")
    return out["n"]


def reset_streak(name):
    """Clear a streak once the condition clears. Best-effort: a miss only delays the next count."""
    def merge(d):
        (d.setdefault("streaks", {})).pop(str(name), None)
    try:
        return _commit(merge)
    except Exception:
        return False


def put_order(rec):
    """Record a PLACED order. client_id is the money identity, so a repeat is an update."""
    return _commit(lambda d: _upsert(d.setdefault("orders", []), dict(rec)))


def put_intent(rec):
    """Record a write-ahead intent BEFORE submitting. A confirmed PUT is the precondition."""
    return _commit(lambda d: _upsert(d.setdefault("intents", []), dict(rec)))


def clear_intent(client_id):
    def merge(d):
        for i in d.setdefault("intents", []):
            if i.get("client_id") == client_id:
                i["cleared"] = True
    return _commit(merge)


def mark_handled(tokens, outcome):
    """Dedupe tokens for this run's plays. outcome 'placed' or 'refused'."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def merge(d):
        h = d.setdefault("handled", {})
        for t in tokens:
            h[t] = {"outcome": outcome, "ts": ts}
    return _commit(merge)


def selftest():
    """One read/write round trip, reported in the run email before anything depends on this store.

    Staged on purpose: the module ships and proves itself against the real API in a real run while
    bot_orders() is still reading Gmail, so a broken transport cannot stop Peter betting. Writes
    only its own throwaway key under handled, inside the same pruning window."""
    if not enabled():
        return "registry: no REGISTRY_TOKEN - still on Gmail (nothing changed)"
    t0 = time.time()
    data = load()
    if data is None:
        return f"registry: UNREADABLE at {REPO}/{PATH} - would fail closed; still on Gmail"
    read_s = time.time() - t0
    probe = "xselftest" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    t1 = time.time()
    ok = mark_handled([probe], "selftest")
    write_s = time.time() - t1
    # Nov 12 (Peter, Priority 1: "determine whether the failure occurs during write, read,
    # authentication, concurrency or consistency verification").
    #
    # This line used to read `seen = bool(back and probe in ...)`, which is the collapse CLAUDE.md
    # warns about: `back is None` (the store could not be READ AT ALL - auth, 5xx, timeout) printed
    # the same "read-back FAILED" as a readable store that did not contain the probe (a LOST
    # UPDATE, or a stale cached blob). Those have opposite remedies, and one bucket cannot tell
    # them apart - which is why "intermittent read-back failures" had no cause attached to it.
    #
    # Four distinct outcomes now, and a second read as the discriminator between the last two:
    #   WRITE FAILED        - the PUT never confirmed; nothing was stored. Fail closed, as before.
    #   READ UNREADABLE     - transport or auth. Says nothing about whether the write landed.
    #   STALE (then seen)   - absent on the first read, present on the second: read-after-write
    #                         staleness, i.e. consistency, not a lost write.
    #   MISSING (twice)     - written, confirmed, and genuinely not there: a LOST UPDATE, which is
    #                         the only one of the four that means the store cannot be trusted.
    back = load()
    if back is None:
        verdict, detail = "FAILED", "read UNREADABLE (transport/auth) - the write is unconfirmed"
    elif probe in (back.get("handled") or {}):
        verdict, detail = "ok", ""
    else:
        time.sleep(1.0)
        back2 = load()
        if back2 is None:
            verdict, detail = "FAILED", "absent, then UNREADABLE - unconfirmed"
        elif probe in (back2.get("handled") or {}):
            verdict, detail = "FAILED", "STALE READ: absent at once, present 1s later (consistency, not a lost write)"
        else:
            verdict, detail = "FAILED", "MISSING on two reads: LOST UPDATE - do not trust the store"
    return (f"registry: read {read_s:.2f}s ({len(data.get('orders') or [])} orders, "
            f"{len(data.get('intents') or [])} intents, {len(data.get('handled') or {})} handled), "
            f"write {'ok' if ok else 'FAILED'} {write_s:.2f}s, read-back {verdict}"
            + (f" [{detail}]" if detail else "")
            + " - compare with the 79s Gmail registry read")

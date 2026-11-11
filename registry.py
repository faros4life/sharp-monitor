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
EMPTY = {"orders": [], "intents": [], "handled": {}, "strikes": {}}


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
        merge(data)
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


def invalidate_tokens():
    return _commit(lambda d: d.setdefault("meta", {}).update({"tok_complete_through": ""}))


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
    back = load()
    seen = bool(back and probe in (back.get("handled") or {}))
    return (f"registry: read {read_s:.2f}s ({len(data.get('orders') or [])} orders, "
            f"{len(data.get('intents') or [])} intents, {len(data.get('handled') or {})} handled), "
            f"write {'ok' if ok else 'FAILED'} {write_s:.2f}s, read-back {'ok' if seen else 'FAILED'}"
            f" - compare with the 79s Gmail registry read")

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

WINDOW: KEEP_DAYS = 4, the same window bot_orders() uses on Gmail. Peter asked for a week and then
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
API = "https://api.github.com"
EMPTY = {"orders": [], "intents": [], "handled": {}}


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


def _prune(data):
    """Drop rows outside the window. Small and bounded: ~10 orders a day keeps this a few KB."""
    cut = _cutoff()
    data["orders"] = [o for o in data.get("orders") or [] if str(o.get("et_day") or "") >= cut]
    data["intents"] = [i for i in data.get("intents") or [] if str(i.get("et_day") or "") >= cut]
    data["handled"] = {k: v for k, v in (data.get("handled") or {}).items()
                       if str((v or {}).get("ts") or "")[:10] >= cut}
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

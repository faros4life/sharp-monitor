#!/usr/bin/env python3
"""SHARED ODDSPAPI CREDIT GATE - Stage 1: implemented, tested, SHADOW BY DEFAULT.

Peter approved the gate on 9 Nov with these requirements, each mapped to the code below:
  fail closed on every PAID request            -> reserve() returns None unless it can prove room
  free endpoints bypass the gate entirely      -> FREE_PATHS, checked before anything else
  500-credit protected reserve of 5,000        -> RESERVE_FLOOR, so usable = 4,500
  the provider's Nov 3 - Dec 3 period          -> clv_ledger.month_key(), period-start keyed
  /account as the authoritative usage source   -> _authority(), free, never a local counter
  atomic reservations for in-flight calls      -> git ref compare-and-swap, see ATOMICITY
  crashes, expiry, outages, retries, rollover  -> see FAILURE MODES
  no double-count when /account catches up     -> see RECONCILIATION
  staged: enforce only after tests pass        -> ENFORCE defaults off; this is shadow mode

ENFORCEMENT IS ON BY DEFAULT since 2026-11-09 (Peter: close the OddsPapi work, protect what is
left). ODDSPAPI_GATE=shadow turns it off for one run; in shadow reserve() never refuses and records
what it WOULD have refused so the gate can be reconciled against the provider before it can block
anything. That is Peter's stage 3.

ATOMICITY, and why git. Separate GitHub Actions runners share no filesystem and no lock service,
and the REST contents API is blocked through our proxy. But `git push` to a ref IS a
compare-and-swap: a non-fast-forward push is REJECTED, not merged. So a reservation is taken by
committing it and pushing; a rejected push means another job won the race, and we re-read and
retry. Two jobs therefore cannot both believe they hold the same remaining credits - the loser
always sees the winner's reservation before it retries. That is the proof Peter asked for, and
test_credit_gate.py exercises it against a real local bare repo with two competing writers.

CONSEQUENCE, stated plainly: taking a reservation needs push access. Workflows that make billable
calls but run with `contents: read` - hcache-fill, slowhr-cell, slowhr-backtest, model-lab - CANNOT
reserve. Under fail-closed they would be refused outright once enforcement is on. Granting them
`contents: write` is a workflow permission change and is listed for Peter rather than done here.

RECONCILIATION - not double-counting. The provider's figure lags: a call we just made may not be in
/account yet. So usage is

    used = provider_used(as_of T) + spends recorded AFTER T + open reservations

Local spend entries carry a timestamp and are dropped once T moves past them, because by then
/account already contains them. Nothing is counted twice and nothing is missed in the window.

FAILURE MODES
  crash mid-call      the reservation stays and EXPIRES (RESERVE_TTL), then is reclaimed on read.
                      A crash leaks one reservation for a few minutes, never the budget.
  provider outage     /account unreachable -> no authority -> FAIL CLOSED (Peter's instruction).
                      Free paths are unaffected because they never reach the gate.
  retries             a retried HTTP call reuses its existing reservation; confirm() is idempotent
                      by token, so a retry cannot be counted twice.
  period rollover     the ledger is keyed by period start, so Dec 3 opens a new budget on its own.
  ledger unreadable   FAIL CLOSED, and say so.

Read-only as to betting: no bet, rule, threshold, venue or notification. Counts only - the ledger
holds no money, balance or account data, so it is safe in a public repo.
"""
import json
import os
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone

# NO project imports at module scope, deliberately. Every billable caller imports this module, and
# clv_ledger imports executor, which pulls the whole credential chain - importing it here would make
# a credit check cost a credential load and would reintroduce the lane2 -> clv_ledger -> executor
# -> lane2 cycle. The gate is a leaf: stdlib only. month_key below mirrors clv_ledger.month_key, and
# test_credit_gate asserts the two agree.
PERIOD_DAY = int(os.environ.get("ODDSPAPI_PERIOD_DAY", "") or "3")


def month_key(now):
    """The period a moment falls in, keyed by its start - the provider bills Nov 3 to Dec 3, so a
    calendar month is the wrong boundary. Same rule as clv_ledger.month_key."""
    y, m = now.year, now.month
    if now.day < PERIOD_DAY:
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return f"{y:04d}-{m:02d}-{PERIOD_DAY:02d}"


LEDGER = os.environ.get("GATE_LEDGER", "") or "credits/gate.json"
PLAN = int(os.environ.get("ODDSPAPI_PLAN", "") or "5000")
RESERVE_FLOOR = int(os.environ.get("ODDSPAPI_RESERVE", "") or "500")
RESERVE_TTL = timedelta(minutes=int(os.environ.get("GATE_TTL_MIN", "") or "10"))
AUTH_TTL = timedelta(minutes=int(os.environ.get("GATE_AUTH_TTL_MIN", "") or "15"))
# ENFORCING BY DEFAULT since 2026-11-09, on Peter's instruction to close the OddsPapi work and
# protect what is left. The default is "enforce", not "shadow", deliberately: enforcement has to
# cover EVERY paid caller, and setting it per workflow means one missed env block is a silent hole
# in the cap. Defaulting on makes a miss impossible. ODDSPAPI_GATE=shadow turns it off for a single
# run if that is ever needed.
MODE = (os.environ.get("ODDSPAPI_GATE") or "enforce").strip().lower()
BRANCH = os.environ.get("GATE_BRANCH", "") or "main"
BASE_REF = f"origin/{BRANCH}"
ENFORCE = MODE == "enforce"
PUSH_TRIES = 5
REFUSAL_LOG = 50          # the refusal log is bounded; it is a diagnostic, not an archive
NOTE_LOG = 20             # likewise the notes: unbounded, they grew a line per failed refresh

# OddsPapi bills everything EXCEPT these. They bypass the gate completely and can never be blocked.
FREE_PATHS = ("/account", "/historical-odds")


def is_free(path):
    p = str(path or "")
    return any(p.startswith(f) for f in FREE_PATHS)


def _now():
    return datetime.now(timezone.utc)


def _iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tp(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _git(*args, check=False):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


# ------------------------------------------------------------------ the ledger
def period_of(d, now):
    """The period this budget belongs to. The provider's own valid_from wins when we have seen it -
    it is the real boundary - and clv_ledger's Nov-3 key is the fallback until then."""
    p = ((d or {}).get("authority") or {}).get("period")
    return p or month_key(now)


def _blank(now, period=None):
    return {"period": period or month_key(now), "authority": {}, "spent": [], "reserved": []}


def _raw(now):
    """The ledger's text AND the commit it was read from. Returns (text, present, base).

    origin/main is the authority on shared state - a stale or half-written working copy is not -
    so the CAS reads the blob straight out of the fetched ref.

    `base` is what makes this a real compare-and-swap, and leaving it out was a genuine lost-update
    bug: when the write re-resolved origin/main for itself, a runner whose push was about to be
    rejected instead found the winner's commit as its parent, pushed a clean fast-forward, and
    silently erased the winner's reservation. Both runners then believed they held the same credits.
    The parent must be the exact commit the data was read from, so that a ref which moved in between
    makes the push non-fast-forward and the loser is told it lost."""
    base = None
    if _fetch():
        r = _git("rev-parse", BASE_REF)
        if r.returncode == 0:
            base = r.stdout.strip()
            s = _git("show", f"{base}:{LEDGER}")
            if s.returncode == 0:
                return s.stdout, True, base
            return "", False, base    # the ref exists but carries no ledger yet: a real first run
    if os.path.exists(LEDGER):        # no remote (local-only use and the pure-logic tests)
        try:
            return open(LEDGER).read(), True, base
        except Exception:
            return None, True, base   # present but unreadable -> fail closed
    return "", False, base


def _read(now):
    """The shared ledger, pruned of expired reservations and of spends the provider has absorbed.

    ok=False means the ledger is PRESENT BUT UNREADABLE, which is the fail-closed case. A ledger
    that simply does not exist yet is ok=True on a blank: a first run must be able to bootstrap,
    or enforcement would deadlock on its own missing file and never spend again."""
    txt, present, base = _raw(now)
    if txt is None:
        return _blank(now), False, base
    if not present or not txt.strip():
        return _blank(now), True, base
    try:
        d = json.loads(txt)
    except Exception:
        return _blank(now), False, base
    if d.get("period") != period_of(d, now):
        # rollover: a fresh budget, keeping the authority block so the new period starts from the
        # provider's own figure rather than from zero
        return _blank(now, period_of(d, now)), True, base
    t = _tp((d.get("authority") or {}).get("as_of"))
    d["reserved"] = [r for r in (d.get("reserved") or [])
                     if (_tp(r.get("expires")) or now) > now]
    # a spend older than the authority read is already inside provider_used - dropping it is what
    # stops the double-count
    # >= not >: a spend recorded in the SAME second as the authority read is ambiguous - the
    # provider may or may not have counted it. Keeping it may count one call twice for up to
    # AUTH_TTL; dropping it loses the call entirely and lets the gate overspend. For a budget the
    # safe direction is to over-count, so equal timestamps are kept.
    d["spent"] = [s for s in (d.get("spent") or [])
                  if not t or (_tp(s.get("at")) or now) >= t]
    return d, True, base


def used(d, now):
    """provider usage as of T, plus spends after T, plus open reservations."""
    a = d.get("authority") or {}
    base = a.get("used")
    if base is None:
        return None                        # no authority -> caller must fail closed
    return int(base) + sum(int(s.get("n", 0)) for s in d.get("spent") or []) \
        + sum(int(r.get("n", 0)) for r in d.get("reserved") or [])


def plan_of(d):
    """The provider's own request_limit when it reported one, else the configured 5,000."""
    lim = ((d or {}).get("authority") or {}).get("limit")
    return int(lim) if isinstance(lim, (int, float)) and lim > 0 else PLAN


def room(d, now):
    u = used(d, now)
    if u is None:
        return None
    return (plan_of(d) - RESERVE_FLOOR) - u


# ------------------------------------------------------------------ authority
def _authority(d, now, force=False):
    """The provider's own usage. /account is FREE, so refreshing costs nothing.

    Field names are not guessed here. credits.py confirmed them against the live response on
    5 Nov: the counters sit under subscriptions[0] as request_count / request_limit, with the
    window as valid_from / valid_until, and credits._pick already searches both scopes."""
    a = d.get("authority") or {}
    t = _tp(a.get("as_of"))
    if not force and t and now - t < AUTH_TTL and a.get("used") is not None:
        return d
    try:
        import credits as cr
        acct = cr.account()
        if acct.get("_error"):
            raise RuntimeError(acct["_error"])
        u = cr._pick(acct, "request_count", "requestsUsed", "used")
        lim = cr._pick(acct, "request_limit", "requestsLimit", "limit")
        pkey, plabel, exact = cr.period_key(acct, now)
        if isinstance(u, (int, float)):
            d["authority"] = {"used": int(u), "as_of": _iso(now), "src": "/account",
                              "limit": int(lim) if isinstance(lim, (int, float)) else None,
                              "period": pkey if exact else month_key(now),
                              "period_label": plabel, "period_exact": bool(exact)}
            d["period"] = d["authority"]["period"]
            # Deliberately NOT clearing d["spent"] here. Doing so assumes /account is fully caught
            # up at the instant of the read, and it is not: the provider lags. Worse, clearing
            # erased other runners' just-recorded spends, which is how a loser of the CAS race
            # regained room and spent credits the winner had already taken. _read's timestamp prune
            # is the single place that drops absorbed spends, and it only drops ones strictly older
            # than this as_of.
        else:
            raise RuntimeError("no usage field in /account")
    except Exception as e:
        n = d.setdefault("notes", [])
        n.append(f"{_iso(now)} authority refresh failed ({type(e).__name__}: {str(e)[:60]})")
        del n[:-NOTE_LOG]            # bounded, like the refusal log: a diagnostic, not an archive
    return d


# ------------------------------------------------------------------ atomic reserve
def _fetch():
    return _git("fetch", "-q", "origin", BRANCH).returncode == 0


def _commit_push(d, msg, base):
    """Compare-and-swap the ledger onto the shared ref.

    Built from git plumbing on purpose. The obvious implementations are both unsafe here:
    `pull --rebase` CONFLICTS whenever two runners touch the ledger and leaves the checkout
    mid-rebase, wedging every later git call in that job; `reset --hard` would throw away other
    scripts' uncommitted data files in the same run. So this writes a blob, builds a tree against
    origin/main in a THROWAWAY index (GIT_INDEX_FILE), commits it with commit-tree, and pushes that
    commit. The working tree and the real index are never touched, nothing can conflict, and the
    push is still a compare-and-swap: if origin/main moved, it is rejected and we lost the race."""
    if base is None:          # no remote: write the working copy and carry on (local-only use)
        try:
            os.makedirs(os.path.dirname(LEDGER) or ".", exist_ok=True)
            open(LEDGER, "w").write(json.dumps(d, indent=1, sort_keys=True) + "\n")
            return True
        except Exception:
            return False
    body = json.dumps(d, indent=1, sort_keys=True) + "\n"
    h = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=body,
                       capture_output=True, text=True)
    if h.returncode != 0:
        return False
    blob = h.stdout.strip()
    idx = os.path.join(tempfile.gettempdir(), f"gate-idx-{uuid.uuid4().hex}")
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    try:
        if subprocess.run(["git", "read-tree", base], env=env,
                          capture_output=True).returncode != 0:
            return False
        if subprocess.run(["git", "update-index", "--add", "--cacheinfo",
                           f"100644,{blob},{LEDGER}"], env=env,
                          capture_output=True).returncode != 0:
            return False
        t = subprocess.run(["git", "write-tree"], env=env, capture_output=True, text=True)
        if t.returncode != 0:
            return False
        c = subprocess.run(["git", "commit-tree", t.stdout.strip(), "-p", base, "-m", msg],
                           capture_output=True, text=True,
                           env=dict(os.environ,
                                    GIT_AUTHOR_NAME="credit-gate", GIT_AUTHOR_EMAIL="gate@local",
                                    GIT_COMMITTER_NAME="credit-gate",
                                    GIT_COMMITTER_EMAIL="gate@local"))
        if c.returncode != 0:
            return False
        ok = _git("push", "-q", "origin", f"{c.stdout.strip()}:{BRANCH}").returncode == 0
    finally:
        try:
            os.remove(idx)
        except OSError:
            pass
    if ok:                       # keep the working copy in step for anything reading it locally
        try:
            os.makedirs(os.path.dirname(LEDGER) or ".", exist_ok=True)
            open(LEDGER, "w").write(body)
        except Exception:
            pass
    return ok


def _note_refusal(now, n, purpose, why, d, base):
    """Record a refusal on the shared ref, retrying because the record is itself a CAS push.

    Without the retry, refusals are the first thing lost under contention - exactly when they
    matter most - and stage 3's shadow reconciliation would under-report what enforcement would
    have blocked. Best effort: a refusal that cannot be recorded still refuses."""
    for i in range(PUSH_TRIES):
        if i:
            _fetch()
            d, ok, base = _read(now)
            if not ok:
                return
        r = d.setdefault("refused", [])
        r.append({"at": _iso(now), "n": n, "purpose": purpose, "why": why,
                  "run": os.environ.get("GITHUB_RUN_ID") or "local"})
        del r[:-REFUSAL_LOG]                       # keep the log bounded
        if _commit_push(d, f"credit gate: refused {n} for {purpose} ({why})", base):
            return
        time.sleep(0.25 * (i + 1))


def reserve(n, purpose, path=None):
    """A token granting n paid calls, or None when the gate refuses. FAIL CLOSED.

    In shadow mode a token is ALWAYS granted and a refusal is only recorded, so the gate can be
    reconciled against the provider before it is allowed to block anything."""
    now = _now()
    if path is not None and is_free(path):
        return {"token": "free", "n": 0, "free": True}
    for attempt in range(PUSH_TRIES):
        if attempt:
            _fetch()          # refresh the ref only; never rebase the checkout
        d, ok, base = _read(now)
        if not ok and ENFORCE:
            return None                                   # ledger unreadable -> closed
        d = _authority(d, now)
        rm = room(d, now)
        if rm is None or rm < n:
            why = "no provider authority" if rm is None else f"only {rm} of the usable budget left"
            _note_refusal(now, n, purpose, why, d, base)
            if ENFORCE:
                return None
            return {"token": "shadow", "n": n, "shadow": True, "would_refuse": why}
        tok = uuid.uuid4().hex[:12]
        d["reserved"].append({"token": tok, "n": n, "purpose": purpose,
                              "run": os.environ.get("GITHUB_RUN_ID") or "local",
                              "at": _iso(now), "expires": _iso(now + RESERVE_TTL)})
        if _commit_push(d, f"credit gate: reserve {n} for {purpose}", base):
            return {"token": tok, "n": n}
        time.sleep(0.4 * (attempt + 1))                    # lost the CAS - re-read and retry
    return None if ENFORCE else {"token": "shadow", "n": n, "shadow": True,
                                 "would_refuse": "could not take an atomic reservation"}


def confirm(res):
    """The calls happened. Idempotent by token, so a retry cannot be counted twice."""
    if not res or res.get("free") or res.get("shadow"):
        return
    now = _now()
    for attempt in range(PUSH_TRIES):
        if attempt:
            _fetch()          # refresh the ref only; never rebase the checkout
        d, _, base = _read(now)
        if any(s.get("token") == res["token"] for s in d.get("spent") or []):
            return                                         # already confirmed
        d["reserved"] = [r for r in d.get("reserved") or [] if r.get("token") != res["token"]]
        d.setdefault("spent", []).append({"token": res["token"], "n": res["n"], "at": _iso(now)})
        if _commit_push(d, "credit gate: spent %d" % res["n"], base):
            return
        time.sleep(0.4 * (attempt + 1))


def release(res):
    """The calls did NOT happen - give the reservation back."""
    if not res or res.get("free") or res.get("shadow"):
        return
    now = _now()
    for attempt in range(PUSH_TRIES):
        if attempt:
            _fetch()          # refresh the ref only; never rebase the checkout
        d, _, base = _read(now)
        d["reserved"] = [r for r in d.get("reserved") or [] if r.get("token") != res["token"]]
        if _commit_push(d, "credit gate: release", base):
            return
        time.sleep(0.4 * (attempt + 1))


# ------------------------------------------------------------- in-process blocks
# Reserving one credit per call would mean a git fetch and a push per API call, which for
# hist_cache's hundreds of calls is far more expensive than the calls themselves. So a process
# reserves a BLOCK once and draws it down in memory, confirming what it used and releasing the
# rest at exit. A crashed process leaks at most one block for RESERVE_TTL, never the budget.
BLOCK = int(os.environ.get("GATE_BLOCK", "") or "25")
SPEND = __import__("collections").Counter()   # billable calls this process, by purpose
_HELD = {"res": None, "left": 0, "used": 0, "purpose": None}


def take(n=1, purpose="api", path=None):
    """True when n paid calls may be made. FAIL CLOSED: False means do not call.

    Also counts what was spent, by purpose, for the attribution summary printed at exit."""
    if path is not None and is_free(path):
        return True
    SPEND[str(purpose)] += n
    if _HELD["left"] >= n:
        _HELD["left"] -= n
        _HELD["used"] += n
        return True
    flush()                                     # settle the old block before taking a new one
    res = reserve(max(BLOCK, n), purpose)
    if res is None:
        return False
    _HELD.update(res=res, left=max(BLOCK, n) - n, used=n, purpose=purpose)
    return True


def flush():
    """Confirm the calls actually made and give back the rest of the block."""
    res = _HELD["res"]
    if not res:
        _HELD.update(res=None, left=0, used=0)
        return
    used_n = _HELD["used"]
    _HELD.update(res=None, left=0, used=0)
    if used_n > 0:
        confirm(dict(res, n=used_n))            # bill only what was used
    else:
        release(res)


def spend_summary():
    """One line naming what this process spent, by endpoint. Counts only - no prices, money or
    account data - so it is safe in a public Actions log.

    WHY THIS EXISTS (Nov 9). The gate's shared ledger cannot do attribution: a contents: read
    workflow cannot push its spend record, so the ledger logged 1 credit over a window in which
    the provider counted 23. The cap was never at risk - it is driven by /account, which is
    authoritative - but we could not see WHICH caller was spending, and ~52 credits/day of the
    burn stayed untraced. stdout needs no permissions, so every caller can report its own spend
    whatever its workflow can or cannot write."""
    if not SPEND:
        return
    parts = " ".join(f"{k}={v}" for k, v in sorted(SPEND.items(), key=lambda kv: -kv[1]))
    print(f"ODDSPAPI BILLABLE this run: total={sum(SPEND.values())}  {parts}")


import atexit                                    # noqa: E402  - flush even on an unclean exit
atexit.register(flush)
atexit.register(spend_summary)


def status():
    now = _now()
    d, ok, base = _read(now)
    d = _authority(d, now)
    u, rm = used(d, now), room(d, now)
    return {"mode": MODE, "enforce": ENFORCE, "period": period_of(d, now), "readable": ok,
            "period_label": (d.get("authority") or {}).get("period_label"),
            "plan": plan_of(d), "floor": RESERVE_FLOOR, "usable": plan_of(d) - RESERVE_FLOOR,
            "provider_used": (d.get("authority") or {}).get("used"),
            "authority_as_of": (d.get("authority") or {}).get("as_of"),
            "spent_since": sum(int(s.get("n", 0)) for s in d.get("spent") or []),
            "open_reservations": sum(int(r.get("n", 0)) for r in d.get("reserved") or []),
            "used_total": u, "room": rm,
            "refused": len(d.get("refused") or [])}


if __name__ == "__main__":
    s = status()
    print("ODDSPAPI CREDIT GATE - " + ("ENFORCING" if s["enforce"] else "SHADOW (never refuses)"))
    for k in ("period", "plan", "floor", "usable", "provider_used", "authority_as_of",
              "spent_since", "open_reservations", "used_total", "room", "refused"):
        print(f"  {k:20s} {s[k]}")
    print(f"  free paths (never gated): {', '.join(FREE_PATHS)}")

#!/usr/bin/env python3
"""Targeted recovery reset for the CLV ledger - Nov 5 2026, on Peter's explicit written approval.

WHAT THIS IS FOR
The /fixtures request used to be clamped to now-14d (d0 = max(game_start, now - FETCH_DAYS)), so a
bet on an older game could never have its fixture fetched. Those rows retried until they hit
MAX_TRIES and were marked done, which permanently removes them from scoring:
    if rec.get("clv") is not None or rec.get("done"): continue
FETCH_DAYS is now 45, so the cause of those failures is gone, but the done flags still bar the rows.
This clears ONLY those stale flags.

WHAT IT WILL NOT TOUCH
MLB rows (the league is not in cl.SPORT at all), no-price rows, far-from-main-line rows, and anything
that has not exhausted its retries. Those failures are real and their flags stay. Nothing already
scored is altered and no fixture assignment is invalidated.

SAFETY
Writes nothing unless APPLY=1. Before any write it copies clv/state.enc byte-for-byte to
clv_backup/state-<utc timestamp>.enc and verifies the two SHA-256 digests match, so the 31/243
baseline stays recoverable. The log prints counts and digests only; row detail goes to private email.
"""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

import executor as ex
import tracker_build as tb

import clv_ledger as cl

STATE = "clv/state.enc"
BACKUP_DIR = "clv_backup"
APPLY = os.environ.get("APPLY", "") == "1"

# Exactly the two reasons Peter authorised, and only where the row exhausted its retries.
STALE = ("no OddsPapi fixture matched", "team not matched")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    now = datetime.now(timezone.utc)
    st = tb.dec(json.load(open(STATE)))
    bets = st.get("bets") or {}
    L = [f"CLV TARGETED RECOVERY RESET | {now:%Y-%m-%d %H:%M} UTC | "
         f"{'APPLY - state written' if APPLY else 'DRY RUN - nothing written'}",
         "",
         "Clears done flags that were set by a failure the widened fetch window has since fixed.",
         "Nothing already scored is altered; no fixture assignment is invalidated; no matching rule",
         "is loosened anywhere by this script.", ""]

    # ---------------------------------------------------------------- baseline, before anything
    scored = {k: r for k, r in bets.items() if r.get("clv") is not None}
    def bk(r):
        return ((r.get("snap") or {}).get("book") or "?")
    books = sorted({bk(r) for r in bets.values()})
    L += ["=" * 68, "BASELINE BEFORE RESET (the figure that must stay recoverable)", "=" * 68,
          f"  scored {len(scored)} of {len(bets)} ({100.0 * len(scored) / max(1, len(bets)):.1f}%)", ""]
    L.append("  book          total   scored    %")
    for b in books:
        t = sum(1 for r in bets.values() if bk(r) == b)
        s_ = sum(1 for r in scored.values() if bk(r) == b)
        L.append(f"  {b[:12]:<12} {t:>6}   {s_:>6}  {100.0 * s_ / max(1, t):>5.1f}%")
    L.append("")

    # ---------------------------------------------------------------- selection
    pick, near = [], []
    for k, r in bets.items():
        if r.get("clv") is not None or not r.get("done"):
            continue
        why, tries = (r.get("why") or "").strip(), r.get("tries", 0)
        if why in STALE and tries >= cl.MAX_TRIES:
            pick.append((k, r))
        elif why in STALE:
            near.append((k, r))          # right reason, retries NOT exhausted - deliberately excluded
    by_reason, by_book = {}, {}
    for _, r in pick:
        by_reason[(r.get("why") or "")] = by_reason.get((r.get("why") or ""), 0) + 1
        by_book[bk(r)] = by_book.get(bk(r), 0) + 1
    L += ["=" * 68, f"SELECTED FOR RESET: {len(pick)} rows", "=" * 68,
          f"  rule: clv is None AND done AND tries >= MAX_TRIES ({cl.MAX_TRIES}) AND reason in {STALE}"]
    for a, b in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        L.append(f"     {b:>5}  {a}")
    L.append("  by book: " + ", ".join(f"{a} {b}" for a, b in sorted(by_book.items(), key=lambda kv: -kv[1])))
    if len(pick) != 74:
        L += ["", f"  *** COUNT IS {len(pick)}, NOT THE AUTHORISED 74. Nothing is written on a count mismatch."]

    if near:
        L += ["", f"  EXCLUDED - right reason but retries not exhausted ({len(near)}). Reported, not reset,",
              "  because the authorisation named only the exhausted rows:"]
        for _, r in near:
            s = r.get("snap") or {}
            L.append(f"     {bk(r):<10} {s.get('league') or '?':<6} tries {r.get('tries', 0)} | "
                     f"{(r.get('why') or '')[:34]} | {(s.get('bet') or '')[:26]}")

    # rows whose flags are deliberately left alone - compare by id, never by dict equality
    picked = {k for k, _ in pick}
    left = {}
    for k, r in bets.items():
        if r.get("clv") is None and r.get("done") and k not in picked:
            w = f"{(r.get('why') or '(no reason recorded)')[:46]} | tries {r.get('tries', 0)}"
            left[w] = left.get(w, 0) + 1
    L += ["", f"  LEFT FLAGGED ({sum(left.values())} rows - real failures, untouched):"]
    for a, b in sorted(left.items(), key=lambda kv: -kv[1]):
        L.append(f"     {b:>5}  {a}")

    # ---------------------------------------------------------------- backup, then write
    L += ["", "=" * 68, "BACKUP AND WRITE", "=" * 68]
    before = sha(STATE)
    L.append(f"  clv/state.enc SHA-256 before: {before}")
    L.append(f"  size: {os.path.getsize(STATE)} bytes")

    if not APPLY:
        L += ["", "  DRY RUN - no backup taken, no flag cleared, state.enc untouched.",
              "  Re-dispatch with APPLY=1 to perform the reset."]
    elif len(pick) != 74:
        L += ["", "  ABORTED - selection count did not match the authorised 74. State untouched."]
    else:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        dest = f"{BACKUP_DIR}/state-{now:%Y%m%dT%H%M%S}Z.enc"
        shutil.copy2(STATE, dest)
        bsha = sha(dest)
        L.append(f"  backup written: {dest}")
        L.append(f"  backup SHA-256:               {bsha}")
        if bsha != before:
            L += ["", "  *** BACKUP DIGEST MISMATCH - ABORTED, state.enc untouched."]
            ex.send("Bets CLV RECOVERY RESET (ABORTED)", "\n".join(L))
            print(f"clv reset ABORTED: backup digest mismatch")
            return
        L.append("  digests match - the baseline is recoverable byte-for-byte.")
        for k, r in pick:
            r["done"] = False
            r["tries"] = 0
            r.pop("why", None)            # stale reason removed so the next run records a fresh one
        json.dump(tb.enc(st), open(STATE, "w"))
        L += [f"  cleared done and reset tries on {len(pick)} rows.",
              f"  clv/state.enc SHA-256 after:  {sha(STATE)}",
              f"  size after: {os.path.getsize(STATE)} bytes",
              "",
              "  The next routine clv-ledger run will attempt these with FETCH_DAYS=45. Credits are",
              f"  billed only by /fixtures; month-to-date before this run: {(st.get('billable') or {}).get(f'{now:%Y-%m}', 0)}."]

    L += ["", "No CLV calculation, basis, lane, staking or execution path was changed by this script.",
          "ProphetX identification remains a separate track and no ProphetX row was reset."]
    body = "\n".join(L)
    ex.send(f"Bets CLV RECOVERY RESET ({'applied' if APPLY and len(pick) == 74 else 'dry run'})", body)
    print(f"clv reset: selected {len(pick)}, excluded-near {len(near)}, apply={APPLY}")   # counts only


if __name__ == "__main__":
    main()

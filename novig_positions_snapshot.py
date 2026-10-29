#!/usr/bin/env python3
"""
Novig positions snapshot (Oct 27, 2026). Runs every 5 min on Peter's home PC (self-hosted runner, PRIVATE repo), because
Novig's compliance provider blocks cloud servers (HTTP 451) on some runs. Reads open positions READ-ONLY (main wallet +
the auto-place sub-wallet) with the management::read key, and writes them to snapshot/novig_positions.json in THIS
private repo. The cloud executor reads that file only when its own Novig read fails; a snapshot older than 15 minutes
counts as unreadable (plays held, never blind fills).
Oct 29: also writes wallet balances (main + sub-accounts) for the private balances email.\nLog: counts only. Nothing is placed, changed or cancelled here (novig_signed.py has no write path).
"""
import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import novig_signed as nv

PATH = "snapshot/novig_positions.json"


def read_positions():
    if not nv.ready():
        raise RuntimeError("read key not ready")
    out = []
    for kid in dict.fromkeys([nv._S["id"], (os.environ.get("NOVIG_TRADE_KEY_ID") or "").strip()]):
        if not kid:
            continue
        d = nv.get("/v3/portfolio/positions", {"keyId": kid})   # main wallet + auto-place sub-wallet (same as the executor)
        for v in (d.values() if isinstance(d, dict) else [d]):
            out += v if isinstance(v, list) else (v.get("items") or [] if isinstance(v, dict) else [])
    return [p for p in out if int(p.get("qty") or 0) > 0]


def gh(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "novig-snapshot"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode() or "{}")


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        pos, err = read_positions(), None
    except Exception as ex:
        pos, err = None, str(ex)[:200]
    snap = {"snapshot_utc": now, "ok": pos is not None, "error": err, "positions": pos or []}
    try:   # Oct 29: wallet balances for the private balances email (main + sub-accounts such as auto-place)
        subs = nv.get("/v3/account/subaccounts")
        items = subs.get("items") if isinstance(subs, dict) else subs
        snap["balances"] = {"main": nv.get("/v3/account/balance").get("balance"),
                            "subaccounts": [{"label": s.get("label"), "keyId": s.get("keyId"), "balance": s.get("balance")}
                                            for s in items or []]}
    except Exception as ex:
        snap["balances_error"] = str(ex)[:160]
    api = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/contents/{PATH}"
    try:
        sha = gh("GET", api + "?ref=main").get("sha")
    except Exception:
        sha = None   # first run: the file doesn't exist yet
    body = {"message": f"Novig positions snapshot {now}", "branch": "main",
            "content": base64.b64encode(json.dumps(snap, indent=1).encode()).decode()}
    if sha:
        body["sha"] = sha
    gh("PUT", api, body)
    print(f"Snapshot {now}: read {'OK' if pos is not None else 'FAILED'}; {len(pos or [])} open positions")   # counts only
    if pos is None:
        print(f"   read error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

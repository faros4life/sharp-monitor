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
        got = []
        for v in (d.values() if isinstance(d, dict) else [d]):
            got += v if isinstance(v, list) else (v.get("items") or [] if isinstance(v, dict) else [])
        for p in got:   # Nov 1: which wallet (main = Peter, sub = the bot's auto-place) for the private tracker
            if isinstance(p, dict):
                p["wallet"] = "main" if kid == nv._S["id"] else "sub"
        out += got
    return [p for p in out if int(p.get("qty") or 0) > 0]


def _paged(path, params, max_pages=20):
    out, after = [], None
    for _ in range(max_pages):
        d = nv.get(path, dict(params, **({"after": after} if after else {})))
        if isinstance(d, dict) and "items" in d:
            items, after = d["items"], d.get("next")
        elif isinstance(d, dict):
            items, after = [], None
            for v in d.values():
                if isinstance(v, dict):
                    items += v.get("items") or []
                    after = after or v.get("next")
                elif isinstance(v, list):
                    items += v
        else:
            items, after = (d or []), None
        out += items
        if not after:
            break
    return out


def read_settled(prev):
    """Nov 1 (Peter's private bet tracker): settled bets of the last 35 days, main wallet + every sub-wallet (auto-place),
    with Novig's own cost / payout / pnl (site numbers). Labels are looked up once and carried over from the previous
    snapshot. Read-only GETs."""
    cut = (datetime.now(timezone.utc).timestamp() - 35 * 86400) * 1000
    known = {r["id"]: r for r in (prev or []) if r.get("label")}
    kids = [nv._S["id"]]
    try:
        d = nv.get("/v3/account/subaccounts")
        kids += [x.get("keyId") for x in ((d.get("items") if isinstance(d, dict) else d) or []) if x.get("keyId")]
    except Exception:
        pass
    out, mk_cache, ev_cache = [], {}, {}
    for kid in dict.fromkeys(kids):
        for p in _paged("/v3/history/positions", {"keyId": kid, "status": "SETTLED", "limit": 1000}):
            ts = int(p.get("settledTs") or 0)
            if ts < cut:
                continue
            pid = f"{kid}|{p.get('marketId')}|{p.get('outcomeId')}|{ts}"
            row = {"id": pid, "wallet": "main" if kid == nv._S["id"] else "sub", "settledTs": ts,
                   "result": str(p.get("result") or "").upper(), "cost": p.get("cost"), "payout": p.get("payout"),
                   "pnl": p.get("pnl"), "marketId": p.get("marketId"), "outcomeId": p.get("outcomeId")}
            if pid in known:
                row.update({k: known[pid].get(k) for k in ("label", "game", "league", "start")})
            else:
                try:
                    mid = p.get("marketId")
                    if mid not in mk_cache:
                        mk_cache[mid] = nv.get(f"/v3/history/markets/{mid}") or {}
                    m = mk_cache[mid]
                    eid = m.get("eventId")
                    if eid and eid not in ev_cache:
                        ev_cache[eid] = nv.get(f"/v3/history/events/{eid}") or {}
                    e = ev_cache.get(eid) or {}
                    side = next((o.get("name") for o in m.get("outcomes") or [] if o.get("outcomeId") == p.get("outcomeId")), "?")
                    strike = m.get("strike")
                    mt = str(m.get("marketType") or "").upper()
                    if mt == "TOTAL" and strike is not None and not any(ch.isdigit() for ch in side):
                        side = f"{side} {strike}"
                    row.update({"label": side, "game": e.get("description") or m.get("description") or "",
                                "league": e.get("league") or "", "start": e.get("startTime") or e.get("startTs")})
                except Exception:
                    pass
            out.append(row)
    return out


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
    prev = {}
    try:
        cur = gh("GET", api + "?ref=main")
        sha = cur.get("sha")
        prev = json.loads(base64.b64decode(cur.get("content") or "").decode() or "{}")
    except Exception:
        sha = None   # first run: the file doesn't exist yet
    try:   # Nov 1: settled history for the private bet tracker (labels carried over, so later runs are cheap)
        snap["settled"] = read_settled(prev.get("settled"))
    except Exception as ex:
        snap["settled"] = prev.get("settled") or []
        snap["settled_error"] = str(ex)[:160]
    body = {"message": f"Novig positions snapshot {now}", "branch": "main",
            "content": base64.b64encode(json.dumps(snap, indent=1).encode()).decode()}
    if sha:
        body["sha"] = sha
    gh("PUT", api, body)
    print(f"Snapshot {now}: read {'OK' if pos is not None else 'FAILED'}; {len(pos or [])} open positions; "
          f"{len(snap.get('settled') or [])} settled (35 days)")   # counts only
    if pos is None:
        print(f"   read error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

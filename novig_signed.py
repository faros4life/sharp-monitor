"""
Novig signed READ-ONLY client (NOVIG-V3 signing, Ed25519/P-256).

Safety, by construction:
  * GET only. There is no code path that sends POST/PUT/PATCH/DELETE, so it cannot place, change or cancel
    an order, move money, or create/revoke keys, whatever key it is given.
  * Fails closed: before any other call, it reads its own key record and refuses to run unless the scope is
    exactly 'management::read' (or 'trading::read'). A write-scoped key stops everything.
  * Keys come only from environment variables (GitHub Actions secrets NOVIG_READ_KEY_ID / NOVIG_READ_KEY_PEM).
    Nothing here prints or writes the key.
"""
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = os.environ.get("NOVIG_API", "") or "https://api.novig.com"
READ_SCOPES = {"management::read", "trading::read"}
_UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_S = {"key": None, "id": None, "skew": 0, "ok": None, "scope": None}


class NovigReadError(Exception):
    pass


def _enc(s):
    return "".join(c if c in _UNRESERVED else "".join(f"%{b:02X}" for b in c.encode()) for c in s)


def canonical_query(q):
    pairs = []
    for part in (q or "").split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        k, v = urllib.parse.unquote_plus(k), urllib.parse.unquote_plus(v)
        if k in ("Expires", "Key-Pair-Id", "Policy", "Signature"):
            continue
        pairs.append((_enc(k), _enc(v)))
    return "&".join(f"{k}={v}" for k, v in sorted(pairs))


def _load():
    if _S["key"] is not None:
        return True
    kid, pem = os.environ.get("NOVIG_READ_KEY_ID", "").strip(), os.environ.get("NOVIG_READ_KEY_PEM", "")
    if not kid or "PRIVATE KEY" not in pem:
        return False
    from cryptography.hazmat.primitives import serialization
    _S["key"] = serialization.load_pem_private_key(pem.replace("\\n", "\n").encode(), password=None)
    _S["id"] = kid
    return True


def _sign(msg):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519
    k = _S["key"]
    return k.sign(msg) if isinstance(k, ed25519.Ed25519PrivateKey) else k.sign(msg, ec.ECDSA(hashes.SHA256()))


def _get(path, params=None):
    """The ONLY request function: signed GET."""
    q = urllib.parse.urlencode(params or {}, doseq=True)
    ts = str(int(time.time() * 1000) + _S["skew"])
    msg = "\n".join(["NOVIG-V3", ts, "GET", path, canonical_query(q), hashlib.sha256(b"").hexdigest()]).encode()
    req = urllib.request.Request(HOST + path + ("?" + q if q else ""), method="GET", headers={
        "Accept": "application/json", "Content-Type": "application/json",
        "Novig-Key-Id": _S["id"], "Novig-Timestamp": ts, "Novig-Signature": base64.b64encode(_sign(msg)).decode()})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            t = r.read().decode()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as ex:
        raise NovigReadError(f"HTTP {ex.code} on GET {path}: {ex.read().decode()[:160]}")


def ready():
    """True only when the key loads AND Novig confirms it is read-only. Checked once per run; fails closed."""
    if _S["ok"] is not None:
        return _S["ok"]
    _S["ok"] = False
    try:
        if not _load():
            return False
        try:
            t = _get("/v3/time")
            _S["skew"] = int(t.get("ts")) - int(time.time() * 1000) if t.get("ts") else 0
        except Exception:
            _S["skew"] = 0
        info = _get(f"/v3/keys/{_S['id']}")
        _S["scope"] = info.get("scope")
        if _S["scope"] not in READ_SCOPES:
            print(f"Novig signed reads DISABLED: key scope is '{_S['scope']}', not read-only")
            return False
        _S["ok"] = True
    except Exception as ex:
        print(f"Novig signed reads unavailable: {str(ex)[:160]}")
    return _S["ok"]


def get(path, params=None):
    if not ready():
        raise NovigReadError("signed reads not available (no key, or key is not read-only)")
    return _get(path, params)


def scope():
    return _S["scope"]

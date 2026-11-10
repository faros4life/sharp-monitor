#!/usr/bin/env python3
"""NETWORK ALLOW-LIST for read-only audit jobs (CLV forensic, 10 Nov 2026). Stdlib only, no secrets.

Why: CACHE_ONLY=1 inside a script is a convention, not a guarantee. clv_ledger.load_markets() bills when
the market map is 7+ days old, hist_cache.get_hist() fetches any uncached or not-yet-final game, and
plimit-level spent unapproved credits that way on Nov 6. This blocks the CONNECTION, not the call site:
every outbound name resolution or connect to a host that is not on the allow-list raises, whoever
asked, whatever the flag says. Every refusal is counted by host so the run can report it.
Install it FIRST, before any project import.
"""
import socket

BLOCKED = {}


class NetworkBlocked(RuntimeError):
    """An audit job tried to reach a host outside its allow-list."""


def _host(h):
    return (h.decode() if isinstance(h, bytes) else str(h or "")).strip().lower().rstrip(".")


def install(allow=("smtp.gmail.com",), loopback=False):
    ok = {a.lower() for a in allow}
    orig_gai, orig_conn, orig_cc = socket.getaddrinfo, socket.socket.connect, socket.create_connection

    def permitted(host):
        h = _host(host)
        return h in ok or (loopback and h in ("localhost", "127.0.0.1", "::1", ""))

    def refuse(host):
        h = _host(host) or "(unknown)"
        BLOCKED[h] = BLOCKED.get(h, 0) + 1
        raise NetworkBlocked(f"outbound connection to {h!r} refused: read-only audit, allow-list {sorted(ok)}")

    def gai(host, *a, **k):
        if not permitted(host):
            refuse(host)
        return orig_gai(host, *a, **k)

    def cc(address, *a, **k):
        if not permitted(address[0]):
            refuse(address[0])
        return orig_cc(address, *a, **k)

    def conn(self, address):
        # numeric addresses reach here without getaddrinfo; allow only loopback and AF_UNIX
        if isinstance(address, tuple) and not permitted(address[0]) and address[0] not in ok:
            # an IP we resolved for an allowed host is fine; anything else is not knowable here
            if not _resolved_ok(address[0], ok, orig_gai):
                refuse(address[0])
        return orig_conn(self, address)

    socket.getaddrinfo, socket.create_connection, socket.socket.connect = gai, cc, conn
    return ok


def _resolved_ok(ip, ok, gai):
    for h in ok:
        try:
            if any(x[4][0] == ip for x in gai(h, None)):
                return True
        except OSError:
            pass
    return False


def report():
    return dict(BLOCKED)


def refuse_if_proxied(env):
    """A proxy would carry traffic the connect-level check cannot attribute to a destination host."""
    bad = [k for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy") if env.get(k)]
    if bad:
        raise NetworkBlocked(f"proxy environment set ({', '.join(bad)}): refusing to run an audit whose "
                             f"destinations cannot be verified")

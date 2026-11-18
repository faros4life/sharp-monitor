"""Socket guard injected into every test subprocess by run_tests.py (Peter, Nov 18).

WHY. A suite that reaches the network is not testing this repo, it is testing what the network happened
to answer. Worse than that: on 18 Nov a socket audit of the suite found three files dialling out, and two
of them were attempting a WRITE to the live order registry -

  test_email_suppression -> executor.journal_intent -> registry.invalidate -> _commit -> PUT
                            {API}/repos/{REPO}/contents/{PATH}
  test_intent_void       -> executor.refuse_untransmitted -> void_intent -> the same path
  test_credit_gate       -> credit_gate.reserve -> credits.account -> clv_ledger.api("/account")

The registry is the bot-order record the daily stop counts against. The only thing stopping that PUT was
the agent proxy refusing the GitHub contents-write API - an infrastructure quirk noted in CLAUDE.md, not
a safety control. If that refusal ever lifts, the test suite writes to production. This file makes the
refusal a property of the suite instead.

The calls already failed, so the guard does not change any test's outcome - it makes the failure
deterministic and local instead of dependent on what the proxy does that day, and it makes the next test
that reaches for the network say so out loud.

Not imported by the code under test, and no part of the live path.
"""
import os
import socket

_ALLOWED_HOSTS = ("127.0.0.1", "::1", "localhost")

# Blocking non-loopback sockets is NOT enough on its own, and the first version of this file was a no-op
# that looked like success: every outbound request in this environment goes through an agent proxy on
# 127.0.0.1, so urllib connected to loopback - which the socket rule allows - and the proxy fetched
# api.github.com quite happily. The suite stayed green because the guard did nothing. So the proxy route
# is removed first, and only then does the socket rule have anything to catch.
_PROXY_VARS = ("http_proxy", "https_proxy", "all_proxy", "no_proxy", "ftp_proxy",
               "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "FTP_PROXY")


class NetworkUseInTest(RuntimeError):
    """A test tried to open a socket. Stub the call instead - see tests_no_net.py."""


def _blocked(addr):
    host = addr[0] if isinstance(addr, (tuple, list)) and addr else addr
    # a unix socket or anything we cannot read is left alone; only IP destinations are judged
    return isinstance(host, str) and host not in _ALLOWED_HOSTS


def install():
    """Block outbound network for this process. Loopback stays open so a local stub server still works."""
    for v in _PROXY_VARS:
        os.environ.pop(v, None)
    _orig_connect = socket.socket.connect
    _orig_connect_ex = socket.socket.connect_ex
    _orig_create = socket.create_connection

    def connect(self, addr, *a, **k):
        if _blocked(addr):
            raise NetworkUseInTest(f"test opened a network socket to {addr} - stub it (tests_no_net.py)")
        return _orig_connect(self, addr, *a, **k)

    def connect_ex(self, addr, *a, **k):
        if _blocked(addr):
            raise NetworkUseInTest(f"test opened a network socket to {addr} - stub it (tests_no_net.py)")
        return _orig_connect_ex(self, addr, *a, **k)

    def create_connection(addr, *a, **k):
        if _blocked(addr):
            raise NetworkUseInTest(f"test opened a network socket to {addr} - stub it (tests_no_net.py)")
        return _orig_create(addr, *a, **k)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.create_connection = create_connection


install()

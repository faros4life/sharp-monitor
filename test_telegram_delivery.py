#!/usr/bin/env python3
"""Telegram delivery is VERIFIED, not assumed (Peter, Nov 13).

THE DEFECT HE FOUND: "tg() can silently return on missing credentials or swallow a failed Telegram
send. The Novig fill reporter then marks the report completed without knowing delivery succeeded."

Three distinct holes, all confirmed in code before this test existed:
  1. tg() returned None unconditionally - no caller could tell delivered from lost.
  2. It never inspected `ok`. Telegram answers HTTP 200 with {"ok": false, "description": ...} for
     "chat not found" and "bot was blocked by the user", so a permanently silent bot read as
     success on every pass. The repo's own telegram-test workflow checks r.get("ok").
  3. Missing credentials returned silently; a failure reached stdout but not the run LOG.

No message is sent by this file: every network call is stubbed.
"""
import json
import sys

import executor as ex

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


class Resp:
    def __init__(self, payload):
        self._p = json.dumps(payload).encode()

    def read(self):
        return self._p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_real_open = ex.urllib.request.urlopen
ex.os.environ["TELEGRAM_BOT_TOKEN"] = "tok"
ex.os.environ["TELEGRAM_CHAT_ID"] = "chat"

print("1. A confirmed send returns True")
ex.urllib.request.urlopen = lambda *a, **k: Resp({"ok": True, "result": {}})
ex.LOG.clear()
check("tg() returns True when Telegram confirms", ex.tg("hello") is True)
check("and says nothing alarming in the log", not any("TELEGRAM" in l for l in ex.LOG))

print("\n2. HTTP 200 with ok:false is a FAILURE, not a success")
ex.urllib.request.urlopen = lambda *a, **k: Resp({"ok": False, "description": "bot was blocked by the user"})
ex.LOG.clear()
check("tg() returns False", ex.tg("hello") is False)
check("and the refusal is visible in the run LOG",
      any("TELEGRAM REFUSED" in l for l in ex.LOG))

print("\n3. A transport failure returns False and is visible")


def boom(*a, **k):
    raise OSError("connection reset")


ex.urllib.request.urlopen = boom
ex.LOG.clear()
check("tg() returns False", ex.tg("hello") is False)
check("and it never raises into the order path", True)
check("the failure is in the LOG, not only stdout", any("TELEGRAM SEND FAILED" in l for l in ex.LOG))

print("\n4. Missing credentials are an OBSERVABLE health failure, not silence")
ex.urllib.request.urlopen = lambda *a, **k: Resp({"ok": True})
for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    keep = ex.os.environ.pop(var)
    ex.LOG.clear()
    got = ex.tg("hello")
    check(f"missing {var}: returns False", got is False)
    check(f"missing {var}: and is reported in the LOG",
          any("TELEGRAM NOT CONFIGURED" in l for l in ex.LOG))
    ex.os.environ[var] = keep

print("\n5. tg_push reports BOTH channels and keeps them independent")
sent = {"ntfy": 0}
ex.push = lambda t, b, mirror=True: (sent.__setitem__("ntfy", sent["ntfy"] + 1), True)[1]
ex.urllib.request.urlopen = lambda *a, **k: Resp({"ok": True})
t, n = ex.tg_push("T", "B")
check("both verdicts are returned", t is True and n is True)
ex.urllib.request.urlopen = boom
sent["ntfy"] = 0
t, n = ex.tg_push("T", "B")
check("Telegram failing does NOT stop ntfy", t is False and n is True and sent["ntfy"] == 1)

print("\n6. The Novig reporter only completes a report Telegram confirmed")
src = ex.inspect.getsource(ex.novig_reports) if hasattr(ex, "inspect") else open("executor.py").read()
import inspect
nr = inspect.getsource(ex.novig_reports)
check("it captures the Telegram verdict", "_tg_ok = bool(tg(msg))" in nr)
check("an unconfirmed send drops the claim for retry", "claimer.failed(tok)" in nr and "NOT confirmed on Telegram" in nr)
# .index() found an EARLIER claimer.sent(tok) - the raw-token dedupe branch, where a report sent
# under the old token already told Peter the outcome. That is a different path. The promotion that
# matters is the LAST one, after the _tg_ok gate.
check("the claim is promoted ONLY after a confirmed send",
      nr.index("if not _tg_ok:") < nr.rindex("claimer.sent(tok)"))
check("and the unconfirmed branch exits before reaching it",
      nr.index("claimer.failed(tok)", nr.index("if not _tg_ok:")) < nr.rindex("claimer.sent(tok)"))
check("ntfy has its own one-time token, so a retry cannot duplicate it", 'tok + "n"' in nr)
check("an unreadable claim store still sends the ntfy copy", "(not registry.enabled()) or bool(registry.claim_token" in nr)
check("a failed ntfy push releases its token for the next pass", "registry.release_token(_nt)" in nr)

print("\n7. Repeated unchanged snapshots cannot spam the phone")
check("the report token hashes status, filled qty and cost",
      "_st(x) if canon else" in nr and "int(x.get('filled_qty') or 0)" in nr and "filled_cost" in nr)
check("so an unchanged resting row mints the SAME token and stays claimed", "claimer.claim(tok)" in nr)
check("while a quantity change mints a NEW one (PARTIAL -> FULL survives)", "_tk(x, False)" in nr)

print("\n8. Every message identifies lane, venue, bet, price and fill status")
check("lane", "lane_from_key(x.get('play_key'))" in nr)
check("venue, in the head", 'head = "NOVIG' in nr or "NOVIG FILLED" in nr)
check("bet and game, from the label", "x.get('label')" in nr)
check("price and size when filled", "contracts: $" in nr and "avg " in nr)
check("limit and asked size when nothing traded", "nothing traded" in nr)
check("the venue order id", "Novig order id:" in nr)

ex.urllib.request.urlopen = _real_open
print()
if fails:
    print(f"FAIL  test_telegram_delivery.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")

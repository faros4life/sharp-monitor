#!/usr/bin/env python3
"""Nov 23 (Peter, priority 1): ntfy and Telegram delivery is COUNTED, failures are LOGGED, and an error on a live play
reaches both channels. Offline: urlopen is stubbed, nothing is sent."""
import io
import os
import sys

os.environ["NTFY_TOPIC"] = "test-topic"
os.environ["TELEGRAM_BOT_TOKEN"] = "t"
os.environ["TELEGRAM_CHAT_ID"] = "c"
import executor as ex   # noqa: E402

FAILED, RAN = [], []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got != "" else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


class Resp(io.BytesIO):
    def __init__(self, body=b"{}", status=200):
        super().__init__(body)
        self.status = status


real = ex.urllib.request.urlopen
try:
    sent = []

    def good(req, timeout=15):
        sent.append(req.full_url)
        return Resp(b'{"ok": true}' if "telegram" in req.full_url else b"{}")
    ex.urllib.request.urlopen = good
    ex.NOTIFY.clear(); ex.LOG.clear()
    ok("ntfy push returns True on a 200", ex.push("t", "b", mirror=False) is True)
    ok("...and is counted as delivered", ex.NOTIFY[("ntfy", "delivered")] == 1, dict(ex.NOTIFY))
    t, n = ex.tg_push("T", "x")
    ok("tg_push: both channels delivered and counted", t and n and ex.NOTIFY[("telegram", "delivered")] == 1
       and ex.NOTIFY[("ntfy", "delivered")] == 2, dict(ex.NOTIFY))

    def down(req, timeout=15):
        raise OSError("network down")
    ex.urllib.request.urlopen = down
    ex.NOTIFY.clear(); ex.LOG.clear()
    t, n = ex.tg_push("T", "x")
    ok("both channels down: tg_push reports both failed", (t, n) == (False, False))
    ok("...counted as FAILED on each channel", ex.NOTIFY[("ntfy", "FAILED")] == 1 and ex.NOTIFY[("telegram", "FAILED")] == 1,
       dict(ex.NOTIFY))
    ok("...and named in the run LOG (no message content)", any("NTFY SEND FAILED" in l for l in ex.LOG)
       and any("TELEGRAM SEND FAILED" in l for l in ex.LOG), ex.LOG)

    def refused(req, timeout=15):
        return Resp(b'{"ok": false, "description": "chat not found"}')
    ex.urllib.request.urlopen = refused
    ex.NOTIFY.clear()
    ok("Telegram 200 with ok:false is a FAILURE, not a delivery", ex.tg("x") is False and ex.NOTIFY[("telegram", "FAILED")] == 1)

    ex.urllib.request.urlopen = lambda req, timeout=15: Resp(b"", status=500)
    ex.NOTIFY.clear()
    ok("ntfy non-2xx is not delivered", ex.push("t", "b", mirror=False) is False and ex.NOTIFY[("ntfy", "HTTP not ok")] == 1)

    os.environ["NTFY_TOPIC"] = ""
    ex.NOTIFY.clear(); ex.LOG.clear()
    ok("no ntfy topic: not delivered, counted and logged", ex.push("t", "b", mirror=False) is False
       and ex.NOTIFY[("ntfy", "NOT CONFIGURED")] == 1 and any("NTFY NOT CONFIGURED" in l for l in ex.LOG))
finally:
    ex.urllib.request.urlopen = real
    os.environ["NTFY_TOPIC"] = "test-topic"

SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor.py")).read()
H = SRC.split('"verdict": "SKIP", "reason": f"error: {str(ex)[:100]}"})')[1][:900]
ok("a per-play error with live on alerts BOTH channels", "if px_live.LIVE:" in H and "tg_push(" in H and "LIVE PLAY ERROR" in H)
ok("...and the alert can never break the run", "except Exception as _nx:" in H)
ok("the run prints delivery counts in the public log", 'print("notifications (counts only): "' in SRC)

print(f"\n{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)

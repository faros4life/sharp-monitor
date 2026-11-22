#!/usr/bin/env python3
"""Peter, Nov 22 2026: "I don't need paper or research to telegram."

The VALUE LAB LAST-50 report was being chunked onto the live alert feed every morning at 5:24 ET,
plus a CSV attachment, because a rule about Claude READING Peter's mailbox had been applied to
SENDING. These checks are the guard against it creeping back: a research reporter that regains a
Telegram path, or a workflow that regains the Telegram secrets, fails here.
"""
import os
import re
import sys

FAILED = []
RAN = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


HERE = os.path.dirname(os.path.abspath(__file__))


def read(p):
    with open(os.path.join(HERE, p), encoding="utf-8") as f:
        return f.read()


# --- research reporters and the liquidity scan lane carry no Telegram path at all -------------
# liquidity_monitor is checked by SOURCE, not by import: importing it does live-trading setup.
for mod in ("last50_report.py", "clv_report.py", "liquidity_monitor.py"):
    src = read(mod)
    ok(f"{mod}: no Telegram credentials read", "TELEGRAM_BOT_TOKEN" not in src and "TELEGRAM_CHAT_ID" not in src)
    ok(f"{mod}: no Telegram API call", "api.telegram.org" not in src)
    ok(f"{mod}: no sendMessage/sendDocument", "sendMessage" not in src and "sendDocument" not in src)

liq = read("liquidity_monitor.py")
ok("liquidity_monitor: tg_mirror deleted, not merely unused", "def tg_mirror" not in liq)
ok("liquidity_monitor: still pushes to ntfy", "ntfy.sh" in liq)

for w in ("liquidity-monitor.yml", "liquidity-extra.yml"):
    wsrc = read(os.path.join(".github/workflows", w))
    ok(f"{w}: TELEGRAM secrets not passed",
       "secrets.TELEGRAM_BOT_TOKEN" not in wsrc and "secrets.TELEGRAM_CHAT_ID" not in wsrc)

mt = read(".github/workflows/telegram-mirror-test.yml")
ok("telegram-mirror-test: no longer previews liquidity", "liquidity_monitor" not in mt)
ok("telegram-mirror-test: still previews sharp alerts", "sharp_monitor" in mt)

# --- the workflow does not hand it the Telegram secrets --------------------------------------
wf = read(".github/workflows/last50-report.yml")
ok("last50-report.yml: TELEGRAM secrets not passed",
   "secrets.TELEGRAM_BOT_TOKEN" not in wf and "secrets.TELEGRAM_CHAT_ID" not in wf)
ok("last50-report.yml: email secrets ARE passed",
   all(s in wf for s in ("secrets.GMAIL_ADDRESS", "secrets.GMAIL_APP_PASSWORD", "secrets.EMAIL_TO")))
ok("last50-report.yml: still read-only permissions", re.search(r"contents:\s*read", wf) is not None)

# --- delivery is wired, and a dead reporter is still loud ------------------------------------
import last50_report as L50

ok("send_report exists", callable(getattr(L50, "send_report", None)))
ok("old send_telegram is gone", getattr(L50, "send_telegram", None) is None)
ok("main() delivers through send_report", "send_report(" in read("last50_report.py"))

saved = {k: os.environ.pop(k, None) for k in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "EMAIL_TO")}
try:
    ok("unconfigured email returns False (so main exits non-zero)",
       L50.send_report("body", [{"test": "x"}]) is False)
finally:
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v

ok("CSV columns unchanged from the Telegram-era attachment",
   L50.CSV_COLS == ["test", "half", "ts", "game", "price_am", "result", "certified_clv_pct",
                    "provisional_clv_pct_not_certified", "provisional_source"], str(L50.CSV_COLS))

# --- Peter, Nov 22: "Alert the play and what happens to it." -------------------------------
# Telegram carries a play and that play's outcome. Diagnostics and agent watchdogs do not.
knp = read("kalshi_no_proof.py")
ok("kalshi_no_proof: no Telegram (diagnostic, not a play)", "ex.tg(" not in knp)
ok("kalshi_no_proof: still emails", "ex.send(" in knp)

ex_src = read("executor.py")
ok("NO MUSE VERDICT no longer goes to Telegram (agent watchdog, not a play outcome)",
   'tg("NO MUSE VERDICT' not in ex_src)
ok("NO MUSE VERDICT still pushes to ntfy", 'push("No Muse verdict: ' in ex_src)

# --- and what MUST still reach Telegram: the play, and what happens to it --------------------
for needle, what in (('tg_push("ORDER REFUSED"', "ORDER REFUSED"),
                     ('tg_push("ORDER FAILED"', "ORDER FAILED"),
                     ('tg_push("DUPLICATE BLOCKED"', "DUPLICATE BLOCKED"),
                     ('tg_push("CLAIM UNAVAILABLE"', "CLAIM UNAVAILABLE"),
                     ("RESTING BID", "resting bid")):
    ok(f"still alerted: {what}", needle in ex_src)

bal = read("balances.py")
ok("still alerted: NEW POSITIONS fills (Peter, Nov 12: 'i want if something gets filled')",
   "ex.tg(msg)" in bal and "NEW POSITIONS" in bal)

sm = read("sharp_monitor.py")
ok("sharp_monitor still mirrors a live phase-1 trigger", "if TG_SHARP or live:" in sm)

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)

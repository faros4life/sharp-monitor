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


# --- the research reporters carry no Telegram path at all -----------------------------------
for mod in ("last50_report.py", "clv_report.py"):
    src = read(mod)
    ok(f"{mod}: no Telegram credentials read", "TELEGRAM_BOT_TOKEN" not in src and "TELEGRAM_CHAT_ID" not in src)
    ok(f"{mod}: no Telegram API call", "api.telegram.org" not in src)
    ok(f"{mod}: no sendMessage/sendDocument", "sendMessage" not in src and "sendDocument" not in src)

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

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)

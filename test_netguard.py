#!/usr/bin/env python3
"""The audit job's network lock must refuse OddsPapi and anything else off the allow-list. Own process only."""
import sys
import netguard
netguard.install(allow=("smtp.gmail.com",))
import urllib.request

bad = 0
for url in ("https://api.oddspapi.io/v4/markets?apiKey=x", "https://gamma-api.polymarket.com/", "http://127.0.0.1:9/"):
    try:
        urllib.request.urlopen(url, timeout=2)
        print("  [FAIL] reached", url); bad += 1
    except netguard.NetworkBlocked:
        print("  [PASS] refused", url)
    except Exception as e:
        print("  [FAIL] other error", type(e).__name__, url); bad += 1
try:
    netguard.refuse_if_proxied({"HTTPS_PROXY": "http://x"})
    print("  [FAIL] proxy accepted"); bad += 1
except netguard.NetworkBlocked:
    print("  [PASS] proxy environment refused")
print("refusals:", netguard.report())
sys.exit(1 if bad else 0)

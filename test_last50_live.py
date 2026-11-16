#!/usr/bin/env python3
"""Offline end-to-end: the last-50 report with synthetic ENCRYPTED ledger / tracker / clv / slowhr files.
No network: ESPN finals are stubbed, Telegram is unconfigured. Checks the live section is driven by the ledger."""
import json
import os
import shutil
import sys
import tempfile

os.environ["TRACKER_PASSPHRASE"] = "synthetic-test-only"
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
HERE = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def check(n, c):
    if not c:
        FAILS.append(n)


tmp = tempfile.mkdtemp()
for f in os.listdir(HERE):
    if f.endswith((".py", ".md", ".json")):
        os.symlink(os.path.join(HERE, f), os.path.join(tmp, f))
for d in ("liquidity", "liquidity-extra", "lanes", "board"):
    if os.path.isdir(os.path.join(HERE, d)):
        os.symlink(os.path.join(HERE, d), os.path.join(tmp, d))
for d in ("reporting", "tracker", "clv", "slowhr"):
    os.makedirs(os.path.join(tmp, d))
os.chdir(tmp)
sys.path.insert(0, HERE)
import tracker_build as tb   # noqa: E402

import test_live_ledger as T  # noqa: E402  (reuses its synthetic ledger + tracker)
json.dump(tb.enc(T.L), open("reporting/ledger.enc", "w"))
json.dump(tb.enc({"bets": T.B}), open(tb.STATE, "w"))
json.dump(tb.enc({"bets": T.C}), open("clv/state.enc", "w"))
NAMES = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima"]
S = [{"kind": "P", "type": "moneyline", "hr_am": 150, "hr_price": 2.5, "ev_pct": 3.0, "late": False,
      "league": "NHL", "game": f"{NAMES[i]} Hawks vs {NAMES[i]} Owls", "team": f"{NAMES[i]} Hawks", "side": "1",
      "start": f"2026-11-{8 + i % 8:02d}T23:00:00Z", "t_move": f"2026-11-{8 + i % 8:02d}T20:{i:02d}:00Z",
      "t_confirm": f"2026-11-{8 + i % 8:02d}T20:{i:02d}:00Z", "close_fair": 0.42} for i in range(12)]
S.append(dict(S[0], hr_am=-120, team="fav"))           # favourite: not in the cell
S.append(dict(S[1], ev_pct=1.0, game="Other X vs Other Y"))   # EV under 2: not in the cell
S.append(dict(S[2], hr_am=350, game="Long A vs Long B"))      # in SLOW-HR, outside DOG BAND
json.dump(tb.enc({"sightings": S}), open("slowhr/state.enc", "w"))

import finals  # noqa: E402
finals.result = lambda x: "W"
import last50_report as r  # noqa: E402
os.environ["LAST50_PRINT"] = "0"
r.main()
out = "\n".join(r.L)

check("live section decrypted", "UNANSWERED: reporting ledger" not in out)
check("R1 lane block present with plays", "R1 - live fills" in out and "NCAAF|Minnesota" in out)
check("Board play counted via order-id", "COUNTED" in out and "Milwaukee vs Orlando" in out and "E1 order-id" in out)
check("unresolved listed", "UNRESOLVED" in out and "Charlotte vs Phoenix" in out)
check("excluded listed", "EXCLUDED" in out and "voided intent" in out)
check("resting bids block", "RESTING BIDS (reg 2)" in out)
check("Peter feed block", "PETER - FEED PLAYS (reg 3)" in out)
check("Street Value block", "STREET VALUE (reg 5)" in out)
check("slow-hr graded", "SLOW-HR (reg 11) - registered cell" in out and "DOG BAND (reg 12)" in out)
sh = r.slowhr_rows(False)
db = r.slowhr_rows(True)
check("slow-hr cell rule", len(sh) == 13)
check("dog band band + date rule", len(db) == 12)
check("live before paper", out.index("LIVE - actual") < out.index("PAPER - TOP 5"))
shutil.rmtree(tmp, ignore_errors=True)
if FAILS:
    print(f"FAIL  test_last50_live.py  {len(FAILS)} failed: {FAILS}")
    sys.exit(1)
print("ok    test_last50_live.py")

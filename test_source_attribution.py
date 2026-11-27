#!/usr/bin/env python3
"""The ledger's order-id proof outranks the tracker's key-window source tag.

Peter, 27 Nov: "Correct tracker attribution for the 24 ledger-proven bot fills. They must not appear in
both manual and bot performance. Correct the underlying attribution, not just one report."

MEASURED before this change (reconcile_live on 0e7bf13c):
    tracker source of the untagged order-linked fills: {'Peter': 24}
while executed_clv counted those same 24 as bot via the ledger join - the same fills in both records.

The cause is tracker_build's settled-row source chain: a row is tagged bot only when bot_match() hits the
key set from bot_keys(None, days=2) - a TWO-DAY key window - and a row already stored as "Peter" is treated
as no evidence by the fallback, which lands on "Peter" again. Sticky, and manual forever.

These tests pin the four properties that matter. Each was checked against a deliberate mutation.
"""
import tracker_build as tb


class FakeLedger:
    """Stands in for live_ledger. `lanes` is the authoritative {row id: lane} the order-id join proves."""

    def __init__(self, lanes, src=("L", None, "C"), raise_on=None):
        self.lanes, self.src, self.raise_on = lanes, src, raise_on

    def load(self):
        if self.raise_on == "load":
            raise RuntimeError("ledger unreadable")
        return self.src

    def feed_alerts(self):
        return []

    def account(self, L, bets, C, alerts):
        if self.raise_on == "account":
            raise ValueError("ledger corrupt")
        return {"plays": []}

    def lane_of_rows(self, acct):
        if self.raise_on == "lanes":
            raise KeyError("lane")
        return self.lanes


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    return bool(cond)


def main():
    ok = True

    # 1. the incident: a ProphetX fill the ledger proves is the bot's, sitting in the manual record
    bets = {"px|1": {"id": "px|1", "source": "Peter", "result": "W", "book": "ProphetX"}}
    line = tb.ledger_attribution(bets, FakeLedger({"px|1": "LANE 1"}))
    ok &= check("a ledger-proven fill tagged Peter becomes bot", bets["px|1"]["source"] == "bot")
    ok &= check("and it carries the ledger's lane", bets["px|1"].get("lane") == "LANE 1")
    ok &= check("and says why it changed hands", bets["px|1"].get("src_fix") == "ledger order id")
    ok &= check("the log counts what moved", "1 re-attributed" in line)

    # 2. NOT IN BOTH: source is the single field every record keys on, so once it reads bot the row is out
    #    of the manual record by construction. This is the property Peter asked for, asserted directly.
    ok &= check("a re-attributed row is no longer manual", bets["px|1"]["source"] != "Peter")

    # 3. a row the ledger does NOT place keeps its tag - not flipped to bot, not flipped to Peter
    bets = {"px|1": {"id": "px|1", "source": "Peter"}, "hr|9": {"id": "hr|9", "source": "Street Value"}}
    tb.ledger_attribution(bets, FakeLedger({"px|1": "R1"}))
    ok &= check("an unplaced row keeps its own source", bets["hr|9"]["source"] == "Street Value")
    ok &= check("an unplaced row is not stamped", "src_fix" not in bets["hr|9"])

    # 4. a lane the ledger could not name is NOT proof. str(None) == "None" would otherwise sail through.
    bets = {"px|1": {"id": "px|1", "source": "Peter"}}
    tb.ledger_attribution(bets, FakeLedger({"px|1": None}))
    ok &= check("a None lane does not re-attribute", bets["px|1"]["source"] == "Peter")
    bets = {"px|1": {"id": "px|1", "source": "Peter"}}
    tb.ledger_attribution(bets, FakeLedger({"px|1": "None"}))
    ok &= check("the string 'None' does not re-attribute either", bets["px|1"]["source"] == "Peter")

    # 5. FAIL CLOSED on every failure mode: an unreadable authority moves nothing, either direction
    for mode, lbl in (("load", "load() raises"), ("account", "account() raises"), ("lanes", "lane_of_rows() raises")):
        bets = {"px|1": {"id": "px|1", "source": "Peter"}, "px|2": {"id": "px|2", "source": "bot"}}
        line = tb.ledger_attribution(bets, FakeLedger({"px|1": "LANE 1"}, raise_on=mode))
        ok &= check(f"{lbl}: nothing is re-attributed", bets["px|1"]["source"] == "Peter")
        ok &= check(f"{lbl}: an existing bot tag is left alone", bets["px|2"]["source"] == "bot")
        ok &= check(f"{lbl}: and it says so", "UNAVAILABLE" in line and "tags unchanged" in line)

    bets = {"px|1": {"id": "px|1", "source": "Peter"}}
    line = tb.ledger_attribution(bets, FakeLedger({"px|1": "LANE 1"}, src=None))
    ok &= check("no passphrase: nothing is re-attributed", bets["px|1"]["source"] == "Peter")
    ok &= check("no passphrase: and it says so", "UNAVAILABLE" in line)

    # 6. idempotent: a second build must not double-count or re-stamp an already-bot row
    bets = {"px|1": {"id": "px|1", "source": "Peter"}}
    tb.ledger_attribution(bets, FakeLedger({"px|1": "LANE 1"}))
    line = tb.ledger_attribution(bets, FakeLedger({"px|1": "LANE 1"}))
    ok &= check("a second pass re-attributes nothing", "0 re-attributed" in line)

    # 7. a row the ledger places that is MISSING from the tracker is not invented
    bets = {}
    line = tb.ledger_attribution(bets, FakeLedger({"ghost|7": "LANE 1"}))
    ok &= check("a ledger row with no tracker row creates nothing", bets == {})
    ok &= check("and it is still counted as proven", "1 row(s) proven" in line)

    print("\nALL PASS" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

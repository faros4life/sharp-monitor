"""Nov 12 (Peter, Telegram audit): repeat LIVE PLAY labelled, HELD checks the journal, NO FILL tokens canonical."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import executor as ex
PASS = FAIL = 0
def check(name, ok):
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    if not ok: print("FAIL:", name)

sent = []
ex.push = lambda title, body, mirror=True: sent.append((title, body))
class R:  # stand-in registry
    n = {}
    @staticmethod
    def enabled(): return True
    @staticmethod
    def bump_streak(name):
        R.n[name] = R.n.get(name, 0) + 1; return R.n[name]
    @staticmethod
    def rows(): return []
ex.registry, ex.SEEN["tok"] = R, {}
play = {"play_key": "rules|NCAAF|Louisiana vs UL Monroe|total|UNDER", "sport": "NCAAF", "game": "Louisiana vs UL Monroe",
        "bet": "Under 48.5 (-115)", "source": "rules"}
r = {"play": play, "live": {"book": "novig", "risk": 100.0}, "entry": {}}
for i in range(3):
    ex.live_play_alert(r)
check("attempt 1 unlabelled", "SAME PLAY" not in sent[0][0] and "SAME PLAY" not in sent[0][1])
check("attempt 2 labelled", "SAME PLAY — attempt 2, previous attempt did not fill." in sent[1][1] and "attempt 2" in sent[1][0])
check("attempt 3 labelled", "attempt 3" in sent[2][1])
class Broken(R):
    @staticmethod
    def bump_streak(name): raise RuntimeError("down")
ex.registry = Broken
sent.clear(); ex.live_play_alert(r)
check("store down: alert still sent, unlabelled", len(sent) == 1 and "SAME PLAY" not in sent[0][1])

# prior_hold
ex.registry = R
ex.LEDGER_ROWS[:] = [{"key": "r1|NCAAF|Louisiana vs UL Monroe|total|UNDER", "decided_utc": "2026-11-12T15:01:00Z",
                      "live_order": {"status": "placed", "order_id": "abc"}}]
check("prior hold time ET", ex.prior_hold(play) == "10:01 AM")
ex.LEDGER_ROWS[:] = []
check("no journal row -> None", ex.prior_hold(play) is None)
ex.LEDGER_ROWS[:] = [{"key": "x|NCAAF|Other vs Team|total|UNDER", "decided_utc": "2026-11-12T15:01:00Z",
                      "live_order": {"status": "placed", "order_id": "abc"}}]
check("different game -> None", ex.prior_hold(play) is None)
print(f"{'PASS' if not FAIL else 'FAIL'} test_play_messages.py {PASS} checks" + (f", {FAIL} failed" if FAIL else ""))
sys.exit(1 if FAIL else 0)

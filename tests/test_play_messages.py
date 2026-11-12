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

# ---- resting bid expiry report (Nov 12, Peter: once, promptly at expiry)
import datetime as _dt
def _run(recs):
    out = []
    ex.book_live.novig_results = lambda: recs
    os.environ["NOVIG_SNAPSHOT_TOKEN"] = "x"
    ex.imap_open = lambda: type("M", (), {"logout": lambda s: None})()
    ex.imap_close = lambda M: None
    ex.tg = lambda t: out.append(("tg", t))
    ex.push = lambda title, body, mirror=True: out.append(("push", title + "|" + body))
    ex.send = lambda *a, **k: None
    seen = set()
    class RC:
        def __init__(self, M, toks, days=None): pass
        def claim(self, tok):
            if tok in seen: return False
            seen.add(tok); return True
        def sent(self, tok): seen.add(tok)
        def failed(self, tok): seen.discard(tok)
    ex.ReportClaim = RC
    ex.novig_reports(); n1 = len(out)
    ex.novig_reports()          # second pass, same data: nothing more
    return out, n1, len(out)
now = _dt.datetime.now(_dt.timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
rec = {"client_id": "c1", "label": "NBA Spurs | Under 239.5", "status": "OPEN", "tif": "GTT", "qty": 1000, "price": "0.480",
       "filled_qty": 0, "ttl_ms": str(3 * 3600 * 1000), "placed_utc": iso(now - _dt.timedelta(hours=5)), "order_id": "o1"}
out, n1, n2 = _run([dict(rec)])
check("expired unfilled bid reported once", n1 >= 1 and n2 == n1)
check("says nothing filled as of last read", any("nothing filled as of the last read" in m for _, m in out))
# still live (not expired): no report
rec2 = dict(rec, client_id="c2", placed_utc=iso(now - _dt.timedelta(minutes=10)))
out2, a, b = _run([rec2])
check("unexpired bid not reported as expired", not any("expired" in m for _, m in out2))
print(f"{'PASS' if not FAIL else 'FAIL'} test_play_messages.py {PASS} checks" + (f", {FAIL} failed" if FAIL else ""))
sys.exit(1 if FAIL else 0)

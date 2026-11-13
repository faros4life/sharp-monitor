#!/usr/bin/env python3
"""Nov 13 (Peter): the two defects behind this morning's incident.

ONE - the bot issued a manual STOP command to its own command channel, and the reader could not
tell that from Peter pressing the kill switch. Since Nov 12 the latch made it permanent.

TWO - the 2-cent ProphetX/Novig tolerance could reverse a FAILED line-adjusted value check, so a
worse line AND a worse price, each individually inside a bound, together landed past the alert's
value. Measured live: Under 218.5 at -104 against a -115 alert at 219.5.

Nothing is placed, submitted, resumed or paused by this file. No STOP or GO is ever sent.
"""
import json
import sys

import line_value as lvcalc

fails = []


def check(name, cond):
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails.append(name)


# ======================================================================= ONE: STOP/GO provenance
print("1. The bot must never issue a manual command to itself")
src_px = open("px_live.py").read()
src_bl = open("book_live.py").read()
check("px_live no longer publishes a bare STOP command", 'push("STOP", "STOP")' not in src_px)
check("book_live no longer publishes a bare STOP command", 'px_live.push("STOP", "STOP")' not in src_bl)
check("px_live latches an automatic pause instead", "auto_pause(" in src_px)
check("book_live latches an automatic pause instead", "px_live.auto_pause(" in src_bl)
check("the over-fill safety condition still pauses", "MAX_ORDER + 0.5" in src_px and "MAX_ORDER + 0.5" in src_bl)

print("\n2. A titled message is the BOT's; only an untitled one is a user command")
import px_live as px

MSGS = []


def fake_open(url, timeout=0):
    class R:
        def read(self_):
            return "\n".join(json.dumps(m) for m in MSGS).encode()

        def __enter__(self_):
            return self_

        def __exit__(self_, *a):
            return False
    return R()


px.urllib.request.urlopen = fake_open
px.TOPIC = "t"

MSGS = [{"id": "a1", "time": 100, "message": "STOP", "title": "STOP"}]      # the bot's own auto-pause
check("a titled STOP is ignored as a command", px._ntfy_switch()[0] is None)
MSGS = [{"id": "b1", "time": 200, "message": "STOP", "title": ""}]          # Peter's phone
w, when, mid = px._ntfy_switch()
check("an untitled STOP IS a command", w == "STOP" and mid == "b1")
MSGS = [{"id": "c1", "time": 300, "message": "GO"}]                         # no title key at all
check("an untitled GO IS a command", px._ntfy_switch()[0] == "GO")
MSGS = [{"id": "d1", "time": 400, "message": "STOP", "title": "Live PAUSED: fill too big"}]
check("a differently-titled bot message is still not a command", px._ntfy_switch()[0] is None)

print("\n3. Commands are processed ONCE - an old one is never replayed")
import registry as rg
STORE = {"switch": None, "auto_pause": None, "switch_seen": []}
rg.enabled = lambda: True
rg.switch_state = lambda: STORE["switch"]
rg.auto_pause_state = lambda: STORE["auto_pause"]
rg.switch_cursor = lambda: list(STORE["switch_seen"])
rg.put_switch = lambda w, when=None: STORE.__setitem__("switch", {"word": w, "when": when}) or True
rg.put_switch_cursor = lambda ids: STORE.__setitem__("switch_seen", list(ids)) or True
rg.clear_auto_pause = lambda: STORE.__setitem__("auto_pause", None) or True
rg.put_auto_pause = lambda reason, source: STORE.__setitem__(
    "auto_pause", {"reason": reason, "source": source, "ts": "2026-11-13T00:00:00Z"}) or True

MSGS = [{"id": "s9", "time": 500, "message": "STOP"}]
check("first read acts on it", px.stop_state()[0] == "STOP")
check("and records the id", STORE["switch_seen"] == ["s9"])
check("the latch now carries it", STORE["switch"]["word"] == "STOP")
check("a SECOND read does not replay it - the latch answers", px.stop_state()[0] == "STOP")
check("and the cursor did not grow", STORE["switch_seen"] == ["s9"])

print("\n4. USER STOP and AUTOMATIC SAFETY PAUSE are different, and both block")
STORE.update(switch=None, auto_pause=None, switch_seen=[])
MSGS = []
px.auto_pause("Novig fill $900.00 exceeded the $415 per-order maximum", "novig")
check("the auto pause is latched with its reason", bool(STORE["auto_pause"]))
st, _ = px.stop_state()
check("it blocks like a STOP", st == "STOP")
check("but it is reported as automatic, not as Peter's STOP", px.PAUSE.get("kind") == "auto")
check("and it names the condition", "per-order maximum" in (px.PAUSE.get("reason") or ""))

STORE.update(switch={"word": "STOP", "when": 1}, auto_pause=None)
st, _ = px.stop_state()
check("a latched USER stop reports as user", st == "STOP" and px.PAUSE.get("kind") == "user")

print("\n5. Only an explicit human GO clears an automatic pause")
STORE.update(switch=None, auto_pause={"reason": "x", "source": "novig", "ts": "t"}, switch_seen=[])
MSGS = [{"id": "g9", "time": 900, "message": "GO"}]
check("the GO is accepted", px.stop_state()[0] == "GO")
check("and the automatic pause is cleared", STORE["auto_pause"] is None)
STORE.update(switch=None, auto_pause={"reason": "x", "source": "novig", "ts": "t"}, switch_seen=[])
MSGS = []
check("nothing else clears it", px.stop_state()[0] == "STOP")

print("\n6. Fail closed: an unreadable latch is never 'not paused'")


def boom():
    raise RuntimeError("registry unreadable")


STORE.update(switch=None, auto_pause=None, switch_seen=[])
MSGS = []
rg.auto_pause_state = boom
check("unreadable auto-pause latch -> UNKNOWN", px.stop_state()[0] == "UNKNOWN")
rg.auto_pause_state = lambda: STORE["auto_pause"]
rg.switch_state = boom
check("unreadable switch latch -> UNKNOWN", px.stop_state()[0] == "UNKNOWN")
rg.switch_state = lambda: STORE["switch"]

# ======================================================================= TWO: pricing
print("\n7. Tolerance may not reverse a failed line-adjusted value check")


def am_to_prob(a):
    a = float(a)
    return (-a) / ((-a) + 100) if a < 0 else 100 / (a + 100)


def gate(cand_line, cand_am, tol_cents, side="UNDER", alert_line=219.5, alert_am=-115, book="novig"):
    """The decision as executor applies it: prob(am_q) <= cv['max_prob']."""
    cv = lvcalc.convert("NBA", "total", side, alert_line, alert_am, cand_line, cand_am, book,
                        tol_cents, lambda a, c: int(a) - c if int(a) < 0 else int(a) + c, None, -130)
    if cv["status"] != "ok" or cv.get("max_prob") is None:
        return None, cv.get("reason")
    return am_to_prob(cand_am) <= cv["max_prob"] + 1e-9, cv["max_prob"]

# THE LIVE CASE. Nov 13: I first reported this as "worse by 0.192 pts, admitted only by the 2c
# allowance". That used HP_FALLBACK/half_point(), which is the LEGACY path (hb * hp). The live
# replacement path uses convert()'s prob_points mass model, where one NBA total point costs 2.434
# pts against a 2.508 pt price gain - so the swap is +0.074 pts and qualifies on its own merits
# with NO tolerance. The test asserts the model that actually runs.
ok0, mp0 = gate(218.5, -104, 0)
ok2, mp2 = gate(218.5, -104, 2)
check("Under 218.5 @ -104 passes WITHOUT tolerance under the live model", ok0 is True)
check("so the no-tolerance gate does not change this play", ok0 is True and ok2 is True)
check("and one point is priced by the model, not by HP_FALLBACK", abs((am_to_prob(-115) - mp0) - 0.0243) < 0.002)

ok0b, _ = gate(218.5, 102, 0)
check("Under 218.5 @ +102 passes comfortably without tolerance", ok0b is True)

# THE CASE THE NEW GATE ACTUALLY CLOSES: a price that fails on its own and is carried ONLY by the
# allowance. -106 sits between max_prob(tol=0)=0.510541 and max_prob(tol=2)=0.514828.
only0, _ = gate(218.5, -106, 0)
only2, _ = gate(218.5, -106, 2)
check("Under 218.5 @ -106 FAILS without tolerance", only0 is False)
check("...and tolerance alone would have carried it", only2 is True)
check("this is exactly what the new gate refuses", only0 is False and only2 is True)

print("\n8. The allowance at the ALERT's own line is preserved (Peter, Oct 27)")
same0, _ = gate(219.5, -117, 0)
same2, _ = gate(219.5, -117, 2)
check("-117 vs a -115 alert fails with no tolerance", same0 is False)
check("and is allowed by the 2c allowance at the same line", same2 is True)

print("\n9. Lines: better accepted, unsupported moves refused, Overs mirror Unders")
bet_u, _ = gate(220.5, -125, 0)
check("Under 220.5 (better) at a worse price is accepted", bet_u is True)
two_u, why = gate(217.5, -104, 0)
check("Under 217.5 (a two-point move) is REFUSED as unsupported, fail closed",
      two_u is None and "not_listed" in str(why))
# For an OVER a HIGHER line is the worse one, and the model charges it the SAME 2.434 pts.
ov_same, mpo = gate(220.5, -104, 0, side="OVER")
check("Over 220.5 is the one-point-worse side and costs the same as Under 218.5", abs(mpo - mp0) < 1e-12)
check("Over 220.5 @ -104 therefore also passes", ov_same is True)
ov_bad, _ = gate(220.5, -108, 0, side="OVER")
check("Over 220.5 @ -108 fails - the price no longer covers the point", ov_bad is False)
bet_o, _ = gate(218.5, -125, 0, side="OVER")
check("Over 218.5 (better for an Over) is accepted", bet_o is True)

print("\n10. The check is wired into BOTH gates, for every tolerance venue")
src = open("executor.py").read()
check("evaluate() runs the no-tolerance check", "lv_value_gate_no_tol" in src)
check("revalidate() runs it too", "before the {PX_TOL_CENTS}c allowance" in src)
check("it is scoped to replacements only", "_repl = bl is not None" in src)
check("it covers every TOL_BOOKS venue, not one book", "PX_TOL_CENTS if b in TOL_BOOKS else 0" in src)

print("\n11. A paused pass announces a QUALIFYING PLAY and is not counted as an attempt")
check("the paused label exists", "QUALIFYING PLAY" in src)
check("nothing-will-be-placed is stated", "NOTHING WILL BE PLACED" in src)
check("the attempt counter skips paused passes", "registry.enabled() and not paused" in src)

print()
if fails:
    print(f"FAIL  test_stop_go_and_pricing.py  {len(fails)} failed: {fails}")
    sys.exit(1)
print("ALL PASS")

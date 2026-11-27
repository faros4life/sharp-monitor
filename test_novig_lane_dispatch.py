"""Nov 27: the Novig dispatch carries lane="dogs" for Dogs only; every other lane's dispatch is byte-identical to before."""
import executor as ex
import book_live as bl

fails = 0
def ok(c, m):
    global fails
    print(("  ok   " if c else "  FAIL ") + m); fails += 0 if c else 1

sent = []
bl.NOVIG_SUBMIT = True
bl._dispatch_token = lambda: "t"
bl.preflight = lambda book, risk: (True, "")
bl._gh = lambda method, url, body, tok=None: (sent.append(body["inputs"]) or (204, None))
bl.novig_place("oc", 0.49, 61200, "L", None, "NCAAF|Buffalo", lane="dogs")
bl.novig_place("oc", 0.52, 40000, "L", None, "NBA|g|total|UNDER")
ok(sent[0].get("lane") == "dogs", "a Dogs dispatch names its lane")
ok("lane" not in sent[1], "a dispatch without a lane has no lane input at all (unchanged)")
ok(set(sent[1]) == set(sent[0]) - {"lane"}, "the other inputs are the same set as before")
ok(ex.NOVIG_LANE_ARG == {"dogs": "dogs"}, "only Dogs is mapped: Lane 1, Board, R1, NCS send nothing new")
for ln in ("rules", "board", "r1", "ncs", "lane2", ""):
    ok(ex.NOVIG_LANE_ARG.get(ln, "") == "", f"lane {ln!r} sends no lane")
print("FAILED" if fails else "all passed"); raise SystemExit(1 if fails else 0)

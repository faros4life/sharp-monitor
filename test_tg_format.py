#!/usr/bin/env python3
"""Peter, Nov 22 2026: a colour symbol and a bold header on EVERY Telegram message.

The property that actually matters here is the LAST one: decorate() must always hand back a
plain fallback with no markup, because a malformed entity makes Telegram answer ok:false and a
formatting change must never be able to suppress an alert.
"""
import sys
import tg_format as F

FAILED = []
RAN = []


def ok(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   got: {got}" if not cond and got else ""))
    RAN.append(name)
    if not cond:
        FAILED.append(name)


# --- every message is marked, none is left plain -------------------------------------------
for msg in ("Bot fill: Under 146.5 @ -123 ProphetX", "[R1] status unknown", "NEW POSITIONS",
            "balance refreshed", "something nobody anticipated"):
    h, p = F.decorate(msg)
    ok(f"symbol present (html): {msg[:28]}", h.lstrip()[:1] in F.SYMBOLS, h[:20])
    ok(f"symbol present (plain): {msg[:28]}", p.lstrip()[:1] in F.SYMBOLS, p[:20])

# --- classification ------------------------------------------------------------------------
ok("verify -> red", F.classify("[R1] status unknown, verify") == F.RED)
ok("conflict -> red", F.classify("ledger conflict on NM -7.5") == F.RED)
ok("no live feed -> red", F.classify("No live feed matched for this game") == F.RED)
ok("HR1 -> yellow", F.classify("HR1 play ready, place it") == F.YELLOW)
ok("manual -> yellow", F.classify("manual action needed") == F.YELLOW)
ok("filled -> green", F.classify("FILLED 1.0u Novig") == F.GREEN)
ok("matched -> green", F.classify("order matched at -110") == F.GREEN)
ok("positions -> blue", F.classify("NEW POSITIONS (3)") == F.BLUE)
ok("balance -> blue", F.classify("balance summary") == F.BLUE)
ok("unknown text defaults BLUE, never GREEN", F.classify("zzz nothing matches here") == F.BLUE,
   F.classify("zzz nothing matches here"))
ok("a failure inside a fill message reads RED, not GREEN",
   F.classify("fill verify failed on Novig") == F.RED)

# --- idempotent: HR1 already carries its own yellow ------------------------------------------
hr1 = "\U0001F7E1\U0001F4B0 HR1 PLAY - SMU +20.5"
h, p = F.decorate(hr1)
ok("already-marked message is returned untouched (html)", h == hr1, h[:24])
ok("already-marked message is returned untouched (plain)", p == hr1, p[:24])
ok("no second symbol stacked", h.count(F.YELLOW) == 1, str(h.count(F.YELLOW)))

# --- bold header, first line only --------------------------------------------------------
h, _ = F.decorate("FILLED 1.0u\nNovig -110\nR1")
ok("header is bolded", "<b>FILLED 1.0u</b>" in h, h)
ok("only one bold pair", h.count("<b>") == 1 and h.count("</b>") == 1, h)
ok("body lines survive", "Novig -110" in h and h.rstrip().endswith("R1"), h)
h1, _ = F.decorate("single line only")
ok("single-line message still bolds", h1.endswith("<b>single line only</b>"), h1)

# --- escaping: the entity that would otherwise make Telegram refuse the send ----------------
h, p = F.decorate("A & B <tag> fill", )
ok("ampersand escaped once", "&amp;" in h and "&amp;amp;" not in h, h)
ok("angle brackets escaped", "&lt;tag&gt;" in h, h)
ok("plain fallback carries NO markup", "<b>" not in p and "&amp;" not in p, p)
ok("plain fallback keeps the original text verbatim after the symbol",
   p.split(" ", 1)[1] == "A & B <tag> fill", p)

# --- caller-supplied HTML is never re-escaped ------------------------------------------------
h, p = F.decorate("<b>Board</b> fill at -105", body_is_html=True)
ok("caller HTML left intact", "<b>Board</b>" in h and "&lt;" not in h, h)
ok("caller HTML still gets a symbol", h.lstrip()[:1] in F.SYMBOLS, h[:12])

# --- decorate is pure: same input, same output, no state ------------------------------------
a1 = F.decorate("NEW POSITIONS")
a2 = F.decorate("NEW POSITIONS")
ok("decorate is deterministic", a1 == a2)

print(f"{len(RAN) - len(FAILED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)

#!/usr/bin/env python3
"""READ-ONLY probe of the STOP/GO switch (Peter, Nov 13: "I DID NOT SEND STOP").

Prints every STOP/GO message ntfy still carries, and the registry's latched switch, with times.
Writes NOTHING: no put_switch, no GO, no order, no resume. Words and timestamps only - no stake,
balance or price - so it is safe for the public Actions log.

WHY THIS EXISTS. px_live._ntfy_switch() matches any ntfy message whose body, stripped and
uppercased, equals "STOP". The bot PUBLISHES exactly that body itself when an automatic safety
trigger fires - book_live._too_big() and px_live's over-fill branch both call push("STOP", "STOP")
when a fill exceeds MAX_ORDER. So the bot's own automatic pause is indistinguishable from Peter
typing STOP on his phone, and since Nov 12 stop_state() LATCHES whatever word it sees into the
registry, where only an explicit GO clears it.

This probe answers the three questions that decide the fix: what does ntfy actually hold, what is
latched, and does the latched time line up with an automatic pause rather than a manual one.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

TOPIC = (os.environ.get("NTFY_TOPIC") or "").strip()


def ts(x):
    try:
        return datetime.fromtimestamp(int(x), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(x)


print("STOP/GO SWITCH PROBE (read-only; nothing is written, no GO is sent)")
print(f"  now: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")

if not TOPIC:
    print("  FAIL  no NTFY_TOPIC in env")
else:
    for window in ("12h", "7d"):
        try:
            with urllib.request.urlopen(
                    f"https://ntfy.sh/{TOPIC}/json?poll=1&since={window}", timeout=20) as r:
                lines = r.read().decode().splitlines()
        except Exception as ex:
            print(f"  ntfy {window}: UNREADABLE ({str(ex)[:60]}) -> _ntfy_switch would return UNKNOWN")
            continue
        sw, total = [], 0
        for ln in lines:
            try:
                m = json.loads(ln)
            except Exception:
                continue
            total += 1
            word = (m.get("message") or "").strip().upper()
            if word in ("STOP", "GO"):
                # title is how the bot's own auto-pause is distinguishable AFTER THE FACT: its
                # push() sends title "STOP" too, while a phone message carries no title.
                sw.append((m.get("time"), word, (m.get("title") or "").strip()))
        print(f"\n  ntfy since={window}: {total} message(s), {len(sw)} STOP/GO switch message(s)")
        for t, w, title in sw:
            tag = "  <- title 'STOP' = published BY THE BOT (automatic pause), not typed by Peter" \
                if title.upper() in ("STOP", "GO") else "  <- no title: consistent with a phone message"
            print(f"    {ts(t)}  {w:4}  title={title!r}{tag}")
        if window == "12h" and sw:
            print(f"    => _ntfy_switch() returns: {sw[-1][1]} at {ts(sw[-1][0])} (it takes the NEWEST in the window)")
        elif window == "12h":
            print("    => _ntfy_switch() returns: None (no switch message in the window)")

try:
    import registry as rg
    if not rg.enabled():
        print("\n  registry: no REGISTRY_TOKEN - ntfy-only, nothing latched")
    else:
        st = rg.switch_state()
        print(f"\n  registry latch: {st!r}")
        if isinstance(st, dict) and st.get("word") == "STOP":
            print(f"    LATCHED STOP at {ts(st.get('when')) if str(st.get('when') or '').isdigit() else st.get('when')}")
            print("    Only an explicit GO newer than this clears it (stop_state(), Nov 12).")
except Exception as ex:
    print(f"\n  registry: unreadable ({str(ex)[:60]}) -> stop_state() returns UNKNOWN (refuses)")

print("\nNothing was written. No GO was sent. The pause is unchanged.")
sys.exit(0)

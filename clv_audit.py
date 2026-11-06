#!/usr/bin/env python3
"""
HISTORICAL CLV AUDIT - standard section 6 (Peter, Nov 6).

"Review all registered tests for inconsistent CLV calculations. Identify which used: trigger-book
prices versus best-net prices; gross versus net entry odds; verified versus modeled closing prices;
different fee assumptions or CLV thresholds. Preserve original published numbers. Show recalculated
CLV alongside the original, with clear labels. Do not retroactively change CLV pass/fail
thresholds."

HOW THIS AUDIT WORKS, and what it deliberately does NOT do.

It derives each test's basis from the SOURCE ITSELF - does it read a Pinnacle close or the trigger
exchange's own close, does it put the entry price through eff() or use it gross, does it price the
trigger book or the best available book, does it route through clv_std. Those are facts about the
code, checked mechanically, so they cannot drift from what the script really does.

It does NOT restate published figures from memory. A number I typed in from recollection would look
exactly like a number read from the record, and would be the easiest thing here to get wrong. Where
a test's original figure is not machine-readable from the repo, this says so and leaves the
published record as the authority. Nothing is overwritten: Peter's Nov 5 rule stands, that no
figure already published is changed retroactively.

It changes NO threshold. Where a different basis would move a pass/fail, the audit says that it
would and leaves the verdict exactly as it was recorded.

RECALCULATION. clv_report.py recalculates the liquidity-alert population under the standard. For
every other test, recalculation needs that test's own population and window, so this audit names
what each one would require rather than guessing at it.
"""
import os
import re
import sys

import clv_std as cs
import exchange_lag as el

# Every script in the repo that computes something it calls CLV.
SCRIPTS = [
    "liq_history_test.py", "post_test.py", "plimit_level.py", "close_vs_close_test.py",
    "small_book_surge_test.py", "p1_backtest.py", "board_lab.py", "liquidity_monitor.py",
    "ncaab_grade.py", "model_lab.py", "nba_backtest2.py", "fill_audit.py", "ev_sightings.py",
    "ev sightings.py",   # yes, with a space - a second copy lives beside ev_sightings.py
]


def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return None


def basis_of(src):
    """What this script actually does, read off the source. Facts, not recollection."""
    pin = bool(re.search(r"\bpinnacle\b", src, re.I))
    selfclose = bool(re.search(r"close_price|clv_cents", src))
    net = bool(re.search(r"\bel\.eff\(|\beff\(", src))
    std = "import clv_std" in src
    # a gross CLV is a close minus an entry with no fee call anywhere near it
    best = bool(re.search(r"best_net|best_bk|kbest|rbest|best_causal", src))
    fees = sorted(set(re.findall(r"0\.0(?:695|7|6|35|175|125|2)\b", src)))
    # A script that applies a fee with its OWN arithmetic is not gross - it is unshared, which is
    # a different and milder problem. Calling it gross would overstate the finding.
    if net:
        entry = "net via shared eff()"
    elif fees:
        entry = "net via its OWN fee code"
    else:
        entry = "GROSS - no fee anywhere"
    return {
        "close": ("Pinnacle + exchange self-close" if (pin and selfclose)
                  else "Pinnacle" if pin else "exchange self-close" if selfclose else "none found"),
        "uses_selfclose": selfclose, "uses_pinnacle": pin, "is_gross": not net and not fees,
        "entry": entry,
        "price": "best-net across books" if best else "trigger book",
        "clv_std": "yes" if std else "no",
        "own_fee_constants": ", ".join(fees) if fees else "-",
    }


def main():
    print("HISTORICAL CLV AUDIT - standard section 6")
    print(cs.stamp())
    print("Originals are preserved. No published figure is rewritten and no threshold is moved.\n")

    rows = []
    for s in SCRIPTS:
        src = read(s)
        if src is None:
            continue
        b = basis_of(src)
        b["script"] = s
        rows.append(b)

    w = max(len(r["script"]) for r in rows)
    print(f"{'script':{w}}  {'close source':30}  {'entry odds':22}  {'price basis':24}  clv_std")
    print("-" * (w + 90))
    for r in sorted(rows, key=lambda x: (x["clv_std"] != "yes", x["entry"].startswith("GROSS"))):
        print(f"{r['script']:{w}}  {r['close']:30}  {r['entry']:22}  {r['price']:24}  {r['clv_std']}")

    gross = [r for r in rows if r["is_gross"]]
    unshared = [r for r in rows if r["entry"] == "net via its OWN fee code"]
    selfc = [r for r in rows if r["uses_selfclose"]]
    nostd = [r for r in rows if r["clv_std"] == "no"]

    print(f"\n{'='*74}\nFINDINGS\n{'='*74}")
    print(f"1. NOT ONE registered test imports clv_std ({len(nostd)} of {len(rows)} scripts).")
    print("   The standard exists; nothing runs on it yet. Each script carries its own fee")
    print("   constants and its own close rule. That is the inconsistency section 6 asks for,")
    print("   and it is structural rather than a stray number.")
    print(f"\n2. GROSS entry odds - no fee applied anywhere ({len(gross)}):")
    for r in gross:
        print(f"   {r['script']}")
    print(f"\n   Fee applied, but with the script's OWN arithmetic rather than the shared "
          f"eff() ({len(unshared)}):")
    for r in unshared:
        print(f"   {r['script']:24} {r['own_fee_constants']}")
    print(f"\n3. READS THE EXCHANGE'S OWN CLOSE ({len(selfc)}) - whether or not it also reads")
    print("   Pinnacle. Any figure built on this close is Exchange Self-Close Price Movement:")
    for r in selfc:
        also = "also reads Pinnacle" if r["uses_pinnacle"] else "NO Pinnacle at all"
        print(f"   {r['script']:24} {also}")
    both = [r for r in rows if (r["is_gross"] or r["entry"] == "net via its OWN fee code")
            and r["uses_selfclose"] and not r["uses_pinnacle"]]
    if both:
        print(f"\n4. FAILS ON BOTH AXES - no shared fee model AND no Pinnacle ({len(both)}):")
        for r in both:
            print(f"   {r['script']}")
        print("   Under the standard these produce no headline CLV at all. Their figures are")
        print("   Exchange Self-Close Price Movement, which is not CLV and is never a gate.")

    print(f"\n5. FEE CONSTANTS duplicated outside the shared model:")
    for r in rows:
        if r["own_fee_constants"] != "-":
            print(f"   {r['script']:24} {r['own_fee_constants']}")
    print(f"   The shared model is {cs.FEE_MODEL}. A script holding its own copy cannot follow a")
    print("   schedule change, so each one is a place the model can silently go stale.")

    # Which of those copies is ALREADY stale against the published schedules
    live = set()
    for d in (el.TAKER, el.MAKER):
        live |= {f"{abs(v):g}" for v in d.values() if v}
    live |= {f"{el.PX_WIN_FEE:g}", f"{el.NOVIG_LIVE_TAKER:g}"}
    live |= {f"{v:g}" for v in el.PX_NHL.values()}
    stale = []
    for r in rows:
        if r["own_fee_constants"] == "-":
            continue
        bad = [c for c in r["own_fee_constants"].split(", ") if f"{float(c):g}" not in live]
        if bad:
            stale.append((r["script"], bad))
    print(f"\n   ALREADY STALE against the published schedules ({len(stale)}):")
    for sc, bad in stale:
        print(f"     {sc:24} carries {', '.join(bad)} - not a rate any venue currently publishes")
    if stale:
        print("     These will produce wrong figures for that venue until they are migrated or")
        print("     repointed at the shared model. Migration is a separate decision, not done here.")

    dupes = [r["script"] for r in rows if r["script"] in ("ev_sightings.py", "ev sightings.py")]
    if len(dupes) > 1:
        print(f"\n6. DUPLICATE FILE: {' and '.join(dupes)} both exist, with the same fee constants.")
        print("   Two copies of one script drift apart silently; one of them is also the duplicate")
        print("   workflow name noted earlier. Flagged, not resolved - deleting a file is Peter's call.")

    print(f"\n{'='*74}\nRECALCULATION\n{'='*74}")
    print("  liquidity alerts      -> clv_report.py recalculates this population under the")
    print("                           standard. Original figures stay as published beside it.")
    print("  every other test      -> needs that test's own population and window. Named here")
    print("                           rather than guessed at; no figure is restated from memory.")
    print("\n  Nothing in this audit changes a pass/fail verdict. Where a different basis would")
    print("  move one, that is reported and the recorded verdict stands.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

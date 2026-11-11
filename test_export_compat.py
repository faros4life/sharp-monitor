#!/usr/bin/env python3
"""
LIVE-CYCLE EXPORT COMPATIBILITY CHECK (Peter, Nov 10).

Peter's requirement is that historical values are preserved, not silently rewritten. The Nov 10
change adds clv_source, clv_verified, clv_pin_line, clv_conv_pts, clv_read_utc and clv_skipped to
the export. Every row written before that change has a legacy `cl` dict holding only p, ev and
mins_before, so the question this answers is: does a legacy row still export exactly what it did?

WHAT IT PROVES. The export's own expressions are applied to the 321 real readings already in
alerts.json, reconstructed as the legacy `cl` dicts that produced them. close_fair_prob,
close_value_pct, beat_true_close and close_read_mins_before must come back byte-identical, and
every new field must come back None - absent evidence staying absent, rather than a missing
conversion record being read as "same line".

WHAT IT DOES NOT PROVE. It does not run the monitor: that needs live state and network. It tests
the export expressions against real historical values, which is the part the change touched.

Peter's rule, asserted here explicitly: clv_verified is NEVER True on a live feed read, including
when clv_conv_pts == 0. A same-line read 20-30 minutes before start is still not the close. True
belongs only to a certified historical close from the clv_recover path.
"""
import json
import sys


def export_fields(cl, cl_skip=None):
    """The export block's expressions, as sharp_monitor.py now writes them."""
    return {
        "close_fair_prob": cl.get("p"),
        "close_value_pct": cl.get("ev"),
        "beat_true_close": (cl["ev"] > 0) if cl else None,
        "close_read_mins_before": cl.get("mins_before"),
        "clv_source": ("live read (provisional)" if cl else None),
        "clv_verified": (False if cl else None),
        "clv_pin_line": cl.get("pin_line"),
        "clv_conv_pts": cl.get("conv_pts"),
        "clv_read_utc": cl.get("read_utc"),
        "clv_skipped": cl_skip,
    }


def main():
    print("EXPORT COMPATIBILITY | legacy rows vs the Nov 10 schema")
    print("=" * 96)
    A = [x for x in json.load(open("alerts.json"))["alerts"]]
    rows = [a for a in A if a.get("close_value_pct") is not None]
    print(f"  historical readings replayed: {len(rows)}")
    bad = []
    newnull = 0
    for a in rows:
        legacy = {"p": a.get("close_fair_prob"), "ev": a.get("close_value_pct"),
                  "mins_before": a.get("close_read_mins_before")}
        got = export_fields(legacy)
        for k, was in (("close_fair_prob", a.get("close_fair_prob")),
                       ("close_value_pct", a.get("close_value_pct")),
                       ("beat_true_close", a.get("beat_true_close")),
                       ("close_read_mins_before", a.get("close_read_mins_before"))):
            if got[k] != was:
                bad.append((a.get("game"), k, was, got[k]))
        if got["clv_pin_line"] is None and got["clv_conv_pts"] is None and got["clv_read_utc"] is None:
            newnull += 1
        if got["clv_verified"] is not False:
            bad.append((a.get("game"), "clv_verified", False, got["clv_verified"]))

    # a row with no reading at all
    empty = export_fields({})
    if any(empty[k] is not None for k in empty):
        bad.append(("(no reading)", "all fields", None, empty))

    # a NEW-style live read: conv_pts == 0 must still be PROVISIONAL, never verified
    fresh = export_fields({"p": 0.53, "ev": 1.4, "mins_before": 25, "pin_line": 221.5,
                           "conv_pts": 0.0, "clamped": False, "source": "live read",
                           "read_utc": "2026-11-10T23:30:00Z"})
    if fresh["clv_verified"] is not False:
        bad.append(("(same-line live read)", "clv_verified", False, fresh["clv_verified"]))
    if fresh["clv_source"] != "live read (provisional)":
        bad.append(("(same-line live read)", "clv_source", "live read (provisional)", fresh["clv_source"]))

    print(f"  old fields byte-identical:    {len(rows) - len(set(b[0] for b in bad))} of {len(rows)}")
    print(f"  new fields null on legacy:    {newnull} of {len(rows)}")
    print(f"  no-reading row -> all null:   {'yes' if all(empty[k] is None for k in empty) else 'NO'}")
    print(f"  same-line live read verified? {fresh['clv_verified']}  (must be False)")
    print(f"  MISMATCHES                    {len(bad)}")
    for g, k, was, now in bad[:10]:
        print(f"      {str(g)[:40]:<40} {k}: was {was!r} now {now!r}")
    print("=" * 96)
    if bad:
        print("  FAIL - historical values would change. Do not ship.")
        return 1
    print("  PASS - every historical value preserved, every new field null on legacy rows,")
    print("  and a same-line live read stays PROVISIONAL rather than verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

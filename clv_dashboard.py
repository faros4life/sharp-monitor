#!/usr/bin/env python3
"""
DAILY DASHBOARD (Peter, 14 Nov 2026: six bands, approved design plus ten adjustments).

WHAT IT IS. One page, rebuilt daily, at a fixed URL. It RENDERS what other jobs already produced
and computes nothing this repo does not already define: selections come from clv_selection, CLV
from clv_basis through the ledger, lane attribution from clv_coverage.build_lane_resolver, fills
from the private registry. No new CLV maths, no new selection rule, no betting behaviour touched.

PRIVACY, VERIFIED NOT ASSUMED. faros4life/sharp-monitor is a PUBLIC repo with Pages enabled, so an
unlisted URL there is public. The whole payload is therefore a single AES-GCM ciphertext under the
existing TRACKER_PASSPHRASE (tb.enc, PBKDF2-SHA256, the same scheme tracker/index.html has used in
production), decrypted in the browser. No new credential. And even behind that: counts, units and
percentages only - no balances, no stakes in currency, no account identifiers, no order ids, no
secrets. A passphrase leak must not expose anything financial.

ZERO PAID CREDITS, BY CONSTRUCTION. The workflow passes no ODDSPAPI key at all, so no billable
call is possible even if a code path tried. Everything is read from committed artifacts, the
encrypted state and the private registry.

THE CUTOFF IS EVIDENCED, NOT ASSUMED. The price-first execution change is commit 7e7c20df, authored
Nov 11 10:31:28 EST. The code was first checked out by a production run at 10:35:07 EST, but that
run and the next three logged "0 qualifying play(s)", so nothing was priced. The first VERIFIED
production execution is 2026-11-11T16:31:19Z = 11:31:19 EST, from the private bot-order registry:
in that one run two rows carry live_why_not "price: nothing at or better than ..." (the new ceiling
refusing instead of walking down to a worse level) and two carry real Novig order ids placed under
the new limit logic. Both halves of the change became effective in the same run, so there is one
cutoff and not two. Peter approved this timestamp and the label on 14 Nov.

ZERO IS NEVER UNKNOWN. Every band renders "-" with a reason where it has no data. A band that
cannot be built is marked NOT AVAILABLE and still appears, because a missing band looks like a
clean one. A `cancelled` workflow run is reported as UNKNOWN, never as a pass or a failure: the
repo's own rule is that it means two different things needing opposite fixes.
"""
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clv_basis as cb
import clv_coverage as cov
import clv_ledger as cl
import clv_selection as csel
import clv_stale as cstale
import registry as rg
import tracker_build as tb

ET = cl.ET
OUT = os.environ.get("DASH_OUT", "") or "dash"
# Peter, 14 Nov: "Use November 11, 2026, at 11:31:19 AM EST as the verified pricing-model cutoff."
CUTOFF = datetime(2026, 11, 11, 16, 31, 19, tzinfo=timezone.utc)
CUTOFF_LABEL = "Price-First Execution Change - Nov 11, 11:31 AM ET"
LANE_UNIT, LANE_NAME = cov.LANE_UNIT, cov.LANE_NAME
# Freshness budgets: how old a source may be before the band goes amber. A source with no budget
# is reported with its age and no verdict rather than being called fresh by default.
BUDGET_H = {"ledger": 2, "tracker": 2, "registry": 2, "liquidity": 6, "sharp": 6, "hcache": 48}


# ------------------------------------------------------------------ small helpers
def pct(x, nd=2):
    return None if x is None else round(100.0 * x, nd)


def ci95(mean, se):
    """[lo, hi] or None. CLAUDE.md: bound a claim, do not assert it - a mean with no spread is an
    overcall, and a null at small n means a difference was not DETECTED, never that none exists."""
    if mean is None or se is None:
        return None
    return [round(100 * (mean - 1.96 * se), 2), round(100 * (mean + 1.96 * se), 2)]


def blk(obs, unit=None):
    """One figure block for a set of collapsed selections: n, CLV, CI, positive %, units, ROI."""
    s = csel.stats(obs)
    if not s.get("n"):
        return {"n": 0, "why": "no selection in this group carries a certified CLV"}
    out = {"n": s["n"], "clv": pct(s["mean"]), "ci": ci95(s["mean"], s.get("se")),
           "pos": s["pos"], "pos_pct": round(s["pos_pct"], 1), "fills": s["fills"],
           "n_settled": s.get("n_settled", 0)}
    # Units only where a lane unit is registered; never a currency figure, never a guess.
    out["units"] = round(s["stake"] / unit, 2) if (unit and s.get("stake")) else None
    out["units_why"] = None if out["units"] is not None else "no registered unit for this group"
    out["roi_pct"] = None if s.get("roi_pct") is None else round(s["roi_pct"], 2)
    out["roi_why"] = (None if out["roi_pct"] is not None else
                      f"profit absent on {s['n'] - s.get('has_profit', 0)} of {s['n']} - ROI "
                      f"UNAVAILABLE, not zero")
    return out


def gate(name, h1, h2, whole, fills_ok):
    """The REGISTERED rules, evaluated clause by clause. No clause is ever skipped silently.

    SCORECARD.md: POTENTIAL PASS needs ALL of - realized-unit CI excluding zero on the positive
    side WITH ACTUAL FILLS, certified CLV >= 0 and precise and representative, both chronological
    halves positive, multiplicity survived, rule pre-registered. CLEAR FAIL needs a realized-unit
    CI excluding zero negative, or a precise and representative certified-CLV CI doing so.

    Multiplicity and pre-registration cannot be computed from the data; they are stated NOT
    MEASURABLE HERE rather than assumed met, which is the difference between a gate and a
    decoration.
    """
    cs = []

    def clause(label, state, detail=""):
        cs.append({"clause": label, "state": state, "detail": detail})

    n = (whole or {}).get("n", 0)
    if not n:
        clause("certified sample", "NOT MEASURABLE", "no certified CLV in this group")
        return {"name": name, "verdict": "INSUFFICIENT EVIDENCE", "clauses": cs,
                "why": "nothing certified to judge"}
    clause("certified sample", "MET" if n >= 20 else "UNMET", f"n={n} (bar is 20)")
    c = whole.get("ci")
    if c is None:
        clause("certified CLV interval", "NOT MEASURABLE", "n too small for an interval")
    elif c[1] < 0:
        clause("certified CLV interval", "UNMET", f"[{c[0]:+.2f}, {c[1]:+.2f}]% excludes zero NEGATIVE")
    elif c[0] > 0:
        clause("certified CLV interval", "MET", f"[{c[0]:+.2f}, {c[1]:+.2f}]% excludes zero positive")
    else:
        clause("certified CLV interval", "UNMET", f"[{c[0]:+.2f}, {c[1]:+.2f}]% straddles zero")
    h1c, h2c = (h1 or {}).get("clv"), (h2 or {}).get("clv")
    if h1c is None or h2c is None:
        clause("both halves positive on CLV", "NOT MEASURABLE", "a half has no certified CLV")
    else:
        clause("both halves positive on CLV", "MET" if (h1c > 0 and h2c > 0) else "UNMET",
               f"H1 {h1c:+.2f}%, H2 {h2c:+.2f}%")
    h1u, h2u = (h1 or {}).get("units"), (h2 or {}).get("units")
    if h1u is None or h2u is None:
        clause("both halves positive on units", "NOT MEASURABLE", "a half has no unit figure")
    else:
        clause("both halves positive on units", "MET" if (h1u > 0 and h2u > 0) else "UNMET",
               f"H1 {h1u:+.2f}u, H2 {h2u:+.2f}u")
    clause("realized-unit CI from CONFIRMED FILLS", "MET" if fills_ok else "UNMET",
           "confirmed fills present" if fills_ok else
           "no confirmed fill in this group - every unit figure here is hypothetical")
    clause("multiplicity survived", "NOT MEASURABLE", "decided in SCORECARD.md, not computable here")
    clause("rule pre-registered", "NOT MEASURABLE", "decided in REGISTRY.md, not computable here")
    neg = c is not None and c[1] < 0
    if neg and n >= 20:
        v = "CLEAR FAIL"
    elif n < 20:
        v = "INSUFFICIENT EVIDENCE"
    else:
        v = "CONTINUE TESTING"
    # PASS is never rendered from a computation: it requires the two NOT MEASURABLE clauses and a
    # realized-unit CI from fills. If those are ever all met the page says SO FAR SO GOOD and
    # points at SCORECARD.md, because promotion is Peter's decision and not a dashboard's.
    if (not neg and n >= 20 and fills_ok and c and c[0] > 0
            and (h1c or 0) > 0 and (h2c or 0) > 0 and (h1u or 0) > 0 and (h2u or 0) > 0):
        v = "ALL COMPUTABLE CLAUSES MET - needs multiplicity + pre-registration in SCORECARD.md"
    return {"name": name, "verdict": v, "clauses": cs}


def split_by_cutoff(obs):
    pre = [o for o in obs if o.get("game_start") and cl.tp(o["game_start"]) and cl.tp(o["game_start"]) < CUTOFF]
    post = [o for o in obs if o.get("game_start") and cl.tp(o["game_start"]) and cl.tp(o["game_start"]) >= CUTOFF]
    nos = [o for o in obs if not (o.get("game_start") and cl.tp(o["game_start"]))]
    return pre, post, nos


# ------------------------------------------------------------------ freshness
def age_of(path):
    try:
        import subprocess
        t = subprocess.run(["git", "log", "-1", "--format=%cI", "--", path],
                           capture_output=True, text=True, timeout=30).stdout.strip()
        d = cl.tp(t)
        return d
    except Exception:
        return None


def band_a(now, reg, st, counts):
    """Status strip. Every figure below is stamped with the age of the data it came from."""
    srcs = []

    def add(name, when, extra=""):
        if when is None:
            srcs.append({"src": name, "state": "UNKNOWN", "age_h": None,
                         "detail": extra or "no timestamp available - not treated as fresh"})
            return
        h = (now - when).total_seconds() / 3600.0
        b = BUDGET_H.get(name)
        state = ("UNKNOWN" if b is None else ("FRESH" if h <= b else "STALE"))
        srcs.append({"src": name, "state": state, "age_h": round(h, 1),
                     "budget_h": b, "when": cl.iso(when), "detail": extra})

    add("ledger", age_of("clv/state.enc"), f"{counts.get('rows', 0)} ledger rows")
    add("tracker", age_of("tracker/state.enc"))
    add("liquidity", age_of("liquidity/alerts.json"))
    add("sharp", age_of("alerts.json"))
    # The registry's own freshness key is complete_at; "updated"/"ts" do not exist, and reading
    # for them reported the registry UNKNOWN - which rolls the whole status strip to UNKNOWN - on
    # a store that was in fact minutes old.
    rmeta = ((reg or {}).get("meta") or {})
    add("registry", cl.tp(rmeta.get("complete_at") or rmeta.get("updated") or rmeta.get("ts")),
        f"{len((reg or {}).get('orders') or [])} order rows" if reg else "registry unreadable")
    hc = os.environ.get("HCACHE_DIR", "") or "hcache"
    add("hcache", now if os.path.isdir(hc) else None,
        f"{len(os.listdir(hc))} files" if os.path.isdir(hc) else "not restored in this run")
    worst = ("FAILED" if any(s["state"] == "FAILED" for s in srcs)
             else "STALE" if any(s["state"] == "STALE" for s in srcs)
             else "UNKNOWN" if any(s["state"] == "UNKNOWN" for s in srcs) else "FRESH")
    return {"sources": srcs, "overall": worst,
            "note": ("Every figure on this page is stamped with the age of the data it came from. "
                     "A cancelled workflow run is reported UNKNOWN, never as a pass or a failure.")}


# ------------------------------------------------------------------ main build
def build():
    now = datetime.now(timezone.utc)
    warn = []
    try:
        st = tb.dec(json.load(open(cl.STATE)))
    except Exception as e:
        return None, f"clv/state.enc unreadable ({type(e).__name__})"
    reg = None
    try:
        reg = rg.load()
    except Exception as e:
        warn.append(f"private registry unreadable ({type(e).__name__}) - lane attribution and "
                    f"confirmed fills are NOT AVAILABLE, not empty")
    bets = st.get("bets") or {}
    # Same loads clv_coverage uses, deliberately: the tracker is its OWN encrypted state (not a
    # key inside the ledger's), and the stale map needs both. My first version read
    # st["tr"]/st["tracker"], which do not exist - it would have handed every row an empty
    # tracker, silently losing dup_of resolution and the stale exclusion while still printing a
    # full-looking page.
    try:
        tracker = (tb.dec(json.load(open(tb.STATE))) or {}).get("bets") or {}
    except Exception as e:
        tracker, _ = {}, warn.append(
            f"tracker/state.enc unreadable ({type(e).__name__}) - dup_of resolution and the stale "
            f"exclusion are NOT AVAILABLE for this build, so selection counts may double-count a "
            f"manual note and its venue row")
    try:
        stale = cstale.stale_map(bets, tracker)
    except Exception:
        stale = {}
    # Certified-only, exactly as clv_coverage does it: a row under fixture doubt is excluded
    # rather than scored, and a proven stale duplicate is excluded rather than counted twice.
    certified = {k: r for k, r in bets.items()
                 if r.get("clv") is not None and not r.get("fixture_doubt") and k not in stale}
    obs = csel.selections(certified, tracker, exclude=set(stale))
    missing = {k: r for k, r in bets.items() if r.get("clv") is None and k not in stale}
    lane_for = cov.build_lane_resolver(reg or {})
    fills = rg.fills() if reg is not None else {}
    confirmed = {k for k, v in (fills or {}).items()
                 if str((v or {}).get("state") or "").upper() in ("FILLED", "PARTIAL")}

    # lane attribution - provable only, everything else an exception
    by_lane = collections.defaultdict(list)
    unassigned = []
    for key, o in obs.items():
        lane = lane_for(key, o)
        if lane:
            o = dict(o, lane=lane)
            by_lane[lane].append(o)
        else:
            unassigned.append({"key": key[:60], "league": str(key.split("|")[0]),
                               "n_fills": o.get("n_fills", 1),
                               "why": "no single registry order joins this selection"})

    # Exceptions: settled selections carrying no certified CLV, attributed to a lane the same
    # provable way as the certified ones. Collapsed with the same identity rule so one bet filled
    # in pieces is one exception, not thirteen.
    miss_obs = {}
    try:
        groups = collections.defaultdict(list)
        for rid, rec in missing.items():
            k, _why = csel.row_key(rid, rec, tracker)
            groups[k].append((rid, rec))
        for k, rows_ in groups.items():
            snap = (rows_[0][1].get("snap") or {})
            miss_obs[k] = {"n_fills": len(rows_), "game_start": snap.get("game_start"),
                           "league": snap.get("league"), "result": snap.get("result"),
                           "ids": [i for i, _ in rows_]}
    except Exception as e:
        warn.append(f"exception list unavailable ({type(e).__name__})")
    miss_by_lane = collections.defaultdict(list)
    miss_unassigned = 0
    for k, o in miss_obs.items():
        ln = lane_for(k, o)
        rec = {"key": k[:60], "n_fills": o.get("n_fills", 1),
               "why": "no certified Pinnacle CLV after settlement"}
        if ln:
            miss_by_lane[ln].append(rec)
        else:
            miss_unassigned += 1

    # How much of the ledger the registry can even speak to. Without this the page shows a large
    # exception count with no way to tell a broken join from a store that simply does not go back
    # that far - two states with opposite remedies.
    otimes = sorted(str(o.get("run_start_utc") or o.get("decided_utc") or "")
                    for o in ((reg or {}).get("orders") or []) if o)
    otimes = [t for t in otimes if t]
    reg_window = {"orders": len(otimes), "first": otimes[0] if otimes else None,
                  "last": otimes[-1] if otimes else None}
    if otimes:
        lo = cl.tp(otimes[0])
        inw = [(k, o) for k, o in obs.items()
               if o.get("game_start") and cl.tp(o["game_start"]) and cl.tp(o["game_start"]) >= lo]
        reg_window["in_window"] = len(inw)
        reg_window["in_window_attributed"] = sum(1 for k, o in inw if lane_for(k, o))
        reg_window["before_window"] = len(obs) - len(inw)

    today = now.astimezone(ET).date()
    bands = {}

    # ---- B: live lanes
    lanes = []
    for lane in ("rules", "r1", "board", "lane2"):
        rows = by_lane.get(lane, [])
        unit = LANE_UNIT.get(lane)
        day = [o for o in rows if o.get("game_start") and cl.tp(o["game_start"])
               and cl.tp(o["game_start"]).astimezone(ET).date() == today]
        pre, post, nos = split_by_cutoff(rows)
        h1, h2, nokey = csel.halves(rows)
        # The collapsed observation carries "ids" (clv_selection.collapse), not "fill_ids".
        # My first version read a key that does not exist, which would have reported ZERO
        # confirmed fills for every lane - and a zero here is read as "no confirmed fill, every
        # unit figure hypothetical", so the page would have understated live performance while
        # looking entirely normal.
        fl = [o for o in rows if set(o.get("ids") or []) & confirmed]
        lanes.append({
            "lane": lane, "name": LANE_NAME.get(lane, lane), "unit_registered": unit,
            "paper": lane == "lane2",
            "today": blk(day, unit), "cumulative": blk(rows, unit),
            "post_change": blk(post, unit), "pre_change": blk(pre, unit),
            "h1": blk(h1, unit), "h2": blk(h2, unit),
            "no_sort_key": len(nokey), "no_cutoff_key": len(nos),
            "confirmed_fill_selections": len(fl),
            "confirmed_fills_note": (
                "Live P/L, ROI and units are reported from CONFIRMED FILLS only. Refused, "
                "unfilled and paper plays are counted separately and never summed into these."),
            # obs is certified-only, so an exception can never be found in it: the rows worth
            # reporting are the ones with NO CLV at all, which live in `missing`. Reading them
            # off obs returned an empty list for every lane - the exception band would have been
            # permanently, silently clean.
            "exceptions": miss_by_lane.get(lane, [])[:25],
        })
        lanes[-1]["gate"] = gate(LANE_NAME.get(lane, lane), lanes[-1]["h1"], lanes[-1]["h2"],
                                 lanes[-1]["cumulative"], bool(fl))
    bands["B_lanes"] = {"lanes": lanes,
                        "unassigned": unassigned[:40], "unassigned_n": len(unassigned),
                        "unassigned_missing_n": miss_unassigned,
                        "missing_total": len(miss_obs),
                        "registry_window": reg_window,
                        "window_note": (
                            "Lane attribution is bounded by the registry's own history, not by the "
                            "join. The private bot-order registry's earliest order is "
                            f"{reg_window.get('first') or 'unknown'} and its latest is "
                            f"{reg_window.get('last') or 'unknown'}, so a selection that settled "
                            "before that window has no order to be joined to and CANNOT be "
                            "attributed by verified evidence. Those are reported as exceptions, "
                            "never attributed on a guess. Within the window: "
                            f"{reg_window.get('in_window_attributed', 0)} of "
                            f"{reg_window.get('in_window', 0)} attributed."),
                        "note": ("A selection appears under a lane only where ONE registry order "
                                 "provably joins it (same league, market, side, nesting game "
                                 "tokens, within 7 days). Everything else is an exception above, "
                                 "never attributed on a guess - a wrong lane label moves one "
                                 "strategy's performance onto another.")}

    # ---- D: triggers, individually
    trig = []
    for lane in ("rules", "r1", "board"):
        rows = by_lane.get(lane, [])
        for lg, group in sorted(collections.Counter(
                str(k.split("|")[0]) for k, o in obs.items() if lane_for(k, o) == lane).items()):
            sel = [o for k, o in obs.items() if lane_for(k, o) == lane and k.split("|")[0] == lg]
            h1, h2, _ = csel.halves(sel)
            trig.append({"lane": LANE_NAME.get(lane, lane), "trigger": f"{lg}",
                         "live": True, "whole": blk(sel, LANE_UNIT.get(lane)),
                         "h1": blk(h1, LANE_UNIT.get(lane)), "h2": blk(h2, LANE_UNIT.get(lane))})
    bands["D_triggers"] = {"live": trig, "collapsed_by_default": True,
                           "registered_total": 32,
                           "note": ("Live lanes and their triggers first. Expand for all 32 "
                                    "registered entries, whose status is quoted from "
                                    "SCORECARD.md as frozen and is not recomputed here.")}

    # ---- E: the pricing-model change
    allrows = [o for rows in by_lane.values() for o in rows]
    pre, post, nos = split_by_cutoff(allrows)
    bands["E_change"] = {
        "label": CUTOFF_LABEL, "cutoff_utc": cl.iso(CUTOFF),
        "before": blk(pre), "after": blk(post), "no_date": len(nos),
        "evidence": ("Cutoff from the private bot-order registry: the first verified production "
                     "execution under commit 7e7c20df is 2026-11-11T16:31:19Z. In that one run "
                     "two rows refused on the new price ceiling and two placed orders under the "
                     "new limit logic, so both halves of the change took effect together."),
        "caveat": ("NOT A CONTROLLED TEST - nothing else was held constant across this boundary. "
                   "n is printed beside every figure because at these sample sizes the honest "
                   "reading is usually 'no difference detected', which is not 'no difference'."),
    }

    # ---- F: research candidates, visually separate
    bands["F_research"] = {
        "title": "RESEARCH - NOT LIVE, NOT STAKED",
        "candidates": research_candidates(obs, lane_for),
        "note": ("Ranked by how close they are to the registered bar, with the missing clause "
                 "named. Every unverified figure reads INSUFFICIENT EVIDENCE; no old-scorecard "
                 "CLV is ever substituted for a missing new-basis figure."),
    }

    bands["A_status"] = band_a(now, reg, st, {"rows": len(bets)})
    bands["A_status"]["warnings"] = warn
    bands["C_qualification"] = {
        "lanes": [{"name": l["name"], "gate": l["gate"]} for l in lanes],
        "note": ("Clause by clause against the registered rules. NOT MEASURABLE is not MET: "
                 "multiplicity and pre-registration are decided in SCORECARD.md and REGISTRY.md "
                 "and are never assumed here. No PASS is rendered from a computation."),
    }
    view = {
        "generated_utc": cl.iso(now),
        "generated_et": now.astimezone(ET).strftime("%Y-%m-%d %H:%M ET"),
        "basis": cb.BASIS_VERSION, "sha": os.environ.get("GITHUB_SHA", "")[:8],
        "run": os.environ.get("GITHUB_RUN_ID", ""),
        "cutoff_label": CUTOFF_LABEL,
        "selections_total": len(obs), "bands": bands,
        "privacy": ("Counts, units and percentages only. No balances, no currency stakes, no "
                    "account identifiers, no order ids, no secrets."),
    }
    return view, None


def research_candidates(obs, lane_for):
    """The five closest research candidates, from certified data only.

    Closeness is distance to the registered bar on the clauses that CAN be computed - never a
    ranking by CLV alone, which would promote a thin positive sample over a well-measured one.
    """
    pools = {}
    for k, o in obs.items():
        if lane_for(k, o):
            continue                      # live lanes belong in band B, not here
        lg = str(k.split("|")[0] or "?")
        mkt = str(k.split("|")[2]) if len(k.split("|")) > 2 else "?"
        pools.setdefault(f"{lg} {mkt}", []).append(o)
    out = []
    for name, sel in pools.items():
        w = blk(sel)
        if not w.get("n"):
            continue
        h1, h2, _ = csel.halves(sel)
        b1, b2 = blk(h1), blk(h2)
        miss = []
        if w["n"] < 20:
            miss.append(f"sample n={w['n']} below 20")
        if w.get("ci") is None:
            miss.append("no interval at this n")
        elif w["ci"][0] <= 0:
            miss.append("CLV interval does not exclude zero positive")
        if (b1.get("clv") or 0) <= 0 or (b2.get("clv") or 0) <= 0:
            miss.append("both halves not positive on CLV")
        miss.append("no confirmed fills - realized-unit CI not obtainable")
        out.append({"name": name, "whole": w, "h1": b1, "h2": b2,
                    "missing": miss, "verdict": "INSUFFICIENT EVIDENCE",
                    "rank_key": (len(miss), -(w.get("clv") or -99), -w["n"])})
    out.sort(key=lambda r: r["rank_key"])
    for r in out:
        r.pop("rank_key", None)
    return out[:5]


# ------------------------------------------------------------------ render
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Daily Dashboard</title>
<meta name="robots" content="noindex"><meta name="theme-color" content="#0f1311">
<style>
:root{--bg:#0f1311;--card:#171c1a;--line:#2a312e;--fg:#eef1ef;--muted:#8b958f;--ok:#4ade80;--bad:#f87171;--warn:#fbbf24}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 Inter,system-ui,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:16px}
h1{font-size:19px;margin:0 0 2px}h2{font-size:15px;margin:22px 0 8px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.sub{color:var(--muted);font-size:12px;margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:right;padding:5px 7px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.mut{color:var(--muted)}
.pill{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;border:1px solid var(--line)}
details{margin:6px 0}summary{cursor:pointer;color:var(--muted);font-size:12px}
.research{border:2px solid var(--warn);border-radius:10px;padding:12px;margin-top:26px}
#f{display:flex;gap:8px;margin:40px 0}input{flex:1;padding:10px;border-radius:8px;border:1px solid var(--line);background:#101413;color:var(--fg)}
button{padding:10px 16px;border-radius:8px;border:0;background:#2f6b4f;color:#fff;font-weight:600}
</style></head><body><div class="wrap" id="app">
<form id="f"><input id="p" type="password" placeholder="Passphrase" autocomplete="current-password">
<button>Unlock</button></form><p class="sub" id="e"></p></div>
<script>
let BLOB=__BLOB__;
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function unlock(pass){
 const km=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveKey']);
 const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64(BLOB.s),iterations:BLOB.n,hash:'SHA-256'},
   km,{name:'AES-GCM',length:256},false,['decrypt']);
 const pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64(BLOB.i)},key,b64(BLOB.c));
 return JSON.parse(new TextDecoder().decode(pt));}
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const n0=v=>v==null?'<span class="mut">&ndash;</span>':v;
const sg=v=>v==null?'<span class="mut">&ndash;</span>':(v>0?'<span class="ok">+'+v.toFixed(2)+'</span>':'<span class="bad">'+v.toFixed(2)+'</span>');
const ciS=c=>c?('['+c[0].toFixed(2)+', '+c[1].toFixed(2)+']'):'<span class="mut">&ndash;</span>';
function fig(b){if(!b||!b.n)return '<span class="mut">&ndash; '+esc((b&&b.why)||'no data')+'</span>';
 return 'n '+b.n+' &middot; CLV '+sg(b.clv)+'% '+ciS(b.ci)+' &middot; pos '+b.pos+'/'+b.n+' ('+b.pos_pct+'%) &middot; u '+
 (b.units==null?('<span class="mut">&ndash;</span>'):sg(b.units))+' &middot; ROI '+(b.roi_pct==null?('<span class="mut">UNAVAIL</span>'):sg(b.roi_pct)+'%');}
function row(label,b){return '<tr><td>'+esc(label)+'</td><td>'+(b&&b.n?b.n:'<span class="mut">&ndash;</span>')+'</td><td>'+
 (b&&b.n?sg(b.clv)+'%':'&ndash;')+'</td><td>'+(b&&b.n?ciS(b.ci):'&ndash;')+'</td><td>'+(b&&b.n?b.pos+'/'+b.n:'&ndash;')+'</td><td>'+
 (b&&b.units!=null?sg(b.units)+'u':'<span class="mut">&ndash;</span>')+'</td><td>'+(b&&b.roi_pct!=null?sg(b.roi_pct)+'%':'<span class="mut">UNAVAIL</span>')+'</td></tr>';}
const TH='<tr><th>period</th><th>n</th><th>CLV</th><th>95% CI</th><th>pos</th><th>units</th><th>ROI</th></tr>';
function render(d){const B=d.bands;let h='';
 h+='<h1>Daily Dashboard</h1><p class="sub">'+esc(d.generated_et)+' &middot; basis '+esc(d.basis)+
   (d.sha?(' &middot; '+esc(d.sha)):'')+' &middot; '+esc(d.selections_total)+' selections &middot; '+esc(d.privacy)+'</p>';
 const A=B.A_status;const cls=A.overall==='FRESH'?'ok':(A.overall==='STALE'?'warn':'bad');
 h+='<h2>A &middot; Status</h2><div class="card"><p><span class="pill '+cls+'">'+esc(A.overall)+'</span> '+esc(A.note)+'</p><table>'+
   '<tr><th>source</th><th>state</th><th>age (h)</th><th>budget</th><th>detail</th></tr>';
 A.sources.forEach(s=>{const c=s.state==='FRESH'?'ok':(s.state==='STALE'?'warn':'bad');
  h+='<tr><td>'+esc(s.src)+'</td><td class="'+c+'">'+esc(s.state)+'</td><td>'+n0(s.age_h)+'</td><td>'+n0(s.budget_h)+'</td><td>'+esc(s.detail||'')+'</td></tr>';});
 h+='</table>'+(A.warnings&&A.warnings.length?('<p class="bad">'+A.warnings.map(esc).join('<br>')+'</p>'):'')+'</div>';
 h+='<h2>B &middot; Live lanes</h2>';
 B.B_lanes.lanes.forEach(L=>{h+='<div class="card"><p><b>'+esc(L.name)+'</b>'+(L.paper?' <span class="pill warn">PAPER</span>':'')+
  ' <span class="pill">'+esc(L.gate.verdict)+'</span></p><table>'+TH+
  row('today',L.today)+row('cumulative',L.cumulative)+row('since the change',L.post_change)+row('before the change',L.pre_change)+
  row('first half',L.h1)+row('second half',L.h2)+'</table>'+
  '<p class="sub">confirmed-fill selections '+L.confirmed_fill_selections+' &middot; '+esc(L.confirmed_fills_note)+'</p>'+
  (L.exceptions.length?('<details><summary>'+L.exceptions.length+' exception(s): settled with no certified CLV</summary><table>'+
    L.exceptions.map(x=>'<tr><td>'+esc(x.key)+'</td><td>'+esc(x.why)+'</td></tr>').join('')+'</table></details>'):'')+'</div>';});
 h+='<div class="card"><p><b>'+B.B_lanes.unassigned_n+' unassigned selection(s)</b> &mdash; exceptions, not losses</p><p class="sub">'+
   esc(B.B_lanes.window_note||'')+'</p><p class="sub">'+esc(B.B_lanes.note)+'</p>'+(B.B_lanes.unassigned.length?('<details><summary>show</summary><table>'+
   B.B_lanes.unassigned.map(x=>'<tr><td>'+esc(x.key)+'</td><td>'+esc(x.why)+'</td></tr>').join('')+'</table></details>'):'')+'</div>';
 const C=B.C_qualification;h+='<h2>C &middot; Qualification</h2><div class="card"><p class="sub">'+esc(C.note)+'</p>';
 C.lanes.forEach(x=>{h+='<details><summary><b>'+esc(x.name)+'</b> &mdash; '+esc(x.gate.verdict)+'</summary><table>'+
  '<tr><th>clause</th><th>state</th><th>detail</th></tr>'+x.gate.clauses.map(c=>{const cc=c.state==='MET'?'ok':(c.state==='UNMET'?'bad':'warn');
   return '<tr><td>'+esc(c.clause)+'</td><td class="'+cc+'">'+esc(c.state)+'</td><td>'+esc(c.detail)+'</td></tr>';}).join('')+'</table></details>';});
 h+='</div>';
 const D=B.D_triggers;h+='<h2>D &middot; Triggers</h2><div class="card"><p class="sub">'+esc(D.note)+'</p><details><summary>'+
  D.live.length+' live trigger row(s) &mdash; expand</summary><table><tr><th>lane</th><th>trigger</th><th>whole</th><th>H1</th><th>H2</th></tr>'+
  D.live.map(t=>'<tr><td>'+esc(t.lane)+'</td><td>'+esc(t.trigger)+'</td><td>'+fig(t.whole)+'</td><td>'+fig(t.h1)+'</td><td>'+fig(t.h2)+'</td></tr>').join('')+
  '</table></details></div>';
 const E=B.E_change;h+='<h2>E &middot; '+esc(E.label)+'</h2><div class="card"><table>'+TH+
  row('before',E.before)+row('after',E.after)+'</table><p class="sub">'+esc(E.evidence)+'</p><p class="warn">'+esc(E.caveat)+'</p></div>';
 const F=B.F_research;h+='<div class="research"><h2 style="color:var(--warn)">F &middot; '+esc(F.title)+'</h2><p class="sub">'+esc(F.note)+'</p>'+
  (F.candidates.length?('<table><tr><th>candidate</th><th>whole</th><th>H1</th><th>H2</th><th>missing</th></tr>'+
   F.candidates.map(c=>'<tr><td>'+esc(c.name)+'</td><td>'+fig(c.whole)+'</td><td>'+fig(c.h1)+'</td><td>'+fig(c.h2)+'</td><td>'+
    c.missing.map(esc).join('<br>')+'</td></tr>').join('')+'</table>'):'<p class="mut">no candidate carries certified data</p>')+'</div>';
 document.getElementById('app').innerHTML=h;}
async function go(p,save){try{const d=await unlock(p);try{if(save)localStorage.setItem('dbp',p)}catch(e){}render(d);}
 catch(e){document.getElementById('e').textContent='Wrong passphrase.';try{localStorage.removeItem('dbp')}catch(_){}}}
document.getElementById('f').onsubmit=e=>{e.preventDefault();go(document.getElementById('p').value,true);};
try{const s=localStorage.getItem('dbp');if(s)go(s,false);}catch(e){}
</script></body></html>"""


def email_body(view):
    """One concise daily summary. Counts, units and percentages - no dollar figures."""
    B = view["bands"]
    L = [f"DAILY DASHBOARD - {view['generated_et']}", f"basis {view['basis']}", ""]
    A = B["A_status"]
    L.append(f"DATA: {A['overall']}")
    for s in A["sources"]:
        if s["state"] != "FRESH":
            L.append(f"  {s['state']:<7} {s['src']} "
                     + (f"{s['age_h']}h old" if s.get("age_h") is not None else "no timestamp")
                     + (f" - {s['detail']}" if s.get("detail") else ""))
    for w in A.get("warnings") or []:
        L.append(f"  WARNING {w}")
    L.append("")
    for x in B["B_lanes"]["lanes"]:
        t, c = x["today"], x["cumulative"]
        L.append(f"{x['name']}{' (paper)' if x['paper'] else ''}: {x['gate']['verdict']}")
        for lab, b in (("today", t), ("cumulative", c), ("since the change", x["post_change"])):
            if b.get("n"):
                u = f"{b['units']:+.2f}u" if b.get("units") is not None else "units -"
                r = f"{b['roi_pct']:+.2f}%" if b.get("roi_pct") is not None else "ROI UNAVAIL"
                L.append(f"  {lab:<18} n {b['n']:>4}  CLV {b['clv']:+.2f}%  "
                         f"CI {b['ci'] if b.get('ci') else '-'}  pos {b['pos']}/{b['n']}  {u}  {r}")
            else:
                L.append(f"  {lab:<18} -  {b.get('why', 'no data')}")
        h1, h2 = x["h1"], x["h2"]
        L.append(f"  halves             H1 CLV {h1.get('clv', '-')}%  H2 CLV {h2.get('clv', '-')}%"
                 f"   (the registered gate needs BOTH positive)")
        L.append(f"  confirmed-fill selections {x['confirmed_fill_selections']}; "
                 f"exceptions {len(x['exceptions'])}")
        L.append("")
    L.append(f"UNASSIGNED selections (exceptions, not losses): {B['B_lanes']['unassigned_n']}")
    rw = B["B_lanes"].get("registry_window") or {}
    if rw.get("orders"):
        L.append(f"  lane attribution is bounded by the registry's own history "
                 f"({rw.get('first', '?')[:16]} to {rw.get('last', '?')[:16]}, {rw['orders']} "
                 f"orders): {rw.get('in_window_attributed', 0)}/{rw.get('in_window', 0)} "
                 f"attributed inside that window, {rw.get('before_window', 0)} selections settled "
                 f"before it and cannot be attributed by verified evidence")
    E = B["E_change"]
    L.append("")
    L.append(f"{E['label']}: before {E['before'].get('n', 0)} / after {E['after'].get('n', 0)} "
             f"selections. NOT a controlled test.")
    L.append("")
    L.append("RESEARCH (not live, not staked): "
             + ("; ".join(c["name"] for c in B["F_research"]["candidates"]) or "none certified"))
    L.append("")
    L.append("No promotion, demotion, stake change or switch follows from this report.")
    return "\n".join(L)


def send_email(view, body):
    """One concise summary per ET day. NO DUPLICATES, enforced by a committed marker.

    Peter: "One concise daily summary ... No duplicate emails." A manual re-dispatch, a retry after
    a failed step, or two schedules firing would each otherwise send another copy, so the ET date
    of the last send is written next to the page and committed. The marker is checked BEFORE the
    send and written only AFTER it succeeds: a failed send must be retryable, and a successful one
    must not be repeatable.
    """
    day = datetime.now(timezone.utc).astimezone(ET).strftime("%Y-%m-%d")
    mark = os.path.join(OUT, "last_email.txt")
    try:
        if open(mark).read().strip() == day and not os.environ.get("DASH_EMAIL_FORCE"):
            print(f"email: already sent for {day} - not sending a duplicate", flush=True)
            return "skipped-duplicate"
    except Exception:
        pass
    user = os.environ.get("GMAIL_ADDRESS", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = os.environ.get("EMAIL_TO", "").strip() or user
    if not (user and pw):
        print("email: not configured - page built, no send attempted", flush=True)
        return "not-configured"
    import smtplib
    from email.message import EmailMessage
    m = EmailMessage()
    A = view["bands"]["A_status"]
    m["Subject"] = f"Daily dashboard {day} - data {A['overall']}"
    m["From"], m["To"] = user, to
    url = os.environ.get("DASH_URL", "").strip()
    m.set_content(body + ("\n\nDashboard: " + url if url else "")
                  + "\n\nCounts, units and percentages only. Dollar figures stay out of this "
                    "summary and off the page.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(user, pw)
        s.send_message(m)
    os.makedirs(OUT, exist_ok=True)
    with open(mark, "w") as f:
        f.write(day + "\n")
    print(f"email: sent for {day}", flush=True)
    return "sent"


def main():
    view, err = build()
    if err:
        print(f"DASHBOARD FAILED: {err}", flush=True)
        return 1
    os.makedirs(OUT, exist_ok=True)
    html = PAGE.replace("__BLOB__", json.dumps(tb.enc(view)))
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(html)
    body = email_body(view)
    with open(os.path.join(OUT, "summary.txt"), "w") as f:
        f.write(body)
    mail = "not-requested"
    if (os.environ.get("DASH_EMAIL") or "").strip() in ("1", "on", "yes", "true"):
        try:
            mail = send_email(view, body)
        except Exception as e:
            mail = f"FAILED ({type(e).__name__})"
            print(f"email: {mail} - the page still built", flush=True)
    # counts only in the log, per the repo rule
    A = view["bands"]["A_status"]
    # Warnings go to the LOG as well as the page. The first run built a page with zero lane
    # attribution and the only record of why was inside the encrypted payload, where no one
    # reading the run would see it.
    for w_ in A.get("warnings") or []:
        print(f"WARNING: {w_}", flush=True)
    print(f"dashboard: {view['selections_total']} selections | data {A['overall']} | "
          f"lanes {len(view['bands']['B_lanes']['lanes'])} | "
          f"unassigned {view['bands']['B_lanes']['unassigned_n']} | "
          f"triggers {len(view['bands']['D_triggers']['live'])} | "
          f"candidates {len(view['bands']['F_research']['candidates'])} | "
          f"page {len(html)} bytes | email {mail}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

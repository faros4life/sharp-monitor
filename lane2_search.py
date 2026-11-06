"""LANE 2 SEARCH - one offline, research-only backtest (Nov 6 2026; Peter approved 15:42 ET).
Paper only. Reads liquidity/alerts.json + the restored OddsPapi history cache + the cached fixtures. No API key is
present, nothing is saved or sent, no live rule is touched. Official CLV standard clv_std.FEE_MODEL.

PRE-REGISTERED (fixed before any result was seen; nothing below is tuned):
  Entry      decision time = alerted_utc (t0). Entry price = best AFTER-FEE TAKER price (clv_std.best_net, AUTO venues) among
             exchange quotes whose last tick is AT OR BEFORE t0 and no older than QUOTE_AGE_CAP. A quote more than +15% vs
             Pinnacle's fair read AT t0 is a misread and rejected (causal). No later quote is ever read.
  Close      Pinnacle no-vig close from cl.close_for(), VERIFIED SAME-LINE only (clv_std.close_verified), close read no older
             than PIN_CLOSE_AGE_CAP min. Converted / half-point closes are excluded and counted.
  Net CLV    (p_close x net entry decimal - 1) x 100.  Units = flat 1u at that net decimal, exchange settlement result.
  Dedup      first USABLE alert per (fixture, market). Uncertainty = bootstrap clustered by fixture (game).
  Split      FIT = alerts through 2026-10-29 ET, CHECK = 2026-10-30 ET onward.  Gate: INSUFFICIENT DATA if usable unique
             games < 40 (research screen, not proof of sufficiency) or CHECK games < 20.
  Verdict    PASS only if FIT mean > 0 AND CHECK mean > 0 AND CHECK one-sided cluster-bootstrap p is Holm-significant
             (alpha .05, three hypotheses; INSUFFICIENT counts as p = 1). H3 also needs treated > matched controls.
  H1  market total, side OVER, no sharp_oppose (all leagues NBA/NFL/NCAAF/NHL; missing opposition is NOT proof of none).
  H2  NBA, any market, no sharp_oppose, second book confirms depth (rule_met). Features reported descriptively only.
  H3  all alerts: Pinnacle limit >= 1.5x its level 2 h earlier (both read at/before t0) AND entry price >= +1% vs Pinnacle fair
      at t0. Controls: same league x market x period, same +1% discrepancy, limit ratio < 1.2.
"""
import collections
import gzip
import json
import os
import random
import sys
from datetime import timedelta, timezone

sys.path.insert(0, os.getcwd())
import clv_ledger as cl      # noqa: E402
import clv_std as cs         # noqa: E402
import hist_cache as hc      # noqa: E402
import nba_names as nn       # noqa: E402
import plimit_level as pl    # noqa: E402

ET = cl.tb.ET
LEAGUES = ("NBA", "NFL", "NCAAF", "NHL")
EXCH = ("prophetx", "novig.us", "kalshi", "polymarket.us")
FROM = cl.tp("2026-10-12T00:00:00Z")
FIT_LAST = "2026-10-29"
QUOTE_AGE_CAP = 300          # seconds
PIN_CLOSE_AGE_CAP = 60       # minutes
GATE_TOTAL, GATE_CHECK = 40, 20
B_BOOT, SEED = 4000, 7
OUT = []


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


def bet_text(a):
    sd, ln, mk = a.get("side"), a.get("line"), a.get("market")
    if mk == "total" and sd in ("OVER", "UNDER") and ln is not None:
        return f"{'Over' if sd == 'OVER' else 'Under'} {ln:g}"
    if mk == "spread" and sd and ln is not None:
        return f"{sd} {ln:+g}"
    if mk == "moneyline" and sd:
        return f"{sd} ML"
    return a.get("side_label")


def units(res, dec):
    return (dec - 1) if res == "W" else (-1.0 if res == "L" else 0.0)


# ------------------------------------------------------------------ build observations
def build():
    A = [a for a in (json.load(open("liquidity/alerts.json")).get("alerts") or [])
         if a.get("league") in LEAGUES and a.get("market") in ("moneyline", "spread", "total")
         and a.get("result") in ("W", "L", "P") and not a.get("artifact") and not a.get("close_suspect")
         and cl.tp(a.get("alerted_utc")) and cl.tp(a["alerted_utc"]) >= FROM and a.get("price")]
    st = {"billable": {}}
    prev = cl.tb.dec(json.load(open(cl.STATE)))
    st["fixtures"] = dict(prev.get("fixtures") or {})
    for k in ("fx_last", "tid", "tname"):
        if prev.get(k) is not None:
            st[k] = prev[k]
    mkmap = json.load(open("clv/markets.json"))["m"]
    P(f"alerts graded in scope: {len(A)} | cached fixtures: {len(st['fixtures'])} | fee model {cs.FEE_MODEL}")
    recs, byfid = [], collections.defaultdict(list)
    for a in A:
        t0 = cl.tp(a["alerted_utc"])
        sd = (a.get("side") or "").upper()
        b = {"bet": bet_text(a), "league": a["league"], "game": (a.get("game") or "").split(":")[0],
             "game_start": a.get("start_utc"), "book": a.get("book")}
        tms = nn.teams_of(a)
        if tms:
            b["teams"] = tms
        r = {"a": a, "b": b, "lg": a["league"], "mk": a["market"], "side": sd, "t0": t0,
             "per": "FIT" if t0.astimezone(ET).strftime("%Y-%m-%d") <= FIT_LAST else "CHECK",
             "oppose": bool(a.get("sharp_oppose")), "agree": bool(a.get("sharp_agree")),
             "depth": bool(a.get("rule_met")), "res": a["result"], "fid": None, "stage": 0, "why": "no fixture matched"}
        r["gkey"] = (a["league"], b["game"], (a.get("start_utc") or "")[:10])
        fid = cl.find_fixture(st, b)
        if fid:
            r["fid"], r["gkey"], r["stage"], r["why"] = fid, fid, 1, "fixture not in history cache (no Pinnacle file)"
            byfid[fid].append(r)
        recs.append(r)
    for fid, rs in byfid.items():
        f = st["fixtures"][fid]
        start = cl.tp(f["start"])
        if not os.path.exists(hc._path(fid, "pinnacle")):
            continue
        h = {"bookmakers": {}}
        for bk in ("pinnacle",) + EXCH:
            p = hc._path(fid, bk)
            if os.path.exists(p):
                try:
                    h["bookmakers"][bk] = json.load(gzip.open(p, "rt"))
                except Exception:
                    pass
        pin = cl.book_markets(h, "pinnacle")
        for r in rs:
            b, lg, t0 = r["b"], r["lg"], r["t0"]
            r["stage"], r["why"] = 2, "no verified same-line Pinnacle close"
            c, _ = cl.close_for(b, f, pin, mkmap, start, lg)
            if not c or not cs.close_verified(c.get("how")) or (c.get("age_min") or 0) > PIN_CLOSE_AGE_CAP:
                if c and not cs.close_verified(c.get("how")):
                    r["why"] = "converted (not same-line) Pinnacle close"
                elif c:
                    r["why"] = "Pinnacle close older than cap"
                continue
            ce, _ = cl.close_for(b, f, pin, mkmap, t0, lg)
            ce = ce if (ce and cs.close_verified(ce.get("how"))) else None
            quotes, ages, rej, seen = {}, {}, 0, 0
            for slug in EXCH:
                bk = cl.book_markets(h, slug)
                x = cl.novig_at(b, f, bk, mkmap, t0, lg) if bk else None
                if not x:
                    continue
                seen += 1
                if x[1] is None or x[1] > QUOTE_AGE_CAP or x[1] < 0:
                    continue
                nd = cs.net_dec(slug, x[0], league=lg)
                if ce and nd and ce["p"] * nd - 1 > 0.15:
                    rej += 1
                    continue
                quotes[slug], ages[slug] = x[0], x[1]
            best = cs.best_net(quotes, scope="auto", league=lg) if quotes else (None, None, None)
            if not best[1]:
                r["why"] = ("no exchange quote at/before entry" if not seen else
                            "exchange quote stale (> cap) or rejected as misread")
                continue
            lim0, _ = pl.pin_limit_at(b, f, pin, mkmap, t0, lg)
            lim2, _ = pl.pin_limit_at(b, f, pin, mkmap, t0 - timedelta(hours=2), lg)
            r.update(stage=3, why="usable", venue=best[0], nd=best[1], age=ages.get(best[2]),
                     clv=round(100 * (c["p"] * best[1] - 1), 4), u=units(r["res"], best[1]),
                     disc=(ce["p"] * best[1] - 1 if ce else None), limx=(lim0 / lim2 if lim0 and lim2 else None))
    return recs


# ------------------------------------------------------------------ statistics
def boot(by_fid):
    keys = list(by_fid)
    rnd = random.Random(SEED)
    out = []
    for _ in range(B_BOOT):
        s = n = 0
        for _ in keys:
            v = by_fid[keys[rnd.randrange(len(keys))]]
            s += sum(v)
            n += len(v)
        out.append(s / n)
    return sorted(out)


def wilson(k, n):
    if not n:
        return (None, None)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5)
    return ((c - m) / d, (c + m) / d)


def summ(rows):
    """rows already deduped. Returns dict with n, games, net CLV, CI, beat%, units, one-sided p."""
    if not rows:
        return {"n": 0, "games": 0}
    by = collections.defaultdict(list)
    for r in rows:
        by[r["fid"]].append(r["clv"])
    bs = boot(by)
    clv = [r["clv"] for r in rows]
    beat = sum(1 for x in clv if x > 0)
    w = wilson(beat, len(rows))
    return {"n": len(rows), "games": len(by), "clv": sum(clv) / len(clv), "lo": bs[int(.025 * B_BOOT)], "hi": bs[int(.975 * B_BOOT)],
            "p": (sum(1 for x in bs if x <= 0) + 1) / (B_BOOT + 1), "beat": 100 * beat / len(rows), "blo": 100 * w[0], "bhi": 100 * w[1],
            "u": sum(r["u"] for r in rows)}


def line(tag, s):
    if not s.get("n"):
        return f"| {tag} | 0 | 0 | - | - | - | - | - |"
    return (f"| {tag} | {s['n']} | {s['games']} | {s['clv']:+.2f}% [{s['lo']:+.2f}, {s['hi']:+.2f}] | "
            f"{s['beat']:.0f}% [{s['blo']:.0f}-{s['bhi']:.0f}] | {s['u']:+.1f}u | p={s['p']:.3f} | |")


def dedup(rows):
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x["t0"]):
        k = (r["fid"], r["mk"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def funnel(name, elig, extra=None):
    P(f"\n### {name} - COVERAGE (alerts / unique games), before any gate")
    P("| stage | alerts | games |"); P("|---|---|---|")
    labels = ["eligible", "fixture matched", "Pinnacle file in cache", "verified same-line close", "fresh causal exchange quote = usable"]
    for k, lb in enumerate(labels):
        rs = [r for r in elig if r["stage"] >= k]
        P(f"| {lb} | {len(rs)} | {len({r['gkey'] for r in rs})} |")
    if extra:
        rs = [r for r in elig if r["stage"] >= 3 and extra(r)]
        P(f"| + hypothesis inputs present (limit ratio / entry fair) | {len(rs)} | {len({r['gkey'] for r in rs})} |")
    P("exclusions:", dict(collections.Counter(r["why"] for r in elig if r["stage"] < 3)))
    P("missingness by league (eligible / usable):", {lg: (sum(1 for r in elig if r["lg"] == lg), sum(1 for r in elig if r["lg"] == lg and r["stage"] >= 3)) for lg in LEAGUES})
    P("missingness by period (eligible / usable):", {p: (sum(1 for r in elig if r["per"] == p), sum(1 for r in elig if r["per"] == p and r["stage"] >= 3)) for p in ("FIT", "CHECK")})


def evaluate(name, rows, extra_check=None):
    use = dedup(rows)
    P(f"usable alerts {len(rows)} -> after game x market dedup {len(use)} ({len({r['fid'] for r in use})} unique games)")
    fit, chk = [r for r in use if r["per"] == "FIT"], [r for r in use if r["per"] == "CHECK"]
    P("| set | n | games | net CLV [95% CI, game-clustered] | beat close [Wilson] | flat units | one-sided p |  |"); P("|---|---|---|---|---|---|---|---|")
    sf, sc, sa = summ(fit), summ(chk), summ(use)
    P(line("FIT", sf)); P(line("CHECK", sc)); P(line("ALL", sa))
    if use:
        P("venues used:", dict(collections.Counter(r["venue"] for r in use)), "| median quote age s:", sorted(r["age"] for r in use)[len(use) // 2])
    insufficient = sa.get("games", 0) < GATE_TOTAL or sc.get("games", 0) < GATE_CHECK
    return {"fit": sf, "chk": sc, "all": sa, "insufficient": insufficient, "use": use}


def main():
    recs = build()
    P(f"\nStages: {dict(collections.Counter(r['why'] for r in recs))}")
    res = {}
    # ---- H1
    e1 = [r for r in recs if r["mk"] == "total" and r["side"] == "OVER" and not r["oppose"]]
    P("\n## H1 totals OVER, no opposing sharp alert  (sharp_agree among eligible:", sum(1 for r in e1 if r['agree']), "of", len(e1), ")")
    funnel("H1", e1)
    res["H1"] = evaluate("H1", [r for r in e1 if r["stage"] >= 3])
    # ---- H2
    e2 = [r for r in recs if r["lg"] == "NBA" and not r["oppose"] and r["depth"]]
    P("\n## H2 NBA, no opposing sharp, second-book depth confirmed")
    funnel("H2", e2)
    res["H2"] = evaluate("H2", [r for r in e2 if r["stage"] >= 3])
    fitu = [r for r in res["H2"]["use"] if r["per"] == "FIT"]
    if fitu:
        P("descriptive only (not tested): CHECK net CLV above vs below the FIT median of each feature")
        for nm, fn in (("base depth", lambda r: r["a"].get("base_depth")), ("new money", lambda r: r["a"].get("new_money")),
                       ("Pinnacle limit x vs 2h", lambda r: r.get("limx"))):
            vals = sorted(v for v in (fn(r) for r in fitu) if v is not None)
            if len(vals) < 4:
                P(f"- {nm}: too few FIT values"); continue
            med = vals[len(vals) // 2]
            hi = [r["clv"] for r in res["H2"]["use"] if r["per"] == "CHECK" and fn(r) is not None and fn(r) >= med]
            lo = [r["clv"] for r in res["H2"]["use"] if r["per"] == "CHECK" and fn(r) is not None and fn(r) < med]
            P(f"- {nm}: median {med:.3g} | above n={len(hi)} mean {sum(hi)/len(hi) if hi else float('nan'):+.2f}% | below n={len(lo)} mean {sum(lo)/len(lo) if lo else float('nan'):+.2f}%")
    # ---- H3
    ok3 = lambda r: r.get("limx") is not None and r.get("disc") is not None
    P("\n## H3 Pinnacle limit jump (>=1.5x vs 2h earlier) + exchange price >= +1% vs Pinnacle fair at entry; matched controls")
    funnel("H3 (all alerts)", recs, ok3)
    u3 = [r for r in recs if r["stage"] >= 3 and ok3(r) and r["disc"] >= 0.01]
    tr = [r for r in u3 if r["limx"] >= 1.5]
    ct = [r for r in u3 if r["limx"] < 1.2]
    res["H3"] = evaluate("H3", tr)
    ctd = dedup(ct)
    P(f"controls (disc >= +1%, limit ratio < 1.2): {len(ct)} usable -> {len(ctd)} deduped; limit ratio missing for {sum(1 for r in recs if r['stage']>=3 and not ok3(r))} usable alerts (excluded)")
    diffs = {}
    for per in ("FIT", "CHECK"):
        t = [r for r in res["H3"]["use"] if r["per"] == per]
        diffs[per] = None
        if t:
            tot = 0.0
            for r in t:
                cs_ = [x["clv"] for x in ctd if x["per"] == per and x["lg"] == r["lg"] and x["mk"] == r["mk"]]
                tot += (r["clv"] - sum(cs_) / len(cs_)) if cs_ else 0.0
            n_m = sum(1 for r in t if any(x["per"] == per and x["lg"] == r["lg"] and x["mk"] == r["mk"] for x in ctd))
            diffs[per] = (tot / n_m if n_m else None, n_m)
    P("treated minus stratum-matched control mean net CLV (treated obs with a control in the same league x market x period):", diffs)
    # ---- Holm + verdicts
    P("\n## VERDICTS (Holm across H1,H2,H3; alpha .05)")
    ps = {k: (1.0 if v["insufficient"] or not v["chk"].get("n") else v["chk"]["p"]) for k, v in res.items()}
    order = sorted(ps, key=lambda k: ps[k])
    hok, alive = {}, True
    for i, k in enumerate(order):
        alive = alive and ps[k] <= 0.05 / (3 - i)
        hok[k] = alive
    final = {}
    for k, v in res.items():
        if v["insufficient"]:
            final[k] = "INSUFFICIENT DATA"
        else:
            good = v["fit"].get("clv", -1) > 0 and v["chk"].get("clv", -1) > 0 and hok[k]
            if k == "H3":
                d = diffs.get("CHECK")
                good = good and d is not None and d[0] is not None and d[0] > 0
            final[k] = "PASS" if good else "FAIL"
        P(f"{k}: {final[k]} | usable games {v['all'].get('games', 0)} (CHECK {v['chk'].get('games', 0)}) | CHECK p={ps[k]:.3f}, Holm-significant: {hok[k]}")
    vals = set(final.values())
    overall = "PASS" if "PASS" in vals else ("FAIL" if "FAIL" in vals else "INSUFFICIENT DATA")
    P(f"\nOVERALL: {overall}. Research only; nothing is deployed. Three hypotheses tested once; no other slices were searched.")
    os.makedirs("summary", exist_ok=True)
    open("summary/summary.md", "w").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()

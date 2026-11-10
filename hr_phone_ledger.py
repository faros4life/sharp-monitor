#!/usr/bin/env python3
"""
HR PHONE-ALERT LEDGER (Peter, Nov 10 2026). READ-ONLY. Changes no rule, gate, threshold, notification or lane.

Reports three groups SEPARATELY, never summed:
  A. ACTUAL PHONE PUSHES   - only Wake Forest and Indiana have documented push evidence (Peter, Nov 10).
  B. ACTUAL MANUAL WAGERS  - rows in tracker/state.enc at Hard Rock, with the real price/stake where known.
  C. RECONSTRUCTED SIGNALS - hrscan.json sightings that passed the flag but have no push evidence: UNVERIFIED.
Plus a CLV de-duplication check of the Hard Rock rows in clv/state.enc. Identical game/line/price is NOT treated as
proof of a duplicate wager: rows are collapsed only on an identical row id; same-key/different-id groups are shown
as UNPROVEN and bounded (as-is / distinct ids / distinct game-bet-price keys), never silently removed.
Stakes are UNVERIFIED where the tracker only assumes one. Dollars by private email; the log prints counts only.
"""
import json
import math
import re

import hr_manual_pull as hm

PUSH_PROVEN = ("wake forest", "indiana")          # Peter, Nov 10: the only documented phone pushes


def is_hr(b):
    return hm.is_hr(b)


def sd_se(xs):
    n = len(xs)
    if n < 2:
        return None, None
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return sd, sd / math.sqrt(n)


def clv_line(label, xs):
    n = len(xs)
    if not n:
        return f"  {label}: n 0"
    m = sum(xs) / n
    sd, se = sd_se(xs)
    beat = sum(1 for x in xs if x > 0)
    if se is None:
        return f"  {label}: n {n}, mean {m*100:+.2f}%, beat close {beat}/{n} (no spread at n<2)"
    return (f"  {label}: n {n}, mean {m*100:+.2f}%, sd {sd*100:.1f}%, SE {se*100:.1f}%, "
            f"95% range {(m-1.96*se)*100:+.1f}% to {(m+1.96*se)*100:+.1f}%, beat close {beat}/{n}")


def scheme(k):
    k = str(k)
    return k.split("|")[0] if "|" in k else ("sha1" if re.fullmatch(r"[0-9a-f]{40}", k) else "other")


def dedupe_section(cs):
    L = ["", "=" * 74, "CLV DE-DUPLICATION CHECK (Hard Rock rows in the CLV ledger state)", "=" * 74]
    rows = []
    for k, r in (cs.get("bets") or {}).items():
        s = r.get("snap") or {}
        if r.get("clv") is None or r.get("fixture_doubt") or not is_hr(s):
            continue
        rows.append((k, r, s))
    L.append(f"scored Hard Rock rows (ledger's own filter: scored, not held out): {len(rows)}")
    L.append("id schemes: " + str(dict(__import__("collections").Counter(scheme(k) for k, _, _ in rows))))
    L.append("NOTE: the tracker rows carry no Hard Rock bet ID, so a true bet-ID match is not possible on this data.")
    L.append("Rows are collapsed only on an identical row id. Everything else stays separate and is labelled.")
    L.append("")
    grp = {}
    for k, r, s in rows:
        grp.setdefault((s.get("game"), s.get("bet"), r.get("eff_am") or s.get("price")), []).append((k, r, s))
    for key, g in sorted(grp.items(), key=lambda kv: -len(kv[1])):
        tag = "single" if len(g) == 1 else ("SAME-ID" if len({k for k, _, _ in g}) == 1 else "UNPROVEN (distinct ids)")
        L.append(f"{tag} x{len(g)} | {str(key[0])[:38]} | {key[1]} @ {key[2]}")
        if len(g) > 1:
            for k, r, s in g:
                L.append(f"     id {str(k)[:14]}.. [{scheme(k)}] source {s.get('source')} | placed {s.get('placed')} | "
                         f"first_seen {s.get('first_seen')} | stake {s.get('stake')} | clv {r.get('clv')}")
    asis = [r["clv"] for _, r, _ in rows]
    by_id = {}
    for k, r, _ in rows:
        by_id.setdefault(k, r["clv"])
    by_key = {key: g[0][1]["clv"] for key, g in grp.items()}
    L += ["", "HARD ROCK CLV, three bounds (none is 'the' answer until the repeats are resolved):",
          clv_line("as-is in ledger        ", asis),
          clv_line("distinct row id        ", list(by_id.values())),
          clv_line("distinct game|bet|price (LOWER bound on n; assumes every repeat is a duplicate)", list(by_key.values()))]
    return L


def build_ledger(R, hr, alerts):
    L = ["", "=" * 74, "HR PHONE-ALERT LEDGER - three groups, never summed", "=" * 74]
    # A. documented pushes
    L += ["", "A. ACTUAL PHONE PUSHES (documented: Wake Forest, Indiana only)"]
    sights = [x for x in hr.get("sightings") or [] if x.get("flag")]
    for x in sights:
        if not any(w in str(x.get("side", "")).lower() for w in PUSH_PROVEN):
            continue
        L.append(f"  {x.get('lg')} {x.get('side')} {x.get('pt'):+g} | offered HR {x.get('hr'):+d} at {x.get('utc')} "
                 f"(lead {x.get('lead')} min) | Pinnacle {x.get('pin'):+d}/{x.get('pin_other'):+d}, fair {x.get('fair_am'):+d}, "
                 f"EV {x.get('evp')}% | close line {((x.get('close') or {}).get('pt'))} price {((x.get('close') or {}).get('pr'))} "
                 f"({((x.get('close') or {}).get('lead'))} min pre-start) | result {(x.get('res') or {}).get('r')}")
        match = [b for b in R if is_hr(b) and str(x.get("side", "")).split()[0].lower() in str(b.get("bet", "")).lower()
                 and str(b.get("game", "")).lower().find(str(x.get("side", "")).split()[0].lower()) >= 0]
        if match:
            for b in match:
                pr, from_text = hm.price_of(b)
                L.append(f"     matched tracker wager: bet price {pr} (text-parsed {from_text}) stake {b.get('stake')} "
                         f"result {b.get('result')} -> bet price vs offered price {'' if pr is None else pr - x.get('hr')}")
        else:
            L.append("     no matched manual wager in the tracker: bet price/stake NOT RECORDED. Not assumed.")
    # B. manual wagers
    L += ["", "B. ACTUAL MANUAL WAGERS at Hard Rock (every tracker row; none labelled a push unless in A)"]
    hrs = [b for b in R if is_hr(b)]
    for b in sorted(hrs, key=lambda b: str(b.get("placed") or b.get("first_seen") or "")):
        pr, from_text = hm.price_of(b)
        est = bool(b.get("est_stake") or b.get("stake_est") or "est" in str(b.get("source", "")).lower())
        L.append(f"  {str(b.get('placed') or b.get('first_seen') or '?')[:16]} | {b.get('league')} | {b.get('game')} | {b.get('bet')} | "
                 f"price {pr} | stake {b.get('stake')}{'  UNVERIFIED (estimate)' if est else ''} | result {b.get('result')} | "
                 f"source {b.get('source')}")
    L.append(f"  rows: {len(hrs)}  (estimated-stake rows are UNVERIFIED and must not be read as confirmed stakes)")
    # C. reconstructed
    L += ["", "C. RECONSTRUCTED SIGNALS (scanner sightings that passed the flag; NO push evidence: UNVERIFIED)"]
    for x in sights:
        if any(w in str(x.get("side", "")).lower() for w in PUSH_PROVEN):
            continue
        L.append(f"  UNVERIFIED {x.get('lg')} {x.get('side')} {x.get('pt'):+g} | HR {x.get('hr'):+d} Pin {x.get('pin'):+d} EV {x.get('evp')}% | {x.get('utc')}")
    if not any(not any(w in str(x.get("side", "")).lower() for w in PUSH_PROVEN) for x in sights):
        L.append("  none in hrscan.json sightings")
    L += ["", "  Scanner log only; the alerts.json HR rows are 'Street Value at HR' / 'HR Edge' bets, labelled by source, not pushes.",
          "  Pelicans (HR Edge): hand-placed, bot-skipped. UCLA -32.5: flag status unverified. Both stay UNVERIFIED as phone alerts."]
    return L


def main():
    import executor as ex
    import tracker_build as tb
    try:
        st = tb.dec(json.load(open(hm.STATE)))
        bets = (st or {}).get("bets")
        R = list(bets.values()) if isinstance(bets, dict) else (bets or [])
        cs = tb.dec(json.load(open("clv/state.enc"))) or {}
        hr = json.load(open("hrscan.json"))
        al = json.load(open("alerts.json"))
    except Exception as e:
        ex.send("Bets HR PHONE LEDGER (failed)", f"could not read inputs: {type(e).__name__}: {str(e)[:200]}")
        print(f"hr phone ledger: inputs unreadable ({type(e).__name__})")
        return
    L = ["HR PHONE-ALERT LEDGER - read-only. No rule, notification or execution change.", ""]
    L += dedupe_section(cs)
    L += build_ledger(R, hr, al)
    ex.send("Bets HR PHONE LEDGER (read-only)", "\n".join(L))
    print(f"hr phone ledger: tracker rows {len(R)}, clv rows {len((cs or {}).get('bets') or {})}, "
          f"flagged sightings {sum(1 for x in hr.get('sightings') or [] if x.get('flag'))}")   # counts only


if __name__ == "__main__":
    main()

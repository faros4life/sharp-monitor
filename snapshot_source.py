"""SECOND-PRIORITY closing evidence: Pinnacle T-12 snapshots (Muse), used only where the certified
ledger has none. Peter, Nov 20.

SOURCE PRIORITY, never blurred:
  1. certified Pinnacle closing quote from the CLV ledger -> V1 CLV
  2. a verified snapshot here                             -> PROVISIONAL CLV, labelled T-12 SNAPSHOT
  3. neither                                              -> unavailable, with the reason

A snapshot is NOT a close. It is captured minutes before tip, and markets move late, so nothing
derived from one is ever written to V1 or presented as certified.

ORIENTATION IS MANDATORY FOR A PRICE. A two-price pair with no statement of which side is ours
cannot yield CLV: taking the wrong one flips the sign (Toledo Nov 19 is -1.27% or +4.94% on that
choice alone). So a record must carry price_our AND price_other to be priced. A record with only an
unordered pair still gives LINE MOVEMENT, which needs no orientation, and says why no CLV followed.

Records live in snapshots/*.json as a list of objects:
  {"day":"2026-11-19","league":"NCAAB","game":"Robert Morris vs Toledo Rockets",
   "market":"spread","side":"Toledo Rockets","line":-7.5,
   "price_our":-116,"price_other":-101,        # explicit orientation -> priceable
   "price_pair":[-101,-116],                   # unordered -> movement only
   "captured":"2026-11-19T23:48:00Z","t_minus_min":12,"source":"muse"}
"""
import glob
import json
import os

import clv_ledger as cl          # fair_from_main and am_to_dec: one implementation, not a copy
import tracker_build as tb

DIR = "snapshots"
LABEL = "Pinnacle T-12 SNAPSHOT (provisional, not a certified close)"


def load(directory=DIR):
    """Every snapshot record on disk. A malformed file is skipped and counted, never guessed at."""
    out, bad = [], 0
    for p in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            d = json.load(open(p))
        except Exception:
            bad += 1
            continue
        for r in (d if isinstance(d, list) else [d]):
            if isinstance(r, dict):
                r.setdefault("file", os.path.basename(p))
                out.append(r)
    return out, bad


def market_of(bet_text):
    """'spread' | 'total' | None, from the bet's own parsed form - the parser the ledger uses."""
    pz = cl.parsed({"bet": bet_text})
    if not pz:
        return None
    return {"spread": "spread", "total": "total"}.get(pz[0])


def matches(snap, b, day):
    """Does this snapshot describe THIS bet? Verified on league, ET day, market and side only.

    Never matched on game-name similarity alone: that is how 'Michigan' put a Senate market on a
    football game. A side must share a real token with the bet text, or for a total the same
    Over/Under direction.
    """
    if str(snap.get("day")) != str(day):
        return False
    if (snap.get("league") or "").upper() != (b.get("league") or "").upper():
        return False
    mk = market_of(b.get("bet"))
    if not mk or (snap.get("market") or "").lower() != mk:
        return False
    pz = cl.parsed(b)
    if not pz:
        return False
    # THE GAME MUST MATCH. Without this, a total's side is only OVER/UNDER, so every NCAAB under
    # on a date matched every NCAAB total snapshot - Ohio State's 155.5 was attached to Oregon's
    # 160.5 bet and to a Kalshi 139.5 bet, producing a CLV from another game's quote. Two shared
    # tokens is the same bar fixture_match uses; one shared word is how "Michigan" put a Senate
    # market on a football game.
    if len(tb.toks(str(snap.get("game"))) & tb.toks(str(b.get("game")))) < 2:
        return False
    if mk == "total":
        want = (snap.get("side") or "").upper()
        if want not in ("OVER", "UNDER") or want != str(pz[1]).upper():
            return False
        # ...and the snapshot must be about a comparable number, not any total on the slate.
        try:
            return abs(float(snap.get("line")) - float(pz[2])) <= 6.0
        except Exception:
            return False
    return bool(tb.toks(str(snap.get("side"))) & tb.toks(str(pz[1])))


def rank(snap):
    """Sort key: a quote AT OUR OWN LINE beats a main-line quote, and fresher beats older.

    An alt_our_line record needs no model conversion at all, so it is strictly better evidence
    than a main-line snapshot that has to be walked across numbers.
    """
    same_line = 0 if str(snap.get("line_type")) == "alt_our_line" else 1
    try:
        age = float(snap.get("t_minus_min"))
    except Exception:
        age = 999.0
    return (same_line, age)


def movement(snap, b):
    """Points our number is better (+) or worse (-) than the snapshot's line. No orientation needed."""
    pz = cl.parsed(b)
    if not pz or pz[2] is None or snap.get("line") is None:
        return None
    ours, theirs = float(pz[2]), float(snap["line"])
    if market_of(b.get("bet")) == "total":
        d = ours - theirs
        return round(d if str(pz[1]).upper() == "UNDER" else -d, 2)
    return round(abs(theirs) - abs(ours), 2)      # a smaller handicap to cover is better


def provisional_clv(snap, b):
    """(clv, note) from a snapshot, or (None, why not). Never a certified figure.

    Requires explicit orientation and a conversion the REGISTERED tables support. Both refusals are
    returned as text so the report can print the reason instead of a number.
    """
    if snap.get("price_our") is None or snap.get("price_other") is None:
        return None, "orientation not stated: cannot tell which price is our side"
    pz = cl.parsed(b)
    if not pz:
        return None, "bet text not parsed"
    try:
        a, o = cl.am_to_dec(float(snap["price_our"])), cl.am_to_dec(float(snap["price_other"]))
        p_snap = cl.novig_p(a, o)
    except Exception:
        return None, "snapshot prices unreadable"
    d = cl.eff_dec(b)
    if not d:
        return None, "no price on our fill"
    mv = movement(snap, b)
    if mv is None:
        return None, "no comparable line"
    mk = market_of(b.get("bet"))
    ours = float(pz[2])
    line = float(snap["line"])
    if mk == "total":
        sl, wl = line, ours
    else:
        sl, wl = (line, ours) if ours < 0 else (abs(line), abs(ours))
        if ours < 0:
            sl, wl = -abs(line), -abs(ours)
    p, why, src = cl.fair_from_main(p_snap, sl, wl, mv > 0, b.get("league"), "spr" if mk == "spread" else "tot")
    if p is None:
        return None, f"no supported conversion: {why}"
    return round(p * d - 1, 4), f"{LABEL}; rows used {', '.join(src) or 'none (same line)'}"

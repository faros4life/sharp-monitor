import json
import clv_ledger as cl, tracker_build as tb
st = tb.dec(json.load(open(cl.STATE)))
print("fx_last", st.get("fx_last"))
for k, r in st["bets"].items():
    s = r["snap"]
    if (s.get("first_seen") or r.get("first_seen") or "") < "2026-11-12T22" and "2026-11-12" not in json.dumps(s): continue
    g = (s.get("game") or "").lower()
    if (s.get("game_start") or "")[:10] != "2026-11-13" and (s.get("game_start") or "")[:10] != "2026-11-12": continue
    if any(x in g for x in ("louisiana", "minnesota", "phoenix", "philadelphia")):
        print("ROW", s.get("book"), s.get("bet"), s.get("source"), "|", r.get("clv"), r.get("close_p"), r.get("eff_am"), r.get("close_am"), "|", r.get("why"), r.get("tries"), r.get("done"), "| fixture", r.get("fixture"))

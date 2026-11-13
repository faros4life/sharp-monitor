import json
import clv_ledger as cl, tracker_build as tb
st = tb.dec(json.load(open(cl.STATE)))
print("fx_last", st.get("fx_last"))
for fid, f in (st.get("fixtures") or {}).items():
    t = (f.get("p1","")+" "+f.get("p2","")).lower()
    if (f.get("lg")=="NCAAF" and "louisiana" in t) or (f.get("lg")=="NBA" and (("dallas" in t and "minnesota" in t) or ("charlotte" in t and "phoenix" in t))):
        print("FX", fid, f.get("lg"), f.get("start"), "|", f.get("p1"), "|", f.get("p2"))
print("NBA fixtures", sum(1 for f in st["fixtures"].values() if f.get("lg")=="NBA"), "latest", max((f.get("start") or "") for f in st["fixtures"].values() if f.get("lg")=="NBA"))

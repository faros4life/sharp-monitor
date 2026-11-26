"""toa.store_guard: a certify run without The Odds API store must not overwrite closes certified from it."""
import gzip, json, os, tempfile
import toa

fails = 0
def ok(c, m):
    global fails
    print(("  ok   " if c else "  FAIL ") + m); fails += 0 if c else 1

d = tempfile.mkdtemp()
p = os.path.join(d, "cert.json")
json.dump({"certified": {"a": {"src": "theoddsapi"}, "b": {"src": "oddspapi"}}}, open(p, "w"))
toa.DIR = os.path.join(d, "toa_hist")
ok(toa.store_guard(p) and "drop" in toa.store_guard(p), "store missing + stored closes in the file -> refused")
os.makedirs(os.path.join(toa.DIR, "basketball_nba"))
with gzip.open(os.path.join(toa.DIR, "basketball_nba", "f_x.json.gz"), "wt") as fh:
    fh.write("{}")
ok(toa.store_guard(p) is None, "store present -> allowed")
json.dump({"certified": {"b": {"src": "oddspapi"}}}, open(p, "w"))
toa.DIR = os.path.join(d, "none")
ok(toa.store_guard(p) is None, "no stored closes in the file -> allowed even without the store")
ok(toa.store_guard(os.path.join(d, "missing.json")) is None, "no existing file -> allowed")
print("FAILED" if fails else "all passed"); raise SystemExit(1 if fails else 0)

"""Nov 12: the audit is read-only, counts-only and imports no execution code."""
import ast, json, os, sys, types
os.environ["AUDIT_PREFIXES"] = "Bets LIVE:|Bets dry run:"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import line_value_audit as au  # noqa: E402
import line_value_replay as rp  # noqa: E402
OK, BAD = [], []
def ck(n, c, d=""): (OK if c else BAD).append(n + (f"  [{d}]" if d and not c else ""))
src = open(au.__file__).read(); tree = ast.parse(src)
mods = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)} | {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
ck("imports no execution, registry, mail-sending or network-write code", not (mods & {"executor", "registry", "smtplib", "requests", "px_live", "book_live"}), str(mods))
ck("opens the mailbox readonly and fetches with PEEK", "readonly=True" in src and "BODY.PEEK" in src and "uid(\"STORE\"" not in src)
ck("never prints row content", "print(" in src and "ledger_row" not in src and "json.dumps" not in src)
wf = open(os.path.join(os.path.dirname(au.__file__), ".github/workflows/line-value-audit.yml")).read()
ck("workflow is dispatch-only, contents:read, no executor, no send", "workflow_dispatch" in wf and "schedule" not in wf and "contents: read" in wf
   and "executor.py" not in wf and "import executor" not in wf and "run: python3 line_value_audit.py" in wf and "EMAIL_TO" not in wf and "REGISTRY_TOKEN" not in wf and "PMUS" not in wf)
# fake IMAP: only a real prefix counts; a substring-subject decoy is dropped
def mail(subj, body):
    return ("Subject: %s\r\nContent-Type: text/plain\r\n\r\n%s" % (subj, body)).encode()
row = {"key": "NBA|A @ B|total|UNDER", "alert_utc": "t", "alert_line": 214.5, "venues_considered": [{"book": "novig", "line": 214.5, "after_fee": -111}]}
led = "LEDGER (machine-readable, rows)\n" + json.dumps([row])
boxes = {"Bets LIVE:": {b"1": mail("Bets LIVE: 0 placed", led), b"2": mail("Re: Bets LIVE: decoy", led)}, "Bets dry run:": {b"3": mail("Bets dry run: x", led)}}
class M:
    def login(s, *a): pass
    def select(s, name, readonly=False): s.ro = readonly; assert readonly
    def uid(s, cmd, *a):
        if cmd == "SEARCH":
            pre = a[2].strip('"'); return "OK", [b" ".join(boxes[pre])]
        return "OK", [(None, boxes[[p for p in boxes if a[0] in boxes[p]][0]][a[0]])]
    def logout(s): pass
au.imaplib.IMAP4_SSL = lambda host: M()
os.environ.update(GMAIL_ADDRESS="x", GMAIL_APP_PASSWORD="y")
texts, seen, skipped = au.fetch_texts(7)
ck("decoy subject dropped, two real emails kept", seen == 2 and len(texts) == 2 and skipped == 0, f"{seen}")
rep = rp.report(texts)
out = rp.render(rep, detail=False)
ck("report counts the rows", rep["ledger_rows_examined"] == 2 and rep["unique_plays_examined"] == 1)
ck("public form has no game, line or price", "214.5" not in out and "novig" not in out and "Charlotte" not in out)
print(f"{len(OK)} pass, {len(BAD)} fail")
for b in BAD: print("FAIL", b)
sys.exit(1 if BAD else 0)

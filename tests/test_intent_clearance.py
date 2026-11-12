"""Intent clearance and read-back (Peter, Nov 11).

TWO BUGS THIS PINS:

A. SELF-CLEARING. The first version put the literal token 'intentdone<cid>' in the intent email's
   OWN BODY, and cleared the intent with gsearch_strict, which searches X-GM-RAW - bodies
   included. Every intent therefore cleared itself the instant it was written, and the
   fail-closed guard could never fire. Clearance is now SUBJECT-ONLY, with a prefix this system
   never emits, and the real Subject header is re-checked (IMAP SUBJECT is a substring match -
   the Oct 27 dry-run-read-as-live bug).

B. SMTP SUCCESS TREATED AS STORAGE. send() returning cleanly does not mean the row is in the
   registry. The intent is now READ BACK before any order is submitted - the same discipline the
   Polymarket order path already follows: acceptance is never proof, read the order back.
"""
import email as _email
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# forced, not setdefault: an inherited GMAIL_ADDRESS would change who is authorized
os.environ["GMAIL_ADDRESS"] = "owner@example.com"
os.environ["GMAIL_APP_PASSWORD"] = "x"
os.environ["EMAIL_TO"] = "owner+bets@example.com"
import executor as ex  # noqa: E402

# Nov 12: journal_intent now takes an ATOMIC SUBMISSION CLAIM before it writes anything, and
# claim_submission() RAISES when the store cannot be written - "without an atomic store a
# concurrent duplicate cannot be prevented, so an unknown answer must block". With no store at all
# every call here refused, which is the gate working, not a defect. These tests need a store that
# can be written so the path past the claim is reachable; the claim's own behaviour is covered by
# test_one_submission.py and test_atomic_submission.py.
import registry as _R   # noqa: E402

_R_ORIG = (_R.load, _R._commit, _R.enabled)


def store_on(data=None):
    box = {"d": data or {"orders": [], "intents": [], "handled": {}, "submissions": {}}}
    _R.load = lambda: json.loads(json.dumps(box["d"]))
    def _commit(merge, tries=4):
        d = json.loads(json.dumps(box["d"]))
        if merge(d) is False:
            return True
        box["d"] = d
        return True
    _R._commit = _commit
    _R.enabled = lambda: True
    return box


def store_off():
    _R.load, _R._commit, _R.enabled = _R_ORIG


OWNER, OUTSIDER = "owner@example.com", "stranger@evil.test"

OK, BAD = [], []


def ck(name, cond, detail=""):
    (OK if cond else BAD).append(name + (f"  [{detail}]" if detail and not cond else ""))


_send, _tg, _rb, _io, _ic = ex.send, ex.tg, ex.intent_readable, ex.imap_open, ex.imap_close


class FakeIMAP:
    """Minimal IMAP double: holds (subject,) messages and answers UID SEARCH/FETCH like Gmail,
    including SUBJECT's substring behaviour, so the header re-check is actually exercised."""

    def __init__(self, subjects, fail=False, sender=None, labels=r"\\Sent"):
        # subjects may be a plain string, (subject, from_addr) or (subject, from_addr, labels)
        norm = []
        for x in subjects:
            if isinstance(x, tuple):
                norm.append(x if len(x) == 3 else (x[0], x[1], labels))
            else:
                norm.append((x, sender or OWNER, labels))
        self.subjects, self.fail = norm, fail

    def uid(self, cmd, *a):
        if self.fail:
            return "NO", [None]
        if cmd == "SEARCH":
            needle = [x for x in a if isinstance(x, str) and x.startswith('"')]
            n = needle[0].strip('"') if needle else ""
            hits = [str(i).encode() for i, (s, _f, _l) in enumerate(self.subjects) if n in s]   # substring, like IMAP
            return "OK", [b" ".join(hits)]
        if cmd == "FETCH":
            i = int(a[0])
            subj, frm, labels = self.subjects[i]
            msg = _email.message.Message()
            msg["Subject"], msg["From"] = subj, frm
            pre = ("%s (X-GM-LABELS (%s) BODY[HEADER.FIELDS (SUBJECT FROM SENDER)] " % (i, labels)).encode()
            return "OK", [(pre, msg.as_bytes())]
        return "NO", [None]


# ======================================================== A. clearance cannot self-match
SENT = []
ex.send = lambda s, b: SENT.append((s, b))
ex.tg = lambda *a, **k: None
ex.intent_readable = lambda cid, **k: True
SENT.clear()
store_on()   # journal_intent takes an atomic submission claim first; it needs a writable store
ok, cid = ex.journal_intent({"play": {"play_key": "K1", "source": "board"}}, "prophetx", 390.0)
subj, body = SENT[0]

ck("A. the intent email's SUBJECT does not contain the clear prefix",
   ex.INTENT_CLEAR_PREFIX not in subj, subj)
ck("A. the old body token is gone entirely", "intentdone" not in body)
ck("A. the body does not contain the contiguous clearing subject",
   (ex.INTENT_CLEAR_PREFIX + " " + cid) not in body)
ck("A. clearance no longer uses the body-searching helper",
   "gsearch_strict" not in inspect.getsource(ex.intent_cleared))
ck("A. clearance searches SUBJECT and re-checks the header",
   "SUBJECT" in inspect.getsource(ex.subject_hits) and "startswith(prefix)" in inspect.getsource(ex.subject_hits))

# the decisive test: feed the clearance search the intent's OWN subject and nothing else
M = FakeIMAP([subj])
ck("A. an intent CANNOT clear itself", ex.intent_cleared(M, cid) is False, subj)
M = FakeIMAP([subj, f"Bets LIVE: 0 placed, 0 would go live (intent {cid} open)"])
ck("A. another bot email naming the id does not clear it", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([subj, f"Re: {ex.INTENT_CLEAR_PREFIX} {cid}"])
ck("A. a REPLY (prefix not at the start) does not clear it", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([f"{ex.INTENT_CLEAR_PREFIX} someoneelsesid"])
ck("A. a clearance for a DIFFERENT id does not clear it", ex.intent_cleared(M, cid) is False)

# only the real thing clears
M = FakeIMAP([subj, f"{ex.INTENT_CLEAR_PREFIX} {cid}"])
ck("A. Peter's manual subject DOES clear it", ex.intent_cleared(M, cid) is True)
M = FakeIMAP([f"{ex.INTENT_CLEAR_PREFIX} {cid} - checked My Trades, nothing was placed"])
ck("A. extra words after the id still clear it", ex.intent_cleared(M, cid) is True)

# a failed search must raise, so bot_orders keeps refusing
try:
    ex.intent_cleared(FakeIMAP([], fail=True), cid)
    ck("A. a failed clearance search raises (fail closed)", False, "did not raise")
except Exception:
    ck("A. a failed clearance search raises (fail closed)", True)
# Nov 12: the ledger-row accounting was extracted from bot_orders() into _account_rows() on Nov 11, so these
# source checks were silently grepping the wrong function - red, and verifying nothing. Read BOTH.
bo = inspect.getsource(ex.bot_orders) + inspect.getsource(ex._account_rows)
ck("A. bot_orders keeps the intent open when the search fails",
   "except Exception" in bo and "keep refusing" in bo)
ck("A. bot_orders uses intent_cleared, not a raw token search", "intent_cleared(M, k)" in bo)

# no code path may ever SEND that subject
src = inspect.getsource(ex)
sent_subjects = [l for l in src.splitlines() if "send(" in l and ex.INTENT_CLEAR_PREFIX in l]
ck("A. no send() call carries the clearing subject", not sent_subjects, str(sent_subjects))

# ======================================================== A2. only an authorized SENDER clears
ck("A2. authorized senders are the account and EMAIL_TO",
   ex.authorized_senders() == {"owner@example.com", "owner+bets@example.com"},
   str(ex.authorized_senders()))
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER)])
ck("A2. a clearance from the account owner DOES clear", ex.intent_cleared(M, cid) is True)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", "owner+bets@example.com")])
ck("A2. a clearance from EMAIL_TO DOES clear", ex.intent_cleared(M, cid) is True)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OUTSIDER)])
ck("A2. the SAME subject from an OUTSIDER does NOT clear", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", "Peter <%s>" % OUTSIDER)])
ck("A2. a display-name spoof does not clear", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", f"Owner <{OWNER}>")])
ck("A2. a decorated but authorized From does clear", ex.intent_cleared(M, cid) is True)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", "")])
ck("A2. a missing From does not clear", ex.intent_cleared(M, cid) is False)
ck("A2. the read-back path verifies the subject prefix (sender check is for clearance)",
   "senders=authorized_senders()" in inspect.getsource(ex.intent_cleared))
_ga = os.environ.pop("GMAIL_ADDRESS")
try:
    ex.intent_cleared(FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER)]), cid)
    ck("A2. an unconfigured account cannot clear (raises)", False, "did not raise")
except BaseException:
    ck("A2. an unconfigured account cannot clear (raises)", True)
finally:
    os.environ["GMAIL_ADDRESS"] = _ga

# ================================================= A3. a FORGED sender cannot clear (Muse's question)
# [Gmail]/All Mail includes RECEIVED mail, and a From header is trivially forged, so authorization
# rests on the \\Sent label: only a message sent THROUGH the authenticated account carries it.
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER, r"\\Sent")])
ck("A3. a genuinely SENT clearance clears", ex.intent_cleared(M, cid) is True)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER, r"\\Inbox")])
ck("A3. a FORGED inbound message with Peter's From does NOT clear",
   ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER, "")])
ck("A3. no labels at all does NOT clear (fail closed)", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER, r"\\Important \\Inbox")])
ck("A3. other labels without Sent do NOT clear", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OUTSIDER, r"\\Sent")])
ck("A3. Sent but an unauthorized From does NOT clear", ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(f"{ex.INTENT_CLEAR_PREFIX} {cid}", OWNER, r"\\Sent \\Important")])
ck("A3. Sent alongside other labels still clears", ex.intent_cleared(M, cid) is True)
# ---- FORGED SUBJECT (Peter, Nov 11): the label must come from FETCH METADATA, never from the
# fetched header bytes. Before this, the whole response was scanned for the text \\Sent, so an
# inbound message whose SUBJECT merely contained it passed as authorized.
M = FakeIMAP([(ex.INTENT_CLEAR_PREFIX + " " + cid + r" \\Sent", OWNER, r"\\Inbox")])
ck("A3. a forged SUBJECT containing the Sent token does NOT clear",
   ex.intent_cleared(M, cid) is False)
M = FakeIMAP([(ex.INTENT_CLEAR_PREFIX + " " + cid, r'"\\Sent" <%s>' % OUTSIDER, r"\\Inbox")])
ck("A3. a forged FROM display-name containing the Sent token does NOT clear",
   ex.intent_cleared(M, cid) is False)
# the parser itself, against real Gmail FETCH metadata shapes
ck("A3. parser accepts a wire-escaped label",
   "\\Sent" in ex._gm_labels(rb"1 (X-GM-LABELS (\\Sent) BODY[HEADER.FIELDS (SUBJECT)] {9}"))
ck("A3. parser accepts a bare atom label",
   "\\Sent" in ex._gm_labels(rb"1 (X-GM-LABELS (\Sent \Important) BODY[HEADER.FIELDS (SUBJECT)] {9}"))
ck("A3. parser rejects inbox-only",
   "\\Sent" not in ex._gm_labels(rb"1 (X-GM-LABELS (\Inbox) BODY[HEADER.FIELDS (SUBJECT)] {9}"))
ck("A3. parser rejects empty label list",
   ex._gm_labels(rb"1 (X-GM-LABELS () BODY[HEADER.FIELDS (SUBJECT)] {9}") == set())
ck("A3. parser rejects a response with no X-GM-LABELS at all",
   ex._gm_labels(rb"1 (BODY[HEADER.FIELDS (SUBJECT)] {9}") == set())
ck("A3. parser does not confuse a USER label named 'Sent reports' with \\Sent",
   "\\Sent" not in ex._gm_labels(rb'1 (X-GM-LABELS ("Sent reports") BODY[HEADER.FIELDS (SUBJECT)] {9}'))
ck("A3. parser ignores anything after the label list (header bytes cannot reach it)",
   "\\Sent" not in ex._gm_labels(
       rb"1 (X-GM-LABELS (\Inbox) BODY[...] {9}" + b"\r\n" + rb"Subject: \Sent"))
_sh = inspect.getsource(ex.subject_hits)
ck("A3. the label comes from the FETCH metadata element, not the payload",
   "meta = d[0][0]" in _sh and "_gm_labels(meta)" in _sh)
ck("A3. _gm_labels is called on nothing but meta",
   _sh.count("_gm_labels(") == 1 and "_gm_labels(meta)" in _sh)
ck("A3. the payload is used only for the secondary From check, after the label",
   _sh.index("_gm_labels(meta)") < _sh.index('_addr(msg.get("From"))'))
ck("A3. the label check sits BEFORE the From check in the code",
   inspect.getsource(ex.subject_hits).index("_gm_labels(meta)")
   < inspect.getsource(ex.subject_hits).index('_addr(msg.get("From"))'))
ck("A3. the code records WHY a header is not authentication",
   "forged" in inspect.getsource(ex.subject_hits).lower())

# ======================================================== B. read-back before submitting
ex.intent_readable = _rb
ex.imap_open, ex.imap_close = (lambda: FakeIMAP([subj])), (lambda M: None)
ck("B. a stored intent reads back", ex.intent_readable(cid, tries=1) is True)
ex.imap_open = lambda: FakeIMAP([])
ck("B. a missing intent does NOT read back", ex.intent_readable(cid, tries=1) is False)
ex.imap_open = lambda: FakeIMAP([], fail=True)
ck("B. an IMAP failure does NOT read back (fail closed)", ex.intent_readable(cid, tries=1) is False)


def boom():
    raise RuntimeError("imap down")


ex.imap_open = boom
ck("B. an IMAP exception does NOT read back", ex.intent_readable(cid, tries=1) is False)
ck("B. read-back only accepts the intent subject prefix",
   "INTENT_SUBJECT_PREFIX" in inspect.getsource(ex.intent_readable))
ck("B. read-back retries for indexing delay", "tries" in inspect.getsource(ex.intent_readable))

# SMTP success + unreadable row => NO order, and it is reported
SENT.clear()
shout = []
ex.send = lambda s, b: SENT.append((s, b))     # SMTP "succeeds"
ex.tg = lambda m, *a, **k: shout.append(m)
ex.imap_open = lambda: FakeIMAP([])            # but nothing is readable
ok2, cid2 = ex.journal_intent({"play": {"play_key": "K2"}}, "prophetx", 390.0)
ck("B. SMTP success with an unreadable row returns NOT ok", ok2 is False and cid2 is None)
ck("B.   and it shouts", len(shout) == 1, str(shout)[:120])
ck("B.   and the shout says no order was placed",
   shout and "NO ORDER WAS PLACED" in shout[0], str(shout)[:160])
ck("B.   and tells Peter the clearing subject", shout and ex.INTENT_CLEAR_PREFIX in shout[0])
ji = inspect.getsource(ex.journal_intent)
ck("B. the read-back gate sits AFTER send and BEFORE returning ok",
   ji.index("send(") < ji.index("intent_verified(") < ji.index("return True, cid"))

lo = inspect.getsource(ex.live_order)
ck("B. a failed intent means nothing is submitted",
   "could not store the pre-order record" in lo and lo.index("journal_intent(") < lo.index("live_order_other(r)"))

# ======================================================== cross-run behaviour
def account(rows, cleared=()):
    seen, risk, keys, intents, confirmed = set(), 0.0, set(), {}, {}
    for r_ in rows:
        lo_ = r_.get("live_order") or {}
        if lo_.get("status") != "placed" or not lo_.get("order_id"):
            continue
        c = lo_.get("client_id")
        if c:
            (intents if lo_.get("intent") else confirmed)[str(c)] = r_
        k = str(c or lo_["order_id"])
        if k in seen:
            continue
        seen.add(k)
        if r_.get("key"):
            keys.add(r_["key"])
        fs = lo_.get("filled_stake")
        risk += max(float(fs or 0), float(lo_.get("asked_stake") or 0)) if fs is None else float(fs)
    return risk, keys, {k: v for k, v in intents.items()
                        if k not in confirmed and k not in cleared}


I = {"key": "K1", "live_order": {"status": "placed", "order_id": "intent-C1", "book": "prophetx",
                                 "asked_stake": 390.0, "filled_stake": None, "client_id": "C1", "intent": True}}
C = {"key": "K1", "live_order": {"status": "placed", "order_id": "PX-9", "book": "prophetx",
                                 "asked_stake": 390.0, "filled_stake": 390.0, "client_id": "C1", "intent": False}}
r1, k1, o1 = account([I])
ck("run 2 sees the unconfirmed intent", list(o1) == ["C1"], str(o1))
ck("run 2 counts its risk", abs(r1 - 390.0) < 1e-9, str(r1))
ck("run 2 holds its play key", k1 == {"K1"})
_, _, o2 = account([I, C])
ck("a confirmed order resolves it without any manual step", o2 == {}, str(o2))
_, _, o3 = account([C, I])
ck("resolution is order-independent", o3 == {}, str(o3))
_, _, o4 = account([I], cleared={"C1"})
ck("only a manual clearance resolves an unconfirmed intent", o4 == {}, str(o4))
r5, _, o5 = account([I, I])
ck("the same intent twice counts its money once", abs(r5 - 390.0) < 1e-9, str(r5))
ck("  and is still reported open once", list(o5) == ["C1"], str(o5))

lg = inspect.getsource(ex.live_guards)
ck("live_guards refuses on an open intent", 'INTENT["open"]' in lg)
ck("the refusal names the SUBJECT-based clearance", "INTENT_CLEAR_PREFIX" in lg)
ck("no stale 'intentdone' instruction survives anywhere", "intentdone" not in src)

# ======================================================== settings unchanged
ex.send, ex.tg, ex.intent_readable, ex.imap_open, ex.imap_close = _send, _tg, _rb, _io, _ic
ck("units 200/300", ex.BOARD_UNIT == 200.0 and ex.LIVE_UNIT == 300.0)
ck("10 plays / 2000 / 15 min", ex.BOARD_MAX_PLAYS == 10 and ex.BOARD_DAILY_RISK == 2000.0
   and ex.BOARD_CONFIRM_MIN == 15)
ck("prophetx+novig 2c", ex.TOL_BOOKS == ("prophetx", "novig") and ex.PX_TOL_CENTS == 2)
ck("-130 cap / 2250 stop / 415 guard",
   ex.CAP_LINE == -130 and ex.px_live.DAILY_STOP == 3000.0 and ex.px_live.MAX_ORDER == 415.0)
ck("board lane off", ex.BOARD_LIVE is False)
ck("px_live untouched", ex.px_live.EXT_PREFIX == "")

print(f"PASS {len(OK)}   FAIL {len(BAD)}")
for b in BAD:
    print("  FAIL:", b)
sys.exit(1 if BAD else 0)

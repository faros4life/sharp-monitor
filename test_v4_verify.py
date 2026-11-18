#!/usr/bin/env python3
"""The sanitized verification block (Peter, 18 Nov). Counts and masked reasons only - no private figure may leak."""
import report_sections as rs

LANE = lambda r: r.get("lane")
ACC = {"lane": "BOARD V4", "board_fee_basis": True, "route": {"rule": "trigger venue first"},
       "board_v4": {"ok": True, "evidence": {"book": "novig", "size": 18869},
                    "strength": [{"confirming": True, "ratio": 3.58, "money": "RESTING"}]}}
REJ = {"lane": "BOARD V4", "board_fee_basis": False, "live_why_not": ["board lane not switched on (EXEC_BOARD_LIVE)"],
       "board_v4": {"ok": False, "why": "second book failed verification (novig: size 9440)", "evidence": None,
                    "strength": []}}


def t_reports_the_approved_fields():
    lines, s = rs.v4_verify([ACC, REJ], LANE)
    a = lines[0]
    for want in ("ACCEPT", "evidence yes", "venue novig", "18,869", "floor 10,000", "ratio 3.58x",
                 "money RESTING", "corrected after-fee", "route trigger venue first", "matches approved rule: YES"):
        assert want in a, (want, a)
    assert s == {"rows": 2, "with_evidence": 1, "accept": 1, "reject": 1, "rule_match": 2, "rule_mismatch": 0,
                 "basis_corrected": 1, "basis_raw": 1, "no_v4_field": 0}


def t_flags_a_decision_that_does_not_match_the_rule():
    bad = {"lane": "BOARD V4", "board_v4": {"ok": True, "evidence": {"book": "novig", "size": 4000}, "strength": []}}
    _l, s = rs.v4_verify([bad], LANE)
    assert s["rule_mismatch"] == 1 and s["rule_match"] == 0          # accepted below the $10k floor
    assert "matches approved rule: NO" in _l[0]
    missing = {"lane": "BOARD V4"}
    _l2, s2 = rs.v4_verify([missing], LANE)
    assert s2["no_v4_field"] == 1 and "no board_v4 field" in _l2[0]


def t_nothing_private_leaks():
    """Digits inside any reason text are masked, and no stake, balance, id or game name is printed."""
    nasty = {"lane": "BOARD V4", "board_v4": {"ok": False, "evidence": None, "strength": [],
             "why": "CONFLICT: opposite side of an earlier alert (Under 224.5, -113, $415 stake, order 7f3a91)"},
             "live_why_not": ["daily stop: $2,250 of $3,000 used on order ab77-9931"],
             "stake": 415.0, "balance": 12345.67, "order_id": "ab77-9931", "game": "Utah @ LA Clippers"}
    lines, _ = rs.v4_verify([nasty], LANE)
    g, _c = rs.gate_reasons([nasty], LANE)
    blob = "\n".join(lines + g)
    for secret in ("224.5", "113", "415", "12345", "ab77", "9931", "2,250", "3,000", "Utah", "Clippers"):
        assert secret not in blob, (secret, blob)
    assert "####" in blob or "#" in blob                              # masked, not dropped
    assert "CONFLICT" in blob and "daily stop" in blob                # the GATE is still identifiable


def t_only_board_rows():
    other = [{"lane": "R1", "board_v4": {"ok": True, "evidence": {"book": "x", "size": 99999}}},
             {"lane": "PHASE 1", "live_why_not": ["something"]}]
    assert rs.v4_verify(other, LANE)[1]["rows"] == 0
    assert rs.gate_reasons(other, LANE)[1] == {}
    assert rs.v4_verify([], LANE)[1]["rows"] == 0 and rs.v4_verify(None, LANE)[1]["rows"] == 0


def t_reporting_only():
    s = open("p2_audit.py").read()
    i = s.index("VERIFICATION BLOCK")
    blk = s[i:i + 1500]
    assert "print(" in blk and "send_" not in blk          # it prints; it never delivers or decides
    for name in ("EXEC_", "place_order", "submit", "refuse(", "live_order"):
        assert name not in blk, name
    assert "rs.v4_verify(rr" in s and "rs.gate_reasons(rr" in s
    # Telegram reporting untouched
    assert "def send_private" in s or "send_private(" in s


for f in (t_reports_the_approved_fields, t_flags_a_decision_that_does_not_match_the_rule, t_nothing_private_leaks,
          t_only_board_rows, t_reporting_only):
    f()
print("v4 verification tests: OK")

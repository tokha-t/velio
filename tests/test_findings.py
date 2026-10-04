from __future__ import annotations

from navigator import findings


def test_no_rule_reason_distinguishes_pending_and_state_prohibition():
    pending = [{"citation": "Mass. S.2983 (194th)", "base_status": "pending"}]
    assert "Pending: Mass. S.2983 (194th)." in findings._reason(pending, [])
    prohibition = [{"citation": "M.G.L. c. 40P, § 4", "key_value": "no rent cap — local rent control prohibited"}]
    assert "No in-force city rent-cap rule" in findings._reason([], prohibition)

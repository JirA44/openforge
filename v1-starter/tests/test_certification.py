import copy
import json
from pathlib import Path
from apps.api.certification import evaluate
from apps.api.models import CertificationRequest, StrategyStatus

ROOT = Path(__file__).resolve().parents[1]


def request_data():
    return json.loads((ROOT / "examples" / "certification-pass.json").read_text())


def test_complete_evidence_becomes_ready_for_live():
    result = evaluate(CertificationRequest.model_validate(request_data()))
    assert result.decision == "PASS"
    assert result.ready_for_live is True
    assert result.status == StrategyStatus.READY_FOR_LIVE
    assert result.blocking_reasons == []


def test_profit_factor_below_threshold_fails():
    data = request_data(); data["evidence"]["profit_factor_net"] = 1.49
    result = evaluate(CertificationRequest.model_validate(data))
    assert result.decision == "FAIL"
    assert result.ready_for_live is False
    assert any("profit_factor_net" in reason for reason in result.blocking_reasons)


def test_missing_shadow_proof_fails():
    data = request_data(); data["evidence"]["shadow_validated"] = False
    result = evaluate(CertificationRequest.model_validate(data))
    assert result.decision == "FAIL"
    assert any("shadow" in reason for reason in result.blocking_reasons)


def test_decision_is_deterministic():
    req = CertificationRequest.model_validate(request_data())
    a = evaluate(req); b = evaluate(req)
    assert a.model_dump() == b.model_dump()


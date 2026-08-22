import hashlib
import json
from pathlib import Path
import yaml
from .models import CertificationRequest, CertificationResponse, GateResult, StrategyStatus


ROOT = Path(__file__).resolve().parents[2]


def load_policy(version: str) -> dict:
    path = ROOT / "policies" / f"{version}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown policy version: {version}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _hash_evidence(request: CertificationRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def evaluate(request: CertificationRequest) -> CertificationResponse:
    policy = load_policy(request.policy_version)
    e = request.evidence
    thresholds = policy["thresholds"]
    checks = [
        ("definition", e.definition_complete, "BLOCK", e.definition_complete, "true"),
        ("dataset_provenance", e.dataset_provenance_verified, "BLOCK", e.dataset_provenance_verified, "true"),
        ("reproducibility", e.reproducible, "BLOCK", e.reproducible, "true"),
        ("rr", e.rr_planned >= thresholds["rr_min"], "FAIL", e.rr_planned, f">= {thresholds['rr_min']}"),
        ("profit_factor_net", e.profit_factor_net >= thresholds["profit_factor_net_min"], "FAIL", e.profit_factor_net, f">= {thresholds['profit_factor_net_min']}"),
        ("expectancy_net", e.expectancy_net > thresholds["expectancy_net_min_exclusive"], "FAIL", e.expectancy_net, f"> {thresholds['expectancy_net_min_exclusive']}"),
        ("sample_size", e.sample_size >= thresholds["sample_size_min"], "FAIL", e.sample_size, f">= {thresholds['sample_size_min']}"),
        ("max_drawdown", e.max_drawdown_pct <= thresholds["max_drawdown_pct_max"], "FAIL", e.max_drawdown_pct, f"<= {thresholds['max_drawdown_pct_max']}"),
        ("oos", e.oos_validated, "FAIL", e.oos_validated, "true"),
        ("walk_forward", e.walk_forward_validated, "FAIL", e.walk_forward_validated, "true"),
        ("paper", e.paper_validated, "FAIL", e.paper_validated, "true"),
        ("shadow", e.shadow_validated, "FAIL", e.shadow_validated, "true"),
        ("shadow_gap", e.shadow_execution_gap_bps <= thresholds["shadow_execution_gap_bps_max"], "FAIL", e.shadow_execution_gap_bps, f"<= {thresholds['shadow_execution_gap_bps_max']}"),
        ("security", e.security_controls_validated, "BLOCK", e.security_controls_validated, "true"),
    ]
    gates = [GateResult(gate=n, passed=p, severity=s, observed=o, required=r) for n,p,s,o,r in checks]
    reasons = [f"{g.gate}: observed={g.observed}, required={g.required}" for g in gates if not g.passed]
    required_passes = sum(1 for g in gates if g.passed)
    score = round(100 * required_passes / len(gates), 2)
    ready = not reasons
    return CertificationResponse(
        decision="PASS" if ready else "FAIL",
        status=StrategyStatus.READY_FOR_LIVE if ready else StrategyStatus.RESEARCH,
        ready_for_live=ready,
        score=score,
        blocking_reasons=reasons,
        gates=gates,
        policy_version=request.policy_version,
        evidence_set_hash=_hash_evidence(request),
    )


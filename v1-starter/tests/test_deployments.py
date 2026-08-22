from pathlib import Path
from tempfile import TemporaryDirectory
from apps.api.certification import evaluate
from apps.api.models import CertificationFromRunRequest, DeploymentCreate, HumanApproval, RiskSnapshot
from apps.api.repository import Repository
from tests.test_certification_from_run import make


def certified(repo):
    strategy,run,att,paper,shadow=make(repo)
    req=repo.certification_request_from_run(CertificationFromRunRequest(run_id=run.id,paper_session_id=paper.id,shadow_session_id=shadow.id,attestations=att))
    repo.save_certification(req,evaluate(req))
    return strategy


def test_live_requires_two_distinct_confirmations_and_remains_gateway_locked():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"d.db"); strategy=certified(repo)
        dep=repo.create_deployment(DeploymentCreate(strategy_id=strategy.id,strategy_version="1.0.0",venue="Lighter",capital_limit=10,daily_loss_limit=2,drawdown_limit_pct=5))
        assert dep.status == "CREATED" and dep.gateway_locked is True
        dep=repo.arm_deployment(dep.id,HumanApproval(approved_by="hugo",confirmation="ARM LIVE CANARY"))
        assert dep.status == "ARMED"
        dep=repo.activate_deployment(dep.id,HumanApproval(approved_by="hugo",confirmation="ACTIVATE LIVE CANARY"))
        assert dep.status == "LIVE_LOCKED" and dep.gateway_locked is True


def test_risk_breach_triggers_kill_switch():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"d.db"); strategy=certified(repo)
        dep=repo.create_deployment(DeploymentCreate(strategy_id=strategy.id,strategy_version="1.0.0",venue="Lighter",capital_limit=10,daily_loss_limit=2,drawdown_limit_pct=5))
        dep=repo.monitor_deployment(dep.id,RiskSnapshot(pnl_today=-3,drawdown_pct=1))
        assert dep.status == "SUSPENDED" and dep.gateway_locked is True
        assert "daily loss limit breached" in dep.blocking_reasons


def test_uncertified_strategy_cannot_create_deployment():
    with TemporaryDirectory() as tmp:
        from tests.test_repository import build_registry
        repo=Repository(Path(tmp)/"d.db"); strategy=build_registry(repo)
        try: repo.create_deployment(DeploymentCreate(strategy_id=strategy.id,strategy_version="1.0.0",venue="x",capital_limit=10,daily_loss_limit=2,drawdown_limit_pct=5))
        except ValueError: pass
        else: raise AssertionError("uncertified deployment accepted")

from pathlib import Path
from tempfile import TemporaryDirectory
from apps.api.certification import evaluate
from apps.api.models import CertificationFromRunRequest, DatasetCreate, RunCreate, TradeObservation, ValidationAttestations, ValidationSessionCreate, ValidationObservation
from apps.api.repository import Repository
from tests.test_repository import build_registry


def make(repo):
    strategy=build_registry(repo)
    ds=repo.create_dataset(DatasetCreate(source="fixture",range_start="a",range_end="b",schema_hash="1"*64,content_hash="2"*64))
    trades=[TradeObservation(pnl_gross=4,fees=.1,slippage=.1,planned_risk=1,planned_reward=3) for _ in range(80)]
    trades += [TradeObservation(pnl_gross=-1,fees=.1,slippage=.1,planned_risk=1,planned_reward=3) for _ in range(20)]
    run=repo.create_run(RunCreate(strategy_id=strategy.id,strategy_version="1.0.0",dataset_version_id=ds.id,starting_equity=1000,trades=trades))
    att=ValidationAttestations(definition_complete=True,dataset_provenance_verified=True,oos_validated=True,walk_forward_validated=True,security_controls_validated=True)
    sessions=[]
    for mode in ("paper","shadow"):
        session=repo.create_validation_session(ValidationSessionCreate(strategy_id=strategy.id,strategy_version="1.0.0",mode=mode,minimum_observations=3))
        for _ in range(3): repo.add_validation_observation(session.id,ValidationObservation(execution_gap_bps=5,accepted=True))
        sessions.append(repo.finalize_validation_session(session.id))
    return strategy,run,att,sessions[0],sessions[1]


def test_certification_metrics_are_derived_from_run():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"x.db"); strategy,run,att,paper,shadow=make(repo)
        request=repo.certification_request_from_run(CertificationFromRunRequest(run_id=run.id,paper_session_id=paper.id,shadow_session_id=shadow.id,attestations=att))
        assert request.evidence.profit_factor_net == run.metrics["profit_factor_net"]
        assert request.evidence.manifest_hash == run.manifest_hash
        assert evaluate(request).ready_for_live is True


def test_failed_shadow_session_blocks_run_certification():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"x.db"); strategy,run,att,paper,shadow=make(repo)
        failed=repo.create_validation_session(ValidationSessionCreate(strategy_id=strategy.id,strategy_version="1.0.0",mode="shadow",minimum_observations=2,max_mean_gap_bps=2))
        repo.add_validation_observation(failed.id,ValidationObservation(execution_gap_bps=10)); repo.add_validation_observation(failed.id,ValidationObservation(execution_gap_bps=10))
        failed=repo.finalize_validation_session(failed.id)
        request=repo.certification_request_from_run(CertificationFromRunRequest(run_id=run.id,paper_session_id=paper.id,shadow_session_id=failed.id,attestations=att))
        result=evaluate(request); assert result.ready_for_live is False
        assert any("shadow" in x for x in result.blocking_reasons)

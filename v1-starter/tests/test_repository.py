import json
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.api.certification import evaluate
from apps.api.models import CertificationRequest, ProjectCreate, StrategyCreate, StrategyVersionCreate
from apps.api.repository import Repository

ROOT=Path(__file__).resolve().parents[1]


def build_registry(repo):
    project=repo.create_project(ProjectCreate(owner_id="hugo",name="MOS"))
    strategy=repo.create_strategy(StrategyCreate(project_id=project.id,name="Demo",thesis="Test",market="BTC",venue="Lighter",timeframe="5m"))
    repo.create_version(strategy.id,StrategyVersionCreate(version="1.0.0",code_hash="a"*64,config_hash="d"*64))
    return strategy


def test_registry_and_persisted_readiness():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"test.db"); strategy=build_registry(repo)
        before=repo.readiness(strategy.id)
        assert before.ready_for_live is False
        raw=json.loads((ROOT/"examples/certification-pass.json").read_text())
        raw["strategy_id"]=strategy.id
        request=CertificationRequest.model_validate(raw); response=evaluate(request)
        cid=repo.save_certification(request,response)
        after=repo.readiness(strategy.id)
        assert after.ready_for_live is True
        assert after.certification_id == cid


def test_strategy_version_is_immutable():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"test.db"); strategy=build_registry(repo)
        try:
            repo.create_version(strategy.id,StrategyVersionCreate(version="1.0.0",code_hash="b"*64,config_hash="e"*64))
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate immutable version accepted")


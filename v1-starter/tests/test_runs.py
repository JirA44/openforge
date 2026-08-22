from pathlib import Path
from tempfile import TemporaryDirectory
from apps.api.models import DatasetCreate, RunCreate, TradeObservation
from apps.api.repository import Repository
from tests.test_repository import build_registry


def test_run_is_hashed_and_replayable():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"test.db"); strategy=build_registry(repo)
        dataset=repo.create_dataset(DatasetCreate(source="fixture",range_start="2026-01-01",range_end="2026-01-31",schema_hash="1"*64,content_hash="2"*64,quality={"missing":0}))
        trades=[TradeObservation(pnl_gross=4,fees=.1,slippage=.1,planned_risk=1,planned_reward=3) for _ in range(80)]
        trades += [TradeObservation(pnl_gross=-1,fees=.1,slippage=.1,planned_risk=1,planned_reward=3) for _ in range(20)]
        run=repo.create_run(RunCreate(strategy_id=strategy.id,strategy_version="1.0.0",dataset_version_id=dataset.id,starting_equity=1000,trades=trades))
        assert run.reproducible is True
        assert run.metrics["sample_size"] == 100
        replay=repo.replay_run(run.id)
        assert replay.status == "REPLAY_MATCH"
        assert replay.result_hash == run.result_hash


def test_identical_manifest_is_not_silently_duplicated():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"test.db"); strategy=build_registry(repo)
        dataset=repo.create_dataset(DatasetCreate(source="fixture",range_start="a",range_end="b",schema_hash="1"*64,content_hash="2"*64))
        req=RunCreate(strategy_id=strategy.id,strategy_version="1.0.0",dataset_version_id=dataset.id,starting_equity=100,trades=[TradeObservation(pnl_gross=1,fees=0,slippage=0,planned_risk=1,planned_reward=3)])
        repo.create_run(req)
        try: repo.create_run(req)
        except ValueError: pass
        else: raise AssertionError("duplicate manifest accepted")

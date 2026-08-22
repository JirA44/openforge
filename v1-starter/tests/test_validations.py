from pathlib import Path
from tempfile import TemporaryDirectory
from apps.api.models import ValidationObservation, ValidationSessionCreate
from apps.api.repository import Repository
from tests.test_repository import build_registry


def test_validation_requires_enough_real_observations():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"v.db"); s=build_registry(repo)
        session=repo.create_validation_session(ValidationSessionCreate(strategy_id=s.id,strategy_version="1.0.0",mode="paper",minimum_observations=3))
        repo.add_validation_observation(session.id,ValidationObservation(execution_gap_bps=1))
        result=repo.finalize_validation_session(session.id)
        assert result.passed is False
        assert any("observations" in x for x in result.blocking_reasons)


def test_validation_passes_only_with_gap_and_rejections_below_limits():
    with TemporaryDirectory() as tmp:
        repo=Repository(Path(tmp)/"v.db"); s=build_registry(repo)
        session=repo.create_validation_session(ValidationSessionCreate(strategy_id=s.id,strategy_version="1.0.0",mode="shadow",minimum_observations=4,max_mean_gap_bps=5,max_rejection_rate=.25))
        for gap in (2,3,4,5): repo.add_validation_observation(session.id,ValidationObservation(execution_gap_bps=gap,accepted=True))
        result=repo.finalize_validation_session(session.id)
        assert result.passed is True

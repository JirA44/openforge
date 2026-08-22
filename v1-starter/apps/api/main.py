from datetime import datetime, timezone
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from .certification import evaluate
from .models import (
    CertificationRequest, CertificationResponse, Project, ProjectCreate,
    ReadinessResponse, Strategy, StrategyCreate, DatasetCreate, DatasetVersion,
    RunCreate, RunResult, StrategyVersion, StrategyVersionCreate, CertificationFromRunRequest,
    ValidationSessionCreate, ValidationObservation, ValidationSessionResult,
)
from .repository import Repository

app = FastAPI(
    title="OpenForge / MOS Hub API",
    version="1.0.3",
    description="API d'artefacts vérifiables et de certification déterministe de stratégies.",
)
DB_PATH = os.getenv("OPENFORGE_DB", str(Path(__file__).resolve().parents[2] / "openforge.db"))
repo = Repository(DB_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/certifications/evaluate", response_model=CertificationResponse)
def certify(request: CertificationRequest) -> CertificationResponse:
    try:
        response = evaluate(request)
        repo.save_certification(request, response)
        return response
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/certifications/from-run", response_model=CertificationResponse)
def certify_from_run(data: CertificationFromRunRequest) -> CertificationResponse:
    try:
        request=repo.certification_request_from_run(data)
        response=evaluate(request)
        repo.save_certification(request,response)
        return response
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc


@app.post("/v1/projects", response_model=Project, status_code=201)
def create_project(data: ProjectCreate) -> Project:
    return repo.create_project(data)


@app.post("/v1/strategies", response_model=Strategy, status_code=201)
def create_strategy(data: StrategyCreate) -> Strategy:
    try: return repo.create_strategy(data)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/strategies/{strategy_id}", response_model=Strategy)
def get_strategy(strategy_id: str) -> Strategy:
    item=repo.get_strategy(strategy_id)
    if not item: raise HTTPException(status_code=404, detail="strategy not found")
    return item


@app.post("/v1/strategies/{strategy_id}/versions", response_model=StrategyVersion, status_code=201)
def create_version(strategy_id: str, data: StrategyVersionCreate) -> StrategyVersion:
    try: return repo.create_version(strategy_id,data)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/datasets/versions", response_model=DatasetVersion, status_code=201)
def create_dataset(data: DatasetCreate) -> DatasetVersion:
    try: return repo.create_dataset(data)
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc


@app.post("/v1/runs", response_model=RunResult, status_code=201)
def create_run(data: RunCreate) -> RunResult:
    try: return repo.create_run(data)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc


@app.get("/v1/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> RunResult:
    try: return repo.get_run(run_id)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc


@app.post("/v1/runs/{run_id}/replay", response_model=RunResult)
def replay_run(run_id: str) -> RunResult:
    try: return repo.replay_run(run_id)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc


@app.post("/v1/validations", response_model=ValidationSessionResult, status_code=201)
def create_validation(data: ValidationSessionCreate) -> ValidationSessionResult:
    try: return repo.create_validation_session(data)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc


@app.post("/v1/validations/{session_id}/observations", status_code=204)
def add_observation(session_id: str, data: ValidationObservation) -> None:
    try: repo.add_validation_observation(session_id,data)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc


@app.post("/v1/validations/{session_id}/finalize", response_model=ValidationSessionResult)
def finalize_validation(session_id: str) -> ValidationSessionResult:
    try: return repo.finalize_validation_session(session_id)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc


@app.get("/v1/strategies/{strategy_id}/readiness", response_model=ReadinessResponse)
def readiness(strategy_id: str) -> ReadinessResponse:
    try: return repo.readiness(strategy_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

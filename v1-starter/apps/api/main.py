from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from .certification import evaluate
from .models import CertificationRequest, CertificationResponse

app = FastAPI(
    title="OpenForge / MOS Hub API",
    version="0.1.0",
    description="API d'artefacts vérifiables et de certification déterministe de stratégies.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/certifications/evaluate", response_model=CertificationResponse)
def certify(request: CertificationRequest) -> CertificationResponse:
    try:
        return evaluate(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/strategies/{strategy_id}/readiness")
def readiness(strategy_id: str) -> dict:
    return {
        "strategy_id": strategy_id,
        "status": "NOT_EVALUATED",
        "ready_for_live": False,
        "blocking_evidence": ["No persisted certification found"],
    }


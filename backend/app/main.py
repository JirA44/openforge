from pathlib import Path
from typing import Any
import hashlib
import json

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="OpenForge API", version="0.1.0")


class ManifestPayload(BaseModel):
    manifest: dict[str, Any]


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/validate")
def validate_manifest(payload: ManifestPayload) -> dict[str, Any]:
    required = {"schema_version", "artifact_type", "name", "version", "license"}
    missing = sorted(required - payload.manifest.keys())
    if missing:
        raise HTTPException(status_code=400, detail={"missing": missing})

    allowed = {"strategy", "dataset", "knowledge", "proof", "decision"}
    artifact_type = payload.manifest["artifact_type"]
    if artifact_type not in allowed:
        raise HTTPException(status_code=400, detail="artifact_type invalide")

    return {
        "valid": True,
        "artifact_type": artifact_type,
        "manifest_hash": canonical_hash(payload.manifest),
    }


@app.post("/hash")
def hash_manifest(payload: ManifestPayload) -> dict[str, str]:
    return {"sha256": canonical_hash(payload.manifest)}


# ── MOS Hub (spec docs/SPEC_OPENFORGE_V1.md) ────────────────────────────────
from . import moshub


class BacktestRequest(BaseModel):
    manifest: dict[str, Any]
    synthetic: bool = False  # True : évaluateur de démo sans dépendances


def _synthetic_evaluator(manifest: dict[str, Any]) -> dict[str, Any]:
    """Évaluateur déterministe minimal pour tests/démo hors ml_trading."""
    seed = int(moshub.canonical_hash(manifest)[:8], 16)
    pf = 1.0 + (seed % 100) / 100  # 1.00–1.99 stable par manifeste
    return {
        "aggregate": {
            "net_profit_factor": round(pf, 3),
            "gross_profit_factor": round(pf * 1.2, 3),
            "compounded_return_pct": round((pf - 1) * 100, 2),
            "closed_trades": 100 + seed % 50,
            "positive_fold_ratio": 0.6,
        },
        "folds": [{"fold": i + 1, "net_pf": round(pf, 3)} for i in range(5)],
    }


@app.post("/moshub/backtest")
def moshub_backtest(request: BacktestRequest) -> dict[str, Any]:
    evaluator = _synthetic_evaluator if request.synthetic else None
    try:
        return moshub.run_backtest(request.manifest, evaluator=evaluator)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/moshub/runs/{run_id}")
def moshub_run(run_id: str) -> dict[str, Any]:
    try:
        return moshub.load_sheet(run_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


class CompareRequest(BaseModel):
    a: str
    b: str


@app.post("/moshub/compare")
def moshub_compare(request: CompareRequest) -> dict[str, Any]:
    try:
        return moshub.compare(request.a, request.b)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/moshub/sheets")
def moshub_sheets() -> list[dict[str, Any]]:
    return moshub.list_sheets()

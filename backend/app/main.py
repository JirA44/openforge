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

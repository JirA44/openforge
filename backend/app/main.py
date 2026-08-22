from pathlib import Path
from typing import Any
import hashlib
import json

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
        sheet = moshub.run_backtest(request.manifest, evaluator=evaluator)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    # Persistance SQLite (spec V1 §2.1)
    from . import db
    mh = sheet["manifest_hash"]
    db.save_artifact(request.manifest, mh, sheet["computed_at"])
    db.save_run(
        run_id=sheet["sheet_signature"][:24],
        manifest_hash=mh,
        engine_version="edge_harness_v2",
        metrics=sheet["results"]["aggregate"],
        folds=sheet["results"].get("folds", []),
        signature=sheet["sheet_signature"],
        runtime_s=sheet["runtime_s"],
        computed_at=sheet["computed_at"],
    )
    return sheet


@app.get("/moshub/leaderboard")
def moshub_leaderboard(format: str = "json") -> Any:
    from . import db
    rows = db.leaderboard()
    if format == "html":
        badges = {
            r: f"<span class='badge' style='background:{color}'>{r}</span>"
            for r, color in [("CERTIFIED", "#2e7d32"), ("READY_FOR_LIVE", "#1b5e20"), ("SHADOW", "#0069c0"), ("PAPER", "#f57c00")]
        }
        lines = [
            "<tr><td>#</td><td>nom</td><td>version</td><td>PF net</td><td>trades</td><td>retour</td><td>hash</td></tr>"
        ]
        for index, row in enumerate(rows, 1):
            lines.append(
                f"<tr><td>{index}</td><td>{row['name']}</td><td>{row['version']}</td>"
                f"<td>{row['net_pf'] if row['net_pf'] is not None else '—'}</td>"
                f"<td>{row['trades'] if row['trades'] is not None else '—'}</td>"
                f"<td>{row['return_pct'] if row['return_pct'] is not None else '—'}%</td>"
                f"<td><code>{row['manifest_hash']}</code></td></tr>"
            )
        body = "\n".join(lines)
        return HTMLResponse(
            "<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='60'><title>MOS Hub — Leaderboard</title>"
            "<style>body{font-family:Consolas,monospace;background:#111;color:#ddd;margin:2em}"
            "table{border-collapse:collapse;width:100%}th,td{padding:6px 10px;border-bottom:1px solid #333;text-align:left}"
            "th{color:#888}h1{font-size:1.3em;color:#fff}.badge{padding:2px 8px;border-radius:3px;color:#fff}"
            "</style></head><body><h1>MOS HUB — LEADERBOARD</h1>"
            "<p style='color:#666'>Trié par PF net OOS · auto-refresh 60s</p>"
            f"<table>{body}</table></body></html>"
        )
    return rows


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

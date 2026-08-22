"""MOS Hub — backtests reproductibles et comparables depuis un manifeste.

Le manifeste est un artefact OpenForge ``artifact_type: strategy``. Le même
manifeste + les mêmes données => le même hash de résultats : c'est le contrat
de reproductibilité.

L'évaluateur réel (walk-forward, coûts, RR gate) vit dans ml_trading
(``trading.edge_harness_v2``). Pour rester exécutable sans cette dépendance,
le module accepte un évaluateur injecté ; sinon il tente le chargement dynamique.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

DataDir = Path(os.environ.get("MOSHUB_DATA_DIR", Path(__file__).resolve().parents[2] / "data" / "moshub"))
ML_TRADING_PATH = Path(os.environ.get("MOSHUB_ML_TRADING_PATH", r"C:\Users\Hugop\ml_trading"))


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sign_sheet(sheet: dict[str, Any], signing_key: str | None = None) -> str:
    """Signature HMAC-SHA256 de la fiche (clé via MOSHUB_SIGNING_KEY)."""
    import hmac

    key = signing_key or os.environ.get("MOSHUB_SIGNING_KEY", "openforge-dev-key")
    body = json.dumps(sheet, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key.encode(), body, hashlib.sha256).hexdigest()


def _load_evaluator() -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    """Charge l'évaluateur walk-forward de ml_trading (dépendance optionnelle)."""
    if str(ML_TRADING_PATH) not in os.sys.path:
        os.sys.path.insert(0, str(ML_TRADING_PATH))
    from run_strategy_sweep import load_frame  # type: ignore

    from strategy_engine.population import Individual, compute_feature, harness_config  # type: ignore
    from trading.edge_harness_v2 import aggregate_v2, evaluate_walk_forward_v2  # type: ignore

    def evaluate(manifest: dict[str, Any], frame: dict[str, Any] | None = None) -> dict[str, Any]:
        params = manifest.get("params", {})
        family = manifest.get("family", "momentum_pullback")
        individual = Individual(family=family, params=params)
        data = load_frame(manifest.get("data_start", "2016-12-30"))
        data = data.dropna(subset=["Open", "High", "Low", "Close"]).reset_index(drop=True)
        data["feature"] = compute_feature(individual, data).to_numpy()
        report = evaluate_walk_forward_v2(
            data,
            feature_column="feature",
            fee_rate=float(manifest.get("fee_rate", 0.0005)),
            config=harness_config(individual),
        )
        agg = aggregate_v2(report["folds"])
        folds = [
            {
                "fold": f["fold"],
                "oos": f["oos_dates"],
                "net_pf": round(f["metrics"]["profit_factor"], 3),
                "trades": f["metrics"]["closed_trades"],
            }
            for f in report["folds"]
        ]
        return {"aggregate": _round_agg(agg), "folds": folds}

    return evaluate


def _round_agg(agg: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in agg.items():
        out[key] = round(value, 4) if isinstance(value, float) else value
    return out


def run_backtest(
    manifest: dict[str, Any],
    evaluator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Exécute un backtest standardisé depuis un manifeste de stratégie."""
    required = {"schema_version", "artifact_type", "name", "version", "license"}
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"manifeste invalide, champs manquants: {missing}")
    if manifest.get("artifact_type") != "strategy":
        raise ValueError("MOS Hub n'accepte que artifact_type=strategy")

    mh = canonical_hash(manifest)
    evaluate = evaluator or _load_evaluator()
    started = time.time()
    results = evaluate(manifest)
    sheet = {
        "manifest_name": manifest["name"],
        "manifest_version": manifest["version"],
        "manifest_hash": mh,
        "results": results,
        "runtime_s": round(time.time() - started, 2),
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    sheet["sheet_signature"] = sign_sheet(sheet)

    DataDir.mkdir(parents=True, exist_ok=True)
    out = DataDir / f"{mh}.json"
    out.write_text(json.dumps(sheet, indent=2), encoding="utf-8")
    return sheet


def load_sheet(manifest_or_hash: dict[str, Any] | str) -> dict[str, Any]:
    mh = manifest_or_hash if isinstance(manifest_or_hash, str) else canonical_hash(manifest_or_hash)
    path = DataDir / f"{mh}.json"
    if not path.exists():
        raise FileNotFoundError(f"aucune fiche pour {mh[:16]}…")
    return json.loads(path.read_text(encoding="utf-8"))


METRIC_KEYS = ("net_profit_factor", "gross_profit_factor", "compounded_return_pct", "closed_trades", "positive_fold_ratio")


def compare(hash_a: str, hash_b: str) -> dict[str, Any]:
    """Compare deux fiches de performance : diff métrique par métrique."""
    sheet_a = load_sheet(hash_a)
    sheet_b = load_sheet(hash_b)
    agg_a = sheet_a["results"]["aggregate"]
    agg_b = sheet_b["results"]["aggregate"]
    diff = {}
    for key in METRIC_KEYS:
        va, vb = agg_a.get(key), agg_b.get(key)
        diff[key] = (
            {
                "a": va,
                "b": vb,
                "delta": round(vb - va, 4) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None,
            }
        )
    winner = max((hash_a, hash_b), key=lambda h: load_sheet(h)["results"]["aggregate"].get("net_profit_factor", -9))
    return {
        "a": hash_a[:16],
        "b": hash_b[:16],
        "diff": diff,
        "winner_by_net_pf": winner[:16],
        "both_signed": bool(sheet_a.get("sheet_signature") and sheet_b.get("sheet_signature")),
    }


def list_sheets() -> list[dict[str, Any]]:
    DataDir.mkdir(parents=True, exist_ok=True)
    sheets = []
    for path in sorted(DataDir.glob("*.json")):
        try:
            sheet = json.loads(path.read_text(encoding="utf-8"))
            sheets.append(
                {
                    "manifest_hash": sheet["manifest_hash"][:16],
                    "name": sheet["manifest_name"],
                    "version": sheet["manifest_version"],
                    "pf_net": sheet["results"]["aggregate"].get("net_profit_factor"),
                    "trades": sheet["results"]["aggregate"].get("closed_trades"),
                }
            )
        except (json.JSONDecodeError, KeyError):
            continue
    return sheets

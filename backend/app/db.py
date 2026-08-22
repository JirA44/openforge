"""SQLite pour MOS Hub — schéma du spec V1 §2.1. Append-only : les tables
runs et certifications ne sont jamais mises à jour, seulement insérées."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "openforge.db"
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
  manifest_hash TEXT PRIMARY KEY,
  artifact_type TEXT NOT NULL,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  license TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  parent_hash TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dataset_bindings (
  manifest_hash TEXT NOT NULL,
  dataset_hash TEXT NOT NULL,
  PRIMARY KEY (manifest_hash, dataset_hash)
);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  manifest_hash TEXT NOT NULL,
  dataset_hash TEXT NOT NULL DEFAULT '',
  engine_version TEXT NOT NULL,
  metrics_json TEXT NOT NULL,
  folds_json TEXT NOT NULL,
  sheet_signature TEXT NOT NULL,
  runtime_s REAL,
  computed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS certifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manifest_hash TEXT NOT NULL,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  checks_json TEXT NOT NULL,
  blocking_reasons_json TEXT NOT NULL,
  computed_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript(SCHEMA)


def save_artifact(manifest: dict, manifest_hash: str, created_at: str) -> None:
    init_db()
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO artifacts (manifest_hash, artifact_type, name, version, license, manifest_json, parent_hash, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                manifest_hash, manifest["artifact_type"], manifest["name"],
                manifest["version"], manifest.get("license", ""),
                json.dumps(manifest, sort_keys=True), manifest.get("parent_hash"),
                created_at,
            ),
        )


def save_run(run_id: str, manifest_hash: str, engine_version: str, metrics: dict, folds: list, signature: str, runtime_s: float, computed_at: str) -> None:
    init_db()
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO runs (run_id, manifest_hash, dataset_hash, engine_version, metrics_json, folds_json, sheet_signature, runtime_s, computed_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, manifest_hash, "", engine_version,
             json.dumps(metrics, sort_keys=True), json.dumps(folds),
             signature, runtime_s, computed_at),
        )


def save_certification(manifest_hash: str, from_status: str, to_status: str, checks: dict, blocking: list, computed_at: str) -> int:
    init_db()
    with _lock, _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO certifications (manifest_hash, from_status, to_status, checks_json, blocking_reasons_json, computed_at)"
            " VALUES (?,?,?,?,?,?)",
            (manifest_hash, from_status, to_status,
             json.dumps(checks, sort_keys=True), json.dumps(blocking), computed_at),
        )
        return cursor.lastrowid or 0


def leaderboard(limit: int = 50) -> list[dict]:
    """Classement par PF net OOS des derniers runs, avec historique de certification."""
    init_db()
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT r.manifest_hash, r.metrics_json, a.name, a.version, MAX(r.computed_at) as last"
            " FROM runs r LEFT JOIN artifacts a ON a.manifest_hash = r.manifest_hash"
            " GROUP BY r.manifest_hash ORDER BY CAST(json_extract(r.metrics_json, '$.net_profit_factor') AS REAL) DESC"
            " LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        metrics = json.loads(row["metrics_json"])
        cert_count = conn_count(row["manifest_hash"])
        out.append(
            {
                "manifest_hash": row["manifest_hash"][:16],
                "name": row["name"] or "—",
                "version": row["version"] or "",
                "net_pf": metrics.get("net_profit_factor"),
                "trades": metrics.get("closed_trades"),
                "return_pct": metrics.get("compounded_return_pct"),
                "certification_events": cert_count,
            }
        )
    return out


def conn_count(manifest_hash: str) -> int:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as n FROM certifications WHERE manifest_hash=?", (manifest_hash,)
        ).fetchone()
    return row["n"] if row else 0

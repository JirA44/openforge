import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import (
    CertificationRequest, CertificationResponse, Project, ProjectCreate,
    ReadinessResponse, Strategy, StrategyCreate, StrategyStatus, DatasetCreate,
    DatasetVersion, RunCreate, RunResult, StrategyVersion, StrategyVersionCreate,
    CertificationFromRunRequest, Evidence,
    ValidationSessionCreate, ValidationObservation, ValidationSessionResult,
)
from .runs import build_manifest, canonical_hash, execute_reproducibly


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL,
  visibility TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategies (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  name TEXT NOT NULL, thesis TEXT NOT NULL, market TEXT NOT NULL,
  venue TEXT NOT NULL, timeframe TEXT NOT NULL, status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategy_versions (
  id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL REFERENCES strategies(id),
  version TEXT NOT NULL, code_hash TEXT NOT NULL, config_hash TEXT NOT NULL,
  parent_id TEXT REFERENCES strategy_versions(id), created_at TEXT NOT NULL,
  UNIQUE(strategy_id, version)
);
CREATE TABLE IF NOT EXISTS certifications (
  id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL REFERENCES strategies(id),
  strategy_version TEXT NOT NULL, policy_version TEXT NOT NULL,
  decision TEXT NOT NULL, status TEXT NOT NULL, ready_for_live INTEGER NOT NULL,
  score REAL NOT NULL, evidence_set_hash TEXT NOT NULL,
  blocking_reasons TEXT NOT NULL, response_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dataset_versions (
  id TEXT PRIMARY KEY, source TEXT NOT NULL, range_start TEXT NOT NULL,
  range_end TEXT NOT NULL, schema_hash TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE,
  quality_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_runs (
  id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL REFERENCES strategies(id),
  strategy_version TEXT NOT NULL, dataset_version_id TEXT NOT NULL REFERENCES dataset_versions(id),
  manifest_json TEXT NOT NULL, manifest_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL, metrics_json TEXT NOT NULL, result_hash TEXT NOT NULL,
  reproducible INTEGER NOT NULL, created_at TEXT NOT NULL, completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
  payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS validation_sessions (
 id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL REFERENCES strategies(id), strategy_version TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('paper','shadow')), minimum_observations INTEGER NOT NULL,
 max_mean_gap_bps REAL NOT NULL, max_rejection_rate REAL NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, finalized_at TEXT
);
CREATE TABLE IF NOT EXISTS validation_observations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES validation_sessions(id),
 execution_gap_bps REAL NOT NULL, accepted INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_strategies_project ON strategies(project_id);
CREATE INDEX IF NOT EXISTS idx_versions_strategy ON strategy_versions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_certifications_strategy ON certifications(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_strategy ON experiment_runs(strategy_id, created_at DESC);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def _audit(self, conn, event: str, kind: str, entity_id: str, payload: dict) -> None:
        conn.execute("INSERT INTO audit_events(event_type,entity_type,entity_id,payload_json,created_at) VALUES(?,?,?,?,?)", (event,kind,entity_id,json.dumps(payload,sort_keys=True),now()))

    def create_project(self, data: ProjectCreate) -> Project:
        item = Project(id=str(uuid.uuid4()), created_at=now(), **data.model_dump())
        with self.connect() as c:
            c.execute("INSERT INTO projects VALUES(?,?,?,?,?)", tuple(item.model_dump().values()))
            self._audit(c,"PROJECT_CREATED","project",item.id,item.model_dump())
        return item

    def create_strategy(self, data: StrategyCreate) -> Strategy:
        item = Strategy(id=str(uuid.uuid4()), status=StrategyStatus.DRAFT, created_at=now(), **data.model_dump())
        with self.connect() as c:
            if not c.execute("SELECT 1 FROM projects WHERE id=?",(data.project_id,)).fetchone():
                raise KeyError("project not found")
            c.execute("INSERT INTO strategies VALUES(?,?,?,?,?,?,?,?,?)", tuple(item.model_dump(mode="json").values()))
            self._audit(c,"STRATEGY_CREATED","strategy",item.id,item.model_dump(mode="json"))
        return item

    def create_version(self, strategy_id: str, data: StrategyVersionCreate) -> StrategyVersion:
        item = StrategyVersion(id=str(uuid.uuid4()), strategy_id=strategy_id, created_at=now(), **data.model_dump())
        with self.connect() as c:
            if not c.execute("SELECT 1 FROM strategies WHERE id=?",(strategy_id,)).fetchone():
                raise KeyError("strategy not found")
            try:
                c.execute("INSERT INTO strategy_versions VALUES(?,?,?,?,?,?,?)", tuple(item.model_dump().values()))
            except sqlite3.IntegrityError as exc:
                raise ValueError("strategy version already exists or parent is invalid") from exc
            self._audit(c,"VERSION_FROZEN","strategy_version",item.id,item.model_dump())
        return item

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        with self.connect() as c:
            row=c.execute("SELECT * FROM strategies WHERE id=?",(strategy_id,)).fetchone()
        return Strategy.model_validate(dict(row)) if row else None

    def create_dataset(self, data: DatasetCreate) -> DatasetVersion:
        item=DatasetVersion(id=str(uuid.uuid4()),created_at=now(),**data.model_dump())
        with self.connect() as c:
            try:
                c.execute("INSERT INTO dataset_versions VALUES(?,?,?,?,?,?,?,?)",(item.id,item.source,item.range_start,item.range_end,item.schema_hash,item.content_hash,json.dumps(item.quality,sort_keys=True),item.created_at))
            except sqlite3.IntegrityError as exc:
                raise ValueError("dataset content hash already registered") from exc
            self._audit(c,"DATASET_REGISTERED","dataset_version",item.id,item.model_dump())
        return item

    def create_run(self, data: RunCreate) -> RunResult:
        created=now(); rid=str(uuid.uuid4())
        with self.connect() as c:
            version=c.execute("SELECT * FROM strategy_versions WHERE strategy_id=? AND version=?",(data.strategy_id,data.strategy_version)).fetchone()
            dataset=c.execute("SELECT * FROM dataset_versions WHERE id=?",(data.dataset_version_id,)).fetchone()
            if not version: raise KeyError("strategy version not found")
            if not dataset: raise KeyError("dataset version not found")
            manifest=build_manifest(data,dict(version),dict(dataset)); manifest_hash=canonical_hash(manifest)
            metrics,result_hash,reproducible=execute_reproducibly(manifest); completed=now()
            try:
                c.execute("INSERT INTO experiment_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(rid,data.strategy_id,data.strategy_version,data.dataset_version_id,json.dumps(manifest,sort_keys=True),manifest_hash,"COMPLETED",json.dumps(metrics,sort_keys=True),result_hash,int(reproducible),created,completed))
            except sqlite3.IntegrityError as exc:
                raise ValueError("identical manifest already executed; use replay") from exc
            self._audit(c,"RUN_COMPLETED","experiment_run",rid,{"manifest_hash":manifest_hash,"result_hash":result_hash,"reproducible":reproducible})
        return RunResult(id=rid,status="COMPLETED",manifest_hash=manifest_hash,result_hash=result_hash,metrics=metrics,reproducible=reproducible,created_at=created,completed_at=completed)

    def get_run(self, run_id: str) -> RunResult:
        with self.connect() as c: row=c.execute("SELECT * FROM experiment_runs WHERE id=?",(run_id,)).fetchone()
        if not row: raise KeyError("run not found")
        return RunResult(id=row["id"],status=row["status"],manifest_hash=row["manifest_hash"],result_hash=row["result_hash"],metrics=json.loads(row["metrics_json"]),reproducible=bool(row["reproducible"]),created_at=row["created_at"],completed_at=row["completed_at"])

    def replay_run(self, run_id: str) -> RunResult:
        with self.connect() as c:
            row=c.execute("SELECT * FROM experiment_runs WHERE id=?",(run_id,)).fetchone()
            if not row: raise KeyError("run not found")
            metrics,result_hash,reproducible=execute_reproducibly(json.loads(row["manifest_json"]))
            same=result_hash==row["result_hash"] and reproducible
            self._audit(c,"RUN_REPLAYED","experiment_run",run_id,{"original_result_hash":row["result_hash"],"replay_result_hash":result_hash,"match":same})
        return RunResult(id=run_id,status="REPLAY_MATCH" if same else "REPLAY_MISMATCH",manifest_hash=row["manifest_hash"],result_hash=result_hash,metrics=metrics,reproducible=same,created_at=row["created_at"],completed_at=now())

    def certification_request_from_run(self, data: CertificationFromRunRequest) -> CertificationRequest:
        with self.connect() as c:
            row=c.execute("SELECT * FROM experiment_runs WHERE id=?",(data.run_id,)).fetchone()
            if not row: raise KeyError("run not found")
        if row["status"] != "COMPLETED" or not bool(row["reproducible"]):
            raise ValueError("run is not completed and reproducible")
        paper=self.get_validation_session(data.paper_session_id); shadow=self.get_validation_session(data.shadow_session_id)
        if paper.strategy_id != row["strategy_id"] or shadow.strategy_id != row["strategy_id"]: raise ValueError("validation session strategy mismatch")
        if paper.strategy_version != row["strategy_version"] or shadow.strategy_version != row["strategy_version"]: raise ValueError("validation session version mismatch")
        if paper.mode != "paper" or shadow.mode != "shadow": raise ValueError("paper/shadow session mode mismatch")
        manifest=json.loads(row["manifest_json"]); metrics=json.loads(row["metrics_json"]); a=data.attestations
        evidence=Evidence(
            definition_complete=a.definition_complete,
            dataset_provenance_verified=a.dataset_provenance_verified,
            reproducible=True,
            oos_validated=a.oos_validated,
            walk_forward_validated=a.walk_forward_validated,
            paper_validated=paper.passed,
            shadow_validated=shadow.passed,
            security_controls_validated=a.security_controls_validated,
            rr_planned=metrics["rr_planned"], profit_factor_net=metrics["profit_factor_net"],
            expectancy_net=metrics["expectancy_net"], sample_size=metrics["sample_size"],
            max_drawdown_pct=metrics["max_drawdown_pct"], shadow_execution_gap_bps=shadow.mean_gap_bps,
            code_hash=manifest["code_hash"], dataset_hash=manifest["dataset_hash"], manifest_hash=row["manifest_hash"],
        )
        return CertificationRequest(project_id="derived-from-registry",strategy_id=row["strategy_id"],strategy_version=row["strategy_version"],policy_version=data.policy_version,evidence=evidence)

    def create_validation_session(self, data: ValidationSessionCreate) -> ValidationSessionResult:
        sid=str(uuid.uuid4())
        with self.connect() as c:
            if not c.execute("SELECT 1 FROM strategy_versions WHERE strategy_id=? AND version=?",(data.strategy_id,data.strategy_version)).fetchone(): raise KeyError("strategy version not found")
            c.execute("INSERT INTO validation_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",(sid,data.strategy_id,data.strategy_version,data.mode,data.minimum_observations,data.max_mean_gap_bps,data.max_rejection_rate,"RUNNING",now(),None))
            self._audit(c,"VALIDATION_STARTED","validation_session",sid,data.model_dump())
        return self.get_validation_session(sid)

    def add_validation_observation(self, session_id: str, data: ValidationObservation) -> None:
        with self.connect() as c:
            row=c.execute("SELECT status FROM validation_sessions WHERE id=?",(session_id,)).fetchone()
            if not row: raise KeyError("validation session not found")
            if row["status"] != "RUNNING": raise ValueError("validation session already finalized")
            c.execute("INSERT INTO validation_observations(session_id,execution_gap_bps,accepted,created_at) VALUES(?,?,?,?)",(session_id,data.execution_gap_bps,int(data.accepted),now()))

    def get_validation_session(self, session_id: str) -> ValidationSessionResult:
        with self.connect() as c:
            row=c.execute("SELECT * FROM validation_sessions WHERE id=?",(session_id,)).fetchone()
            if not row: raise KeyError("validation session not found")
            stats=c.execute("SELECT COUNT(*) n, COALESCE(AVG(execution_gap_bps),0) gap, COALESCE(AVG(CASE WHEN accepted=0 THEN 1.0 ELSE 0 END),0) reject FROM validation_observations WHERE session_id=?",(session_id,)).fetchone()
        reasons=[]
        if stats["n"] < row["minimum_observations"]: reasons.append(f"observations {stats['n']} < {row['minimum_observations']}")
        if stats["gap"] > row["max_mean_gap_bps"]: reasons.append(f"mean gap {stats['gap']:.4f} > {row['max_mean_gap_bps']}")
        if stats["reject"] > row["max_rejection_rate"]: reasons.append(f"rejection rate {stats['reject']:.4f} > {row['max_rejection_rate']}")
        passed=row["status"]=="PASSED"
        return ValidationSessionResult(id=row["id"],strategy_id=row["strategy_id"],strategy_version=row["strategy_version"],mode=row["mode"],status=row["status"],observation_count=stats["n"],mean_gap_bps=round(stats["gap"],8),rejection_rate=round(stats["reject"],8),passed=passed,blocking_reasons=reasons)

    def finalize_validation_session(self, session_id: str) -> ValidationSessionResult:
        current=self.get_validation_session(session_id)
        status="PASSED" if not current.blocking_reasons else "FAILED"
        with self.connect() as c:
            c.execute("UPDATE validation_sessions SET status=?, finalized_at=? WHERE id=?",(status,now(),session_id))
            self._audit(c,"VALIDATION_FINALIZED","validation_session",session_id,{"status":status,"blocking_reasons":current.blocking_reasons})
        return self.get_validation_session(session_id)

    def save_certification(self, request: CertificationRequest, response: CertificationResponse) -> str:
        cid=str(uuid.uuid4()); created=now()
        with self.connect() as c:
            strategy=c.execute("SELECT 1 FROM strategies WHERE id=?",(request.strategy_id,)).fetchone()
            version=c.execute("SELECT 1 FROM strategy_versions WHERE strategy_id=? AND version=?",(request.strategy_id,request.strategy_version)).fetchone()
            if not strategy: raise KeyError("strategy not found")
            if not version: raise KeyError("strategy version not found")
            c.execute("INSERT INTO certifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(
                cid,request.strategy_id,request.strategy_version,response.policy_version,response.decision,
                response.status.value,int(response.ready_for_live),response.score,response.evidence_set_hash,
                json.dumps(response.blocking_reasons),response.model_dump_json(),created))
            c.execute("UPDATE strategies SET status=? WHERE id=?",(response.status.value,request.strategy_id))
            self._audit(c,"CERTIFICATION_EVALUATED","strategy",request.strategy_id,{"certification_id":cid,"decision":response.decision,"evidence_set_hash":response.evidence_set_hash})
        return cid

    def readiness(self, strategy_id: str) -> ReadinessResponse:
        with self.connect() as c:
            strategy=c.execute("SELECT status FROM strategies WHERE id=?",(strategy_id,)).fetchone()
            if not strategy: raise KeyError("strategy not found")
            row=c.execute("SELECT * FROM certifications WHERE strategy_id=? ORDER BY created_at DESC LIMIT 1",(strategy_id,)).fetchone()
        if not row:
            return ReadinessResponse(strategy_id=strategy_id,status=strategy["status"],ready_for_live=False,blocking_evidence=["No persisted certification found"])
        return ReadinessResponse(strategy_id=strategy_id,strategy_version=row["strategy_version"],status=row["status"],ready_for_live=bool(row["ready_for_live"]),score=row["score"],blocking_evidence=json.loads(row["blocking_reasons"]),certification_id=row["id"],evaluated_at=row["created_at"])

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class StrategyStatus(str, Enum):
    DRAFT = "DRAFT"
    RESEARCH = "RESEARCH"
    BACKTESTING = "BACKTESTING"
    BACKTEST_VALIDATED = "BACKTEST_VALIDATED"
    OOS_VALIDATED = "OOS_VALIDATED"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    SHADOW_VALIDATED = "SHADOW_VALIDATED"
    CERTIFIED = "CERTIFIED"
    READY_FOR_LIVE = "READY_FOR_LIVE"
    LIVE = "LIVE"
    SUSPENDED = "SUSPENDED"
    DECERTIFIED = "DECERTIFIED"


class ProjectCreate(BaseModel):
    owner_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    visibility: str = "private"


class Project(BaseModel):
    id: str
    owner_id: str
    name: str
    visibility: str
    created_at: str


class StrategyCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    market: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)


class Strategy(BaseModel):
    id: str
    project_id: str
    name: str
    thesis: str
    market: str
    venue: str
    timeframe: str
    status: StrategyStatus
    created_at: str


class StrategyVersionCreate(BaseModel):
    version: str = Field(min_length=1)
    code_hash: str = Field(min_length=16)
    config_hash: str = Field(min_length=16)
    parent_id: str | None = None


class StrategyVersion(BaseModel):
    id: str
    strategy_id: str
    version: str
    code_hash: str
    config_hash: str
    parent_id: str | None
    created_at: str


class DatasetCreate(BaseModel):
    source: str
    range_start: str
    range_end: str
    schema_hash: str = Field(min_length=16)
    content_hash: str = Field(min_length=16)
    quality: dict[str, Any] = Field(default_factory=dict)


class DatasetVersion(DatasetCreate):
    id: str
    created_at: str


class TradeObservation(BaseModel):
    pnl_gross: float
    fees: float = Field(ge=0)
    slippage: float = Field(ge=0)
    planned_risk: float = Field(gt=0)
    planned_reward: float = Field(gt=0)


class RunCreate(BaseModel):
    strategy_id: str
    strategy_version: str
    dataset_version_id: str
    runner_version: str = "builtin-trade-metrics-v1"
    parameters: dict[str, Any] = Field(default_factory=dict)
    seed: int = 0
    trades: list[TradeObservation] = Field(min_length=1)


class RunResult(BaseModel):
    id: str
    status: str
    manifest_hash: str
    result_hash: str
    metrics: dict[str, float | int]
    reproducible: bool
    created_at: str
    completed_at: str


class Evidence(BaseModel):
    definition_complete: bool
    dataset_provenance_verified: bool
    reproducible: bool
    oos_validated: bool
    walk_forward_validated: bool
    paper_validated: bool
    shadow_validated: bool
    security_controls_validated: bool
    rr_planned: float = Field(gt=0)
    profit_factor_net: float = Field(ge=0)
    expectancy_net: float
    sample_size: int = Field(gt=0)
    max_drawdown_pct: float = Field(ge=0)
    shadow_execution_gap_bps: float = Field(ge=0)
    code_hash: str = Field(min_length=16)
    dataset_hash: str = Field(min_length=16)
    manifest_hash: str = Field(min_length=16)


class CertificationRequest(BaseModel):
    project_id: str
    strategy_id: str
    strategy_version: str
    policy_version: str = "mos-hub-v1"
    evidence: Evidence


class GateResult(BaseModel):
    gate: str
    passed: bool
    severity: str
    observed: Any
    required: str


class CertificationResponse(BaseModel):
    decision: str
    status: StrategyStatus
    ready_for_live: bool
    score: float
    blocking_reasons: list[str]
    gates: list[GateResult]
    policy_version: str
    evidence_set_hash: str
    warning: str = "Certification technique, sans garantie de rentabilité. Activation humaine obligatoire."


class ReadinessResponse(BaseModel):
    strategy_id: str
    strategy_version: str | None = None
    status: str
    ready_for_live: bool
    score: float | None = None
    blocking_evidence: list[str]
    certification_id: str | None = None
    evaluated_at: str | None = None

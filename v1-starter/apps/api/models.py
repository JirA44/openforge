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


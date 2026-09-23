"""Pydantic schemas for the pre-trade AI Research Desk committee.

A full 6-analyst pre-trade research desk runs before any BUY/SELL suggestion is
surfaced. Each analyst produces an :class:`AnalystVerdict`; the deterministic
Committee consensus engine aggregates them into a :class:`CommitteeDecision`.
Streams are produced in backend/ai/system prompt as structured JSON.
"""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


Side = Literal["BUY", "SELL", "HOLD"]


class AnalystVerdict(BaseModel):
    """Structured opinion of a single pre-trade analyst."""

    analyst_role: str = Field(description="e.g. TECHNICAL_TREND, RISK_EXECUTION")
    side: Side
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0-1 in this analyst's side")
    top_factor: str = ""
    supporting_factors: List[str] = []
    risk_flags: List[str] = []
    rationale: str = ""
    weight: float = Field(default=1.0, ge=0.0, description="Voting weight in the committee")
    veto: bool = Field(default=False, description="Risk analyst veto: forces committee to HOLD")
    provider: Optional[str] = None
    model: Optional[str] = None


class CommitteeDecision(BaseModel):
    """Deterministic consensus output of the 6-analyst committee."""

    verdict: Side
    overall_confidence: float = Field(ge=0.0, le=1.0)
    num_agree: int = Field(default=0, description="Analysts agreeing with the final verdict")
    total_analysts: int = Field(default=6)
    risk_vetoed: bool = False
    reasons: List[str] = []
    symbol: Optional[str] = None
    timeframe: Optional[str] = "5m"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
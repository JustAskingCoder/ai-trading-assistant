"""Pydantic schemas for AI market setup analysis."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal


class EntryZone(BaseModel):
    min: float
    max: float


class AIAnalysisRequest(BaseModel):
    symbol: str
    timeframe: str = "5m"
    price: float
    trend: str = "neutral"
    indicators: Dict[str, Optional[float]]
    patterns: List[Dict[str, Any]] = []
    strategy_signal: Optional[str] = None
    strategy_reason: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the analysis (NOT probability of profit)")
    setup: str
    entry_zone: EntryZone
    stop_loss: float
    target: float
    risk_reward: float
    timeframe: str
    supporting_factors: List[str] = []
    risk_factors: List[str] = []
    invalidation_conditions: List[str] = []
    provider: Optional[str] = None
    model: Optional[str] = None

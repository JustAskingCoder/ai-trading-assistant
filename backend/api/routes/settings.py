"""System settings and status API routes."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.core.config import settings

router = APIRouter(prefix="/api", tags=["Settings"])


class SettingsUpdate(BaseModel):
    initial_capital: Optional[float] = None
    max_investment_per_trade: Optional[float] = None
    risk_per_trade: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_open_positions: Optional[int] = None
    min_risk_reward: Optional[float] = None
    min_ai_confidence: Optional[float] = None
    default_ai_provider: Optional[str] = None
    default_ai_model: Optional[str] = None


@router.get("/settings")
def get_settings():
    return {
        "trading_mode": settings.TRADING_MODE,
        "initial_capital": settings.INITIAL_CAPITAL,
        "max_investment_per_trade": getattr(settings, "MAX_INVESTMENT_PER_TRADE", 5000.0),
        "risk_per_trade": settings.RISK_PER_TRADE,
        "max_daily_loss": settings.MAX_DAILY_LOSS,
        "max_open_positions": settings.MAX_OPEN_POSITIONS,
        "min_risk_reward": settings.MIN_RISK_REWARD,
        "min_ai_confidence": settings.MIN_AI_CONFIDENCE,
        "default_timeframe": settings.DEFAULT_TIMEFRAME,
        "default_ai_provider": settings.DEFAULT_AI_PROVIDER,
        "default_ai_model": settings.DEFAULT_AI_MODEL,
        "database_url": settings.DATABASE_URL
    }


@router.put("/settings")
def update_settings(payload: SettingsUpdate):
    if payload.initial_capital is not None:
        settings.INITIAL_CAPITAL = payload.initial_capital
    if payload.max_investment_per_trade is not None:
        settings.MAX_INVESTMENT_PER_TRADE = payload.max_investment_per_trade
    if payload.risk_per_trade is not None:
        settings.RISK_PER_TRADE = payload.risk_per_trade
    if payload.max_daily_loss is not None:
        settings.MAX_DAILY_LOSS = payload.max_daily_loss
    if payload.max_open_positions is not None:
        settings.MAX_OPEN_POSITIONS = payload.max_open_positions
    if payload.min_risk_reward is not None:
        settings.MIN_RISK_REWARD = payload.min_risk_reward
    if payload.min_ai_confidence is not None:
        settings.MIN_AI_CONFIDENCE = payload.min_ai_confidence
    if payload.default_ai_provider is not None:
        settings.DEFAULT_AI_PROVIDER = payload.default_ai_provider
    if payload.default_ai_model is not None:
        settings.DEFAULT_AI_MODEL = payload.default_ai_model

    return {"status": "updated", "settings": get_settings()}

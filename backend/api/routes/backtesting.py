"""Backtesting API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
from backend.database.session import get_db
from backend.database.models import Instrument, Candle
from backend.backtesting.engine import run_backtest
from backend.strategies.base_strategy import BreakoutStrategy, MomentumStrategy, TrendFollowingStrategy

router = APIRouter(prefix="/api", tags=["Backtesting"])


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = "MomentumStrategy"  # MomentumStrategy, BreakoutStrategy, TrendFollowingStrategy
    initial_capital: float = 100000.0
    risk_percentage: float = 0.005


@router.post("/backtest")
def execute_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    instrument = db.query(Instrument).filter(Instrument.symbol == req.symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument '{req.symbol}' not found.")

    candles = db.query(Candle).filter(
        Candle.instrument_id == instrument.id
    ).order_by(Candle.timestamp.asc()).all()

    if len(candles) < 35:
        raise HTTPException(status_code=400, detail="Insufficient candles for backtest (minimum 35 required).")

    df = pd.DataFrame([{
        "timestamp": c.timestamp.isoformat(),
        "symbol": req.symbol,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume
    } for c in candles])

    strat_map = {
        "BreakoutStrategy": BreakoutStrategy(),
        "MomentumStrategy": MomentumStrategy(),
        "TrendFollowingStrategy": TrendFollowingStrategy()
    }
    strategy = strat_map.get(req.strategy, MomentumStrategy())

    result = run_backtest(
        df=df,
        strategy=strategy,
        initial_capital=req.initial_capital,
        risk_percentage=req.risk_percentage
    )
    return result

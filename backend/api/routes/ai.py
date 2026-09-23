"""AI Market Analysis API routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from backend.database.session import get_db
from backend.database.models import AIAnalysis, Signal
from backend.ai.schemas import AIAnalysisRequest, AIAnalysisResponse
from backend.ai.analyst_schemas import AnalystVerdict, CommitteeDecision
from backend.ai.base_provider import get_ai_provider
from backend.ai.committee_service import committee_service
from backend.core.logging import logger

router = APIRouter(prefix="/api", tags=["AI Analysis"])


class CommitteeRequest(BaseModel):
    symbol: str
    timeframe: str = "5m"
    provider: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class CommitteeResponse(BaseModel):
    decision: CommitteeDecision
    analyst_verdicts: List[AnalystVerdict]
    session_id: Optional[int] = None


@router.post("/ai/analyze", response_model=AIAnalysisResponse)
async def analyze_market_setup(
    req: AIAnalysisRequest,
    provider: Optional[str] = None,
    signal_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        ai_provider = get_ai_provider(provider)
        data = req.model_dump()

        result = await ai_provider.analyze_market_setup(data)

        # Log analysis to database
        db_log = AIAnalysis(
            signal_id=signal_id,
            provider=result.provider or ai_provider.name,
            model=result.model or ai_provider.model,
            prompt_version="1.0.0",
            input_data=data,
            response=result.model_dump(),
            signal=result.signal,
            confidence=result.confidence,
            reasoning_summary=result.setup
        )
        db.add(db_log)
        db.commit()

        return result
    except Exception as e:
        logger.error("AI Analysis route error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/history")
def get_ai_analysis_history(limit: int = 50, db: Session = Depends(get_db)):
    items = db.query(AIAnalysis).order_by(AIAnalysis.created_at.desc()).limit(limit).all()
    return [{
        "id": item.id,
        "signal_id": item.signal_id,
        "provider": item.provider,
        "model": item.model,
        "signal": item.signal,
        "confidence": item.confidence,
        "reasoning": item.reasoning_summary,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "details": item.response
    } for item in items]


@router.post("/ai/committee", response_model=CommitteeResponse)
async def run_committee(
    req: CommitteeRequest,
    db: Session = Depends(get_db),
):
    """Run the full 6-analyst pre-trade research desk for a symbol.

    Optional ``data`` carries market context (indicators, patterns, price,
    bracket stop-loss/target, sentiment, ...); otherwise a minimal context is
    constructed from the requested symbol.
    """
    try:
        context = dict(req.data or {})
        context.setdefault("symbol", req.symbol)
        context.setdefault("timeframe", req.timeframe)
        if "price" not in context:
            context["price"] = 0.0
        if "strategy_signal" not in context:
            context["strategy_signal"] = "HOLD"

        decision, verdicts, session_id = await committee_service.run_committee(
            req.symbol,
            context,
            db=db,
            persist=True,
        )
        return {
            "decision": decision,
            "analyst_verdicts": verdicts,
            "session_id": session_id,
        }
    except Exception as e:
        logger.error("Committee route error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/committee/history")
def get_committee_history(limit: int = 50, db: Session = Depends(get_db)):
    """Return recent committee sessions with full per-analyst verdicts."""
    return committee_service.list_history(limit=limit, db=db)

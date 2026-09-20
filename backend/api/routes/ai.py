"""AI Market Analysis API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from backend.database.session import get_db
from backend.database.models import AIAnalysis, Signal
from backend.ai.schemas import AIAnalysisRequest, AIAnalysisResponse
from backend.ai.base_provider import get_ai_provider
from backend.core.logging import logger

router = APIRouter(prefix="/api", tags=["AI Analysis"])


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

"""Committee orchestration: run the 6-analyst desk, persist, and gate surfaces.

``CommitteeService`` is the entry point used by the API and by the live market
service gate. It accepts a canonical data dict (quote payload, raw candles
context, or arbitrary per-symbol market data), runs the five LLM analysts plus
the deterministic Risk/Execution analyst, aggregates them via
:class:`CommitteeConsensus`, and records the run in SQLite.

``committee_gate`` is a thin, TTL-cached wrapper used by the live market
service: before a BUY/SELL surfaces to the UI it must first be approved by the
committee for the same symbol.
"""
import asyncio
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.ai.analyst_schemas import AnalystVerdict, CommitteeDecision
from backend.ai.analyst_base import build_analyst_context
from backend.ai.committee_consensus import CommitteeConsensus, RISK_ROLE
from backend.ai.technical_trend import TechnicalTrendAnalyst
from backend.ai.pattern_price_action import PatternPriceActionAnalyst
from backend.ai.volume_liquidity import VolumeLiquidityAnalyst
from backend.ai.market_structure import MarketStructureAnalyst
from backend.ai.news_sentiment import NewsSentimentAnalyst
from backend.ai.risk_execution import RiskExecutionAnalyst
from backend.core.config import settings
from backend.core.logging import logger
from backend.database.session import SessionLocal
from backend.database.models import CommitteeSession, CommitteeAnalystVerdict

ANALYST_ROLES = [
    "TECHNICAL_TREND",
    "PATTERN_PRICE_ACTION",
    "VOLUME_LIQUIDITY",
    "MARKET_STRUCTURE",
    "NEWS_SENTIMENT",
    RISK_ROLE,
]


class CommitteeService:
    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider
        self.analysts = {
            "TECHNICAL_TREND": TechnicalTrendAnalyst(),
            "PATTERN_PRICE_ACTION": PatternPriceActionAnalyst(),
            "VOLUME_LIQUIDITY": VolumeLiquidityAnalyst(),
            "MARKET_STRUCTURE": MarketStructureAnalyst(),
            "NEWS_SENTIMENT": NewsSentimentAnalyst(),
            RISK_ROLE: RiskExecutionAnalyst(),
        }
        self.consensus = CommitteeConsensus()

    async def run_committee(
        self,
        symbol: str,
        data: Dict[str, Any],
        db: Optional[Session] = None,
        persist: bool = True,
    ) -> Tuple[CommitteeDecision, List[AnalystVerdict], Optional[int]]:
        """Run the full analyst team for ``symbol`` and aggregate a decision."""
        context = build_analyst_context(data)
        if symbol:
            context["symbol"] = str(symbol).upper()

        verdicts: List[AnalystVerdict] = []
        for role, analyst in self.analysts.items():
            try:
                if role == RISK_ROLE:
                    verdict = analyst.analyze(context)
                else:
                    verdict = await analyst.analyze(context, self.provider)
                verdicts.append(verdict)
            except Exception as exc:  # pragma: no cover - defensive; never break the desk
                logger.error("Analyst %s failed for %s: %s", role, symbol, exc)
                verdicts.append(
                    AnalystVerdict(
                        analyst_role=role,
                        side="HOLD",
                        confidence=0.1,
                        top_factor="Analyst error",
                        risk_flags=[f"Analyst execution failed: {exc}"],
                        rationale="Analyst failed; recorder as abstain (HOLD).",
                        weight=self.analysts[role].weight,
                        veto=False,
                    )
                )

        decision = self.consensus.decide(
            verdicts,
            symbol=context.get("symbol"),
            timeframe=str(context.get("timeframe", settings.DEFAULT_TIMEFRAME or "5m")),
        )

        session_id: Optional[int] = None
        if persist:
            session_id = self._persist(context, verdicts, decision, db)

        return decision, verdicts, session_id

    def _persist(
        self,
        context: Dict[str, Any],
        verdicts: List[AnalystVerdict],
        decision: CommitteeDecision,
        db: Optional[Session] = None,
    ) -> Optional[int]:
        should_close = db is None
        session_db = db or SessionLocal()
        try:
            row = CommitteeSession(
                symbol=context.get("symbol", ""),
                timeframe=decision.timeframe or context.get("timeframe", "5m"),
                verdict=decision.verdict,
                overall_confidence=decision.overall_confidence,
                num_agree=decision.num_agree,
                risk_vetoed=decision.risk_vetoed,
                reasons=list(decision.reasons),
                decision=decision.model_dump(),
            )
            session_db.add(row)
            session_db.flush()

            for v in verdicts:
                session_db.add(
                    CommitteeAnalystVerdict(
                        session_id=row.id,
                        analyst_role=v.analyst_role,
                        side=v.side,
                        confidence=v.confidence,
                        top_factor=v.top_factor,
                        supporting_factors=list(v.supporting_factors),
                        risk_flags=list(v.risk_flags),
                        rationale=v.rationale,
                        weight=v.weight,
                        veto=v.veto,
                        provider=v.provider,
                        model=v.model,
                    )
                )
            session_db.commit()
            return row.id
        except Exception as exc:  # pragma: no cover - persistence must never crash the desk
            logger.error("Could not persist committee session: %s", exc)
            session_db.rollback()
            return None
        finally:
            if should_close:
                session_db.close()

    def list_history(self, limit: int = 50, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Return the most recent committee sessions with their analyst verdicts."""
        should_close = db is None
        session_db = db or SessionLocal()
        try:
            sessions = (
                session_db.query(CommitteeSession)
                .order_by(CommitteeSession.created_at.desc(), CommitteeSession.id.desc())
                .limit(max(1, int(limit)))
                .all()
            )
            out: List[Dict[str, Any]] = []
            for s in sessions:
                out.append({
                    "id": s.id,
                    "symbol": s.symbol,
                    "timeframe": s.timeframe,
                    "verdict": s.verdict,
                    "overall_confidence": s.overall_confidence,
                    "num_agree": s.num_agree,
                    "risk_vetoed": s.risk_vetoed,
                    "reasons": s.reasons or [],
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "analyst_verdicts": [
                        {
                            "analyst_role": v.analyst_role,
                            "side": v.side,
                            "confidence": v.confidence,
                            "top_factor": v.top_factor,
                            "supporting_factors": v.supporting_factors or [],
                            "risk_flags": v.risk_flags or [],
                            "rationale": v.rationale,
                            "veto": v.veto,
                            "provider": v.provider,
                            "model": v.model,
                        }
                        for v in s.analyst_verdicts
                    ],
                })
            return out
        finally:
            if should_close:
                session_db.close()

    def gate_quote_action(self, quote: Dict[str, Any], symbol: str = None) -> Dict[str, Any]:
        """Consult the committee before an actionable side is surfaced.

        Only BUY/SELL actions are gated; HOLD/WAIT pass through untouched and
        cheap. When the committee does not approve the same side, the action is
        downgraded to WAIT (signal HOLD) with the committee reasons attached.
        """
        returned = dict(quote)
        action = str(returned.get("action", returned.get("signal", "WAIT")) or "WAIT").upper()
        if action not in ("BUY", "SELL"):
            return returned

        sym = str(symbol or returned.get("symbol", "")).upper()
        decision, verdicts = self._cached_decision(sym, action, returned)

        returned["committee"] = self._decision_payload(decision, verdicts)
        approved_for_side = decision.verdict == action

        if approved_for_side:
            logger.info(
                "Committee approval %s %s (%.0f%% confidence, %d/6 agree)",
                decision.verdict, sym, decision.overall_confidence * 100, decision.num_agree,
            )
            returned["gate"] = {
                "status": "APPROVED",
                "approved": True,
                "desired_action": action,
                "verdict": decision.verdict,
            }
            return returned

        returned["action"] = "WAIT"
        returned["signal"] = "HOLD"
        returned["confidence"] = min(float(returned.get("confidence", 0.5) or 0.5), 0.45)
        veto_note = "Risk veto" if decision.risk_vetoed else "Committee"
        returned["reason"] = (
            f"Gated by {veto_note} (pre-trade research desk): committee verdict "
            f"{decision.verdict} for {sym}; {action} not approved. "
            + "; ".join(decision.reasons[:2])
        )
        returned["gate"] = {
            "status": "BLOCKED",
            "approved": False,
            "desired_action": action,
            "verdict": decision.verdict,
        }
        return returned

    def _cached_decision(
        self, symbol: str, action: str, context: Dict[str, Any]
    ) -> Tuple[CommitteeDecision, List[AnalystVerdict]]:
        cache = _gate_cache
        now = time.time()
        cache_key = f"{symbol}:{action}"
        cached = cache.get(cache_key)
        ttl = float(getattr(settings, "COMMITTEE_GATE_TTL", 120))
        if cached and (now - cached[0]) < ttl:
            return cached[1], cached[2]
        decision, verdicts, _ = _run_sync(self.run_committee(symbol, context))
        cache[cache_key] = (now, decision, verdicts)
        return decision, verdicts

    @staticmethod
    def _decision_payload(decision: CommitteeDecision, verdicts: List[AnalystVerdict]) -> Dict[str, Any]:
        return {
            "verdict": decision.verdict,
            "overall_confidence": decision.overall_confidence,
            "num_agree": decision.num_agree,
            "total_analysts": decision.total_analysts,
            "risk_vetoed": decision.risk_vetoed,
            "reasons": list(decision.reasons),
            "timestamp": decision.timestamp,
            "analysts": [
                {
                    "analyst_role": v.analyst_role,
                    "side": v.side,
                    "confidence": v.confidence,
                    "top_factor": v.top_factor,
                    "risk_flags": list(v.risk_flags),
                    "veto": v.veto,
                }
                for v in verdicts
            ],
        }


def _run_sync(coro):
    """Run a coroutine from synchronous code, tolerating a running loop."""
    try:
        asyncio.get_running_loop()
        result: Dict[str, Any] = {}

        def runner():
            result["v"] = asyncio.run(coro)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join(timeout=30)
        return result.get("v")
    except RuntimeError:
        return asyncio.run(coro)


committee_service = CommitteeService()
committee_gate = committee_service
_gate_cache: Dict[str, Tuple[float, CommitteeDecision, List[AnalystVerdict]]] = {}


def clear_committee_gate_cache() -> None:
    _gate_cache.clear()


__all__ = [
    "CommitteeService",
    "committee_service",
    "committee_gate",
    "ANALYST_ROLES",
    "clear_committee_gate_cache",
]
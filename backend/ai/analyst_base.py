"""Base class for committee analysts plus shared context helpers.

Each analyst reuses the existing ``AIProvider`` abstraction
(``backend.ai.base_provider``): when an API key is configured the provider is
consulted with a role-framed data payload and the LLM's call is validated into
an :class:`AnalystVerdict`; when no key is present the analyst falls back to a
deterministic, role-specific local heuristic so the research desk still runs.
"""
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.base_provider import get_ai_provider
from backend.core.config import settings
from backend.core.logging import logger


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _has_llm_key() -> bool:
    """True when the configured default provider has a usable API key."""
    provider = (settings.DEFAULT_AI_PROVIDER or "openai").lower()
    if provider == "claude":
        return bool(settings.ANTHROPIC_API_KEY)
    return bool(settings.OPENAI_API_KEY)


def normalize_indicators(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Normalize an arbitrary indicator bag into analyst-friendly keys."""
    indicators = data.get("indicators") if isinstance(data.get("indicators"), dict) else {}
    return {
        "rsi": _to_float(indicators.get("rsi", data.get("rsi"))),
        "ema20": _to_float(indicators.get("ema20", data.get("ema20"))),
        "ema50": _to_float(indicators.get("ema50", data.get("ema50"))),
        "vwap": _to_float(indicators.get("vwap", data.get("vwap"))),
        "atr": _to_float(indicators.get("atr", data.get("atr"))),
        "adx": _to_float(indicators.get("adx", data.get("adx"))),
        "macd": _to_float(indicators.get("macd", data.get("macd"))),
        "macd_signal": _to_float(indicators.get("macd_signal", data.get("macd_signal"))),
        "volume_sma": _to_float(indicators.get("volume_sma", data.get("volume_sma"))),
    }


def build_analyst_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a canonical context dict consumed by every analyst."""
    ctx: Dict[str, Any] = dict(data or {})
    ctx.setdefault("symbol", str(ctx.get("symbol", "")).upper())
    ctx.setdefault("price", _to_float(ctx.get("price"), 0.0))
    ctx.setdefault("change_pct", _to_float(ctx.get("change_pct", ctx.get("change_percentage")), 0.0))
    ctx.setdefault("timeframe", str(ctx.get("timeframe", settings.DEFAULT_TIMEFRAME or "5m")))
    ctx.setdefault("market", str(ctx.get("market", "NSE")).upper())
    ctx["indicators"] = normalize_indicators(ctx)

    raw_patterns = ctx.get("patterns") or []
    ctx["patterns"] = raw_patterns if isinstance(raw_patterns, list) else []

    ctx.setdefault("strategy_signal", ctx.get("signal", "HOLD"))
    if ctx["strategy_signal"] is None:
        ctx["strategy_signal"] = "HOLD"
    ctx["strategy_signal"] = str(ctx["strategy_signal"]).upper()

    strategy_reason = ctx.get("strategy_reason") or ctx.get("reason") or ""
    ctx["strategy_reason"] = strategy_reason

    stock_strategy = ctx.get("strategy") or "Unknown Strategy"
    ctx["strategy"] = str(stock_strategy)

    ctx.setdefault("market_tide", "NEUTRAL")
    ctx.setdefault("macro_trend", "NEUTRAL")
    ctx.setdefault("confluence_score", 0)
    ctx.setdefault("risk_reward", 0.0)
    ctx.setdefault("entry_price", ctx["price"])
    ctx.setdefault("stop_loss", 0.0)
    ctx.setdefault("target", 0.0)
    return ctx


def provider_payload(ctx: Dict[str, Any], analyst_role: str, focus: str) -> Dict[str, Any]:
    """Role-framed data payload handed to the shared AIProvider for the LLM path."""
    return {
        "analyst_role": analyst_role,
        "analysis_focus": focus,
        "symbol": ctx.get("symbol"),
        "price": ctx.get("price"),
        "change_pct": ctx.get("change_pct"),
        "timeframe": ctx.get("timeframe"),
        "market": ctx.get("market"),
        "indicators": ctx.get("indicators"),
        "patterns": ctx.get("patterns"),
        "strategy_signal": ctx.get("strategy_signal"),
        "strategy_reason": ctx.get("strategy_reason"),
        "strategy": ctx.get("strategy"),
        "market_tide": ctx.get("market_tide"),
        "macro_trend": ctx.get("macro_trend"),
        "confluence_score": ctx.get("confluence_score"),
        "risk_reward": ctx.get("risk_reward"),
        "entry_price": ctx.get("entry_price"),
        "stop_loss": ctx.get("stop_loss"),
        "target": ctx.get("target"),
    }


class BaseAnalyst(ABC):
    """Base pre-trade analyst.

    Subclasses provide a deterministic ``_local_heuristic`` used whenever no
    usable API key exists. The ``analyze`` flow optionally consults the shared
    AIProvider first and only falls back to the heuristic.
    """

    role: str = "ANALYST"
    focus: str = "Pre-trade market analysis"
    weight: float = 1.0

    def __init__(self) -> None:
        self.provider_name: Optional[str] = None
        self.model_name: Optional[str] = None

    @abstractmethod
    def _local_heuristic(self, ctx: Dict[str, Any]) -> AnalystVerdict:
        """Deterministic, role-specific opinion when no API key is available."""

    async def analyze(self, data: Dict[str, Any], provider: Optional[str] = None) -> AnalystVerdict:
        """Produce an AnalystVerdict for the supplied market context."""
        ctx = build_analyst_context(data)

        if _has_llm_key():
            try:
                ai = get_ai_provider(provider)
                payload = provider_payload(ctx, self.role, self.focus)
                response = await ai.analyze_market_setup(payload)
                self.provider_name = response.provider or ai.name
                self.model_name = response.model or ai.model
                verdict = self._verdict_from_llm(ctx, response)
                if verdict is not None:
                    return verdict
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("LLM analysis failed for %s (%s): %s", self.role, ctx.get("symbol"), exc)

        verdict = self._local_heuristic(ctx)
        self.provider_name = "LocalHeuristic"
        self.model_name = "heuristic-v1"
        verdict.provider = self.provider_name
        verdict.model = self.model_name
        return verdict

    def _verdict_from_llm(self, ctx: Dict[str, Any], response: Any) -> Optional[AnalystVerdict]:
        """Map a validated AIAnalysisResponse into an AnalystVerdict."""
        side = getattr(response, "signal", "HOLD")
        if side not in ("BUY", "SELL", "HOLD"):
            side = "HOLD"
        return AnalystVerdict(
            analyst_role=self.role,
            side=side,
            confidence=min(1.0, max(0.0, float(getattr(response, "confidence", 0.5)))),
            top_factor=(getattr(response, "setup", "") or ""),
            supporting_factors=list(getattr(response, "supporting_factors", []) or []),
            risk_flags=list(getattr(response, "risk_factors", []) or []),
            rationale=(getattr(response, "setup", "") or ""),
            weight=self.weight,
            veto=False,
            provider=getattr(response, "provider", None),
            model=getattr(response, "model", None),
        )

    def _default_verdict(self, ctx: Dict[str, Any], side: str, confidence: float, top_factor: str,
                         supporting: List[str], risks: List[str], rationale: str) -> AnalystVerdict:
        return AnalystVerdict(
            analyst_role=self.role,
            side=side,
            confidence=min(1.0, max(0.05, confidence)),
            top_factor=top_factor,
            supporting_factors=supporting,
            risk_flags=risks,
            rationale=rationale,
            weight=self.weight,
            veto=False,
            provider="LocalHeuristic",
            model="heuristic-v1",
        )

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"<{self.__class__.__name__} role={self.role} weight={self.weight}>"
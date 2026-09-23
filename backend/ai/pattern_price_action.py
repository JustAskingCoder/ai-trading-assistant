"""Pattern & Price-Action analyst module.

Reads the deterministic candlestick/pattern engine output (engulfing, hammer,
doji, breakout/crossover events) and weighs price-action evidence for or
against the strategy side.
"""
from typing import Any, Dict, List, Literal

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.analyst_base import BaseAnalyst


class PatternPriceActionAnalyst(BaseAnalyst):
    role = "PATTERN_PRICE_ACTION"
    focus = "Candlestick patterns, breakouts, and price-action confluence"
    weight = 1.0

    def _local_heuristic(self, ctx: Dict[str, Any]) -> AnalystVerdict:
        patterns = ctx.get("patterns") or []
        strategy_side: Literal["BUY", "SELL", "HOLD"] = ctx.get("strategy_signal", "HOLD")

        bull = [p for p in patterns if (p.get("direction") or "").upper() == "BUY"]
        bear = [p for p in patterns if (p.get("direction") or "").upper() == "SELL"]

        supporting: List[str] = []
        risks: List[str] = []

        bull_strength = sum(float(p.get("strength", 0.6)) for p in bull if p.get("strength"))
        bear_strength = sum(float(p.get("strength", 0.6)) for p in bear if p.get("strength"))

        if bull:
            supporting.append(f"Bullish price action: {', '.join(p.get('pattern', p.get('name', 'pattern')) for p in bull[:3])}")
        if bear:
            supporting.append(f"Bearish price action: {', '.join(p.get('pattern', p.get('name', 'pattern')) for p in bear[:3])}")

        if strategy_side in ("BUY", "SELL"):
            # Strongly conflicting pattern family overrides the strategy side.
            if strategy_side == "BUY" and bear_strength >= 1.5 and bear_strength > bull_strength * 2:
                return self._default_verdict(
                    ctx, "HOLD", 0.40, "Dominant bearish pattern",
                    list(supporting), ["Several bearish patterns contradict the long", *risks],
                    "Price action has stacked against the long side; stand aside."
                )
            if strategy_side == "SELL" and bull_strength >= 1.5 and bull_strength > bear_strength * 2:
                return self._default_verdict(
                    ctx, "HOLD", 0.40, "Dominant bullish pattern",
                    list(supporting), ["Several bullish patterns contradict the short", *risks],
                    "Price action has stacked against the short side; stand aside."
                )

            if strategy_side == "BUY":
                confidence = 0.62 + min(0.12, bull_strength / 8.0)
                supporting.append("Strategy BUY compatible with observed price action")
                return self._default_verdict(
                    ctx, "BUY", confidence, "Pattern support",
                    supporting or ["Price-action aligned with the long"],
                    risks or ["Patterns may whipsaw on low volume"],
                    "Candlestick structure does not contradict the bullish setup."
                )

            confidence = 0.62 + min(0.12, bear_strength / 8.0)
            supporting.append("Strategy SELL compatible with observed price action")
            return self._default_verdict(
                ctx, "SELL", confidence, "Rejection structure",
                supporting or ["Price-action aligned with the short"],
                risks or ["Patterns may whipsaw on low volume"],
                "Candlestick structure does not contradict the bearish setup."
            )

        if bull and not bear:
            hint = "Bullish"
        elif bear and not bull:
            hint = "Bearish"
        else:
            hint = "Neutral"
        return self._default_verdict(
            ctx, "HOLD", 0.52, f"Price action: {hint}",
            supporting or ["No actionable pattern cluster"],
            risks or ["Pattern noise without a trigger"],
            "No high-confidence pattern setup; waiting for a clean trigger."
        )


pattern_price_action_analyst = PatternPriceActionAnalyst()
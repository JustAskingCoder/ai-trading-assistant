"""Technical & Trend analyst module.

Evaluates the dominant price trend using EMA structure, RSI momentum and the
VWAP anchor. Reuses the AIProvider when a key exists; otherwise a deterministic
local heuristic aligned with the strategy signal drives the verdict.
"""
from typing import Any, Dict, List, Literal

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.analyst_base import BaseAnalyst


class TechnicalTrendAnalyst(BaseAnalyst):
    role = "TECHNICAL_TREND"
    focus = "Trend direction, EMA structure, RSI momentum, VWAP anchor"
    weight = 1.0

    def _local_heuristic(self, ctx: Dict[str, Any]) -> AnalystVerdict:
        ind = ctx["indicators"]
        rsi = float(ind.get("rsi") or 50.0)
        ema20 = ind.get("ema20")
        ema50 = ind.get("ema50")
        vwap = ind.get("vwap")
        price = float(ctx.get("price") or 0.0)
        strategy_side: Literal["BUY", "SELL", "HOLD"] = ctx.get("strategy_signal", "HOLD")

        supporting: List[str] = []
        risks: List[str] = []

        bullish_ema = ema20 and ema50 and ema20 > ema50
        bearish_ema = ema20 and ema50 and ema20 < ema50
        above_vwap = vwap and vwap > 0 and price > vwap
        below_vwap = vwap and vwap > 0 and price < vwap

        if bullish_ema:
            supporting.append("EMA20 trading above EMA50 (bullish trend structure)")
        if bearish_ema:
            supporting.append("EMA20 trading below EMA50 (bearish trend structure)")
        if above_vwap:
            supporting.append("Price holding above VWAP (buy-side pressure)")
        if below_vwap:
            supporting.append("Price below VWAP (sell-side pressure)")

        if rsi >= 75:
            risks.append(f"RSI {rsi:.1f} deeply overbought - chase risk elevated")
        elif rsi >= 65:
            supporting.append(f"Strong momentum (RSI {rsi:.1f})")
        elif rsi <= 30:
            risks.append(f"RSI {rsi:.1f} suggests weak momentum / oversold conditions")
        else:
            supporting.append(f"Momentum neutral (RSI {rsi:.1f})")

        # Strong contradictions that would override a directional strategy signal.
        if strategy_side in ("BUY", "SELL"):
            if strategy_side == "BUY" and (bearish_ema and below_vwap) and rsi <= 35:
                return self._default_verdict(
                    ctx, "HOLD", 0.35, "Trend structure contradicts BUY",
                    list(supporting), ["Bearish EMA structure below VWAP", *risks],
                    "Technical trend does not support a long here: EMA bearish grind below VWAP with weak RSI."
                )
            if strategy_side == "SELL" and (bullish_ema and above_vwap) and rsi >= 65:
                return self._default_verdict(
                    ctx, "HOLD", 0.35, "Trend structure contradicts SELL",
                    list(supporting), ["Bullish EMA structure above VWAP", *risks],
                    "Technical trend does not support a short here: price riding bullish EMA/VWAP structure."
                )

            if strategy_side == "BUY":
                confidence = 0.66
                if bullish_ema:
                    confidence += 0.08
                if not below_vwap:
                    confidence += 0.06
                if supporting:
                    supporting.append("Strategy BUY aligns with current technical backdrop")
                risks = risks or ["General market volatility"]
                rationale = "Bullish technical alignment; tradeable long bias with strict bracket risk."
                return self._default_verdict(ctx, "BUY", confidence, "Trend momentum", supporting, risks, rationale)

            confidence = 0.66
            if bearish_ema:
                confidence += 0.08
            if not above_vwap:
                confidence += 0.06
            supporting.append("Strategy SELL aligns with current technical backdrop")
            risks = risks or ["General market volatility"]
            rationale = "Bearish technical alignment; tradeable short bias with strict bracket risk."
            return self._default_verdict(ctx, "SELL", confidence, "Trend rejection", supporting, risks, rationale)

        # Neutral / strategy HOLD
        if bullish_ema:
            bias = "Bullish"
        elif bearish_ema:
            bias = "Bearish"
        else:
            bias = "Sideways"
        return self._default_verdict(
            ctx, "HOLD", 0.52, f"Trend: {bias}",
            supporting or ["No dominant trend signal"],
            risks or ["Consolidation may precede whipsaw"],
            "No actionable trend setup; standing aside until momentum resolves."
        )


# Backwards-friendly alias
technical_trend_analyst = TechnicalTrendAnalyst()
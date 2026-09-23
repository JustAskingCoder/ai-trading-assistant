"""Market Structure analyst module.

Assesses the macro backdrop for Indian intraday trading: Nifty tide, 15m
macro trend alignment, time-of-day session windows, and scanner confluence.
An opposed tide/macro is the strongest reason to withhold a side.
"""
from typing import Any, Dict, List, Literal

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.analyst_base import BaseAnalyst


class MarketStructureAnalyst(BaseAnalyst):
    role = "MARKET_STRUCTURE"
    focus = "Nifty market tide, macro trend alignment, session windows, confluence"
    weight = 1.0

    def _local_heuristic(self, ctx: Dict[str, Any]) -> AnalystVerdict:
        strategy_side: Literal["BUY", "SELL", "HOLD"] = ctx.get("strategy_signal", "HOLD")
        tide = str(ctx.get("market_tide", "NEUTRAL")).upper()
        macro = str(ctx.get("macro_trend", "NEUTRAL")).upper()
        confluence = int(ctx.get("confluence_score") or 0)

        supporting: List[str] = []
        risks: List[str] = []

        if tide == "BULLISH":
            supporting.append("Nifty tide bullish - favorable tape for longs")
        elif tide == "BEARISH":
            supporting.append("Nifty tide bearish - favorable tape for shorts")
        else:
            supporting.append("Nifty tide neutral")

        if macro == "BULLISH":
            supporting.append("15m macro trend aligned bullish")
        elif macro == "BEARISH":
            supporting.append("15m macro trend aligned bearish")
        else:
            supporting.append("15m macro trend unconfirmed")

        if confluence >= 2:
            supporting.append(f"High-win-rate confluence ({confluence} scanner tags)")
            risks.append("Confluence setups still require strict bracket discipline")
        elif confluence >= 1:
            supporting.append(f"Partial confluence ({confluence} scanner tag)")
        else:
            risks.append("No scanner confluence confirmation")

        time_ok = ctx.get("time_filter_ok")
        if time_ok is False:
            risks.append("Outside optimal trade session window (opening whipsaw / lunch chop)")

        if strategy_side in ("BUY", "SELL"):
            # Tide and macro are the strongest structural filters.
            if strategy_side == "BUY" and tide == "BEARISH":
                return self._default_verdict(
                    ctx, "HOLD", 0.35, "Bearish Nifty tide",
                    list(supporting), ["NIFTY bearish tape hostile to longs", *risks],
                    "Market structure (bearish tide) opposes a long; waiting for tide change."
                )
            if strategy_side == "SELL" and tide == "BULLISH":
                return self._default_verdict(
                    ctx, "HOLD", 0.35, "Bullish Nifty tide",
                    list(supporting), ["NIFTY bullish tape hostile to shorts", *risks],
                    "Market structure (bullish tide) opposes a short; waiting for tide change."
                )
            if strategy_side == "BUY" and macro == "BEARISH":
                return self._default_verdict(
                    ctx, "HOLD", 0.40, "Bearish 15m macro",
                    list(supporting), ["Higher timeframe below EMA50 opposes long", *risks],
                    "Macro trend filter (15m) blocks the long."
                )
            if strategy_side == "SELL" and macro == "BULLISH":
                return self._default_verdict(
                    ctx, "HOLD", 0.40, "Bullish 15m macro",
                    list(supporting), ["Higher timeframe above EMA50 opposes short", *risks],
                    "Macro trend filter (15m) blocks the short."
                )

            if time_ok is False:
                return self._default_verdict(
                    ctx, "HOLD", 0.40, "Poor session timing",
                    list(supporting), [*risks, "Opening whipsaw / lunch chop window"],
                    "Time-of-day filter blocks the side."
                )

            if strategy_side == "BUY":
                confidence = 0.60
                if tidy := (tide == "BULLISH"):
                    confidence += 0.10
                if macro == "BULLISH":
                    confidence += 0.08
                supporting.append("Tide/macro do not oppose the long")
                if tidy:
                    supporting.append(f"NIFTY tide ({tide}) confirms long bias")
                return self._default_verdict(
                    ctx, "BUY", confidence, "Structural alignment",
                    supporting or ["Structure neutral"],
                    risks or ["Structure can shift intraday"],
                    "Market structure supports the long; no opposing tide or macro filter."
                )

            confidence = 0.60
            if tide == "BEARISH":
                confidence += 0.10
            if macro == "BEARISH":
                confidence += 0.08
            supporting.append("Tide/macro do not oppose the short")
            return self._default_verdict(
                ctx, "SELL", confidence, "Structural rejection",
                supporting or ["Structure neutral"],
                risks or ["Structure can shift intraday"],
                "Market structure supports the short; no opposing tide or macro filter."
            )

        if tide in ("BULLISH", "BEARISH") or macro in ("BULLISH", "BEARISH"):
            hint = f"Tide {tide} / Macro {macro}"
        else:
            hint = "Range tape"
        return self._default_verdict(
            ctx, "HOLD", 0.52, f"Market structure: {hint}",
            supporting,
            risks or ["Tape neutral"],
            "No structural catalyst; holding cash."
        )


market_structure_analyst = MarketStructureAnalyst()
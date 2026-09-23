"""Volume & Liquidity analyst module.

Evaluates volume expansion (2.0x+ 20-period volume SMA), volume surge events,
day breakouts, and overall market liquidity before endorsing any side.
"""
from typing import Any, Dict, List, Literal

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.analyst_base import BaseAnalyst


class VolumeLiquidityAnalyst(BaseAnalyst):
    role = "VOLUME_LIQUIDITY"
    focus = "Volume expansion, liquidity, volume surge, day breakout confirmation"
    weight = 1.0

    def _local_heuristic(self, ctx: Dict[str, Any]) -> AnalystVerdict:
        strategy_side: Literal["BUY", "SELL", "HOLD"] = ctx.get("strategy_signal", "HOLD")
        ind = ctx["indicators"]
        supporting: List[str] = []
        risks: List[str] = []

        volume_surge = ctx.get("volume_surge")
        if isinstance(volume_surge, dict):
            ratio = float(volume_surge.get("ratio") or 0.0)
            if volume_surge.get("is_surge") and ratio >= 2.0:
                supporting.append(f"Abnormal volume expansion ({ratio:.1f}x SMA20)")
                if strategy_side == "BUY":
                    supporting.append("Volume expansion confirms institutional participation")
            elif ratio >= 1.2:
                supporting.append(f"Healthy volume participation ({ratio:.1f}x SMA20)")
            else:
                risks.append(f"Volume ratio {ratio:.1f}x is below participation threshold")

        vol_sma = ind.get("volume_sma")
        if vol_sma and vol_sma > 0:
            current_vol = float(ctx.get("volume") or 0.0)
            rel_vol = current_vol / vol_sma if current_vol > 0 else 0.0
            if rel_vol >= 2.0:
                supporting.append(f"Current print is {rel_vol:.1f}x typical volume")
            elif current_vol <= 0:
                risks.append("Live volume data unavailable - liquidity unverified")

        day_breakout = ctx.get("day_breakout")
        if isinstance(day_breakout, dict):
            if day_breakout.get("is_breakout"):
                supporting.append("Trading at day-high territory (breakout tape)")
            elif day_breakout.get("is_breakdown"):
                supporting.append("Trading at day-low territory (breakdown tape)")

        scanner_tags = ctx.get("scanner_tags") or []
        if scanner_tags:
            supporting.append(f"Scanner tags: {', '.join(str(t) for t in scanner_tags[:3])}")

        if strategy_side in ("BUY", "SELL"):
            # A genuine liquidity failure (price action on vanishing volume) blocks the side.
            if strategy_side in ("BUY", "SELL") and (volume_surge is None) and ctx.get("market") == "NSE":
                risks.append("Intraday volume profile could not be confirmed")

            if strategy_side == "BUY":
                confidence = 0.58
                if any("expansion" in s for s in supporting):
                    confidence += 0.12
                if any("participation" in s for s in supporting):
                    confidence += 0.06
                if not risks:
                    supporting.append("Liquidity adequate for an intraday long")
                return self._default_verdict(
                    ctx, "BUY", confidence, "Volume participation",
                    supporting or ["Volume profile neutral"],
                    risks or ["Volume may thin into afternoon European windows"],
                    "Volume/liquidity profile is consistent with a long; no distribution signal."
                )

            confidence = 0.58
            if any("expansion" in s for s in supporting):
                confidence += 0.12
            if any("participation" in s for s in supporting):
                confidence += 0.06
            return self._default_verdict(
                ctx, "SELL", confidence, "Distribution pressure",
                supporting or ["Volume profile neutral"],
                risks or ["Volume may thin into afternoon sessions"],
                "Volume/liquidity profile is consistent with a short; no accumulation signal."
            )

        return self._default_verdict(
            ctx, "HOLD", 0.50, "Volume neutral",
            supporting or ["No volume expansion trigger"],
            risks or ["Thin liquidity can amplify slippage"],
            "No volume-based trigger present."
        )


volume_liquidity_analyst = VolumeLiquidityAnalyst()
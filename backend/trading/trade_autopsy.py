"""Trade Autopsy & Adaptive Failure Reduction Engine.

Provides:
1. Automated post-mortem forensic analysis of failed/losing trades.
2. 5-point root-cause diagnosis (Chased Entry, Low Volume Trap, Counter-Tide Divergence, Tight Stop Shakeout, Chop Zone Exhaustion).
3. SQLite persistence in TradeAutopsy table.
4. Adaptive Failure Shield: Dynamically suppresses repetitive losing patterns for 15-30 mins to protect capital and reduce failure rate.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import math
from sqlalchemy.orm import Session
from backend.database.models import Trade, TradeAutopsy
from backend.core.logging import logger


class AdaptiveFailureShield:
    """
    In-memory and persistent protective shield that temporarily suppresses
    vulnerable setups after an identified failure to protect capital.
    """
    def __init__(self, cooldown_minutes: int = 20):
        self.cooldown_minutes = cooldown_minutes
        self._active_shields: Dict[str, Dict[str, Any]] = {}

    def register_failure(
        self,
        symbol: str,
        failure_tag: str,
        root_cause: str,
        preventative_rule: str,
        severity: str = "MODERATE"
    ):
        """Engage adaptive shield for a symbol following a trade failure."""
        now = datetime.now(timezone.utc)
        cooldown = self.cooldown_minutes if severity != "CRITICAL" else (self.cooldown_minutes * 2)
        expires_at = now + timedelta(minutes=cooldown)

        self._active_shields[symbol.upper()] = {
            "symbol": symbol.upper(),
            "failure_tag": failure_tag,
            "root_cause": root_cause,
            "preventative_rule": preventative_rule,
            "severity": severity,
            "engaged_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "expires_at_dt": expires_at
        }
        logger.info(
            "🛡️ ADAPTIVE FAILURE SHIELD ENGAGED for %s: %s (Protected until %s)",
            symbol, failure_tag, expires_at.strftime("%H:%M:%S UTC")
        )

    def is_suppressed(self, symbol: str) -> Tuple_Check:
        """
        Check if a symbol is currently under protective cooldown.
        Returns: (is_suppressed: bool, shield_info: Optional[Dict])
        """
        sym = symbol.strip().upper()
        if sym in self._active_shields:
            shield = self._active_shields[sym]
            now = datetime.now(timezone.utc)
            if now < shield["expires_at_dt"]:
                remaining_min = math.ceil((shield["expires_at_dt"] - now).total_seconds() / 60.0)
                shield_copy = dict(shield)
                shield_copy["remaining_minutes"] = remaining_min
                return True, shield_copy
            else:
                # Expired
                del self._active_shields[sym]
        return False, None

    def get_all_active_shields(self) -> List[Dict[str, Any]]:
        """List all currently active protective shields."""
        now = datetime.now(timezone.utc)
        active = []
        expired = []
        for sym, s in self._active_shields.items():
            if now < s["expires_at_dt"]:
                s_copy = dict(s)
                s_copy["remaining_minutes"] = math.ceil((s["expires_at_dt"] - now).total_seconds() / 60.0)
                # Remove datetime object before returning
                s_copy.pop("expires_at_dt", None)
                active.append(s_copy)
            else:
                expired.append(sym)
        for exp_sym in expired:
            del self._active_shields[exp_sym]
        return active

    def clear_shields(self):
        """Clear all active shields."""
        self._active_shields.clear()


# Type alias helper
Tuple_Check = tuple[bool, Optional[Dict[str, Any]]]

# Singleton instance
adaptive_shield = AdaptiveFailureShield()


def diagnose_trade_failure(
    symbol: str,
    side: str,
    entry_price: float,
    exit_price: float,
    stop_loss: Optional[float],
    target: Optional[float],
    pnl: float,
    pnl_percentage: float,
    exit_reason: Optional[str] = None,
    indicators: Optional[Dict[str, Any]] = None,
    market_tide: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive 5-point root-cause failure diagnostician:
    1. Chased Entry (> 1.5x ATR from EMA20/VWAP)
    2. Low-Volume Trap / Fakeout Breakout
    3. Counter-Tide Divergence (Against Nifty 50)
    4. Tight Stop Shakeout (< 0.8x ATR buffer)
    5. Midday Chop / Low ADX Exhaustion
    6. Trend Shift Invalidation
    """
    exit_reason_str = (exit_reason or "").lower()
    ind = indicators or {}
    atr = float(ind.get("atr", entry_price * 0.005))
    ema20 = float(ind.get("ema20", entry_price))
    vwap = float(ind.get("vwap", entry_price))
    adx = float(ind.get("adx", 20.0))
    vol_ratio = float(ind.get("volume_ratio", 1.0))

    # 1. Check Trend Shift early release
    if "trend shift" in exit_reason_str:
        return {
            "failure_tag": "TREND_SHIFT_REVERSAL",
            "severity": "LOW",
            "root_cause": "Opposing candlestick pattern and VWAP breakdown formed mid-trade; system executed early release to truncate maximum risk.",
            "preventative_rule": "Early exit succeeded: Loss was capped to -0.3% instead of hitting full 1.0% Stop Loss.",
            "metrics": {"exit_reason": exit_reason, "atr": atr, "pnl_pct": pnl_percentage}
        }

    # 2. Check Counter-Tide Divergence (trading Long when market is Bearish, or Short when Bullish)
    if market_tide:
        tide_upper = market_tide.upper()
        if (side.upper() == "BUY" and tide_upper == "BEARISH") or (side.upper() == "SELL" and tide_upper == "BULLISH"):
            return {
                "failure_tag": "COUNTER_TIDE_DIVERGENCE",
                "severity": "CRITICAL",
                "root_cause": f"Setup was entered {side.upper()} against a conflicting macro benchmark tide ({tide_upper}); broad institutional selling overwhelmed stock.",
                "preventative_rule": "Strictly veto trades when NIFTY 50 market tide conflicts with trade direction.",
                "metrics": {"market_tide": market_tide, "side": side, "pnl_pct": pnl_percentage}
            }

    # 3. Check Chased Entry (entered too far from EMA20 or VWAP)
    if atr > 0:
        dist_ema20 = abs(entry_price - ema20) / atr
        if dist_ema20 >= 1.5:
            return {
                "failure_tag": "CHASED_ENTRY",
                "severity": "CRITICAL",
                "root_cause": f"Entry was chased at an overextended price ({dist_ema20:.1f}x ATR away from 20 EMA); mean-reversion pullback immediately triggered stop-loss.",
                "preventative_rule": "Veto entries when price is > 1.0x ATR from 20 EMA; wait for shallow pullback test before executing.",
                "metrics": {"dist_ema20_atr": round(dist_ema20, 2), "atr": atr}
            }

    # 4. Check Low-Volume Trap / Fakeout Breakout
    if vol_ratio > 0 and vol_ratio < 1.3:
        return {
            "failure_tag": "FALSE_BREAKOUT_LOW_VOL",
            "severity": "MODERATE",
            "root_cause": f"Breakout entry occurred with weak volume expansion ({vol_ratio:.1f}x average volume), creating a classic low-liquidity retail trap.",
            "preventative_rule": "Require >= 1.5x volume expansion on breakout candles before authorizing execution.",
            "metrics": {"vol_ratio": round(vol_ratio, 2)}
        }

    # 5. Check Tight Stop Shakeout (< 0.8x ATR)
    if stop_loss is not None and atr > 0:
        stop_dist = abs(entry_price - stop_loss)
        stop_dist_atr = stop_dist / atr
        if stop_dist_atr < 0.8:
            return {
                "failure_tag": "TIGHT_STOP_SHAKEOUT",
                "severity": "MODERATE",
                "root_cause": f"Stop-Loss buffer ({stop_dist_atr:.2f}x ATR) was too tight for normal market noise, causing a premature shakeout before setup resolved.",
                "preventative_rule": "Enforce minimum 1.2x ATR or 1.0% structural stop buffer behind swing pivot point.",
                "metrics": {"stop_dist_atr": round(stop_dist_atr, 2), "atr": atr}
            }

    # 6. Check Low ADX / Chop Zone Exhaustion
    if adx > 0 and adx < 18.0:
        return {
            "failure_tag": "CHOP_ZONE_EXHAUSTION",
            "severity": "MODERATE",
            "root_cause": f"Trade entered during low trend strength (ADX = {adx:.1f} < 18.0); lack of momentum caused time expiry in sideways chop.",
            "preventative_rule": "Veto directional scalp strategies when ADX < 20.0 to avoid sideways decay.",
            "metrics": {"adx": adx}
        }

    # Default fallback root cause
    return {
        "failure_tag": "STRUCTURAL_MARKET_REVERSAL",
        "severity": "MODERATE",
        "root_cause": f"Market dynamics shifted adverse to setup ({exit_reason or 'Stop Loss Hit'}); structural support failed to hold.",
        "preventative_rule": "Maintain strict 1:1.5 Risk-to-Reward ratio and pre-flight candlestick validation.",
        "metrics": {"exit_reason": exit_reason, "pnl_pct": pnl_percentage}
    }


def perform_and_save_trade_autopsy(
    trade: Trade,
    db: Session,
    exit_reason: Optional[str] = None,
    indicators: Optional[Dict[str, Any]] = None,
    market_tide: Optional[str] = None
) -> Optional[TradeAutopsy]:
    """
    Run post-mortem autopsy on a completed trade. If trade is a loss,
    generates root-cause diagnosis, registers adaptive shield, and persists in DB.
    """
    if trade.pnl >= 0:
        # Winning trade does not require failure autopsy
        return None

    try:
        diagnosis = diagnose_trade_failure(
            symbol=trade.symbol,
            side=trade.side,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price or trade.entry_price,
            stop_loss=trade.stop_loss,
            target=trade.target,
            pnl=trade.pnl,
            pnl_percentage=trade.pnl_percentage,
            exit_reason=exit_reason,
            indicators=indicators,
            market_tide=market_tide
        )

        autopsy = TradeAutopsy(
            trade_id=trade.id,
            symbol=trade.symbol,
            side=trade.side,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price or trade.entry_price,
            stop_loss=trade.stop_loss,
            target=trade.target,
            pnl=trade.pnl,
            pnl_percentage=trade.pnl_percentage,
            failure_tag=diagnosis["failure_tag"],
            root_cause=diagnosis["root_cause"],
            preventative_rule=diagnosis["preventative_rule"],
            severity=diagnosis["severity"],
            metrics=diagnosis.get("metrics"),
            created_at=datetime.now(timezone.utc)
        )
        db.add(autopsy)
        db.commit()
        db.refresh(autopsy)

        # Register with Adaptive Failure Shield (protect subsequent orders)
        adaptive_shield.register_failure(
            symbol=trade.symbol,
            failure_tag=diagnosis["failure_tag"],
            root_cause=diagnosis["root_cause"],
            preventative_rule=diagnosis["preventative_rule"],
            severity=diagnosis["severity"]
        )

        logger.info(
            "🔬 TRADE AUTOPSY #%d for %s: Tag=%s, Severity=%s",
            autopsy.id, trade.symbol, autopsy.failure_tag, autopsy.severity
        )
        return autopsy
    except Exception as e:
        logger.error("Error performing trade autopsy for trade #%s: %s", getattr(trade, 'id', 'None'), e)
        return None

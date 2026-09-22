"""Base Strategy interface and concrete strategy implementations."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
from backend.patterns.engine import detect_all_patterns


class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, idx: int = -1) -> Optional[Dict[str, Any]]:
        """Evaluate market data at candle idx and return signal or None."""
        pass


def get_precision_for_symbol(symbol: str, price: float = 0.0) -> int:
    """Determine decimal precision: 4 for Forex/micro-pairs, 2 for Equities/Gold/Crypto."""
    clean = str(symbol).upper().replace("/", "").replace(" ", "").replace("_", "")
    if clean in ["BTCUSD", "BTC-USD", "BTC", "ETHUSD", "GOLD", "GC=F"]:
        return 2
    if any(fx in clean for fx in ["USD", "EUR", "GBP", "JPY", "INR", "AUD", "CHF", "CAD", "=X"]) and not clean.endswith(".NS"):
        if clean in ["JPY", "USDJPY", "JPY=X"]:
            return 2
        return 4
    if 0.0 < price < 20.0:
        return 4
    return 2


def validate_pattern_alignment(patterns: list, proposed_side: str) -> tuple[bool, float, str]:
    """
    Validates that detected price action and technical patterns do not conflict with proposed trade direction,
    and identifies confirming patterns to boost confidence.
    Returns: (is_approved: bool, confidence_delta: float, pattern_annotation: str)
    """
    conf_delta = 0.0
    confirming = []
    conflicting = []

    # Severe candlestick reversals & structural breaks that strictly veto opposite trades
    # Bull traps for BUY: shooting_star, bearish_engulfing, support_breakdown, vwap_cross_below
    # Bear traps for SELL: hammer, bullish_engulfing, resistance_breakout, vwap_cross_above
    severe_bearish_vetos = {"shooting_star", "bearish_engulfing", "support_breakdown", "vwap_cross_below"}
    severe_bullish_vetos = {"hammer", "bullish_engulfing", "resistance_breakout", "vwap_cross_above"}

    for p in patterns:
        p_name = p.get("pattern", "")
        p_label = p_name.replace("_", " ").title()
        p_dir = p.get("direction", "NEUTRAL")

        if proposed_side == "BUY":
            if p_name in severe_bearish_vetos:
                conflicting.append(p_label)
            elif p_dir == "BUY":
                confirming.append(p_label)
        elif proposed_side == "SELL":
            if p_name in severe_bullish_vetos:
                conflicting.append(p_label)
            elif p_dir == "SELL":
                confirming.append(p_label)

    # Strict Veto: If severe opposing candlestick or structural pattern is detected, reject setup
    if conflicting:
        return False, -0.20, f"Vetoed by opposing pattern ({', '.join(conflicting)})"

    if confirming:
        conf_delta = min(0.10, len(confirming) * 0.04)
        return True, conf_delta, f"Confirmed by {', '.join(confirming)} pattern"

    return True, 0.0, ""


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy:
    BUY when:
    - Price breaks 20-period resistance (close > resistance, prev_close <= resistance)
    - Volume > 1.2x Volume SMA (or ATR range expansion for Forex OTC)
    - EMA20 > EMA50
    - RSI between 48 and 68 (prevent buying overbought)
    - Price within 1.2% of EMA20
    SELL when:
    - Price breaks 20-period support (close < support, prev_close >= support)
    - Volume > 1.2x Volume SMA (or ATR range expansion for Forex OTC)
    - EMA20 < EMA50
    - RSI between 32 and 52 (prevent shorting oversold)
    - Price within 1.2% of EMA20
    """
    def __init__(self):
        super().__init__("BreakoutStrategy")

    def evaluate(self, df: pd.DataFrame, idx: int = -1) -> Optional[Dict[str, Any]]:
        if len(df) < 25:
            return None

        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        close = curr["close"]
        prev_close = prev["close"]
        sym_str = str(curr.get("symbol", "UNKNOWN"))
        dec = get_precision_for_symbol(sym_str, close)
        is_forex = (dec == 4)

        # Window for resistance / support
        window = df.iloc[max(0, idx - 21):idx]
        resistance = window["high"].max()
        support = window["low"].min()

        vol = curr.get("volume", 0)
        vol_sma = curr.get("volume_sma", 1) or 1
        ema20 = curr.get("ema20")
        ema50 = curr.get("ema50")
        rsi = curr.get("rsi")
        adx = curr.get("adx")
        atr = curr.get("atr")
        if atr is None or pd.isna(atr) or atr <= 0:
            atr = close * 0.005

        near_ema20 = (
            ema20 is not None and pd.notnull(ema20) and
            abs(close - ema20) / ema20 <= 0.012
        )

        c_open, c_high, c_low = curr["open"], curr["high"], curr["low"]
        c_range = c_high - c_low
        c_body = abs(close - c_open)
        solid_body = (c_body / c_range >= 0.35) if c_range > 0 else True
        vol_breakout = (vol > 1.2 * vol_sma) if (vol_sma > 0 and not is_forex) else (vol > 1.1 * vol_sma or c_range >= 1.2 * atr)

        # Bullish Breakout BUY
        if (
            close > resistance and
            prev_close <= resistance and
            vol_breakout and
            solid_body and
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 > ema50 and
            rsi is not None and pd.notnull(rsi) and 48.0 <= rsi <= 68.0 and
            near_ema20
        ):
            patterns = detect_all_patterns(df, idx)
            approved, conf_delta, annotation = validate_pattern_alignment(patterns, "BUY")
            if not approved:
                return None

            risk_buffer = max(1.5 * atr, close * (0.004 if is_forex else 0.010))
            reward_buffer = max(2.5 * atr, close * (0.006 if is_forex else 0.015))
            target = round(close + reward_buffer, dec)
            sl_candidate = round(support - 0.5 * atr, dec) if (support is not None and pd.notnull(support)) else None
            min_risk_pct = 0.003 if is_forex else 0.008
            if sl_candidate is not None and sl_candidate < close and (close - sl_candidate) >= (close * min_risk_pct):
                stop_loss = sl_candidate
            else:
                stop_loss = round(close - risk_buffer, dec)

            risk = close - stop_loss
            risk_reward = round((target - close) / risk, 2) if risk > 0 else 1.5
            confidence = min(0.95, max(0.70, round(0.82 + conf_delta, 2)))
            vol_mult = (vol / vol_sma) if vol_sma > 0 else 1.5
            res_str = f"{resistance:.4f}" if is_forex else f"{resistance:.2f}"
            reason_text = f"Resistance breakout above {res_str} with {vol_mult:.1f}x volume/volatility expansion and bullish EMA/RSI"
            if annotation:
                reason_text += f" | {annotation}"

            return {
                "symbol": sym_str,
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "BUY",
                "confidence": confidence,
                "entry_price": round(close, dec),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": reason_text,
                "patterns": patterns,
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "ema20": round(ema20, dec) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, dec) if pd.notnull(ema50) else None,
                }
            }

        # Bearish Breakdown SELL
        elif (
            close < support and
            prev_close >= support and
            vol_breakout and
            solid_body and
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 < ema50 and
            rsi is not None and pd.notnull(rsi) and 32.0 <= rsi <= 52.0 and
            near_ema20
        ):
            patterns = detect_all_patterns(df, idx)
            approved, conf_delta, annotation = validate_pattern_alignment(patterns, "SELL")
            if not approved:
                return None

            risk_buffer = max(1.5 * atr, close * (0.004 if is_forex else 0.010))
            reward_buffer = max(2.5 * atr, close * (0.006 if is_forex else 0.015))
            target = round(close - reward_buffer, dec)
            sl_candidate = round(resistance + 0.5 * atr, dec) if (resistance is not None and pd.notnull(resistance)) else None
            min_risk_pct = 0.003 if is_forex else 0.008
            if sl_candidate is not None and sl_candidate > close and (sl_candidate - close) >= (close * min_risk_pct):
                stop_loss = sl_candidate
            else:
                stop_loss = round(close + risk_buffer, dec)

            risk = stop_loss - close
            risk_reward = round((close - target) / risk, 2) if risk > 0 else 1.5
            confidence = min(0.95, max(0.70, round(0.82 + conf_delta, 2)))
            vol_mult = (vol / vol_sma) if vol_sma > 0 else 1.5
            sup_str = f"{support:.4f}" if is_forex else f"{support:.2f}"
            reason_text = f"Support breakdown below {sup_str} with {vol_mult:.1f}x volume/volatility expansion and bearish EMA/RSI"
            if annotation:
                reason_text += f" | {annotation}"

            return {
                "symbol": sym_str,
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "SELL",
                "confidence": confidence,
                "entry_price": round(close, dec),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": reason_text,
                "patterns": patterns,
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "ema20": round(ema20, dec) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, dec) if pd.notnull(ema50) else None,
                }
            }

        return None


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy:
    BUY when:
    - EMA20 > EMA50
    - MACD > Signal Line and Histogram expanding
    - RSI between 50 and 66
    - Price within 1.0% of EMA20
    SELL when:
    - EMA20 < EMA50
    - MACD < Signal Line and Histogram expanding downwards
    - RSI between 34 and 50
    - Price within 1.0% of EMA20
    """
    def __init__(self):
        super().__init__("MomentumStrategy")

    def evaluate(self, df: pd.DataFrame, idx: int = -1) -> Optional[Dict[str, Any]]:
        if len(df) < 25:
            return None

        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        close = curr["close"]
        sym_str = str(curr.get("symbol", "UNKNOWN"))
        dec = get_precision_for_symbol(sym_str, close)
        is_forex = (dec == 4)

        ema20 = curr.get("ema20")
        ema50 = curr.get("ema50")
        macd = curr.get("macd")
        macd_sig = curr.get("macd_signal")
        rsi = curr.get("rsi")
        atr = curr.get("atr")
        if atr is None or pd.isna(atr) or atr <= 0:
            atr = close * 0.005

        prev_macd = prev.get("macd")
        prev_sig = prev.get("macd_signal")

        near_ema20 = (
            ema20 is not None and pd.notnull(ema20) and
            abs(close - ema20) / ema20 <= 0.010
        )

        # Bullish Momentum BUY
        macd_expanding_up = (
            prev_macd is None or prev_sig is None or pd.isna(prev_macd) or pd.isna(prev_sig) or
            prev_macd <= prev_sig or
            (macd - macd_sig) > (prev_macd - prev_sig)
        )
        if (
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 > ema50 and
            macd is not None and macd_sig is not None and pd.notnull(macd) and pd.notnull(macd_sig) and macd > macd_sig and
            macd_expanding_up and
            rsi is not None and pd.notnull(rsi) and 50.0 <= rsi <= 66.0 and
            near_ema20
        ):
            patterns = detect_all_patterns(df, idx)
            approved, conf_delta, annotation = validate_pattern_alignment(patterns, "BUY")
            if not approved:
                return None

            risk_buffer = max(1.5 * atr, close * (0.004 if is_forex else 0.010))
            reward_buffer = max(2.5 * atr, close * (0.006 if is_forex else 0.015))
            stop_loss = round(close - risk_buffer, dec)
            target = round(close + reward_buffer, dec)
            risk = close - stop_loss
            risk_reward = round((target - close) / risk, 2) if risk > 0 else 1.5
            confidence = min(0.95, max(0.70, round(0.78 + conf_delta, 2)))
            reason_text = f"Bullish momentum: MACD positive expansion, RSI {rsi:.1f}, EMA20 > EMA50"
            if annotation:
                reason_text += f" | {annotation}"

            return {
                "symbol": sym_str,
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "BUY",
                "confidence": confidence,
                "entry_price": round(close, dec),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": reason_text,
                "patterns": patterns,
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "macd": round(macd, 4 if is_forex else 2) if pd.notnull(macd) else None,
                    "ema20": round(ema20, dec) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, dec) if pd.notnull(ema50) else None,
                }
            }

        # Bearish Momentum SELL
        macd_expanding_down = (
            prev_macd is None or prev_sig is None or pd.isna(prev_macd) or pd.isna(prev_sig) or
            prev_macd >= prev_sig or
            (macd - macd_sig) < (prev_macd - prev_sig)
        )
        if (
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 < ema50 and
            macd is not None and macd_sig is not None and pd.notnull(macd) and pd.notnull(macd_sig) and macd < macd_sig and
            macd_expanding_down and
            rsi is not None and pd.notnull(rsi) and 34.0 <= rsi <= 50.0 and
            near_ema20
        ):
            patterns = detect_all_patterns(df, idx)
            approved, conf_delta, annotation = validate_pattern_alignment(patterns, "SELL")
            if not approved:
                return None

            risk_buffer = max(1.5 * atr, close * (0.004 if is_forex else 0.010))
            reward_buffer = max(2.5 * atr, close * (0.006 if is_forex else 0.015))
            stop_loss = round(close + risk_buffer, dec)
            target = round(close - reward_buffer, dec)
            risk = stop_loss - close
            risk_reward = round((close - target) / risk, 2) if risk > 0 else 1.5
            confidence = min(0.95, max(0.70, round(0.78 + conf_delta, 2)))
            reason_text = f"Bearish momentum: MACD negative expansion, RSI {rsi:.1f}, EMA20 < EMA50"
            if annotation:
                reason_text += f" | {annotation}"

            return {
                "symbol": sym_str,
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "SELL",
                "confidence": confidence,
                "entry_price": round(close, dec),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": reason_text,
                "patterns": patterns,
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "macd": round(macd, 4 if is_forex else 2) if pd.notnull(macd) else None,
                    "ema20": round(ema20, dec) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, dec) if pd.notnull(ema50) else None,
                }
            }

        return None


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy (Pullback entries):
    BUY when:
    - Price > VWAP
    - EMA20 > EMA50
    - ADX > 18
    - Close > Open (bullish candle)
    - Close <= VWAP * 1.008 (pullback test near VWAP/EMA20)
    SELL when:
    - Price < VWAP
    - EMA20 < EMA50
    - ADX > 18
    - Close < Open (bearish candle)
    - Close >= VWAP * 0.992 (rejection test at VWAP from below)
    """
    def __init__(self):
        super().__init__("TrendFollowingStrategy")

    def evaluate(self, df: pd.DataFrame, idx: int = -1) -> Optional[Dict[str, Any]]:
        if len(df) < 25:
            return None

        curr = df.iloc[idx]
        close = curr["close"]
        sym_str = str(curr.get("symbol", "UNKNOWN"))
        dec = get_precision_for_symbol(sym_str, close)
        is_forex = (dec == 4)

        vwap = curr.get("vwap")
        ema20 = curr.get("ema20")
        ema50 = curr.get("ema50")
        adx = curr.get("adx")
        atr = curr.get("atr")
        if atr is None or pd.isna(atr) or atr <= 0:
            atr = close * 0.005

        # BUY: Pullback test near VWAP/EMA20
        if (
            vwap is not None and pd.notnull(vwap) and close > vwap and
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 > ema50 and
            adx is not None and pd.notnull(adx) and adx > 18.0 and
            curr["close"] > curr["open"] and
            close <= vwap * 1.008
        ):
            patterns = detect_all_patterns(df, idx)
            approved, conf_delta, annotation = validate_pattern_alignment(patterns, "BUY")
            if not approved:
                return None

            risk_buffer = max(1.5 * atr, close * (0.004 if is_forex else 0.010))
            reward_buffer = max(2.5 * atr, close * (0.006 if is_forex else 0.015))
            target = round(close + reward_buffer, dec)
            sl_cand = round(vwap - 0.5 * atr, dec)
            min_dist = close * (0.003 if is_forex else 0.008)
            if sl_cand >= close or (close - sl_cand) < min_dist:
                stop_loss = round(close - risk_buffer, dec)
            else:
                stop_loss = sl_cand

            risk = close - stop_loss
            risk_reward = round((target - close) / risk, 2) if risk > 0 else 1.5
            confidence = min(0.95, max(0.70, round(0.76 + conf_delta, 2)))
            vwap_str = f"{vwap:.4f}" if is_forex else f"{vwap:.2f}"
            reason_text = f"Bullish pullback trend: Price testing VWAP ({vwap_str}) from above, ADX={adx:.1f}, EMA20 > EMA50"
            if annotation:
                reason_text += f" | {annotation}"

            return {
                "symbol": sym_str,
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "BUY",
                "confidence": confidence,
                "entry_price": round(close, dec),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": reason_text,
                "patterns": patterns,
                "indicators": {
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "vwap": round(vwap, dec) if pd.notnull(vwap) else None,
                    "ema20": round(ema20, dec) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, dec) if pd.notnull(ema50) else None,
                }
            }

        # SELL: Rejection test at VWAP from below
        elif (
            vwap is not None and pd.notnull(vwap) and close < vwap and
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 < ema50 and
            adx is not None and pd.notnull(adx) and adx > 18.0 and
            curr["close"] < curr["open"] and
            close >= vwap * 0.992
        ):
            patterns = detect_all_patterns(df, idx)
            approved, conf_delta, annotation = validate_pattern_alignment(patterns, "SELL")
            if not approved:
                return None

            risk_buffer = max(1.5 * atr, close * (0.004 if is_forex else 0.010))
            reward_buffer = max(2.5 * atr, close * (0.006 if is_forex else 0.015))
            target = round(close - reward_buffer, dec)
            sl_cand = round(vwap + 0.5 * atr, dec)
            min_dist = close * (0.003 if is_forex else 0.008)
            if sl_cand <= close or (sl_cand - close) < min_dist:
                stop_loss = round(close + risk_buffer, dec)
            else:
                stop_loss = sl_cand

            risk = stop_loss - close
            risk_reward = round((close - target) / risk, 2) if risk > 0 else 1.5
            confidence = min(0.95, max(0.70, round(0.76 + conf_delta, 2)))
            vwap_str = f"{vwap:.4f}" if is_forex else f"{vwap:.2f}"
            reason_text = f"Bearish rejection trend: Price testing VWAP ({vwap_str}) from below, ADX={adx:.1f}, EMA20 < EMA50"
            if annotation:
                reason_text += f" | {annotation}"

            return {
                "symbol": sym_str,
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "SELL",
                "confidence": confidence,
                "entry_price": round(close, dec),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": reason_text,
                "patterns": patterns,
                "indicators": {
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "vwap": round(vwap, dec) if pd.notnull(vwap) else None,
                    "ema20": round(ema20, dec) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, dec) if pd.notnull(ema50) else None,
                }
            }

        return None


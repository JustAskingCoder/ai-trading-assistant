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


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy:
    BUY when:
    - Price breaks 20-period resistance (close > resistance, prev_close <= resistance)
    - Volume > 1.2x Volume SMA
    - EMA20 > EMA50
    - RSI between 48 and 68 (prevent buying overbought)
    - Price within 1.2% of EMA20
    SELL when:
    - Price breaks 20-period support (close < support, prev_close >= support)
    - Volume > 1.2x Volume SMA
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

        # Bullish Breakout BUY
        if (
            close > resistance and
            prev_close <= resistance and
            vol > 1.2 * vol_sma and
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 > ema50 and
            rsi is not None and pd.notnull(rsi) and 48.0 <= rsi <= 68.0 and
            near_ema20
        ):
            target = round(close + min(1.2 * atr, close * 0.005), 2)
            sl_candidate = round(support - 0.5 * atr, 2) if (support is not None and pd.notnull(support)) else None
            if sl_candidate is not None and sl_candidate < close and (target - close) / (close - sl_candidate + 1e-10) >= 0.8:
                stop_loss = sl_candidate
            else:
                stop_loss = round(close - 1.2 * atr, 2)

            risk = close - stop_loss
            risk_reward = round((target - close) / risk, 2) if risk > 0 else 0.8
            patterns = detect_all_patterns(df, idx)

            return {
                "symbol": str(curr.get("symbol", "UNKNOWN")),
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "BUY",
                "confidence": 0.82,
                "entry_price": round(close, 2),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": f"Resistance breakout above {resistance:.2f} with {vol / vol_sma:.1f}x volume expansion and bullish EMA/RSI",
                "patterns": patterns,
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "ema20": round(ema20, 2) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, 2) if pd.notnull(ema50) else None,
                }
            }

        # Bearish Breakdown SELL
        elif (
            close < support and
            prev_close >= support and
            vol > 1.2 * vol_sma and
            ema20 is not None and ema50 is not None and pd.notnull(ema20) and pd.notnull(ema50) and ema20 < ema50 and
            rsi is not None and pd.notnull(rsi) and 32.0 <= rsi <= 52.0 and
            near_ema20
        ):
            target = round(close - min(1.2 * atr, close * 0.005), 2)
            sl_candidate = round(resistance + 0.5 * atr, 2) if (resistance is not None and pd.notnull(resistance)) else None
            if sl_candidate is not None and sl_candidate > close and (close - target) / (sl_candidate - close + 1e-10) >= 0.8:
                stop_loss = sl_candidate
            else:
                stop_loss = round(close + 1.2 * atr, 2)

            risk = stop_loss - close
            risk_reward = round((close - target) / risk, 2) if risk > 0 else 0.8
            patterns = detect_all_patterns(df, idx)

            return {
                "symbol": str(curr.get("symbol", "UNKNOWN")),
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "SELL",
                "confidence": 0.82,
                "entry_price": round(close, 2),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": f"Support breakdown below {support:.2f} with {vol / vol_sma:.1f}x volume expansion and bearish EMA/RSI",
                "patterns": patterns,
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "ema20": round(ema20, 2) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, 2) if pd.notnull(ema50) else None,
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
            stop_loss = round(close - (1.2 * atr), 2)
            target = round(close + min(1.2 * atr, close * 0.005), 2)
            risk = close - stop_loss
            risk_reward = round((target - close) / risk, 2) if risk > 0 else 0.8

            return {
                "symbol": str(curr.get("symbol", "UNKNOWN")),
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "BUY",
                "confidence": 0.78,
                "entry_price": round(close, 2),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": f"Bullish momentum: MACD positive expansion, RSI {rsi:.1f}, EMA20 > EMA50",
                "patterns": detect_all_patterns(df, idx),
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "macd": round(macd, 2) if pd.notnull(macd) else None,
                    "ema20": round(ema20, 2) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, 2) if pd.notnull(ema50) else None,
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
            stop_loss = round(close + (1.2 * atr), 2)
            target = round(close - min(1.2 * atr, close * 0.005), 2)
            risk = stop_loss - close
            risk_reward = round((close - target) / risk, 2) if risk > 0 else 0.8

            return {
                "symbol": str(curr.get("symbol", "UNKNOWN")),
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "SELL",
                "confidence": 0.78,
                "entry_price": round(close, 2),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": f"Bearish momentum: MACD negative expansion, RSI {rsi:.1f}, EMA20 < EMA50",
                "patterns": detect_all_patterns(df, idx),
                "indicators": {
                    "rsi": round(rsi, 2) if pd.notnull(rsi) else None,
                    "macd": round(macd, 2) if pd.notnull(macd) else None,
                    "ema20": round(ema20, 2) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, 2) if pd.notnull(ema50) else None,
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
            target = round(close + min(1.2 * atr, close * 0.006), 2)
            stop_loss = round(vwap - 0.5 * atr, 2)
            if stop_loss >= close or (target - close) / (close - stop_loss + 1e-10) < 0.8:
                stop_loss = round(close - 1.2 * atr, 2)

            risk = close - stop_loss
            risk_reward = round((target - close) / risk, 2) if risk > 0 else 0.8

            return {
                "symbol": str(curr.get("symbol", "UNKNOWN")),
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "BUY",
                "confidence": 0.76,
                "entry_price": round(close, 2),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": f"Bullish pullback trend: Price testing VWAP ({vwap:.2f}) from above, ADX={adx:.1f}, EMA20 > EMA50",
                "patterns": detect_all_patterns(df, idx),
                "indicators": {
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "vwap": round(vwap, 2) if pd.notnull(vwap) else None,
                    "ema20": round(ema20, 2) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, 2) if pd.notnull(ema50) else None,
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
            target = round(close - min(1.2 * atr, close * 0.006), 2)
            stop_loss = round(vwap + 0.5 * atr, 2)
            if stop_loss <= close or (close - target) / (stop_loss - close + 1e-10) < 0.8:
                stop_loss = round(close + 1.2 * atr, 2)

            risk = stop_loss - close
            risk_reward = round((close - target) / risk, 2) if risk > 0 else 0.8

            return {
                "symbol": str(curr.get("symbol", "UNKNOWN")),
                "timestamp": str(curr.get("timestamp", "")),
                "strategy": self.name,
                "signal": "SELL",
                "confidence": 0.76,
                "entry_price": round(close, 2),
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": risk_reward,
                "reason": f"Bearish rejection trend: Price testing VWAP ({vwap:.2f}) from below, ADX={adx:.1f}, EMA20 < EMA50",
                "patterns": detect_all_patterns(df, idx),
                "indicators": {
                    "adx": round(adx, 2) if pd.notnull(adx) else None,
                    "vwap": round(vwap, 2) if pd.notnull(vwap) else None,
                    "ema20": round(ema20, 2) if pd.notnull(ema20) else None,
                    "ema50": round(ema50, 2) if pd.notnull(ema50) else None,
                }
            }

        return None

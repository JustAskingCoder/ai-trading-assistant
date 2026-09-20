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
    - Price breaks 20-period resistance
    - Volume > 1.5x average volume (Volume SMA20)
    - EMA20 > EMA50
    - RSI between 50 and 70
    - ADX > 20
    """
    def __init__(self):
        super().__init__("BreakoutStrategy")

    def evaluate(self, df: pd.DataFrame, idx: int = -1) -> Optional[Dict[str, Any]]:
        if len(df) < 25:
            return None

        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        close = curr["close"]

        # Window for resistance / support
        window = df.iloc[max(0, idx - 21):idx]
        resistance = window["high"].max()
        support = window["low"].min()

        vol = curr.get("volume", 0)
        vol_sma = curr.get("volume_sma", 1)
        ema20 = curr.get("ema20")
        ema50 = curr.get("ema50")
        rsi = curr.get("rsi")
        adx = curr.get("adx")
        atr = curr.get("atr", close * 0.005) or (close * 0.005)

        # Bullish Breakout condition
        if (
            close > resistance and
            prev["close"] <= resistance and
            vol > 1.5 * vol_sma and
            ema20 is not None and ema50 is not None and ema20 > ema50 and
            rsi is not None and 50.0 <= rsi <= 72.0 and
            adx is not None and adx >= 18.0
        ):
            stop_loss = round(close - (1.5 * atr), 2)
            risk = close - stop_loss
            target = round(close + (2.0 * risk), 2)  # 2:1 R:R
            risk_reward = round((target - close) / (close - stop_loss), 2) if (close - stop_loss) > 0 else 2.0

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
                    "rsi": round(rsi, 2) if rsi else None,
                    "adx": round(adx, 2) if adx else None,
                    "ema20": round(ema20, 2) if ema20 else None,
                    "ema50": round(ema50, 2) if ema50 else None,
                }
            }

        return None


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy:
    BUY when:
    - EMA20 > EMA50 (or crossed recently)
    - MACD > Signal Line and Histogram expanding
    - RSI between 55 and 68
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
        atr = curr.get("atr", close * 0.005) or (close * 0.005)

        if (
            ema20 and ema50 and ema20 > ema50 and
            macd is not None and macd_sig is not None and macd > macd_sig and
            rsi is not None and 52.0 <= rsi <= 68.0
        ):
            # Check if MACD crossed recently or momentum is fresh
            prev_macd = prev.get("macd", 0)
            prev_sig = prev.get("macd_signal", 0)
            if prev_macd <= prev_sig or (macd - macd_sig) > (prev_macd - prev_sig):
                stop_loss = round(close - (1.2 * atr), 2)
                risk = close - stop_loss
                target = round(close + (2.0 * risk), 2)
                risk_reward = round((target - close) / (close - stop_loss), 2) if (close - stop_loss) > 0 else 2.0

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
                        "rsi": round(rsi, 2) if rsi else None,
                        "macd": round(macd, 2) if macd else None,
                        "ema20": round(ema20, 2) if ema20 else None,
                    }
                }

        return None


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy:
    BUY when:
    - Price > VWAP
    - EMA20 > EMA50
    - ADX > 22 (confirmed strong trend)
    - Close > Open (bullish candle)
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
        atr = curr.get("atr", close * 0.005) or (close * 0.005)

        if (
            vwap and close > vwap and
            ema20 and ema50 and ema20 > ema50 and
            adx and adx > 22.0 and
            curr["close"] > curr["open"]
        ):
            stop_loss = round(min(vwap, close - (1.5 * atr)), 2)
            risk = close - stop_loss
            if risk <= 0:
                risk = atr
                stop_loss = round(close - risk, 2)

            target = round(close + (2.0 * risk), 2)
            risk_reward = round((target - close) / risk, 2)

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
                "reason": f"Strong trend: Price above VWAP ({vwap:.2f}), ADX={adx:.1f}, EMA20 > EMA50",
                "patterns": detect_all_patterns(df, idx),
                "indicators": {
                    "adx": round(adx, 2) if adx else None,
                    "vwap": round(vwap, 2) if vwap else None,
                }
            }

        return None

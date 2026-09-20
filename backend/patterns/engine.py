"""Deterministic pattern detection engine for AI Trading Assistant."""
import pandas as pd
from typing import List, Dict, Any


def detect_candlestick_patterns(df: pd.DataFrame, idx: int = -1) -> List[Dict[str, Any]]:
    """Detect single and multi-candle price action patterns."""
    patterns = []
    if len(df) < 3:
        return patterns

    curr = df.iloc[idx]
    prev = df.iloc[idx - 1]
    ts = str(curr.get("timestamp", ""))

    c_open, c_high, c_low, c_close = curr["open"], curr["high"], curr["low"], curr["close"]
    p_open, p_close = prev["open"], prev["close"]

    body = abs(c_close - c_open)
    candle_range = c_high - c_low + 1e-10
    upper_wick = c_high - max(c_open, c_close)
    lower_wick = min(c_open, c_close) - c_low

    # 1. Doji
    if body / candle_range < 0.1:
        patterns.append({
            "pattern": "doji",
            "direction": "NEUTRAL",
            "strength": 0.65,
            "timestamp": ts,
            "evidence": ["Body is less than 10% of total candle range", "Indicates market indecision"]
        })

    # 2. Hammer (bullish in downtrend)
    if (lower_wick >= 2.0 * body) and (upper_wick <= 0.2 * body) and (c_close > c_low):
        patterns.append({
            "pattern": "hammer",
            "direction": "BUY",
            "strength": 0.75,
            "timestamp": ts,
            "evidence": ["Lower wick is at least 2x body length", "Minimal upper wick", "Rejection of lower prices"]
        })

    # 3. Shooting Star (bearish in uptrend)
    if (upper_wick >= 2.0 * body) and (lower_wick <= 0.2 * body):
        patterns.append({
            "pattern": "shooting_star",
            "direction": "SELL",
            "strength": 0.75,
            "timestamp": ts,
            "evidence": ["Upper wick is at least 2x body length", "Minimal lower wick", "Rejection of higher prices"]
        })

    # 4. Bullish Engulfing
    if p_close < p_open and c_close > c_open:  # Previous red, current green
        if c_open <= p_close and c_close >= p_open:
            patterns.append({
                "pattern": "bullish_engulfing",
                "direction": "BUY",
                "strength": 0.80,
                "timestamp": ts,
                "evidence": ["Current green body completely engulfs previous red body", "Strong buying momentum shift"]
            })

    # 5. Bearish Engulfing
    if p_close > p_open and c_close < c_open:  # Previous green, current red
        if c_open >= p_close and c_close <= p_open:
            patterns.append({
                "pattern": "bearish_engulfing",
                "direction": "SELL",
                "strength": 0.80,
                "timestamp": ts,
                "evidence": ["Current red body completely engulfs previous green body", "Strong selling momentum shift"]
            })

    return patterns


def detect_technical_breakouts_and_crossovers(df: pd.DataFrame, idx: int = -1) -> List[Dict[str, Any]]:
    """Detect indicator crossovers, volume surges, and support/resistance breakouts."""
    patterns = []
    if len(df) < 20:
        return patterns

    curr = df.iloc[idx]
    prev = df.iloc[idx - 1]
    ts = str(curr.get("timestamp", ""))

    close = curr["close"]
    prev_close = prev["close"]

    # 1. EMA Crossover
    if pd.notnull(curr.get("ema20")) and pd.notnull(curr.get("ema50")):
        ema20_curr, ema50_curr = curr["ema20"], curr["ema50"]
        ema20_prev, ema50_prev = prev["ema20"], prev["ema50"]

        if ema20_prev <= ema50_prev and ema20_curr > ema50_curr:
            patterns.append({
                "pattern": "ema_golden_crossover",
                "direction": "BUY",
                "strength": 0.82,
                "timestamp": ts,
                "evidence": [f"EMA20 ({ema20_curr:.2f}) crossed above EMA50 ({ema50_curr:.2f})"]
            })
        elif ema20_prev >= ema50_prev and ema20_curr < ema50_curr:
            patterns.append({
                "pattern": "ema_death_crossover",
                "direction": "SELL",
                "strength": 0.82,
                "timestamp": ts,
                "evidence": [f"EMA20 ({ema20_curr:.2f}) crossed below EMA50 ({ema50_curr:.2f})"]
            })

    # 2. MACD Crossover
    if pd.notnull(curr.get("macd")) and pd.notnull(curr.get("macd_signal")):
        macd_curr, sig_curr = curr["macd"], curr["macd_signal"]
        macd_prev, sig_prev = prev["macd"], prev["macd_signal"]

        if macd_prev <= sig_prev and macd_curr > sig_curr:
            patterns.append({
                "pattern": "macd_bullish_crossover",
                "direction": "BUY",
                "strength": 0.78,
                "timestamp": ts,
                "evidence": [f"MACD line ({macd_curr:.2f}) crossed above Signal line ({sig_curr:.2f})"]
            })
        elif macd_prev >= sig_prev and macd_curr < sig_curr:
            patterns.append({
                "pattern": "macd_bearish_crossover",
                "direction": "SELL",
                "strength": 0.78,
                "timestamp": ts,
                "evidence": [f"MACD line ({macd_curr:.2f}) crossed below Signal line ({sig_curr:.2f})"]
            })

    # 3. RSI Overbought / Oversold
    if pd.notnull(curr.get("rsi")):
        rsi_curr = curr["rsi"]
        if rsi_curr >= 70:
            patterns.append({
                "pattern": "rsi_overbought",
                "direction": "SELL",
                "strength": 0.70,
                "timestamp": ts,
                "evidence": [f"RSI is at {rsi_curr:.1f} (>= 70) indicating overbought zone"]
            })
        elif rsi_curr <= 30:
            patterns.append({
                "pattern": "rsi_oversold",
                "direction": "BUY",
                "strength": 0.70,
                "timestamp": ts,
                "evidence": [f"RSI is at {rsi_curr:.1f} (<= 30) indicating oversold zone"]
            })

    # 4. Volume Breakout
    if pd.notnull(curr.get("volume_sma")):
        vol = curr["volume"]
        vol_sma = curr["volume_sma"]
        if vol > 1.8 * vol_sma and vol_sma > 0:
            direction = "BUY" if close > curr["open"] else "SELL"
            patterns.append({
                "pattern": "volume_breakout",
                "direction": direction,
                "strength": 0.85,
                "timestamp": ts,
                "evidence": [f"Volume ({vol:,.0f}) is {vol / vol_sma:.1f}x higher than 20-period average ({vol_sma:,.0f})"]
            })

    # 5. Support / Resistance Breakout (Rolling 20-period High / Low)
    window = df.iloc[max(0, idx - 21):idx]
    if len(window) >= 15:
        resistance = window["high"].max()
        support = window["low"].min()

        if close > resistance and prev_close <= resistance:
            patterns.append({
                "pattern": "resistance_breakout",
                "direction": "BUY",
                "strength": 0.88,
                "timestamp": ts,
                "evidence": [f"Price ({close:.2f}) broke above 20-period resistance ({resistance:.2f})"]
            })
        elif close < support and prev_close >= support:
            patterns.append({
                "pattern": "support_breakdown",
                "direction": "SELL",
                "strength": 0.88,
                "timestamp": ts,
                "evidence": [f"Price ({close:.2f}) broke below 20-period support ({support:.2f})"]
            })

    # 6. VWAP Breakout
    if pd.notnull(curr.get("vwap")) and pd.notnull(prev.get("vwap")):
        vwap_curr, vwap_prev = curr["vwap"], prev["vwap"]
        if prev_close <= vwap_prev and close > vwap_curr:
            patterns.append({
                "pattern": "vwap_cross_above",
                "direction": "BUY",
                "strength": 0.72,
                "timestamp": ts,
                "evidence": [f"Price crossed above VWAP ({vwap_curr:.2f})"]
            })
        elif prev_close >= vwap_prev and close < vwap_curr:
            patterns.append({
                "pattern": "vwap_cross_below",
                "direction": "SELL",
                "strength": 0.72,
                "timestamp": ts,
                "evidence": [f"Price crossed below VWAP ({vwap_curr:.2f})"]
            })

    return patterns


def detect_all_patterns(df_with_indicators: pd.DataFrame, idx: int = -1) -> List[Dict[str, Any]]:
    """Aggregate all detected patterns on the latest or specified candle."""
    c_patterns = detect_candlestick_patterns(df_with_indicators, idx)
    t_patterns = detect_technical_breakouts_and_crossovers(df_with_indicators, idx)
    return c_patterns + t_patterns

"""Technical indicator calculations using Pandas and NumPy."""
import numpy as np
import pandas as pd
from typing import Dict, Any


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    # Wilder's exponential smoothing
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    middle = calculate_sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    tp_vol = typical_price * df["volume"]

    # Daily reset if timestamp is available
    if "timestamp" in df.columns:
        dt = pd.to_datetime(df["timestamp"])
        day_group = dt.dt.date
        cum_tp_vol = tp_vol.groupby(day_group).cumsum()
        cum_vol = df["volume"].groupby(day_group).cumsum()
    else:
        cum_tp_vol = tp_vol.cumsum()
        cum_vol = df["volume"].cumsum()

    return cum_tp_vol / (cum_vol + 1e-10)


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = calculate_atr(high, low, close, period=period)
    smooth_tr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    smooth_plus_dm = plus_dm.ewm(alpha=1.0 / period, adjust=False).mean()
    smooth_minus_dm = minus_dm.ewm(alpha=1.0 / period, adjust=False).mean()

    plus_di = 100 * (smooth_plus_dm / (smooth_tr + 1e-10))
    minus_di = 100 * (smooth_minus_dm / (smooth_tr + 1e-10))

    dx = 100 * (plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10)
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()
    return adx


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all required indicators on an OHLCV DataFrame."""
    out = df.copy()

    # Sort chronologically if timestamp exists
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"])
        out = out.sort_values("timestamp").reset_index(drop=True)

    out["ema20"] = calculate_ema(out["close"], 20)
    out["ema50"] = calculate_ema(out["close"], 50)
    out["sma20"] = calculate_sma(out["close"], 20)
    out["rsi"] = calculate_rsi(out["close"], 14)

    macd_line, signal_line, macd_hist = calculate_macd(out["close"], 12, 26, 9)
    out["macd"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = macd_hist

    out["vwap"] = calculate_vwap(out)
    out["atr"] = calculate_atr(out["high"], out["low"], out["close"], 14)

    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(out["close"], 20, 2.0)
    out["bb_upper"] = bb_upper
    out["bb_middle"] = bb_middle
    out["bb_lower"] = bb_lower

    out["adx"] = calculate_adx(out["high"], out["low"], out["close"], 14)
    out["volume_sma"] = calculate_sma(out["volume"], 20)

    return out


def get_latest_indicators_summary(df_with_indicators: pd.DataFrame) -> Dict[str, Any]:
    """Return dictionary summary of the latest candle's indicators."""
    if df_with_indicators.empty:
        return {}

    last_row = df_with_indicators.iloc[-1]
    return {
        "close": float(last_row.get("close", 0.0)),
        "ema20": float(last_row.get("ema20", 0.0)) if pd.notnull(last_row.get("ema20")) else None,
        "ema50": float(last_row.get("ema50", 0.0)) if pd.notnull(last_row.get("ema50")) else None,
        "sma20": float(last_row.get("sma20", 0.0)) if pd.notnull(last_row.get("sma20")) else None,
        "rsi": float(last_row.get("rsi", 0.0)) if pd.notnull(last_row.get("rsi")) else None,
        "macd": float(last_row.get("macd", 0.0)) if pd.notnull(last_row.get("macd")) else None,
        "macd_signal": float(last_row.get("macd_signal", 0.0)) if pd.notnull(last_row.get("macd_signal")) else None,
        "macd_hist": float(last_row.get("macd_hist", 0.0)) if pd.notnull(last_row.get("macd_hist")) else None,
        "vwap": float(last_row.get("vwap", 0.0)) if pd.notnull(last_row.get("vwap")) else None,
        "atr": float(last_row.get("atr", 0.0)) if pd.notnull(last_row.get("atr")) else None,
        "bb_upper": float(last_row.get("bb_upper", 0.0)) if pd.notnull(last_row.get("bb_upper")) else None,
        "bb_middle": float(last_row.get("bb_middle", 0.0)) if pd.notnull(last_row.get("bb_middle")) else None,
        "bb_lower": float(last_row.get("bb_lower", 0.0)) if pd.notnull(last_row.get("bb_lower")) else None,
        "adx": float(last_row.get("adx", 0.0)) if pd.notnull(last_row.get("adx")) else None,
        "volume_sma": float(last_row.get("volume_sma", 0.0)) if pd.notnull(last_row.get("volume_sma")) else None,
    }

"""High-Win-Rate Intraday Scanner Engine.

Provides algorithmic detection for institutional setups:
1. Open = High & Open = Low (OHL) Institutional Momentum.
2. Volume Surge & Shockers (>= 2.0x 20-period Volume SMA).
3. Central Pivot Range (Narrow CPR <= 0.25%, TC/BC boundaries, and CPR territory).
4. Day High Breakout & Day Low Breakdown (ORB).
5. Multi-factor Confluence Scoring (Grade A+ Institutional Setup when >= 2 factors align).
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def detect_ohl_pattern(
    open_price: float,
    high_price: float,
    low_price: float,
    tolerance_pct: float = 0.05
) -> Dict[str, Any]:
    """
    Detect Open = High (Bearish) or Open = Low (Bullish) institutional momentum.
    tolerance_pct: max % distance allowed between Open and High/Low (default 0.05%).
    """
    if open_price <= 0:
        return {
            "signal": "NONE",
            "diff_pct": 0.0,
            "label": None,
            "is_ohl": False
        }

    low_diff_pct = abs(open_price - low_price) / open_price * 100.0
    high_diff_pct = abs(high_price - open_price) / open_price * 100.0

    # Check Open = Low (Bullish Institutional Buying from bell)
    if low_diff_pct <= tolerance_pct:
        return {
            "signal": "OPEN_LOW",
            "diff_pct": round(low_diff_pct, 4),
            "label": "🟢 O=L (Bullish)",
            "is_ohl": True,
            "bias": "BULLISH",
            "description": f"Open equals Low (within {low_diff_pct:.2f}%): Aggressive institutional buying from open"
        }

    # Check Open = High (Bearish Institutional Selling from bell)
    if high_diff_pct <= tolerance_pct:
        return {
            "signal": "OPEN_HIGH",
            "diff_pct": round(high_diff_pct, 4),
            "label": "🔴 O=H (Bearish)",
            "is_ohl": True,
            "bias": "BEARISH",
            "description": f"Open equals High (within {high_diff_pct:.2f}%): Heavy institutional dumping from open"
        }

    return {
        "signal": "NONE",
        "diff_pct": round(min(low_diff_pct, high_diff_pct), 4),
        "label": None,
        "is_ohl": False,
        "bias": "NEUTRAL",
        "description": "Standard opening range with two-way wicks"
    }


def detect_volume_surge(
    current_volume: float,
    volume_series: Optional[pd.Series] = None,
    avg_volume: Optional[float] = None,
    current_close: Optional[float] = None,
    current_open: Optional[float] = None,
    surge_threshold: float = 2.0
) -> Dict[str, Any]:
    """
    Detect abnormal volume expansion relative to 20-period Volume SMA.
    surge_threshold: Multiplier threshold (default 2.0x average volume).
    """
    if avg_volume is None or avg_volume <= 0:
        if volume_series is not None and len(volume_series) >= 5:
            avg_volume = float(volume_series.tail(20).mean())
        else:
            avg_volume = current_volume

    if avg_volume <= 0:
        return {
            "is_surge": False,
            "ratio": 1.0,
            "current_volume": round(current_volume, 2),
            "avg_volume": round(avg_volume, 2),
            "surge_type": "NORMAL",
            "label": None
        }

    ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    is_surge = ratio >= surge_threshold

    surge_type = "NORMAL"
    label = None
    if is_surge:
        is_bull = (current_close is not None and current_open is not None and current_close >= current_open)
        if is_bull:
            surge_type = "BULLISH_SURGE"
            label = f"🔥 Vol {ratio:.1f}x (Bull)"
        else:
            surge_type = "BEARISH_SURGE"
            label = f"🔥 Vol {ratio:.1f}x (Bear)"

    return {
        "is_surge": is_surge,
        "ratio": round(ratio, 2),
        "current_volume": round(current_volume, 2),
        "avg_volume": round(avg_volume, 2),
        "surge_type": surge_type,
        "label": label
    }


def calculate_cpr_levels(
    high_price: float,
    low_price: float,
    close_price: float,
    current_price: Optional[float] = None,
    dec: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate Central Pivot Range (Pivot, Bottom Central BC, Top Central TC)
    and evaluate Narrow CPR trending potential vs Wide CPR consolidation.
    """
    if dec is None:
        dec = 4 if (close_price < 20.0 or (current_price and current_price < 20.0)) else 2

    if high_price <= 0 or low_price <= 0 or close_price <= 0:
        return {
            "pivot": 0.0,
            "tc": 0.0,
            "bc": 0.0,
            "width_pct": 0.0,
            "cpr_type": "AVERAGE",
            "price_location": "UNKNOWN",
            "label": None,
            "is_narrow": False
        }

    pivot = (high_price + low_price + close_price) / 3.0
    bc = (high_price + low_price) / 2.0
    tc = (pivot - bc) + pivot

    # Standardize boundaries so lower_cpr is always <= upper_cpr
    lower_cpr = min(bc, tc)
    upper_cpr = max(bc, tc)

    width = abs(tc - bc)
    width_pct = (width / pivot * 100.0) if pivot > 0 else 0.0

    # Classification
    if width_pct <= 0.25:
        cpr_type = "NARROW"
        label = "🎯 Narrow CPR"
        is_narrow = True
    elif width_pct >= 0.50:
        cpr_type = "WIDE"
        label = "↔ Wide CPR"
        is_narrow = False
    else:
        cpr_type = "AVERAGE"
        label = "CPR Normal"
        is_narrow = False

    # Evaluate Price Location
    cur_p = current_price if current_price is not None else close_price
    if cur_p > upper_cpr:
        price_location = "ABOVE_CPR"
    elif cur_p < lower_cpr:
        price_location = "BELOW_CPR"
    else:
        price_location = "INSIDE_CPR"

    return {
        "pivot": round(pivot, dec),
        "tc": round(tc, dec),
        "bc": round(bc, dec),
        "lower_boundary": round(lower_cpr, dec),
        "upper_boundary": round(upper_cpr, dec),
        "width_pct": round(width_pct, 3),
        "cpr_type": cpr_type,
        "price_location": price_location,
        "label": label,
        "is_narrow": is_narrow
    }


def detect_day_breakouts(
    current_price: float,
    day_high: float,
    day_low: float,
    is_volume_expanding: bool = False,
    dec: Optional[int] = None
) -> Dict[str, Any]:
    """
    Detect Day's High Breakout or Day's Low Breakdown.
    """
    if dec is None:
        dec = 4 if current_price < 20.0 else 2

    if day_high <= 0 or day_low <= 0 or current_price <= 0:
        return {
            "is_breakout": False,
            "is_breakdown": False,
            "label": None,
            "day_high": day_high,
            "day_low": day_low
        }

    # At or above Day High (with 0.05% threshold for near-test)
    is_breakout = current_price >= (day_high * 0.9995)
    is_breakdown = current_price <= (day_low * 1.0005)

    label = None
    if is_breakout:
        label = "⚡ Day High Breakout"
    elif is_breakdown:
        label = "⚡ Day Low Breakdown"

    return {
        "is_breakout": is_breakout,
        "is_breakdown": is_breakdown,
        "label": label,
        "day_high": round(day_high, dec),
        "day_low": round(day_low, dec)
    }


def analyze_high_win_rate_scanners(
    df: pd.DataFrame,
    current_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Run the full suite of High-Win-Rate intraday scanners against a candle DataFrame.
    Evaluates:
    - OHL Pattern
    - Volume Surge
    - CPR Width & Territory
    - Day Breakout / Breakdown
    - Multi-factor Confluence Scoring
    """
    if df is None or df.empty or len(df) < 2:
        return {
            "ohl": {"signal": "NONE", "label": None, "is_ohl": False},
            "volume_surge": {"is_surge": False, "ratio": 1.0, "label": None},
            "cpr": {"cpr_type": "AVERAGE", "label": None, "is_narrow": False},
            "day_breakout": {"is_breakout": False, "is_breakdown": False, "label": None},
            "confluence": {
                "score": 0,
                "bullish_points": 0,
                "bearish_points": 0,
                "grade": "NEUTRAL",
                "bias": "NEUTRAL",
                "badge": None,
                "tags": []
            }
        }

    last_candle = df.iloc[-1]
    first_candle = df.iloc[0]

    cur_close = float(last_candle["close"])
    cur_open = float(last_candle["open"])
    cur_p = current_price if current_price is not None else cur_close
    dec = 4 if cur_p < 20.0 else 2

    # Intraday range
    day_open = float(first_candle["open"])
    day_high = float(df["high"].max())
    day_low = float(df["low"].min())
    day_close = cur_close

    # 1. OHL Analysis (from opening of session)
    ohl_res = detect_ohl_pattern(day_open, day_high, day_low)

    # 2. Volume Surge Analysis
    cur_vol = float(last_candle.get("volume", 0.0))
    vol_sma = float(last_candle["volume_sma"]) if "volume_sma" in last_candle and pd.notnull(last_candle["volume_sma"]) else None
    vol_res = detect_volume_surge(
        current_volume=cur_vol,
        volume_series=df["volume"] if "volume" in df.columns else None,
        avg_volume=vol_sma,
        current_close=cur_close,
        current_open=cur_open
    )

    # 3. CPR Analysis
    cpr_res = calculate_cpr_levels(day_high, day_low, day_close, cur_p, dec=dec)

    # 4. Day Breakout Analysis
    bo_res = detect_day_breakouts(cur_p, day_high, day_low, is_volume_expanding=vol_res["is_surge"], dec=dec)

    # 5. Multi-factor Confluence Scoring
    bullish_pts = 0
    bearish_pts = 0
    tags: List[str] = []

    # OHL Points
    if ohl_res["signal"] == "OPEN_LOW":
        bullish_pts += 1
        tags.append(ohl_res["label"])
    elif ohl_res["signal"] == "OPEN_HIGH":
        bearish_pts += 1
        tags.append(ohl_res["label"])

    # Volume Surge Points
    if vol_res["is_surge"]:
        if vol_res["surge_type"] == "BULLISH_SURGE":
            bullish_pts += 1
            tags.append(vol_res["label"])
        elif vol_res["surge_type"] == "BEARISH_SURGE":
            bearish_pts += 1
            tags.append(vol_res["label"])

    # CPR Points
    if cpr_res["is_narrow"]:
        tags.append(cpr_res["label"])
        if cpr_res["price_location"] == "ABOVE_CPR":
            bullish_pts += 1
        elif cpr_res["price_location"] == "BELOW_CPR":
            bearish_pts += 1

    # Breakout Points
    if bo_res["is_breakout"]:
        bullish_pts += 1
        tags.append(bo_res["label"])
    elif bo_res["is_breakdown"]:
        bearish_pts += 1
        tags.append(bo_res["label"])

    # Determine Grade and Setup Bias
    total_score = max(bullish_pts, bearish_pts)
    badge = None
    if bullish_pts >= 2 and bullish_pts > bearish_pts:
        grade = "A+ HIGH CONFLUENCE"
        bias = "STRONG_BUY"
        badge = "⚡ A+ Bullish Setup"
    elif bearish_pts >= 2 and bearish_pts > bullish_pts:
        grade = "A+ HIGH CONFLUENCE"
        bias = "STRONG_SELL"
        badge = "⚡ A+ Bearish Setup"
    elif total_score == 1:
        grade = "B PROBABILITY"
        bias = "BULLISH" if bullish_pts > 0 else "BEARISH"
        badge = "✦ Setup Forming"
    else:
        grade = "NEUTRAL"
        bias = "NEUTRAL"

    return {
        "ohl": ohl_res,
        "volume_surge": vol_res,
        "cpr": cpr_res,
        "day_breakout": bo_res,
        "confluence": {
            "score": total_score,
            "bullish_points": bullish_pts,
            "bearish_points": bearish_pts,
            "grade": grade,
            "bias": bias,
            "badge": badge,
            "tags": tags
        }
    }

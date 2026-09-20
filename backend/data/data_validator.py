"""CSV market data validator."""
import pandas as pd
from typing import List, Tuple, Dict, Any


class DataValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_ohlcv_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str], Dict[str, Any]]:
    errors = []
    metadata = {}

    required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return False, errors, metadata

    # Check for empty dataframe
    if df.empty:
        errors.append("CSV file is empty or contains no data rows.")
        return False, errors, metadata

    # 1. Validate timestamps
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        errors.append(f"Invalid timestamp format: {str(e)}")
        return False, errors, metadata

    if df["timestamp"].isnull().any():
        null_count = int(df["timestamp"].isnull().sum())
        errors.append(f"Found {null_count} missing/null timestamp values.")

    # Check for duplicate timestamps
    duplicates = int(df["timestamp"].duplicated().sum())
    if duplicates > 0:
        errors.append(f"Found {duplicates} duplicate timestamps.")

    # Check chronological ordering
    if not df["timestamp"].is_monotonic_increasing:
        errors.append("Timestamps are not in chronological ascending order.")

    # 2. Validate numeric prices & volume
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols + ["volume"]:
        if df[col].isnull().any():
            null_count = int(df[col].isnull().sum())
            errors.append(f"Found {null_count} missing/null values in column '{col}'.")
        # Check negative or non-positive prices
        if (df[col] < 0).any():
            errors.append(f"Negative values detected in column '{col}'.")

    # High must be >= Low, High >= Open, High >= Close, Low <= Open, Low <= Close
    invalid_high_low = (df["high"] < df["low"]).sum()
    if invalid_high_low > 0:
        errors.append(f"{invalid_high_low} rows where high < low.")

    invalid_high_open = (df["high"] < df["open"]).sum()
    if invalid_high_open > 0:
        errors.append(f"{invalid_high_open} rows where high < open.")

    invalid_high_close = (df["high"] < df["close"]).sum()
    if invalid_high_close > 0:
        errors.append(f"{invalid_high_close} rows where high < close.")

    invalid_low_open = (df["low"] > df["open"]).sum()
    if invalid_low_open > 0:
        errors.append(f"{invalid_low_open} rows where low > open.")

    invalid_low_close = (df["low"] > df["close"]).sum()
    if invalid_low_close > 0:
        errors.append(f"{invalid_low_close} rows where low > close.")

    is_valid = len(errors) == 0

    if is_valid:
        metadata = {
            "total_candles": len(df),
            "start_time": df["timestamp"].min().isoformat(),
            "end_time": df["timestamp"].max().isoformat(),
            "symbol": str(df["symbol"].iloc[0]) if "symbol" in df.columns else "UNKNOWN",
            "first_close": float(df["close"].iloc[0]),
            "last_close": float(df["close"].iloc[-1]),
        }

    return is_valid, errors, metadata

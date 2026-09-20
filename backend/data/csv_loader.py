"""CSV market data loader."""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple
from backend.data.data_validator import validate_ohlcv_dataframe, DataValidationError
from backend.database.session import SessionLocal
from backend.database.models import Instrument, Candle
from backend.core.logging import logger


def load_csv_to_dataframe(file_path_or_buffer) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = pd.read_csv(file_path_or_buffer)

    # Normalize column names to lowercase and trim
    df.columns = [c.strip().lower() for c in df.columns]

    # Validate
    is_valid, errors, metadata = validate_ohlcv_dataframe(df)
    if not is_valid:
        logger.error("CSV validation failed: %s", errors)
        raise DataValidationError(errors)

    logger.info("CSV validated successfully. Total candles: %d", len(df))
    return df, metadata


def import_csv_to_database(file_path: str, symbol: str = None, interval: str = "5m") -> Dict[str, Any]:
    df, metadata = load_csv_to_dataframe(file_path)

    effective_symbol = symbol or (df["symbol"].iloc[0] if "symbol" in df.columns else Path(file_path).stem.split("_")[0])

    db = SessionLocal()
    try:
        # Get or create instrument
        instrument = db.query(Instrument).filter(Instrument.symbol == effective_symbol).first()
        if not instrument:
            instrument = Instrument(
                symbol=effective_symbol,
                exchange="NSE",
                company_name=effective_symbol
            )
            db.add(instrument)
            db.commit()
            db.refresh(instrument)

        # Batch insert candles (avoid duplicates)
        existing_timestamps = set(
            ts[0] for ts in db.query(Candle.timestamp).filter(
                Candle.instrument_id == instrument.id,
                Candle.interval == interval
            ).all()
        )

        candles_to_add = []
        for _, row in df.iterrows():
            ts = pd.to_datetime(row["timestamp"])
            if ts in existing_timestamps:
                continue

            candle = Candle(
                instrument_id=instrument.id,
                timestamp=ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                interval=interval
            )
            candles_to_add.append(candle)

        if candles_to_add:
            db.bulk_save_objects(candles_to_add)
            db.commit()
            logger.info("Imported %d new candles for %s", len(candles_to_add), effective_symbol)

        return {
            "symbol": effective_symbol,
            "interval": interval,
            "total_imported": len(candles_to_add),
            "skipped_duplicates": len(df) - len(candles_to_add),
            "metadata": metadata
        }
    finally:
        db.close()

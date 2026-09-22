"""Market data and simulator API routes."""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import io
import pandas as pd
from backend.database.session import get_db
from backend.database.models import Instrument, Candle
from backend.data.csv_loader import load_csv_to_dataframe
from backend.data.market_simulator import simulator
from backend.data.live_market_service import live_service, get_market_category, SYMBOL_NAMES, get_market_trading_status
from backend.integrations.zerodha.kite_client import zerodha_client
from backend.indicators.engine import calculate_indicators, get_latest_indicators_summary
from backend.patterns.engine import detect_all_patterns
from backend.core.logging import logger

router = APIRouter(prefix="/api", tags=["Market"])


@router.post("/data/upload")
async def upload_csv_data(
    file: UploadFile = File(...),
    symbol: Optional[str] = Form(None),
    interval: str = Form("5m"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        buffer = io.BytesIO(content)
        df, metadata = load_csv_to_dataframe(buffer)

        effective_symbol = symbol or (df["symbol"].iloc[0] if "symbol" in df.columns else file.filename.split(".")[0].split("_")[0])

        # Get or create instrument
        instrument = db.query(Instrument).filter(Instrument.symbol == effective_symbol).first()
        if not instrument:
            instrument = Instrument(symbol=effective_symbol, exchange="NSE", company_name=effective_symbol)
            db.add(instrument)
            db.commit()
            db.refresh(instrument)

        existing_ts = set(
            ts[0] for ts in db.query(Candle.timestamp).filter(
                Candle.instrument_id == instrument.id,
                Candle.interval == interval
            ).all()
        )

        candles_to_add = []
        for _, row in df.iterrows():
            ts = pd.to_datetime(row["timestamp"])
            if ts in existing_ts:
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

        # Load into simulator
        df["symbol"] = effective_symbol
        simulator.load_dataset(df)

        return {
            "success": True,
            "symbol": effective_symbol,
            "interval": interval,
            "imported_count": len(candles_to_add),
            "metadata": metadata
        }
    except Exception as e:
        logger.error("Upload error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/market/mode")
def get_market_mode():
    return {
        "mode": live_service.mode,
        "is_running": live_service.is_running,
        "symbol": live_service.symbol
    }


@router.post("/market/mode")
async def set_market_mode(
    mode: str = Query("LIVE"),
    symbol: str = Query("RELIANCE")
):
    target_mode = mode.upper()
    if target_mode == "LIVE":
        if simulator.is_running:
            simulator.stop()
        live_service.start(symbol=symbol)
    elif target_mode == "SIMULATOR":
        if live_service.is_running:
            live_service.stop()
        live_service.mode = "SIMULATOR"
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'LIVE' or 'SIMULATOR'.")

    return {
        "status": "success",
        "mode": live_service.mode,
        "is_running": live_service.is_running,
        "symbol": live_service.symbol
    }


@router.get("/market/watchlist")
def get_watchlist(symbols: str = Query("RELIANCE,TCS,INFY,HDFCBANK,USDINR,EURUSD")):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return live_service.get_watchlist_quotes(symbol_list)


@router.get("/market/scanners")
def get_scanners(symbols: Optional[str] = Query(None)):
    """Return categorized high-win-rate intraday scanner results across tracked symbols."""
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else None
    return live_service.get_categorized_scanners(symbol_list)


@router.get("/market/status")
def get_market_session_status(category: str = "NSE"):
    """Get real-time exchange trading status (OPEN / CLOSED) and trading hours."""
    return get_market_trading_status(category)



@router.get("/market/{symbol}/trend")
def get_market_trend(symbol: str):
    """Return comprehensive multi-factor trend analysis and suggested trade holding window."""
    return live_service.get_trend_analysis(symbol)


@router.get("/market/{symbol}")
def get_market_overview(symbol: str, db: Session = Depends(get_db)):
    if live_service.mode == "LIVE" or (live_service.data_source == "ZERODHA" and zerodha_client.is_connected):
        try:
            live_candles = live_service.get_latest_candles(symbol, limit=2)
            if live_candles:
                curr = live_candles[-1]
                prev = live_candles[-2] if len(live_candles) > 1 else curr
                c_change = curr["close"] - prev["close"]
                c_pct = (c_change / prev["close"] * 100.0) if prev["close"] > 0 else 0.0
                return {
                    "symbol": symbol,
                    "company_name": symbol,
                    "exchange": "NSE",
                    "price": round(curr["close"], 2),
                    "change": round(c_change, 2),
                    "change_percentage": round(c_pct, 2),
                    "open": round(curr["open"], 2),
                    "high": round(curr["high"], 2),
                    "low": round(curr["low"], 2),
                    "volume": curr["volume"],
                    "timestamp": str(curr["timestamp"])
                }
        except Exception as e:
            logger.warning("Could not get live market overview: %s", e)

    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        try:
            live_candles = live_service.get_latest_candles(symbol, limit=2)
            if live_candles:
                curr = live_candles[-1]
                prev = live_candles[-2] if len(live_candles) > 1 else curr
                c_change = curr["close"] - prev["close"]
                c_pct = (c_change / prev["close"] * 100.0) if prev["close"] > 0 else 0.0
                is_forex = get_market_category(symbol) == "FOREX"
                dec = 4 if is_forex else 2
                return {
                    "symbol": symbol,
                    "company_name": SYMBOL_NAMES.get(symbol.upper(), symbol),
                    "exchange": "FOREX" if is_forex else "NSE",
                    "price": round(curr["close"], dec),
                    "change": round(c_change, dec),
                    "change_percentage": round(c_pct, 2),
                    "open": round(curr["open"], dec),
                    "high": round(curr["high"], dec),
                    "low": round(curr["low"], dec),
                    "volume": curr["volume"],
                    "timestamp": str(curr["timestamp"])
                }
        except Exception as e:
            logger.warning("Fallback live market overview failed: %s", e)
        raise HTTPException(status_code=404, detail=f"Instrument '{symbol}' not found.")

    last_candle = db.query(Candle).filter(Candle.instrument_id == instrument.id).order_by(Candle.timestamp.desc()).first()
    if not last_candle:
        raise HTTPException(status_code=404, detail="No candle data available.")

    prev_candle = db.query(Candle).filter(
        Candle.instrument_id == instrument.id,
        Candle.timestamp < last_candle.timestamp
    ).order_by(Candle.timestamp.desc()).first()

    change = (last_candle.close - prev_candle.close) if prev_candle else 0.0
    change_pct = (change / prev_candle.close * 100.0) if prev_candle and prev_candle.close > 0 else 0.0

    return {
        "symbol": symbol,
        "company_name": instrument.company_name,
        "exchange": instrument.exchange,
        "price": last_candle.close,
        "change": round(change, 2),
        "change_percentage": round(change_pct, 2),
        "open": last_candle.open,
        "high": last_candle.high,
        "low": last_candle.low,
        "volume": last_candle.volume,
        "timestamp": last_candle.timestamp.isoformat()
    }


@router.get("/market/{symbol}/candles")
def get_candles(symbol: str, interval: str = "5m", limit: int = 300, db: Session = Depends(get_db)):
    if live_service.mode == "LIVE" or (live_service.data_source == "ZERODHA" and zerodha_client.is_connected):
        return live_service.get_latest_candles(symbol, interval=interval, limit=limit)

    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        # Fallback to live_service for forex pairs or unseeded symbols
        return live_service.get_latest_candles(symbol, interval=interval, limit=limit)

    candles = db.query(Candle).filter(
        Candle.instrument_id == instrument.id,
        Candle.interval == interval
    ).order_by(Candle.timestamp.asc()).all()

    if not candles:
        return []

    df = pd.DataFrame([{
        "timestamp": c.timestamp.isoformat(),
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume
    } for c in candles])

    ind_df = calculate_indicators(df)
    tail = ind_df.iloc[-limit:]

    return tail.replace({float('nan'): None}).to_dict(orient="records")


@router.get("/indicators/{symbol}")
def get_indicators(symbol: str, interval: str = "5m", db: Session = Depends(get_db)):
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found.")

    candles = db.query(Candle).filter(
        Candle.instrument_id == instrument.id,
        Candle.interval == interval
    ).order_by(Candle.timestamp.asc()).all()

    if not candles:
        raise HTTPException(status_code=404, detail="No candle data.")

    df = pd.DataFrame([{
        "timestamp": c.timestamp,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume
    } for c in candles])

    ind_df = calculate_indicators(df)
    return get_latest_indicators_summary(ind_df)


@router.post("/simulator/control")
async def control_simulator(action: str, speed: float = 1.0):
    act = action.lower()
    if act == "start":
        if live_service.is_running:
            live_service.stop()
        simulator.start(speed)
    elif act == "pause":
        simulator.pause()
    elif act == "stop":
        simulator.stop()
    elif act == "reset":
        simulator.reset()
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use start, pause, stop, reset.")

    return {
        "status": "success",
        "action": act,
        "is_running": simulator.is_running,
        "is_paused": simulator.is_paused,
        "speed": simulator.speed,
        "current_index": simulator.current_index
    }


@router.get("/simulator/status")
def get_simulator_status():
    return {
        "is_running": simulator.is_running,
        "is_paused": simulator.is_paused,
        "speed": simulator.speed,
        "current_index": simulator.current_index,
        "total_candles": len(simulator.data) if simulator.data is not None else 0
    }


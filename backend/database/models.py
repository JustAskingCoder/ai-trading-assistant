"""SQLAlchemy database models for AI Trading Assistant."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), unique=True, index=True, nullable=False)
    exchange = Column(String(20), default="NSE")
    instrument_token = Column(String(50), nullable=True)
    company_name = Column(String(150), nullable=True)

    candles = relationship("Candle", back_populates="instrument")


class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    interval = Column(String(10), default="5m")

    instrument = relationship("Instrument", back_populates="candles")
    indicator = relationship("Indicator", back_populates="candle", uselist=False)


class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True, index=True)
    candle_id = Column(Integer, ForeignKey("candles.id"), nullable=False, index=True)
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    vwap = Column(Float, nullable=True)
    atr = Column(Float, nullable=True)
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    adx = Column(Float, nullable=True)
    volume_sma = Column(Float, nullable=True)

    candle = relationship("Candle", back_populates="indicator")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    instrument = Column(String(50), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    signal = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    strategy = Column(String(50), nullable=False)
    confidence = Column(Float, default=0.0)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    risk_reward = Column(Float, default=0.0)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED, EXECUTED

    ai_analyses = relationship("AIAnalysis", back_populates="signal_rel")


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True, index=True)
    provider = Column(String(30), nullable=False)  # openai, claude
    model = Column(String(50), nullable=False)
    prompt_version = Column(String(20), default="1.0.0")
    input_data = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)
    signal = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, default=0.0)
    reasoning_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    signal_rel = relationship("Signal", back_populates="ai_analyses")


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), index=True, nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(20), default="MARKET")  # MARKET, LIMIT
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    status = Column(String(20), default="FILLED")  # PENDING, FILLED, CANCELLED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), unique=True, index=True, nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), index=True, nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    strategy = Column(String(50), nullable=True)


class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    capital = Column(Float, default=10000.0)
    available_cash = Column(Float, default=10000.0)
    invested_amount = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="WARNING")  # INFO, WARNING, CRITICAL


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20), default="INFO")
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    metadata_info = Column(JSON, nullable=True)

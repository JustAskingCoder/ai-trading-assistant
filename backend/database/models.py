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
    window_minutes = Column(Integer, default=30)


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
    entry_time = Column(DateTime, default=datetime.utcnow)
    window_minutes = Column(Integer, default=30)


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


class CommitteeSession(Base):
    """One run of the 6-analyst pre-trade research desk for a symbol."""

    __tablename__ = "committee_sessions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), index=True, nullable=False)
    timeframe = Column(String(10), default="5m")
    verdict = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    overall_confidence = Column(Float, default=0.0)
    num_agree = Column(Integer, default=0)
    risk_vetoed = Column(Boolean, default=False)
    reasons = Column(JSON, nullable=True)
    decision = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    analyst_verdicts = relationship(
        "CommitteeAnalystVerdict",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class CommitteeAnalystVerdict(Base):
    """Per-analyst verdict recorded for a committee session."""

    __tablename__ = "committee_analyst_verdicts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("committee_sessions.id"), nullable=False, index=True)
    analyst_role = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    confidence = Column(Float, default=0.0)
    top_factor = Column(String(255), nullable=True)
    supporting_factors = Column(JSON, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    rationale = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)
    veto = Column(Boolean, default=False)
    provider = Column(String(30), nullable=True)
    model = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CommitteeSession", back_populates="analyst_verdicts")


class TradeAutopsy(Base):
    __tablename__ = "trade_autopsies"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True, index=True)
    symbol = Column(String(50), index=True, nullable=False)
    side = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    failure_tag = Column(String(50), nullable=False)
    root_cause = Column(Text, nullable=False)
    preventative_rule = Column(Text, nullable=False)
    severity = Column(String(20), default="MODERATE")  # LOW, MODERATE, CRITICAL
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


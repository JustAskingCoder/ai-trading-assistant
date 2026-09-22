"""Configuration module for AI Trading Assistant."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Trading Assistant"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Safety: Paper mode is strictly enforced in V1
    TRADING_MODE: str = Field(default="PAPER", description="Trading mode: PAPER or LIVE (LIVE disabled in V1)")

    # Database
    DATABASE_URL: str = "sqlite:///./database/trading.db"

    # Risk Management Defaults
    INITIAL_CAPITAL: float = 10000.0
    MAX_INVESTMENT_PER_TRADE: float = 5000.0
    RISK_PER_TRADE: float = 0.015  # 1.5% max risk per trade
    MAX_DAILY_LOSS: float = 0.03   # 3% max daily loss
    MAX_OPEN_POSITIONS: int = 6
    MIN_RISK_REWARD: float = 0.8
    MIN_AI_CONFIDENCE: float = 0.75
    DEFAULT_TIMEFRAME: str = "5m"
    AUTO_RELEASE_ON_TREND_SHIFT: bool = True
    MIN_RELEASE_CONFIDENCE: float = 0.80  # Only suggest or trigger release if >= 80% confident
    AUTO_EXTEND_WINNERS: bool = True       # Extend timer by +15m with breakeven locked if in profit

    # Institutional Win-Rate Optimization Filters
    ENABLE_MACRO_TREND_FILTER: bool = True     # 15m Higher-Timeframe trend alignment
    ENABLE_MARKET_TIDE_FILTER: bool = True     # NIFTY benchmark direction alignment
    ENABLE_TIME_OF_DAY_FILTER: bool = True     # Restrict entries during opening whipsaw & lunch chop
    BREAKOUT_VOLUME_MULTIPLIER: float = 1.4    # Minimum volume expansion for breakouts

    # AI Provider Settings
    DEFAULT_AI_PROVIDER: str = "openai"
    DEFAULT_AI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Future Zerodha Settings
    ZERODHA_API_KEY: Optional[str] = None
    ZERODHA_API_SECRET: Optional[str] = None
    ZERODHA_ACCESS_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

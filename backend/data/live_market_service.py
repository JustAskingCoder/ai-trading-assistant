"""Live market data poller and real-time streaming service using yfinance."""
import asyncio
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import yfinance

from backend.indicators.engine import calculate_indicators
from backend.patterns.engine import detect_all_patterns
from backend.strategies.base_strategy import BreakoutStrategy, MomentumStrategy, TrendFollowingStrategy
from backend.paper.paper_broker import paper_broker
from backend.data.market_simulator import simulator
from backend.core.logging import logger

SYMBOL_MAP = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "LT": "LT.NS",
    "WIPRO": "WIPRO.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "MARUTI": "MARUTI.NS",
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
}


def to_yf_symbol(symbol: str) -> str:
    """Map common Indian stock symbols to Yahoo Finance ticker notation."""
    sym = symbol.strip().upper()
    if sym in SYMBOL_MAP:
        return SYMBOL_MAP[sym]
    if "." in sym or "^" in sym or "=" in sym:
        return sym
    return f"{sym}.NS"


class LiveMarketService:
    def __init__(self):
        self._mode: str = "SIMULATOR"
        self._symbol: str = "RELIANCE"
        self._interval: str = "5m"
        self._task: Any = None
        self._bg_loop: Optional[asyncio.AbstractEventLoop] = None
        self._bg_thread: Optional[threading.Thread] = None
        self.poll_interval: float = 4.0
        self.strategies = [BreakoutStrategy(), MomentumStrategy(), TrendFollowingStrategy()]

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, val: str):
        self._mode = val.upper()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def symbol(self) -> str:
        return self._symbol

    @symbol.setter
    def symbol(self, val: str):
        self._symbol = val.upper()

    @property
    def interval(self) -> str:
        return self._interval

    def to_yf_symbol(self, symbol: str) -> str:
        return to_yf_symbol(symbol)

    def _fetch_and_prepare(
        self,
        symbol: str,
        interval: str = "5m",
        limit: int = 200
    ) -> Tuple[List[Dict[str, Any]], Optional[pd.DataFrame]]:
        """Synchronously fetch intraday candles from yfinance, format, and compute indicators."""
        yf_sym = self.to_yf_symbol(symbol)
        ticker = yfinance.Ticker(yf_sym)
        hist = ticker.history(period="1d", interval=interval)
        if hist is None or hist.empty or len(hist) < 20:
            hist_fallback = ticker.history(period="5d", interval=interval)
            if hist_fallback is not None and not hist_fallback.empty:
                hist = hist_fallback

        if hist is None or hist.empty:
            return [], None

        df = hist.reset_index()
        time_col = "Datetime" if "Datetime" in df.columns else ("Date" if "Date" in df.columns else df.columns[0])
        df = df.rename(columns={
            time_col: "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = df[col].astype(float)
            else:
                df[col] = 0.0

        df["timestamp"] = df["timestamp"].astype(str)
        df["symbol"] = symbol.upper()

        ind_df = calculate_indicators(df)
        tail = ind_df.iloc[-limit:] if limit and limit > 0 else ind_df
        records = tail.replace({float('nan'): None, float('inf'): None, float('-inf'): None}).to_dict(orient="records")
        for r in records:
            if "timestamp" in r and r["timestamp"] is not None:
                r["timestamp"] = str(r["timestamp"])

        return records, ind_df

    def get_latest_candles(
        self,
        symbol: str = "RELIANCE",
        interval: str = "5m",
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Fetch latest candles with technical indicators for the frontend."""
        if isinstance(interval, int):
            limit = interval
            interval = "5m"
        try:
            records, _ = self._fetch_and_prepare(symbol, interval, limit=limit)
            return records
        except Exception as e:
            logger.warning("LiveMarketService failed to fetch candles for %s: %s", symbol, e)
            return []

    def start(
        self,
        symbol: str = "RELIANCE",
        interval: str = "5m",
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """Start the live background polling loop for the specified symbol."""
        self.stop()
        self._mode = "LIVE"
        self._symbol = symbol.upper()
        self._interval = interval

        target_loop = loop
        if target_loop is None:
            try:
                target_loop = asyncio.get_running_loop()
            except RuntimeError:
                target_loop = None

        if target_loop and target_loop.is_running():
            self._task = target_loop.create_task(self._live_stream_loop())
        else:
            self._bg_loop = asyncio.new_event_loop()
            self._bg_thread = threading.Thread(target=self._bg_loop.run_forever, daemon=True)
            self._bg_thread.start()
            self._task = asyncio.run_coroutine_threadsafe(self._live_stream_loop(), self._bg_loop)

        logger.info("LiveMarketService started for %s (%s).", self._symbol, self._interval)

    def stop(self):
        """Stop the background polling loop and reset mode to SIMULATOR."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

        if self._bg_loop is not None and self._bg_loop.is_running():
            try:
                self._bg_loop.call_soon_threadsafe(self._bg_loop.stop)
                if self._bg_thread and self._bg_thread.is_alive():
                    self._bg_thread.join(timeout=0.5)
            except Exception:
                pass
        self._bg_loop = None
        self._bg_thread = None

        self._mode = "SIMULATOR"
        logger.info("LiveMarketService stopped.")

    async def _live_stream_loop(self):
        """Background loop polling yfinance every 4s, running strategies, updating broker, and broadcasting."""
        logger.info("Live stream loop started for %s (%s).", self._symbol, self._interval)
        try:
            while self.is_running and self._mode == "LIVE":
                try:
                    records, ind_df = await asyncio.to_thread(
                        self._fetch_and_prepare,
                        self._symbol,
                        self._interval,
                        200
                    )
                    if records and ind_df is not None and not ind_df.empty:
                        latest_candle = records[-1]
                        close_p = float(latest_candle["close"])
                        raw_ts = latest_candle.get("timestamp")
                        candle_dt = pd.to_datetime(raw_ts).to_pydatetime() if raw_ts else None

                        # Update paper positions
                        triggers = paper_broker.update_market_price(self._symbol, close_p)
                        if triggers:
                            for evt in triggers:
                                if evt.get("type") == "BREAKEVEN_TRAILED":
                                    await simulator.broadcast({
                                        "type": "BREAKEVEN_TRAILED",
                                        "data": evt
                                    })
                                else:
                                    await simulator.broadcast({
                                        "type": "AUTO_EXIT_TRIGGERED",
                                        "data": evt
                                    })

                        # Detect patterns and evaluate strategies
                        patterns = detect_all_patterns(ind_df, -1) if len(ind_df) >= 20 else []
                        signals = []
                        if len(ind_df) >= 25:
                            for strat in self.strategies:
                                sig = strat.evaluate(ind_df, -1)
                                if sig:
                                    signals.append(sig)

                        # Broadcast tick payload
                        payload = {
                            "type": "CANDLE_UPDATE",
                            "mode": "LIVE",
                            "index": len(ind_df) - 1,
                            "total": len(ind_df),
                            "timestamp": str(latest_candle.get("timestamp", "")),
                            "symbol": self._symbol,
                            "open": float(latest_candle["open"]),
                            "high": float(latest_candle["high"]),
                            "low": float(latest_candle["low"]),
                            "close": close_p,
                            "volume": float(latest_candle["volume"]),
                            "indicators": {
                                "ema20": float(latest_candle["ema20"]) if latest_candle.get("ema20") is not None else None,
                                "ema50": float(latest_candle["ema50"]) if latest_candle.get("ema50") is not None else None,
                                "rsi": float(latest_candle["rsi"]) if latest_candle.get("rsi") is not None else None,
                                "vwap": float(latest_candle["vwap"]) if latest_candle.get("vwap") is not None else None,
                            },
                            "patterns": patterns,
                            "signals": signals
                        }
                        await simulator.broadcast(payload)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning("Error in LiveMarketService polling tick for %s: %s", self._symbol, e)

                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("LiveMarketService stream loop cancelled.")
        finally:
            self._task = None


live_service = LiveMarketService()
live_market_service = live_service

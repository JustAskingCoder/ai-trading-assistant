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
    # Indian Equities & Indices
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
    # Forex Currency Pairs, Commodities & Crypto
    "USDINR": "USDINR=X",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "EURINR": "EURINR=X",
    "GBPINR": "GBPINR=X",
    "AUDUSD": "AUDUSD=X",
    "GOLD": "GC=F",
    "BTCUSD": "BTC-USD",
}

FOREX_SYMBOLS = {
    "USDINR", "EURUSD", "GBPUSD", "USDJPY", "EURINR", "GBPINR", "AUDUSD",
    "GOLD", "BTCUSD", "GC=F", "BTC-USD", "JPY=X"
}

SYMBOL_NAMES = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys Ltd",
    "HDFCBANK": "HDFCBANK",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ITC": "ITC Limited",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro",
    "WIPRO": "Wipro Limited",
    "TATAMOTORS": "Tata Motors",
    "TATASTEEL": "Tata Steel",
    "MARUTI": "Maruti Suzuki",
    "NIFTY": "NIFTY 50",
    "BANKNIFTY": "BANK NIFTY",
    "USDINR": "USD / INR",
    "EURUSD": "EUR / USD",
    "GBPUSD": "GBP / USD",
    "USDJPY": "USD / JPY",
    "EURINR": "EUR / INR",
    "GBPINR": "GBP / INR",
    "AUDUSD": "AUD / USD",
    "GOLD": "Gold Futures",
    "BTCUSD": "Bitcoin / USD",
}


def get_market_category(symbol: str) -> str:
    """Classify symbol into 'NSE' or 'FOREX'."""
    clean = symbol.strip().upper().replace("/", "").replace(" ", "").replace("_", "")
    yf = to_yf_symbol(symbol)
    if clean in FOREX_SYMBOLS or "=X" in yf or yf in ["GC=F", "BTC-USD"] or "-USD" in yf:
        return "FOREX"
    return "NSE"


def to_yf_symbol(symbol: str) -> str:
    """Map common Indian stock symbols and Forex currency pairs to Yahoo Finance ticker notation."""
    raw = symbol.strip().upper()
    if "." in raw or "^" in raw or "=" in raw or "-" in raw:
        return raw

    clean = raw.replace("/", "").replace(" ", "").replace("_", "")
    if clean in SYMBOL_MAP:
        return SYMBOL_MAP[clean]

    return f"{clean}.NS"


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

    def _fetch_single_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch quote, calculate metrics, and evaluate signal for a single symbol."""
        raw_sym = symbol.strip()
        clean_sym = raw_sym.upper().replace(" ", "")
        yf_sym = self.to_yf_symbol(raw_sym)
        market = get_market_category(raw_sym)
        name = SYMBOL_NAMES.get(clean_sym.replace("/", ""), clean_sym)
        is_forex = (market == "FOREX")
        dec = 4 if is_forex else 2

        try:
            ticker = yfinance.Ticker(yf_sym)
            hist = ticker.history(period="1d", interval="5m")
            if hist is None or hist.empty or len(hist) < 5:
                hist_fallback = ticker.history(period="5d", interval="5m")
                if hist_fallback is not None and not hist_fallback.empty:
                    hist = hist_fallback

            if hist is None or hist.empty:
                return {
                    "symbol": clean_sym,
                    "name": name,
                    "price": 0.0,
                    "change": 0.0,
                    "change_percentage": 0.0,
                    "open": 0.0,
                    "high": 0.0,
                    "low": 0.0,
                    "volume": 0.0,
                    "signal": "HOLD",
                    "action": "WAIT",
                    "quantity": 1,
                    "entry_price": 0.0,
                    "stop_loss": 0.0,
                    "target": 0.0,
                    "risk_reward": 1.0,
                    "target_profit": 0.0,
                    "max_risk": 0.0,
                    "reason": "Insufficient market data for trade decision",
                    "strategy": "Consolidation",
                    "confidence": 0.50,
                    "market": market,
                    "indicators": {},
                    "timestamp": datetime.now().isoformat()
                }

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
            df["symbol"] = clean_sym

            ind_df = calculate_indicators(df)
            last_candle = ind_df.iloc[-1]
            prev_candle = ind_df.iloc[-2] if len(ind_df) > 1 else last_candle

            close_p = float(last_candle["close"])
            prev_close = float(prev_candle["close"])
            change = close_p - prev_close
            change_pct = (change / prev_close * 100.0) if prev_close > 0 else 0.0

            open_p = float(last_candle["open"])
            high_p = float(ind_df["high"].max())
            low_p = float(ind_df["low"].min())
            vol_total = float(ind_df["volume"].sum())

            # Extract ATR
            atr_raw = last_candle.get("atr")
            atr = float(atr_raw) if pd.notnull(atr_raw) and float(atr_raw) > 0 else (close_p * 0.005)

            # Evaluate quick signal ('BUY', 'SELL', or 'HOLD')
            signal = "HOLD"
            strat_sig = None
            if len(ind_df) >= 25:
                for strat in self.strategies:
                    sig = strat.evaluate(ind_df, -1)
                    if sig and "signal" in sig:
                        strat_sig = sig
                        signal = sig["signal"]
                        break

            if signal == "HOLD":
                rsi = last_candle.get("rsi")
                ema20 = last_candle.get("ema20")
                ema50 = last_candle.get("ema50")
                if rsi is not None and pd.notnull(rsi):
                    if rsi < 35.0 or (ema20 is not None and ema50 is not None and ema20 > ema50 and close_p > ema20):
                        signal = "BUY"
                    elif rsi > 65.0 or (ema20 is not None and ema50 is not None and ema20 < ema50 and close_p < ema20):
                        signal = "SELL"

            # Derive actionable trade parameters
            entry_price = round(close_p, dec)
            quantity = 1
            min_step = 0.0001 if is_forex else 0.05

            if signal == "BUY":
                action = "BUY"
                confidence = float(strat_sig.get("confidence", 0.82)) if strat_sig else 0.82
                strategy_name = strat_sig.get("strategy", "Scalp Pullback Strategy") if strat_sig else "Scalp Pullback Strategy"
                reason = strat_sig.get("reason", "Bullish momentum & 20 EMA pullback test") if (strat_sig and strat_sig.get("reason")) else "Bullish momentum & 20 EMA pullback test"

                sl = round(close_p - max(close_p * 0.006, 1.2 * atr), dec)
                if sl >= entry_price:
                    sl = round(entry_price * 0.994, dec)
                if sl >= entry_price:
                    sl = round(entry_price - min_step, dec)

                tgt = round(close_p + min(1.2 * atr, close_p * 0.005), dec)
                if tgt <= entry_price:
                    tgt = round(entry_price * 1.005, dec)
                if tgt <= entry_price:
                    tgt = round(entry_price + min_step, dec)

            elif signal == "SELL":
                action = "SELL"
                confidence = float(strat_sig.get("confidence", 0.82)) if strat_sig else 0.82
                strategy_name = strat_sig.get("strategy", "Scalp Breakout Strategy") if strat_sig else "Scalp Breakout Strategy"
                reason = strat_sig.get("reason", "Bearish rejection at resistance & downward EMA alignment") if (strat_sig and strat_sig.get("reason")) else "Bearish rejection at resistance & downward EMA alignment"

                sl = round(close_p + max(close_p * 0.006, 1.2 * atr), dec)
                if sl <= entry_price:
                    sl = round(entry_price * 1.006, dec)
                if sl <= entry_price:
                    sl = round(entry_price + min_step, dec)

                tgt = round(close_p - min(1.2 * atr, close_p * 0.005), dec)
                if tgt >= entry_price:
                    tgt = round(entry_price * 0.995, dec)
                if tgt >= entry_price:
                    tgt = round(entry_price - min_step, dec)

            else:
                action = "WAIT"
                confidence = 0.50
                strategy_name = "Consolidation"
                reason = "Consolidation / neutral range; awaiting directional breakout"

                sl = round(entry_price * 0.994, dec)
                if sl >= entry_price:
                    sl = round(entry_price - min_step, dec)

                tgt = round(entry_price * 1.005, dec)
                if tgt <= entry_price:
                    tgt = round(entry_price + min_step, dec)

            risk_dist = abs(entry_price - sl)
            target_dist = abs(tgt - entry_price)
            risk_reward = round(target_dist / (risk_dist + 1e-6), 2)
            target_profit = round(target_dist * quantity, dec)
            max_risk = round(risk_dist * quantity, dec)

            return {
                "symbol": clean_sym,
                "name": name,
                "price": entry_price,
                "change": round(change, dec),
                "change_percentage": round(change_pct, 2),
                "open": round(open_p, dec),
                "high": round(high_p, dec),
                "low": round(low_p, dec),
                "volume": round(vol_total, 2),
                "signal": signal,
                "action": action,
                "quantity": quantity,
                "entry_price": entry_price,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": risk_reward,
                "target_profit": target_profit,
                "max_risk": max_risk,
                "reason": reason,
                "strategy": strategy_name,
                "confidence": confidence,
                "market": market,
                "indicators": {
                    "rsi": round(float(last_candle["rsi"]), 2) if pd.notnull(last_candle.get("rsi")) else None,
                    "ema20": round(float(last_candle["ema20"]), dec) if pd.notnull(last_candle.get("ema20")) else None,
                    "ema50": round(float(last_candle["ema50"]), dec) if pd.notnull(last_candle.get("ema50")) else None,
                    "vwap": round(float(last_candle["vwap"]), dec) if pd.notnull(last_candle.get("vwap")) else None,
                },
                "timestamp": str(last_candle.get("timestamp", datetime.now().isoformat()))
            }
        except Exception as e:
            logger.warning("Error fetching quote for %s: %s", symbol, e)
            return {
                "symbol": clean_sym,
                "name": name,
                "price": 0.0,
                "change": 0.0,
                "change_percentage": 0.0,
                "open": 0.0,
                "high": 0.0,
                "low": 0.0,
                "volume": 0.0,
                "signal": "HOLD",
                "action": "WAIT",
                "quantity": 1,
                "entry_price": 0.0,
                "stop_loss": 0.0,
                "target": 0.0,
                "risk_reward": 1.0,
                "target_profit": 0.0,
                "max_risk": 0.0,
                "reason": "Market feed unavailable",
                "strategy": "Consolidation",
                "confidence": 0.50,
                "market": market,
                "indicators": {},
                "timestamp": datetime.now().isoformat()
            }

    def get_watchlist_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch watchlist quotes concurrently for a list of symbols."""
        if not symbols:
            return []

        clean_symbols = [s.strip() for s in symbols if s and s.strip()]
        if not clean_symbols:
            return []

        from concurrent.futures import ThreadPoolExecutor
        max_workers = min(len(clean_symbols), 8)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            quotes = list(executor.map(self._fetch_single_quote, clean_symbols))

        return [q for q in quotes if q is not None]

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

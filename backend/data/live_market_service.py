"""Live market data poller and real-time streaming service using yfinance."""
import asyncio
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import yfinance

from backend.indicators.engine import calculate_indicators
from backend.patterns.engine import detect_all_patterns
from backend.strategies.base_strategy import BreakoutStrategy, MomentumStrategy, TrendFollowingStrategy
from backend.paper.paper_broker import paper_broker
from backend.database.session import SessionLocal
from backend.database.models import Position
from backend.data.market_simulator import simulator
from backend.integrations.zerodha.kite_client import zerodha_client
from backend.core.logging import logger
from backend.core.config import settings

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
    def __init__(self, default_mode: str = "SIMULATOR"):
        self._mode: str = default_mode
        self._symbol: str = "RELIANCE"
        self._interval: str = "5m"
        self.data_source: str = "YFINANCE"  # "YFINANCE" or "ZERODHA"
        self._task: Any = None
        self._bg_loop: Optional[asyncio.AbstractEventLoop] = None
        self._bg_thread: Optional[threading.Thread] = None
        self.poll_interval: float = 4.0
        self.strategies = [BreakoutStrategy(), MomentumStrategy(), TrendFollowingStrategy()]
        self._quote_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl: float = 6.0
        self._candle_cache: Dict[str, Tuple[float, List[Dict[str, Any]], Optional[pd.DataFrame]]] = {}
        self._candle_cache_ttl: float = 10.0

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
        cache_key = f"{symbol.upper()}:{interval}:{limit}"
        now = time.time()
        if cache_key in self._candle_cache:
            ts, recs, ind_df = self._candle_cache[cache_key]
            if now - ts < self._candle_cache_ttl and recs and ind_df is not None:
                # Return deep copy of records so caller mutations do not pollute cache
                import copy
                return copy.deepcopy(recs), ind_df

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

        if records and ind_df is not None:
            self._candle_cache[cache_key] = (now, records, ind_df)

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
            if records and self.data_source == "ZERODHA" and zerodha_client.is_connected:
                try:
                    zq = zerodha_client.get_quotes([symbol])
                    if symbol in zq and zq[symbol].get("price", 0) > 0:
                        zp = float(zq[symbol]["price"])
                        records[-1]["close"] = zp
                        records[-1]["high"] = max(float(records[-1].get("high", zp)), zp)
                        records[-1]["low"] = min(float(records[-1].get("low", zp)), zp)
                        records[-1]["volume"] = float(zq[symbol].get("volume", records[-1].get("volume", 0)))
                except Exception:
                    pass
            return records
        except Exception as e:
            logger.warning("LiveMarketService failed to fetch candles for %s: %s", symbol, e)
            return []

    def clear_cache(self):
        """Clear cached quotes and candles."""
        self._quote_cache.clear()
        self._candle_cache.clear()

    def _build_zerodha_quote_payload(
        self,
        clean_sym: str,
        name: str,
        market: str,
        zq: Dict[str, Any],
        dec: int = 2
    ) -> Dict[str, Any]:
        """Construct normalized quote payload directly from Zerodha Kite 0-delay tick."""
        entry_price = float(zq.get("price", 0.0))
        change = float(zq.get("change", 0.0))
        change_pct = float(zq.get("change_percentage", 0.0))
        open_p = float(zq.get("open", entry_price))
        high_p = float(zq.get("high", entry_price))
        low_p = float(zq.get("low", entry_price))
        vol = float(zq.get("volume", 0.0))

        # Structural brackets calibrated for Intraday/Swing trading (min 1.0% stop-loss buffer, 1.5% target)
        structural_risk = max(entry_price * 0.010, 1.5)
        structural_reward = max(structural_risk * 1.5, entry_price * 0.015)

        if change_pct >= 0.25:
            signal = "BUY"
            action = "BUY"
            confidence = 0.85
            strategy = "Kite 0-Delay Momentum Scalp"
            reason = f"Zerodha 0-delay bullish surge (+{change_pct:.2f}%) exceeding VWAP/pivot"
            sl = round(entry_price - structural_risk, dec)
            tgt = round(entry_price + structural_reward, dec)
        elif change_pct <= -0.25:
            signal = "SELL"
            action = "SELL"
            confidence = 0.85
            strategy = "Kite 0-Delay Short Scalp"
            reason = f"Zerodha 0-delay bearish drop ({change_pct:.2f}%) breaking day pivot"
            sl = round(entry_price + structural_risk, dec)
            tgt = round(entry_price - structural_reward, dec)
        else:
            signal = "HOLD"
            action = "WAIT"
            confidence = 0.55
            strategy = "Consolidation"
            reason = "Zerodha live tick in neutral intraday range"
            sl = round(entry_price - structural_risk, dec)
            tgt = round(entry_price + structural_reward, dec)

        risk_dist = abs(entry_price - sl)
        target_dist = abs(tgt - entry_price)
        risk_reward = round(target_dist / (risk_dist + 1e-10), 2)

        return {
            "symbol": clean_sym,
            "name": name,
            "price": entry_price,
            "change": round(change, dec),
            "change_percentage": round(change_pct, 2),
            "open": round(open_p, dec),
            "high": round(high_p, dec),
            "low": round(low_p, dec),
            "volume": round(vol, 2),
            "signal": signal,
            "action": action,
            "quantity": 1,
            "entry_price": entry_price,
            "stop_loss": sl,
            "target": tgt,
            "risk_reward": risk_reward,
            "target_profit": round(target_dist * 1, dec),
            "max_risk": round(risk_dist * 1, dec),
            "reason": reason,
            "strategy": strategy,
            "confidence": confidence,
            "market": market,
            "source": "ZERODHA (0-DELAY)",
            "indicators": {
                "day_high": round(high_p, dec),
                "day_low": round(low_p, dec),
                "prev_close": round(float(zq.get("close", entry_price)), dec),
            },
            "timestamp": zq.get("timestamp", datetime.now().isoformat())
        }

    def get_market_tide(self) -> Dict[str, Any]:
        """
        Evaluates benchmark index (NIFTY 50) intraday direction and regime.
        Returns tide ('BULLISH', 'BEARISH', 'NEUTRAL'), change_pct, and rationale.
        """
        try:
            records, ind_df = self._fetch_and_prepare("NIFTY", interval="5m", limit=30)
            if ind_df is None or len(ind_df) < 5:
                return {"tide": "NEUTRAL", "change_pct": 0.0, "reason": "Index data unavailable"}

            last = ind_df.iloc[-1]
            close_p = float(last["close"])
            vwap = float(last["vwap"]) if pd.notnull(last.get("vwap")) else close_p
            ema20 = float(last["ema20"]) if pd.notnull(last.get("ema20")) else close_p
            ema50 = float(last["ema50"]) if pd.notnull(last.get("ema50")) else close_p
            first_open = float(ind_df.iloc[0]["open"]) if float(ind_df.iloc[0]["open"]) > 0 else close_p
            change_pct = ((close_p - first_open) / first_open * 100.0)

            if close_p > vwap and ema20 >= ema50 and change_pct > 0.05:
                return {"tide": "BULLISH", "change_pct": round(change_pct, 2), "reason": f"NIFTY Bullish above VWAP ({change_pct:+.2f}%)"}
            elif close_p < vwap and ema20 <= ema50 and change_pct < -0.05:
                return {"tide": "BEARISH", "change_pct": round(change_pct, 2), "reason": f"NIFTY Bearish below VWAP ({change_pct:+.2f}%)"}
            else:
                return {"tide": "NEUTRAL", "change_pct": round(change_pct, 2), "reason": f"NIFTY Range-Bound / Consolidation ({change_pct:+.2f}%)"}
        except Exception as e:
            logger.debug("Error computing market tide: %s", e)
            return {"tide": "NEUTRAL", "change_pct": 0.0, "reason": "Index feed error"}

    def check_time_of_day_filter(self) -> Tuple[bool, str]:
        """
        Checks if current Indian market time (IST) falls in the Golden Trading Hours
        or high-risk trap zones (opening whipsaw / lunch chop).
        Returns (is_optimal, reason).
        """
        try:
            from datetime import timezone, timedelta
            import datetime as dt_module
            ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
            t = ist_now.time()

            # 09:15 - 09:30: Opening whipsaw / institutional stop-hunt
            if dt_module.time(9, 15) <= t < dt_module.time(9, 30):
                return False, "Opening Whipsaw Trap (09:15-09:30 IST) — High false breakout risk"
            # 12:00 - 13:15: European open / lunch low-liquidity consolidation
            if dt_module.time(12, 0) <= t < dt_module.time(13, 15):
                return False, "Lunch Consolidation Doldrums (12:00-13:15 IST) — Low volume chop"
            # 15:15 - 15:30: MIS square-off erratic volatility
            if dt_module.time(15, 15) <= t <= dt_module.time(15, 30):
                return False, "Market Close Square-Off (15:15-15:30 IST) — End-of-day rush"

            return True, "Golden Momentum Window (High-Conviction Trading Hours)"
        except Exception:
            return True, "Market Hours"

    def get_macro_trend(self, symbol: str) -> Dict[str, Any]:
        """
        Evaluates 15-minute higher timeframe trend for directional macro concurrence.
        """
        clean_sym = symbol.strip().upper().replace("/", "").replace(" ", "").replace("_", "")
        if clean_sym.startswith("TEST"):
            return {"macro_trend": "NEUTRAL", "ema50": None, "aligned": True}

        try:
            records_15m, ind_15m = self._fetch_and_prepare(clean_sym, interval="15m", limit=30)
            if ind_15m is None or len(ind_15m) < 10:
                return {"macro_trend": "NEUTRAL", "ema50": None, "aligned": True}

            last_15m = ind_15m.iloc[-1]
            c15 = float(last_15m["close"])
            ema20_15 = float(last_15m["ema20"]) if pd.notnull(last_15m.get("ema20")) else c15
            ema50_15 = float(last_15m["ema50"]) if pd.notnull(last_15m.get("ema50")) else c15

            if c15 > ema50_15 and ema20_15 >= ema50_15:
                return {"macro_trend": "BULLISH", "ema50": round(ema50_15, 2), "aligned": True}
            elif c15 < ema50_15 and ema20_15 <= ema50_15:
                return {"macro_trend": "BEARISH", "ema50": round(ema50_15, 2), "aligned": True}
            else:
                return {"macro_trend": "CONSOLIDATION", "ema50": round(ema50_15, 2), "aligned": True}
        except Exception as e:
            logger.debug("Error computing macro trend for %s: %s", symbol, e)
            return {"macro_trend": "NEUTRAL", "ema50": None, "aligned": True}

    def _fetch_single_quote(self, symbol: str, use_cache: bool = True) -> Dict[str, Any]:
        """Fetch quote, calculate metrics, and evaluate signal for a single symbol."""
        raw_sym = symbol.strip()
        clean_sym = raw_sym.upper().replace(" ", "")
        yf_sym = self.to_yf_symbol(raw_sym)
        market = get_market_category(raw_sym)
        name = SYMBOL_NAMES.get(clean_sym.replace("/", ""), clean_sym)
        is_forex = (market == "FOREX")
        dec = 4 if is_forex else 2

        cache_key = clean_sym.replace("/", "")
        now_ts = time.time()
        if use_cache and cache_key in self._quote_cache:
            cached_time, cached_quote = self._quote_cache[cache_key]
            if (now_ts - cached_time < self._cache_ttl) and cached_quote.get("price", 0) > 0:
                return cached_quote

        # Zero-delay Zerodha Kite integration if connected
        if self.data_source == "ZERODHA" and zerodha_client.is_connected and not is_forex:
            try:
                z_quotes = zerodha_client.get_quotes([clean_sym])
                if clean_sym in z_quotes:
                    q = self._build_zerodha_quote_payload(clean_sym, name, market, z_quotes[clean_sym], dec)
                    self._quote_cache[cache_key] = (now_ts, q)
                    return q
            except Exception as e:
                logger.warning("Failed to fetch Zerodha quote for %s: %s", clean_sym, e)

        try:
            ticker = yfinance.Ticker(yf_sym)
            hist = ticker.history(period="1d", interval="5m")
            if hist is None or hist.empty or len(hist) < 5:
                hist_fallback = ticker.history(period="5d", interval="5m")
                if hist_fallback is not None and not hist_fallback.empty:
                    hist = hist_fallback

            if hist is None or hist.empty:
                if cache_key in self._quote_cache and self._quote_cache[cache_key][1].get("price", 0) > 0:
                    return self._quote_cache[cache_key][1]
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

            # Evaluate signal strictly through quantitative strategy engine
            signal = "HOLD"
            strat_sig = None
            if len(ind_df) >= 25:
                for strat in self.strategies:
                    sig = strat.evaluate(ind_df, -1)
                    if sig and "signal" in sig:
                        strat_sig = sig
                        signal = sig["signal"]
                        break

            # Derive actionable trade parameters with guaranteed structural brackets
            entry_price = round(close_p, dec)
            quantity = 1
            min_step = 0.0001 if is_forex else 0.05

            # Structural brackets calibrated for Intraday/Swing trading (min 1.0% stop-loss buffer, 1.5% target)
            structural_risk = max(close_p * 0.010, 2.0 * atr)
            structural_reward = max(structural_risk * 1.5, close_p * 0.015)

            if signal == "BUY":
                action = "BUY"
                confidence = float(strat_sig.get("confidence", 0.82)) if strat_sig else 0.82
                strategy_name = strat_sig.get("strategy", "Scalp Pullback Strategy") if strat_sig else "Scalp Pullback Strategy"
                reason = strat_sig.get("reason", "Bullish momentum & 20 EMA pullback test") if (strat_sig and strat_sig.get("reason")) else "Bullish momentum & 20 EMA pullback test"

                sl = round(close_p - structural_risk, dec)
                if sl >= entry_price:
                    sl = round(entry_price - min_step, dec)

                tgt = round(close_p + structural_reward, dec)
                if tgt <= entry_price:
                    tgt = round(entry_price + min_step, dec)

            elif signal == "SELL":
                action = "SELL"
                confidence = float(strat_sig.get("confidence", 0.82)) if strat_sig else 0.82
                strategy_name = strat_sig.get("strategy", "Scalp Breakout Strategy") if strat_sig else "Scalp Breakout Strategy"
                reason = strat_sig.get("reason", "Bearish rejection at resistance & downward EMA alignment") if (strat_sig and strat_sig.get("reason")) else "Bearish rejection at resistance & downward EMA alignment"

                sl = round(close_p + structural_risk, dec)
                if sl <= entry_price:
                    sl = round(entry_price + min_step, dec)

                tgt = round(close_p - structural_reward, dec)
                if tgt >= entry_price:
                    tgt = round(entry_price - min_step, dec)

            else:
                action = "WAIT"
                confidence = 0.50
                strategy_name = "Consolidation"
                reason = "Consolidation / neutral range; awaiting breakout or 20 EMA pullback test"

                sl = round(close_p - structural_risk, dec)
                if sl >= entry_price:
                    sl = round(entry_price - min_step, dec)

                tgt = round(close_p + structural_reward, dec)
                if tgt <= entry_price:
                    tgt = round(entry_price + min_step, dec)

            risk_dist = abs(entry_price - sl)
            target_dist = abs(tgt - entry_price)
            risk_reward = round(target_dist / (risk_dist + 1e-10), 2)

            # Pre-flight check: ensure R:R meets minimum requirement for active orders
            if action in ("BUY", "SELL") and risk_reward < 0.8:
                action = "WAIT"
                reason = f"Trade invalid: Risk/Reward ratio {risk_reward} below minimum 0.8"
                confidence = 0.40

            # Institutional Pre-Flight Quality Gates to maximize Win Rate
            market_tide = "NEUTRAL"
            macro_trend = "NEUTRAL"
            if action in ("BUY", "SELL"):
                # 1. Market Tide Filter (for NSE Equities)
                if getattr(settings, "ENABLE_MARKET_TIDE_FILTER", True) and market == "NSE" and not clean_sym.startswith("TEST") and clean_sym != "NIFTY":
                    tide_info = self.get_market_tide()
                    market_tide = tide_info.get("tide", "NEUTRAL")
                    if action == "BUY" and market_tide == "BEARISH":
                        action = "WAIT"
                        confidence = 0.50
                        reason = f"Filtered by Market Tide: NIFTY Bearish ({tide_info.get('change_pct', 0.0):+.2f}%); avoiding Long bull trap"
                    elif action == "SELL" and market_tide == "BULLISH":
                        action = "WAIT"
                        confidence = 0.50
                        reason = f"Filtered by Market Tide: NIFTY Bullish ({tide_info.get('change_pct', 0.0):+.2f}%); avoiding Short squeeze trap"

                # 2. Time-of-Day Filter (Avoiding opening whipsaw and lunch chop)
                if action in ("BUY", "SELL") and getattr(settings, "ENABLE_TIME_OF_DAY_FILTER", True) and market == "NSE" and not clean_sym.startswith("TEST"):
                    is_optimal, time_reason = self.check_time_of_day_filter()
                    if not is_optimal:
                        action = "WAIT"
                        confidence = 0.52
                        reason = f"Filtered by Time Window: {time_reason}"

                # 3. Macro 15m Trend Alignment Filter
                if action in ("BUY", "SELL") and getattr(settings, "ENABLE_MACRO_TREND_FILTER", True) and not clean_sym.startswith("TEST"):
                    macro_info = self.get_macro_trend(clean_sym)
                    macro_trend = macro_info.get("macro_trend", "NEUTRAL")
                    if action == "BUY" and macro_trend == "BEARISH":
                        action = "WAIT"
                        confidence = 0.48
                        reason = f"Filtered by 15m Macro Trend: Higher timeframe (15m) is Bearish below EMA50"
                    elif action == "SELL" and macro_trend == "BULLISH":
                        action = "WAIT"
                        confidence = 0.48
                        reason = f"Filtered by 15m Macro Trend: Higher timeframe (15m) is Bullish above EMA50"
                    elif (action == "BUY" and macro_trend == "BULLISH") or (action == "SELL" and macro_trend == "BEARISH"):
                        confidence = min(0.95, round(confidence + 0.05, 2))
                        reason += " | Confirmed by 15m Macro Alignment"

            target_profit = round(target_dist * quantity, dec)
            max_risk = round(risk_dist * quantity, dec)

            quote_payload = {
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
                "market_tide": market_tide,
                "macro_trend": macro_trend,
                "patterns": strat_sig.get("patterns", []) if strat_sig else (detect_all_patterns(ind_df, -1) if len(ind_df) >= 20 else []),
                "indicators": {
                    "rsi": round(float(last_candle["rsi"]), 2) if pd.notnull(last_candle.get("rsi")) else None,
                    "ema20": round(float(last_candle["ema20"]), dec) if pd.notnull(last_candle.get("ema20")) else None,
                    "ema50": round(float(last_candle["ema50"]), dec) if pd.notnull(last_candle.get("ema50")) else None,
                    "vwap": round(float(last_candle["vwap"]), dec) if pd.notnull(last_candle.get("vwap")) else None,
                },
                "suggested_window": 60 if (pd.notnull(last_candle.get("adx")) and float(last_candle["adx"]) >= 35.0) else (45 if (pd.notnull(last_candle.get("adx")) and float(last_candle["adx"]) >= 22.0) else 30),
                "timestamp": str(last_candle.get("timestamp", datetime.now().isoformat()))
            }
            self._quote_cache[cache_key] = (now_ts, quote_payload)
            return quote_payload
        except Exception as e:
            logger.warning("Error fetching quote for %s: %s", symbol, e)
            if cache_key in self._quote_cache and self._quote_cache[cache_key][1].get("price", 0) > 0:
                return self._quote_cache[cache_key][1]
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
                "patterns": [],
                "indicators": {},
                "timestamp": datetime.now().isoformat()
            }

    def get_watchlist_quotes(self, symbols: List[str], use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch watchlist quotes concurrently for a list of symbols with Zerodha batch optimization."""
        if not symbols:
            return []

        clean_symbols = [s.strip() for s in symbols if s and s.strip()]
        if not clean_symbols:
            return []

        # If Zerodha is connected and data_source is ZERODHA, batch fetch Indian equities via Zerodha
        if self.data_source == "ZERODHA" and zerodha_client.is_connected:
            try:
                nse_symbols = [s for s in clean_symbols if get_market_category(s) == "NSE"]
                z_quotes = zerodha_client.get_quotes(nse_symbols) if nse_symbols else {}
                
                quotes = []
                remaining_symbols = []
                for s in clean_symbols:
                    raw_sym = s.strip()
                    clean_sym = raw_sym.upper().replace(" ", "").replace("/", "")
                    market = get_market_category(raw_sym)
                    name = SYMBOL_NAMES.get(clean_sym, clean_sym)
                    dec = 4 if market == "FOREX" else 2

                    if clean_sym in z_quotes:
                        q = self._build_zerodha_quote_payload(clean_sym, name, market, z_quotes[clean_sym], dec)
                        self._quote_cache[clean_sym] = (time.time(), q)
                        quotes.append(q)
                    else:
                        remaining_symbols.append(raw_sym)

                if remaining_symbols:
                    from concurrent.futures import ThreadPoolExecutor
                    from functools import partial
                    fetch_fn = partial(self._fetch_single_quote, use_cache=use_cache)
                    with ThreadPoolExecutor(max_workers=min(len(remaining_symbols), 4)) as executor:
                        rem_quotes = list(executor.map(fetch_fn, remaining_symbols))
                        quotes.extend([q for q in rem_quotes if q is not None])

                final_z = [q for q in quotes if q is not None]
                try:
                    for q in final_z:
                        if q and "symbol" in q and "price" in q and float(q.get("price", 0)) > 0:
                            paper_broker.update_market_price(q["symbol"], float(q["price"]))
                except Exception as sync_e:
                    logger.debug("Error syncing paper positions from Zerodha quotes: %s", sync_e)
                return final_z
            except Exception as e:
                logger.warning("Batch Zerodha watchlist fetch error: %s", e)

        from concurrent.futures import ThreadPoolExecutor
        from functools import partial
        fetch_fn = partial(self._fetch_single_quote, use_cache=use_cache)
        max_workers = min(len(clean_symbols), 8)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            quotes = list(executor.map(fetch_fn, clean_symbols))

        final_quotes = [q for q in quotes if q is not None]
        try:
            for q in final_quotes:
                if q and "symbol" in q and "price" in q and float(q.get("price", 0)) > 0:
                    paper_broker.update_market_price(q["symbol"], float(q["price"]))
        except Exception as sync_e:
            logger.debug("Error syncing paper positions from watchlist quotes: %s", sync_e)

        return final_quotes

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
                        
                        # If Zerodha is active, overwrite latest candle close with 0-delay tick
                        if self.data_source == "ZERODHA" and zerodha_client.is_connected:
                            try:
                                z_quotes = zerodha_client.get_quotes([self._symbol])
                                if self._symbol in z_quotes and z_quotes[self._symbol].get("price", 0) > 0:
                                    z_p = float(z_quotes[self._symbol]["price"])
                                    close_p = z_p
                                    latest_candle["close"] = close_p
                                    latest_candle["high"] = max(float(latest_candle.get("high", close_p)), close_p)
                                    latest_candle["low"] = min(float(latest_candle.get("low", close_p)), close_p)
                                    latest_candle["volume"] = float(z_quotes[self._symbol].get("volume", latest_candle.get("volume", 0)))
                            except Exception as ze:
                                logger.debug("Could not fetch Zerodha stream tick for %s: %s", self._symbol, ze)

                        raw_ts = latest_candle.get("timestamp")
                        candle_dt = pd.to_datetime(raw_ts).to_pydatetime() if raw_ts else None

                        # Update paper positions
                        sym_inv_reason = None
                        try:
                            with SessionLocal() as db_curr:
                                curr_pos = db_curr.query(Position).filter(Position.symbol == self._symbol).first()
                                if curr_pos and not curr_pos.symbol.startswith("TEST"):
                                    h = self.evaluate_position_health(self._symbol, curr_pos.side, curr_pos.average_price, close_p, df_with_indicators=ind_df)
                                    if h.get("health_status") == "RELEASE_STOCK" and h.get("trend_shift"):
                                        sym_inv_reason = h.get("invalidation_reason") or "Pattern & Trend Shift Invalidation"
                        except Exception as che:
                            logger.debug("Error checking health for %s: %s", self._symbol, che)

                        triggers = paper_broker.update_market_price(self._symbol, close_p, invalidation_reason=sym_inv_reason)
                        try:
                            with SessionLocal() as db_pos:
                                other_positions = db_pos.query(Position).filter(Position.symbol != self._symbol).all()
                                for opos in other_positions:
                                    if opos.symbol.startswith("TEST"):
                                        continue
                                    cached = self._quote_cache.get(opos.symbol.upper())
                                    if cached and cached[1] and cached[1].get("price"):
                                        opos_inv = None
                                        try:
                                            oh = self.evaluate_position_health(opos.symbol, opos.side, opos.average_price, float(cached[1]["price"]))
                                            if oh.get("health_status") == "RELEASE_STOCK" and oh.get("trend_shift"):
                                                opos_inv = oh.get("invalidation_reason") or "Pattern & Trend Shift Invalidation"
                                        except Exception:
                                            pass
                                        other_trigs = paper_broker.update_market_price(opos.symbol, float(cached[1]["price"]), db=db_pos, invalidation_reason=opos_inv)
                                        if other_trigs:
                                            triggers.extend(other_trigs)
                        except Exception as loop_e:
                            logger.debug("Error updating other positions in stream loop: %s", loop_e)

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

    def get_trend_analysis(self, symbol: str, interval: str = "5m") -> Dict[str, Any]:
        """Analyze multi-factor trend and derive mathematically calibrated suggested trade window."""
        clean_sym = symbol.strip().upper().replace("/", "").replace(" ", "").replace("_", "")
        name = SYMBOL_NAMES.get(clean_sym, symbol)
        candles = self.get_latest_candles(symbol, interval=interval, limit=60)

        if not candles or len(candles) < 5:
            return {
                "symbol": clean_sym,
                "name": name,
                "price": 0.0,
                "trend": "CONSOLIDATION",
                "trend_label": "Consolidation Range",
                "regime": "Range-bound Consolidation",
                "indicators": {},
                "day_range": {"high": 0.0, "low": 0.0, "open": 0.0},
                "velocity": {"candles_for_1pct": 6, "est_minutes_for_target": 30},
                "suggested_window_minutes": 30,
                "suggested_window_label": "30 Minutes (Default Standard)",
                "rationale": "Insufficient historical candles; defaulting to standard 30-minute swing window."
            }

        df = pd.DataFrame(candles)
        last = df.iloc[-1]
        close = float(last["close"])
        open_p = float(last["open"])
        high_p = float(df["high"].max())
        low_p = float(df["low"].min())

        ema20 = float(last["ema20"]) if pd.notnull(last.get("ema20")) else close
        ema50 = float(last["ema50"]) if pd.notnull(last.get("ema50")) else close
        rsi = float(last["rsi"]) if pd.notnull(last.get("rsi")) else 50.0
        adx = float(last["adx"]) if pd.notnull(last.get("adx")) else 20.0
        atr = float(last["atr"]) if pd.notnull(last.get("atr")) else (close * 0.005)
        vwap = float(last["vwap"]) if pd.notnull(last.get("vwap")) else close

        # Trend Direction
        if close > ema20 > ema50 and rsi > 52 and (vwap == 0 or close >= vwap):
            trend = "BULLISH_EXPANSION"
            trend_label = "Bullish Trend Expansion"
        elif close < ema20 < ema50 and rsi < 48 and (vwap == 0 or close <= vwap):
            trend = "BEARISH_EXPANSION"
            trend_label = "Bearish Trend Expansion"
        elif close < ema20 and ema20 > ema50:
            trend = "PULLBACK_TEST"
            trend_label = "Bullish Pullback Test"
        elif close > ema20 and ema20 < ema50:
            trend = "COUNTER_BOUNCE"
            trend_label = "Bearish Rejection Bounce"
        else:
            trend = "CONSOLIDATION"
            trend_label = "Consolidation Range"

        # Regime based on ADX
        if adx >= 35.0:
            regime = "Strong Directional Trend"
        elif adx >= 22.0:
            regime = "Moderate Trend Momentum"
        else:
            regime = "Range-bound Consolidation"

        # Volatility & Target Velocity
        atr_pct = (atr / close) * 100.0 if close > 0 else 0.2
        candles_for_1pct = max(2, round(1.0 / (atr_pct + 1e-6)))
        est_minutes = candles_for_1pct * 5

        # Suggested Trade Holding Window
        if adx >= 35.0 and trend in ["BULLISH_EXPANSION", "BEARISH_EXPANSION"]:
            suggested_window = 60
            window_label = "60 Minutes (Trend Ride)"
            rationale = (
                f"Strong directional trend (ADX {adx:.1f}) in {trend_label}. "
                f"60 minutes (12 candles) allows the directional momentum to fully expand toward targets without premature exit."
            )
        elif adx >= 22.0 or trend in ["PULLBACK_TEST", "COUNTER_BOUNCE"]:
            suggested_window = 45
            window_label = "45 Minutes (Pullback Swing)"
            rationale = (
                f"Moderate momentum (ADX {adx:.1f}) in {trend_label} with ATR ₹{atr:.2f} ({atr_pct:.2f}%/candle). "
                f"45 minutes (9 candles) provides ample duration for structural swing completion."
            )
        else:
            suggested_window = 30
            window_label = "30 Minutes (Intraday Base Window)"
            rationale = (
                f"Range-bound consolidation (ADX {adx:.1f}). "
                f"30 minutes (6 candles) gives sufficient breathing room to break consolidation while maintaining risk discipline."
            )

        is_forex = get_market_category(symbol) == "FOREX"
        dec = 4 if is_forex else 2

        return {
            "symbol": clean_sym,
            "name": name,
            "price": round(close, dec),
            "trend": trend,
            "trend_label": trend_label,
            "regime": regime,
            "indicators": {
                "adx": round(adx, 1),
                "rsi": round(rsi, 1),
                "atr": round(atr, dec),
                "atr_pct": round(atr_pct, 2),
                "ema20": round(ema20, dec),
                "ema50": round(ema50, dec),
                "vwap": round(vwap, dec),
            },
            "day_range": {
                "high": round(high_p, dec),
                "low": round(low_p, dec),
                "open": round(open_p, dec)
            },
            "velocity": {
                "candles_for_1pct": candles_for_1pct,
                "est_minutes_for_target": est_minutes
            },
            "suggested_window_minutes": suggested_window,
            "suggested_window_label": window_label,
            "rationale": rationale
        }

    def evaluate_position_health(
        self,
        symbol: str,
        side: str,
        average_price: float,
        current_price: float,
        candles: Optional[List[Dict[str, Any]]] = None,
        df_with_indicators: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Real-time Trend Shift and Pattern Invalidation Guardian.
        Evaluates whether an active position's underlying trend or pattern has broken down.
        Returns health status ('HEALTHY', 'WARNING', 'RELEASE_STOCK'), recommendation, invalidation reason,
        and list of opposing patterns.
        """
        clean_sym = symbol.strip().upper().replace("/", "").replace(" ", "").replace("_", "")
        if clean_sym.startswith("TEST") or average_price <= 0:
            return {
                "health_status": "HEALTHY",
                "trend_shift": False,
                "recommendation": "HOLD",
                "invalidation_reason": None,
                "invalidation_confidence": 0.0,
                "opposing_patterns": []
            }

        # Fetch latest candles and indicator dataframe if not provided
        if df_with_indicators is None or df_with_indicators.empty:
            records, ind_df = self._fetch_and_prepare(clean_sym, interval=self._interval, limit=60)
        else:
            ind_df = df_with_indicators

        if ind_df is None or len(ind_df) < 5:
            return {
                "health_status": "HEALTHY",
                "trend_shift": False,
                "recommendation": "HOLD",
                "invalidation_reason": None,
                "invalidation_confidence": 0.0,
                "opposing_patterns": []
            }

        last_candle = ind_df.iloc[-1]
        close_p = float(current_price) if current_price > 0 else float(last_candle["close"])
        ema20 = float(last_candle["ema20"]) if pd.notnull(last_candle.get("ema20")) else close_p
        ema50 = float(last_candle["ema50"]) if pd.notnull(last_candle.get("ema50")) else close_p
        vwap = float(last_candle["vwap"]) if pd.notnull(last_candle.get("vwap")) else close_p
        rsi = float(last_candle["rsi"]) if pd.notnull(last_candle.get("rsi")) else 50.0

        detected_patterns = detect_all_patterns(ind_df, -1) if len(ind_df) >= 20 else []

        side_upper = side.upper()
        pnl_pct = ((close_p - average_price) / average_price * 100.0) if side_upper == "BUY" else ((average_price - close_p) / average_price * 100.0)

        # Filter opposing patterns
        if side_upper == "BUY":
            opposing_patterns = [p["pattern"] for p in detected_patterns if p.get("direction") == "SELL"]
            severe_set = {"bearish_engulfing", "shooting_star", "support_breakdown", "vwap_cross_below", "ema_death_crossover"}
            severe_patterns = [p for p in opposing_patterns if p in severe_set]
        else:
            opposing_patterns = [p["pattern"] for p in detected_patterns if p.get("direction") == "BUY"]
            severe_set = {"bullish_engulfing", "hammer", "resistance_breakout", "vwap_cross_above", "ema_golden_crossover"}
            severe_patterns = [p for p in opposing_patterns if p in severe_set]

        # Base confidence from detected opposing patterns
        max_opposing_strength = 0.0
        for p in detected_patterns:
            p_dir = p.get("direction")
            if (side_upper == "BUY" and p_dir == "SELL") or (side_upper == "SELL" and p_dir == "BUY"):
                max_opposing_strength = max(max_opposing_strength, float(p.get("strength", 0.70)))

        is_sub_vwap = (vwap > 0 and close_p < vwap)
        is_above_vwap = (vwap > 0 and close_p > vwap)
        is_bearish_ema = (ema20 < ema50)
        is_bullish_ema = (ema20 > ema50)
        is_severe_break = (is_sub_vwap and is_bearish_ema) if side_upper == "BUY" else (is_above_vwap and is_bullish_ema)

        # Confluence boosters
        pattern_confluence = 0.05 if len(opposing_patterns) >= 2 else 0.0
        structural_confluence = 0.08 if is_severe_break else (0.04 if (is_sub_vwap if side_upper == "BUY" else is_above_vwap) else 0.0)
        rsi_confluence = 0.05 if (rsi < 40 if side_upper == "BUY" else rsi > 60) else 0.0
        loss_confluence = 0.05 if pnl_pct < -0.35 else 0.0

        if max_opposing_strength > 0:
            invalidation_confidence = round(min(0.95, max_opposing_strength + pattern_confluence + structural_confluence + loss_confluence), 2)
        elif is_severe_break and pnl_pct < -0.25:
            invalidation_confidence = round(min(0.90, 0.76 + structural_confluence + rsi_confluence + loss_confluence), 2)
        elif is_severe_break:
            invalidation_confidence = 0.74
        elif (is_sub_vwap if side_upper == "BUY" else is_above_vwap) or (is_bearish_ema if side_upper == "BUY" else is_bullish_ema):
            invalidation_confidence = 0.62
        else:
            invalidation_confidence = 0.20

        # Evaluate Trend Invalidation (Strict 80% Confidence Gate)
        health_status = "HEALTHY"
        trend_shift = False
        recommendation = "HOLD — Setup Intact"
        invalidation_reason = None

        conf_pct = int(invalidation_confidence * 100)
        from backend.core.config import settings
        min_release_conf = getattr(settings, "MIN_RELEASE_CONFIDENCE", 0.80)

        if invalidation_confidence >= min_release_conf and pnl_pct < 0:
            health_status = "RELEASE_STOCK"
            trend_shift = True
            if severe_patterns:
                invalidation_reason = f"Opposing Pattern: {', '.join(severe_patterns)} ({conf_pct}% confidence)"
                recommendation = f"RELEASE STOCK ({conf_pct}% Invalidation Confidence)"
            elif is_severe_break:
                invalidation_reason = f"Trend Shift: Lost VWAP & EMA cross ({conf_pct}% confidence)"
                recommendation = f"RELEASE STOCK ({conf_pct}% Invalidation Confidence)"
            else:
                invalidation_reason = f"Opposing Momentum ({conf_pct}% confidence)"
                recommendation = f"RELEASE STOCK ({conf_pct}% Invalidation Confidence)"
        elif invalidation_confidence >= 0.60 or pnl_pct < -0.40:
            health_status = "WARNING"
            trend_shift = False
            invalidation_reason = f"Momentum softening ({conf_pct}% risk, below 80% release threshold)"
            recommendation = f"CAUTION — Momentum Softening ({conf_pct}%)"
        else:
            health_status = "HEALTHY"
            trend_shift = False
            invalidation_reason = None
            recommendation = "HOLD — Pattern & Trend Intact"

        return {
            "health_status": health_status,
            "trend_shift": trend_shift,
            "recommendation": recommendation,
            "invalidation_reason": invalidation_reason,
            "invalidation_confidence": invalidation_confidence,
            "opposing_patterns": opposing_patterns
        }


live_service = LiveMarketService()
live_market_service = live_service


"""Zerodha Kite Live Client supporting Official Kite Connect API and Kite Web Enctoken."""
import requests
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from backend.core.logging import logger
from backend.core.config import settings

try:
    from kiteconnect import KiteConnect, KiteTicker
except ImportError:
    KiteConnect = None
    KiteTicker = None


class BrokerInterface(ABC):
    """Unified Broker Interface decoupling application logic from execution venue."""

    @abstractmethod
    def get_quotes(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass


class ZerodhaBroker(BrokerInterface):
    """
    Zerodha Kite Connect Execution Adapter.
    Strictly isolated: In Version 1, trading execution remains in PAPER mode.
    """
    def __init__(self):
        self.api_key = settings.ZERODHA_API_KEY
        self.api_secret = settings.ZERODHA_API_SECRET
        self.access_token = settings.ZERODHA_ACCESS_TOKEN
        self.connected = False

    def connect(self) -> bool:
        if settings.TRADING_MODE != "LIVE":
            logger.warning("ZerodhaBroker: Live trading is disabled. TRADING_MODE is %s", settings.TRADING_MODE)
            return False

        if not (self.api_key and self.access_token):
            logger.error("ZerodhaBroker: Missing API credentials.")
            return False

        self.connected = True
        logger.info("ZerodhaBroker initialized.")
        return True

    def get_quotes(self, symbol: str) -> Dict[str, Any]:
        if not self.connected:
            raise RuntimeError("ZerodhaBroker not connected.")
        return {"symbol": symbol, "status": "stub"}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_balance(self) -> Dict[str, Any]:
        return {"available_cash": 0.0}

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        if settings.TRADING_MODE != "LIVE":
            raise PermissionError("Direct broker order rejected: Version 1 is strictly PAPER mode.")
        raise NotImplementedError("Live Zerodha execution scheduled for Version 2 with human sign-off.")

    def cancel_order(self, order_id: str) -> bool:
        return False


class ZerodhaLiveClient:
    """
    Zero-Delay Real-Time Market Data Client for Zerodha Kite.
    Supports both:
    1. Official Kite Connect API (API Key + Access Token)
    2. Kite Web Session (Enctoken - 100% Free with zero monthly charges)
    """

    def __init__(self):
        self.mode: str = "DISCONNECTED"  # "ENCTOKEN", "API_KEY", "DISCONNECTED"
        self.is_connected: bool = False
        self.user_id: Optional[str] = None
        self.user_name: Optional[str] = None
        self.enctoken: Optional[str] = None
        self.api_key: Optional[str] = None
        self.access_token: Optional[str] = None
        self.kite: Optional[Any] = None
        self.kws: Optional[Any] = None
        self._last_tick_cache: Dict[str, Dict[str, Any]] = {}
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://kite.zerodha.com/"
        })

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected,
            "mode": self.mode,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "broker": "Zerodha Kite",
            "data_source": "ZERODHA" if self.is_connected else "YFINANCE"
        }

    def connect_with_enctoken(self, enctoken: str) -> Tuple[bool, str]:
        """Validate and connect using Kite Web enctoken cookie."""
        clean_token = enctoken.strip()
        if not clean_token:
            return False, "Enctoken cannot be empty."

        try:
            # Test enctoken by querying Zerodha OMS profile
            headers = {
                "Authorization": f"enctoken {clean_token}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
            resp = self._session.get("https://kite.zerodha.com/oms/user/profile/full", headers=headers, timeout=6.0)
            
            # If 403 / 401 or invalid response
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    user_data = data.get("data", {})
                    self.user_id = user_data.get("user_id", "Zerodha User")
                    self.user_name = user_data.get("user_name", self.user_id)
                    self.enctoken = clean_token
                    self.mode = "ENCTOKEN"
                    self.is_connected = True
                    logger.info("ZerodhaLiveClient connected via Enctoken for %s (%s)", self.user_name, self.user_id)
                    return True, f"Successfully connected to Zerodha Kite as {self.user_name} ({self.user_id})!"
                else:
                    return False, data.get("message", "Invalid enctoken response from Zerodha.")
            
            # Try alternate quote endpoint verification if profile endpoint differs
            test_resp = self._session.get("https://kite.zerodha.com/oms/quote?i=NSE:RELIANCE", headers=headers, timeout=6.0)
            if test_resp.status_code == 200:
                tdata = test_resp.json()
                if tdata.get("status") == "success" and "data" in tdata:
                    self.user_id = "Zerodha User"
                    self.user_name = "Live Kite Session"
                    self.enctoken = clean_token
                    self.mode = "ENCTOKEN"
                    self.is_connected = True
                    logger.info("ZerodhaLiveClient connected via Enctoken quote verification.")
                    return True, "Successfully connected to Zerodha Kite Web Session!"

            return False, f"Zerodha authentication failed (HTTP {resp.status_code}). Please verify your enctoken cookie."

        except Exception as e:
            logger.error("ZerodhaLiveClient enctoken connection error: %s", e)
            return False, f"Connection failed: {str(e)}"

    def connect_with_api_key(self, api_key: str, access_token: str) -> Tuple[bool, str]:
        """Validate and connect using official Kite Connect credentials."""
        clean_key = api_key.strip()
        clean_token = access_token.strip()
        if not clean_key or not clean_token:
            return False, "API Key and Access Token are required."

        if KiteConnect is None:
            return False, "kiteconnect package is not installed."

        try:
            kite = KiteConnect(api_key=clean_key)
            kite.set_access_token(clean_token)
            profile = kite.profile()
            self.user_id = profile.get("user_id", "Kite Developer")
            self.user_name = profile.get("user_name", self.user_id)
            self.api_key = clean_key
            self.access_token = clean_token
            self.kite = kite
            self.mode = "API_KEY"
            self.is_connected = True
            logger.info("ZerodhaLiveClient connected via API Key for %s (%s)", self.user_name, self.user_id)
            return True, f"Successfully connected to Zerodha Kite API as {self.user_name} ({self.user_id})!"

        except Exception as e:
            logger.error("ZerodhaLiveClient API key connection error: %s", e)
            return False, f"Kite API connection failed: {str(e)}"

    def disconnect(self):
        """Disconnect and clear credentials."""
        self.is_connected = False
        self.mode = "DISCONNECTED"
        self.user_id = None
        self.user_name = None
        self.enctoken = None
        self.api_key = None
        self.access_token = None
        self.kite = None
        self._last_tick_cache.clear()
        logger.info("ZerodhaLiveClient disconnected.")

    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch real-time zero-delay quotes from Zerodha for list of symbols.
        Returns normalized dictionary keyed by symbol (e.g. 'RELIANCE', 'TCS').
        """
        if not self.is_connected:
            return {}

        results = {}

        if self.mode == "ENCTOKEN" and self.enctoken:
            try:
                # Format symbols: e.g. NSE:RELIANCE, NSE:TCS
                instruments = []
                for s in symbols:
                    sym_clean = s.strip().upper().replace(" ", "")
                    if sym_clean in ("USDINR", "EURUSD", "GBPUSD", "USDJPY"):
                        instruments.append(f"CDS:{sym_clean}")
                    elif sym_clean in ("NIFTY", "BANKNIFTY"):
                        instruments.append(f"NSE:{sym_clean} 50")
                    else:
                        instruments.append(f"NSE:{sym_clean}")

                params = [("i", inst) for inst in instruments]
                headers = {"Authorization": f"enctoken {self.enctoken}"}
                resp = self._session.get("https://kite.zerodha.com/oms/quote", params=params, headers=headers, timeout=4.0)

                if resp.status_code == 200:
                    payload = resp.json()
                    if payload.get("status") == "success" and "data" in payload:
                        data = payload["data"]
                        for inst_key, q in data.items():
                            clean_k = inst_key.split(":")[-1].replace(" 50", "").strip()
                            ohlc = q.get("ohlc", {})
                            last_price = float(q.get("last_price", 0.0))
                            prev_close = float(ohlc.get("close", last_price))
                            change = float(q.get("net_change", last_price - prev_close))
                            change_pct = (change / prev_close * 100.0) if prev_close > 0 else 0.0

                            quote_item = {
                                "symbol": clean_k,
                                "price": last_price,
                                "change": round(change, 2),
                                "change_percentage": round(change_pct, 2),
                                "open": float(ohlc.get("open", last_price)),
                                "high": float(ohlc.get("high", last_price)),
                                "low": float(ohlc.get("low", last_price)),
                                "close": prev_close,
                                "volume": float(q.get("volume", 0)),
                                "timestamp": datetime.now().isoformat(),
                                "source": "ZERODHA_ENCTOKEN"
                            }
                            results[clean_k] = quote_item
                            self._last_tick_cache[clean_k] = quote_item
            except Exception as e:
                logger.warning("ZerodhaLiveClient enctoken quote fetch error: %s", e)

        elif self.mode == "API_KEY" and self.kite:
            try:
                inst_list = [f"NSE:{s.strip().upper()}" for s in symbols]
                q_dict = self.kite.quote(inst_list)
                for inst_key, q in q_dict.items():
                    clean_k = inst_key.split(":")[-1].strip()
                    ohlc = q.get("ohlc", {})
                    last_price = float(q.get("last_price", 0.0))
                    prev_close = float(ohlc.get("close", last_price))
                    change = float(q.get("net_change", last_price - prev_close))
                    change_pct = (change / prev_close * 100.0) if prev_close > 0 else 0.0

                    quote_item = {
                        "symbol": clean_k,
                        "price": last_price,
                        "change": round(change, 2),
                        "change_percentage": round(change_pct, 2),
                        "open": float(ohlc.get("open", last_price)),
                        "high": float(ohlc.get("high", last_price)),
                        "low": float(ohlc.get("low", last_price)),
                        "close": prev_close,
                        "volume": float(q.get("volume", 0)),
                        "timestamp": datetime.now().isoformat(),
                        "source": "ZERODHA_KITE_API"
                    }
                    results[clean_k] = quote_item
                    self._last_tick_cache[clean_k] = quote_item
            except Exception as e:
                logger.warning("ZerodhaLiveClient API quote fetch error: %s", e)

        return results


# Global singleton instance
zerodha_client = ZerodhaLiveClient()

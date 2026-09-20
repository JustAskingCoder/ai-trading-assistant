"""BrokerInterface abstraction and future Zerodha Kite Connect integration."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from backend.core.logging import logger
from backend.core.config import settings


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
    Future Zerodha Kite Connect Adapter.
    DISABLED by default in Version 1.
    Requires explicit live configuration and human sign-off.
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

        # In Version 2+: initialize KiteConnect(api_key=self.api_key)
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

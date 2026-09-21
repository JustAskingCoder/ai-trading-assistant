"""Zerodha Kite Connect and Enctoken API routes."""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.integrations.zerodha.kite_client import zerodha_client
from backend.data.live_market_service import live_service
from backend.data.market_simulator import simulator
from backend.core.logging import logger

router = APIRouter(prefix="/api/zerodha", tags=["Zerodha Kite Live Feed"])


class ZerodhaConnectRequest(BaseModel):
    mode: str = "ENCTOKEN"  # "ENCTOKEN" or "API_KEY"
    enctoken: Optional[str] = None
    api_key: Optional[str] = None
    access_token: Optional[str] = None


@router.get("/status")
def get_zerodha_status():
    """Get current Zerodha Kite connection status."""
    return zerodha_client.status


@router.post("/connect")
def connect_zerodha(req: ZerodhaConnectRequest):
    """
    Connect to Zerodha Kite using either:
    1. Enctoken (Free Kite Web session)
    2. Official Kite Connect API Key + Access Token
    """
    mode = req.mode.upper().strip()

    if mode == "ENCTOKEN":
        if not req.enctoken or not req.enctoken.strip():
            raise HTTPException(status_code=400, detail="Enctoken is required for Kite Web session mode.")
        success, message = zerodha_client.connect_with_enctoken(req.enctoken)
    elif mode == "API_KEY":
        if not req.api_key or not req.access_token:
            raise HTTPException(status_code=400, detail="API Key and Access Token are required for Developer API mode.")
        success, message = zerodha_client.connect_with_api_key(req.api_key, req.access_token)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid connection mode '{req.mode}'. Must be 'ENCTOKEN' or 'API_KEY'.")

    if not success:
        raise HTTPException(status_code=401, detail=message)

    # Set LiveMarketService data source to Zerodha and start live streaming
    live_service.data_source = "ZERODHA"
    if simulator.is_running:
        simulator.stop()
    live_service.start(symbol="RELIANCE")
    logger.info("Market data source switched to ZERODHA Kite (0-Delay) and LIVE mode activated.")

    return {
        "status": "connected",
        "message": message,
        "mode": zerodha_client.mode,
        "user_id": zerodha_client.user_id,
        "user_name": zerodha_client.user_name,
        "data_source": "ZERODHA"
    }


@router.post("/disconnect")
def disconnect_zerodha():
    """Disconnect Zerodha Kite and fallback to default data source."""
    zerodha_client.disconnect()
    live_service.data_source = "YFINANCE"
    logger.info("Zerodha disconnected. Market data source reverted to default.")
    return {
        "status": "disconnected",
        "message": "Disconnected from Zerodha Kite. Reverted to standard market feed.",
        "data_source": "YFINANCE"
    }

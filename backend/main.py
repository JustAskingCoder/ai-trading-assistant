"""Main FastAPI application entrypoint for AI Trading Assistant."""
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.logging import logger
from backend.database.init_db import init_db
from backend.data.market_simulator import simulator
from backend.data.live_market_service import live_service
from backend.api.routes import market, trading, ai, backtesting, settings as settings_route, zerodha


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing %s v%s...", settings.PROJECT_NAME, settings.VERSION)
    init_db()
    logger.info("Trading Mode: %s (LIVE trading disabled in V1)", settings.TRADING_MODE)

    # Auto-load default dataset into simulator if available
    from pathlib import Path
    sample_file = Path("data/RELIANCE_5m.csv")
    if sample_file.exists():
        try:
            from backend.data.csv_loader import load_csv_to_dataframe
            df, _ = load_csv_to_dataframe(str(sample_file))
            df["symbol"] = "RELIANCE"
            simulator.load_dataset(df)
            logger.info("Pre-loaded %d candles into simulator from %s.", len(df), sample_file)
        except Exception as e:
            logger.warning("Could not pre-load sample data: %s", e)

    # Auto-start live market service for real-time tracking
    try:
        live_service.start(symbol="RELIANCE")
        logger.info("Live market service auto-started for RELIANCE.")
    except Exception as e:
        logger.warning("Could not auto-start live service: %s", e)

    yield
    simulator.stop()
    live_service.stop()
    logger.info("Shutting down %s.", settings.PROJECT_NAME)



app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware for React/Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(market.router)
app.include_router(trading.router)
app.include_router(ai.router)
app.include_router(backtesting.router)
app.include_router(settings_route.router)
app.include_router(zerodha.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": settings.TRADING_MODE,
        "database": "connected",
        "simulator_running": simulator.is_running,
        "live_running": live_service.is_running
    }


@app.websocket("/ws/market")
async def market_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = simulator.subscribe()
    logger.info("WebSocket client connected to /ws/market.")
    try:
        while True:
            # Deliver ticks from queue or listen for client commands
            message = await queue.get()
            await websocket.send_text(json.dumps(message))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        simulator.unsubscribe(queue)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

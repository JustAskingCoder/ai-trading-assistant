"""Market replay simulator broadcasting candle ticks via WebSocket."""
import asyncio
import pandas as pd
from typing import Optional, Dict, Any, List
from backend.indicators.engine import calculate_indicators, get_latest_indicators_summary
from backend.patterns.engine import detect_all_patterns
from backend.strategies.base_strategy import BreakoutStrategy, MomentumStrategy, TrendFollowingStrategy
from backend.paper.paper_broker import paper_broker
from backend.core.logging import logger


class MarketSimulator:
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.speed = 1.0  # 1x, 2x, 5x, 10x, 50x
        self.current_index = 0
        self.data: Optional[pd.DataFrame] = None
        self.subscribers: List[asyncio.Queue] = []
        self.strategies = [BreakoutStrategy(), MomentumStrategy(), TrendFollowingStrategy()]
        self._task: Optional[asyncio.Task] = None

    def load_dataset(self, df: pd.DataFrame):
        self.data = calculate_indicators(df)
        self.current_index = 0
        self.is_running = False
        self.is_paused = False
        logger.info("MarketSimulator loaded %d candles with indicators.", len(self.data))

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.subscribers:
            self.subscribers.remove(q)

    async def _broadcast(self, message: Dict[str, Any]):
        for q in list(self.subscribers):
            try:
                await q.put(message)
            except Exception:
                pass

    async def broadcast(self, message: Dict[str, Any]):
        await self._broadcast(message)

    def start(self, speed: float = 1.0, loop: Optional[asyncio.AbstractEventLoop] = None):
        if self.data is None or self.data.empty:
            raise ValueError("No market data loaded in simulator.")

        self.speed = max(0.1, float(speed))
        if self.is_paused:
            self.is_paused = False
            self.is_running = True
            logger.info("MarketSimulator resumed at %.1fx speed.", self.speed)
            return

        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            if self.current_index >= len(self.data):
                self.current_index = 0
            if self._task and not self._task.done():
                self._task.cancel()

            target_loop = loop
            if target_loop is None:
                try:
                    target_loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass

            if target_loop and target_loop.is_running():
                self._task = target_loop.create_task(self._simulation_loop())
            else:
                self._task = asyncio.create_task(self._simulation_loop())
            logger.info("MarketSimulator started at %.1fx speed from index %d.", self.speed, self.current_index)

    def pause(self):
        self.is_paused = True
        logger.info("MarketSimulator paused at index %d.", self.current_index)

    def stop(self):
        self.is_running = False
        self.is_paused = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("MarketSimulator stopped.")

    def reset(self):
        self.stop()
        self.current_index = 0
        logger.info("MarketSimulator reset to beginning.")

    async def _simulation_loop(self):
        try:
            while self.is_running and self.data is not None and self.current_index < len(self.data):
                if self.is_paused:
                    await asyncio.sleep(0.2)
                    continue

                candle = self.data.iloc[self.current_index]
                symbol = str(candle.get("symbol", "ASSET"))
                close_p = float(candle["close"])
                raw_ts = candle.get("timestamp")
                candle_dt = pd.to_datetime(raw_ts).to_pydatetime() if pd.notnull(raw_ts) else None

                # Update paper positions
                market_events = paper_broker.update_market_price(symbol, close_p, candle_time=candle_dt)
                if market_events:
                    for evt in market_events:
                        if evt.get('type') == 'BREAKEVEN_TRAILED':
                            await manager.broadcast({
                                'type': 'BREAKEVEN_TRAILED',
                                'data': evt
                            })
                        else:
                            await manager.broadcast({
                                'type': 'AUTO_EXIT_TRIGGERED',
                                'data': evt
                            })

                # Detect patterns and evaluate strategies
                current_slice = self.data.iloc[:self.current_index + 1]
                patterns = detect_all_patterns(current_slice, -1) if self.current_index >= 20 else []

                signals = []
                if self.current_index >= 25:
                    for strat in self.strategies:
                        sig = strat.evaluate(current_slice, -1)
                        if sig:
                            signals.append(sig)

                # Format tick payload
                payload = {
                    "type": "CANDLE_UPDATE",
                    "index": self.current_index,
                    "total": len(self.data),
                    "timestamp": str(candle.get("timestamp", "")),
                    "symbol": symbol,
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": close_p,
                    "volume": float(candle["volume"]),
                    "indicators": {
                        "ema20": float(candle["ema20"]) if pd.notnull(candle.get("ema20")) else None,
                        "ema50": float(candle["ema50"]) if pd.notnull(candle.get("ema50")) else None,
                        "rsi": float(candle["rsi"]) if pd.notnull(candle.get("rsi")) else None,
                        "vwap": float(candle["vwap"]) if pd.notnull(candle.get("vwap")) else None,
                    },
                    "patterns": patterns,
                    "signals": signals
                }

                await self._broadcast(payload)
                self.current_index += 1

                # Delay between candles (e.g. 1 second per candle divided by speed)
                base_delay = 1.0 / self.speed
                await asyncio.sleep(base_delay)

            self.is_running = False
            await self._broadcast({"type": "SIMULATION_COMPLETE", "index": self.current_index})
        except asyncio.CancelledError:
            self.is_running = False
        except Exception as e:
            logger.error("Error in simulation loop: %s", e)
            self.is_running = False


simulator = MarketSimulator()
manager = simulator

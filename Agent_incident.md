# Agent Incident & Post-Mortem Log (`Agent_incident.md`)

> **Notice to Successor AI Agents**: This document records real engineering incidents, mistaken architectural decisions, and bug post-mortems encountered during the iterative development of the **AI Trading Assistant**. Read this file before proposing or implementing changes to ensure you do not repeat past failures.

---

## Index of Incidents

| ID | Incident Title | Severity | Component | Root Cause Category |
|---|---|---|---|---|
| **INC-001** | Simulator Async Event Loop Crash | High | `backend/api/routes/market.py` | Sync/Async Impedance Mismatch |
| **INC-002** | AI Schema Validation Crash (`PydanticUserError`) | High | `backend/ai/schemas.py` | Missing Type Annotation Import |
| **INC-003** | Standalone Short/SELL Virtual Position Loss | Critical | `backend/paper/paper_broker.py` | Spot Bias (Long-Only Assumption) |
| **INC-004** | Premature Trade Liquidation (Ultra-Tight SL & 15m Window) | Critical | Strategy & Risk Engine | Over-fitting to Noise / Rigid Timing |
| **INC-005** | Order Rejection on 6-Asset Scanner (`REJECT_MAX_POSITIONS`) | High | `backend/risk/risk_manager.py` | Risk Ceiling vs UI Feature Mismatch |
| **INC-006** | Runaway React Re-Render Infinite Loop | Critical | `frontend/src/.../MultiAssetWatchlist.tsx` | Unmemoized High-Frequency State Loop |
| **INC-007** | Yahoo Finance Rate-Limiting & Thread Starvation | High | `backend/data/live_market_service.py` | Uncached External HTTP Polling |
| **INC-008** | Phantom 5.5-Hour UTC Timezone Skew (`0m 00s left`) | Critical | Backend API Serialization & Frontend Parser | Missing UTC "Z" Designator |
| **INC-009** | Unrealized P&L Siloed to Active Chart Symbol Only | High | `backend/data/live_market_service.py` | UI-Coupled Business Logic |
| **INC-010** | False Signals from Loose Trend Fallbacks ($R:R < 0.8$) | Critical | Strategy Engine & Watchlist Quotes | Speculative Fallback Bias |
| **INC-011** | Test Suite Ledger Pollution (531 Ghost Trades) | Medium | Test Suite & SQLite DB | Shared Test/Dev Environment |
| **INC-012** | OTC Spot Forex Zero-Volume Strategy Failure | High | Indicator & Strategy Engine | Asset Class Assumption Mismatch |
| **INC-013** | Cross-Symbol Candle Ticks Contamination in WebSocket | High | `frontend/src/App.tsx` | Missing Payload Symbol Isolation Guard |

---

## Detailed Post-Mortem Records

### INC-001: Simulator Async Event Loop Crash
* **Symptoms**: Clicking "Play" in the UI failed. Backend threw `RuntimeError: no running event loop` when calling `/api/simulator/control?action=start`.
* **Mistake / Wrong Decision**: The route handler `def control_simulator(...)` was declared as a synchronous Python function (`def`), but internally attempted to access `asyncio.get_event_loop()` to schedule the background replay task. In FastAPI, standard synchronous route handlers run in a separate thread pool (`anyio` worker thread) where no asyncio event loop is attached to the thread.
* **Resolution**:
  1. Converted `control_simulator` in `backend/api/routes/market.py` to `async def`.
  2. In `MarketSimulator.start()`, bound task creation to the running loop via `asyncio.create_task()`.
* **Rule for Next AI**: Any endpoint that interacts with background asyncio workers, WebSockets, or async event loops MUST be declared `async def`.

---

### INC-002: AI Schema Validation Crash (`PydanticUserError`)
* **Symptoms**: Clicking "Analyze with AI" returned HTTP 500. Pydantic raised `PydanticUserError: Cannot resolve type 'Any'`.
* **Mistake / Wrong Decision**: The schema definition in `backend/ai/schemas.py` utilized `Any` in type annotations without importing it from `typing`. Because Pydantic models with delayed string annotations evaluate when an endpoint is first instantiated with a payload, the app started up without syntax errors, but crashed on the first real API invocation.
* **Resolution**:
  1. Added `from typing import Any, Dict, List, Optional` in `backend/ai/schemas.py`.
  2. Added an automated unit test `test_ai_analyze_endpoint` in `tests/test_trading_system.py` verifying full serialization and schema conformity.
* **Rule for Next AI**: Never trust that Python models are valid just because the server starts. Always exercise all endpoint schemas with an automated test fixture.

---

### INC-003: Standalone Short/SELL Virtual Position Loss
* **Symptoms**: Clicking "SELL" or executing a Short setup from the Live Scanner completed with HTTP 200, but no position appeared in `Open Virtual Positions`, and P&L never tracked downward price movement.
* **Mistake / Wrong Decision**: The initial version of `PaperBroker` assumed standard spot equity buying: a `BUY` created a position, and a `SELL` was assumed to be an exit of an existing position. When a user executed a standalone `SELL` without holding shares, `paper_broker` either ignored it or reduced shares to 0.
* **Resolution**:
  1. Refactored `PaperBroker.place_order` to support true bi-directional positions:
     - If no position exists and side is `SELL`, open a `SHORT` position (`quantity < 0` or `side="SELL"`).
     - If a `SHORT` position exists and side is `BUY`, cover/close the short.
     - If quantity exceeds the existing short, flip the position to long.
  2. Updated P&L formula for short trades: $\text{Unrealized P\&L} = (\text{Entry Price} - \text{Current Price}) \times |\text{Quantity}|$.
  3. Corrected `pnl_percentage` in `/api/positions` and dynamic closing action in `/api/positions/{id}/close`.
* **Rule for Next AI**: Trading systems must treat Shorting as a first-class order type with inverse P&L logic. Never assume `SELL` only means "close long position".

---

### INC-004: Premature Trade Liquidation (Ultra-Tight SL & 15m Window)
* **Symptoms**: User reported trade #407 (RELIANCE) closed in only 2 minutes 55 seconds with a loss. Trades were getting liquidated almost immediately after entry.
* **Mistake / Wrong Decision**: Two flawed assumptions collided:
  1. Strategies were calculating Stop-Loss as $\text{Pivot} \pm 0.15\%\text{ ATR}$, which was far tighter than standard 5-minute bid-ask spread and candle volatility.
  2. A rigid 15-minute scalp timer forced liquidation after only 3 five-minute candles, before the trade had time to play out, dumping profitable trades during minor consolidation.
* **Resolution**:
  1. Enforced a **minimum Stop-Loss buffer of 1.0%** (or $2.0\times\text{ATR}$) and Target buffer of $1.5\%$ (or $3.0\times\text{ATR}$) across all base strategies, guaranteeing a healthy $1:1.5$ Risk-to-Reward ratio.
  2. Calibrated holding windows: 30 minutes base, 45 minutes swing, 60 minutes trend ride.
  3. Added **Trailing Breakeven Protection on Expiry**: In `paper_broker.update_market_price`, if a trade is in profit (`unrealized_pnl > 0`) when the window expires, the system trails the Stop-Loss to Breakeven (`pos.stop_loss = pos.average_price`) and extends the window by +15 minutes (up to 90 min max) instead of dumping it.
* **Rule for Next AI**: Never set intraday stop-losses below instrument noise (~0.8%–1.0% for Indian equities). Never arbitrarily dump winning trades on a timer; protect with trailing breakeven instead.

---

### INC-005: Order Rejection on 6-Asset Scanner (`REJECT_MAX_POSITIONS`)
* **Symptoms**: Users attempting to trade multiple opportunities identified by the Multi-Asset Watchlist were rejected with `Order rejected: Maximum open positions limit (3) reached`.
* **Mistake / Wrong Decision**: `MAX_OPEN_POSITIONS = 3` was hardcoded in `config.py` and `risk_manager.py` during early single-asset prototype testing. When the Multi-Asset Scanner expanded to display 6–10 tickers simultaneously, the risk engine was not synchronized with the expanded product scope.
* **Resolution**:
  1. Raised `MAX_OPEN_POSITIONS` to 6 in `backend/core/config.py`, `.env`, and `risk_manager.py`.
  2. Added dynamic headroom check in frontend order modal so users see available position slots.
* **Rule for Next AI**: When expanding UI/scanner capabilities to support $N$ concurrent assets, immediately audit backend risk thresholds (`MAX_OPEN_POSITIONS`, capital sizing) to ensure they accommodate $N$ setups.

---

### INC-006: Runaway React Re-Render Infinite Loop
* **Symptoms**: Browser tab frozen, 100% CPU usage, and high memory consumption on the dashboard.
* **Mistake / Wrong Decision**: In `MultiAssetWatchlist.tsx`, `fetchWatchlist` was called inside a `useEffect` whose dependency array included `onQuotesUpdate`. However, `onQuotesUpdate` was an inline function passed from `App.tsx` that changed reference on every render, triggering an infinite request-render loop.
* **Resolution**:
  1. Decoupled `fetchWatchlist` from the prop function using `useRef` for callbacks.
  2. Memoized `handleWatchlistQuotesUpdate` with `useCallback` in `App.tsx`.
  3. Added shallow equality comparison before setting `setWatchlistQuotes` to bail out of re-renders if prices haven't changed.
* **Rule for Next AI**: Never put parent callback functions directly in polling `useEffect` dependency arrays without wrapping in `useRef` or `useCallback` with shallow state equality guards.

---

### INC-007: Yahoo Finance Rate-Limiting & Thread Starvation
* **Symptoms**: Live market quotes returned HTTP 429 Too Many Requests or hung indefinitely; backend worker threads became unresponsive.
* **Mistake / Wrong Decision**: Fired raw, unthrottled `yfinance` network calls for all symbols on every tick or WebSocket heartbeat without caching.
* **Resolution**:
  1. Implemented a thread-safe `_candle_cache` with a 3-second TTL in `backend/data/live_market_service.py`.
  2. Added concurrent batching via `ThreadPoolExecutor(max_workers=4)` with timeout handling.
  3. Provided graceful fallback to previous cached candle data during network hiccups.
* **Rule for Next AI**: Any free external financial API (especially Yahoo Finance) MUST have short-term caching (3–5s) and bounded concurrency. Never fire unthrottled requests on user interaction loops.

---

### INC-008: Phantom 5.5-Hour UTC Timezone Skew (`0m 00s left`)
* **Symptoms**: As soon as a trade was opened, the Trade Duration Window in `PositionTable.tsx` displayed `⏱ 0m 00s left`, and positions were at risk of immediate auto-expiry.
* **Mistake / Wrong Decision**: The backend SQLite database stored UTC timestamps (`datetime.utcnow()`), and the FastAPI route serialized them as plain strings (e.g. `"2026-09-22T06:45:00"`). JavaScript's `new Date("2026-09-22T06:45:00")` parses timestamps *without* a timezone specifier as **local time** (IST, UTC+05:30). The browser calculated that the trade was entered 5.5 hours ago!
* **Resolution**:
  1. Explicitly appended `"Z"` in the backend serializer: `pos.entry_time.isoformat() + "Z"`.
  2. In `PositionTable.tsx`, ensured dates are parsed with explicit UTC handling: `new Date(pos.entry_time.endsWith("Z") ? pos.entry_time : pos.entry_time + "Z")`.
* **Rule for Next AI**: Always enforce strict ISO 8601 UTC representation with trailing `"Z"` on every timestamp emitted across the REST and WebSocket boundary.

---

### INC-009: Unrealized P&L Siloed to Active Chart Symbol Only
* **Symptoms**: When holding positions in both `RELIANCE` and `TCS`, switching the chart to `RELIANCE` caused the unrealized P&L for `TCS` to stop updating.
* **Mistake / Wrong Decision**: Mark-to-market position updates were originally implemented inside the WebSocket candle handler for the *actively viewed chart symbol*. Non-viewed positions were starved of price updates.
* **Resolution**:
  1. Integrated portfolio price updating into the centralized `live_market_service.get_watchlist_quotes` poller that runs for all tracked symbols.
  2. Added a 3-second portfolio polling fallback in `App.tsx` that queries `GET /api/positions` and updates unrealized P&L for all open positions simultaneously.
* **Rule for Next AI**: Portfolio accounting and mark-to-market calculations must be completely decoupled from UI view state or active charts.

---

### INC-010: False Signals from Loose Trend Fallbacks ($R:R < 0.8$)
* **Symptoms**: Watchlist cards recommended BUY/SELL orders with negative risk-to-reward ratios ($0.5$–$0.7$), leading to poor statistical win-rates.
* **Mistake / Wrong Decision**: In `_fetch_single_quote`, when none of the 3 core strategies triggered, a loose fallback checked simple EMA positioning (`price > EMA20`) and generated a BUY signal with an arbitrary Stop-Loss.
* **Resolution**:
  1. Completely removed the loose trend fallback.
  2. Enforced strict strategy signals (`BreakoutStrategy`, `MomentumStrategy`, `TrendFollowingStrategy`).
  3. Added an explicit pre-flight guard: if $R:R < 0.8$, downgrade action to `'WAIT'`.
  4. In the UI, render `Awaiting Strategy Setup` instead of recommending speculative trades.
* **Rule for Next AI**: A trading assistant's primary job is capital preservation. Never create fallback signals just to show something on the screen. Waiting is a valid and vital trading position.

---

### INC-011: Test Suite Ledger Pollution (531 Ghost Trades)
* **Symptoms**: User noticed historical win rate displayed `0W / 531L` and distorted metrics even though they had only placed a few test trades.
* **Mistake / Wrong Decision**: Pytest unit tests were running against the dev SQLite database (`trading_system.db`) and generating mock orders with symbol `RELIANCE` without cleaning up afterwards.
* **Resolution**:
  1. Prefixed all automated test symbols with `TEST_` (e.g. `TEST_RELIANCE`).
  2. Filtered out `TEST%` symbols in all live portfolio queries, trade logs, and win-rate statistics (`filter(~Trade.symbol.like('TEST%'))`).
  3. Added automated fixture teardown in `tests/test_trading_system.py` to delete created rows.
  4. Added `POST /api/trades/reset` endpoint and a 1-click Reset button on the Win Rate KPI card.
* **Rule for Next AI**: Never allow automated tests to write production-style data into the development database without test-prefix isolation and deterministic teardown fixtures.

---

### INC-012: OTC Spot Forex Zero-Volume Strategy Failure
* **Symptoms**: Adding Forex pairs (`EURUSD`, `GBPUSD`) caused `BreakoutStrategy` and volume indicators to fail or output zero confidence because volume was always 0.
* **Mistake / Wrong Decision**: Assumed all financial instruments have centralized volume bars. Decentralized OTC Spot Forex does not report centralized volume in free feeds (Yahoo reports `0`).
* **Resolution**:
  1. Created an **OTC Tick Volume Proxy** in `backend/data/live_market_service.py`: when `volume == 0`, synthesize proxy volume from normalized candle range expansion:
     $$\text{Proxy Volume} = \left(\frac{\text{High} - \text{Low}}{\text{ATR}_{20}}\right) \times 1000.0$$
  2. Updated `BreakoutStrategy` to evaluate range expansion and candle body ratio when trading Forex pairs.
  3. Added `getCurrencySymbol` and 4-decimal precision formatting (`1.0825`) for FX.
* **Rule for Next AI**: Understand instrument microstructure. Equities have centralized exchange volume; spot FX uses tick-density or volatility-range proxies.

---

### INC-013: Cross-Symbol Candle Ticks Contamination in WebSocket
* **Symptoms**: Switching from `RELIANCE` to `EURUSD` caused the candlestick chart to render distorted erratic spikes because incoming RELIANCE ticks were being painted onto the EURUSD chart.
* **Mistake / Wrong Decision**: The WebSocket `CANDLE_UPDATE` listener in `App.tsx` processed every incoming candle tick and updated `chartData` without verifying that the tick's symbol matched the currently viewed symbol.
* **Resolution**:
  1. Maintained an active symbol reference via `symbolRef = useRef(selectedSymbol)`.
  2. Added symbol isolation guard in the listener:
     ```typescript
     if (data.symbol && data.symbol !== symbolRef.current) {
       return; // Ignore ticks for non-active symbols
     }
     ```
* **Rule for Next AI**: In real-time multi-asset WebSocket streams, always filter incoming tick payloads against the active UI symbol state.

---

## 7 Golden Rules for Successor AI Agents

1. **Deterministic Safety Chain**: Never allow an AI LLM to place orders directly. AI provides structured sentiment and probability ratings; the **Deterministic Risk Manager** has absolute veto power over capital allocation, stop-loss, and sizing.
2. **Capital Calibration**: Account base is calibrated to **₹10,000**. Maximum single-trade investment is **₹5,000**. Max daily loss is **3% (-₹300)**. Never alter these parameters without explicit human approval.
3. **Bi-Directional First**: Always test both BUY (Long) and SELL (Short) paths whenever touching order routing, P&L math, or positions tables.
4. **Timezone Rigor**: All timestamps between Python and React MUST be serialized as ISO 8601 strings ending in `"Z"`. Never pass naive strings.
5. **Quality over Activity**: If technical indicators do not align with guaranteed $R:R \ge 1.0$, output `WAIT`. Do not fabricate speculative setups.
6. **Decoupled Business Logic**: Portfolio accounting, auto-bracket exits, and risk evaluations must run independently of the user's active screen or chart.
7. **Test Cleanliness**: When writing unit tests in `tests/test_trading_system.py`, use `TEST_` prefixed symbols so dev data is never polluted.

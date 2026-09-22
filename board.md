# Hive Board — AI Trading Assistant (Paper Trading & AI Pattern Analysis)

_Shared plans live here. The god agent (Michael) is the sole scribe._

---

## 1. Governance & Execution Rule
> **Golden Rule**: Before starting actual work on any feature or phase, decompose the requirement into explicit **Tasks and Subtasks** on this board (`board.md`) and in `tasks.json`. Assign owners, define acceptance boundaries, and establish verification gates before writing code.

---

## 2. Platform Architecture Chain
$$\text{Market Data (CSV / Replay)} \longrightarrow \text{Deterministic Indicators} \longrightarrow \text{Pattern Detection} \longrightarrow \text{Rule-Based Strategy} \longrightarrow \text{Structured AI Analysis (Pydantic JSON)} \longrightarrow \text{Deterministic Risk Engine} \longrightarrow \text{Paper Broker}$$

* **Safety Policy**: Strictly `TRADING_MODE=PAPER`. Zero real money in Version 1. AI cannot bypass the risk engine.

---

## 3. Master Epics, Tasks & Subtasks Breakdown

### Epic 1: Core Infrastructure & Market Data Feed
* **Task 1.1: Project Scaffolding & Database Setup** (Owner: `god` / `backend-engineer`)
  - [x] Subtask 1.1.1: Create project directory structure (`backend`, `frontend`, `data`, `database`, `tests`, `docs`).
  - [x] Subtask 1.1.2: Initialize git repo with `.gitignore`, `.env.example`, and configuration management (`core/config.py`).
  - [x] Subtask 1.1.3: Define SQLAlchemy models for all 12 tables (`database/models.py`).
  - [x] Subtask 1.1.4: Implement table migration & portfolio seeder (`database/init_db.py`).
* **Task 1.2: CSV Market Data Loader & Validation** (Owner: `backend-engineer`)
  - [x] Subtask 1.2.1: Build strict data validator (`data_validator.py`) for monotonic timestamps, duplicate rejection, and price logic.
  - [x] Subtask 1.2.2: Implement batch CSV ingestion engine (`csv_loader.py`) with duplicate timestamp skipping.
  - [x] Subtask 1.2.3: Generate realistic 500-candle test dataset (`data/RELIANCE_5m.csv`).
* **Task 1.3: Historical Market Simulator & Replay WebSocket** (Owner: `backend-engineer`)
  - [x] Subtask 1.3.1: Build replay engine with `start`, `pause`, `stop`, `reset` state machine.
  - [x] Subtask 1.3.2: Implement variable playback speeds (`1x`, `2x`, `5x`, `10x`, `50x`).
  - [x] Subtask 1.3.3: Mount FastAPI WebSocket endpoint (`/ws/market`) to broadcast live candle streams.

---

### Epic 2: Quantitative Technical Engine
* **Task 2.1: Technical Indicator Engine** (Owner: `backend-engineer`)
  - [x] Subtask 2.1.1: Implement trend indicators: EMA(20), EMA(50), SMA(20).
  - [x] Subtask 2.1.2: Implement momentum indicators: RSI(14), MACD(12/26/9 with signal & histogram).
  - [x] Subtask 2.1.3: Implement volatility & volume metrics: VWAP (daily reset), ATR(14), Bollinger Bands(20, 2.0), ADX(14), Volume SMA(20).
  - [x] Subtask 2.1.4: Provide unified calculation pipeline (`calculate_indicators`) with Pandas vectorization.
* **Task 2.2: Deterministic Pattern Recognition** (Owner: `backend-engineer`)
  - [x] Subtask 2.2.1: Candlestick pattern detectors (Bullish/Bearish Engulfing, Hammer, Shooting Star, Doji).
  - [x] Subtask 2.2.2: Crossover pattern detectors (EMA Golden/Death Cross, MACD Crossover, RSI extremes).
  - [x] Subtask 2.2.3: Breakout pattern detectors (Volume breakout $>1.8\times$, 20-period Support/Resistance, VWAP breach).
  - [x] Subtask 2.2.4: Standardize output format with direction, strength score (0.0–1.0), and empirical evidence facts.
* **Task 2.3: Rule-Based Strategy Engine** (Owner: `backend-engineer`)
  - [x] Subtask 2.3.1: Define `BaseStrategy` abstract interface with setup validation and R:R evaluation.
  - [x] Subtask 2.3.2: Implement `BreakoutStrategy` (resistance break + volume surge + ADX + RSI range).
  - [x] Subtask 2.3.3: Implement `MomentumStrategy` (EMA alignment + expanding MACD + RSI momentum).
  - [x] Subtask 2.3.4: Implement `TrendFollowingStrategy` (VWAP support + ADX trend strength).

---

### Epic 3: Risk Management, Paper Execution & Backtesting
* **Task 3.1: Deterministic Risk Management Engine** (Owner: `backend-engineer` / `agent-architect`)
  - [x] Subtask 3.1.1: Position sizing formula: $size = (capital \times 0.005) / |entry - stop|$.
  - [x] Subtask 3.1.2: Hard risk limits: 0.5% max risk per trade, 2% daily loss ceiling, max 3 open positions, min 1.5 R:R.
  - [x] Subtask 3.1.3: Implement global emergency **Kill Switch** with instant circuit breaker.
  - [x] Subtask 3.1.4: Maintain audit trail of all risk approvals and rejections in `risk_events` table.
* **Task 3.2: Paper Broker & Virtual Portfolio** (Owner: `backend-engineer`)
  - [x] Subtask 3.2.1: Simulate virtual order placement (`MARKET`, `LIMIT`) and execution fills.
  - [x] Subtask 3.2.2: Position ledger with real-time mark-to-market unrealized P&L.
  - [x] Subtask 3.2.3: Order close handling with realized P&L calculation and trade journal persistence.
* **Task 3.3: Walk-Forward Backtester** (Owner: `backend-engineer`)
  - [x] Subtask 3.3.1: Build sequential simulation loop **strictly avoiding look-ahead bias**.
  - [x] Subtask 3.3.2: Compute performance metrics: win rate, net P&L, profit factor, average win/loss, max drawdown.
  - [x] Subtask 3.3.3: Generate historical equity curve and exportable trade log.

---

### Epic 4: AI Provider Layer & Schemas
* **Task 4.1: AI Provider Abstraction** (Owner: `agent-architect`)
  - [x] Subtask 4.1.1: Define `AIProvider` base interface and Pydantic request/response schemas.
  - [x] Subtask 4.1.2: Implement `OpenAIProvider` with JSON mode (`gpt-4o-mini`).
  - [x] Subtask 4.1.3: Implement `ClaudeProvider` with Anthropic Messages API (`claude-3-5-haiku`).
  - [x] Subtask 4.1.4: Implement `LocalHeuristicProvider` as deterministic zero-cost fallback when API keys are absent.
  - [x] Subtask 4.1.5: Enforce strict output schema (signal, confidence, entry zone, stop loss, target, supporting factors, risk factors, invalidation conditions).

---

### Epic 5: User Interface & Trading Terminal
* **Task 5.1: React Frontend Scaffolding & Design System** (Owner: `frontend-engineer`)
  - [x] Subtask 5.1.1: Setup React 18, Vite, TypeScript, Tailwind CSS with dark terminal theme and Nunito Sans typography.
  - [x] Subtask 5.1.2: Implement typed API service client (`services/api.ts`) and WebSocket listener.
* **Task 5.2: Financial Charting & Data Visualizations** (Owner: `frontend-engineer`)
  - [x] Subtask 5.2.1: Integrate TradingView Lightweight Charts with candlestick series and volume histogram.
  - [x] Subtask 5.2.2: Add real-time technical indicator overlays (EMA 20, EMA 50, VWAP).
* **Task 5.3: Terminal Dashboard Cards & Controls** (Owner: `frontend-engineer`)
  - [x] Subtask 5.3.1: Header toolbar with live simulator controls (1x–50x), CSV upload, and Kill Switch.
  - [x] Subtask 5.3.2: Portfolio KPI metric cards (capital, available cash, daily P&L, win rate).
  - [x] Subtask 5.3.3: Signal card with "ANALYZE WITH AI" and "PAPER TRADE" actions.
  - [x] Subtask 5.3.4: AI analysis card displaying confidence, setup, and risk invalidations.
  - [x] Subtask 5.3.5: Paper order modal with risk calculations.
  - [x] Subtask 5.3.6: Open positions and trade history tables.
  - [x] Subtask 5.3.7: Interactive Backtester view with strategy selector and metrics grid.

---

### Epic 6: Future Integrations & Verification
* **Task 6.1: Future Zerodha Kite & MCP Interfaces** (Owner: `agent-architect`)
  - [x] Subtask 6.1.1: Create `BrokerInterface` contract decoupling order routing from application logic.
  - [x] Subtask 6.1.2: Build `ZerodhaBroker` stub with strict live-trading permission guards.
  - [x] Subtask 6.1.3: Build `MarketIntelligenceMCP` client for read-only agent queries.
* **Task 6.2: Quality Assurance & Test Verification** (Owner: `god` / `backend-engineer`)
  - [x] Subtask 6.2.1: Write unit tests for validators, indicators, patterns, strategies, risk rules, and paper broker.
  - [x] Subtask 6.2.2: Verify 100% test pass rate (`pytest tests/test_trading_system.py`).
  - [x] Subtask 6.2.3: Verify production frontend build (`npm run build`).
  - [x] Subtask 6.2.4: Author comprehensive `README.md` documentation.

---

### Epic 7: Real-Time Stream & Simulator Stabilization
* **Task 7.1: Fix Simulator Async Event Loop & Real-Time Playback** (Owner: `backend-engineer`)
  - [x] Subtask 7.1.1: Convert `/api/simulator/control` endpoint in `backend/api/routes/market.py` to `async def` to bind execution directly to the active event loop.
  - [x] Subtask 7.1.2: Ensure `MarketSimulator.start()` runs task on main event loop and gracefully handles resume/start transitions.
  - [x] Subtask 7.1.3: Verify WebSocket broadcasts candle updates and test `/api/simulator/control?action=start` returns 200 OK.
* **Task 7.2: Fix AI Analysis Schema Validation & Result Display** (Owner: `backend-engineer`)
  - [x] Subtask 7.2.1: Fix missing `Any` import in `backend/ai/schemas.py` causing `PydanticUserError`.
  - [x] Subtask 7.2.2: Add error state handling in `frontend/src/App.tsx` for AI analysis requests.
  - [x] Subtask 7.2.3: Verify `POST /api/ai/analyze` returns HTTP 200 and renders `AIAnalysisCard` with confidence, setup, and risk factors.

---

### Epic 8: Virtual Portfolio Management & Position Controls
* **Task 8.1: Backend Portfolio Reset & Position Closing Endpoints** (Owner: `backend-engineer`)
  - [x] Subtask 8.1.1: Implement `paper_broker.reset_portfolio(db)` and `POST /api/portfolio/reset` to restore initial capital (₹1,00,000), clear open positions, and reset daily/realized P&L.
  - [x] Subtask 8.1.2: Implement `POST /api/positions/{position_id}/close` to liquidate open positions at latest market price and credit cash.
* **Task 8.2: Frontend Portfolio Controls & Position Management** (Owner: `frontend-engineer`)
  - [x] Subtask 8.2.1: Add API client methods `resetPortfolio` and `closePosition` in `frontend/src/services/api.ts`.
  - [x] Subtask 8.2.2: Add 1-click **"Reset Portfolio"** button with confirmation prompt in dashboard header toolbar.
  - [x] Subtask 8.2.3: Add **"Close Position"** action button in `PositionTable.tsx` for each open position.

---

### Epic 9: Actionable Trade Execution Card & Order Feedback
* **Task 9.1: Enrich Setup Calculations with Recommended Quantity & Risk Budget** (Owner: `backend-engineer`)
  - [x] Subtask 9.1.1: Calculate recommended quantity based on capital & 0.5% risk budget in strategy signals and AI response schemas.
  - [x] Subtask 9.1.2: Compute exact rupee risk amount and expected target profit for BUY and SELL setups.
* **Task 9.2: Redesign Signal & AI Cards with 1-Click Order Execution & Status Result** (Owner: `frontend-engineer`)
  - [x] Subtask 9.2.1: Display clear actionable headline: "BUY X SHARES" or "SELL X SHARES" with Entry, Stop Loss, and Target grid.
  - [x] Subtask 9.2.2: Add direct 1-click **"Place Order"** button with instant execution.
  - [x] Subtask 9.2.3: Render inline banner feedback for **"Trade Successful"** (with filled price & quantity) or **"Trade Failed: [Reason]"**.

---

### Epic 10: Automatic Bracket Order Exits & Position Target/SL Visibility
* **Task 10.1: Backend Bracket Order Exit Automation & Position SL/Target Persistence** (Owner: `backend-engineer`)
  - [x] Subtask 10.1.1: Add `stop_loss` and `target` columns to `Position` model and run DB table alter migration.
  - [x] Subtask 10.1.2: Update `paper_broker.place_order` to persist `stop_loss` and `target` on new and updated positions.
  - [x] Subtask 10.1.3: Update `paper_broker.update_market_price` to check if `current_price` hits stop-loss or target, automatically execute market exit, update portfolio cash/realized P&L, record trade with exit reason (`"Target Hit"` or `"Stop Loss Hit"`), and return trigger events.
  - [x] Subtask 10.1.4: Update `MarketSimulator._simulation_loop` to broadcast `AUTO_EXIT_TRIGGERED` event over WebSocket when exits occur.
  - [x] Subtask 10.1.5: Return `stop_loss` and `target` in `GET /api/positions` and verify automated pytest test suite passes 100%.
* **Task 10.2: Frontend Position Table SL/Target Columns & Auto-Exit Toast Notifications** (Owner: `frontend-engineer`)
  - [x] Subtask 10.2.1: Update `PositionData` interface in `frontend/src/types/index.ts` with `stop_loss` and `target`.
  - [x] Subtask 10.2.2: Add "Stop Loss" and "Target" columns with color badges in `PositionTable.tsx`.
  - [x] Subtask 10.2.3: In `App.tsx`, listen for `AUTO_EXIT_TRIGGERED` WebSocket events and display prominent banner/alert when a position auto-exits.
  - [x] Subtask 10.2.4: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 11: Capital Calibration (₹10,000 Balance) & ₹5,000 Max Trade Allocation
* **Task 11.1: Backend Capital Calibration to ₹10,000 & ₹5,000 Trade Investment Cap** (Owner: `backend-engineer`)
  - [x] Subtask 11.1.1: Set `INITIAL_CAPITAL = 10000.0`, `MAX_INVESTMENT_PER_TRADE = 5000.0`, `RISK_PER_TRADE = 0.015`, and `MAX_DAILY_LOSS = 0.03` in `backend/core/config.py`.
  - [x] Subtask 11.1.2: Enforce max ₹5,000 position investment cap and dynamic account risk budget in `backend/risk/risk_manager.py`.
  - [x] Subtask 11.1.3: Update `paper_broker.get_portfolio` and `reset_portfolio` to calibrate clean capital to ₹10,000 cash.
  - [x] Subtask 11.1.4: Update and verify test suite in `tests/test_trading_system.py` passes 100%.
* **Task 11.2: Frontend Position Sizing & ₹5,000 Trade Allocation Calibration** (Owner: `frontend-engineer`)
  - [x] Subtask 11.2.1: Update `SignalCard.tsx` sizing formula: cap quantity to $\lfloor 5000 / \text{entry\_price} \rfloor$ and calculate proportional Stop Loss risk for ₹10k capital.
  - [x] Subtask 11.2.2: Update `AIAnalysisCard.tsx` sizing to enforce ₹5,000 investment cap.
  - [x] Subtask 11.2.3: Update `App.tsx` reset confirmation prompt to ₹10,000.
  - [x] Subtask 11.2.4: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 12: 10-Minute Trading Window & Time-Based Auto-Square-Off
* **Task 12.1: Backend 10-Minute Position Expiry Automation & Entry Timestamp Persistence** (Owner: `backend-engineer`)
  - [x] Subtask 12.1.1: Add `entry_time` column to `Position` model in `backend/database/models.py` and SQLite schema migration.
  - [x] Subtask 12.1.2: Record `entry_time` in `paper_broker.place_order`.
  - [x] Subtask 12.1.3: Update `paper_broker.update_market_price` to check if 10 minutes have elapsed, triggering auto-exit with reason `"10-Min Window Expired"`.
  - [x] Subtask 12.1.4: Return `entry_time` and `window_minutes` in `GET /api/positions` and broadcast exit over WebSocket.
  - [x] Subtask 12.1.5: Add pytest test coverage in `tests/test_trading_system.py` and verify all tests pass 100%.
* **Task 12.2: Frontend 10-Minute Window Tracker & Manual Exit Preservation** (Owner: `frontend-engineer`)
  - [x] Subtask 12.2.1: Update `PositionData` interface with `entry_time` in `frontend/src/types/index.ts`.
  - [x] Subtask 12.2.2: Add "Trading Window" column in `PositionTable.tsx` displaying `⏱ 10m Max Window` while preserving the manual red **"Close"** button.
  - [x] Subtask 12.2.3: Add `⏱ Max Window: 10 Min` badges in `SignalCard.tsx` and `AIAnalysisCard.tsx`.
  - [x] Subtask 12.2.4: In `App.tsx`, handle `"10-Min Window Expired"` WebSocket toast alert (`⏰ 10-Min Window Expired! Auto-exited X shares @ ₹...`).
  - [x] Subtask 12.2.5: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 13: Order Execution Reliability, Stale Signal Protection & Live 10-Minute Countdown Window Tracker
* **Task 13.1: Backend Order Execution Hardening & Real-Time Window Calibration** (Owner: `backend-engineer`)
  - [x] Subtask 13.1.1: Fix `paper_broker.py` 10-minute expiry to evaluate real wall-clock elapsed time `(datetime.utcnow() - pos.entry_time).total_seconds() >= 600` so positions don't instantly vanish on historical replay ticks.
  - [x] Subtask 13.1.2: In `api/routes/trading.py` `place_paper_order`, accept `req.quantity` while enforcing risk engine caps and cash limits.
  - [x] Subtask 13.1.3: Prevent instant bracket exit on order entry: In `risk_manager.py` / `place_order`, ensure entry price and stop loss / target are directionally valid at the moment of execution.
  - [x] Subtask 13.1.4: Run full automated pytest test suite (`pytest tests/test_trading_system.py`) verifying 100% pass rate.
* **Task 13.2: Frontend Live 10-Minute Countdown Timer, Instant Position Render & Stale Signal Protection** (Owner: `frontend-engineer`)
  - [x] Subtask 13.2.1: In `PositionTable.tsx`, implement a live 1-second interval countdown timer for each open position showing `⏱ {mm}:{ss} left` (counting down from 10m based on `p.entry_time`) with status coloring.
  - [x] Subtask 13.2.2: In `PositionTable.tsx`, add a "⚡ Quick Paper Order" trigger allowing the user to place a 10-minute trade at current market price anytime without waiting for automated strategy signals.
  - [x] Subtask 13.2.3: In `SignalCard.tsx`, check current price against signal stop_loss and target. If breached, display "⚠️ Signal Expired / Out of Bounds" and prevent entering invalid trades.
  - [x] Subtask 13.2.4: In `App.tsx`, upon placing an order, show a persistent prominent success alert (`✅ Order Placed! Active in Open Virtual Positions`), immediately update `positions` state, and smoothly scroll to the positions table.
  - [x] Subtask 13.2.5: In `PortfolioCard.tsx`, update subtitles to reflect ₹10,000 initial capital and 3% (-₹300) daily loss limit.
  - [x] Subtask 13.2.6: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 14: High-Probability Scalp Calibration, Structural SL/Target, Breakeven Trailing & Bi-Directional Signals
* **Task 14.1: Quantitative Strategy Refactoring & Bi-Directional Detection** (Owner: `backend-engineer`)
  - [x] Subtask 14.1.1: Add Short / SELL Setups across strategies (`BreakoutStrategy`, `MomentumStrategy`, `TrendFollowingStrategy`) in `base_strategy.py`.
  - [x] Subtask 14.1.2: Implement Pullback Entry Filters (prevent buying overbought RSI > 68 or extended prices; require pullback to 20 EMA / VWAP).
  - [x] Subtask 14.1.3: Structural Stop-Loss & Realistic 10-Minute Scalp Targets (SL behind swing pivot + 0.5 ATR; target calibrated to 0.4%–0.6% / 1x ATR).
  - [x] Subtask 14.1.4: Dynamic Trailing Breakeven Auto-Lock in `paper_broker.py` (when profit $\ge +0.3\%$, trail SL to entry price and broadcast `BREAKEVEN_TRAILED`).
  - [x] Subtask 14.1.5: Enforce minimal share sizing (strictly 1 share for stocks > ₹1,000 on ₹10k capital).
  - [x] Subtask 14.1.6: Run automated pytest test suite (`pytest tests/test_trading_system.py`) verifying 100% pass rate.
* **Task 14.2: Frontend Bi-Directional UI, Scalp Target Display & Breakeven Alerts** (Owner: `frontend-engineer`)
  - [x] Subtask 14.2.1: Update `SignalCard.tsx` and `AIAnalysisCard.tsx` to display BUY vs SELL (Short) setups with distinct styling.
  - [x] Subtask 14.2.2: Display realistic scalp metrics and minimal quantity recommendations (1 share) in signal cards.
  - [x] Subtask 14.2.3: In `PositionTable.tsx`, display `🛡 Breakeven Locked` badge when Stop Loss is trailed to entry price.
  - [x] Subtask 14.2.4: In `App.tsx`, listen for `BREAKEVEN_TRAILED` WebSocket event and display alert toast.
  - [x] Subtask 14.2.5: Calibrate `handleQuickOrder` in `App.tsx` with realistic 0.5% target and structural SL.
  - [x] Subtask 14.2.6: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 15: Real-Time Live Market Data Feed & Live Paper Trading
* **Task 15.1: Backend Live Market Service & Real-Time Poller** (Owner: `backend-engineer`)
  - [x] Subtask 15.1.1: Build `backend/data/live_market_service.py` to stream live intraday candles & quotes for NSE stocks (`RELIANCE.NS`, `TCS.NS`, etc.) via `yfinance`.
  - [x] Subtask 15.1.2: Compute real-time indicators, detect patterns, evaluate bi-directional strategies, and update mark-to-market positions live.
  - [x] Subtask 15.1.3: Mount live feed control endpoints in `backend/api/routes/market.py` (`POST /api/market/mode` to toggle `LIVE` vs `SIMULATOR`, `GET /api/market/mode`).
  - [x] Subtask 15.1.4: Broadcast live ticks and alerts over `/ws/market` WebSocket.
  - [x] Subtask 15.1.5: Verify full automated pytest test suite (`pytest tests/test_trading_system.py`) passes 100% (31/31 passed).
* **Task 15.2: Frontend Live Market Mode Toggle & Real-Time Feed UI** (Owner: `frontend-engineer`)
  - [x] Subtask 15.2.1: Add `🔴 LIVE FEED` vs `🎞 SIMULATOR` mode switch in the top toolbar.
  - [x] Subtask 15.2.2: Add live market indicator badge with pulsing green status (`● LIVE NSE`).
  - [x] Subtask 15.2.3: Wire chart, signal cards, and order execution to live market quotes.
  - [x] Subtask 15.2.4: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 16: Multi-Asset Live Watchlist Scanner, Symbol Selector & Forex Market Support
* **Task 16.1: Backend Multi-Asset Watchlist API & Forex Market Integration** (Owner: `backend-engineer`)
  - [x] Subtask 16.1.1: Add Forex symbol mapping (`USDINR`, `EURUSD`, `GBPUSD`, `USDJPY`, `EURINR`, `GBPINR`, `AUDUSD`) in `backend/data/live_market_service.py`.
  - [x] Subtask 16.1.2: Implement `get_watchlist_quotes(symbols)` to batch-fetch live quotes and compute quick strategy signals concurrently.
  - [x] Subtask 16.1.3: Implement `GET /api/market/watchlist` endpoint in `backend/api/routes/market.py`.
  - [x] Subtask 16.1.4: Add unit tests in `tests/test_trading_system.py` verifying watchlist and Forex quotes.
  - [x] Subtask 16.1.5: Verify full automated pytest suite passes 100%.
* **Task 16.2: Frontend Multi-Asset Live Watchlist Scanner & Asset Selector UI** (Owner: `frontend-engineer`)
  - [x] Subtask 16.2.1: Add `getWatchlist` API method in `frontend/src/services/api.ts`.
  - [x] Subtask 16.2.2: Build `MultiAssetWatchlist.tsx` component displaying simultaneous multi-ticker cards with live quotes, % change, and signals.
  - [x] Subtask 16.2.3: Add Symbol Selector Dropdown & Market Category Tabs in header toolbar (NSE Stocks vs Forex).
  - [x] Subtask 16.2.4: Wire 1-click asset switching: selecting any watchlist card updates chart, indicators, and order engine.
  - [x] Subtask 16.2.5: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 17: Multi-Asset Simultaneous Trade Decision Center & Universal Actionable Cards
* **Task 17.1: Backend Multi-Asset Trade Decision & Brackets API** (Owner: `backend-engineer`)
  - [x] Subtask 17.1.1: Calculate `entry_price`, `stop_loss`, `target`, `risk_reward`, `action`, and `quantity` for each symbol in `_fetch_single_quote`.
  - [x] Subtask 17.1.2: Calibrate equities to 1 share minimal sizing and Forex to micro units with realistic pip targets and structural SL.
  - [x] Subtask 17.1.3: Return full actionable trade decision parameters in `GET /api/market/watchlist`.
  - [x] Subtask 17.1.4: Add unit tests in `tests/test_trading_system.py` verifying multi-asset decision payload.
  - [x] Subtask 17.1.5: Verify full automated pytest suite passes 100%.
* **Task 17.2: Frontend Multi-Asset Trade Decision Cards & 1-Click Multi-Trade Execution** (Owner: `frontend-engineer`)
  - [x] Subtask 17.2.1: Update `WatchlistQuote` type in `frontend/src/types/index.ts` with decision fields (`stop_loss`, `target`, `action`, `risk_reward`, `quantity`).
  - [x] Subtask 17.2.2: Redesign `MultiAssetWatchlist.tsx` cards with actionable decision headlines, SL, Target, and 1-click **"⚡ Place Order"** button.
  - [x] Subtask 17.2.3: Add comparative **Multi-Asset Decision Center** board view showing all 6 setups side-by-side.
  - [x] Subtask 17.2.4: Wire `onTradeSymbol` in `App.tsx` so clicking "⚡ Place Order" on any of the 6 cards executes the trade into Open Virtual Positions.
  - [x] Subtask 17.2.5: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 18: Strict Strategy-Risk Synchronization, Rigorous R:R Validation & False Signal Elimination
* **Task 18.1: Backend Strategy Authenticity & Risk-Reward Guaranteed Brackets** (Owner: `backend-engineer`)
  - [x] Subtask 18.1.1: Remove loose trend fallback in `_fetch_single_quote`; strictly require verified strategy triggers for BUY/SELL.
  - [x] Subtask 18.1.2: Calibrate target formula so target reward is strictly $\ge 1.05\times$ structural risk, guaranteeing $R:R \ge 1.0$.
  - [x] Subtask 18.1.3: Add pre-flight check in `_fetch_single_quote`: if $R:R < 0.8$, downgrade action to `'WAIT'`.
  - [x] Subtask 18.1.4: Add pytest tests in `tests/test_trading_system.py` asserting $R:R \ge 0.8$ and strategy authenticity.
  - [x] Subtask 18.1.5: Verify full test suite passes with 100% pass rate.
* **Task 18.2: Frontend SignalCard Synchronization, False Signal Elimination & Quick Scalp Brackets** (Owner: `frontend-engineer`)
  - [x] Subtask 18.2.1: In `MultiAssetWatchlist.tsx`, display `Awaiting Setup` for `WAIT` assets and only highlight verified BUY/SELL setups.
  - [x] Subtask 18.2.2: In `App.tsx` `handleTradeFromWatchlist`, ensure orders use calibrated $R:R \ge 1.2$ brackets ($-0.5\%$ SL, $+0.6\%$ Target).
  - [x] Subtask 18.2.3: Synchronize `activeSignal` with selected symbol watchlist quote in `App.tsx`.
  - [x] Subtask 18.2.4: In `SignalCard.tsx`, display informative `Awaiting Strategy Setup` state explaining technical conditions.
  - [x] Subtask 18.2.5: Verify frontend production build (`npm run build`) passes with 0 errors.

---

### Epic 19: Zero-Delay Zerodha Kite Live Feed Integration & Connection Manager
* **Task 19.1: Backend Zerodha Kite Connect & Enctoken Zero-Delay Live Market Adapter** (Owner: `backend-engineer`)
  - [x] Subtask 19.1.1: Build `KiteLiveClient` in `backend/integrations/zerodha/kite_client.py` supporting both Official API Key+Access Token and Web Enctoken session.
  - [x] Subtask 19.1.2: Mount `/api/zerodha/connect`, `/api/zerodha/status`, and `/api/zerodha/disconnect` endpoints in `backend/api/routes/zerodha.py`.
  - [x] Subtask 19.1.3: Integrate Zerodha zero-delay live quotes into `live_market_service.py` for watchlist and candles when connected.
  - [x] Subtask 19.1.4: Add unit tests in `tests/test_trading_system.py` verifying Zerodha connection lifecycle and quote ingestion.
  - [x] Subtask 19.1.5: Verify full test suite passes with 100% pass rate.
* **Task 19.2: Frontend Zerodha Kite Connection Modal & Real-Time 0-Delay Status UI** (Owner: `frontend-engineer`)
  - [x] Subtask 19.2.1: Add Zerodha API methods in `frontend/src/services/api.ts` (`connectZerodha`, `getZerodhaStatus`, `disconnectZerodha`).
  - [x] Subtask 19.2.2: Build `ZerodhaConnectModal.tsx` with tabs for Enctoken (Free) and Developer API Key with inline guides.
  - [x] Subtask 19.2.3: Add Connect Zerodha button and glowing 0-DELAY status badge in header toolbar.
  - [x] Subtask 19.2.4: Handle live connection status, persistence, and instant disconnect.
  - [x] Subtask 19.2.5: Verify frontend production build passes with 0 errors.
---

### Epic 20: High-Win-Rate Intraday Scanners & Confluence Suite
* **Task 20.1: Backend High-Win-Rate Intraday Scanner Engine & Confluence API** (Owner: `backend-engineer`)
  - [x] Subtask 20.1.1: Create `backend/data/scanner_engine.py` with OHL (Open=High/Low), Volume Surge ($\ge 2.0\times$ SMA20), Central Pivot Range (Narrow CPR $\le 0.25\%$, TC/BC levels), and Day High/Low Breakout algorithms.
  - [x] Subtask 20.1.2: Integrate scanner engine into `LiveMarketService` quote builder to enrich quotes with scanner tags and confluence scoring.
  - [x] Subtask 20.1.3: Add `GET /api/market/scanners` endpoint in `backend/api/routes/market.py` returning categorized institutional intraday setups.
  - [x] Subtask 20.1.4: Write comprehensive unit test suite in `tests/test_trading_system.py` verifying all scanner algorithms.
  - [x] Subtask 20.1.5: Run test suite and verify 100% pass rate.
* **Task 20.2: Frontend High-Win-Rate Scanner Cockpit, Filter Tabs & Real-Time Confluence Badges** (Owner: `frontend-engineer`)
  - [x] Subtask 20.2.1: Update `frontend/src/types/index.ts` to include scanner fields (`scanner_tags`, `ohl`, `volume_surge`, `cpr`, `day_breakout`, `confluence_score`).
  - [x] Subtask 20.2.2: Add `getScanners` API client method in `frontend/src/services/api.ts`.
  - [x] Subtask 20.2.3: Add scanner category filter pills in `MultiAssetWatchlist.tsx` (`All`, `High Confluence`, `Open=Low`, `Open=High`, `Volume Surge`, `Narrow CPR`, `Day Breakouts`).
  - [x] Subtask 20.2.4: Render glowing scanner badges, confluence counter, and CPR metrics in Cards view and Table view.
  - [x] Subtask 20.2.5: Verify frontend production build compiles with 0 TypeScript/Vite errors.

---

### Epic 21: Trade Autopsy Engine & Adaptive Failure Reduction Suite
* **Task 21.1: Backend Trade Autopsy Diagnostic Engine & Adaptive Failure Suppression** (Owner: `backend-engineer`)
  - [x] Subtask 21.1.1: Create `TradeAutopsy` model in `backend/database/models.py` and run SQLite migration.
  - [x] Subtask 21.1.2: Build `backend/trading/trade_autopsy.py` with 5-point root-cause diagnosis and adaptive suppression manager.
  - [x] Subtask 21.1.3: Hook autopsy trigger into `paper_broker` order close/auto-exit and integrate suppression filter into `RiskManager`.
  - [x] Subtask 21.1.4: Add `GET /api/trades/autopsies` and `GET /api/trades/{id}/autopsy` endpoints in `backend/api/routes/trading.py`.
  - [x] Subtask 21.1.5: Write unit tests in `tests/test_trading_system.py` verifying failure diagnosis, suppression filter, and API.
* **Task 21.2: Frontend Trade Autopsy Modal, Loss Diagnostic Badges & Adaptive Shield Status UI** (Owner: `frontend-engineer`)
  - [x] Subtask 21.2.1: Add `TradeAutopsy` interface in `frontend/src/types/index.ts` and api methods in `frontend/src/services/api.ts`.
  - [x] Subtask 21.2.2: Build `TradeAutopsyModal.tsx` with root-cause breakdown, chart metrics, and preventative guidance.
  - [x] Subtask 21.2.3: Render clickable autopsy badges on losing trades in `PositionTable`/`Trade History`.
  - [x] Subtask 21.2.4: Verify frontend production build compiles cleanly with 0 TypeScript/Vite errors.

---

### Epic 22: Live 24/5 Forex & Commodities Market Suite
* **Task 22.1: Backend 24/5 Forex Live Streaming Engine, Volatility Proxy & Precision Formatting** (Owner: `backend-engineer`)
  - [x] Subtask 22.1.1: Expand `SYMBOL_MAP`, `FOREX_SYMBOLS`, and `SYMBOL_NAMES` in `backend/data/live_market_service.py` with full 10 Forex, Commodity, and Crypto pairs.
  - [x] Subtask 22.1.2: Implement OTC tick volume proxy computation in `_fetch_and_prepare` using normalized range volatility when volume is zero.
  - [x] Subtask 22.1.3: Adapt `BreakoutStrategy` and scanner engine for Forex: allow price body and ATR range expansion without failing on zero volume.
  - [x] Subtask 22.1.4: Implement `get_market_trading_status(symbol)` supporting 24/5 Forex market hours and 24/7 Crypto.
  - [x] Subtask 22.1.5: Write unit tests in `tests/test_trading_system.py` verifying Forex live quotes, volatility proxy, 24/5 market hours, and precision formatting.
* **Task 22.2: Frontend Multi-Asset Watchlist Forex Suite, Live 24/5 Status Banner & Cross-Symbol Chart Isolation** (Owner: `frontend-engineer`)
  - [x] Subtask 22.2.1: Expand `MultiAssetWatchlist.tsx` `DEFAULT_SYMBOLS` and `FALLBACK_QUOTES` to include all 10 Forex/Commodity/Crypto pairs.
  - [x] Subtask 22.2.2: Implement multi-currency symbol and precision formatting ($/€/£/¥/₹, 4-decimal precision for FX, 2-decimal for Equities/Gold/Crypto).
  - [x] Subtask 22.2.3: Fix WebSocket `CANDLE_UPDATE` tick routing in `App.tsx` with symbol isolation check to prevent cross-symbol candle contamination.
  - [x] Subtask 22.2.4: Dynamic Market Hours Banner in `App.tsx` displaying `FOREX 24/5 LIVE` or `24/7 CRYPTO LIVE` when a Forex/Crypto asset is active.
  - [x] Subtask 22.2.5: Ensure `handleSelectSymbol` switches live feed polling to the selected symbol seamlessly and verify frontend production build compiles cleanly.


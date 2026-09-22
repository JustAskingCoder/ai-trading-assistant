# Master Ticket Catalog & Implementation Ledger (`TICKETS.md`)

This document is the structured catalog of all 43 delivered tasks and 150+ subtasks across Epics 1 through 22.

---

## Summary Matrix

| Epic | Tasks | Focus Area | Primary Worker | Status |
|---|---|---|---|---|
| **Epic 1** | `task-001` .. `task-003` | Core Scaffolding, SQLite DB, CSV Loader & Market Simulator | `backend-engineer`, `god` | Done |
| **Epic 2** | `task-004` .. `task-007` | Lightweight Charts, Indicator Engine, Patterns & Rule Strategies | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 3** | `task-008` .. `task-010` | Deterministic Risk Manager, Paper Broker & Backtesting Engine | `backend-engineer` | Done |
| **Epic 4** | `task-011` | AI Provider Abstraction (OpenAI, Claude, Local Heuristic) | `agent-architect` | Done |
| **Epic 5** | `task-012` | React 18, Vite, Tailwind CSS Dark Terminal Dashboard | `frontend-engineer` | Done |
| **Epic 6** | `task-013` | Zerodha Broker Interface & Market Intelligence MCP Architecture | `agent-architect` | Done |
| **Epic 7** | `task-014`, `task-015` | Async Event Loop Fix & Pydantic Schema Validation Hardening | `backend-engineer` | Done |
| **Epic 8** | `task-016` | Virtual Portfolio Reset & Individual Position Close Controls | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 9** | `task-017` | Actionable Trade Cards, Exact Rupee Sizing & Inline Feedback | `frontend-engineer` | Done |
| **Epic 10** | `task-018`, `task-019` | Automatic Bracket Exits (SL/Target) & WebSocket Toast Banners | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 11** | `task-020`, `task-021` | Capital Calibration (₹10,000 Balance, ₹5,000 Trade Cap) | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 12** | `task-022`, `task-023` | 10-Minute Trading Window & Time-Based Auto-Square-Off | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 13** | `task-024`, `task-025` | Wall-Clock Expiry Hardening, Live 1s Countdown Timer | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 14** | `task-026`, `task-027` | Quantitative Scalp Calibration, Structural SL, Breakeven Trailing | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 15** | `task-028`, `task-029` | Real-Time Live Market Poller (NSE via Yahoo) & Dual Mode Switch | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 16** | `task-030`, `task-031` | Multi-Asset Live Watchlist Scanner & Initial Forex Support | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 17** | `task-032`, `task-033` | Simultaneous Trade Decision Matrix & 1-Click Multi-Trade Execution | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 18** | `task-034`, `task-035` | Strict Strategy Authenticity, R:R >= 1.0 Guarantee & False Signal Filter | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 19** | `task-036`, `task-037` | Zero-Delay Zerodha Kite Connect & Web Enctoken Live Adapter | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 20** | `task-038`, `task-039` | High-Win-Rate Intraday Scanner Suite (OHL, Vol Surge, CPR, ORB) | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 21** | `task-040`, `task-041` | Automated Trade Autopsy Engine & Adaptive Failure Suppression Shield | `backend-engineer`, `frontend-engineer` | Done |
| **Epic 22** | `task-042`, `task-043` | 24/5 Forex & Commodities Engine, OTC Range Proxy, Multi-Currency UI | `backend-engineer`, `frontend-engineer` | Done |

---

## Detailed Ticket Specifications

### Phase 1 to Phase 6 (Foundation & Core Quantitative Engine)
* **task-001: Phase 1 — Project Setup & Core Infrastructure**
  - Owner: `god`
  - Deliverables: Directory tree, virtual environment, 12 SQLAlchemy ORM models, SQLite database initialization with initial seed.
* **task-002: Phase 2 — CSV Market Data Loader & Validation**
  - Owner: `backend-engineer`
  - Deliverables: Chronological order validator, duplicate candle deduplicator, synthetic 500-candle sample generator (`data/RELIANCE_5m.csv`).
* **task-003: Phase 3 — Market Simulator & WebSocket Stream**
  - Owner: `backend-engineer`
  - Deliverables: Playback engine with Start/Pause/Stop/Reset and 1x–50x speed multipliers, `/ws/market` WebSocket broadcaster.
* **task-004: Phase 4 — Candlestick & Volume Charting**
  - Owner: `frontend-engineer`
  - Deliverables: TradingView Lightweight Charts integration with candlestick series, volume histogram, and EMA overlays.
* **task-005: Phase 5 — Technical Indicator Engine**
  - Owner: `backend-engineer`
  - Deliverables: Vectorized Pandas computation for EMA(20/50), SMA(20), RSI(14), MACD(12/26/9), VWAP, ATR(14), Bollinger Bands, ADX(14), and Volume SMA(20).
* **task-006: Phase 6 — Deterministic Pattern Detection**
  - Owner: `backend-engineer`
  - Deliverables: Rule-based recognition for Bullish/Bearish Engulfing, Hammer, Shooting Star, Doji, Breakouts, and Crossovers.
* **task-007: Phase 7 — Strategy Engine**
  - Owner: `backend-engineer`
  - Deliverables: `BaseStrategy` interface, `BreakoutStrategy`, `MomentumStrategy`, and `TrendFollowingStrategy`.

### Phase 8 to Phase 13 (Risk, Portfolio, AI & UI Terminal)
* **task-008: Phase 8 — Deterministic Risk Management Engine**
  - Owner: `backend-engineer`
  - Deliverables: Strict sizing formula ($size = capital \times 0.005 / |entry - stop|$), daily loss ceiling, open position limits, emergency Kill Switch, and risk audit logging.
* **task-009: Phase 9 — Paper Broker & Virtual Portfolio**
  - Owner: `backend-engineer`
  - Deliverables: Order placement simulation, fill execution, real-time mark-to-market position updates, realized P&L accounting.
* **task-010: Phase 10 — Walk-Forward Backtester**
  - Owner: `backend-engineer`
  - Deliverables: Sequential simulation loop strictly avoiding look-ahead bias, win rate, profit factor, max drawdown, and equity curve.
* **task-011: Phase 11 — AI Provider Abstraction**
  - Owner: `agent-architect`
  - Deliverables: Pydantic schemas, `OpenAIProvider`, `ClaudeProvider`, and `LocalHeuristicProvider` fallback.
* **task-012: Phase 12 — Professional React Financial Dashboard**
  - Owner: `frontend-engineer`
  - Deliverables: Dark terminal trading UI, header toolbar, KPI cards, signal cards, AI cards, order modal, positions table, backtest view.
* **task-013: Phase 13 — Zerodha Kite & MCP Future Architecture**
  - Owner: `agent-architect`
  - Deliverables: `BrokerInterface` decoupling, `ZerodhaBroker` live guard stub, `MarketIntelligenceMCP` client.

### Phase 14 to Phase 22 (Stabilization, Live Feeds, Scalping & Autopsy)
* **task-014: Fix Simulator Async Event Loop & Real-Time Playback**
  - Owner: `backend-engineer`
  - Fix: Converted control endpoint to `async def` and bound tasks to running asyncio event loop.
* **task-015: Fix AI Analysis Schema Validation & Result Display**
  - Owner: `backend-engineer`
  - Fix: Added missing `Any` import to `backend/ai/schemas.py`, resolved `PydanticUserError`.
* **task-016: Reset Virtual Portfolio & Position Close Controls**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: `POST /api/portfolio/reset`, `POST /api/positions/{id}/close`, header Reset button, and table Close actions.
* **task-017: Actionable Trade Execution Card & Order Feedback**
  - Owner: `frontend-engineer`
  - Deliverables: Sizing math, BUY/SELL X SHARES headline, 1-click execution, and inline status banners.
* **task-018 & task-019: Automated Bracket Order Exits & SL/Target UI**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Auto-exit evaluation on price ticks, `AUTO_EXIT_TRIGGERED` WebSocket broadcast, colored SL/Target columns in table, and toast alerts.
* **task-020 & task-021: Capital Calibration (₹10,000 Balance, ₹5,000 Trade Cap)**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: ₹10,000 cash balance, ₹5,000 single-trade investment cap, 1.5% max trade risk, and synchronized frontend sizing.
* **task-022 & task-023: 10-Minute Position Expiry Automation**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Persisted `entry_time`, automatic square-off after 10 minutes, `⏱ 10m Max Window` badge, manual exit preservation.
* **task-024 & task-025: Wall-Clock Expiry Hardening & Live 1s Countdown Timer**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Real wall-clock elapsed time evaluation (`>= 600s`), live 1-second countdown timer (`⏱ mm:ss left`), Quick Paper Order action, stale signal protection.
* **task-026 & task-027: Quantitative Scalp Refactoring & Bi-Directional UI**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Bi-directional BUY/SELL (Short) setups, pullback filters, structural SL (pivot + 0.5 ATR), 0.4%–0.6% scalp targets, trailing breakeven auto-lock at +0.3% profit, 1-share sizing floor.
* **task-028 & task-029: Real-Time Live Market Service & Mode Switch**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Real-time Yahoo Finance poller, `LIVE` vs `SIMULATOR` mode switch, live pulsing green `● LIVE NSE` badge.
* **task-030 & task-031: Multi-Asset Watchlist Scanner & Initial Forex Support**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Concurrent multi-symbol quote fetcher, category tabs (NSE Stocks vs Forex), 1-click asset switching.
* **task-032 & task-033: Simultaneous Trade Decision Center & Universal Action Cards**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Multi-asset decision parameters (Action, Entry, SL, Target, R:R, Qty), 6-card side-by-side Decision Center matrix, 1-click execution across all cards.
* **task-034 & task-035: Strict Strategy Authenticity & R:R Guaranteed Brackets**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Elimination of false signals, pre-flight $R:R \ge 0.8$ validation, downgrade of weak setups to `WAIT`, informative `Awaiting Setup` state.
* **task-036 & task-037: Zero-Delay Zerodha Kite Connect & Web Enctoken Live Adapter**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: `KiteLiveClient` supporting free Web Enctoken and Developer API Key, REST endpoints, `ZerodhaConnectModal.tsx` dual-tab UI with 30-second DevTools copy guide, glowing 0-DELAY live feed status badge.
* **task-038 & task-039: High-Win-Rate Intraday Scanner Suite**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: Open=High/Low detection, Volume Surge $\ge 2.0\times$, Narrow Central Pivot Range ($\le 0.25\%$), Day High/Low Breakouts, A+ Confluence scoring, interactive filter pills.
* **task-040 & task-041: Automated Trade Autopsy Engine & Adaptive Failure Shield**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: 6-point root cause diagnosis (`CHASED_ENTRY`, `FALSE_BREAKOUT_LOW_VOL`, `COUNTER_TIDE_DIVERGENCE`, etc.), 20–40 min adaptive suppression cooldown, `TradeAutopsyModal.tsx`, loss badges in trade history.
* **task-042 & task-043: 24/5 Forex & Commodities Engine, OTC Range Proxy & Multi-Currency UI**
  - Owner: `backend-engineer` & `frontend-engineer`
  - Deliverables: 10 Forex/Commodity/Crypto tickers, normalized range volatility tick volume proxy ($\frac{\text{Range}}{\text{ATR}} \times 1000$), 24/5 Forex market hours (Mon–Sat 02:30 IST) and 24/7 Crypto, multi-currency formatting ($/€/£/¥/₹), 4-decimal pip precision, cross-symbol WebSocket chart isolation guard.

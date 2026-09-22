# Architectural Decision Records (ADRs) & Engineering Decisions

This document details all fundamental design decisions, system constraints, trade-offs, and invariants governing the **AI Trading Assistant** codebase (`ai-trading-assistant`).

---

## ADR-001: Unidirectional Safety Pipeline
* **Status**: ACCEPTED & ENFORCED
* **Context**: Financial trading applications face severe existential risk if generative AI models have direct execution authority. LLMs hallucinate, miscalculate numbers, and suffer from stochastic drift.
* **Decision**: Enforce a strict unidirectional execution chain:
  $$\text{Market Data / Replay} \longrightarrow \text{Deterministic Indicators} \longrightarrow \text{Deterministic Patterns} \longrightarrow \text{Rule Strategies} \longrightarrow \text{Structured AI Analysis} \longrightarrow \textbf{Deterministic Risk Engine} \longrightarrow \text{Paper Broker}$$
* **Consequences**:
  - The AI layer (`backend/ai/`) provides structured qualitative context, confidence scores, and invalidation criteria using Pydantic JSON schemas.
  - The **Deterministic Risk Engine** (`backend/risk/risk_manager.py`) has absolute veto power over order authorization, sizing, stop-loss distance, and daily loss caps.
  - The AI **cannot** bypass the Risk Engine under any circumstance.

---

## ADR-002: Portfolio Capital Calibration (₹10,000 Capital & ₹5,000 Trade Cap)
* **Status**: ACCEPTED & ENFORCED
* **Context**: Real retail day traders in India typically begin with small accounts (~₹10,000) rather than institutional ₹1,00,000 balances. Sizing formulas must produce realistic share allocations (e.g. 1 share of RELIANCE @ ₹3,000) rather than fractional or multi-lot institutional numbers.
* **Decision**:
  - `INITIAL_CAPITAL = 10000.0`
  - `MAX_INVESTMENT_PER_TRADE = 5000.0` (Maximum 50% capital allocation into any single position)
  - `RISK_PER_TRADE = 0.015` (1.5% max risk per trade = ₹150 max loss)
  - `MAX_DAILY_LOSS = 0.03` (3% max daily drawdown = ₹300)
  - Minimal share sizing: Enforce 1-share floor for equities trading above ₹1,000 on small capital.
* **Consequences**: Realistic, disciplined risk modeling suitable for retail capital testing.

---

## ADR-003: Multi-Tiered Holding Windows & Trailing Breakeven Protection
* **Status**: ACCEPTED & ENFORCED
* **Context**: Intraday scalp trades should not remain open indefinitely overnight or through multiple sessions, but forcing exit strictly on an arbitrary timer often dumps winning trades during normal consolidation.
* **Decision**:
  - Base Intraday Scalp Window: **30 minutes** (calibrated from initial 10-minute prototype).
  - Swing Window: **45 minutes**; Trend Ride: **60 minutes**.
  - **Trailing Breakeven on Expiry**: If a position's holding window expires but the trade is currently in profit (`unrealized_pnl > 0`), the algorithm automatically locks Stop Loss to breakeven (`pos.stop_loss = pos.average_price`) and grants a +15-minute extension (up to 90 minutes max). If the trade is in a loss when the timer expires, it auto-exits immediately at market price to protect capital.
* **Consequences**: Prevents premature liquidation of winning momentum trades while eliminating overnight gap risk.

---

## ADR-004: Bi-Directional Position Management (Long & Short)
* **Status**: ACCEPTED & ENFORCED
* **Context**: Intraday trading requires capitalizing on both market rallies and intraday sell-offs. A spot long-only architecture limits utility to only bullish market regimes.
* **Decision**: Implement full bi-directional position mechanics in `PaperBroker`:
  - `BUY` opens a `LONG` position or covers an existing `SHORT` position.
  - `SELL` opens a `SHORT` position or liquidates an existing `LONG` position.
  - Position flipping: If an order's quantity exceeds the opposing open position, close the old position and open the remainder in the new direction.
  - P&L calculation: Short P&L is calculated as $(\text{Entry Price} - \text{Current Price}) \times |\text{Quantity}|$.
* **Consequences**: Symmetrical intraday execution across both bullish and bearish market trends.

---

## ADR-005: Dual Zerodha Kite Adapter (Free Enctoken & Official API)
* **Status**: ACCEPTED & ENFORCED
* **Context**: Many retail traders and algorithmic researchers want live zero-delay market quotes without paying ₹2,000/month for Kite Connect Developer API keys during development and testing.
* **Decision**:
  - Build `KiteLiveClient` supporting two modes:
    1. **Web Enctoken (Free)**: Users copy the `enctoken` cookie from Kite Web DevTools via a 30-second workflow. Provides live 0-delay quotes with zero API fees.
    2. **Official Developer API**: Standard API Key + Access Token for licensed developer accounts.
  - Store tokens locally in browser `localStorage` and pass to backend session manager.
* **Consequences**: Zero friction onboarding for live tick testing without subscription barriers.

---

## ADR-006: High-Win-Rate Institutional Intraday Confluence Engine
* **Status**: ACCEPTED & ENFORCED
* **Context**: Single-indicator strategies suffer high false-positive rates in choppy markets. Institutional desks look for multi-factor confluence before deploying capital.
* **Decision**:
  - Build `ScannerEngine` (`backend/data/scanner_engine.py`) calculating:
    - **Open = Low (Bullish)** and **Open = High (Bearish)** institutional morning open momentum.
    - **Volume Surge**: Volume $\ge 2.0\times$ 20-period Volume SMA.
    - **Central Pivot Range (CPR)**: TC, Pivot, BC levels with Narrow CPR detection ($\le 0.25\%$ width indicating impending explosive directional trend).
    - **Day High / Day Low Breakout (ORB)**: 15-minute opening range breach with volume expansion.
    - **A+ Confluence Rating**: Triggers when $\ge 2$ institutional conditions align simultaneously.
* **Consequences**: Dramatically elevates trade quality; filters out noise in sideways consolidation zones.

---

## ADR-007: Closed-Loop Automated Trade Autopsy & Adaptive Shield
* **Status**: ACCEPTED & ENFORCED
* **Context**: Retail traders frequently commit revenge trading or repeat identical mistakes in hostile market regimes.
* **Decision**:
  - Automatically conduct a forensic autopsy on every losing trade (`unrealized_pnl < 0`) upon exit:
    - Diagnose root cause across 6 institutional categories: `CHASED_ENTRY`, `FALSE_BREAKOUT_LOW_VOL`, `COUNTER_TIDE_DIVERGENCE`, `TIGHT_STOP_SHAKEOUT`, `CHOP_ZONE_EXHAUSTION`, `TREND_SHIFT_REVERSAL`.
    - Persist autopsy in SQLite `TradeAutopsy` table with financial impact and preventative guidance.
  - **Adaptive Failure Shield (Closed-Loop Defense)**:
    - Automatically activate a 20–40 minute protective cooldown on that symbol and strategy.
    - Block incoming order attempts during the cooldown in `RiskManager.evaluate_order()`.
* **Consequences**: Prevents revenge trading, halts algorithmic bleed in adverse market regimes, and delivers automated educational feedback.

---

## ADR-008: 24/5 Live Forex & 24/7 Crypto Engine with OTC Tick Volume Proxy
* **Status**: ACCEPTED & ENFORCED
* **Context**: Indian stock markets (NSE) operate from 09:15 to 15:30 IST. Users need to test algorithmic setups during evening hours and weekends via Forex and Crypto.
* **Decision**:
  - Support 10 international instruments: `USDINR`, `EURUSD`, `GBPUSD`, `USDJPY`, `EURINR`, `GBPINR`, `AUDUSD`, `USDCHF`, `GOLD`, `BTCUSD`.
  - Handle OTC spot Forex zero-volume limitation: Synthesize tick volume from normalized candle range expansion:
    $$\text{Proxy Volume} = \left(\frac{\text{High} - \text{Low}}{\text{ATR}_{20}}\right) \times 1000.0$$
  - Support 24/5 Forex trading sessions (Mon 02:30 IST to Sat 02:30 IST) and 24/7 Crypto sessions (`BTCUSD`).
  - Implement dynamic currency symbol formatting (`$`, `€`, `£`, `¥`, `₹`, `CHF`) and 4-decimal precision for spot FX.
* **Consequences**: The platform is active and testable 24 hours a day, 7 days a week.

---

## ADR-009: Zero-Cost Fallback Provider (`LocalHeuristicProvider`)
* **Status**: ACCEPTED & ENFORCED
* **Context**: Users running the app without external OpenAI or Anthropic API keys must still receive structured technical analysis rather than application errors.
* **Decision**:
  - Implement `LocalHeuristicProvider` as the default AI provider when `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are absent.
  - Computes deterministic confidence scores based on multi-indicator alignment (RSI, MACD, EMA slope, Volume surge) and returns the identical Pydantic JSON schema as cloud LLMs.
* **Consequences**: 100% functionality out-of-the-box with zero API subscriptions or credit cards required.

---

## ADR-010: Strict UTC Timestamping & Serialization Boundary
* **Status**: ACCEPTED & ENFORCED
* **Context**: Timezone skews between Python SQLite backends and JavaScript browsers cause critical bugs in trade duration windows, countdown timers, and historical candle synchronization.
* **Decision**:
  - All database timestamps are generated and stored in UTC.
  - Every timestamp emitted via REST API or WebSocket MUST include explicit UTC ISO 8601 formatting with trailing `"Z"` (e.g. `2026-09-22T15:30:00Z`).
  - Frontend parsing utility explicitly ensures trailing `"Z"` before creating `new Date(...)`.
* **Consequences**: Eliminates 5.5-hour IST/UTC phantom skew and guarantees microsecond accuracy across all timers.

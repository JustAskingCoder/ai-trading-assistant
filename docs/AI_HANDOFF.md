# AI Handoff & Continuity Briefing (`AI_HANDOFF.md`)

> **For the incoming AI Agent**: This document provides a complete orientation and handoff briefing on the **AI Trading Assistant** repository. It outlines exactly where the previous AI left off, where tickets and decisions are stored, how the system is constructed, and how to verify and run the project.

---

## 1. Executive Summary & Current State

* **Repository**: `ai-trading-assistant` (Git initialized, remote tracking `origin/main` and `origin/ai-handoff-tickets-and-decisions`).
* **Platform Purpose**: An institutional-grade intraday trading platform featuring live streaming market data (NSE Stocks, 24/5 Forex, 24/7 Crypto), deterministic indicator and pattern calculation, rule-based strategies, structured LLM market intelligence (Pydantic JSON), an absolute deterministic risk engine, paper broker execution, automated trade autopsies, and a high-performance React financial terminal.
* **Current Operational Status**:
  * **All 43 tasks across Epics 1 through 22 are 100% complete**.
  * **Test Suite**: 67/67 pytest unit tests passing (100% pass rate).
  * **Frontend Production Build**: Compiles cleanly with 0 TypeScript/Vite errors (`tsc && vite build`).
  * **Git Status**: All tickets, ADRs, post-mortems, and handoff documentation committed to branch `ai-handoff-tickets-and-decisions`.

---

## 2. Key Handoff Documents in this Repository

| File Path | Description & Purpose |
|---|---|
| [`Agent_incident.md`](file:///Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/Agent_incident.md) | **MANDATORY READING**. Detailed post-mortem of 13 historical incidents, mistaken assumptions, and 7 Golden Rules so you do not repeat past mistakes. |
| [`tasks.json`](file:///Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/tasks.json) | Complete structured Kanban ledger of all 43 tasks, subtasks, assignees, priorities, and dependency graphs. |
| [`board.md`](file:///Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/board.md) | Comprehensive narrative architecture, platform safety pipeline, and subtask roadmap across all 22 epics. |
| [`docs/DECISIONS.md`](file:///Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/docs/DECISIONS.md) | 10 Architectural Decision Records (ADRs) explaining core design decisions (unidirectional pipeline, capital calibration, holding windows, etc.). |
| [`docs/TICKETS.md`](file:///Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/docs/TICKETS.md) | Human- and machine-readable catalog of all 43 delivered tickets from Phase 1 through Phase 22. |
| [`README.md`](file:///Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/README.md) | Production user and developer guide with architecture diagrams, API specs, launch scripts, and Zerodha setup. |

---

## 3. Architecture & Safety Pipeline

The system is governed by a strict unidirectional safety constraint:
$$\text{Market Data / Replay} \longrightarrow \text{Deterministic Indicators} \longrightarrow \text{Deterministic Patterns} \longrightarrow \text{Rule Strategies} \longrightarrow \text{Structured AI Analysis} \longrightarrow \textbf{Deterministic Risk Engine} \longrightarrow \text{Paper Broker}$$

* **Safety Invariant**: Under no circumstance should AI output directly trigger order execution. The **Deterministic Risk Engine** (`backend/risk/risk_manager.py`) is the sole authority that can approve, reject, or size orders.

---

## 4. Key Configuration Parameters (`backend/core/config.py`)

* `INITIAL_CAPITAL`: ₹10,000.0 (virtual cash balance).
* `MAX_INVESTMENT_PER_TRADE`: ₹5,000.0 (max 50% single trade allocation).
* `RISK_PER_TRADE`: 0.015 (1.5% max risk budget per trade = ₹150).
* `MAX_DAILY_LOSS`: 0.03 (3.0% daily loss ceiling = ₹300).
* `MAX_OPEN_POSITIONS`: 6 (allows trading multi-asset scanner setups concurrently).
* `STOP_LOSS_MIN_BUFFER`: 1.0% (or $2.0\times\text{ATR}$ minimum).
* `TARGET_MIN_BUFFER`: 1.5% (or $3.0\times\text{ATR}$ minimum, guaranteeing $R:R \ge 1.5$).
* `HOLDING_WINDOW_MINUTES`: 30m base / 45m swing / 60m trend ride.
* `AUTO_RELEASE_ON_TREND_SHIFT`: `True` (auto-exits trades early on opposing reversal patterns or VWAP breach).
* `ADAPTIVE_SHIELD_COOLDOWN_MINUTES`: 20 to 40 minutes (suppresses repeat trades on symbols following a loss).

---

## 5. Verification Commands

### Backend Unit Tests
```bash
cd /Users/ashutoshjanrao/MundirFramework/ai-trading-assistant
PYTHONPATH=. venv/bin/pytest tests/test_trading_system.py
```
*Expected Result*: `67 passed in ~6.0s`.

### Frontend Production Build
```bash
cd /Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/frontend
npm run build
```
*Expected Result*: `✓ built in ~1.2s` with 0 TypeScript/Vite errors.

---

## 6. How to Run the Application

### 1-Click Launch
```bash
cd /Users/ashutoshjanrao/MundirFramework/ai-trading-assistant
./start.sh
```

### Manual Launch
1. **Backend**:
   ```bash
   cd /Users/ashutoshjanrao/MundirFramework/ai-trading-assistant
   source venv/bin/activate
   uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Frontend**:
   ```bash
   cd /Users/ashutoshjanrao/MundirFramework/ai-trading-assistant/frontend
   npm run dev -- --host 127.0.0.1 --port 5173
   ```
3. Open browser at `http://127.0.0.1:5173`.

---

## 7. Immediate Next Steps / Open Roadmap Opportunities
If the user requests new work, potential next areas include:
1. **Full Zerodha Kite Automated Order Execution**: Transition from PaperBroker stub to live Kite Connect execution guarded by a 2-factor human confirmation toggle.
2. **Additional Forex Currency Pairs / Commodities**: Support for Silver (`XAGUSD`), Natural Gas, Crude Oil (`CL=F`).
3. **Advanced Machine Learning / LightGBM Feature Store**: Deterministic quantitative feature extraction powering offline ML probability scoring alongside rule-based setups.
4. **Mobile Responsive PWA Optimization**: Enhance mobile viewport controls for the TradingView Lightweight Charts canvas.

# AI Trading Assistant — Paper Trading & AI Pattern Analysis

A local desktop/web quantitative analysis, pattern detection, strategy backtesting, and virtual paper-trading platform.

> **IMPORTANT FINANCIAL SAFETY NOTICE**:  
> Version 1 is strictly **LIVE-SIMULATION / BACKTESTING / PAPER TRADING**.  
> Real-money broker execution is disabled by default (`TRADING_MODE=PAPER`).  
> An LLM is never given direct authority to place trades or bypass deterministic risk controls.

---

## 1. Architectural Chain of Execution

The platform enforces a unidirectional pipeline:

```
Market Data (CSV / Replay)
           │
           ▼
Deterministic Indicators (EMA, RSI, MACD, VWAP, ATR, ADX, BB)
           │
           ▼
Deterministic Pattern Detection (Engulfing, Doji, Breakouts, Crossovers)
           │
           ▼
Rule-Based Strategy Engine (Momentum, Breakout, Trend-Following)
           │
           ▼
Structured AI Analysis (OpenAI / Claude / Local Heuristic via Pydantic JSON)
           │
           ▼
Deterministic Risk Manager (0.5% max risk, 2% daily loss limit, position sizing, kill switch)
           │
           ▼
Paper Broker (Virtual execution, position ledger, realized/unrealized P&L)
```

---

## 2. Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, SQLite (PostgreSQL compatible), Pydantic v2, Pandas, NumPy, Uvicorn, WebSockets.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TradingView Lightweight Charts, Zustand, Lucide Icons.
- **AI Engine**: Provider abstraction supporting OpenAI (`gpt-4o-mini`), Claude (`claude-3-5-haiku`), and local deterministic heuristics.

---

## 3. Project Directory Structure

```
ai-trading-assistant/
├── backend/
│   ├── api/
│   │   └── routes/
│   │       ├── ai.py              # Structured AI evaluation & analysis logging
│   │       ├── backtesting.py     # Quantitative backtest execution
│   │       ├── market.py          # CSV upload, candle feeds, simulator controls
│   │       ├── settings.py        # System configuration & parameters
│   │       └── trading.py         # Paper orders, portfolio KPIs, risk status, kill switch
│   ├── core/
│   │   ├── config.py              # Pydantic BaseSettings
│   │   ├── logging.py             # Rotating file & console logging
│   │   └── security.py
│   ├── data/
│   │   ├── candle_builder.py
│   │   ├── csv_loader.py          # Data ingestion & schema normalization
│   │   ├── data_validator.py      # Strict validation (disorder, duplicates, bad OHLC)
│   │   ├── market_simulator.py    # Historical candle replay & WebSocket broadcaster
│   │   └── sample_data_generator.py
│   ├── database/
│   │   ├── init_db.py             # Table initialization & initial capital seeding
│   │   ├── models.py              # 12 SQLAlchemy tables
│   │   └── session.py             # SQLAlchemy sessionmaker
│   ├── indicators/
│   │   └── engine.py              # EMA(20/50), SMA(20), RSI(14), MACD, VWAP, ATR, BB, ADX
│   ├── patterns/
│   │   └── engine.py              # Candlestick, volume, and breakout pattern detection
│   ├── strategies/
│   │   └── base_strategy.py       # MomentumStrategy, BreakoutStrategy, TrendFollowingStrategy
│   ├── ai/
│   │   ├── base_provider.py       # AIProvider, OpenAIProvider, ClaudeProvider, LocalHeuristic
│   │   └── schemas.py             # Pydantic request/response schemas
│   ├── risk/
│   │   └── risk_manager.py        # Position sizing, daily loss caps, stop-loss checks, kill switch
│   ├── paper/
│   │   └── paper_broker.py        # Virtual order execution, position tracking, P&L
│   ├── backtesting/
│   │   └── engine.py              # Walk-forward backtester free of look-ahead bias
│   ├── integrations/
│   │   ├── zerodha/
│   │   │   └── kite_client.py     # Future Kite Connect broker adapter stub
│   │   └── mcp/
│   │       └── client.py          # MCP query interface
│   ├── main.py                    # FastAPI app entrypoint & /ws/market WebSocket
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   └── CandlestickChart.tsx # Lightweight Charts with EMA & VWAP
│   │   │   ├── dashboard/
│   │   │   │   ├── AIAnalysisCard.tsx
│   │   │   │   ├── PortfolioCard.tsx
│   │   │   │   └── SignalCard.tsx
│   │   │   ├── trading/
│   │   │   │   ├── PaperOrderModal.tsx
│   │   │   │   └── PositionTable.tsx
│   │   │   └── backtesting/
│   │   │       └── BacktestView.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── data/
│   └── RELIANCE_5m.csv            # 500-candle sample dataset
├── tests/
│   └── test_trading_system.py     # Pytest test suite (100% pass)
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Quickstart Guide

### 1. Backend Setup
```bash
cd ai-trading-assistant
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Initialize database
python -m backend.database.init_db

# Run tests
PYTHONPATH=. pytest tests/test_trading_system.py

# Start Backend Server
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd ai-trading-assistant/frontend
npm install
npm run dev
```

Open your browser to `http://localhost:5173`.

---

## 5. Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```ini
TRADING_MODE=PAPER
INITIAL_CAPITAL=100000.0
RISK_PER_TRADE=0.005
MAX_DAILY_LOSS=0.02
MAX_OPEN_POSITIONS=3
MIN_RISK_REWARD=1.5
MIN_AI_CONFIDENCE=0.75
DEFAULT_TIMEFRAME=5m
DATABASE_URL=sqlite:///./database/trading.db

# Optional AI API keys (falls back to local heuristic if not provided)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

---

## 6. How to Run Features

### Replaying Market Data
1. Click **Start** in the simulator toolbar at the top.
2. Select speed (`1x`, `2x`, `5x`, `10x`, `50x`).
3. Watch simulated candles stream into the chart via WebSocket.
4. When a technical setup forms, a **Signal Card** appears automatically.

### Running AI Analysis
1. On an active signal card, click **ANALYZE WITH AI**.
2. The AI provider evaluates the technical setup and returns structured JSON (confidence, entry zone, invalidation rules).

### Executing a Paper Trade
1. Click **PAPER TRADE**.
2. The modal pre-fills entry price, stop loss, and target.
3. The deterministic **RiskManager** calculates position size based on 0.5% risk budget and verifies all rules.
4. The **PaperBroker** updates your virtual balance and active positions.

### Running a Backtest
1. Click the **Quantitative Backtester** tab.
2. Choose a strategy (`Momentum`, `Breakout`, or `TrendFollowing`).
3. Click **Run Backtest** to view win rate, net P&L, profit factor, drawdown, and trade logs.

---

## 7. Future Zerodha & MCP Architecture

- In `backend/integrations/zerodha/kite_client.py`, the `BrokerInterface` standardizes order execution. In Version 2, `ZerodhaBroker` will connect to Kite Connect without altering strategy or risk engines.
- In `backend/integrations/mcp/client.py`, the `MarketIntelligenceMCP` exposes read-only portfolio and market tools to external agent environments.
- **Safety Guarantee**: Real-money trading cannot be activated without explicitly modifying `TRADING_MODE=LIVE`, providing API keys, and passing human checkpoint verification.

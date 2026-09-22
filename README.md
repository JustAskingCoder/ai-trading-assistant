# 📈 AI Trading Assistant — Quantitative Scalp Analysis & Paper Trading

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![TradingView Lightweight Charts](https://img.shields.io/badge/Lightweight_Charts-4.1-blue.svg)](https://tradingview.github.io/lightweight-charts/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An institutional-grade local desktop/web quantitative analysis, pattern detection, strategy backtesting, and virtual paper-trading platform designed for Indian Equities (NSE) and Global Forex markets.

> 🛡️ **FINANCIAL SAFETY NOTICE**:  
> By default, the system operates in **STRICT PAPER TRADING MODE** (`TRADING_MODE=PAPER`).  
> Virtual capital is calibrated to **₹10,000** with hard risk rules and a ₹5,000 per-trade allocation cap.  
> An AI model / LLM is **never** given direct authority to execute trades or bypass the deterministic risk engine.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Architectural Chain of Execution](#-architectural-chain-of-execution)
3. [Technology Stack](#-technology-stack)
4. [Directory Structure](#-directory-structure)
5. [Prerequisites](#-prerequisites)
6. [Quickstart (1-Click Launch)](#-quickstart-1-click-launch)
7. [Manual Installation Guide](#-manual-installation-guide)
8. [Configuration & Environment Variables](#-configuration--environment-variables)
9. [Zerodha Kite Live Market Adapter (Zero-Delay)](#-zerodha-kite-live-market-adapter-zero-delay)
10. [Automated Risk & Bracket Rules](#-automated-risk--bracket-rules)
11. [API & WebSocket Reference](#-api--websocket-reference)
12. [Running Tests](#-running-tests)
13. [License & Disclaimer](#-license--disclaimer)

---

## ✨ Key Features

- 🇮🇳 **Live NSE & Multi-Asset Scanner**: Real-time intraday monitoring across top Indian equities (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`) and Forex currency pairs (`USDINR`, `EURUSD`, `GBPUSD`, `EURINR`) with 5-second asynchronous updates.
- ⚡ **Zerodha Kite Zero-Delay Adapter**: Connect via your existing Zerodha Kite credentials using either the **free Web Enctoken** (no ₹2,000/month API fee required) or official Kite Connect API key.
- 📊 **TradingView Lightweight Charts**: Smooth 60fps candlestick rendering with volume buying/selling pressure histograms, EMA(20), EMA(50), and VWAP overlays aligned to **Indian Standard Time (IST, UTC+5:30)**.
- 🧠 **Structured AI Analysis (Pydantic JSON)**: Strict schema-enforced technical validations powered by OpenAI (`gpt-4o-mini`), Anthropic Claude (`claude-3-5-haiku`), or built-in local quantitative heuristics.
- 🛡️ **Deterministic Bracket Automation**:
  - Auto Stop-Loss and Scalp Target (0.4%–0.6%) limit cross detections.
  - **Trailing Breakeven Lock**: Stop-loss automatically trails to entry price once a trade crosses +0.3% unrealized profit.
  - **10-Minute Window Expiry**: Intraday scalp trades auto-exit at market price if held $\ge$ 10 minutes, complete with real-time countdown timers.
- 🎮 **Historical Market Simulator**: Replay multi-day 5-minute historical datasets with variable speed controls (`1x`, `2x`, `5x`, `10x`, `50x`), Play, Pause, Stop, and Reset.
- 📈 **Look-Ahead Bias-Free Backtester**: Walk-forward backtesting engine calculating Win Rate, Profit Factor, Max Drawdown, Sharpe Ratio, and trade logs.

---

## 🔗 Architectural Chain of Execution

The platform strictly enforces an isolated, unidirectional pipeline to guarantee execution safety:

```
┌────────────────────────────────────────────────────────┐
│  Market Data (Zerodha 0-Delay / Live NSE / CSV Replay) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Deterministic Indicators (EMA, RSI, MACD, VWAP, ATR)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Deterministic Pattern Recognition (Engulfing, Breaks) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Rule-Based Strategies (Momentum, Pullback, Scalp)     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Structured AI Reasoning (Validated via Pydantic JSON) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Deterministic Risk Engine (1.5% Risk, ₹5k Cap, SL/TP) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  Paper Broker Execution (Virtual SQLite Ledger & P&L)  │
└────────────────────────────────────────────────────────┘
```

---

## 💻 Technology Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com) (Python 3.10+)
- **Server**: [Uvicorn](https://www.uvicorn.org) with AsyncIO WebSocket streaming
- **Database & ORM**: SQLite via [SQLAlchemy 2.0](https://www.sqlalchemy.org) (PostgreSQL ready)
- **Data & Math**: Pandas, NumPy, yfinance
- **Validation**: Pydantic v2 (strict JSON typing)
- **Testing**: Pytest (40 unit and integration tests, 100% pass)

### Frontend
- **Framework**: [React 18](https://react.dev) with [TypeScript](https://www.typescriptlang.org)
- **Build Tool**: [Vite 5](https://vitejs.dev)
- **Styling**: [Tailwind CSS 3.4](https://tailwindcss.com)
- **Charting**: [TradingView Lightweight Charts 4.1](https://tradingview.github.io/lightweight-charts/)
- **Icons**: [Lucide React](https://lucide.dev)
- **Networking**: Axios & Native WebSockets

---

## 📁 Directory Structure

```
ai-trading-assistant/
├── backend/
│   ├── ai/                      # AI provider abstraction (OpenAI, Claude, Heuristics)
│   │   ├── base_provider.py
│   │   └── schemas.py
│   ├── api/
│   │   └── routes/              # FastAPI REST routers
│   │       ├── ai.py            # AI signal evaluation endpoint
│   │       ├── backtesting.py   # Historical backtest engine endpoint
│   │       ├── market.py        # Quotes, candles, watchlist, mode toggle
│   │       ├── settings.py      # System configuration
│   │       ├── trading.py       # Paper orders, portfolio, positions, kill switch
│   │       └── zerodha.py       # Zerodha Kite connect, status & disconnect
│   ├── backtesting/
│   │   └── engine.py            # Lookahead bias-free backtester
│   ├── core/                    # App config, logging & security
│   ├── data/
│   │   ├── csv_loader.py        # CSV parsing & normalization
│   │   ├── data_validator.py    # Strict chronologic & price validator
│   │   ├── live_market_service.py # Real-time market poller & candle builder
│   │   └── market_simulator.py  # WebSocket broadcast replay simulator
│   ├── database/
│   │   ├── init_db.py           # DB tables migration & ₹10,000 capital seeder
│   │   ├── models.py            # 12 SQLAlchemy tables
│   │   └── session.py           # DB session factory
│   ├── indicators/
│   │   └── engine.py            # Vectorized EMA, SMA, RSI, MACD, VWAP, ATR, BB, ADX
│   ├── integrations/
│   │   └── zerodha/
│   │       └── kite_client.py   # KiteLiveClient (Enctoken & API key adapter)
│   ├── paper/
│   │   └── paper_broker.py      # Virtual execution engine with bracket automation
│   ├── patterns/
│   │   └── engine.py            # Deterministic candlestick & price patterns
│   ├── risk/
│   │   └── risk_manager.py      # Sizing formula, ₹5,000 cap, daily loss limit
│   ├── strategies/
│   │   └── base_strategy.py     # Breakout, Momentum & TrendFollowing strategies
│   ├── main.py                  # FastAPI application & /ws/market WebSocket
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── backtesting/     # Backtesting UI & trade logs
│   │   │   ├── charts/          # TradingView Lightweight CandlestickChart
│   │   │   ├── dashboard/       # Watchlist, AI Card, Signal Card, Zerodha modal
│   │   │   └── trading/         # Position Table & Paper Order Modal
│   │   ├── services/
│   │   │   └── api.ts           # Axios client & WebSocket helpers
│   │   ├── types/
│   │   │   └── index.ts         # TypeScript data contracts
│   │   ├── App.tsx              # Main dashboard root
│   │   ├── index.css            # Custom financial UI styles
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts           # Proxy config for /api and /ws
│   └── tailwind.config.js
├── data/
│   └── RELIANCE_5m.csv          # Sample 5-minute replay dataset
├── tests/
│   └── test_trading_system.py   # Comprehensive pytest test suite (40 tests)
├── .env.example
├── .gitignore
├── start.sh                     # 1-click startup script (Unix/Mac)
├── stop.sh                      # Clean shutdown script
└── README.md
```

---

## 📦 Prerequisites

Before running the application, ensure your environment has:
- **Python**: `3.10` or higher ([Download Python](https://www.python.org/downloads/))
- **Node.js**: `18.x` or higher and `npm` ([Download Node.js](https://nodejs.org/))
- **Git**: Installed and configured

---

## 🚀 Quickstart (1-Click Launch)

On macOS / Linux:

```bash
# 1. Clone the repository
git clone https://github.com/JustAskingCoder/ai-trading-assistant.git
cd ai-trading-assistant

# 2. Make startup script executable and launch
chmod +x start.sh stop.sh
./start.sh
```

`start.sh` will automatically:
1. Create a Python virtual environment (`venv/`) and install backend dependencies.
2. Initialize the SQLite database and seed ₹10,000 paper capital.
3. Start the FastAPI backend on `http://127.0.0.1:8000`.
4. Start the Vite React development server on `http://localhost:5173`.

To stop both services cleanly, press `Ctrl+C` or run `./stop.sh`.

---

## 🛠️ Manual Installation Guide

If you prefer running the backend and frontend in separate terminals:

### Terminal 1: Backend
```bash
cd ai-trading-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment settings
cp .env.example .env

# Initialize database
python -m backend.database.init_db

# Start FastAPI server
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd ai-trading-assistant/frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

Open your browser at **[http://localhost:5173](http://localhost:5173)**.  
Swagger API documentation is available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

---

## ⚙️ Configuration & Environment Variables

Copy `.env.example` to `.env` in the root folder to customize settings:

```ini
# Core Platform Mode (Always PAPER in V1)
TRADING_MODE=PAPER

# Capital & Risk Parameters (Calibrated for Scalping)
INITIAL_CAPITAL=10000.0
MAX_INVESTMENT_PER_TRADE=5000.0
RISK_PER_TRADE=0.015
MAX_DAILY_LOSS=0.03
MAX_OPEN_POSITIONS=3
MIN_RISK_REWARD=1.2
MIN_AI_CONFIDENCE=0.75

# Market Defaults
DEFAULT_TIMEFRAME=5m
DATABASE_URL=sqlite:///./database/trading.db

# Optional AI Providers (System falls back to quantitative heuristics if omitted)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

---

## ⚡ Zerodha Kite Live Market Adapter (Zero-Delay)

The platform includes a built-in adapter for Indian traders using **Zerodha Kite**. You can connect using your browser session token **without paying ₹2,000/month** for a Kite Connect developer subscription!

### How to get your free Web Enctoken (Takes 30 Seconds):
1. Log in to [kite.zerodha.com](https://kite.zerodha.com) in Chrome, Brave, or Firefox.
2. Press `F12` (or `Cmd + Option + I` on Mac) to open **Developer Tools** and switch to the **Application** (or **Storage**) tab.
3. In the left sidebar, expand **Cookies** → `https://kite.zerodha.com`.
4. Find the cookie named **`enctoken`** and copy its value.
5. In our dashboard, click **🔌 Connect Zerodha** in the top header.
6. Select **Kite Web Enctoken**, paste your token, and click **Connect Live Feed**.

Once connected:
- The system automatically engages **`🔴 LIVE NSE`** mode.
- Market feeds for Indian equities stream zero-delay quotes directly from Zerodha Kite.
- Your session token is safely stored in browser `localStorage` and can be disconnected with one click.

---

## 🛡️ Automated Risk & Bracket Rules

The platform implements non-bypassable safety mechanisms:

1. **Position Sizing Formula**:
   $$\text{Quantity} = \min\left( \left\lfloor \frac{\text{Capital} \times 0.015}{|\text{Entry} - \text{StopLoss}|} \right\rfloor, \left\lfloor \frac{5000}{\text{Price}} \right\rfloor \right)$$
   Every position is capped at a maximum of ₹5,000 total investment.
2. **Structural Stop-Loss & Target**:
   - Longs: $\text{StopLoss} = \text{Entry} - (0.5\% \times \text{Price})$, $\text{Target} = \text{Entry} + (0.6\% \times \text{Price})$ (Minimum 1:1.2 Risk-to-Reward).
3. **Trailing Breakeven Lock**:
   - When unrealized profit reaches **+0.3%**, the Stop-Loss is automatically adjusted to the entry price (`BREAKEVEN_TRAILED`), guaranteeing a risk-free trade.
4. **10-Minute Maximum Expiry**:
   - If a scalp position remains open after 10 minutes, the background risk monitor auto-exits the position at market price with reason `"10-Min Window Expired"`.

---

## 🔌 API & WebSocket Reference

### Core Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health status and operational mode check |
| `GET` | `/api/market/{symbol}/candles` | Latest intraday candles with 14 technical indicators |
| `GET` | `/api/market/watchlist` | Multi-asset quotes, signals, and scalp parameters |
| `POST` | `/api/market/mode` | Toggle between `LIVE` and `SIMULATOR` modes |
| `POST` | `/api/simulator/control` | Control simulator (`start`, `pause`, `stop`, `reset`) |
| `POST` | `/api/zerodha/connect` | Authenticate Zerodha Kite via Enctoken or API Key |
| `GET` | `/api/zerodha/status` | Current Zerodha connection state |
| `POST` | `/api/paper/orders` | Submit a paper order with SL and Target brackets |
| `GET` | `/api/positions` | List active virtual open positions |
| `POST` | `/api/positions/{id}/close` | Manually close an open position at current market price |
| `POST` | `/api/portfolio/reset` | Reset virtual portfolio back to ₹10,000 cash |
| `POST` | `/api/ai/analyze` | Run structured Pydantic AI analysis on active setup |
| `POST` | `/api/backtest` | Run backtest on historical strategy |
| `WS` | `/ws/market` | WebSocket stream broadcasting ticks, indicators, and auto-exits |

---

## 🧪 Running Tests

A comprehensive Pytest test suite verifies indicators, pattern recognition, risk constraints, paper broker mechanics, and WebSocket broadcasting:

```bash
# Activate virtual environment
source venv/bin/activate

# Run test suite
PYTHONPATH=. pytest tests/test_trading_system.py -v
```

All **40 tests** pass 100%.

To verify the frontend TypeScript build:
```bash
cd frontend
npm run build
```

---

## 📄 License & Disclaimer

This project is licensed under the **MIT License**.

**Disclaimer**: This software is developed for educational, research, and simulation purposes only. It is not financial advice. Algorithmic and intraday trading involves significant financial risk. Always test thoroughly in simulation before considering live capital deployment.

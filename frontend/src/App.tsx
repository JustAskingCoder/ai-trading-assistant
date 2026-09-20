import React, { useEffect, useState, useRef } from 'react';
import { api } from './services/api';
import { CandleData, PortfolioData, PositionData, TradeData, Signal, AIAnalysis, RiskStatus } from './types';
import { CandlestickChart } from './components/charts/CandlestickChart';
import { PortfolioCard } from './components/dashboard/PortfolioCard';
import { SignalCard } from './components/dashboard/SignalCard';
import { AIAnalysisCard } from './components/dashboard/AIAnalysisCard';
import { PositionTable } from './components/trading/PositionTable';
import { PaperOrderModal } from './components/trading/PaperOrderModal';
import { BacktestView } from './components/backtesting/BacktestView';
import {
  Play, Pause, Square, RotateCcw, Upload, ShieldAlert,
  ShieldCheck, Activity, Terminal, RefreshCw, BarChart2,
  CheckCircle2, AlertTriangle, X
} from 'lucide-react';

export default function App() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [positions, setPositions] = useState<PositionData[]>([]);
  const [trades, setTrades] = useState<TradeData[]>([]);
  const [riskStatus, setRiskStatus] = useState<RiskStatus | null>(null);

  const [activeSignal, setActiveSignal] = useState<Signal | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [orderAlert, setOrderAlert] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  // Auto-dismiss order alert after 8 seconds
  useEffect(() => {
    if (orderAlert) {
      const timer = setTimeout(() => {
        setOrderAlert(null);
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [orderAlert]);

  // Simulator state
  const [simRunning, setSimRunning] = useState(false);
  const [simSpeed, setSimSpeed] = useState(2.0);

  // Modals
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [selectedSignalForOrder, setSelectedSignalForOrder] = useState<Signal | null>(null);
  const [activeTab, setActiveTab] = useState<'live' | 'backtest'>('live');

  // Load portfolio and positions data
  const loadPortfolioData = async () => {
    try {
      const [p, pos, tr] = await Promise.all([
        api.getPortfolio(),
        api.getPositions(),
        api.getTrades()
      ]);
      setPortfolio(p);
      setPositions(pos);
      setTrades(tr);
    } catch (e) {
      console.error('Error fetching portfolio data:', e);
    }
  };

  // Load initial data
  const fetchData = async () => {
    try {
      const [c, p, pos, tr, r] = await Promise.all([
        api.getCandles(symbol, '5m', 200),
        api.getPortfolio(),
        api.getPositions(),
        api.getTrades(),
        api.getRiskStatus()
      ]);
      setCandles(c);
      setPortfolio(p);
      setPositions(pos);
      setTrades(tr);
      setRiskStatus(r);
    } catch (e) {
      console.error('Error fetching initial data:', e);
    }
  };

  useEffect(() => {
    fetchData();
  }, [symbol]);

  // WebSocket Live Stream Connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/market`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'AUTO_EXIT_TRIGGERED') {
          const data = msg.data || msg;
          const isTarget = data.reason === 'Target Hit';
          setOrderAlert({
            type: isTarget ? 'success' : 'error',
            message: `${isTarget ? '🎯 Target Hit!' : '🛑 Stop Loss Hit!'} Auto-exited ${data.quantity} shares of ${data.symbol} @ ₹${data.exit_price?.toFixed(2)} (${data.pnl >= 0 ? '+' : ''}₹${data.pnl?.toFixed(2)})`
          });
          loadPortfolioData();
        } else if (msg.type === 'CANDLE_UPDATE') {
          const newCandle: CandleData = {
            timestamp: msg.timestamp,
            open: msg.open,
            high: msg.high,
            low: msg.low,
            close: msg.close,
            volume: msg.volume,
            ema20: msg.indicators?.ema20,
            ema50: msg.indicators?.ema50,
            vwap: msg.indicators?.vwap,
            rsi: msg.indicators?.rsi,
          };

          setCandles((prev) => {
            const updated = [...prev, newCandle];
            return updated.slice(-250);
          });

          // Check for new signals
          if (msg.signals && msg.signals.length > 0) {
            setActiveSignal(msg.signals[0]);
          }

          // Refresh portfolio and positions periodically
          api.getPortfolio().then(setPortfolio).catch(() => {});
          api.getPositions().then(setPositions).catch(() => {});
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  // Simulator controls
  const handleSimAction = async (action: 'start' | 'pause' | 'stop' | 'reset') => {
    try {
      const res = await api.controlSimulator(action, simSpeed);
      setSimRunning(res.is_running && !res.is_paused);
      if (action === 'reset' || action === 'stop') {
        fetchData();
      }
    } catch (e) {
      console.error('Simulator control error:', e);
    }
  };

  // Kill Switch Toggle
  const handleToggleKillSwitch = async () => {
    if (!riskStatus) return;
    const nextState = !riskStatus.kill_switch_active;
    try {
      const res = await api.toggleKillSwitch(nextState);
      setRiskStatus((prev) => prev ? { ...prev, kill_switch_active: res.kill_switch_active } : null);
    } catch (e) {
      console.error('Kill switch toggle error:', e);
    }
  };

  // AI Analysis trigger
  const handleAnalyzeAI = async (signal: Signal) => {
    setAiLoading(true);
    try {
      const latestCandle = candles[candles.length - 1];
      const payload = {
        symbol: signal.symbol,
        price: signal.entry_price,
        timeframe: '5m',
        trend: 'bullish',
        indicators: latestCandle ? {
          rsi: latestCandle.rsi,
          ema20: latestCandle.ema20,
          ema50: latestCandle.ema50,
          vwap: latestCandle.vwap
        } : {},
        patterns: signal.patterns || [],
        strategy_signal: signal.signal,
        strategy_reason: signal.reason
      };

      const result = await api.analyzeWithAI(payload);
      setAiAnalysis(result);
    } catch (e: any) {
      console.error('AI analysis error:', e);
      alert(`AI Analysis Failed: ${e?.response?.data?.detail || e.message || 'Unknown error'}`);
    } finally {
      setAiLoading(false);
    }
  };

  // Order submission
  const handlePaperOrder = (signal: Signal) => {
    setSelectedSignalForOrder(signal);
    setOrderModalOpen(true);
  };

  const handleOrderSubmit = async (orderData: any) => {
    await api.placePaperOrder(orderData);
    await loadPortfolioData();
  };

  // Direct 1-click order execution handler
  const handleDirectOrder = async (orderData: {
    symbol: string;
    side: string;
    price: number;
    stop_loss: number;
    target: number;
    order_type?: string;
    quantity?: number;
  }): Promise<{ success: boolean; data?: any; error?: string }> => {
    try {
      const res = await api.placePaperOrder({
        symbol: orderData.symbol,
        side: orderData.side,
        price: orderData.price,
        stop_loss: orderData.stop_loss,
        target: orderData.target,
        order_type: orderData.order_type || 'MARKET'
      });
      await loadPortfolioData();
      return { success: true, data: res };
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Order execution failed';
      return { success: false, error: errorMsg };
    }
  };

  // Portfolio Reset
  const handleResetPortfolio = async () => {
    if (!window.confirm('Reset virtual portfolio to ₹100,000 initial capital?')) {
      return;
    }
    try {
      await api.resetPortfolio();
      await loadPortfolioData();
    } catch (e) {
      console.error('Reset portfolio error:', e);
    }
  };

  // Close Position
  const handleClosePosition = async (id: number) => {
    try {
      await api.closePosition(id);
      await loadPortfolioData();
    } catch (e) {
      console.error('Close position error:', e);
    }
  };

  // CSV Upload handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('symbol', symbol);
    formData.append('interval', '5m');

    try {
      await api.uploadCsv(formData);
      alert('CSV uploaded and validated successfully!');
      fetchData();
    } catch (err: any) {
      alert(`Upload failed: ${err?.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 p-4 md:p-6 space-y-5">
      {/* Header Bar */}
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-dark-600 bg-dark-800 p-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-sky-500 shadow-md">
            <Terminal className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-extrabold tracking-tight text-white">AI Trading Assistant</h1>
              <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-bold text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                ONLINE
              </span>
              <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[11px] font-bold text-sky-400">
                PAPER MODE
              </span>
            </div>
            <p className="text-xs text-slate-400">Local Quantitative Replay, Technical Patterns & Structured AI Strategy</p>
          </div>
        </div>

        {/* Simulator & Kill Switch Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Simulator Controls */}
          <div className="flex items-center gap-1 rounded-xl border border-dark-600 bg-dark-900/80 p-1">
            <button
              onClick={() => handleSimAction('start')}
              disabled={simRunning}
              title="Start Simulation"
              className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-30"
            >
              <Play className="h-3.5 w-3.5 fill-current" /> Start
            </button>
            <button
              onClick={() => handleSimAction('pause')}
              disabled={!simRunning}
              title="Pause Simulation"
              className="rounded-lg p-1.5 text-slate-300 hover:bg-dark-700 hover:text-white disabled:opacity-30"
            >
              <Pause className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleSimAction('stop')}
              title="Stop Simulation"
              className="rounded-lg p-1.5 text-slate-300 hover:bg-dark-700 hover:text-white"
            >
              <Square className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleSimAction('reset')}
              title="Reset Simulation"
              className="rounded-lg p-1.5 text-slate-300 hover:bg-dark-700 hover:text-white"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            {/* Speed Selector */}
            <select
              value={simSpeed}
              onChange={(e) => {
                const s = Number(e.target.value);
                setSimSpeed(s);
                if (simRunning) handleSimAction('start');
              }}
              className="rounded-lg border-0 bg-transparent px-2 py-1 text-xs font-semibold text-slate-300 focus:ring-0"
            >
              <option value="1">1x</option>
              <option value="2">2x</option>
              <option value="5">5x</option>
              <option value="10">10x</option>
              <option value="50">50x</option>
            </select>
          </div>

          {/* CSV Upload */}
          <label className="flex cursor-pointer items-center gap-1.5 rounded-xl border border-dark-600 bg-dark-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-dark-600 transition-colors">
            <Upload className="h-3.5 w-3.5" />
            <span>Upload CSV</span>
            <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
          </label>

          {/* Reset Portfolio */}
          <button
            onClick={handleResetPortfolio}
            title="Reset Virtual Portfolio to ₹100,000"
            className="flex items-center gap-1.5 rounded-xl border border-dark-600 bg-dark-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-dark-600 hover:text-amber-400 hover:border-amber-500/40 transition-colors shadow-sm"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Portfolio</span>
          </button>

          {/* Global Kill Switch */}
          <button
            onClick={handleToggleKillSwitch}
            className={`flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-extrabold transition-colors shadow-sm ${
              riskStatus?.kill_switch_active
                ? 'bg-red-600 text-white animate-pulse'
                : 'border border-dark-600 bg-dark-700 text-slate-300 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/40'
            }`}
          >
            <ShieldAlert className="h-4 w-4" />
            {riskStatus?.kill_switch_active ? 'KILL SWITCH ACTIVE' : 'KILL SWITCH'}
          </button>
        </div>
      </header>

      {/* Auto-Exit / Order Notification Toast Banner */}
      {orderAlert && (
        <div
          className={`flex items-center justify-between gap-3 rounded-xl p-3.5 shadow-xl border transition-all ${
            orderAlert.type === 'success'
              ? 'bg-emerald-950/80 border-emerald-500/60 text-emerald-200'
              : 'bg-rose-950/80 border-rose-500/60 text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2.5 text-sm font-semibold">
            {orderAlert.type === 'success' ? (
              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-5 w-5 shrink-0 text-rose-400" />
            )}
            <span>{orderAlert.message}</span>
          </div>
          <button
            onClick={() => setOrderAlert(null)}
            className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-dark-700/50 transition-colors"
            title="Dismiss notification"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Portfolio KPIs */}
      <PortfolioCard portfolio={portfolio} />

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-dark-700 pb-2">
        <button
          onClick={() => setActiveTab('live')}
          className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-bold transition-colors ${
            activeTab === 'live' ? 'bg-trade-blue text-white shadow-md' : 'text-slate-400 hover:text-white'
          }`}
        >
          <Activity className="h-4 w-4" /> Live Market & Execution
        </button>
        <button
          onClick={() => setActiveTab('backtest')}
          className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-bold transition-colors ${
            activeTab === 'backtest' ? 'bg-trade-blue text-white shadow-md' : 'text-slate-400 hover:text-white'
          }`}
        >
          <BarChart2 className="h-4 w-4" /> Quantitative Backtester
        </button>
      </div>

      {activeTab === 'live' ? (
        <div className="space-y-5">
          {/* Main Candlestick Chart */}
          <CandlestickChart data={candles} symbol={symbol} />

          {/* Intelligence & Signal Deck */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <SignalCard
              signal={activeSignal}
              onAnalyzeAI={handleAnalyzeAI}
              onPaperTrade={handlePaperOrder}
              onIgnore={() => setActiveSignal(null)}
              onDirectOrder={async (signal, qty) => {
                return await handleDirectOrder({
                  symbol: signal.symbol,
                  side: signal.signal,
                  price: signal.entry_price,
                  stop_loss: signal.stop_loss,
                  target: signal.target,
                  quantity: qty
                });
              }}
            />
            <AIAnalysisCard
              analysis={aiAnalysis}
              loading={aiLoading}
              symbol={activeSignal?.symbol || symbol}
              onDirectOrder={handleDirectOrder}
            />
          </div>

          {/* Open Positions and Completed Trade History */}
          <PositionTable positions={positions} trades={trades} onClosePosition={handleClosePosition} />
        </div>
      ) : (
        <BacktestView symbol={symbol} />
      )}

      {/* Paper Order Modal */}
      <PaperOrderModal
        isOpen={orderModalOpen}
        signal={selectedSignalForOrder}
        onClose={() => setOrderModalOpen(false)}
        onSubmit={handleOrderSubmit}
      />
    </div>
  );
}

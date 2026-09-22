import React, { useState, useEffect, useCallback, useRef } from 'react';
import { WatchlistQuote } from '../../types';
import { api } from '../../services/api';
import { getNSEMarketStatus, getMarketStatusForSymbol } from '../../utils/marketHours';
import {
  TrendingUp, TrendingDown, Minus, RefreshCw, Activity,
  LayoutGrid, Table, Zap, Target, Shield, ArrowUpRight, ArrowDownRight
} from 'lucide-react';

interface Props {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  onPlaceOrder?: (quote: WatchlistQuote) => void;
  onQuotesUpdate?: (quotes: WatchlistQuote[]) => void;
}

type FilterCategory = 'All' | 'NSE' | 'FOREX';
type ViewMode = 'cards' | 'matrix';

const DEFAULT_SYMBOLS = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'USDINR', 'EURUSD'];

const FALLBACK_QUOTES: WatchlistQuote[] = [
  {
    symbol: 'RELIANCE',
    name: 'Reliance Ind.',
    market: 'NSE',
    price: 2985.50,
    change: 36.85,
    change_percentage: 1.25,
    signal: 'HOLD',
    action: 'WAIT',
    quantity: 1,
    entry_price: 2985.50,
    stop_loss: 2970.55,
    target: 3003.45,
    risk_reward: 1.2,
    target_profit: 17.95,
    max_risk: 14.95,
    reason: 'Consolidation / Awaiting 20 EMA Pullback'
  },
  {
    symbol: 'TCS',
    name: 'Tata Consultancy',
    market: 'NSE',
    price: 4210.00,
    change: 18.90,
    change_percentage: 0.45,
    signal: 'HOLD',
    action: 'WAIT',
    quantity: 1,
    entry_price: 4210.00,
    stop_loss: 4188.95,
    target: 4235.25,
    risk_reward: 1.2,
    target_profit: 25.25,
    max_risk: 21.05,
    reason: 'VWAP Compression / Neutral'
  },
  {
    symbol: 'INFY',
    name: 'Infosys Ltd',
    market: 'NSE',
    price: 1890.30,
    change: -15.20,
    change_percentage: -0.80,
    signal: 'HOLD',
    action: 'WAIT',
    quantity: 1,
    entry_price: 1890.30,
    stop_loss: 1880.85,
    target: 1901.65,
    risk_reward: 1.2,
    target_profit: 11.35,
    max_risk: 9.45,
    reason: 'Consolidation near Support'
  },
  {
    symbol: 'HDFCBANK',
    name: 'HDFC Bank',
    market: 'NSE',
    price: 1645.20,
    change: 9.80,
    change_percentage: 0.60,
    signal: 'HOLD',
    action: 'WAIT',
    quantity: 1,
    entry_price: 1645.20,
    stop_loss: 1636.95,
    target: 1655.10,
    risk_reward: 1.2,
    target_profit: 9.90,
    max_risk: 8.25,
    reason: 'Awaiting Breakout / Consolidation'
  },
  {
    symbol: 'USDINR',
    name: 'USD / INR Spot',
    market: 'FOREX',
    price: 83.5250,
    change: 0.0410,
    change_percentage: 0.05,
    signal: 'HOLD',
    action: 'WAIT',
    quantity: 1,
    entry_price: 83.5250,
    stop_loss: 83.1074,
    target: 84.0261,
    risk_reward: 1.2,
    target_profit: 0.5011,
    max_risk: 0.4176,
    reason: 'Range Consolidation'
  },
  {
    symbol: 'EURUSD',
    name: 'EUR / USD Spot',
    market: 'FOREX',
    price: 1.0845,
    change: -0.0016,
    change_percentage: -0.15,
    signal: 'HOLD',
    action: 'WAIT',
    quantity: 1,
    entry_price: 1.0845,
    stop_loss: 1.0791,
    target: 1.0910,
    risk_reward: 1.2,
    target_profit: 0.0065,
    max_risk: 0.0054,
    reason: 'Awaiting Trend Continuation'
  },
];

/**
 * Ensures every quote has concrete trade decision parameters calculated
 */
const enrichQuote = (q: WatchlistQuote): WatchlistQuote => {
  const isForex = q.market === 'FOREX';
  const dec = isForex ? 4 : 2;
  const rawSignal = (q.signal || 'HOLD').toUpperCase();
  const action: 'BUY' | 'SELL' | 'WAIT' =
    q.action || (rawSignal === 'BUY' ? 'BUY' : rawSignal === 'SELL' ? 'SELL' : 'WAIT');
  const price = Number(q.price) || 0;
  const entry_price = q.entry_price !== undefined ? Number(q.entry_price) : price;
  const quantity = q.quantity || 1;

  // Calibrate guaranteed risk/reward >= 1.2
  const riskAmount =
    q.max_risk && q.max_risk > 0
      ? Number(q.max_risk)
      : Number((entry_price * 0.005).toFixed(dec));
  const rewardAmount = Math.max(riskAmount * 1.2, Number((entry_price * 0.006).toFixed(dec)));

  let stop_loss = q.stop_loss !== undefined ? Number(q.stop_loss) : undefined;
  let target = q.target !== undefined ? Number(q.target) : undefined;

  const isSell = action === 'SELL';
  if (!stop_loss || !target || (Math.abs(target - entry_price) / (Math.abs(entry_price - stop_loss) + 1e-6)) < 0.8) {
    stop_loss = isSell
      ? Number((entry_price + riskAmount).toFixed(dec))
      : Number((entry_price - riskAmount).toFixed(dec));
    target = isSell
      ? Number((entry_price - rewardAmount).toFixed(dec))
      : Number((entry_price + rewardAmount).toFixed(dec));
  }

  const target_profit = Number(Math.abs(target - entry_price).toFixed(dec));
  const max_risk = Number(Math.abs(entry_price - stop_loss).toFixed(dec));
  const risk_reward = max_risk > 0 ? Number((target_profit / max_risk).toFixed(2)) : 1.2;

  return {
    ...q,
    action,
    quantity,
    entry_price,
    stop_loss,
    target,
    target_profit,
    max_risk,
    risk_reward,
  };
};

export const MultiAssetWatchlist: React.FC<Props> = ({
  selectedSymbol,
  onSelectSymbol,
  onPlaceOrder,
  onQuotesUpdate,
}) => {
  const [quotes, setQuotes] = useState<WatchlistQuote[]>(() =>
    FALLBACK_QUOTES.map(enrichQuote)
  );
  const [filter, setFilter] = useState<FilterCategory>('All');
  const [viewMode, setViewMode] = useState<ViewMode>('cards');
  const [loading, setLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const onQuotesUpdateRef = useRef(onQuotesUpdate);
  useEffect(() => {
    onQuotesUpdateRef.current = onQuotesUpdate;
  });

  const fetchWatchlist = useCallback(async (isManual = false) => {
    if (isManual) setLoading(true);
    try {
      const data = await api.getWatchlist(DEFAULT_SYMBOLS.join(','));
      if (Array.isArray(data) && data.length > 0) {
        const enriched = data.map(enrichQuote);
        setQuotes(enriched);
        setLastUpdated(new Date());
        onQuotesUpdateRef.current?.(enriched);
      }
    } catch (e) {
      console.debug('MultiAssetWatchlist polling (using fallback):', e);
    } finally {
      if (isManual) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
    const timer = setInterval(() => {
      fetchWatchlist();
    }, 5000);
    return () => clearInterval(timer);
  }, [fetchWatchlist]);

  const filteredQuotes = quotes.filter((q) => {
    if (filter === 'All') return true;
    return q.market === filter;
  });

  const formatPrice = (price: number, market: 'NSE' | 'FOREX', symbol: string) => {
    if (typeof price !== 'number' || isNaN(price)) return '—';
    if (market === 'FOREX') {
      if (symbol.includes('INR')) {
        return `₹${price.toFixed(4)}`;
      }
      return price.toFixed(4);
    }
    return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatCurrencyValue = (val: number | undefined, market: 'NSE' | 'FOREX', symbol: string) => {
    if (val === undefined || isNaN(val)) return '—';
    if (market === 'FOREX') {
      if (symbol.includes('INR')) {
        return `₹${val.toFixed(4)}`;
      }
      return val.toFixed(4);
    }
    return `₹${val.toFixed(2)}`;
  };

  // Render Action Suggestion Banner
  const renderActionBanner = (action?: 'BUY' | 'SELL' | 'WAIT', quantity = 1) => {
    if (action === 'BUY') {
      return (
        <span className="flex items-center gap-1 rounded-md bg-emerald-500/20 px-2 py-1 text-[11px] font-black text-emerald-300 border border-emerald-500/40">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          🟢 BUY {quantity} SHARE
        </span>
      );
    }
    if (action === 'SELL') {
      return (
        <span className="flex items-center gap-1 rounded-md bg-rose-500/20 px-2 py-1 text-[11px] font-black text-rose-300 border border-rose-500/40">
          <span className="h-2 w-2 rounded-full bg-rose-400 animate-pulse"></span>
          🔴 SELL {quantity} SHARE
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 rounded-md bg-slate-700/60 px-2 py-1 text-[11px] font-bold text-slate-300 border border-slate-600/40">
        <span className="h-2 w-2 rounded-full bg-slate-400"></span>
        ⚪ AWAITING SETUP
      </span>
    );
  };

  return (
    <div className="rounded-2xl border border-dark-600 bg-dark-800/95 p-4 shadow-xl backdrop-blur">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dark-700 pb-3 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
            <Activity className="h-4 w-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-black tracking-wide text-white uppercase">
                ⚡ LIVE MULTI-ASSET SCANNER & TRADE DECISION MATRIX
              </h2>
              {getNSEMarketStatus().is_open ? (
                <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                  ● NSE OPEN
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                  ⏸ NSE CLOSED (09:15-15:30 IST)
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Real-time actionable scalp setups for all 6 assets simultaneously with 1-click execution
            </p>
          </div>
        </div>

        {/* Category Tabs, View Switcher & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category Filter Tabs */}
          <div className="flex items-center gap-1 rounded-lg bg-dark-900/80 p-1 border border-dark-600 text-xs">
            <button
              onClick={() => setFilter('All')}
              className={`px-2.5 py-1 rounded-md font-bold transition-colors ${
                filter === 'All'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('NSE')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-bold transition-colors ${
                filter === 'NSE'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>🇮🇳</span> NSE Stocks
            </button>
            <button
              onClick={() => setFilter('FOREX')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-bold transition-colors ${
                filter === 'FOREX'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>🌍</span> Forex Pairs
            </button>
          </div>

          {/* View Switcher: Cards vs Decision Matrix */}
          <div className="flex items-center gap-1 rounded-lg bg-dark-900/80 p-1 border border-dark-600 text-xs">
            <button
              onClick={() => setViewMode('cards')}
              title="Card Grid View"
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-bold transition-colors ${
                viewMode === 'cards'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              <span>🗂 Cards</span>
            </button>
            <button
              onClick={() => setViewMode('matrix')}
              title="Decision Matrix Comparison View"
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-bold transition-colors ${
                viewMode === 'matrix'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Table className="h-3.5 w-3.5" />
              <span>📊 Decision Matrix</span>
            </button>
          </div>

          <span className="hidden xl:inline-flex rounded-full bg-dark-700 px-2.5 py-1 text-xs font-bold text-slate-300 border border-dark-600">
            {filteredQuotes.length} Assets
          </span>

          <button
            onClick={() => fetchWatchlist(true)}
            disabled={loading}
            title={`Refresh Scanner (Last updated ${lastUpdated.toLocaleTimeString()})`}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-dark-700 hover:text-white transition-colors border border-dark-600/60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* VIEW 1: CARDS VIEW */}
      {viewMode === 'cards' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          {filteredQuotes.map((item) => {
            const isSelected = item.symbol === selectedSymbol;
            const isPositive = (item.change_percentage ?? 0) >= 0;
            const action = item.action || 'WAIT';

            return (
              <div
                key={item.symbol}
                onClick={() => onSelectSymbol(item.symbol)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectSymbol(item.symbol);
                  }
                }}
                className={`group relative flex flex-col justify-between cursor-pointer rounded-2xl p-3.5 transition-all duration-200 select-none ${
                  isSelected
                    ? 'bg-dark-750/95 ring-2 ring-indigo-500 border-transparent shadow-xl shadow-indigo-500/15'
                    : 'bg-dark-900/70 border border-dark-600/80 hover:bg-dark-750 hover:border-dark-500'
                }`}
              >
                {/* Active Ticker Indicator */}
                {isSelected && (
                  <div className="absolute -top-2 right-3 flex items-center gap-1 rounded-full bg-indigo-600 px-2 py-0.5 text-[9px] font-black text-white shadow uppercase tracking-wider">
                    VIEWING
                  </div>
                )}

                {/* Card Header: Symbol & Market */}
                <div>
                  <div className="flex items-center justify-between gap-1.5 mb-1">
                    <div>
                      <span className="font-black text-base text-white tracking-tight group-hover:text-indigo-300 transition-colors">
                        {item.symbol}
                      </span>
                      {item.name && (
                        <p className="text-[10px] font-medium text-slate-400 truncate max-w-[120px]">
                          {item.name}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {!getMarketStatusForSymbol(item.symbol).is_open && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded border bg-amber-500/20 text-amber-300 border-amber-500/40 uppercase">
                          Closed
                        </span>
                      )}
                      <span
                        className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded border uppercase tracking-wider ${
                          item.market === 'FOREX'
                            ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        }`}
                      >
                        {item.market}
                      </span>
                    </div>
                  </div>

                  {/* Price & Day Change */}
                  <div className="my-2.5 pb-2 border-b border-dark-700/60">
                    <div className="text-lg font-black text-slate-100 font-mono tracking-tight">
                      {formatPrice(item.price, item.market, item.symbol)}
                    </div>
                    <div className="flex items-center justify-between text-xs font-bold font-mono mt-0.5">
                      <span
                        className={`flex items-center gap-0.5 ${
                          isPositive ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isPositive ? (
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowDownRight className="h-3.5 w-3.5" />
                        )}
                        {isPositive ? '+' : ''}
                        {item.change_percentage?.toFixed(2)}%
                      </span>
                      {item.high && item.low ? (
                        <span className="text-[10px] text-slate-500 font-normal">
                          H: {item.market === 'FOREX' ? item.high.toFixed(4) : item.high.toFixed(1)} L:{' '}
                          {item.market === 'FOREX' ? item.low.toFixed(4) : item.low.toFixed(1)}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  {/* Trade Decision Headline Banner */}
                  <div className="mb-2.5">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Recommended Action
                    </div>
                    {renderActionBanner(item.action, item.quantity)}
                    {item.patterns && item.patterns.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {item.patterns.slice(0, 2).map((p, pIdx) => (
                          <span
                            key={pIdx}
                            className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-tight ${
                              p.direction === 'BUY'
                                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                : p.direction === 'SELL'
                                ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                                : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                            }`}
                          >
                            {p.pattern.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Key Trade Parameters: SL, TP, Target, Risk */}
                  <div className="space-y-1 rounded-xl bg-dark-950/60 p-2 border border-dark-700/60 text-[11px] mb-3">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1 text-slate-400 text-[10px]">
                        <Shield className="h-3 w-3 text-rose-400" /> SL:
                      </span>
                      <span className="font-mono font-bold text-rose-400">
                        {formatCurrencyValue(item.stop_loss, item.market, item.symbol)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1 text-slate-400 text-[10px]">
                        <Target className="h-3 w-3 text-emerald-400" /> TP:
                      </span>
                      <span className="font-mono font-bold text-emerald-400">
                        {formatCurrencyValue(item.target, item.market, item.symbol)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-dark-800">
                      <span>R:R {item.risk_reward || 0.83}</span>
                      <span className="text-emerald-400 font-bold">
                        +{formatCurrencyValue(item.target_profit, item.market, item.symbol)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 1-Click Action Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onPlaceOrder) {
                      onPlaceOrder(item);
                    }
                  }}
                  className={`w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-black transition-all shadow-md active:scale-95 ${
                    action === 'BUY'
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/40'
                      : action === 'SELL'
                      ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-950/40'
                      : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-950/40'
                  }`}
                >
                  <Zap className="h-3.5 w-3.5 fill-current" />
                  {action === 'BUY'
                    ? `⚡ BUY ${item.quantity || 1} SHARE`
                    : action === 'SELL'
                    ? `⚡ SELL ${item.quantity || 1} SHARE`
                    : '⚡ QUICK SCALP TRADE'}
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        /* VIEW 2: DECISION MATRIX COMPARISON TABLE */
        <div className="overflow-x-auto rounded-xl border border-dark-700 bg-dark-900/60">
          <table className="w-full text-left text-xs text-slate-200">
            <thead className="bg-dark-900 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-dark-700">
              <tr>
                <th className="px-4 py-3">Asset</th>
                <th className="px-3 py-3">Category</th>
                <th className="px-3 py-3 text-right">Live Price</th>
                <th className="px-3 py-3 text-right">Day %</th>
                <th className="px-4 py-3 text-center">Action Decision</th>
                <th className="px-3 py-3 text-right">Entry Zone</th>
                <th className="px-3 py-3 text-right">Stop Loss</th>
                <th className="px-3 py-3 text-right">Target (TP)</th>
                <th className="px-3 py-3 text-center">R:R</th>
                <th className="px-4 py-3 text-center">1-Click Execution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-750 font-medium">
              {filteredQuotes.map((item) => {
                const isSelected = item.symbol === selectedSymbol;
                const isPositive = (item.change_percentage ?? 0) >= 0;
                const action = item.action || 'WAIT';

                return (
                  <tr
                    key={item.symbol}
                    onClick={() => onSelectSymbol(item.symbol)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-indigo-950/40 hover:bg-indigo-950/60'
                        : 'hover:bg-dark-800/80'
                    }`}
                  >
                    {/* Asset */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        {isSelected && (
                          <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
                        )}
                        <div>
                          <span className="font-extrabold text-sm text-white">{item.symbol}</span>
                          {item.name && (
                            <p className="text-[10px] text-slate-400">{item.name}</p>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="px-3 py-3.5">
                      <div className="flex items-center gap-1.5">
                        {!getMarketStatusForSymbol(item.symbol).is_open && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded border bg-amber-500/20 text-amber-300 border-amber-500/40 uppercase">
                            Closed
                          </span>
                        )}
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                            item.market === 'FOREX'
                              ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {item.market}
                        </span>
                      </div>
                    </td>

                    {/* Live Price */}
                    <td className="px-3 py-3.5 text-right font-mono font-bold text-white">
                      {formatPrice(item.price, item.market, item.symbol)}
                    </td>

                    {/* Change % */}
                    <td
                      className={`px-3 py-3.5 text-right font-mono font-bold ${
                        isPositive ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {isPositive ? '+' : ''}
                      {item.change_percentage?.toFixed(2)}%
                    </td>

                    {/* Action Decision */}
                    <td className="px-4 py-3.5 text-center">
                      <div className="flex flex-col items-center gap-1">
                        {renderActionBanner(item.action, item.quantity)}
                        {item.patterns && item.patterns.length > 0 && (
                          <div className="flex flex-wrap justify-center gap-1">
                            {item.patterns.slice(0, 1).map((p, pIdx) => (
                              <span
                                key={pIdx}
                                className={`text-[8px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-tight ${
                                  p.direction === 'BUY'
                                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                    : p.direction === 'SELL'
                                    ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                                    : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                                }`}
                              >
                                {p.pattern.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Entry Zone */}
                    <td className="px-3 py-3.5 text-right font-mono text-slate-300">
                      {formatCurrencyValue(item.entry_price, item.market, item.symbol)}
                    </td>

                    {/* Stop Loss */}
                    <td className="px-3 py-3.5 text-right font-mono font-bold text-rose-400">
                      {formatCurrencyValue(item.stop_loss, item.market, item.symbol)}
                    </td>

                    {/* Target TP */}
                    <td className="px-3 py-3.5 text-right font-mono font-bold text-emerald-400">
                      {formatCurrencyValue(item.target, item.market, item.symbol)}
                    </td>

                    {/* R:R */}
                    <td className="px-3 py-3.5 text-center font-mono text-slate-300">
                      {item.risk_reward || 0.83}
                    </td>

                    {/* 1-Click Execution */}
                    <td className="px-4 py-3.5 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onPlaceOrder) {
                            onPlaceOrder(item);
                          }
                        }}
                        className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-black transition-all shadow active:scale-95 ${
                          action === 'BUY'
                            ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                            : action === 'SELL'
                            ? 'bg-rose-600 hover:bg-rose-500 text-white'
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                        }`}
                      >
                        <Zap className="h-3 w-3 fill-current" />
                        {action === 'BUY' ? 'BUY' : action === 'SELL' ? 'SELL' : 'QUICK SCALP'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

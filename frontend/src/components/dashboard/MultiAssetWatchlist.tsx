import React, { useState, useEffect, useCallback } from 'react';
import { WatchlistQuote } from '../../types';
import { api } from '../../services/api';
import { TrendingUp, TrendingDown, Minus, RefreshCw, Activity } from 'lucide-react';

interface Props {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

type FilterCategory = 'All' | 'NSE' | 'FOREX';

const DEFAULT_SYMBOLS = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'USDINR', 'EURUSD'];

const FALLBACK_QUOTES: WatchlistQuote[] = [
  { symbol: 'RELIANCE', name: 'Reliance Ind.', market: 'NSE', price: 2985.50, change: 36.85, change_percentage: 1.25, signal: 'BUY' },
  { symbol: 'TCS', name: 'Tata Consultancy', market: 'NSE', price: 4210.00, change: 18.90, change_percentage: 0.45, signal: 'HOLD' },
  { symbol: 'INFY', name: 'Infosys Ltd', market: 'NSE', price: 1890.30, change: -15.20, change_percentage: -0.80, signal: 'SELL' },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', market: 'NSE', price: 1645.20, change: 9.80, change_percentage: 0.60, signal: 'BUY' },
  { symbol: 'USDINR', name: 'USD / INR Spot', market: 'FOREX', price: 83.5250, change: 0.0410, change_percentage: 0.05, signal: 'HOLD' },
  { symbol: 'EURUSD', name: 'EUR / USD Spot', market: 'FOREX', price: 1.0845, change: -0.0016, change_percentage: -0.15, signal: 'SELL' },
];

export const MultiAssetWatchlist: React.FC<Props> = ({ selectedSymbol, onSelectSymbol }) => {
  const [quotes, setQuotes] = useState<WatchlistQuote[]>(FALLBACK_QUOTES);
  const [filter, setFilter] = useState<FilterCategory>('All');
  const [loading, setLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchWatchlist = useCallback(async (isManual = false) => {
    if (isManual) setLoading(true);
    try {
      const data = await api.getWatchlist(DEFAULT_SYMBOLS.join(','));
      if (Array.isArray(data) && data.length > 0) {
        setQuotes(data);
        setLastUpdated(new Date());
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

  const getSignalBadge = (signal?: 'BUY' | 'SELL' | 'HOLD') => {
    const s = signal?.toUpperCase() || 'HOLD';
    if (s === 'BUY') {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-extrabold text-emerald-300 border border-emerald-500/30">
          <TrendingUp className="h-3 w-3" /> BUY
        </span>
      );
    }
    if (s === 'SELL') {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-[10px] font-extrabold text-rose-300 border border-rose-500/30">
          <TrendingDown className="h-3 w-3" /> SELL
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded bg-slate-700/60 px-2 py-0.5 text-[10px] font-bold text-slate-300 border border-slate-600/40">
        <Minus className="h-3 w-3" /> HOLD
      </span>
    );
  };

  return (
    <div className="rounded-2xl border border-dark-600 bg-dark-800/90 p-4 shadow-xl backdrop-blur">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dark-700 pb-3 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/20 border border-indigo-500/30 text-indigo-400">
            <Activity className="h-4 w-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-extrabold tracking-wide text-white uppercase">
                ⚡ LIVE MULTI-ASSET SCANNER
              </h2>
              <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                5s Live Poll
              </span>
            </div>
          </div>
        </div>

        {/* Category Tabs & Status */}
        <div className="flex items-center gap-2">
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

          <span className="hidden sm:inline-flex rounded-full bg-dark-700 px-2.5 py-1 text-xs font-bold text-slate-300 border border-dark-600">
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

      {/* Grid of Multi-Asset Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {filteredQuotes.map((item) => {
          const isSelected = item.symbol === selectedSymbol;
          const isPositive = (item.change_percentage ?? 0) >= 0;

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
              className={`group relative cursor-pointer rounded-xl p-3 transition-all duration-200 select-none ${
                isSelected
                  ? 'bg-dark-700/95 ring-2 ring-indigo-500 border-transparent shadow-lg shadow-indigo-500/20'
                  : 'bg-dark-900/60 border border-dark-600 hover:bg-dark-750 hover:border-dark-500'
              }`}
            >
              {/* Active Ticker Indicator */}
              {isSelected && (
                <div className="absolute -top-1.5 right-2 flex items-center gap-1 rounded-full bg-indigo-600 px-1.5 py-0.2 text-[9px] font-black text-white shadow uppercase tracking-wider">
                  ACTIVE
                </div>
              )}

              {/* Symbol Name & Market Badge */}
              <div className="flex items-center justify-between gap-1.5 mb-1.5">
                <span className="font-extrabold text-sm text-white tracking-tight group-hover:text-indigo-300 transition-colors">
                  {item.symbol}
                </span>
                <span
                  className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${
                    item.market === 'FOREX'
                      ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/25'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/25'
                  }`}
                >
                  {item.market}
                </span>
              </div>

              {/* Price & Change */}
              <div className="mb-2">
                <div className="text-base font-black text-slate-100 font-mono tracking-tight">
                  {formatPrice(item.price, item.market, item.symbol)}
                </div>
                <div className="flex items-center gap-1 text-xs font-bold font-mono">
                  <span className={isPositive ? 'text-emerald-400' : 'text-rose-400'}>
                    {isPositive ? '+' : ''}
                    {item.change_percentage?.toFixed(2)}%
                  </span>
                  {item.change !== undefined && (
                    <span className="text-[10px] text-slate-500">
                      ({isPositive ? '+' : ''}
                      {item.market === 'FOREX' ? item.change.toFixed(4) : item.change.toFixed(2)})
                    </span>
                  )}
                </div>
              </div>

              {/* Strategy Signal Badge */}
              <div className="flex items-center justify-between pt-1.5 border-t border-dark-700/60">
                <span className="text-[10px] text-slate-400 font-semibold uppercase">Signal</span>
                {getSignalBadge(item.signal)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

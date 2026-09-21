import React, { useState, useEffect } from 'react';
import { PositionData, TradeData } from '../../types';
import { TrendingUp, TrendingDown, Layers, Zap } from 'lucide-react';

interface Props {
  positions: PositionData[];
  trades: TradeData[];
  onClosePosition?: (id: number) => void;
  onQuickOrder?: () => void;
}

export const PositionTable: React.FC<Props> = ({ positions, trades, onClosePosition, onQuickOrder }) => {
  const [, setTick] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const getWindowStatus = (entryTime?: string | null) => {
    if (!entryTime) return { text: '⏱ 10m Max', style: 'bg-amber-500/20 text-amber-300 border-amber-500/30' };
    const elapsedSec = Math.floor((Date.now() - new Date(entryTime).getTime()) / 1000);
    const remSec = Math.max(0, 600 - elapsedSec);
    const mins = Math.floor(remSec / 60);
    const secs = remSec % 60;
    const text = `⏱ ${mins}m ${String(secs).padStart(2, '0')}s left`;
    if (remSec > 300) return { text, style: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' };
    if (remSec > 120) return { text, style: 'bg-amber-500/20 text-amber-300 border-amber-500/30' };
    return { text, style: 'bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse font-black' };
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Active Positions */}
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-4 shadow-lg">
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-trade-blue" />
            <h3 className="font-bold text-white text-sm tracking-tight">Open Virtual Positions ({positions.length})</h3>
          </div>
          <button
            onClick={() => onQuickOrder?.()}
            className="flex items-center gap-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 px-2.5 py-1 text-xs font-bold text-indigo-300 hover:text-white transition-colors shadow-sm"
            title="Place instant manual paper trade"
          >
            ⚡ Quick Paper Trade
          </button>
        </div>

        {positions.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500">No open positions in portfolio.</div>
        ) : (
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-dark-700 text-slate-400 font-semibold">
                <tr>
                  <th className="py-2">Symbol</th>
                  <th className="py-2">Side</th>
                  <th className="py-2">Qty</th>
                  <th className="py-2">Avg Price</th>
                  <th className="py-2">LTP</th>
                  <th className="py-2">Stop Loss</th>
                  <th className="py-2">Target</th>
                  <th className="py-2">Window</th>
                  <th className="py-2 text-right">Unrealized P&L</th>
                  {onClosePosition && <th className="py-2 text-right">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700/50">
                {positions.map(p => {
                  const isProfit = (p.unrealized_pnl ?? 0) >= 0;
                  const windowStatus = getWindowStatus(p.entry_time);
                  const isForex = p.symbol.includes('USD') || p.symbol.includes('EUR') || p.symbol.includes('GBP');
                  const prefix = isForex ? (p.symbol.includes('INR') ? '₹' : '') : '₹';
                  const dec = isForex ? 4 : 2;
                  return (
                    <tr key={p.id} className="hover:bg-dark-700/30">
                      <td className="py-2.5 font-bold text-white">{p.symbol}</td>
                      <td className="py-2.5">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            p.side === 'BUY'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {p.side}
                        </span>
                      </td>
                      <td className="py-2.5 font-medium">{p.quantity}</td>
                      <td className="py-2.5 text-slate-300">{prefix}{(p.average_price ?? 0).toFixed(dec)}</td>
                      <td className="py-2.5 text-white font-medium">{prefix}{(p.current_price ?? p.average_price ?? 0).toFixed(dec)}</td>
                      <td className="py-2.5">
                        {p.stop_loss !== null && p.stop_loss !== undefined && Math.abs(p.stop_loss - p.average_price) < (isForex ? 0.0005 : 0.05) ? (
                          <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-bold text-sky-300 border border-sky-500/30">
                            🛡 Breakeven ({prefix}{p.stop_loss.toFixed(dec)})
                          </span>
                        ) : (
                          <span className="text-red-400 font-semibold">
                            {p.stop_loss ? prefix + p.stop_loss.toFixed(dec) : '—'}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5">
                        <span className="text-emerald-400 font-semibold">
                          {p.target ? `${prefix}${p.target.toFixed(dec)}` : '—'}
                        </span>
                      </td>
                      <td className="py-2.5">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold border ${windowStatus.style}`}>
                          {windowStatus.text}
                        </span>
                      </td>
                      <td className={`py-2.5 text-right font-bold ${isProfit ? 'text-trade-green' : 'text-trade-red'}`}>
                        {isProfit ? '+' : ''}₹{(p.unrealized_pnl ?? 0).toFixed(2)} ({isProfit ? '+' : ''}{p.pnl_percentage ?? 0}%)
                      </td>
                      {onClosePosition && (
                        <td className="py-2.5 text-right">
                          <button
                            onClick={() => {
                              if (window.confirm(`Close position for ${p.symbol} (${p.quantity} qty)?`)) {
                                onClosePosition(p.id);
                              }
                            }}
                            className="rounded bg-red-500/20 px-2 py-0.5 text-[11px] font-bold text-red-400 hover:bg-red-500/30 hover:text-red-300 transition-colors border border-red-500/30"
                            title={`Close ${p.symbol} position`}
                          >
                            Close
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Completed Trades History */}
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-4 shadow-lg">
        <div className="flex items-center gap-2 border-b border-dark-700 pb-3">
          <TrendingUp className="h-4 w-4 text-emerald-400" />
          <h3 className="font-bold text-white text-sm tracking-tight">Recent Trade History</h3>
        </div>

        {trades.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500">No trades recorded yet.</div>
        ) : (
          <div className="overflow-x-auto mt-2 max-h-[220px]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-dark-700 text-slate-400 font-semibold sticky top-0 bg-dark-800">
                <tr>
                  <th className="py-2">Symbol</th>
                  <th className="py-2">Qty</th>
                  <th className="py-2">Entry</th>
                  <th className="py-2">Exit</th>
                  <th className="py-2 text-right">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700/50">
                {trades.slice(0, 10).map(t => {
                  const isProfit = t.pnl >= 0;
                  return (
                    <tr key={t.id} className="hover:bg-dark-700/30">
                      <td className="py-2 font-bold text-white">{t.symbol}</td>
                      <td className="py-2 font-medium">{t.quantity}</td>
                      <td className="py-2 text-slate-300">₹{t.entry_price.toFixed(2)}</td>
                      <td className="py-2 text-slate-300">₹{t.exit_price?.toFixed(2) || '—'}</td>
                      <td className={`py-2 text-right font-bold ${isProfit ? 'text-trade-green' : 'text-trade-red'}`}>
                        {isProfit ? '+' : ''}₹{t.pnl.toFixed(2)} ({isProfit ? '+' : ''}{t.pnl_percentage}%)
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

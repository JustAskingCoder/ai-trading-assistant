import React, { useState, useEffect } from 'react';
import { PositionData, TradeData, TradeAutopsyData, AdaptiveShieldData } from '../../types';
import { api } from '../../services/api';
import { TradeAutopsyModal } from './TradeAutopsyModal';
import { TrendingUp, TrendingDown, Layers, Zap, AlertTriangle, ShieldAlert } from 'lucide-react';

interface Props {
  positions: PositionData[];
  trades: TradeData[];
  onClosePosition?: (id: number) => void;
  onQuickOrder?: () => void;
}

export const PositionTable: React.FC<Props> = ({ positions, trades, onClosePosition, onQuickOrder }) => {
  const [, setTick] = useState(0);
  const [selectedAutopsy, setSelectedAutopsy] = useState<TradeAutopsyData | null>(null);
  const [activeShields, setActiveShields] = useState<AdaptiveShieldData[]>([]);

  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchShields = () => {
      api.getActiveShields()
        .then(res => setActiveShields(res.shields || []))
        .catch(() => {});
    };
    fetchShields();
    const shieldInterval = setInterval(fetchShields, 5000);
    return () => clearInterval(shieldInterval);
  }, []);

  const getWindowStatus = (entryTime?: string | null, windowMinutes: number = 30) => {
    const totalSec = Math.max(60, (windowMinutes || 30) * 60);
    if (!entryTime) return { text: `⏱ ${windowMinutes || 30}m Max`, style: 'bg-amber-500/20 text-amber-300 border-amber-500/30' };

    // Ensure ISO timestamp from backend is parsed as UTC if no timezone offset is present
    const isoUtc = entryTime.endsWith('Z') || entryTime.includes('+') ? entryTime : `${entryTime}Z`;
    const entryEpoch = new Date(isoUtc).getTime();
    if (isNaN(entryEpoch)) return { text: `⏱ ${windowMinutes || 30}m Max`, style: 'bg-amber-500/20 text-amber-300 border-amber-500/30' };

    const elapsedSec = Math.max(0, Math.floor((Date.now() - entryEpoch) / 1000));
    const remSec = Math.max(0, totalSec - elapsedSec);
    const mins = Math.floor(remSec / 60);
    const secs = remSec % 60;
    const text = `⏱ ${mins}m ${String(secs).padStart(2, '0')}s left`;
    if (remSec > totalSec * 0.5) return { text, style: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' };
    if (remSec > totalSec * 0.2) return { text, style: 'bg-amber-500/20 text-amber-300 border-amber-500/30' };
    return { text, style: 'bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse font-black' };
  };

  const hasInvalidatedPositions = positions.some(p => p.health_status === 'RELEASE_STOCK');

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

        {hasInvalidatedPositions && (
          <div className="mt-3 rounded-lg bg-rose-950/60 border border-rose-500/50 p-2.5 flex items-start gap-2.5 text-xs text-rose-200 animate-pulse">
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-bold text-rose-300">🚨 Trend Shift Invalidation Detected</div>
              <div className="text-[11px] text-rose-200/90 mt-0.5">
                Market shifted against open position(s) with opposing patterns or broken VWAP/EMA. Release stock recommended to protect capital!
              </div>
            </div>
          </div>
        )}

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
                  <th className="py-2">Health / Pattern</th>
                  <th className="py-2 text-right">Unrealized P&L</th>
                  {onClosePosition && <th className="py-2 text-right">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700/50">
                {positions.map(p => {
                  const isProfit = (p.unrealized_pnl ?? 0) >= 0;
                  const windowStatus = getWindowStatus(p.entry_time, p.window_minutes || 30);
                  const isForex = p.symbol.includes('USD') || p.symbol.includes('EUR') || p.symbol.includes('GBP');
                  const prefix = isForex ? (p.symbol.includes('INR') ? '₹' : '') : '₹';
                  const dec = isForex ? 4 : 2;
                  const isRelease = p.health_status === 'RELEASE_STOCK';
                  const isWarning = p.health_status === 'WARNING';
                  return (
                    <tr key={p.id} className={`hover:bg-dark-700/30 ${isRelease ? 'bg-rose-950/20' : ''}`}>
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
                        {p.stop_loss !== null && p.stop_loss !== undefined && (
                          p.side === 'BUY' ? p.stop_loss >= p.average_price * 1.007 : p.stop_loss <= p.average_price * 0.993
                        ) ? (
                          <span className="rounded bg-teal-500/20 px-1.5 py-0.5 text-[10px] font-bold text-teal-300 border border-teal-500/30" title="Tier 3 Trailing: +0.8% Runner Profit Locked!">
                            🚀 Lock +0.8% ({prefix}{p.stop_loss.toFixed(dec)})
                          </span>
                        ) : p.stop_loss !== null && p.stop_loss !== undefined && (
                          p.side === 'BUY' ? p.stop_loss > p.average_price + (isForex ? 0.0005 : 0.05) : p.stop_loss < p.average_price - (isForex ? 0.0005 : 0.05)
                        ) ? (
                          <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-500/30" title="Tier 2 Trailing: +0.4% Profit Locked In!">
                            🔒 Lock +0.4% ({prefix}{p.stop_loss.toFixed(dec)})
                          </span>
                        ) : p.stop_loss !== null && p.stop_loss !== undefined && Math.abs(p.stop_loss - p.average_price) <= (isForex ? 0.0005 : 0.05) ? (
                          <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-bold text-sky-300 border border-sky-500/30" title="Tier 1 Trailing: Risk-Free (Stop-Loss at Breakeven)">
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
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold border ${windowStatus.style}`}
                          title={p.window_minutes && p.window_minutes > 30 ? `Profitable position: Holding window extended from 30m base to ${p.window_minutes}m with breakeven locked to let profits expand.` : `Active trade holding window.`}
                        >
                          {windowStatus.text}
                        </span>
                      </td>
                      <td className="py-2.5">
                        {isRelease && (p.invalidation_confidence === undefined || p.invalidation_confidence >= 0.80) ? (
                          <span
                            className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] font-black text-rose-300 border border-rose-500/40 animate-pulse"
                            title={p.invalidation_reason || 'Opposing pattern or trend shift detected with >= 80% confidence'}
                          >
                            🚨 RELEASE ({p.invalidation_confidence ? Math.round(p.invalidation_confidence * 100) : 80}%)
                          </span>
                        ) : isWarning ? (
                          <span
                            className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30"
                            title={p.invalidation_reason || 'Trend momentum weakening (< 80% confidence)'}
                          >
                            ⚠️ Weakening ({p.invalidation_confidence ? Math.round(p.invalidation_confidence * 100) : 65}%)
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300 border border-emerald-500/30"
                            title="Pattern & trend intact"
                          >
                            ✓ Intact
                          </span>
                        )}
                      </td>
                      <td className={`py-2.5 text-right font-bold ${isProfit ? 'text-trade-green' : 'text-trade-red'}`}>
                        {isProfit ? '+' : ''}₹{(p.unrealized_pnl ?? 0).toFixed(2)} ({isProfit ? '+' : ''}{p.pnl_percentage ?? 0}%)
                      </td>
                      {onClosePosition && (
                        <td className="py-2.5 text-right">
                          {isRelease && (p.invalidation_confidence === undefined || p.invalidation_confidence >= 0.80) ? (
                            <button
                              onClick={() => {
                                if (window.confirm(`🚨 80%+ CONFIDENT TREND SHIFT DETECTED!\n\nReason: ${p.invalidation_reason || 'Pattern invalidation / opposing momentum'}\nConfidence: ${p.invalidation_confidence ? Math.round(p.invalidation_confidence * 100) : 80}%\n\nRelease ${p.symbol} (${p.quantity} qty) now to protect capital?`)) {
                                  onClosePosition(p.id);
                                }
                              }}
                              className="rounded bg-rose-600 hover:bg-rose-500 px-2 py-0.5 text-[11px] font-black text-white hover:text-rose-100 shadow-md shadow-rose-950/50 border border-rose-400 animate-pulse transition-transform active:scale-95"
                              title={`🚨 RELEASE STOCK: ${p.invalidation_reason || '>= 80% confident trend shift'}`}
                            >
                              🚨 Release ({p.invalidation_confidence ? Math.round(p.invalidation_confidence * 100) : 80}%)
                            </button>
                          ) : (
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
                          )}
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
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <h3 className="font-bold text-white text-sm tracking-tight">Recent Trade History</h3>
          </div>
          {activeShields.length > 0 && (
            <span className="inline-flex items-center gap-1 rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-500/30">
              🛡️ {activeShields.length} Shield{activeShields.length > 1 ? 's' : ''} Active
            </span>
          )}
        </div>

        {activeShields.length > 0 && (
          <div className="mt-3 mb-1 rounded-lg bg-indigo-950/40 border border-indigo-500/40 p-2.5 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-indigo-400 shrink-0" />
              <div>
                <span className="font-bold text-indigo-200">Adaptive Shield Cooldown:</span>{' '}
                <span className="text-slate-300 text-[11px]">
                  {activeShields.map(s => `${s.symbol} (${s.remaining_minutes}m: ${s.failure_tag})`).join(', ')}
                </span>
              </div>
            </div>
            <button
              onClick={async () => {
                await api.clearActiveShields();
                setActiveShields([]);
              }}
              className="ml-2 rounded px-2 py-0.5 text-[10px] font-bold bg-indigo-500/20 hover:bg-indigo-500/40 text-indigo-300 border border-indigo-500/30 transition-colors whitespace-nowrap"
              title="Manually clear active cooldown shields"
            >
              Clear
            </button>
          </div>
        )}

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
                  <th className="py-2 text-right">Autopsy</th>
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
                      <td className="py-2 text-right">
                        {!isProfit ? (
                          <button
                            onClick={() => {
                              if (t.autopsy) {
                                setSelectedAutopsy(t.autopsy);
                              } else {
                                api.getTradeAutopsy(t.id).then(setSelectedAutopsy).catch(() => {});
                              }
                            }}
                            className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold border transition-colors shadow-sm ${
                              t.autopsy?.severity === 'CRITICAL'
                                ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 hover:bg-rose-500/40'
                                : 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/40'
                            }`}
                            title={t.autopsy?.root_cause || "Click to inspect trade forensic autopsy"}
                          >
                            🔬 {t.autopsy?.failure_tag || 'AUTOPSY'}
                          </button>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
                            ✓ Profit Target
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade Forensic Autopsy Modal */}
      <TradeAutopsyModal
        autopsy={selectedAutopsy}
        onClose={() => setSelectedAutopsy(null)}
      />
    </div>
  );
};

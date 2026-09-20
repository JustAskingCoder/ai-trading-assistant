import React from 'react';
import { PositionData, TradeData } from '../../types';
import { TrendingUp, TrendingDown, Layers } from 'lucide-react';

interface Props {
  positions: PositionData[];
  trades: TradeData[];
  onClosePosition?: (id: number) => void;
}

export const PositionTable: React.FC<Props> = ({ positions, trades, onClosePosition }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Active Positions */}
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-4 shadow-lg">
        <div className="flex items-center gap-2 border-b border-dark-700 pb-3">
          <Layers className="h-4 w-4 text-trade-blue" />
          <h3 className="font-bold text-white text-sm tracking-tight">Open Virtual Positions ({positions.length})</h3>
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
                  <th className="py-2 text-right">Unrealized P&L</th>
                  {onClosePosition && <th className="py-2 text-right">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700/50">
                {positions.map(p => {
                  const isProfit = p.unrealized_pnl >= 0;
                  return (
                    <tr key={p.id} className="hover:bg-dark-700/30">
                      <td className="py-2.5 font-bold text-white">{p.symbol}</td>
                      <td className="py-2.5">
                        <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400">
                          {p.side}
                        </span>
                      </td>
                      <td className="py-2.5 font-medium">{p.quantity}</td>
                      <td className="py-2.5 text-slate-300">₹{p.average_price.toFixed(2)}</td>
                      <td className="py-2.5 text-white font-medium">₹{p.current_price.toFixed(2)}</td>
                      <td className={`py-2.5 text-right font-bold ${isProfit ? 'text-trade-green' : 'text-trade-red'}`}>
                        {isProfit ? '+' : ''}₹{p.unrealized_pnl.toFixed(2)} ({isProfit ? '+' : ''}{p.pnl_percentage}%)
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

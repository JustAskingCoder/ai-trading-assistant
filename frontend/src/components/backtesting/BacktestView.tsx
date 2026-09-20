import React, { useState } from 'react';
import { api } from '../../services/api';
import { Play, TrendingUp, TrendingDown, Percent, DollarSign, ShieldAlert } from 'lucide-react';

interface Props {
  symbol: string;
}

export const BacktestView: React.FC<Props> = ({ symbol }) => {
  const [strategy, setStrategy] = useState('MomentumStrategy');
  const [capital, setCapital] = useState(100000);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.runBacktest({
        symbol,
        strategy,
        initial_capital: capital,
        risk_percentage: 0.005
      });
      setResult(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Backtest failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dark-700 pb-3">
        <div>
          <h3 className="font-bold text-white text-base tracking-tight">Quantitative Strategy Backtester</h3>
          <p className="text-xs text-slate-400">Strictly prevents look-ahead bias across historical simulation candles</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={strategy}
            onChange={e => setStrategy(e.target.value)}
            className="rounded-lg border border-dark-600 bg-dark-700 px-3 py-1.5 text-xs text-white"
          >
            <option value="MomentumStrategy">Momentum Strategy (EMA+MACD+RSI)</option>
            <option value="BreakoutStrategy">Breakout Strategy (Resistance+Vol+ADX)</option>
            <option value="TrendFollowingStrategy">Trend Following (VWAP+EMA+ADX)</option>
          </select>
          <button
            onClick={handleRun}
            disabled={running}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-50 shadow-sm"
          >
            <Play className="h-3.5 w-3.5 fill-current" /> {running ? 'Simulating...' : 'Run Backtest'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="rounded-lg bg-dark-900/60 p-3">
              <span className="text-[11px] text-slate-400">Total Trades</span>
              <div className="text-lg font-bold text-white mt-0.5">{result.total_trades}</div>
              <div className="text-[10px] text-slate-500">
                {result.winning_trades}W / {result.losing_trades}L
              </div>
            </div>

            <div className="rounded-lg bg-dark-900/60 p-3">
              <span className="text-[11px] text-slate-400">Win Rate</span>
              <div className="text-lg font-bold text-emerald-400 mt-0.5">{result.win_rate}%</div>
            </div>

            <div className="rounded-lg bg-dark-900/60 p-3">
              <span className="text-[11px] text-slate-400">Net P&L</span>
              <div
                className={`text-lg font-bold mt-0.5 ${
                  result.net_pnl >= 0 ? 'text-trade-green' : 'text-trade-red'
                }`}
              >
                {result.net_pnl >= 0 ? '+' : ''}₹{result.net_pnl}
              </div>
              <div className="text-[10px] text-slate-500">{result.net_pnl_percentage}%</div>
            </div>

            <div className="rounded-lg bg-dark-900/60 p-3">
              <span className="text-[11px] text-slate-400">Profit Factor</span>
              <div className="text-lg font-bold text-yellow-400 mt-0.5">{result.profit_factor}</div>
            </div>

            <div className="rounded-lg bg-dark-900/60 p-3">
              <span className="text-[11px] text-slate-400">Max Drawdown</span>
              <div className="text-lg font-bold text-rose-400 mt-0.5">{result.max_drawdown}%</div>
            </div>

            <div className="rounded-lg bg-dark-900/60 p-3">
              <span className="text-[11px] text-slate-400">Final Equity</span>
              <div className="text-lg font-bold text-white mt-0.5">₹{result.final_capital}</div>
            </div>
          </div>

          {/* Trade log preview */}
          {result.trades && result.trades.length > 0 && (
            <div className="overflow-x-auto max-h-[180px] border border-dark-700/60 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-dark-700 text-slate-300 font-semibold">
                  <tr>
                    <th className="p-2">Side</th>
                    <th className="p-2">Qty</th>
                    <th className="p-2">Entry</th>
                    <th className="p-2">Exit</th>
                    <th className="p-2">Reason</th>
                    <th className="p-2 text-right">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-700/40">
                  {result.trades.slice(0, 8).map((t: any, idx: number) => (
                    <tr key={idx} className="hover:bg-dark-700/20">
                      <td className="p-2 font-bold text-emerald-400">{t.side}</td>
                      <td className="p-2">{t.quantity}</td>
                      <td className="p-2">₹{t.entry_price}</td>
                      <td className="p-2">₹{t.exit_price}</td>
                      <td className="p-2 text-slate-400 text-[11px]">{t.exit_reason}</td>
                      <td
                        className={`p-2 text-right font-bold ${
                          t.pnl >= 0 ? 'text-trade-green' : 'text-trade-red'
                        }`}
                      >
                        {t.pnl >= 0 ? '+' : ''}₹{t.pnl}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { PortfolioData } from '../../types';
import { Wallet, TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';

interface Props {
  portfolio: PortfolioData | null;
}

export const PortfolioCard: React.FC<Props> = ({ portfolio }) => {
  if (!portfolio) return null;

  const isDailyProfitable = portfolio.daily_pnl >= 0;
  const isRealizedProfitable = portfolio.realized_pnl >= 0;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-3.5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <Wallet className="h-3.5 w-3.5 text-trade-blue" /> Capital
        </div>
        <div className="mt-1 text-lg font-bold text-white tracking-tight">
          ₹{portfolio.capital.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">Virtual Initial: ₹1,00,000</div>
      </div>

      <div className="rounded-xl border border-dark-600 bg-dark-800 p-3.5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <DollarSign className="h-3.5 w-3.5 text-emerald-400" /> Available Cash
        </div>
        <div className="mt-1 text-lg font-bold text-white tracking-tight">
          ₹{portfolio.available_cash.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">
          Invested: ₹{portfolio.invested_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
      </div>

      <div className="rounded-xl border border-dark-600 bg-dark-800 p-3.5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <Activity className="h-3.5 w-3.5 text-yellow-400" /> Today's P&L
        </div>
        <div className={`mt-1 text-lg font-bold tracking-tight ${isDailyProfitable ? 'text-trade-green' : 'text-trade-red'}`}>
          {isDailyProfitable ? '+' : ''}₹{portfolio.daily_pnl.toFixed(2)}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">
          Limit: -₹{(portfolio.capital * 0.02).toFixed(0)} (2%)
        </div>
      </div>

      <div className="rounded-xl border border-dark-600 bg-dark-800 p-3.5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          {isRealizedProfitable ? (
            <TrendingUp className="h-3.5 w-3.5 text-trade-green" />
          ) : (
            <TrendingDown className="h-3.5 w-3.5 text-trade-red" />
          )}
          Realized P&L
        </div>
        <div className={`mt-1 text-lg font-bold tracking-tight ${isRealizedProfitable ? 'text-trade-green' : 'text-trade-red'}`}>
          {isRealizedProfitable ? '+' : ''}₹{portfolio.realized_pnl.toFixed(2)}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">Closed trades net</div>
      </div>

      <div className="rounded-xl border border-dark-600 bg-dark-800 p-3.5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <Activity className="h-3.5 w-3.5 text-indigo-400" /> Unrealized P&L
        </div>
        <div className={`mt-1 text-lg font-bold tracking-tight ${portfolio.unrealized_pnl >= 0 ? 'text-trade-green' : 'text-trade-red'}`}>
          {portfolio.unrealized_pnl >= 0 ? '+' : ''}₹{portfolio.unrealized_pnl.toFixed(2)}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">Live open positions</div>
      </div>

      <div className="rounded-xl border border-dark-600 bg-dark-800 p-3.5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <TrendingUp className="h-3.5 w-3.5 text-emerald-400" /> Win Rate
        </div>
        <div className="mt-1 text-lg font-bold text-white tracking-tight">
          {portfolio.win_rate}%
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">
          {portfolio.winning_trades}W / {portfolio.losing_trades}L ({portfolio.total_trades} total)
        </div>
      </div>
    </div>
  );
};

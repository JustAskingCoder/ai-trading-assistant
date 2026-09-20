import React from 'react';
import { Signal } from '../../types';
import { Sparkles, ArrowUpRight, ShieldCheck, AlertTriangle } from 'lucide-react';

interface Props {
  signal: Signal | null;
  onAnalyzeAI: (signal: Signal) => void;
  onPaperTrade: (signal: Signal) => void;
  onIgnore: () => void;
}

export const SignalCard: React.FC<Props> = ({ signal, onAnalyzeAI, onPaperTrade, onIgnore }) => {
  if (!signal) {
    return (
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 text-center text-slate-400">
        <p className="text-sm">No active signal currently detected. Monitoring live market simulation...</p>
      </div>
    );
  }

  const isBuy = signal.signal === 'BUY';

  return (
    <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 shadow-lg">
      <div className="flex items-center justify-between border-b border-dark-700 pb-3">
        <div>
          <span className="text-lg font-bold text-white tracking-tight">{signal.symbol}</span>
          <span className="ml-2.5 text-xs text-slate-400">Strategy: {signal.strategy}</span>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider ${
            isBuy ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}
        >
          {signal.signal} WATCH
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div className="rounded-lg bg-dark-900/60 p-2.5">
          <div className="text-xs text-slate-400">Entry Price</div>
          <div className="text-base font-bold text-white">₹{signal.entry_price.toFixed(2)}</div>
        </div>
        <div className="rounded-lg bg-dark-900/60 p-2.5">
          <div className="text-xs text-slate-400">Stop Loss</div>
          <div className="text-base font-bold text-rose-400">₹{signal.stop_loss.toFixed(2)}</div>
        </div>
        <div className="rounded-lg bg-dark-900/60 p-2.5">
          <div className="text-xs text-slate-400">Target</div>
          <div className="text-base font-bold text-emerald-400">₹{signal.target.toFixed(2)}</div>
        </div>
        <div className="rounded-lg bg-dark-900/60 p-2.5">
          <div className="text-xs text-slate-400">Risk : Reward</div>
          <div className="text-base font-bold text-yellow-400">{signal.risk_reward.toFixed(1)} : 1</div>
        </div>
      </div>

      <div className="mt-3 text-xs text-slate-300">
        <span className="font-semibold text-slate-400">Reason:</span> {signal.reason}
      </div>

      {signal.patterns && signal.patterns.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {signal.patterns.map((p, idx) => (
            <span
              key={idx}
              className="rounded bg-dark-700/80 px-2 py-0.5 text-[11px] font-medium text-sky-300 border border-dark-600"
            >
              ✓ {p.pattern.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2.5 pt-2">
        <button
          onClick={() => onAnalyzeAI(signal)}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-indigo-500 transition-colors shadow-sm"
        >
          <Sparkles className="h-3.5 w-3.5" /> ANALYZE WITH AI
        </button>

        <button
          onClick={() => onPaperTrade(signal)}
          className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-emerald-500 transition-colors shadow-sm"
        >
          <ArrowUpRight className="h-3.5 w-3.5" /> PAPER TRADE
        </button>

        <button
          onClick={onIgnore}
          className="rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-dark-600 transition-colors"
        >
          IGNORE
        </button>
      </div>
    </div>
  );
};

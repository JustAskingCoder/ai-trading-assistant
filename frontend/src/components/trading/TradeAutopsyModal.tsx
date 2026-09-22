import React from 'react';
import { TradeAutopsyData } from '../../types';
import { X, AlertOctagon, ShieldAlert, CheckCircle2, TrendingDown, ArrowRight, Activity, Zap } from 'lucide-react';

interface Props {
  autopsy: TradeAutopsyData | null;
  onClose: () => void;
}

export const TradeAutopsyModal: React.FC<Props> = ({ autopsy, onClose }) => {
  if (!autopsy) return null;

  const getTagDescription = (tag: string) => {
    switch (tag) {
      case 'CHASED_ENTRY':
        return { label: 'Chased Overextended Entry', icon: '🏃‍♂️', bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40' };
      case 'COUNTER_TIDE_DIVERGENCE':
        return { label: 'Counter-Tide Divergence (Macro Conflict)', icon: '🌊', bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40' };
      case 'FALSE_BREAKOUT_LOW_VOL':
        return { label: 'Low-Volume Trap / False Breakout', icon: '🪤', bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
      case 'TIGHT_STOP_SHAKEOUT':
        return { label: 'Tight Stop Noise Shakeout', icon: '⚡', bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
      case 'CHOP_ZONE_EXHAUSTION':
        return { label: 'Sideways Chop / Low Momentum Decay', icon: '⏳', bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40' };
      case 'TREND_SHIFT_REVERSAL':
        return { label: 'Intraday Trend Shift Invalidation', icon: '🔄', bg: 'bg-blue-500/20 text-blue-300 border-blue-500/40' };
      default:
        return { label: tag.replace(/_/g, ' '), icon: '🔬', bg: 'bg-purple-500/20 text-purple-300 border-purple-500/40' };
    }
  };

  const tagInfo = getTagDescription(autopsy.failure_tag);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl border border-rose-500/30 bg-dark-900 p-6 shadow-2xl shadow-rose-950/40 my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-dark-700 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white tracking-tight">Trade Forensic Autopsy</h3>
                <span className="rounded bg-dark-700 px-2 py-0.5 text-xs font-mono font-bold text-slate-300">
                  {autopsy.symbol}
                </span>
                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-black uppercase tracking-wider border ${
                    autopsy.severity === 'CRITICAL'
                      ? 'bg-rose-500/30 text-rose-300 border-rose-500/50 animate-pulse'
                      : autopsy.severity === 'MODERATE'
                      ? 'bg-amber-500/30 text-amber-300 border-amber-500/50'
                      : 'bg-blue-500/30 text-blue-300 border-blue-500/50'
                  }`}
                >
                  {autopsy.severity} SEVERITY
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Automated root-cause analysis & adaptive failure prevention audit
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-dark-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Financial Metrics Strip */}
        <div className="mt-4 grid grid-cols-4 gap-2 rounded-xl bg-dark-800/80 border border-dark-700/80 p-3 text-center">
          <div>
            <div className="text-[10px] uppercase font-semibold text-slate-400">Side / Setup</div>
            <div className={`text-xs font-bold mt-0.5 ${autopsy.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>
              {autopsy.side} Long/Short
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase font-semibold text-slate-400">Entry → Exit</div>
            <div className="text-xs font-mono font-bold text-slate-200 mt-0.5">
              ₹{autopsy.entry_price.toFixed(2)} → ₹{autopsy.exit_price.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase font-semibold text-slate-400">Stop Loss / Target</div>
            <div className="text-xs font-mono text-slate-300 mt-0.5">
              SL ₹{autopsy.stop_loss?.toFixed(2) || '—'} | T ₹{autopsy.target?.toFixed(2) || '—'}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase font-semibold text-slate-400">Realized Loss</div>
            <div className="text-xs font-mono font-bold text-rose-400 mt-0.5">
              -₹{Math.abs(autopsy.pnl).toFixed(2)} ({autopsy.pnl_percentage.toFixed(2)}%)
            </div>
          </div>
        </div>

        {/* Primary Root-Cause Diagnosis */}
        <div className="mt-4 space-y-4">
          <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertOctagon className="h-4 w-4 text-rose-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-rose-300">
                  Forensic Root Cause
                </span>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold border ${tagInfo.bg}`}>
                {tagInfo.icon} {tagInfo.label}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-slate-200 font-medium">
              {autopsy.root_cause}
            </p>

            {/* Metrics Breakdown if present */}
            {autopsy.metrics && Object.keys(autopsy.metrics).length > 0 && (
              <div className="mt-3 pt-3 border-t border-rose-500/20 flex flex-wrap gap-2 text-[11px]">
                {Object.entries(autopsy.metrics).map(([k, v]) => (
                  <span key={k} className="rounded bg-dark-800/90 border border-dark-600 px-2 py-0.5 text-slate-300 font-mono">
                    <span className="text-slate-400 font-sans">{k.replace(/_/g, ' ')}:</span> {typeof v === 'number' ? v.toFixed(2) : String(v)}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Adaptive Preventative Rule & Protection */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">
                Institutional Preventative Rule
              </span>
            </div>
            <p className="text-xs leading-relaxed text-slate-200 font-medium">
              {autopsy.preventative_rule}
            </p>
          </div>

          {/* Adaptive Failure Shield Guard Note */}
          <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3.5 flex items-start gap-3">
            <Zap className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
            <div className="text-xs text-indigo-200/90 leading-relaxed">
              <span className="font-bold text-indigo-300">Adaptive Shield Engaged:</span> The deterministic risk engine has placed a protective cooldown on <span className="font-mono font-bold text-white">{autopsy.symbol}</span> to prevent revenge trading and duplicate loss execution. Subsequent orders with this setup will be automatically vetoed until market structure resets.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-xl bg-slate-700 hover:bg-slate-600 px-5 py-2 text-xs font-bold text-white transition-colors"
          >
            Acknowledge & Close
          </button>
        </div>
      </div>
    </div>
  );
};

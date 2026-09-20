import React from 'react';
import { AIAnalysis } from '../../types';
import { Sparkles, CheckCircle, AlertOctagon, HelpCircle } from 'lucide-react';

interface Props {
  analysis: AIAnalysis | null;
  loading: boolean;
}

export const AIAnalysisCard: React.FC<Props> = ({ analysis, loading }) => {
  if (loading) {
    return (
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 shadow-lg flex flex-col items-center justify-center min-h-[220px]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent mb-3"></div>
        <p className="text-sm text-slate-300 font-medium">Running Structured AI Analysis...</p>
        <p className="text-xs text-slate-500 mt-1">Evaluating market context, indicators, and risk invalidations</p>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 shadow-lg flex flex-col items-center justify-center min-h-[220px] text-center text-slate-400">
        <Sparkles className="h-8 w-8 text-indigo-400/40 mb-2" />
        <p className="text-sm">Click "ANALYZE WITH AI" on any active signal to trigger structured LLM evaluation.</p>
      </div>
    );
  }

  const isBuy = analysis.signal === 'BUY';
  const isSell = analysis.signal === 'SELL';

  return (
    <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 shadow-lg">
      <div className="flex items-center justify-between border-b border-dark-700 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <h3 className="font-bold text-white text-base tracking-tight">{analysis.setup}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400">
            Confidence: <span className="text-indigo-300 font-bold">{(analysis.confidence * 100).toFixed(0)}%</span>
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
              isBuy
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : isSell
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
            }`}
          >
            AI {analysis.signal}
          </span>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div className="rounded bg-dark-900/60 p-2">
          <span className="text-slate-400">Entry Zone:</span>
          <div className="font-semibold text-white">
            ₹{analysis.entry_zone.min} - ₹{analysis.entry_zone.max}
          </div>
        </div>
        <div className="rounded bg-dark-900/60 p-2">
          <span className="text-slate-400">Stop Loss:</span>
          <div className="font-semibold text-rose-400">₹{analysis.stop_loss}</div>
        </div>
        <div className="rounded bg-dark-900/60 p-2">
          <span className="text-slate-400">Target:</span>
          <div className="font-semibold text-emerald-400">₹{analysis.target}</div>
        </div>
      </div>

      <div className="mt-3 space-y-2 text-xs">
        <div>
          <div className="flex items-center gap-1 font-semibold text-emerald-400 mb-1">
            <CheckCircle className="h-3.5 w-3.5" /> Supporting Factors
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1">
            {analysis.supporting_factors.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>

        <div>
          <div className="flex items-center gap-1 font-semibold text-amber-400 mb-1">
            <AlertOctagon className="h-3.5 w-3.5" /> Risk Factors
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1">
            {analysis.risk_factors.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>

        <div>
          <div className="flex items-center gap-1 font-semibold text-rose-400 mb-1">
            <AlertOctagon className="h-3.5 w-3.5" /> Invalidation Conditions
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1">
            {analysis.invalidation_conditions.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4 border-t border-dark-700/80 pt-2 text-[11px] text-slate-500 flex justify-between">
        <span>Provider: {analysis.provider || 'AI Engine'} ({analysis.model || 'Structured'})</span>
        <span>Paper Mode Only • Non-Financial Advice</span>
      </div>
    </div>
  );
};

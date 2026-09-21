import React, { useState, useEffect } from 'react';
import { AIAnalysis } from '../../types';
import { Sparkles, CheckCircle, AlertOctagon, Zap, CheckCircle2, AlertTriangle } from 'lucide-react';
import { api } from '../../services/api';

interface TradeFeedback {
  type: 'success' | 'rejected';
  message: string;
}

interface Props {
  analysis: AIAnalysis | null;
  loading: boolean;
  symbol?: string;
  onDirectOrder?: (order: {
    symbol: string;
    side: string;
    price: number;
    stop_loss: number;
    target: number;
    quantity: number;
  }) => Promise<{ success: boolean; data?: any; error?: string }>;
}

export const AIAnalysisCard: React.FC<Props> = ({
  analysis,
  loading,
  symbol = 'RELIANCE',
  onDirectOrder
}) => {
  const [executing, setExecuting] = useState(false);
  const [feedback, setFeedback] = useState<TradeFeedback | null>(null);

  useEffect(() => {
    setFeedback(null);
  }, [analysis]);

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
  const isActionable = isBuy || isSell;

  // Midpoint entry price from AI entry zone
  const entryPrice = analysis.entry_zone
    ? Number(((analysis.entry_zone.min + analysis.entry_zone.max) / 2).toFixed(2))
    : 0;

  const qty = 1;
  const totalInvestment = (qty * entryPrice).toFixed(2);
  const maxRiskRupees = (qty * Math.abs(entryPrice - analysis.stop_loss)).toFixed(2);
  const targetProfitRupees = (qty * Math.abs(analysis.target - entryPrice)).toFixed(2);

  const handleExecuteAISetup = async () => {
    if (!isActionable) return;
    setExecuting(true);
    setFeedback(null);
    try {
      let result: { success: boolean; data?: any; error?: string };
      if (onDirectOrder) {
        result = await onDirectOrder({
          symbol,
          side: analysis.signal,
          price: entryPrice,
          stop_loss: analysis.stop_loss,
          target: analysis.target,
          quantity: qty
        });
      } else {
        const res = await api.placePaperOrder({
          symbol,
          side: analysis.signal,
          price: entryPrice,
          stop_loss: analysis.stop_loss,
          target: analysis.target,
          order_type: 'MARKET'
        });
        result = { success: true, data: res };
      }

      if (result.success) {
        const filledQty = result.data?.quantity ?? qty;
        const filledPrice = Number(result.data?.price ?? entryPrice).toFixed(2);
        const sl = analysis.stop_loss.toFixed(2);
        const tgt = analysis.target.toFixed(2);
        setFeedback({
          type: 'success',
          message: `✓ Trade Successful! Filled ${filledQty} ${Number(filledQty) === 1 ? 'share' : 'shares'} @ ₹${filledPrice} (Stop Loss: ₹${sl}, Target: ₹${tgt})`
        });
      } else {
        setFeedback({
          type: 'rejected',
          message: `✗ Trade Rejected: ${result.error || 'Declined by risk engine'}`
        });
      }
    } catch (err: any) {
      const errorReason = err?.response?.data?.detail || err?.message || 'Execution error';
      setFeedback({
        type: 'rejected',
        message: `✗ Trade Rejected: ${errorReason}`
      });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className={`rounded-xl border ${isBuy ? 'border-emerald-500/30' : isSell ? 'border-rose-500/30' : 'border-dark-600'} bg-dark-800 p-5 shadow-lg flex flex-col justify-between`}>
      <div>
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <Sparkles className={`h-4 w-4 ${isBuy ? 'text-emerald-400' : isSell ? 'text-rose-400' : 'text-indigo-400'}`} />
            <h3 className={`font-bold text-base tracking-tight ${isBuy ? 'text-emerald-400' : isSell ? 'text-rose-400' : 'text-white'}`}>{analysis.setup}</h3>
            <span className="flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300 border border-amber-500/20">
              ⏱ 10m Max Window
            </span>
            <span className="rounded bg-sky-500/10 px-2 py-0.5 text-[11px] font-medium text-sky-300 border border-sky-500/20">
              🎯 10m Scalp Target
            </span>
            <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[11px] font-medium text-indigo-300 border border-indigo-500/20">
              🛡 Structural SL
            </span>
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
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  : 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
              }`}
            >
              AI {analysis.signal}
            </span>
          </div>
        </div>

        {/* Actionable AI Headline */}
        <div
          className={`mt-3 rounded-lg px-4 py-3 border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 shadow-inner ${
            isBuy
              ? 'bg-emerald-500/10 border-emerald-500/30'
              : isSell
              ? 'bg-rose-500/10 border-rose-500/30'
              : 'bg-dark-700/40 border-dark-600'
          }`}
        >
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              AI Actionable Setup
            </div>
            <div
              className={`text-lg sm:text-xl font-black tracking-tight ${
                isBuy ? 'text-emerald-400' : isSell ? 'text-rose-400' : 'text-slate-300'
              }`}
            >
              {isBuy
                ? `RECOMMENDED ACTION: BUY ${qty} SHARE (Scalp Target: +₹${targetProfitRupees} · 10m Window)`
                : isSell
                ? `RECOMMENDED ACTION: SELL ${qty} SHARE (Short Scalp: +₹${targetProfitRupees} · 10m Window)`
                : `AI RECOMMENDATION: HOLD / NEUTRAL`}
            </div>
          </div>
          <div className="text-xs font-semibold text-slate-300 sm:text-right">
            <span className="text-slate-400">Target Entry:</span> ₹{entryPrice.toFixed(2)}
          </div>
        </div>

        {/* AI Metric Grid */}
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="rounded bg-dark-900/60 p-2 border border-dark-700/60">
            <span className="text-slate-400">Entry Zone:</span>
            <div className="font-semibold text-white mt-0.5">
              ₹{analysis.entry_zone.min} - ₹{analysis.entry_zone.max}
            </div>
          </div>
          <div className="rounded bg-dark-900/60 p-2 border border-dark-700/60">
            <span className="text-slate-400">Stop Loss:</span>
            <div className="font-semibold text-rose-400 mt-0.5">₹{analysis.stop_loss} (-₹{maxRiskRupees})</div>
          </div>
          <div className="rounded bg-dark-900/60 p-2 border border-dark-700/60">
            <span className="text-slate-400">Target:</span>
            <div className="font-semibold text-emerald-400 mt-0.5">₹{analysis.target} (+₹{targetProfitRupees})</div>
          </div>
          <div className="rounded bg-dark-900/60 p-2 border border-dark-700/60">
            <span className="text-slate-400">Allocation:</span>
            <div
              className="font-semibold text-yellow-400 mt-0.5 truncate"
              title={`Invest: ₹${totalInvestment} (Risk: ₹${maxRiskRupees})`}
            >
              ₹{totalInvestment} (Risk: ₹{maxRiskRupees})
            </div>
          </div>
        </div>

        {/* Supporting, Risk & Invalidation Factors */}
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

        {/* Inline Feedback Alert */}
        {feedback && (
          <div
            className={`mt-3.5 flex items-start gap-2.5 rounded-lg p-3 text-xs font-semibold border transition-all ${
              feedback.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300'
                : 'bg-rose-950/40 border-rose-500/50 text-rose-300'
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
            ) : (
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
            )}
            <div className="flex-1 leading-relaxed">{feedback.message}</div>
            <button
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-white text-sm leading-none px-1"
              title="Dismiss"
            >
              ×
            </button>
          </div>
        )}
      </div>

      <div>
        {/* 1-click Execute AI Setup Button */}
        {isActionable && (
          <div className="mt-4 pt-3 border-t border-dark-700/80">
            <button
              onClick={handleExecuteAISetup}
              disabled={executing}
              className={`w-full flex items-center justify-center gap-2 rounded-lg py-2.5 px-4 text-xs sm:text-sm font-black text-white transition-all shadow-md ${
                isBuy
                  ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30'
                  : 'bg-rose-600 hover:bg-rose-500 shadow-rose-900/30'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <Zap className="h-4 w-4 fill-current" />
              <span>
                {executing
                  ? 'EXECUTING AI SETUP...'
                  : isBuy
                  ? `⚡ EXECUTE AI SETUP (BUY ${qty} SHARE · ₹${totalInvestment})`
                  : `⚡ EXECUTE AI SETUP (SELL ${qty} SHARE · ₹${totalInvestment})`}
              </span>
            </button>
          </div>
        )}

        <div className="mt-3 border-t border-dark-700/80 pt-2 text-[11px] text-slate-500 flex justify-between">
          <span>Provider: {analysis.provider || 'AI Engine'} ({analysis.model || 'Structured'})</span>
          <span>Paper Mode Only • Non-Financial Advice</span>
        </div>
      </div>
    </div>
  );
};

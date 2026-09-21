import React, { useState, useEffect } from 'react';
import { Signal } from '../../types';
import { Sparkles, ArrowUpRight, Zap, CheckCircle2, AlertTriangle } from 'lucide-react';
import { api } from '../../services/api';

interface TradeFeedback {
  type: 'success' | 'rejected';
  message: string;
  orderId?: number;
}

interface Props {
  signal: Signal | null;
  onAnalyzeAI: (signal: Signal) => void;
  onPaperTrade: (signal: Signal) => void;
  onIgnore: () => void;
  onDirectOrder?: (signal: Signal, qty: number) => Promise<{ success: boolean; data?: any; error?: string }>;
}

export const SignalCard: React.FC<Props> = ({
  signal,
  onAnalyzeAI,
  onPaperTrade,
  onIgnore,
  onDirectOrder
}) => {
  const [executing, setExecuting] = useState(false);
  const [feedback, setFeedback] = useState<TradeFeedback | null>(null);

  useEffect(() => {
    setFeedback(null);
  }, [signal?.symbol, signal?.timestamp, signal?.signal]);

  if (!signal) {
    return (
      <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 text-center text-slate-400">
        <p className="text-sm">No active signal currently detected. Monitoring live market simulation...</p>
      </div>
    );
  }

  const isBuy = signal.signal === 'BUY';
  const maxInvestment = 5000;
  const riskPerShare = Math.max(0.1, Math.abs(signal.entry_price - signal.stop_loss));
  const maxQtyByCost = Math.max(1, Math.floor(maxInvestment / signal.entry_price));
  const riskBudget = 150; // 1.5% of ₹10,000 account capital
  const qtyByRisk = Math.max(1, Math.floor(riskBudget / riskPerShare));
  const qty = Math.min(qtyByRisk, maxQtyByCost);
  const totalInvestment = (qty * signal.entry_price).toFixed(2);
  const maxRiskRupees = (qty * riskPerShare).toFixed(2);
  const targetProfitRupees = (qty * Math.abs(signal.target - signal.entry_price)).toFixed(2);

  const handlePlaceDirectOrder = async () => {
    setExecuting(true);
    setFeedback(null);
    try {
      let result: { success: boolean; data?: any; error?: string };
      if (onDirectOrder) {
        result = await onDirectOrder(signal, qty);
      } else {
        const res = await api.placePaperOrder({
          symbol: signal.symbol,
          side: signal.signal,
          price: signal.entry_price,
          stop_loss: signal.stop_loss,
          target: signal.target,
          order_type: 'MARKET'
        });
        result = { success: true, data: res };
      }

      if (result.success) {
        const filledQty = result.data?.quantity ?? qty;
        const filledPrice = Number(result.data?.price ?? signal.entry_price).toFixed(2);
        const sl = signal.stop_loss.toFixed(2);
        const tgt = signal.target.toFixed(2);
        setFeedback({
          type: 'success',
          message: `✓ Trade Successful! Filled ${filledQty} shares @ ₹${filledPrice} (Stop Loss: ₹${sl}, Target: ₹${tgt})`,
          orderId: result.data?.order_id
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
    <div className="rounded-xl border border-dark-600 bg-dark-800 p-5 shadow-lg flex flex-col justify-between">
      <div>
        {/* Header with symbol & actionable headline */}
        <div className="border-b border-dark-700 pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl font-black text-white tracking-tight">{signal.symbol}</span>
              <span className="rounded bg-dark-700 px-2 py-0.5 text-xs font-semibold text-slate-300 border border-dark-600">
                {signal.strategy}
              </span>
              <span className="flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300 border border-amber-500/20">
                ⏱ 10m Max Window
              </span>
            </div>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${
                isBuy
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}
            >
              CONFIDENCE {(signal.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {/* Big bold actionable headline */}
          <div
            className={`mt-3 rounded-lg px-4 py-3 border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 shadow-inner ${
              isBuy
                ? 'bg-emerald-500/10 border-emerald-500/30'
                : 'bg-rose-500/10 border-rose-500/30'
            }`}
          >
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Actionable Signal
              </div>
              <div
                className={`text-lg sm:text-xl font-black tracking-tight ${
                  isBuy ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                RECOMMENDED ACTION: {isBuy ? 'BUY' : 'SELL'} {qty} SHARES (Invest: ₹{totalInvestment} / Max ₹5k)
              </div>
            </div>
            <div className="text-xs font-semibold text-slate-300 sm:text-right">
              <span className="text-slate-400">Target Entry:</span> ₹{signal.entry_price.toFixed(2)}
            </div>
          </div>
        </div>

        {/* Clear Metric Grid */}
        <div className="mt-3.5 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-sm">
          <div className="rounded-lg bg-dark-900/70 p-2.5 border border-dark-700/60">
            <div className="text-[11px] text-slate-400 font-medium">Entry</div>
            <div className="text-sm sm:text-base font-bold text-white mt-0.5">₹{signal.entry_price.toFixed(2)}</div>
          </div>
          <div className="rounded-lg bg-dark-900/70 p-2.5 border border-dark-700/60">
            <div className="text-[11px] text-slate-400 font-medium">Stop Loss</div>
            <div className="text-xs sm:text-sm font-bold text-rose-400 mt-0.5">₹{signal.stop_loss.toFixed(2)} (-₹{maxRiskRupees})</div>
          </div>
          <div className="rounded-lg bg-dark-900/70 p-2.5 border border-dark-700/60">
            <div className="text-[11px] text-slate-400 font-medium">Target</div>
            <div className="text-xs sm:text-sm font-bold text-emerald-400 mt-0.5">₹{signal.target.toFixed(2)} (+₹{targetProfitRupees})</div>
          </div>
          <div className="rounded-lg bg-dark-900/70 p-2.5 border border-dark-700/60">
            <div className="text-[11px] text-slate-400 font-medium">Allocation</div>
            <div className="text-xs sm:text-sm font-bold text-yellow-400 mt-0.5">
              ₹{totalInvestment} (Risk: ₹{maxRiskRupees})
            </div>
          </div>
        </div>

        {/* Reason & Patterns */}
        <div className="mt-3 text-xs text-slate-300">
          <span className="font-semibold text-slate-400">Reason:</span> {signal.reason}
        </div>

        {signal.patterns && signal.patterns.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
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

        {/* Inline Feedback Alert State */}
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

      {/* Prominent Action Buttons */}
      <div className="mt-4 pt-3 border-t border-dark-700/80 flex flex-wrap items-center gap-2.5">
        <button
          onClick={handlePlaceDirectOrder}
          disabled={executing}
          className={`flex-1 min-w-[200px] flex items-center justify-center gap-2 rounded-lg py-2.5 px-4 text-xs sm:text-sm font-black text-white transition-all shadow-md ${
            isBuy
              ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30'
              : 'bg-rose-600 hover:bg-rose-500 shadow-rose-900/30'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <Zap className="h-4 w-4 fill-current" />
          <span>
            {executing
              ? 'EXECUTING ORDER...'
              : `⚡ PLACE ORDER (${isBuy ? 'BUY' : 'SELL'} ${qty} SHARES · ₹${totalInvestment})`}
          </span>
        </button>

        <button
          onClick={() => onAnalyzeAI(signal)}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2.5 text-xs font-bold text-white hover:bg-indigo-500 transition-colors shadow-sm"
        >
          <Sparkles className="h-3.5 w-3.5" /> ANALYZE WITH AI
        </button>

        <button
          onClick={() => onPaperTrade(signal)}
          title="Customize order parameters before submitting"
          className="flex items-center gap-1.5 rounded-lg border border-dark-600 bg-dark-700 px-3 py-2.5 text-xs font-semibold text-slate-300 hover:bg-dark-600 transition-colors"
        >
          <ArrowUpRight className="h-3.5 w-3.5" /> CUSTOM
        </button>

        <button
          onClick={onIgnore}
          className="rounded-lg border border-dark-600 bg-dark-700 px-3 py-2.5 text-xs font-medium text-slate-400 hover:bg-dark-600 hover:text-white transition-colors"
        >
          IGNORE
        </button>
      </div>
    </div>
  );
};

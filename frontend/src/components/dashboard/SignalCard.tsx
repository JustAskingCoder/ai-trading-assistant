import React, { useState, useEffect } from 'react';
import { Signal, TrendAnalysis } from '../../types';
import { Sparkles, ArrowUpRight, Zap, CheckCircle2, AlertTriangle, TrendingUp } from 'lucide-react';
import { api } from '../../services/api';
import { getMarketStatusForSymbol } from '../../utils/marketHours';

interface TradeFeedback {
  type: 'success' | 'rejected';
  message: string;
  orderId?: number;
}

interface Props {
  signal: Signal | null;
  symbol?: string;
  trendAnalysis?: TrendAnalysis | null;
  onQuickOrder?: () => void;
  onAnalyzeAI: (signal: Signal) => void;
  onPaperTrade: (signal: Signal) => void;
  onIgnore: () => void;
  onDirectOrder?: (signal: Signal, qty: number, windowMinutes?: number) => Promise<{ success: boolean; data?: any; error?: string }>;
}

export const SignalCard: React.FC<Props> = ({
  signal,
  symbol,
  trendAnalysis,
  onQuickOrder,
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

  const effectiveWindow = signal?.suggested_window || trendAnalysis?.suggested_window_minutes || 30;
  const windowLabel = trendAnalysis?.suggested_window_label || `${effectiveWindow}m Window`;
  const trendLabel = trendAnalysis?.trend_label || 'Consolidation / Setup';
  const mktStatus = getMarketStatusForSymbol(signal?.symbol || symbol || 'RELIANCE');

  if (!signal) {
    return (
      <div className="rounded-2xl border border-dark-600 bg-dark-800/95 p-5 shadow-xl backdrop-blur">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-slate-400"></span>
              <h3 className="text-sm font-extrabold tracking-wide text-white uppercase">
                AWAITING STRATEGY SETUP ({trendLabel.toUpperCase()})
              </h3>
              <span className="rounded bg-dark-700 px-2 py-0.5 text-[10px] font-bold text-slate-300 border border-dark-600 uppercase">
                {symbol || 'MARKET'}
              </span>
              {!mktStatus.is_open && (
                <span className="rounded bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30">
                  ⏸ MARKET CLOSED ({mktStatus.market})
                </span>
              )}
              {trendAnalysis && (
                <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-500/20">
                  {trendAnalysis.regime}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {trendAnalysis?.rationale || `Monitoring 20 EMA pullback & resistance breakout conditions for ${symbol || 'active asset'}.`}
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-400">
              <span className="rounded-full bg-dark-900/80 px-2.5 py-0.5 border border-dark-700">
                🛡 Min 1.2 R:R Protection
              </span>
              <span className="rounded-full bg-dark-900/80 px-2.5 py-0.5 border border-sky-500/30 text-sky-300 font-semibold">
                ⏱ {windowLabel}
              </span>
              {trendAnalysis?.indicators?.adx && (
                <span className="rounded-full bg-dark-900/80 px-2.5 py-0.5 border border-indigo-500/30 text-indigo-300">
                  ADX {trendAnalysis.indicators.adx.toFixed(1)} · ATR ₹{trendAnalysis.indicators.atr?.toFixed(2) || '—'}
                </span>
              )}
              <span className="rounded-full bg-dark-900/80 px-2.5 py-0.5 border border-dark-700">
                📊 1-Share Sizing
              </span>
            </div>
          </div>
          {onQuickOrder && (
            <button
              onClick={onQuickOrder}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 px-4 py-2.5 text-xs font-black text-white shadow-lg shadow-indigo-950/40 transition-all active:scale-95 shrink-0"
            >
              <Zap className="h-4 w-4 fill-current" />
              <span>⚡ PLACE QUICK TRADE ({effectiveWindow}m Window)</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  const isBuy = signal.signal === 'BUY';
  const isOutOfRange = (isBuy && signal.entry_price <= signal.stop_loss) || (!isBuy && signal.entry_price >= signal.stop_loss);
  const qty = 1;
  const totalInvestment = (qty * signal.entry_price).toFixed(2);
  const maxRiskRupees = (qty * Math.abs(signal.entry_price - signal.stop_loss)).toFixed(2);
  const targetProfitRupees = (qty * Math.abs(signal.target - signal.entry_price)).toFixed(2);

  const handlePlaceDirectOrder = async () => {
    setExecuting(true);
    setFeedback(null);
    try {
      let result: { success: boolean; data?: any; error?: string };
      if (onDirectOrder) {
        result = await onDirectOrder(signal, qty, effectiveWindow);
      } else {
        const res = await api.placePaperOrder({
          symbol: signal.symbol,
          side: signal.signal,
          price: signal.entry_price,
          stop_loss: signal.stop_loss,
          target: signal.target,
          order_type: 'MARKET',
          window_minutes: effectiveWindow
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
          message: `✓ Trade Successful! Filled ${filledQty} ${Number(filledQty) === 1 ? 'share' : 'shares'} @ ₹${filledPrice} (SL: ₹${sl}, Target: ₹${tgt} · ${effectiveWindow}m Window)`,
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
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xl font-black text-white tracking-tight">{signal.symbol}</span>
              <span className="rounded bg-dark-700 px-2 py-0.5 text-xs font-semibold text-slate-300 border border-dark-600">
                {signal.strategy}
              </span>
              <span className="flex items-center gap-1 rounded bg-sky-500/10 px-2 py-0.5 text-[11px] font-bold text-sky-300 border border-sky-500/20">
                ⏱ {effectiveWindow}m Window
              </span>
              {trendAnalysis && (
                <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[11px] font-medium text-indigo-300 border border-indigo-500/20">
                  📈 {trendAnalysis.trend_label}
                </span>
              )}
              <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[11px] font-medium text-indigo-300 border border-indigo-500/20">
                🛡 Structural SL
              </span>
              {signal.market_tide && signal.market_tide !== 'NEUTRAL' && (
                <span className={`flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-bold border ${
                  signal.market_tide === 'BULLISH'
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                }`}>
                  🌊 Tide: {signal.market_tide}
                </span>
              )}
              {signal.macro_trend && signal.macro_trend !== 'NEUTRAL' && (
                <span className="rounded bg-purple-500/10 px-2 py-0.5 text-[11px] font-bold text-purple-300 border border-purple-500/30">
                  🧭 15m: {signal.macro_trend}
                </span>
              )}
              {!mktStatus.is_open && (
                <span className="flex items-center gap-1 rounded bg-amber-500/15 px-2 py-0.5 text-[11px] font-bold text-amber-300 border border-amber-500/30">
                  ⏸ Market Closed ({mktStatus.market})
                </span>
              )}
              {isOutOfRange && (
                <span className="flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-[11px] font-bold text-rose-300 border border-rose-500/30 animate-pulse">
                  ⚠️ Signal Out of Range
                </span>
              )}
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
                {isBuy
                  ? `RECOMMENDED ACTION: BUY ${qty} SHARE (Target: +₹${targetProfitRupees} · ${effectiveWindow}m Window)`
                  : `RECOMMENDED ACTION: SELL ${qty} SHARE (Target: +₹${targetProfitRupees} · ${effectiveWindow}m Window)`}
              </div>
            </div>
            <div className="text-xs font-semibold text-slate-300 sm:text-right">
              <span className="text-slate-400">Target Entry:</span> ₹{signal.entry_price.toFixed(2)}
            </div>
          </div>

          {!mktStatus.is_open && (
            <div className="mt-2.5 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3.5 py-2 text-xs text-amber-200">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
              <span>
                <strong>Market is Closed:</strong> Regular {mktStatus.market} trading session is closed ({mktStatus.trading_hours}). Signal parameters reflect the latest closing prices.
              </span>
            </div>
          )}
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
          disabled={executing || isOutOfRange}
          className={`flex-1 min-w-[200px] flex items-center justify-center gap-2 rounded-lg py-2.5 px-4 text-xs sm:text-sm font-black text-white transition-all shadow-md ${
            isOutOfRange
              ? 'bg-slate-700 text-slate-400 border border-slate-600 cursor-not-allowed'
              : isBuy
              ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30'
              : 'bg-rose-600 hover:bg-rose-500 shadow-rose-900/30'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <Zap className="h-4 w-4 fill-current" />
          <span>
            {isOutOfRange
              ? '⚠️ SIGNAL OUT OF RANGE'
              : executing
              ? 'EXECUTING ORDER...'
              : isBuy
              ? `⚡ PLACE ORDER (BUY ${qty} SHARE · ₹${totalInvestment})`
              : `⚡ PLACE ORDER (SELL ${qty} SHARE · ₹${totalInvestment})`}
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

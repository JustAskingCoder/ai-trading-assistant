import React, { useState, useEffect } from 'react';
import { Signal } from '../../types';
import { X, ShieldAlert, Check, ShieldCheck } from 'lucide-react';

interface Props {
  isOpen: boolean;
  signal: Signal | null;
  onClose: () => void;
  onSubmit: (order: {
    symbol: string;
    side: string;
    price: number;
    stop_loss: number;
    target: number;
  }) => Promise<void>;
}

export const PaperOrderModal: React.FC<Props> = ({ isOpen, signal, onClose, onSubmit }) => {
  if (!isOpen || !signal) return null;

  const isForex = signal.symbol.includes('USD') || signal.symbol.includes('EUR') || signal.symbol.includes('GBP');
  const dec = isForex ? 4 : 2;
  const currencySymbol = isForex ? '' : '₹';

  const [side, setSide] = useState<string>(signal.signal || 'BUY');
  const [price, setPrice] = useState<number>(signal.entry_price);
  const [stopLoss, setStopLoss] = useState<number>(signal.stop_loss);
  const [target, setTarget] = useState<number>(signal.target);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (signal) {
      setSide(signal.signal || 'BUY');
      setPrice(signal.entry_price);
      setStopLoss(signal.stop_loss);
      setTarget(signal.target);
      setError(null);
    }
  }, [signal]);

  const applySlPercent = (pct: number) => {
    if (!price) return;
    const factor = pct / 100;
    const newSl = side === 'BUY'
      ? Number((price * (1 - factor)).toFixed(dec))
      : Number((price * (1 + factor)).toFixed(dec));
    setStopLoss(newSl);
  };

  const applyTgtPercent = (pct: number) => {
    if (!price) return;
    const factor = pct / 100;
    const newTgt = side === 'BUY'
      ? Number((price * (1 + factor)).toFixed(dec))
      : Number((price * (1 - factor)).toFixed(dec));
    setTarget(newTgt);
  };

  // Distance calculations
  const slDist = Math.abs(price - stopLoss);
  const slDistPct = price > 0 ? (slDist / price) * 100 : 0;
  const tgtDist = Math.abs(target - price);
  const tgtDistPct = price > 0 ? (tgtDist / price) * 100 : 0;
  const rrRatio = slDist > 0 ? tgtDist / slDist : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        symbol: signal.symbol,
        side,
        price: Number(price),
        stop_loss: Number(stopLoss),
        target: Number(target)
      });
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Order failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl border border-dark-600 bg-dark-800 p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-white">Create Virtual Paper Order</span>
            <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-400">PAPER MODE</span>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-dark-700 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-400">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-400">Symbol</label>
            <input
              type="text"
              disabled
              value={signal.symbol}
              className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-900 px-3 py-2 text-white opacity-80"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400">Order Side</label>
              <select
                value={side}
                onChange={e => {
                  const newSide = e.target.value;
                  setSide(newSide);
                  // Recalculate brackets to match side
                  if (price) {
                    const factor = 0.01;
                    const newSl = newSide === 'BUY'
                      ? Number((price * (1 - factor)).toFixed(dec))
                      : Number((price * (1 + factor)).toFixed(dec));
                    const newTgt = newSide === 'BUY'
                      ? Number((price * (1 + 0.015)).toFixed(dec))
                      : Number((price * (1 - 0.015)).toFixed(dec));
                    setStopLoss(newSl);
                    setTarget(newTgt);
                  }
                }}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-white"
              >
                <option value="BUY">BUY (Long)</option>
                <option value="SELL">SELL (Exit/Short)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400">
                Entry Price {currencySymbol ? `(${currencySymbol})` : '(Rate)'}
              </label>
              <input
                type="number"
                step="any"
                value={price}
                onChange={e => {
                  const newPrice = Number(e.target.value);
                  setPrice(newPrice);
                }}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-white font-semibold"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Stop Loss Input & Quick Presets */}
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-slate-400">
                  Stop Loss {currencySymbol ? `(${currencySymbol})` : ''}
                </label>
                <span className="text-[11px] text-rose-400 font-medium">
                  -{currencySymbol}{slDist.toFixed(dec)} ({slDistPct.toFixed(2)}%)
                </span>
              </div>
              <input
                type="number"
                step="any"
                value={stopLoss}
                onChange={e => setStopLoss(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-rose-400 font-semibold"
                required
              />
              <div className="mt-1.5 flex items-center gap-1.5">
                {[0.8, 1.0, 1.5, 2.0].map(pct => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => applySlPercent(pct)}
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold transition-colors ${
                      Math.abs(slDistPct - pct) < 0.1
                        ? 'bg-rose-500/30 text-rose-300 border border-rose-500/50'
                        : 'bg-dark-700 text-slate-400 hover:text-white hover:bg-dark-600'
                    }`}
                  >
                    {pct}%
                  </button>
                ))}
              </div>
            </div>

            {/* Target Input & Quick Presets */}
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-slate-400">
                  Target {currencySymbol ? `(${currencySymbol})` : ''}
                </label>
                <span className="text-[11px] text-emerald-400 font-medium">
                  +{currencySymbol}{tgtDist.toFixed(dec)} ({tgtDistPct.toFixed(2)}%)
                </span>
              </div>
              <input
                type="number"
                step="any"
                value={target}
                onChange={e => setTarget(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-emerald-400 font-semibold"
                required
              />
              <div className="mt-1.5 flex items-center gap-1.5">
                {[1.2, 1.5, 2.0, 3.0].map(pct => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => applyTgtPercent(pct)}
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold transition-colors ${
                      Math.abs(tgtDistPct - pct) < 0.1
                        ? 'bg-emerald-500/30 text-emerald-300 border border-emerald-500/50'
                        : 'bg-dark-700 text-slate-400 hover:text-white hover:bg-dark-600'
                    }`}
                  >
                    {pct}%
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-dark-900/60 p-3 text-xs text-slate-400 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="flex items-center gap-1 text-slate-300">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> Volatility Buffer:
              </span>
              <span className="text-emerald-400 font-medium">
                {slDistPct >= 0.8 ? 'Healthy Breathing Room (≥0.8%)' : 'Tight Stop (<0.8%)'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Risk Management:</span>
              <span className="text-emerald-400 font-medium">Automatic Position Sizing (0.5% max capital risk)</span>
            </div>
            <div className="flex justify-between">
              <span>Calculated R:R Ratio:</span>
              <span className={`font-bold ${rrRatio >= 1.2 ? 'text-emerald-400' : rrRatio >= 0.8 ? 'text-yellow-400' : 'text-rose-400'}`}>
                {rrRatio.toFixed(2)} : 1 {rrRatio >= 1.5 ? '(Optimal)' : rrRatio >= 1.0 ? '(Acceptable)' : '(Risky)'}
              </span>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-dark-600 bg-dark-700 py-2.5 text-xs font-semibold text-slate-300 hover:bg-dark-600"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-emerald-600 py-2.5 text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-50 shadow-lg shadow-emerald-950/40"
            >
              <Check className="h-4 w-4" /> {submitting ? 'Validating Risk...' : 'Submit Paper Trade'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

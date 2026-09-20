import React, { useState } from 'react';
import { Signal } from '../../types';
import { X, ShieldAlert, Check } from 'lucide-react';

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

  const [side, setSide] = useState<string>(signal.signal || 'BUY');
  const [price, setPrice] = useState<number>(signal.entry_price);
  const [stopLoss, setStopLoss] = useState<number>(signal.stop_loss);
  const [target, setTarget] = useState<number>(signal.target);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      <div className="w-full max-w-md rounded-2xl border border-dark-600 bg-dark-800 p-6 shadow-2xl">
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
                onChange={e => setSide(e.target.value)}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-white"
              >
                <option value="BUY">BUY (Long)</option>
                <option value="SELL">SELL (Exit)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400">Entry Price (₹)</label>
              <input
                type="number"
                step="0.05"
                value={price}
                onChange={e => setPrice(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-white font-semibold"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400">Stop Loss (₹)</label>
              <input
                type="number"
                step="0.05"
                value={stopLoss}
                onChange={e => setStopLoss(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-rose-400 font-semibold"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400">Target (₹)</label>
              <input
                type="number"
                step="0.05"
                value={target}
                onChange={e => setTarget(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-dark-600 bg-dark-700 px-3 py-2 text-emerald-400 font-semibold"
                required
              />
            </div>
          </div>

          <div className="rounded-lg bg-dark-900/60 p-3 text-xs text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Risk Management:</span>
              <span className="text-emerald-400 font-medium">Automatic Position Sizing (0.5% max risk)</span>
            </div>
            <div className="flex justify-between">
              <span>Calculated R:R Ratio:</span>
              <span className="text-yellow-400 font-bold">
                {price && stopLoss && target && Math.abs(price - stopLoss) > 0
                  ? (Math.abs(target - price) / Math.abs(price - stopLoss)).toFixed(2)
                  : '—'} : 1
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
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-emerald-600 py-2.5 text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              <Check className="h-4 w-4" /> {submitting ? 'Validating Risk...' : 'Submit Paper Trade'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

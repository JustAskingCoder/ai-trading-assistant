import React, { useState } from 'react';
import { X, Check, AlertCircle, Key, Zap, Shield, ExternalLink, HelpCircle, ChevronDown, ChevronUp, LogOut } from 'lucide-react';
import { ZerodhaStatus } from '../../types';
import { api } from '../../services/api';

interface Props {
  isOpen: boolean;
  status: ZerodhaStatus | null;
  onClose: () => void;
  onStatusChange: (status: ZerodhaStatus) => void;
}

export const ZerodhaConnectModal: React.FC<Props> = ({
  isOpen,
  status,
  onClose,
  onStatusChange
}) => {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState<'ENCTOKEN' | 'API_KEY'>(
    status?.mode === 'API_KEY' ? 'API_KEY' : 'ENCTOKEN'
  );
  const [enctoken, setEnctoken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(true);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const payload = activeTab === 'ENCTOKEN'
        ? { mode: 'ENCTOKEN' as const, enctoken: enctoken.trim() }
        : { mode: 'API_KEY' as const, api_key: apiKey.trim(), access_token: accessToken.trim() };

      const res = await api.connectZerodha(payload);
      if (res.status === 'connected') {
        const newStatus: ZerodhaStatus = {
          is_connected: true,
          mode: res.mode,
          user_id: res.user_id,
          user_name: res.user_name,
          broker: 'Zerodha Kite',
          data_source: 'ZERODHA'
        };
        onStatusChange(newStatus);
        onClose();
      }
    } catch (err: any) {
      console.error('Zerodha connection error:', err);
      const msg = err?.response?.data?.detail || err?.message || 'Failed to authenticate with Zerodha Kite.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect from Zerodha Kite and revert to standard market feed?')) {
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await api.disconnectZerodha();
      const newStatus: ZerodhaStatus = {
        is_connected: false,
        mode: 'DISCONNECTED',
        user_id: null,
        user_name: null,
        broker: 'Zerodha Kite',
        data_source: 'YFINANCE'
      };
      onStatusChange(newStatus);
      onClose();
    } catch (err: any) {
      console.error('Zerodha disconnect error:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to disconnect.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl border border-dark-600 bg-dark-800 p-6 shadow-2xl space-y-5 max-h-[92vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500 to-rose-500 text-white font-black text-lg shadow-md">
              🪁
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-extrabold text-white">Zerodha Kite Live Feed</h2>
                {status?.is_connected ? (
                  <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-bold text-emerald-400 border border-emerald-500/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    0-DELAY ACTIVE
                  </span>
                ) : (
                  <span className="rounded-full bg-dark-700 px-2 py-0.5 text-[11px] font-medium text-slate-400 border border-dark-600">
                    DISCONNECTED
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">Zero-latency Indian market tick data directly from Zerodha Kite</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-dark-700 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Connected State Banner */}
        {status?.is_connected ? (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-3">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-emerald-400 font-bold" />
                  <span className="text-xs font-bold text-emerald-300">Connected to Zerodha Kite Live Feed</span>
                </div>
                <p className="text-sm font-black text-white">
                  {status.user_name || 'Zerodha User'} ({status.user_id})
                </p>
                <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-300">
                  <span className="rounded bg-dark-800/80 px-2 py-0.5 border border-dark-600">
                    Mode: {status.mode === 'ENCTOKEN' ? 'Kite Web Session' : 'Official Kite API'}
                  </span>
                  <span className="rounded bg-dark-800/80 px-2 py-0.5 border border-dark-600 text-emerald-400 font-medium">
                    Latency: ~0 ms (Live Exchange)
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-emerald-500/20 flex items-center justify-between">
              <span className="text-xs text-slate-400">Want to disconnect or switch accounts?</span>
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={loading}
                className="flex items-center gap-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600 px-3 py-1.5 text-xs font-bold text-rose-300 hover:text-white border border-rose-500/30 transition-all disabled:opacity-50"
              >
                <LogOut className="h-3.5 w-3.5" />
                Disconnect
              </button>
            </div>
          </div>
        ) : null}

        {/* Error Alert */}
        {error && (
          <div className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
            <div>
              <p className="font-bold text-rose-200">Connection Failed</p>
              <p className="text-rose-300/90">{error}</p>
            </div>
          </div>
        )}

        {/* Tab Selection */}
        <div className="space-y-4">
          <div className="flex rounded-xl bg-dark-900/80 p-1 border border-dark-700">
            <button
              type="button"
              onClick={() => setActiveTab('ENCTOKEN')}
              className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold transition-all ${
                activeTab === 'ENCTOKEN'
                  ? 'bg-amber-500 text-dark-900 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Zap className="h-3.5 w-3.5" />
              <span>Kite Web Enctoken</span>
              <span className="rounded bg-black/20 px-1.5 py-0.2 text-[9px] font-black uppercase tracking-wider">
                Free
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('API_KEY')}
              className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold transition-all ${
                activeTab === 'API_KEY'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Key className="h-3.5 w-3.5" />
              <span>Official Developer API</span>
            </button>
          </div>

          {/* Form Content */}
          <form onSubmit={handleConnect} className="space-y-4">
            {activeTab === 'ENCTOKEN' ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5">
                    Zerodha Enctoken Cookie:
                  </label>
                  <textarea
                    rows={3}
                    value={enctoken}
                    onChange={(e) => setEnctoken(e.target.value)}
                    placeholder="Paste the enctoken cookie from kite.zerodha.com here..."
                    required
                    className="w-full rounded-xl border border-dark-600 bg-dark-900 px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                {/* Collapsible How-To Guide */}
                <div className="rounded-xl border border-dark-600 bg-dark-900/60 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setShowGuide(!showGuide)}
                    className="w-full flex items-center justify-between px-3.5 py-2.5 text-xs font-bold text-amber-400 hover:bg-dark-700/50 transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <HelpCircle className="h-3.5 w-3.5" />
                      <span>How to copy your Enctoken in 30 seconds (100% Free)</span>
                    </div>
                    {showGuide ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>

                  {showGuide && (
                    <div className="px-3.5 pb-3 text-xs text-slate-300 space-y-2 border-t border-dark-700/60 pt-2.5">
                      <ol className="list-decimal list-inside space-y-1.5 text-slate-300 text-[11px] leading-relaxed">
                        <li>
                          Open <a href="https://kite.zerodha.com" target="_blank" rel="noreferrer" className="text-amber-400 underline inline-flex items-center gap-0.5 font-semibold">kite.zerodha.com <ExternalLink className="h-2.5 w-2.5 inline" /></a> in your browser and log in.
                        </li>
                        <li>
                          Press <kbd className="rounded bg-dark-800 px-1.5 py-0.5 text-amber-300 font-mono font-bold border border-dark-600">F12</kbd> (or Right Click &rarr; <span className="font-semibold text-white">Inspect</span>) to open Developer Tools.
                        </li>
                        <li>
                          Click the <span className="font-semibold text-white">Application</span> tab (or <span className="font-semibold text-white">Storage</span> in Safari/Firefox).
                        </li>
                        <li>
                          In the left sidebar under <span className="font-semibold text-white">Cookies</span>, click <span className="font-mono text-amber-300 text-[10px]">https://kite.zerodha.com</span>.
                        </li>
                        <li>
                          Find the row named <span className="font-mono text-amber-300 font-bold bg-dark-800 px-1 rounded">enctoken</span>, double-click its <span className="font-semibold text-white">Value</span>, and copy it (<kbd className="rounded bg-dark-800 px-1 py-0.5 text-[10px]">Ctrl+C</kbd> / <kbd className="rounded bg-dark-800 px-1 py-0.5 text-[10px]">⌘+C</kbd>).
                        </li>
                        <li>
                          Paste the copied token into the text area above and click <span className="font-bold text-amber-400">Connect & Stream 0-Delay</span>!
                        </li>
                      </ol>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1">
                    Kite API Key:
                  </label>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="e.g. abcdef1234567890"
                    required
                    className="w-full rounded-xl border border-dark-600 bg-dark-900 px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1">
                    Kite Access Token:
                  </label>
                  <input
                    type="password"
                    value={accessToken}
                    onChange={(e) => setAccessToken(e.target.value)}
                    placeholder="Your daily session access_token"
                    required
                    className="w-full rounded-xl border border-dark-600 bg-dark-900 px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <p className="text-[11px] text-slate-400">
                  Direct official connection using Zerodha&apos;s <span className="text-indigo-400 font-mono">kiteconnect</span> Python library.
                </p>
              </div>
            )}

            {/* Safety Assurance Callout */}
            <div className="flex items-start gap-2 rounded-xl bg-dark-900/60 p-3 border border-dark-700/60 text-[11px] text-slate-400">
              <Shield className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>
                <strong className="text-slate-200">Zero Execution Risk:</strong> Trading execution is strictly locked to <span className="text-sky-400 font-bold">PAPER MODE</span> (virtual money). Your Zerodha credentials are used exclusively to stream real-time 0-delay prices for Indian equities.
              </span>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-dark-700">
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-dark-600 bg-dark-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-dark-600 hover:text-white transition-colors"
              >
                Close
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 px-4 py-2 text-xs font-extrabold text-white shadow-lg transition-all disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <span className="h-3 w-3 rounded-full border-2 border-white/20 border-t-white animate-spin"></span>
                    <span>Validating with Kite...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-3.5 w-3.5 fill-current" />
                    <span>Connect & Stream 0-Delay</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

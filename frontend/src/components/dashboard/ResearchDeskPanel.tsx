import React from 'react';
import { CommitteeDecision, CommitteeSide } from '../../types';
import {
  Sparkles, Users, TrendingUp,
  ShieldAlert, AlertTriangle, Play, Gavel, BarChart3,
  Activity, CandlestickChart as CandleIcon, Volume2, Layers,
  Newspaper, Scale, RefreshCw
} from 'lucide-react';
import { getMarketStatusForSymbol } from '../../utils/marketHours';

const ROLE_META: Array<{
  keyword: string;
  label: string;
  icon: React.ReactNode;
  accent: string;
}> = [
  { keyword: 'technical', label: 'Technical & Trend', icon: <TrendingUp className="h-3.5 w-3.5" />, accent: 'text-sky-400 bg-sky-500/10 border-sky-500/30' },
  { keyword: 'pattern', label: 'Pattern & Price-Action', icon: <CandleIcon className="h-3.5 w-3.5" />, accent: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
  { keyword: 'volume', label: 'Volume & Liquidity', icon: <Volume2 className="h-3.5 w-3.5" />, accent: 'text-amber-400 bg-amber-500/10 border-amber-500/30' },
  { keyword: 'market structure', label: 'Market Structure', icon: <Layers className="h-3.5 w-3.5" />, accent: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30' },
  { keyword: 'news', label: 'News & Sentiment', icon: <Newspaper className="h-3.5 w-3.5" />, accent: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  { keyword: 'risk', label: 'Risk & Execution', icon: <Scale className="h-3.5 w-3.5" />, accent: 'text-rose-400 bg-rose-500/10 border-rose-500/30' },
];

const SIDE_STYLE: Record<CommitteeSide, { badge: string; bar: string; text: string }> = {
  BUY: { badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', bar: 'bg-emerald-500', text: 'text-emerald-400' },
  SELL: { badge: 'bg-rose-500/20 text-rose-400 border-rose-500/40', bar: 'bg-rose-500', text: 'text-rose-400' },
  HOLD: { badge: 'bg-slate-500/20 text-slate-300 border-slate-500/40', bar: 'bg-slate-500', text: 'text-slate-300' },
};

const VERDICT_BANNER: Record<CommitteeSide, { bg: string; headline: string; sub: string }> = {
  BUY: {
    bg: 'bg-emerald-500/10 border-emerald-500/40',
    headline: 'COMMITTEE APPROVED: BUY',
    sub: 'Weighted majority has signed off the long side.',
  },
  SELL: {
    bg: 'bg-rose-500/10 border-rose-500/40',
    headline: 'COMMITTEE APPROVED: SELL',
    sub: 'Weighted majority has signed off the short side.',
  },
  HOLD: {
    bg: 'bg-amber-500/10 border-amber-500/40',
    headline: 'COMMITTEE VERDICT: HOLD',
    sub: 'No directional side reached consensus — stay flat.',
  },
};

function roleMeta(role: string) {
  const r = (role || '').toLowerCase();
  const hit = ROLE_META.find((m) => r.includes(m.keyword));
  if (hit) return hit;
  return {
    keyword: 'other',
    label: role || 'Analyst',
    icon: <Activity className="h-3.5 w-3.5" />,
    accent: 'text-slate-300 bg-dark-700 border-dark-600',
  };
}

interface Props {
  symbol: string;
  decision: CommitteeDecision | null;
  loading: boolean;
  history?: CommitteeDecision[];
  onRun: (symbol: string) => void;
}

export const ResearchDeskPanel: React.FC<Props> = ({
  symbol,
  decision,
  loading,
  history = [],
  onRun,
}) => {
  const mktStatus = getMarketStatusForSymbol(symbol);

  const sideCounts = { BUY: 0, SELL: 0, HOLD: 0 } as Record<CommitteeSide, number>;
  const total = decision?.per_analyst?.length ?? 0;
  decision?.per_analyst?.forEach((a) => {
    const side = (a.side || 'HOLD').toUpperCase() as CommitteeSide;
    if (sideCounts[side] !== undefined) sideCounts[side] += 1;
  });

  const banner = decision ? VERDICT_BANNER[decision.verdict] : null;
  const agreePct = total > 0 ? Math.round(((decision?.num_agree ?? 0) / Math.max(total, 6)) * 100) : 0;

  return (
    <div className="rounded-2xl border border-dark-600 bg-dark-800/95 p-4 md:p-5 shadow-xl backdrop-blur">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dark-700 pb-3 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 text-white shadow-md">
            <Gavel className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-black tracking-wide text-white uppercase">
                AI Research Desk — 6-Analyst Consensus Committee
              </h2>
              <span className="rounded bg-dark-700 px-2 py-0.5 text-[10px] font-bold text-violet-300 border border-violet-500/30 uppercase tracking-wider">
                {symbol}
              </span>
              {!mktStatus.is_open && (
                <span className="rounded bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30">
                  ⏸ Market Closed
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Every BUY/SELL needs 3/6 weighted-majority sign-off; Risk & Execution analyst holds a veto.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onRun(symbol)}
            disabled={loading}
            className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-black transition-all shadow-md ${
              decision?.verdict && decision.verdict !== 'HOLD'
                ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                : 'bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white shadow-violet-950/40'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {loading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 fill-current" />
            )}
            <span>{loading ? 'RUNNING COMMITTEE...' : decision ? 'RERUN COMMITTEE' : 'RUN COMMITTEE'}</span>
          </button>
          {history.length > 0 && (
            <span className="hidden sm:inline-flex rounded-full bg-dark-700 px-2.5 py-1 text-[10px] font-bold text-slate-300 border border-dark-600">
              {history.length} decision{history.length === 1 ? '' : 's'} on record
            </span>
          )}
        </div>
      </div>

      {loading && !decision ? (
        <div className="flex flex-col items-center justify-center py-8 text-slate-400">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent mb-3"></div>
          <p className="text-sm font-semibold text-slate-300">Running the 6-analyst pre-trade research desk...</p>
          <p className="text-xs text-slate-500 mt-1">Evaluating trend, price-action, volume, market structure, sentiment & risk veto</p>
        </div>
      ) : !decision ? (
        <div className="flex flex-col items-center justify-center py-8 text-center text-slate-400">
          <Sparkles className="h-8 w-8 text-violet-400/40 mb-2" />
          <p className="text-sm">No committee verdict yet for <span className="font-bold text-white">{symbol}</span>.</p>
          <p className="text-xs text-slate-500 mt-1">Run the research desk to get a 6-analyst consensus verdict with risk veto before any trade.</p>
        </div>
      ) : (
        <>
          {/* Verdict Headline */}
          <div className={`rounded-lg px-4 py-3 border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 shadow-inner ${banner?.bg}`}>
            <div>
              <div className="flex items-center gap-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Committee Verdict
                </div>
                {decision.risk_vetoed && (
                  <span className="flex items-center gap-1 rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] font-black text-rose-300 border border-rose-500/40">
                    <ShieldAlert className="h-3 w-3" /> RISK VETO
                  </span>
                )}
              </div>
              <div className={`text-xl md:text-2xl font-black tracking-tight ${SIDE_STYLE[decision.verdict].text}`}>
                {banner?.headline} — {decision.num_agree}/6 AGREE
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                {banner?.sub} Overall confidence {Math.round((decision.overall_confidence ?? 0) * 100)}%
              </div>
            </div>
            <div className="flex items-center gap-2 sm:flex-col sm:items-end text-xs font-semibold text-slate-300">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-dark-900/70 px-2.5 py-1 border border-dark-600">
                <Users className="h-3.5 w-3.5 text-violet-400" />
                {decision.num_agree} / {Math.max(total, 6)} analysts
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-dark-900/70 px-2.5 py-1 border border-dark-600">
                <BarChart3 className="h-3.5 w-3.5 text-violet-400" />
                {agreePct}% consensus
              </span>
            </div>
          </div>

          {/* Risk Veto Banner */}
          {decision.risk_vetoed && (
            <div className="mt-3 flex items-start gap-2.5 rounded-lg border border-rose-500/40 bg-rose-950/40 px-3.5 py-2.5 text-xs text-rose-200">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400 animate-pulse" />
              <div>
                <strong>Risk &amp; Execution Veto:</strong> the deterministic risk analyst vetoed the trade.
                Any directional side is downgraded to <strong>HOLD</strong> regardless of analyst majority.
              </div>
            </div>
          )}

          {/* Consensus Meter */}
          <div className="mt-3 rounded-lg bg-dark-900/70 border border-dark-700/60 p-3">
            <div className="flex items-center justify-between text-[11px] mb-1.5">
              <span className="font-black uppercase tracking-wider text-slate-400">Consensus Meter</span>
              <span className="font-mono font-bold text-slate-300">
                BUY {sideCounts.BUY} · SELL {sideCounts.SELL} · HOLD {sideCounts.HOLD}
              </span>
            </div>
            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-dark-950 border border-dark-700">
              {total > 0 ? (
                <>
                  <div
                    className="h-full bg-emerald-500 transition-all"
                    style={{ width: `${(sideCounts.BUY / Math.max(total, 6)) * 100}%` }}
                  />
                  <div
                    className="h-full bg-rose-500 transition-all"
                    style={{ width: `${(sideCounts.SELL / Math.max(total, 6)) * 100}%` }}
                  />
                  <div
                    className="h-full bg-slate-500 transition-all"
                    style={{ width: `${(sideCounts.HOLD / Math.max(total, 6)) * 100}%` }}
                  />
                </>
              ) : (
                <div className="h-full w-full bg-slate-700" />
              )}
            </div>
          </div>

          {/* Committee Reasons */}
          {decision.reasons && decision.reasons.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-[11px] font-black uppercase tracking-wider text-slate-400">Committee Reasoning</div>
              <ul className="list-disc list-inside space-y-0.5 text-xs text-slate-300 pl-1">
                {decision.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Analyst Cards */}
          <div className="mt-3.5">
            <div className="text-[11px] font-black uppercase tracking-wider text-slate-400 mb-2">
              6-Analyst Verdicts ({total})
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-2.5">
              {decision.per_analyst?.map((a, idx) => {
                const meta = roleMeta(a.role);
                const side = (a.side || 'HOLD').toUpperCase() as CommitteeSide;
                const st = SIDE_STYLE[side];
                const conf = Math.max(0, Math.min(1, Number(a.confidence) || 0));
                return (
                  <div key={idx} className="flex flex-col rounded-xl border border-dark-600 bg-dark-900/70 p-3">
                    <div className="flex items-center justify-between gap-1 mb-1.5">
                      <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-black border ${meta.accent} uppercase tracking-wider truncate`}>
                        {meta.icon}
                        <span className="truncate">{meta.label}</span>
                      </span>
                      <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-black border uppercase ${st.badge}`}>
                        {side}
                      </span>
                    </div>
                    <div className="mb-1.5">
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mb-0.5">
                        <span>Confidence</span>
                        <span className={`font-mono font-bold ${st.text}`}>{Math.round(conf * 100)}%</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-dark-950 border border-dark-700 overflow-hidden">
                        <div className={`h-full rounded-full ${st.bar}`} style={{ width: `${conf * 100}%` }} />
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-300 mb-1">
                      <span className="text-slate-500">Top factor:</span> {a.top_factor}
                    </div>
                    {a.risk_flags && a.risk_flags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-1">
                        {a.risk_flags.map((f, fi) => (
                          <span key={fi} className="rounded bg-rose-500/10 px-1.5 py-0.5 text-[8px] font-bold text-rose-300 border border-rose-500/30">
                            ⚠ {f}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="text-[10px] text-slate-400 line-clamp-3 leading-relaxed mt-auto">
                      {a.rationale}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';
import { CandleData } from '../../types';

interface ChartProps {
  data: CandleData[];
  symbol: string;
  marketMode?: 'LIVE' | 'SIMULATOR';
}

/**
 * Shifts timestamp by +5 hours 30 mins (+19800s) so TradingView Lightweight Charts
 * horizontal axis (which defaults to UTC) displays exact Indian Standard Time (IST).
 * E.g., 15:15 IST (09:45 UTC) will display as 15:15 instead of 09:45.
 */
const toIstChartTime = (rawTs: string | number): any => {
  if (!rawTs) return Math.floor(Date.now() / 1000);
  const d = new Date(rawTs);
  if (isNaN(d.getTime())) return Math.floor(Date.now() / 1000);
  return (Math.floor(d.getTime() / 1000) + 19800) as any;
};

export const CandlestickChart: React.FC<ChartProps> = ({ data, symbol, marketMode = 'SIMULATOR' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const ema20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ema50SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#111722' },
        textColor: '#94a3b8',
        fontFamily: 'Nunito Sans, system-ui, sans-serif',
      },
      localization: {
        timeFormatter: (ts: number) => {
          const date = new Date(ts * 1000);
          const hh = String(date.getUTCHours()).padStart(2, '0');
          const mm = String(date.getUTCMinutes()).padStart(2, '0');
          return `${hh}:${mm} IST`;
        },
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 480,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#334155',
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      crosshair: {
        vertLine: { color: '#64748b', width: 1, style: 2 },
        horzLine: { color: '#64748b', width: 1, style: 2 },
      }
    });

    chartRef.current = chart;

    // Candlestick Series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    candleSeriesRef.current = candleSeries;

    // Volume Histogram
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '', // Overlay on separate sub-scale
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });
    volumeSeriesRef.current = volumeSeries;

    // EMA 20 (Cyan)
    const ema20 = chart.addLineSeries({
      color: '#38bdf8',
      lineWidth: 2,
      title: 'EMA 20',
    });
    ema20SeriesRef.current = ema20;

    // EMA 50 (Purple)
    const ema50 = chart.addLineSeries({
      color: '#a855f7',
      lineWidth: 2,
      title: 'EMA 50',
    });
    ema50SeriesRef.current = ema50;

    // VWAP (Yellow)
    const vwap = chart.addLineSeries({
      color: '#facc15',
      lineWidth: 1,
      lineStyle: 2,
      title: 'VWAP',
    });
    vwapSeriesRef.current = vwap;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update chart data whenever data changes
  useEffect(() => {
    if (!candleSeriesRef.current || !data || data.length === 0) return;

    try {
      const formattedCandles = data.map(d => ({
        time: toIstChartTime(d.timestamp),
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }));

      const formattedVolume = data.map(d => ({
        time: toIstChartTime(d.timestamp),
        value: d.volume,
        color: d.close >= d.open ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)',
      }));

      const formattedEma20 = data
        .filter(d => d.ema20 !== null && d.ema20 !== undefined)
        .map(d => ({
          time: toIstChartTime(d.timestamp),
          value: d.ema20 as number,
        }));

      const formattedEma50 = data
        .filter(d => d.ema50 !== null && d.ema50 !== undefined)
        .map(d => ({
          time: toIstChartTime(d.timestamp),
          value: d.ema50 as number,
        }));

      const formattedVwap = data
        .filter(d => d.vwap !== null && d.vwap !== undefined)
        .map(d => ({
          time: toIstChartTime(d.timestamp),
          value: d.vwap as number,
        }));

      candleSeriesRef.current.setData(formattedCandles);
      if (volumeSeriesRef.current) volumeSeriesRef.current.setData(formattedVolume);
      if (ema20SeriesRef.current) ema20SeriesRef.current.setData(formattedEma20);
      if (ema50SeriesRef.current) ema50SeriesRef.current.setData(formattedEma50);
      if (vwapSeriesRef.current) vwapSeriesRef.current.setData(formattedVwap);

      chartRef.current?.timeScale().fitContent();
    } catch (e) {
      console.error('Error updating chart series:', e);
    }
  }, [data]);

  return (
    <div className="relative rounded-xl border border-dark-600 bg-dark-800 p-4 shadow-xl">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-dark-700 pb-3">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight text-white">{symbol}</span>
          <span className="rounded bg-dark-700 px-2 py-0.5 text-xs font-semibold text-slate-300">5m</span>
          <span className="rounded bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 text-[11px] font-bold text-indigo-300">
            🇮🇳 IST (UTC+5:30)
          </span>
          {marketMode === 'LIVE' ? (
            <span className="flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-bold text-rose-400 border border-rose-500/20">
              <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
              ● LIVE REAL-TIME FEED
            </span>
          ) : (
            <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Simulated Feed
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 font-medium text-sky-400">
            <span className="h-2 w-2 rounded-full bg-sky-400"></span> EMA 20
          </span>
          <span className="flex items-center gap-1.5 font-medium text-purple-400">
            <span className="h-2 w-2 rounded-full bg-purple-400"></span> EMA 50
          </span>
          <span className="flex items-center gap-1.5 font-medium text-yellow-400">
            <span className="h-2 w-2 rounded-full bg-yellow-400"></span> VWAP
          </span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
};

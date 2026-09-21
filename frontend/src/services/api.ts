import axios from 'axios';
import { CandleData, PortfolioData, PositionData, TradeData, AIAnalysis, RiskStatus, Signal } from '../types';

const client = axios.create({
  baseURL: '/api'
});

export const api = {
  getHealth: () => client.get('/health').then(r => r.data),
  getCandles: (symbol: string, interval = '5m', limit = 200): Promise<CandleData[]> =>
    client.get(`/market/${symbol}/candles`, { params: { interval, limit } }).then(r => r.data),
  getOverview: (symbol: string) =>
    client.get(`/market/${symbol}`).then(r => r.data),
  getPortfolio: (): Promise<PortfolioData> =>
    client.get('/portfolio').then(r => r.data),
  resetPortfolio: () => client.post('/portfolio/reset').then(r => r.data),
  getPositions: (): Promise<PositionData[]> =>
    client.get('/positions').then(r => r.data),
  closePosition: (id: number) => client.post(`/positions/${id}/close`).then(r => r.data),
  getTrades: (): Promise<TradeData[]> =>
    client.get('/trades').then(r => r.data),
  getRiskStatus: (): Promise<RiskStatus> =>
    client.get('/risk').then(r => r.data),
  toggleKillSwitch: (active: boolean) =>
    client.post('/risk/kill-switch', null, { params: { active } }).then(r => r.data),
  placePaperOrder: (order: {
    symbol: string;
    side: string;
    price: number;
    stop_loss: number;
    target: number;
    order_type?: string;
    quantity?: number;
  }) => client.post('/paper/orders', order).then(r => r.data),
  analyzeWithAI: (data: any, provider?: string): Promise<AIAnalysis> =>
    client.post('/ai/analyze', data, { params: { provider } }).then(r => r.data),
  runBacktest: (params: { symbol: string; strategy: string; initial_capital?: number; risk_percentage?: number }) =>
    client.post('/backtest', params).then(r => r.data),
  controlSimulator: (action: 'start' | 'pause' | 'stop' | 'reset', speed = 1.0) =>
    client.post('/simulator/control', null, { params: { action, speed } }).then(r => r.data),
  getSimulatorStatus: () =>
    client.get('/simulator/status').then(r => r.data),
  uploadCsv: (formData: FormData) =>
    client.post('/data/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data),
  getSettings: () => client.get('/settings').then(r => r.data),
  updateSettings: (settings: any) => client.put('/settings', settings).then(r => r.data)
};

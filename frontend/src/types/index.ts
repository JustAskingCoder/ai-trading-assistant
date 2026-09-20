export interface CandleData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema20?: number | null;
  ema50?: number | null;
  vwap?: number | null;
  rsi?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_hist?: number | null;
  adx?: number | null;
}

export interface Pattern {
  pattern: string;
  direction: 'BUY' | 'SELL' | 'NEUTRAL';
  strength: number;
  timestamp: string;
  evidence: string[];
}

export interface Signal {
  symbol: string;
  timestamp: string;
  strategy: string;
  signal: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  entry_price: number;
  stop_loss: number;
  target: number;
  risk_reward: number;
  reason: string;
  patterns?: Pattern[];
  indicators?: Record<string, any>;
}

export interface PortfolioData {
  capital: number;
  available_cash: number;
  invested_amount: number;
  realized_pnl: number;
  unrealized_pnl: number;
  daily_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  open_positions: number;
}

export interface PositionData {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  average_price: number;
  current_price: number;
  stop_loss?: number | null;
  target?: number | null;
  unrealized_pnl: number;
  pnl_percentage: number;
}

export interface TradeData {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  stop_loss?: number;
  target?: number;
  pnl: number;
  pnl_percentage: number;
  entry_time: string;
  exit_time: string;
  strategy: string;
}

export interface AIAnalysis {
  signal: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  setup: string;
  entry_zone: {
    min: number;
    max: number;
  };
  stop_loss: number;
  target: number;
  risk_reward: number;
  timeframe: string;
  supporting_factors: string[];
  risk_factors: string[];
  invalidation_conditions: string[];
  provider?: string;
  model?: string;
}

export interface RiskStatus {
  kill_switch_active: boolean;
  daily_loss_limit: number;
  daily_loss_current: number;
  daily_risk_remaining: number;
  open_positions: number;
  max_open_positions: number;
  risk_per_trade_percent: number;
  recent_events: Array<{
    id: number;
    timestamp: string;
    event_type: string;
    description: string;
    severity: string;
  }>;
}

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
  suggested_window?: number;
  market_tide?: string;
  macro_trend?: string;
  is_market_open?: boolean;
  market_status?: 'OPEN' | 'CLOSED';
  market_status_message?: string;
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
  entry_time?: string | null;
  window_minutes?: number;
  health_status?: 'HEALTHY' | 'WARNING' | 'RELEASE_STOCK';
  trend_shift?: boolean;
  recommendation?: string;
  invalidation_reason?: string | null;
  invalidation_confidence?: number | null;
  opposing_patterns?: string[];
}

export interface TradeAutopsyData {
  id: number;
  trade_id?: number;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  stop_loss?: number | null;
  target?: number | null;
  pnl: number;
  pnl_percentage: number;
  failure_tag: string;
  root_cause: string;
  preventative_rule: string;
  severity: 'LOW' | 'MODERATE' | 'CRITICAL';
  metrics?: Record<string, any> | null;
  created_at?: string;
}

export interface AdaptiveShieldData {
  symbol: string;
  failure_tag: string;
  root_cause: string;
  preventative_rule: string;
  severity: string;
  engaged_at: string;
  expires_at: string;
  remaining_minutes: number;
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
  autopsy?: TradeAutopsyData | null;
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

export interface CPRData {
  pivot: number;
  tc: number;
  bc: number;
  lower_boundary?: number;
  upper_boundary?: number;
  width_pct: number;
  cpr_type: 'NARROW' | 'WIDE' | 'AVERAGE';
  price_location: 'ABOVE_CPR' | 'BELOW_CPR' | 'INSIDE_CPR' | 'UNKNOWN';
  label?: string | null;
  is_narrow: boolean;
}

export interface OHLData {
  signal: 'OPEN_LOW' | 'OPEN_HIGH' | 'NONE';
  diff_pct: number;
  label?: string | null;
  is_ohl: boolean;
  bias?: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  description?: string;
}

export interface VolumeSurgeData {
  is_surge: boolean;
  ratio: number;
  current_volume?: number;
  avg_volume?: number;
  surge_type?: 'BULLISH_SURGE' | 'BEARISH_SURGE' | 'NORMAL';
  label?: string | null;
}

export interface DayBreakoutData {
  is_breakout: boolean;
  is_breakdown: boolean;
  label?: string | null;
  day_high?: number;
  day_low?: number;
}

export interface WatchlistQuote {
  symbol: string;
  name?: string;
  market: 'NSE' | 'FOREX' | 'CRYPTO';
  price: number;
  change?: number;
  change_percentage: number;
  high?: number;
  low?: number;
  volume?: number;
  signal?: 'BUY' | 'SELL' | 'HOLD';
  indicators?: Record<string, any>;
  action?: 'BUY' | 'SELL' | 'WAIT';
  quantity?: number;
  entry_price?: number;
  stop_loss?: number;
  target?: number;
  risk_reward?: number;
  target_profit?: number;
  max_risk?: number;
  reason?: string;
  strategy?: string;
  confidence?: number;
  suggested_window?: number;
  patterns?: Pattern[];
  is_market_open?: boolean;
  market_status?: 'OPEN' | 'CLOSED';
  market_status_message?: string;
  cpr?: CPRData;
  ohl?: OHLData;
  volume_surge?: VolumeSurgeData;
  day_breakout?: DayBreakoutData;
  scanner_tags?: string[];
  confluence_score?: number;
  confluence_badge?: string | null;
  confluence_grade?: string;
}

export interface ScannerSummary {
  high_confluence: WatchlistQuote[];
  open_low: WatchlistQuote[];
  open_high: WatchlistQuote[];
  volume_surge: WatchlistQuote[];
  narrow_cpr: WatchlistQuote[];
  day_breakouts: WatchlistQuote[];
  all: WatchlistQuote[];
  counts: {
    high_confluence: number;
    open_low: number;
    open_high: number;
    volume_surge: number;
    narrow_cpr: number;
    day_breakouts: number;
    total: number;
  };
  timestamp: string;
}

export interface MarketTradingStatus {
  market: 'NSE' | 'FOREX' | 'CRYPTO';
  is_open: boolean;
  status: 'OPEN' | 'CLOSED';
  current_time_ist: string;
  trading_hours: string;
  message: string;
  reason?: string;
  next_open?: string | null;
}

export interface TrendAnalysis {
  symbol: string;
  name: string;
  price: number;
  trend: string;
  trend_label: string;
  regime: string;
  indicators: {
    adx?: number | null;
    rsi?: number | null;
    atr?: number | null;
    atr_pct?: number | null;
    ema20?: number | null;
    ema50?: number | null;
    vwap?: number | null;
  };
  day_range: {
    high: number;
    low: number;
    open: number;
  };
  velocity: {
    candles_for_1pct: number;
    est_minutes_for_target: number;
  };
  suggested_window_minutes: number;
  suggested_window_label: string;
  rationale: string;
}

export interface ZerodhaStatus {
  is_connected: boolean;
  mode: 'ENCTOKEN' | 'API_KEY' | 'DISCONNECTED';
  user_id?: string | null;
  user_name?: string | null;
  broker: string;
  data_source: 'ZERODHA' | 'YFINANCE';
}

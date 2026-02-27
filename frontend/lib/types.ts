// 전략 관련 타입
export interface EntryCondition {
  indicator: string;
  operator: string;
  value: number;
  unit: string;
  description: string;
}

export interface Entry {
  conditions: EntryCondition[];
  logic: "AND" | "OR";
}

export interface PartialExit {
  enabled: boolean;
  at_percent: number;
  sell_ratio: number;
}

export interface TakeProfit {
  type: string;
  value: number;
  partial?: PartialExit;
}

export interface StopLoss {
  type: string;
  value: number;
}

export interface Exit {
  take_profit: TakeProfit;
  stop_loss: StopLoss;
}

export interface Position {
  size_type: string;
  size_value: number;
  max_positions: number;
}

export interface Filters {
  min_liquidity_usd: number;
  min_market_cap_usd: number;
  exclude_tokens: string[];
  token_whitelist: string[];
}

export interface ParsedStrategy {
  name: string;
  version: number;
  entry: Entry;
  exit: Exit;
  position: Position;
  filters: Filters;
  timeframe: string;
  target_pair: string;
}

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  raw_input: string;
  input_type: "text" | "image" | "paste";
  parsed_strategy: ParsedStrategy;
  status: "draft" | "tested" | "verified";
  created_at: string;
  updated_at: string;
}

// 백테스트 타입
export interface BacktestMetrics {
  total_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_trades: number;
  init_cash?: number;
}

export interface EquityPoint {
  date: string | number;
  value: number;
}

export interface TradeRecord {
  entry_date: string;
  exit_date: string;
  pnl: number;
  return_pct: number;
}

export interface ActualPeriod {
  start: string;
  end: string;
  candles: number;
}

export interface BacktestResult {
  id: string;
  strategy_id: string;
  metrics: BacktestMetrics;
  equity_curve: EquityPoint[];
  trade_log: TradeRecord[];
  ai_summary?: string;
  actual_period?: ActualPeriod;
}

export interface BacktestHistoryItem {
  id: string;
  timestamp: Date;
  strategy: ParsedStrategy;
  result: BacktestResult;
  startDate: string;
  endDate: string;
}

// 채팅 타입
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  imageUrl?: string;
  metadata?: {
    type?: "strategy_parsed" | "strategy_updated" | "backtest_result" | "coaching" | "general";
    parsed_strategy?: ParsedStrategy;
    backtest_result?: BacktestResult;
  };
  created_at: string;
}

// API 응답 타입
export interface ChatResponse {
  type: "strategy_parsed" | "strategy_updated" | "coaching" | "general";
  message: string;
  parsed_strategy?: ParsedStrategy;
  backtest_result?: BacktestResult;
}

// 사용자 타입
export interface User {
  id: string;
  wallet_address: string;
  display_name?: string;
  tier: "free" | "pro";
  created_at: string;
}

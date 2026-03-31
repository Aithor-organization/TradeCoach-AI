const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("tc_token") : null;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

// 모의투자 타입
export interface DemoStartParams {
  symbol?: string;
  leverage?: number;
  initial_balance?: number;
  parsed_strategy?: Record<string, unknown>;
  strategy_nft_id?: string;  // Phase 5: 신호 기록용 NFT ID
}

export interface DemoSession {
  session_id: string;
  symbol: string;
  leverage: number;
  initial_balance: number;
  status: string;
}

export interface DemoTrade {
  side: string;
  signal_type?: string;  // "BUY_LONG" | "SELL_SHORT" | "SELL_LONG" | "BUY_SHORT"
  entry_price: number;
  exit_price: number;
  quantity?: number;
  leverage?: number;
  pnl: number;
  pnl_pct?: number;
  fee?: number;
  exit_reason: string;
  entry_at?: string;
  exit_at?: string;
}

export interface DemoStatus {
  session_id: string;
  balance: number;
  current_balance: number;
  unrealized_pnl: number;
  last_signal?: string;
  position: {
    side: string;
    entry_price: number;
    quantity: number;
    leverage: number;
    sl_price?: number;
    tp_price?: number;
    liquidation_price?: number;
  } | null;
}

// API 함수
export async function startDemo(params: DemoStartParams = {}) {
  return fetcher<DemoSession>("/trading/demo/start", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export interface SignalRecording {
  signals_recorded: number;
  flushed: number;
  merkle_root?: string;
  network: string;
  tx_signature?: string;
  explorer_url?: string;
  trade_hash?: string;
}

export async function stopDemo(sessionId: string, recordMode: "test" | "verify" = "test") {
  return fetcher<{ session_id: string; status: string; final_balance: number; trades: DemoTrade[]; signal_recording?: SignalRecording; record_mode: string }>(
    "/trading/demo/stop",
    {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, record_mode: recordMode }),
    },
  );
}

export async function getDemoStatus(sessionId: string, currentPrice?: number) {
  const params = new URLSearchParams({ session_id: sessionId });
  if (currentPrice) params.set("current_price", String(currentPrice));
  return fetcher<DemoStatus>(`/trading/demo/status?${params}`);
}

export async function getDemoHistory(sessionId: string) {
  return fetcher<{ session_id: string; trades: DemoTrade[] }>(
    `/trading/demo/history?session_id=${sessionId}`,
  );
}

// Phase 5: 블록체인 신호 히스토리 조회
export interface OnchainSignal {
  signal_hash: string;
  leaf_index: number;
  strategy_nft_id: string;
  signal_type: string;
  symbol: string;
  price: number;
  leverage: number;
  timestamp: number;
}

export async function getSignalHistory(strategyId: string, limit = 100) {
  return fetcher<OnchainSignal[]>(
    `/blockchain/signal/history/${strategyId}?limit=${limit}`,
  );
}

export async function getSignalBufferStatus() {
  return fetcher<{ buffer_count: number; batch_size: number; ready_to_flush: boolean; network: string }>(
    "/blockchain/signal/buffer/status",
  );
}

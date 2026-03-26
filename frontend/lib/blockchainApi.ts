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

// 전략 cNFT 민팅 준비 (메타데이터 생성)
export async function prepareMintStrategy(strategyId: string, parsedStrategy: Record<string, unknown>) {
  return fetcher<{
    strategy_hash: string;
    metadata: Record<string, unknown>;
    network: string;
    ready_to_sign: boolean;
  }>("/blockchain/strategy/mint", {
    method: "POST",
    body: JSON.stringify({ strategy_id: strategyId, parsed_strategy: parsedStrategy }),
  });
}

// 전략 무결성 검증
export async function verifyStrategy(strategyId: string) {
  return fetcher<{
    verified: boolean;
    db_hash: string;
    onchain_hash: string | null;
    match: boolean;
    network: string;
  }>(`/blockchain/strategy/${strategyId}/verify`);
}

// 지갑 잔고 조회
export async function getWalletBalance(address: string) {
  return fetcher<{ address: string; balance_sol: number }>(`/blockchain/balance/${address}`);
}

// devnet 에어드랍
export async function requestAirdrop(address: string, amount = 2) {
  return fetcher<{ address: string; amount_sol: number; tx_signature: string }>(
    `/blockchain/airdrop/${address}`,
    { method: "POST" },
  );
}

// 공개 전략 목록 (마켓플레이스)
export interface PublicStrategy {
  id: string;
  name: string;
  parsed_strategy: Record<string, unknown>;
  created_at: string;
  onchain: { asset_id: string; strategy_hash: string } | null;
}

export async function getPublicStrategies() {
  return fetcher<{ strategies: PublicStrategy[] }>("/strategy/public");
}

// 신호 버퍼 상태
export async function getSignalBufferStatus() {
  return fetcher<{ buffer_count: number; batch_size: number; ready_to_flush: boolean }>(
    "/blockchain/signal/buffer/status",
  );
}

// ─── 마켓플레이스 API (Phase 3+) ───

export interface PlatformInfo {
  initialized: boolean;
  pda?: string;
  authority?: string;
  strategy_count?: number;
  fee_bps?: number;
  is_paused?: boolean;
}

export async function getPlatformInfo() {
  return fetcher<PlatformInfo>("/blockchain/platform/info");
}

export interface StrategyPerformance {
  strategy_id: string;
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  sessions: number;
  period_days?: number;
  tx_signatures?: string[];
  verified: boolean;
}

export async function getStrategyPerformance(strategyId: string) {
  return fetcher<StrategyPerformance & { message?: string }>(
    `/blockchain/strategy/${strategyId}/performance`,
  );
}

export interface TradeHistoryResponse {
  strategy_id: string;
  trades: Array<{
    symbol?: string;
    side?: string;
    pnl?: number;
    exit_reason?: string;
    timestamp?: number;
  }>;
}

export async function getStrategyTradeHistory(strategyId: string, limit = 50) {
  return fetcher<TradeHistoryResponse>(
    `/blockchain/strategy/${strategyId}/trade-history?limit=${limit}`,
  );
}

export async function registerStrategyOnchain(
  strategyId: string,
  strategyName: string,
  strategyData: Record<string, unknown>,
) {
  return fetcher<{
    tx_signature: string;
    strategy_hash?: string;
    strategy_pda?: string;
    explorer_url: string;
    network: string;
    tier?: number;
    error?: string;
  }>("/blockchain/strategy/register-onchain", {
    method: "POST",
    body: JSON.stringify({
      strategy_id: strategyId,
      strategy_name: strategyName,
      strategy_data: strategyData,
    }),
  });
}

// 온체인 TX 히스토리 조회 (서버 재시작 후에도 유지)
export interface OnchainTxRecord {
  tx_signature: string;
  block_time: number | null;
  slot: number;
  explorer_url: string;
}

export async function getStrategyTxHistory(strategyId: string, limit = 20) {
  return fetcher<{
    strategy_id: string;
    transactions: OnchainTxRecord[];
    count: number;
    source: string;
  }>(`/blockchain/strategy/${strategyId}/tx-history?limit=${limit}`);
}

// Phase 4: 성과 검증
export async function updatePerformanceOnchain(
  strategyPda: string,
  tradePnlScaled: number,
  holdingSeconds = 0,
  isLive = false,
) {
  return fetcher<{ tx_signature: string; performance_pda: string; explorer_url: string }>(
    "/blockchain/performance/update",
    {
      method: "POST",
      body: JSON.stringify({
        strategy_pda: strategyPda,
        trade_pnl_scaled: tradePnlScaled,
        holding_seconds: holdingSeconds,
        is_live: isLive,
      }),
    },
  );
}

export async function verifyTrackRecord(strategyPda: string) {
  return fetcher<{ tx_signature: string; explorer_url: string; verified: boolean }>(
    `/blockchain/performance/verify/${strategyPda}`,
    { method: "POST" },
  );
}

// Phase 5-3: 구매/대여
export async function purchaseStrategy(
  strategyPda: string,
  strategyOwner: string,
  buyerPubkey?: string,
) {
  return fetcher<{
    tx_signature: string;
    license_pda: string;
    license_type: string;
    explorer_url: string;
  }>("/blockchain/marketplace/purchase", {
    method: "POST",
    body: JSON.stringify({
      strategy_pda: strategyPda,
      strategy_owner: strategyOwner,
      buyer_pubkey: buyerPubkey,
    }),
  });
}

export async function rentStrategy(
  strategyPda: string,
  days: number,
  renterPubkey?: string,
) {
  return fetcher<{
    tx_signature: string;
    license_pda: string;
    escrow_pda: string;
    license_type: string;
    days: number;
    explorer_url: string;
  }>("/blockchain/marketplace/rent", {
    method: "POST",
    body: JSON.stringify({
      strategy_pda: strategyPda,
      days,
      renter_pubkey: renterPubkey,
    }),
  });
}

export async function verifyMerkleProof(
  signalData: Record<string, unknown>,
  proof: string[],
  root: string,
  leafIndex: number,
) {
  return fetcher<{ verified: boolean; leaf_hash: string; root: string }>(
    "/blockchain/merkle/verify",
    {
      method: "POST",
      body: JSON.stringify({
        signal_data: signalData,
        proof,
        root,
        leaf_index: leafIndex,
      }),
    },
  );
}

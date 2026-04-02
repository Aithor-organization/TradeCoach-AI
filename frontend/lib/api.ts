const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined"
    ? localStorage.getItem("tc_token")
    : null;

  console.log(`[API] ${options?.method || "GET"} ${path} | token: ${token ? "있음" : "없음"}`);

  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // FormData일 때는 Content-Type 설정하지 않음 (브라우저가 자동 설정)
  if (!(options?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (e) {
    console.error(`[API] ${path} 네트워크 에러:`, e);
    throw e;
  }

  console.log(`[API] ${path} → ${res.status}`);

  if (!res.ok) {
    // 401: 토큰 만료 → 자동 로그아웃
    if (res.status === 401 && typeof window !== "undefined") {
      console.warn(`[API] 401 — 토큰 만료, 자동 로그아웃`);
      localStorage.removeItem("tc_token");
      const { useAuthStore } = await import("@/stores/authStore");
      useAuthStore.getState().logout();
    }
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    console.error(`[API] ${path} 에러:`, error);
    throw new Error(error.detail || "API Error");
  }

  return res.json();
}

// 채팅 API
export async function sendMessage(content: string, strategyId?: string, history?: Array<{ role: string; content: string; metadata?: Record<string, unknown> }>, language?: string) {
  const formData = new FormData();
  formData.append("content", content);
  if (strategyId) formData.append("strategy_id", strategyId);
  if (history && history.length > 0) formData.append("history", JSON.stringify(history));
  if (language) formData.append("language", language);

  return fetcher("/chat/message", {
    method: "POST",
    body: formData,
  });
}

export async function sendMessageWithImage(content: string, image: File, strategyId?: string, history?: Array<{ role: string; content: string; metadata?: Record<string, unknown> }>, language?: string) {
  const formData = new FormData();
  formData.append("content", content);
  formData.append("image", image);
  if (strategyId) formData.append("strategy_id", strategyId);
  if (history && history.length > 0) formData.append("history", JSON.stringify(history));
  if (language) formData.append("language", language);

  return fetcher("/chat/message/image", {
    method: "POST",
    body: formData,
  });
}

export async function sendMessageStream(
  content: string,
  strategyId?: string,
  history?: Array<{ role: string; content: string }>,
  onChunk?: (chunk: string) => void,
  onDone?: (data: { type: string; full_text: string; parsed_strategy?: Record<string, unknown> }) => void,
  language?: string,
) {
  const token = typeof window !== "undefined" ? localStorage.getItem("tc_token") : null;
  const formData = new FormData();
  formData.append("content", content);
  if (strategyId) formData.append("strategy_id", strategyId);
  if (history && history.length > 0) formData.append("history", JSON.stringify(history));
  if (language) formData.append("language", language);

  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}/chat/message/stream`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API Error");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr) continue;

      try {
        const data = JSON.parse(jsonStr);
        if (data.done) {
          onDone?.(data);
        } else if (data.chunk) {
          onChunk?.(data.chunk);
        }
      } catch {
        // JSON 파싱 실패 무시
      }
    }
  }
}

export async function getChatHistory(strategyId: string) {
  return fetcher(`/chat/history/${strategyId}`);
}

// 전략 API
export async function parseStrategy(rawInput: string) {
  return fetcher("/strategy/parse", {
    method: "POST",
    body: JSON.stringify({ raw_input: rawInput }),
  });
}

export async function saveStrategy(name: string, parsedStrategy: Record<string, unknown>, rawInput = "") {
  return fetcher("/strategy/save", {
    method: "POST",
    body: JSON.stringify({
      name,
      raw_input: rawInput,
      input_type: "text",
      parsed_strategy: parsedStrategy,
    }),
  });
}

export async function getStrategies() {
  return fetcher("/strategy/list");
}

export async function getStrategy(id: string) {
  return fetcher(`/strategy/${id}`);
}

export async function updateStrategy(id: string, updates: Record<string, unknown>) {
  return fetcher(`/strategy/${id}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

// 전략 버전 관리
export interface StrategyVersion {
  id: string;
  version: number;
  label: string;
  mint_tx: string | null;
  mint_hash: string | null;
  mint_network: string;
  created_at: string;
}

export async function getStrategyVersions(strategyId: string) {
  return fetcher<{ versions: StrategyVersion[] }>(`/strategy/${strategyId}/versions`);
}

export async function restoreStrategyVersion(strategyId: string, versionId: string) {
  return fetcher<{ restored: boolean; version: number; label: string }>(
    `/strategy/${strategyId}/restore/${versionId}`,
    { method: "POST" },
  );
}

export async function publishToMarketplace(strategyId: string) {
  return fetcher<{
    strategy_id: string;
    is_public: boolean;
    message: string;
    blockchain?: { tx_signature?: string; explorer_url?: string; error?: string };
  }>(
    `/strategy/${strategyId}/publish`,
    { method: "POST" },
  );
}

export async function unpublishFromMarketplace(strategyId: string) {
  return fetcher<{ strategy_id: string; is_public: boolean; message: string }>(
    `/strategy/${strategyId}/unpublish`,
    { method: "POST" },
  );
}

export async function forkStrategy(id: string, name?: string) {
  return fetcher<{ id: string; name: string; parsed_strategy: Record<string, unknown> }>(`/strategy/fork/${id}`, {
    method: "POST",
    body: JSON.stringify(name ? { name } : {}),
  });
}

// 백테스트 API
export async function runBacktest(
  strategyId: string,
  tokenPair = "SOL/USDC",
  timeframe = "1h",
  parsedStrategy?: Record<string, unknown>,
  startDate?: string,
  endDate?: string,
  language?: string,
) {
  return fetcher("/backtest/run", {
    method: "POST",
    body: JSON.stringify({
      strategy_id: strategyId,
      token_pair: tokenPair,
      timeframe,
      ...(parsedStrategy ? { parsed_strategy: parsedStrategy } : {}),
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
      ...(language ? { language } : {}),
      // 선물 자동 감지: leverage > 1 또는 market_type이 futures이면
      market_type: parsedStrategy?.market_type === "futures" ||
        (parsedStrategy?.leverage && Number(parsedStrategy.leverage) > 1)
          ? "futures" : "spot",
    }),
  });
}

export async function getBacktestResult(id: string) {
  return fetcher(`/backtest/result/${id}`);
}

export async function getBacktestHistory(strategyId: string) {
  return fetcher<Array<Record<string, unknown>>>(`/backtest/history/${strategyId}`);
}

export async function deleteBacktestHistory(backtestId: string) {
  return fetcher(`/backtest/history/${backtestId}`, {
    method: "DELETE",
  });
}

export async function linkBacktestsToStrategy(backtestIds: string[], strategyId: string) {
  return fetcher("/backtest/link", {
    method: "POST",
    body: JSON.stringify({ backtest_ids: backtestIds, strategy_id: strategyId }),
  });
}

export async function analyzeBacktest(strategy: Record<string, unknown>, metrics: Record<string, unknown>) {
  return fetcher("/backtest/analyze", {
    method: "POST",
    body: JSON.stringify({ strategy, metrics }),
  });
}

export async function deleteStrategy(id: string) {
  return fetcher(`/strategy/${id}`, {
    method: "DELETE",
  });
}

// 시장 데이터 API
export async function getTokenPrices() {
  return fetcher<{ prices: Record<string, number | null> }>("/market/prices");
}

// 인증 API
export async function requestNonce(walletAddress: string) {
  return fetcher("/auth/wallet", {
    method: "POST",
    body: JSON.stringify({ wallet_address: walletAddress }),
  });
}

export async function verifyWallet(walletAddress: string, signature: string, nonce: string) {
  return fetcher("/auth/verify", {
    method: "POST",
    body: JSON.stringify({
      wallet_address: walletAddress,
      signature,
      nonce,
    }),
  });
}

export async function registerWithEmail(name: string, email: string) {
  return fetcher<{ access_token: string; user_id: string; name: string; email: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email }),
  });
}

// 최적화 API (Phase 2)
export interface OptimizeResult {
  params: Record<string, number>;
  metrics: Record<string, number>;
  rank: number;
}

// 백그라운드 작업 폴링 헬퍼
async function pollJob<T>(jobId: string, intervalMs = 2000, maxAttempts = 150): Promise<T> {
  for (let i = 0; i < maxAttempts; i++) {
    const job = await fetcher<{ job_id: string; status: string; result?: T; error?: string }>(
      `/optimize/job/${jobId}`
    );
    if (job.status === "completed" && job.result) {
      return job.result;
    }
    if (job.status === "failed") {
      throw new Error(job.error || "작업 실패");
    }
    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error("작업 시간 초과 (5분)");
}

export async function runOptimization(
  parsedStrategy: Record<string, unknown>,
  paramRanges: Record<string, number[]>,
  objective = "sharpe",
  maxCombinations = 100,
) {
  // 작업 시작 → job_id 수신
  const { job_id } = await fetcher<{ job_id: string; status: string }>("/optimize/grid", {
    method: "POST",
    body: JSON.stringify({
      parsed_strategy: parsedStrategy,
      param_ranges: paramRanges,
      objective,
      max_combinations: maxCombinations,
    }),
  });
  // 폴링으로 결과 대기
  return pollJob<{ results: OptimizeResult[]; total_tested: number; objective: string }>(job_id);
}

export interface WalkForwardWindow {
  window: number;
  is_metrics: Record<string, number>;
  oos_metrics: Record<string, number>;
  best_params: Record<string, number>;
  ratio: number;
}

export interface WalkForwardResult {
  windows: WalkForwardWindow[];
  avg_ratio: number;
  passed: boolean;
  recommended_params: Record<string, number>;
}

export async function runWalkForward(
  parsedStrategy: Record<string, unknown>,
  paramRanges?: Record<string, number[]>,
  inSampleDays = 60,
  outSampleDays = 30,
  windows = 3,
  days = 180,
) {
  // 작업 시작 → job_id 수신
  const { job_id } = await fetcher<{ job_id: string; status: string }>("/optimize/walk-forward", {
    method: "POST",
    body: JSON.stringify({
      parsed_strategy: parsedStrategy,
      param_ranges: paramRanges,
      in_sample_days: inSampleDays,
      out_sample_days: outSampleDays,
      windows,
      days,
    }),
  });
  // 폴링으로 결과 대기 (walk-forward는 더 오래 걸릴 수 있으므로 3초 간격)
  return pollJob<WalkForwardResult>(job_id, 3000, 200);
}

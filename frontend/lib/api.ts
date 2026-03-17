const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined"
    ? localStorage.getItem("tc_token")
    : null;

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

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
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

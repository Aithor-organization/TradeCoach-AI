"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "@/stores/chatStore";
import { useAuthStore } from "@/stores/authStore";
import { saveStrategy, runBacktest, linkBacktestsToStrategy } from "@/lib/api";
import StrategyCard from "./StrategyCard";
import BacktestResult from "./BacktestResult";
import BacktestChart from "./BacktestChart";
import BacktestSummary from "./BacktestSummary";
import ReactMarkdown from "react-markdown";
import TradeLogTable from "./TradeLogTable";
import type { Language } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import type { ChatMessage, BacktestResult as BacktestResultType } from "@/lib/types";

export default function ChatWindow({ onExampleClick, language = "ko" }: { onExampleClick?: (text: string) => void; language?: Language } = {}) {
  const { messages, isLoading } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {/* 빈 상태 */}
      {messages.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <span className="text-5xl mb-4">🤖</span>
          <h3 className="text-lg font-semibold text-white mb-2">{t("empty.title", language)}</h3>
          <p className="text-sm text-[#94A3B8] max-w-md whitespace-pre-line">
            {t("empty.description", language)}
          </p>
          <div className="mt-6 flex flex-wrap gap-2 justify-center">
            {[
              t("example.1", language),
              t("example.2", language),
              t("example.3", language),
              t("example.4", language),
            ].map((example) => (
              <button
                key={example}
                onClick={() => onExampleClick?.(example)}
                className="px-3 py-2 text-xs rounded-lg bg-[#1E293B] text-[#94A3B8] border border-[#22D3EE15] hover:border-[#22D3EE40] cursor-pointer transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 메시지 목록 */}
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} language={language} />
      ))}

      {/* 로딩 인디케이터 */}
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-[#0F172A] rounded-lg px-4 py-3 border border-[#22D3EE10]">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#22D3EE]">TradeCoach AI</span>
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

function MessageBubble({ message, language = "ko" }: { message: ChatMessage; language?: Language }) {
  const isUser = message.role === "user";
  const router = useRouter();
  const { addMessage } = useChatStore();
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [savedStrategyId, setSavedStrategyId] = useState<string | null>(null);
  const [isBacktesting, setIsBacktesting] = useState(false);

  const { messages: allMessages } = useChatStore();

  const handleSave = useCallback(async () => {
    const strategy = message.metadata?.parsed_strategy;
    if (!strategy) return;

    // 로그인 체크: 미로그인 시 AuthGuard가 있는 페이지로 리다이렉트
    const { isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated) {
      // 전략 데이터를 sessionStorage에 임시 저장
      sessionStorage.setItem("tc_pending_strategy", JSON.stringify({
        name: strategy.name || "New Strategy",
        parsed_strategy: strategy,
        raw_input: message.content || "",
      }));
      alert(language === "ko" ? "전략을 저장하려면 로그인이 필요합니다." : "Please login to save your strategy.");
      router.push("/strategies");
      return;
    }

    setIsSaving(true);
    try {
      const result: any = await saveStrategy(strategy.name || (language === "en" ? "New Strategy" : "새 전략"), strategy as unknown as Record<string, unknown>, message.content || "");
      setIsSaved(true);
      if (result?.id && result.id !== "local-strategy") {
        setSavedStrategyId(result.id);

        // 메인 챗의 백테스트 결과를 새 전략에 연결
        const btIds = allMessages
          .filter((m) => m.metadata?.backtest_result?.id && !m.metadata.backtest_result.id.startsWith("bt-"))
          .map((m) => m.metadata!.backtest_result!.id);
        if (btIds.length > 0) {
          linkBacktestsToStrategy(btIds, result.id).catch(() => {});
        }

        router.push(`/strategies/${result.id}`);
      }
    } catch (e: any) {
      const msg = e?.message || "";
      if (msg.includes("로그인") || msg.includes("401")) {
        alert(language === "ko" ? "전략을 저장하려면 로그인이 필요합니다." : "Please login to save your strategy.");
        router.push("/strategies");
      } else {
        console.error("Save strategy failed:", e);
      }
    } finally {
      setIsSaving(false);
    }
  }, [message, router, allMessages]);

  const handleRunBacktest = useCallback(async () => {
    const strategy = message.metadata?.parsed_strategy;
    if (!strategy) return;
    setIsBacktesting(true);
    try {
      const pair = strategy.target_pair || "SOL/USDC";
      const tf = strategy.timeframe || "1h";
      // max_positions=1 고정
      const strategyWithFixedPos = {
        ...(strategy as unknown as Record<string, unknown>),
        position: {
          ...(strategy.position || {}),
          max_positions: 1,
        },
      };
      const result: any = await runBacktest(
        savedStrategyId || "local",
        pair,
        tf,
        savedStrategyId ? undefined : strategyWithFixedPos,
        undefined,
        undefined,
        language,
      );
      // 백테스트 결과를 새 메시지로 추가
      const btResult: BacktestResultType = {
        id: result.id || "bt-" + Date.now(),
        strategy_id: savedStrategyId || "local",
        metrics: result.metrics,
        equity_curve: result.equity_curve || [],
        trade_log: result.trade_log || [],
        ai_summary: result.ai_summary || undefined,
        actual_period: result.actual_period,
      };
      addMessage({
        id: "bt-result-" + Date.now(),
        role: "assistant",
        content: language === "en"
          ? `Backtest complete: ${pair} ${tf}\nTotal return ${result.metrics?.total_return ?? 0}%, Win rate ${result.metrics?.win_rate ?? 0}%, ${result.metrics?.total_trades ?? 0} trades`
          : `백테스트 완료: ${pair} ${tf} 기준\n총 수익률 ${result.metrics?.total_return ?? 0}%, 승률 ${result.metrics?.win_rate ?? 0}%, ${result.metrics?.total_trades ?? 0}회 거래`,
        metadata: { type: "backtest_result", backtest_result: btResult },
        created_at: new Date().toISOString(),
      });
    } catch (e: any) {
      addMessage({
        id: "bt-error-" + Date.now(),
        role: "assistant",
        content: language === "en"
          ? `Backtest failed: ${e.message || "Server error"}`
          : `백테스트 실행 실패: ${e.message || "서버 오류"}`,
        created_at: new Date().toISOString(),
      });
    } finally {
      setIsBacktesting(false);
    }
  }, [message, savedStrategyId, addMessage]);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-lg ${isUser
            ? "bg-[#22D3EE15] border border-[#22D3EE30] rounded-lg px-4 py-3"
            : "space-y-3"
          }`}
      >
        {isUser ? (
          <div>
            {message.imageUrl && (
              <img
                src={message.imageUrl}
                alt={t("cp.attachedImage", language)}
                className="max-w-full max-h-60 rounded-lg mb-2"
              />
            )}
            <p className="text-sm text-white whitespace-pre-wrap">{message.content}</p>
          </div>
        ) : (
          <>
            {/* AI 텍스트 응답 */}
            <div className="bg-[#0F172A] rounded-lg px-4 py-3 border border-[#22D3EE10]">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-mono font-bold text-[#22D3EE]">TradeCoach AI</span>
              </div>
              <div className="prose prose-sm prose-invert max-w-none prose-p:text-[#94A3B8] prose-strong:text-white prose-li:text-[#94A3B8] prose-headings:text-white prose-h3:text-[14px] prose-h3:mt-4 prose-h3:mb-1.5">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>

            {/* 전략 카드 (있으면) */}
            {message.metadata?.parsed_strategy && (
              <StrategyCard
                strategy={message.metadata.parsed_strategy}
                onSave={handleSave}
                isSaving={isSaving}
                isSaved={isSaved}
                onRunBacktest={handleRunBacktest}
              />
            )}

            {/* 백테스트 실행 중 */}
            {isBacktesting && (
              <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] px-5 py-3 max-w-md">
                <div className="flex items-center gap-2">
                  <span className="text-sm">📊</span>
                  <span className="text-xs text-[#94A3B8]">{t("backtest.running", language)}</span>
                  <div className="flex gap-1 ml-auto">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            {/* 백테스트 결과 (차트 또는 메트릭스) */}
            {message.metadata?.backtest_result?.equity_curve?.length ? (
              <BacktestChart
                equityCurve={message.metadata.backtest_result.equity_curve}
                metrics={message.metadata.backtest_result.metrics}
                tradeLog={message.metadata.backtest_result.trade_log}
                actualPeriod={message.metadata.backtest_result.actual_period}
              />
            ) : message.metadata?.backtest_result ? (
              <BacktestResult result={message.metadata.backtest_result} />
            ) : null}

            {/* AI 전략 분석 리포트 */}
            {message.metadata?.backtest_result?.ai_summary && (
              <BacktestSummary aiSummary={message.metadata.backtest_result.ai_summary} />
            )}

            {/* 거래 내역 테이블 */}
            {message.metadata?.backtest_result?.trade_log && (
              <TradeLogTable trades={message.metadata.backtest_result.trade_log} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

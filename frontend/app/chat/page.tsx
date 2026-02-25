"use client";

import { Suspense, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useChatStore } from "@/stores/chatStore";
import ChatWindow from "@/components/chat/ChatWindow";
import ChatInput from "@/components/chat/ChatInput";
import { sendMessage, sendMessageWithImage } from "@/lib/api";
import type { ChatMessage, ChatResponse } from "@/lib/types";

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center bg-[#0A0F1C] text-[#475569]">
        로딩 중...
      </div>
    }>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const searchParams = useSearchParams();
  const initRef = useRef(false);

  const {
    messages,
    addMessage,
    setLoading,
    currentStrategyId,
    currentStrategy,
    lastBacktestResult,
    setCurrentStrategy,
    setCurrentStrategyId,
  } = useChatStore();

  const handleSend = useCallback(async (text: string, image?: File) => {
    // 사용자 메시지 추가
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: image ? `${text} [📎 이미지 첨부]` : text,
      created_at: new Date().toISOString(),
    };
    addMessage(userMsg);
    setLoading(true);

    // 대화 히스토리 구성 (현재 메시지 포함)
    const history = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
      metadata: m.metadata,
    }));

    try {
      let response: ChatResponse;

      if (image) {
        response = await sendMessageWithImage(text, image, currentStrategyId || undefined, history) as ChatResponse;
      } else {
        response = await sendMessage(text, currentStrategyId || undefined, history) as ChatResponse;
      }

      // AI 응답 메시지 추가
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: response.message,
        metadata: {
          type: response.type,
          parsed_strategy: response.parsed_strategy,
          backtest_result: response.backtest_result,
        },
        created_at: new Date().toISOString(),
      };
      addMessage(aiMsg);

      // 전략이 파싱되면 상태 업데이트
      if (response.parsed_strategy) {
        setCurrentStrategy(response.parsed_strategy);
      }
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}. 백엔드 서버가 실행 중인지 확인해주세요.`,
        created_at: new Date().toISOString(),
      };
      addMessage(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [messages, addMessage, setLoading, currentStrategyId, setCurrentStrategy, setCurrentStrategyId]);

  // 전략 상세 페이지에서 진입 시 자동 코칭 시작
  useEffect(() => {
    if (initRef.current) return;
    const from = searchParams.get("from");
    if (from !== "strategy" || !currentStrategy) return;
    initRef.current = true;

    // 전략 요약 + 백테스트 결과를 포함한 시스템 메시지 구성
    const ps = currentStrategy;
    const conditions = ps.entry?.conditions?.map(c => c.description || `${c.indicator} ${c.operator} ${c.value}`).join(", ") || "없음";
    let contextMsg = `[전략 분석 요청]\n전략명: ${ps.name}\n진입조건: ${conditions}\n익절: ${ps.exit?.take_profit?.value ?? "미설정"}%\n손절: ${ps.exit?.stop_loss?.value ?? "미설정"}%\n타임프레임: ${ps.timeframe || "1h"}\n대상: ${ps.target_pair || "SOL/USDC"}`;

    if (lastBacktestResult) {
      const m = lastBacktestResult.metrics;
      contextMsg += `\n\n[백테스트 결과]\n총 수익률: ${m.total_return}%\n최대 낙폭(MDD): ${m.max_drawdown}%\n샤프비율: ${m.sharpe_ratio}\n승률: ${m.win_rate}%\n총 거래수: ${m.total_trades}회`;
    }

    contextMsg += "\n\n이 전략의 강점과 약점을 분석하고, 개선 방향을 제안해주세요.";

    // 시스템 메시지를 사용자 메시지로 표시
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: contextMsg,
      created_at: new Date().toISOString(),
    };
    addMessage(userMsg);

    // AI에게 코칭 요청
    const requestCoaching = async () => {
      setLoading(true);
      try {
        const history = [{ role: "user" as const, content: contextMsg }];
        const response = await sendMessage(contextMsg, currentStrategyId || undefined, history) as ChatResponse;

        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: response.message,
          metadata: {
            type: response.type,
            parsed_strategy: response.parsed_strategy,
          },
          created_at: new Date().toISOString(),
        };
        addMessage(aiMsg);

        if (response.parsed_strategy) {
          setCurrentStrategy(response.parsed_strategy);
        }
      } catch (error) {
        addMessage({
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `코칭 요청 중 오류: ${error instanceof Error ? error.message : "알 수 없는 오류"}`,
          created_at: new Date().toISOString(),
        });
      } finally {
        setLoading(false);
      }
    };

    requestCoaching();
  }, [searchParams, currentStrategy, lastBacktestResult, currentStrategyId, addMessage, setLoading, setCurrentStrategy]);

  return (
    <div className="h-screen flex flex-col bg-[#0A0F1C]">
      {/* 상단 바 */}
      <header className="h-14 flex items-center justify-between px-4 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold text-white">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
              AI
            </span>
          </Link>
          {currentStrategy && (
            <>
              <span className="text-[#475569]">/</span>
              <span className="text-xs text-[#94A3B8] truncate max-w-[200px]">
                {currentStrategy.name} 코칭 중
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/strategies"
            className="text-xs text-[#475569] hover:text-[#94A3B8] transition-colors"
          >
            전략 목록
          </Link>
          <button
            onClick={() => useChatStore.getState().clearChat()}
            className="text-xs text-[#475569] hover:text-[#94A3B8] cursor-pointer"
          >
            새 대화
          </button>
        </div>
      </header>

      {/* 채팅 영역 */}
      <ChatWindow onExampleClick={(text) => handleSend(text)} />

      {/* 입력 바 */}
      <ChatInput onSend={handleSend} />
    </div>
  );
}

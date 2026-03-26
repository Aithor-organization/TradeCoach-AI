"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useChatStore } from "@/stores/chatStore";
import ChatWindow from "@/components/chat/ChatWindow";
import ChatInput from "@/components/chat/ChatInput";
import { sendMessageStream, sendMessageWithImage } from "@/lib/api";
import { useLanguageStore } from "@/stores/languageStore";
import AuthGuard from "@/components/common/AuthGuard";
import AppHeader from "@/components/layout/AppHeader";
import { t } from "@/lib/i18n";
import type { ChatMessage, ChatResponse, ParsedStrategy } from "@/lib/types";

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center bg-[#0A0F1C]">
        <div className="animate-spin h-8 w-8 border-2 border-[#22D3EE] border-t-transparent rounded-full" />
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
    updateMessage,
    setLoading,
    currentStrategyId,
    currentStrategy,
    lastBacktestResult,
    setCurrentStrategy,
    setCurrentStrategyId,
    clearChat,
  } = useChatStore();

  const { language, toggleLanguage } = useLanguageStore();

  const handleSend = useCallback(async (text: string, image?: File) => {
    // 사용자 메시지 추가
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text || (image ? t("strategy.imageAnalysis", language) : ""),
      imageUrl: image ? URL.createObjectURL(image) : undefined,
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
      if (image) {
        // 이미지 첨부 시 기존 non-streaming 방식 유지
        const response = await sendMessageWithImage(text, image, currentStrategyId || undefined, history, language) as ChatResponse;
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
        if (response.parsed_strategy) {
          setCurrentStrategy(response.parsed_strategy);
        }
      } else {
        // 텍스트 전용: 스트리밍 방식
        const aiMsgId = `ai-${Date.now()}`;
        addMessage({
          id: aiMsgId,
          role: "assistant",
          content: "",
          created_at: new Date().toISOString(),
        });
        setLoading(false);

        await sendMessageStream(
          text,
          currentStrategyId || undefined,
          history,
          (chunk) => {
            updateMessage(aiMsgId, {
              content: (useChatStore.getState().messages.find(m => m.id === aiMsgId)?.content || "") + chunk,
            });
          },
          (data) => {
            const parsedStrat = data.parsed_strategy as ParsedStrategy | undefined;
            const msgType = data.type as NonNullable<ChatMessage["metadata"]>["type"];
            updateMessage(aiMsgId, {
              metadata: { type: msgType, parsed_strategy: parsedStrat },
            });
            if (parsedStrat) setCurrentStrategy(parsedStrat);
          },
          language,
        );
      }
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `${t("error.aiResponse", language)}: ${error instanceof Error ? error.message : "Unknown error"}. ${t("error.checkServer", language)}`,
        created_at: new Date().toISOString(),
      };
      addMessage(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [messages, addMessage, updateMessage, setLoading, currentStrategyId, setCurrentStrategy, language]);

  // 전략 상세 페이지에서 진입 시 자동 코칭 시작
  useEffect(() => {
    if (initRef.current) return;
    const from = searchParams.get("from");
    if (from !== "strategy" || !currentStrategy) return;
    initRef.current = true;

    // 전략 요약 + 백테스트 결과를 포함한 시스템 메시지 구성
    const ps = currentStrategy;
    const conditions = ps.entry?.conditions?.map(c => c.description || `${c.indicator} ${c.operator} ${c.value}`).join(", ") || t("ctx.none", language);
    let contextMsg = `${t("ctx.strategyRequest", language)}\n${t("ctx.strategyName", language)} ${ps.name}\n${t("ctx.entryCondition", language)} ${conditions}\n${t("ctx.takeProfit", language)} ${ps.exit?.take_profit?.value ?? t("ctx.notSet", language)}%\n${t("ctx.stopLoss", language)} ${ps.exit?.stop_loss?.value ?? t("ctx.notSet", language)}%\n${t("ctx.timeframe", language)} ${ps.timeframe || "1h"}\n${t("ctx.target", language)} ${ps.target_pair || "SOL/USDC"}`;

    if (lastBacktestResult) {
      const m = lastBacktestResult.metrics;
      contextMsg += `\n\n${t("ctx.backtestResult", language)}\n${t("ctx.totalReturn", language)} ${m.total_return}%\n${t("ctx.mdd", language)} ${m.max_drawdown}%\n${t("ctx.sharpe", language)} ${m.sharpe_ratio}\n${t("ctx.winRate", language)} ${m.win_rate}%\n${t("ctx.totalTrades", language)} ${m.total_trades}`;
    }

    contextMsg += `\n\n${t("ctx.coachingPrompt", language)}`;

    // 시스템 메시지를 사용자 메시지로 표시
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: contextMsg,
      created_at: new Date().toISOString(),
    };
    addMessage(userMsg);

    // AI에게 코칭 요청 (스트리밍)
    const requestCoaching = async () => {
      setLoading(true);
      const aiMsgId = `ai-${Date.now()}`;
      addMessage({
        id: aiMsgId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
      });
      setLoading(false);

      try {
        const history = [{ role: "user" as const, content: contextMsg }];
        await sendMessageStream(
          contextMsg,
          currentStrategyId || undefined,
          history,
          (chunk) => {
            updateMessage(aiMsgId, {
              content: (useChatStore.getState().messages.find(m => m.id === aiMsgId)?.content || "") + chunk,
            });
          },
          (data) => {
            const parsedStrat = data.parsed_strategy as ParsedStrategy | undefined;
            const msgType = data.type as NonNullable<ChatMessage["metadata"]>["type"];
            updateMessage(aiMsgId, {
              metadata: { type: msgType, parsed_strategy: parsedStrat },
            });
            if (parsedStrat) setCurrentStrategy(parsedStrat);
          },
          language,
        );
      } catch (error) {
        addMessage({
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `${t("error.coaching", language)}: ${error instanceof Error ? error.message : "Unknown error"}`,
          created_at: new Date().toISOString(),
        });
      }
    };

    requestCoaching();
  }, [searchParams, currentStrategy, lastBacktestResult, currentStrategyId, addMessage, updateMessage, setLoading, setCurrentStrategy]);

  return (
    <AuthGuard>
    <div className="h-screen flex flex-col bg-[#0A0F1C]">
      {/* 상단 바 */}
      <AppHeader
        activePage="chat"
        rightSlot={
          <div className="flex items-center gap-3">
            <button
              onClick={toggleLanguage}
              className="flex items-center gap-1 px-2 py-1 rounded-md bg-[#1E293B] border border-[#22D3EE20] hover:border-[#22D3EE50] transition-colors cursor-pointer"
              title={language === "ko" ? "Switch to English" : "한국어로 전환"}
            >
              <span className={`text-xs font-bold ${language === "ko" ? "text-[#22D3EE]" : "text-[#475569]"}`}>한</span>
              <span className="text-xs text-[#475569]">/</span>
              <span className={`text-xs font-bold ${language === "en" ? "text-[#22D3EE]" : "text-[#475569]"}`}>EN</span>
            </button>
            <button
              onClick={() => clearChat()}
              className="text-xs text-[#94A3B8] hover:text-white cursor-pointer"
            >
              {t("chat.newChat", language)}
            </button>
          </div>
        }
      />

      {/* 채팅 영역 */}
      <ChatWindow onExampleClick={(text) => handleSend(text)} language={language} />

      {/* 입력 바 */}
      <ChatInput onSend={handleSend} language={language} />
    </div>
    </AuthGuard>
  );
}

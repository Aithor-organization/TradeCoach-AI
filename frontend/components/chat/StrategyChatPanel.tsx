"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sendMessage, sendMessageWithImage, sendMessageStream, getChatHistory } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import type { ChatMessage, ChatResponse, ParsedStrategy } from "@/lib/types";
import ImagePreview from "./ImagePreview";
import StrategyCard from "./StrategyCard";

interface StrategyChatPanelProps {
  strategyId: string;
  strategy: ParsedStrategy;
  onStrategyUpdate: (updated: ParsedStrategy) => void;
  onOptimizeRanges?: (ranges: Record<string, number[]>, objective?: string) => void;
  investmentAmount?: number;
}

export default function StrategyChatPanel({ strategyId, strategy, onStrategyUpdate, onOptimizeRanges, investmentAmount }: StrategyChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [attachedImage, setAttachedImage] = useState<File | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { language } = useLanguageStore();
  const pendingInput = useChatStore((s) => s.pendingInput);
  const setPendingInput = useChatStore((s) => s.setPendingInput);

  // 외부에서 pendingInput이 설정되면 입력창에 반영 (바로 개선 버튼 등)
  useEffect(() => {
    if (pendingInput) {
      setText(pendingInput);
      setPendingInput(null);
    }
  }, [pendingInput, setPendingInput]);

  // 텍스트 양에 따라 textarea 높이 자동 조절 (최대 3배)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    // 기본 높이 36px, 최대 3배 = 108px
    el.style.height = Math.min(el.scrollHeight, 108) + "px";
  }, [text]);

  // 마운트 시 저장된 채팅 히스토리 로드
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getChatHistory(strategyId) as { messages: Array<{ id: string; role: "user" | "assistant"; content: string; metadata?: Record<string, unknown>; created_at: string }> };
        if (!cancelled && data.messages?.length > 0) {
          setMessages(data.messages.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            metadata: m.metadata as ChatMessage["metadata"],
            created_at: m.created_at,
          })));
        }
      } catch {
        // 히스토리 로드 실패는 무시 (빈 채팅으로 시작)
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    })();
    return () => { cancelled = true; };
  }, [strategyId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // 전략 요약 텍스트 생성 (UI 표시용)
  const displayInvestment = investmentAmount ?? strategy.position?.size_value ?? 1000;
  const strategySummary = (() => {
    const ps = strategy;
    const conditions = ps.entry?.conditions?.map(c => c.description || `${c.indicator} ${c.operator} ${c.value}`).join(", ") || t("cp.none", language);
    return `${ps.name} | ${t("sc.entryConditions", language)}: ${conditions} | ${t("sc.takeProfit", language)} ${ps.exit?.take_profit?.value ?? t("ctx.notSet", language)}% / ${t("sc.stopLoss", language)} ${ps.exit?.stop_loss?.value ?? t("ctx.notSet", language)}% | ${t("sc.investment", language)} $${displayInvestment.toLocaleString()} | ${ps.timeframe || "1h"} ${ps.target_pair || "SOL/USDC"}`;
  })();

  const handleSend = useCallback(async () => {
    if ((!text.trim() && !attachedImage) || isLoading) return;
    const content = text.trim();
    const image = attachedImage;
    setText("");
    setAttachedImage(null);

    const displayContent = image ? `${content || ""}\n${t("cp.imageAttached", language)}` : content;
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: displayContent,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const history = [...messages, userMsg].map(m => ({
        role: m.role,
        content: m.content,
      }));
      // 투자금 컨텍스트를 시스템 메시지로 첫 번째에 삽입
      history.unshift({
        role: "user" as const,
        content: `${t("cp.systemContext", language)} $${displayInvestment.toLocaleString()}. ${t("cp.systemContextSuffix", language)}`,
      });

      // 이미지가 있으면 기존 방식 (멀티모달은 스트리밍 미지원)
      if (image) {
        const response = await sendMessageWithImage(content || t("cp.analyzeChart", language), image, strategyId, history, language) as ChatResponse;
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: response.message,
          metadata: { type: response.type, parsed_strategy: response.parsed_strategy },
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, aiMsg]);
        if (response.parsed_strategy) onStrategyUpdate(response.parsed_strategy);
        return;
      }

      // 텍스트 전용: 스트리밍 모드
      const aiMsgId = `ai-${Date.now()}`;
      // 빈 AI 메시지를 먼저 추가 (스트리밍 중 점진적 업데이트)
      setMessages(prev => [...prev, {
        id: aiMsgId,
        role: "assistant" as const,
        content: "",
        created_at: new Date().toISOString(),
      }]);
      setIsLoading(false); // 스트리밍 시작하면 로딩 인디케이터 숨김

      await sendMessageStream(
        content,
        strategyId,
        history,
        // onChunk: 청크가 도착할 때마다 AI 메시지 업데이트
        (chunk) => {
          setMessages(prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, content: m.content + chunk } : m
          ));
        },
        // onDone: 스트리밍 완료
        (data) => {
          const msgType = data.type as "strategy_parsed" | "strategy_updated" | "coaching" | "general";
          const parsedStrat = data.parsed_strategy as ParsedStrategy | undefined;
          setMessages(prev => prev.map(m =>
            m.id === aiMsgId
              ? { ...m, metadata: { type: msgType, parsed_strategy: parsedStrat } }
              : m
          ));
          if (parsedStrat) {
            onStrategyUpdate(parsedStrat);
          }
        },
        language,
      );
    } catch {
      setMessages(prev => {
        const last = prev[prev.length - 1];
        // 빈 AI 메시지가 있으면 에러 내용으로 교체
        if (last?.role === "assistant" && !last.content) {
          return [...prev.slice(0, -1), { ...last, content: t("cp.error", language) }];
        }
        return [...prev, {
          id: `error-${Date.now()}`,
          role: "assistant" as const,
          content: t("cp.error", language),
          created_at: new Date().toISOString(),
        }];
      });
    } finally {
      setIsLoading(false);
    }
  }, [text, attachedImage, isLoading, messages, strategyId, onStrategyUpdate]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) setAttachedImage(file);
        return;
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith("image/")) {
      setAttachedImage(file);
    }
    e.target.value = "";
  };

  return (
    <div className="flex flex-col h-full bg-[#0F172A] rounded-xl border border-[#1E293B] overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1E293B]">
        <span className="text-xs font-mono font-bold text-[#22D3EE]">AI Coach</span>
        <span className="text-xs text-[#475569]">/ {strategy.name}</span>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {/* 히스토리 로딩 중 */}
        {isLoadingHistory && (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-xs text-[#475569]">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              {t("cp.loadingHistory", language)}
            </div>
          </div>
        )}

        {/* 전략 컨텍스트 안내 (시스템 지식) */}
        {messages.length === 0 && !isLoading && !isLoadingHistory && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
            <div className="w-10 h-10 rounded-full bg-[#22D3EE15] border border-[#22D3EE30] flex items-center justify-center">
              <span className="text-sm font-mono font-bold text-[#22D3EE]">AI</span>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-[#94A3B8]">
                {t("cp.aiReady", language)}
              </p>
              <p className="text-[10px] text-[#475569] leading-relaxed max-w-[300px]">
                {strategySummary}
              </p>
            </div>
            <div className="space-y-1.5 w-full max-w-[280px]">
              <p className="text-[10px] text-[#475569] mb-2">{t("cp.exampleQuestions", language)}</p>
              {[
                t("cp.example1", language),
                t("cp.example2", language),
                t("cp.example3", language),
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => { setText(example); }}
                  className="w-full text-left text-[10px] text-[#94A3B8] px-3 py-2 rounded-lg bg-[#1E293B] border border-[#22D3EE08] hover:border-[#22D3EE30] transition-colors cursor-pointer"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => {
          let displayContent = msg.content;

          if (msg.role === "assistant" && msg.metadata?.parsed_strategy) {
            displayContent = displayContent.replace(/```strategy_update[\s\S]*?```/g, "").trim();
            displayContent = displayContent.replace(/```json[\s\S]*?```/g, "").trim();
          }

          // optimize_ranges 블록 감지 → 버튼으로 변환
          const optimizeMatch = msg.role === "assistant"
            ? displayContent.match(/```optimize_ranges\s*([\s\S]*?)```/)
            : null;
          if (optimizeMatch) {
            displayContent = displayContent.replace(/```optimize_ranges[\s\S]*?```/g, "").trim();
          }

          return (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} w-full`}>
              <div className={`max-w-[100%] ${msg.role === "user"
                  ? "bg-[#22D3EE15] border border-[#22D3EE30] rounded-lg px-3 py-2 ms-auto"
                  : "bg-[#1E293B] rounded-lg px-3 py-3 border border-[#22D3EE08] w-full"
                }`}>
                {msg.role === "assistant" && (
                  <div className="flex items-center gap-1.5 mb-2">
                    <span className="text-[10px] font-mono font-bold text-[#22D3EE]">TradeCoach AI</span>
                  </div>
                )}

                {displayContent && (
                  <p className="text-xs text-[#94A3B8] whitespace-pre-wrap leading-relaxed">{displayContent}</p>
                )}

                {msg.role === "assistant" && msg.metadata?.parsed_strategy && (
                  <div className="mt-4 border-t border-[#0F172A] pt-4">
                    <div className="mb-2 text-[10px] text-[#22D3EE] font-bold">{t("cp.strategyUpdate", language)}</div>
                    <StrategyCard strategy={msg.metadata.parsed_strategy as ParsedStrategy} />
                  </div>
                )}

                {/* AI 추천 최적화 범위 → 버튼 */}
                {optimizeMatch && onOptimizeRanges && (
                  <button
                    onClick={() => {
                      try {
                        const parsed = JSON.parse(optimizeMatch[1]);
                        const { objective, ...ranges } = parsed;
                        onOptimizeRanges(ranges, objective);
                      } catch { /* JSON 파싱 실패 */ }
                    }}
                    className="mt-2 w-full py-2 text-xs font-semibold rounded-lg bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B30] hover:bg-[#F59E0B]/20 transition cursor-pointer"
                  >
                    {t("cp.runOptimize", language)}
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#1E293B] rounded-lg px-4 py-3 border border-[#22D3EE15]">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold text-[#22D3EE]">TradeCoach AI</span>
                <span className="text-[10px] text-[#94A3B8]">analyzing...</span>
                <div className="flex gap-1 ml-1">
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

      {/* 입력 영역 */}
      <div className="border-t border-[#1E293B] p-3">
        {/* 이미지 미리보기 */}
        {attachedImage && (
          <ImagePreview file={attachedImage} onRemove={() => setAttachedImage(null)} />
        )}

        <div className="flex items-end gap-2">
          {/* 이미지 첨부 버튼 */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-8 h-8 flex-shrink-0 rounded-lg bg-[#1E293B] flex items-center justify-center text-[#94A3B8] hover:text-white hover:bg-[#22D3EE20] transition-colors cursor-pointer text-xs"
            title={t("cp.attachImage", language)}
          >
            📎
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileSelect}
          />

          <textarea
            ref={textareaRef}
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={t("cp.placeholder", language)}
            className="flex-1 bg-[#1E293B] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none resize-none min-h-[36px] placeholder-[#475569] overflow-y-auto"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || (!text.trim() && !attachedImage)}
            className="w-8 h-8 flex-shrink-0 rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] flex items-center justify-center text-[#0A0F1C] text-xs font-bold disabled:opacity-40 cursor-pointer transition-opacity"
          >
            {isLoading ? "..." : "↑"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatMessage, ParsedStrategy, BacktestResult } from "@/lib/types";

interface ChatThread {
  id: string;
  title: string;
  messages: ChatMessage[];
  strategyId: string | null;
  strategy: ParsedStrategy | null;
  updatedAt: string;
}

interface ChatState {
  // 현재 활성 쓰레드
  activeThreadId: string | null;
  threads: ChatThread[];

  // 현재 쓰레드의 편의 접근자
  messages: ChatMessage[];
  isLoading: boolean;
  currentStrategyId: string | null;
  currentStrategy: ParsedStrategy | null;
  lastBacktestResult: BacktestResult | null;
  attachedImage: File | null;
  pendingInput: string | null;

  // 액션
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setLoading: (loading: boolean) => void;
  setCurrentStrategyId: (id: string | null) => void;
  setCurrentStrategy: (strategy: ParsedStrategy | null) => void;
  setLastBacktestResult: (result: BacktestResult | null) => void;
  setAttachedImage: (image: File | null) => void;
  setPendingInput: (text: string | null) => void;
  clearChat: () => void;

  // 쓰레드 관리
  loadThread: (threadId: string) => void;
  deleteThread: (threadId: string) => void;
}

function generateThreadId() {
  return `thread-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
}

function deriveTitle(messages: ChatMessage[]): string {
  const firstUser = messages.find(m => m.role === "user");
  if (!firstUser) return "새 대화";
  const text = firstUser.content.replace(/\[.*?\]/g, "").trim();
  return text.length > 30 ? text.substring(0, 30) + "..." : text || "새 대화";
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      activeThreadId: null,
      threads: [],
      messages: [],
      isLoading: false,
      currentStrategyId: null,
      currentStrategy: null,
      lastBacktestResult: null,
      attachedImage: null,
      pendingInput: null,

      addMessage: (message) =>
        set((state) => {
          const newMessages = [...state.messages, message];
          // 활성 쓰레드가 없으면 자동 생성
          let threadId = state.activeThreadId;
          let threads = [...state.threads];

          if (!threadId) {
            threadId = generateThreadId();
            threads.push({
              id: threadId,
              title: "새 대화",
              messages: newMessages,
              strategyId: state.currentStrategyId,
              strategy: state.currentStrategy,
              updatedAt: new Date().toISOString(),
            });
          } else {
            threads = threads.map(t =>
              t.id === threadId
                ? { ...t, messages: newMessages, title: deriveTitle(newMessages), updatedAt: new Date().toISOString() }
                : t
            );
          }

          return { messages: newMessages, activeThreadId: threadId, threads };
        }),

      updateMessage: (id, updates) =>
        set((state) => {
          const newMessages = state.messages.map(m =>
            m.id === id ? { ...m, ...updates } : m
          );
          const threads = state.activeThreadId
            ? state.threads.map(t =>
              t.id === state.activeThreadId
                ? { ...t, messages: newMessages, updatedAt: new Date().toISOString() }
                : t
            )
            : state.threads;
          return { messages: newMessages, threads };
        }),

      setLoading: (loading) =>
        set({ isLoading: loading }),

      setCurrentStrategyId: (id) =>
        set((state) => {
          const threads = state.activeThreadId
            ? state.threads.map(t =>
              t.id === state.activeThreadId ? { ...t, strategyId: id } : t
            )
            : state.threads;
          return { currentStrategyId: id, threads };
        }),

      setCurrentStrategy: (strategy) =>
        set((state) => {
          const threads = state.activeThreadId
            ? state.threads.map(t =>
              t.id === state.activeThreadId ? { ...t, strategy } : t
            )
            : state.threads;
          return { currentStrategy: strategy, threads };
        }),

      setLastBacktestResult: (result) =>
        set({ lastBacktestResult: result }),

      setAttachedImage: (image) =>
        set({ attachedImage: image }),

      setPendingInput: (text) =>
        set({ pendingInput: text }),

      clearChat: () =>
        set({
          activeThreadId: null,
          messages: [],
          currentStrategyId: null,
          currentStrategy: null,
          lastBacktestResult: null,
          attachedImage: null,
        }),

      loadThread: (threadId) =>
        set((state) => {
          const thread = state.threads.find(t => t.id === threadId);
          if (!thread) return {};
          return {
            activeThreadId: threadId,
            messages: thread.messages,
            currentStrategyId: thread.strategyId,
            currentStrategy: thread.strategy,
            lastBacktestResult: null,
            attachedImage: null,
          };
        }),

      deleteThread: (threadId) =>
        set((state) => {
          const threads = state.threads.filter(t => t.id !== threadId);
          // 삭제된 쓰레드가 현재 활성이면 초기화
          if (state.activeThreadId === threadId) {
            return {
              threads,
              activeThreadId: null,
              messages: [],
              currentStrategyId: null,
              currentStrategy: null,
              lastBacktestResult: null,
            };
          }
          return { threads };
        }),
    }),
    {
      name: "tc-chat-store",
      // File 객체, loading 상태 등은 persist 제외
      partialize: (state) => ({
        activeThreadId: state.activeThreadId,
        threads: state.threads,
        messages: state.messages,
        currentStrategyId: state.currentStrategyId,
        currentStrategy: state.currentStrategy,
      }),
    }
  )
);

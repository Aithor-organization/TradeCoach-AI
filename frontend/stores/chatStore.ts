import { create } from "zustand";
import type { ChatMessage, ParsedStrategy, BacktestResult } from "@/lib/types";

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  currentStrategyId: string | null;
  currentStrategy: ParsedStrategy | null;
  lastBacktestResult: BacktestResult | null;
  attachedImage: File | null;

  // 액션
  addMessage: (message: ChatMessage) => void;
  setLoading: (loading: boolean) => void;
  setCurrentStrategyId: (id: string | null) => void;
  setCurrentStrategy: (strategy: ParsedStrategy | null) => void;
  setLastBacktestResult: (result: BacktestResult | null) => void;
  setAttachedImage: (image: File | null) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  currentStrategyId: null,
  currentStrategy: null,
  lastBacktestResult: null,
  attachedImage: null,

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setLoading: (loading) =>
    set({ isLoading: loading }),

  setCurrentStrategyId: (id) =>
    set({ currentStrategyId: id }),

  setCurrentStrategy: (strategy) =>
    set({ currentStrategy: strategy }),

  setLastBacktestResult: (result) =>
    set({ lastBacktestResult: result }),

  setAttachedImage: (image) =>
    set({ attachedImage: image }),

  clearChat: () =>
    set({
      messages: [],
      currentStrategyId: null,
      currentStrategy: null,
      lastBacktestResult: null,
      attachedImage: null,
    }),
}));

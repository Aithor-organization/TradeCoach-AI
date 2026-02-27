"use client";

import ReactMarkdown from "react-markdown";
import { useChatStore } from "@/stores/chatStore";

interface BacktestSummaryProps {
    aiSummary?: string;
}

export default function BacktestSummary({ aiSummary }: BacktestSummaryProps) {
    const setPendingInput = useChatStore((s) => s.setPendingInput);

    if (!aiSummary) return null;

    const handleQuickImprove = () => {
        const prompt = `위 AI 전략 분석 리포트를 기반으로 전략을 개선해주세요:\n\n${aiSummary}`;
        setPendingInput(prompt);
    };

    return (
        <div className="bg-[#1E293B] rounded-xl border border-[#D946EF]/20 overflow-hidden w-full relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-[#D946EF] to-[#8B5CF6]" />

            <div className="px-5 py-3 border-b border-[#0F172A] flex items-center justify-between">
                <label className="font-semibold text-white text-sm flex items-center gap-2">
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#D946EF] to-[#8B5CF6]">
                        AI 전략 분석 리포트
                    </span>
                </label>
                <button
                    type="button"
                    onClick={handleQuickImprove}
                    className="px-3 py-1 text-xs font-semibold rounded-md bg-gradient-to-r from-[#D946EF] to-[#8B5CF6] text-white hover:opacity-90 transition-opacity cursor-pointer"
                >
                    바로 개선
                </button>
            </div>

            <div className="p-5 text-sm">
                <div className="prose prose-sm prose-invert max-w-none prose-p:text-[#CBD5E1] prose-strong:text-white prose-li:text-[#CBD5E1]">
                    <ReactMarkdown
                        components={{
                            h3: ({ children }) => (
                                <h3 className="text-[15px] font-extrabold text-white mt-5 mb-2 pb-1.5 border-b border-[#D946EF]/30 first:mt-0">
                                    {children}
                                </h3>
                            ),
                        }}
                    >{aiSummary}</ReactMarkdown>
                </div>
            </div>
        </div>
    );
}

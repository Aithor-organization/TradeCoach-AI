"use client";

import { useState, useEffect } from "react";
import { analyzeBacktest } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface BacktestSummaryProps {
    strategy: Record<string, unknown>;
    metrics: Record<string, unknown>;
}

export default function BacktestSummary({ strategy, metrics }: BacktestSummaryProps) {
    const [summary, setSummary] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        let isMounted = true;

        async function fetchSummary() {
            setLoading(true);
            setError(false);
            try {
                const response = await analyzeBacktest(strategy, metrics) as { summary?: string };
                if (response?.summary && isMounted) {
                    setSummary(response.summary);
                } else if (isMounted) {
                    setError(true);
                }
            } catch (err) {
                console.error("AI 요약 분석 중 오류 발생:", err);
                if (isMounted) setError(true);
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        fetchSummary();

        return () => {
            isMounted = false;
        };
    }, [strategy, metrics]);

    return (
        <div className="bg-[#1E293B] rounded-xl border border-[#D946EF]/20 overflow-hidden w-full relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-[#D946EF] to-[#8B5CF6]" />

            <div className="px-5 py-3 border-b border-[#0F172A] flex items-center justify-between">
                <label className="font-semibold text-white text-sm flex items-center gap-2">
                    <span>✨</span>
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#D946EF] to-[#8B5CF6]">
                        AI 전략 분석 리포트
                    </span>
                </label>
            </div>

            <div className="p-5 text-sm">
                {loading ? (
                    <div className="flex items-center gap-3 text-[#94A3B8] animate-pulse">
                        <div className="w-4 h-4 rounded-full border-2 border-t-transparent border-[#D946EF] animate-spin" />
                        <span>AI가 백테스트 결과를 꼼꼼하게 분석 중입니다...</span>
                    </div>
                ) : error || !summary ? (
                    <div className="text-[#EF4444] text-xs">
                        요약 정보를 불러오는 데 실패했습니다. 다시 시도해주세요.
                    </div>
                ) : (
                    <div className="prose prose-sm prose-invert max-w-none prose-p:text-[#CBD5E1] prose-strong:text-white prose-li:text-[#CBD5E1]">
                        <ReactMarkdown>{summary}</ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    );
}

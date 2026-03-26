"use client";

import { useState } from "react";
import type { ParsedStrategy } from "@/lib/types";
import type { WalkForwardResult as WFResult } from "@/lib/api";
import { runWalkForward } from "@/lib/api";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface WalkForwardProps {
  strategy: ParsedStrategy;
}

export default function WalkForwardSection({ strategy }: WalkForwardProps) {
  const { language } = useLanguageStore();
  const [result, setResult] = useState<WFResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const defaultRanges = {
        "leverage": [5, 10],
        "exit.take_profit.value": [1.5, 2.0],
        "exit.stop_loss.value": [-0.3, -0.5],
      };
      const res = await runWalkForward(
        strategy as unknown as Record<string, unknown>,
        defaultRanges,
        30,   // IS 30일
        15,   // OOS 15일
        2,    // 2윈도우 (빠른 분석)
        120,  // 120일 데이터
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Walk-Forward 분석 실패");
    } finally {
      setLoading(false);
    }
  };

  if (!result) {
    if (error) {
      return (
        <div className="w-full py-3 rounded-lg bg-[#0F172A] border border-[#EF444430] text-center">
          <p className="text-xs text-[#EF4444]">{error}</p>
          <button onClick={handleRun} className="mt-2 text-[10px] text-[#94A3B8] underline cursor-pointer">
            {"Retry"}
          </button>
        </div>
      );
    }
    return loading ? (
      <div className="w-full py-3 rounded-lg bg-[#0F172A] border border-[#22D3EE20] text-center">
        <div className="flex items-center justify-center gap-2">
          <svg className="animate-spin h-4 w-4 text-[#22D3EE]" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          <span className="text-xs text-[#22D3EE] animate-pulse">{"Analyzing..."}</span>
        </div>
        <p className="text-[10px] text-[#475569] mt-1">{"Walk-forward analysis in progress"}</p>
      </div>
    ) : (
      <button
        onClick={handleRun}
        className="w-full py-2 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] cursor-pointer hover:border-[#22D3EE50]"
      >
        {"Run Walk-Forward"}
      </button>
    );
  }

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-visible">
      {/* 헤더 + 판정 배지 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#0F172A]">
        <span className="font-semibold text-white text-sm">Walk-Forward Analysis</span>
        <span className={`text-xs px-2 py-0.5 rounded font-bold ${
          result.passed
            ? "bg-[#22C55E15] text-[#22C55E] border border-[#22C55E30]"
            : "bg-[#EF444415] text-[#EF4444] border border-[#EF444430]"
        }`}>
          {result.passed ? "Pass" : "Fail"}
        </span>
      </div>

      {/* 윈도우별 결과 */}
      <div className="px-5 py-3 space-y-2">
        {result.windows.map((w, i) => {
          const isReturn = w.is_metrics?.total_return ?? 0;
          const oosReturn = w.oos_metrics?.total_return ?? 0;
          const ratio = w.ratio ?? 0;
          const maxBar = Math.max(Math.abs(isReturn), Math.abs(oosReturn), 1);

          return (
            <div key={i} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-[#475569]">
                <span>Window {(w as unknown as Record<string, unknown>).window_index as number ?? i + 1}</span>
                <span className={ratio >= 0.5 ? "text-[#22C55E]" : "text-[#EF4444]"}>
                  {(ratio * 100).toFixed(0)}%
                </span>
              </div>
              {/* IS bar */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#475569] w-6">IS</span>
                <div className="flex-1 h-3 bg-[#0F172A] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#22D3EE] rounded-full"
                    style={{ width: `${Math.min(100, (Math.abs(isReturn) / maxBar) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono text-white w-12 text-right">
                  {isReturn.toFixed(1)}%
                </span>
              </div>
              {/* OOS bar */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#475569] w-6">OOS</span>
                <div className="flex-1 h-3 bg-[#0F172A] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${oosReturn >= 0 ? "bg-[#22C55E]" : "bg-[#EF4444]"}`}
                    style={{ width: `${Math.min(100, (Math.abs(oosReturn) / maxBar) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono text-white w-12 text-right">
                  {oosReturn.toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 요약 */}
      <div className="px-5 py-2.5 border-t border-[#0F172A] text-xs text-[#94A3B8]">
        Avg OOS/IS Ratio: <span className="font-mono text-white">{(result.avg_ratio * 100).toFixed(0)}%</span>
        <span className="text-[#475569]"> (50%+ = Pass)</span>
      </div>
    </div>
  );
}

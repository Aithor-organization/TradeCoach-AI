"use client";

import { useState } from "react";
import { useLanguageStore } from "@/stores/languageStore";

// 타임프레임별 추천 기간 (일 단위)
const TIMEFRAME_LIMITS: Record<string, { min: number; max: number; recommended: number; label: string }> = {
  "1m": { min: 7, max: 30, recommended: 14, label: "1 Min" },
  "3m": { min: 14, max: 60, recommended: 30, label: "3 Min" },
  "5m": { min: 14, max: 90, recommended: 30, label: "5 Min" },
  "15m": { min: 30, max: 180, recommended: 90, label: "15 Min" },
  "30m": { min: 60, max: 365, recommended: 180, label: "30 Min" },
  "1h": { min: 90, max: 730, recommended: 365, label: "1 Hour" },
  "4h": { min: 180, max: 1095, recommended: 365, label: "4 Hour" },
  "1d": { min: 365, max: 1825, recommended: 730, label: "1 Day" },
};

interface TimeframePeriodModalProps {
  timeframe: string;
  currentDays: number;
  onConfirm: (days: number) => void;
  onCancel: () => void;
}

export default function TimeframePeriodModal({ timeframe, currentDays, onConfirm, onCancel }: TimeframePeriodModalProps) {
  const { language } = useLanguageStore();
  const limits = TIMEFRAME_LIMITS[timeframe] || TIMEFRAME_LIMITS["1h"];
  const [selectedDays, setSelectedDays] = useState(Math.min(Math.max(limits.recommended, limits.min), limits.max));

  const ko = language === "ko";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] w-full max-w-md mx-4 shadow-2xl">
        {/* 헤더 */}
        <div className="px-6 pt-5 pb-3 border-b border-[#0F172A]">
          <h3 className="text-base font-semibold text-white">
            {ko ? "백테스트 기간 조정" : "Backtest Period Adjustment"}
          </h3>
          <p className="text-[11px] text-[#94A3B8] mt-1">
            {ko
              ? `${limits.label} 봉은 ${limits.min}~${limits.max}일 범위가 적합합니다.`
              : `${limits.label} candles work best with ${limits.min}-${limits.max} day range.`}
          </p>
        </div>

        {/* 경고 메시지 */}
        <div className="px-6 py-3">
          <div className="bg-[#F59E0B]/10 border border-[#F59E0B]/20 rounded-lg px-4 py-3 text-[11px]">
            <div className="flex items-start gap-2">
              <span className="text-[#F59E0B] text-sm mt-0.5">!</span>
              <div>
                <p className="text-[#F59E0B] font-semibold mb-1">
                  {ko ? "기간 불일치 감지" : "Period Mismatch Detected"}
                </p>
                <p className="text-[#94A3B8]">
                  {ko
                    ? `현재 설정: ${currentDays}일 / ${limits.label} 봉의 추천 기간: ${limits.min}~${limits.max}일`
                    : `Current: ${currentDays} days / Recommended for ${limits.label}: ${limits.min}-${limits.max} days`}
                </p>
                {currentDays > limits.max && (
                  <p className="text-[#EF4444] mt-1">
                    {ko
                      ? `${limits.label} 봉으로 ${currentDays}일은 데이터가 너무 많아 처리 시간이 오래 걸리고 과적합 위험이 있습니다.`
                      : `${currentDays} days with ${limits.label} candles is too much data, causing slow processing and overfitting risk.`}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 타임프레임별 추천 기간 테이블 */}
        <div className="px-6 py-2">
          <p className="text-[10px] text-[#475569] font-semibold mb-2 uppercase tracking-wider">
            {ko ? "타임프레임별 추천 기간" : "Recommended Periods by Timeframe"}
          </p>
          <div className="grid grid-cols-4 gap-1 text-[10px]">
            {Object.entries(TIMEFRAME_LIMITS).map(([tf, v]) => (
              <div
                key={tf}
                className={`px-2 py-1.5 rounded text-center ${
                  tf === timeframe
                    ? "bg-[#22D3EE]/10 border border-[#22D3EE]/30 text-[#22D3EE]"
                    : "bg-[#0F172A] text-[#475569]"
                }`}
              >
                <div className="font-semibold">{v.label}</div>
                <div>{v.min}-{v.max}{ko ? "일" : "d"}</div>
              </div>
            ))}
          </div>
        </div>

        {/* 슬라이더 */}
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-[#475569]">
              {ko ? "백테스트 기간" : "Backtest Period"}
            </span>
            <span className="text-sm font-mono font-semibold text-[#22D3EE]">
              {selectedDays}{ko ? "일" : " days"}
            </span>
          </div>
          <input
            type="range"
            min={limits.min}
            max={limits.max}
            value={selectedDays}
            onChange={e => setSelectedDays(Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, #22D3EE 0%, #22D3EE ${((selectedDays - limits.min) / (limits.max - limits.min)) * 100}%, #0F172A ${((selectedDays - limits.min) / (limits.max - limits.min)) * 100}%, #0F172A 100%)`,
            }}
          />
          <div className="flex justify-between text-[9px] text-[#475569] mt-1">
            <span>{limits.min}{ko ? "일" : "d"}</span>
            <span className="text-[#22D3EE]">{ko ? "추천" : "Rec"}: {limits.recommended}{ko ? "일" : "d"}</span>
            <span>{limits.max}{ko ? "일" : "d"}</span>
          </div>
          <p className="text-[9px] text-[#475569] mt-2">
            {(() => {
              const tfMinutes: Record<string, number> = { "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440 };
              const mins = tfMinutes[timeframe] || 60;
              const bars = Math.round(selectedDays * 24 * 60 / mins);
              return ko
                ? `약 ${bars.toLocaleString()}개 봉으로 백테스트를 실행합니다.`
                : `Approximately ${bars.toLocaleString()} candles will be tested.`;
            })()}
          </p>
        </div>

        {/* 버튼 */}
        <div className="flex gap-2 px-6 pb-5">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 text-xs font-medium text-[#94A3B8] rounded-lg bg-[#0F172A] hover:bg-[#1E293B] transition"
          >
            {ko ? "취소" : "Cancel"}
          </button>
          <button
            onClick={() => onConfirm(selectedDays)}
            className="flex-1 py-2.5 text-xs font-semibold text-white rounded-lg bg-[#22D3EE] hover:bg-[#06B6D4] transition"
          >
            {ko ? `${selectedDays}일로 백테스트 실행` : `Run with ${selectedDays} days`}
          </button>
        </div>
      </div>
    </div>
  );
}

// 기간이 타임프레임에 적합한지 검사
export function isPeriodAppropriate(timeframe: string, days: number): boolean {
  const limits = TIMEFRAME_LIMITS[timeframe];
  if (!limits) return true;
  return days >= limits.min && days <= limits.max;
}

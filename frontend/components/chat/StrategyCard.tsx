"use client";

import type { ParsedStrategy } from "@/lib/types";

interface StrategyCardProps {
  strategy: ParsedStrategy;
  onRunBacktest?: () => void;
  onEdit?: () => void;
  onSave?: () => void;
  isSaving?: boolean;
  isSaved?: boolean;
}

export default function StrategyCard({ strategy, onRunBacktest, onEdit, onSave, isSaving, isSaved }: StrategyCardProps) {
  const tp = strategy.exit?.take_profit;
  const sl = strategy.exit?.stop_loss;
  const pos = strategy.position;

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden max-w-md">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#0F172A]">
        <div className="flex items-center gap-2">
          <span className="text-base">📊</span>
          <span className="font-semibold text-white text-sm">{strategy.name}</span>
        </div>
        <span className="font-mono text-xs text-[#475569]">v{strategy.version}</span>
      </div>

      {/* 진입 조건 */}
      <div className="px-5 py-3 border-b border-[#0F172A]">
        <p className="text-xs text-[#475569] mb-1.5">진입 조건</p>
        {strategy.entry?.conditions?.map((cond, i) => (
          <div key={i} className="flex items-center gap-1.5 text-sm text-[#94A3B8]">
            <span className="text-[#22D3EE]">├</span>
            <span>{cond.description || `${cond.indicator} ${cond.operator} ${cond.value}${cond.unit === "percent" ? "%" : ""}`}</span>
          </div>
        ))}
        {strategy.entry?.logic && (
          <div className="flex items-center gap-1.5 text-sm text-[#475569]">
            <span className="text-[#22D3EE]">└</span>
            <span>로직: {strategy.entry.logic}</span>
          </div>
        )}
      </div>

      {/* 익절/손절/포지션 */}
      <div className="grid grid-cols-3 divide-x divide-[#0F172A] border-b border-[#0F172A]">
        <div className="px-4 py-3 text-center">
          <p className="text-xs text-[#475569] mb-1">익절</p>
          <p className="font-mono text-sm font-bold text-[#22C55E]">
            +{tp?.value ?? 0}%
            {tp?.partial?.enabled && " (절반)"}
          </p>
        </div>
        <div className="px-4 py-3 text-center">
          <p className="text-xs text-[#475569] mb-1">손절</p>
          <p className="font-mono text-sm font-bold text-[#EF4444]">
            {sl?.value ?? 0}%
          </p>
        </div>
        <div className="px-4 py-3 text-center">
          <p className="text-xs text-[#475569] mb-1">포지션</p>
          <p className="font-mono text-sm font-bold text-[#22D3EE]">
            ${pos?.size_value ?? 0} × {pos?.max_positions ?? 1}
          </p>
        </div>
      </div>

      {/* 대상/타임프레임 */}
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-[#0F172A] text-xs text-[#94A3B8]">
        <span>대상: <span className="font-mono text-white">{strategy.target_pair}</span></span>
        <span>타임프레임: <span className="font-mono text-white">{strategy.timeframe}</span></span>
      </div>

      {/* 액션 버튼 */}
      {(onRunBacktest || onEdit || onSave) && (
        <div className="flex gap-2 px-5 py-3">
          {onSave && !isSaved && (
            <button
              onClick={onSave}
              disabled={isSaving}
              className="flex-1 py-2 text-xs font-semibold rounded-lg gradient-accent text-[#0A0F1C] cursor-pointer hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? "저장 중..." : "전략 저장"}
            </button>
          )}
          {isSaved && (
            <span className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#22C55E15] text-[#22C55E] text-center border border-[#22C55E30]">
              저장 완료
            </span>
          )}
          {onRunBacktest && (
            <button
              onClick={onRunBacktest}
              className="flex-1 py-2 text-xs font-semibold rounded-lg gradient-accent text-[#0A0F1C] cursor-pointer hover:opacity-90 transition-opacity"
            >
              백테스트 실행
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] cursor-pointer hover:border-[#22D3EE50] transition-colors"
            >
              전략 수정
            </button>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import type { ParsedStrategy } from "@/lib/types";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface StrategyCardProps {
  strategy: ParsedStrategy;
  onRunBacktest?: () => void;
  onEdit?: () => void;
  onSave?: () => void;
  isSaving?: boolean;
  isSaved?: boolean;
  investmentAmount?: number;
  onInvestmentChange?: (amount: number) => void;
}

function Tooltip({ text }: { text: string }) {
  return (
    <span className="relative group/tip inline-flex ml-1 cursor-help">
      <span className="w-3.5 h-3.5 rounded-full bg-[#475569]/30 text-[#94A3B8] text-[9px] font-bold inline-flex items-center justify-center leading-none">?</span>
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 rounded-md bg-[#0F172A] border border-[#22D3EE30] text-[10px] text-[#94A3B8] whitespace-nowrap opacity-0 pointer-events-none group-hover/tip:opacity-100 transition-opacity z-10 shadow-lg">
        {text}
      </span>
    </span>
  );
}

export default function StrategyCard({ strategy, onRunBacktest, onEdit, onSave, isSaving, isSaved, investmentAmount, onInvestmentChange }: StrategyCardProps) {
  const { language } = useLanguageStore();
  const tp = strategy.exit?.take_profit;
  const sl = strategy.exit?.stop_loss;
  const pos = strategy.position;
  const displayAmount = investmentAmount ?? pos?.size_value ?? 1000;

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden w-full">
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
        <div className="flex items-center mb-1.5">
          <p className="text-xs text-[#475569]">{t("sc.entryConditions", language)}</p>
          <Tooltip text={t("sc.entryTooltip", language)} />
        </div>
        {strategy.entry?.conditions?.map((cond, i) => (
          <div key={i} className="flex items-center gap-1.5 text-sm text-[#94A3B8]">
            <span className="text-[#22D3EE]">├</span>
            <span>{cond.description || `${cond.indicator} ${cond.operator} ${cond.value}${cond.unit === "percent" ? "%" : ""}`}</span>
          </div>
        ))}
        {strategy.entry?.logic && (
          <div className="flex items-center gap-1.5 text-sm text-[#475569]">
            <span className="text-[#22D3EE]">└</span>
            <span>{t("sc.logic", language) + " "}{strategy.entry.logic}</span>
          </div>
        )}
      </div>

      {/* 익절/손절/투자금 */}
      <div className="grid grid-cols-3 divide-x divide-[#0F172A] border-b border-[#0F172A]">
        <div className="px-4 py-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <p className="text-xs text-[#475569]">{t("sc.takeProfit", language)}</p>
            <Tooltip text={t("sc.takeProfitTooltip", language)} />
          </div>
          <p className="font-mono text-sm font-bold text-[#22C55E]">
            +{tp?.value ?? 0}%
            {tp?.partial?.enabled && ` ${t("sc.half", language)}`}
          </p>
        </div>
        <div className="px-4 py-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <p className="text-xs text-[#475569]">{t("sc.stopLoss", language)}</p>
            <Tooltip text={t("sc.stopLossTooltip", language)} />
          </div>
          <p className="font-mono text-sm font-bold text-[#EF4444]">
            {sl?.value ?? 0}%
          </p>
        </div>
        <div className="px-4 py-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <p className="text-xs text-[#475569]">{t("sc.investment", language)}</p>
            <Tooltip text={t("sc.investmentTooltip", language)} />
          </div>
          <p className="font-mono text-sm font-bold text-[#22D3EE]">
            ${displayAmount.toLocaleString()}
          </p>
        </div>
      </div>

      {/* 투자금 직접 입력 */}
      {onInvestmentChange && (
        <div className="px-5 py-3 border-b border-[#0F172A]">
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#475569] flex-shrink-0">{t("sc.investmentSetting", language)}</label>
            <div className="flex items-center gap-1.5 flex-1">
              <span className="text-xs text-[#94A3B8]">$</span>
              <input
                type="number"
                value={displayAmount}
                onChange={e => {
                  const val = parseFloat(e.target.value);
                  if (!isNaN(val) && val > 0) onInvestmentChange(val);
                }}
                min={1}
                step={100}
                className="flex-1 bg-[#0F172A] text-white text-sm font-mono rounded-lg px-3 py-1.5 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none w-full min-w-0"
              />
            </div>
          </div>
        </div>
      )}

      {/* 대상/타임프레임 */}
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-[#0F172A] text-xs text-[#94A3B8]">
        <span className="flex items-center">
          {t("sc.target", language)} <span className="font-mono text-white ml-1">{strategy.target_pair}</span>
          <Tooltip text={t("sc.targetTooltip", language)} />
        </span>
        <span className="flex items-center">
          {t("sc.timeframe", language)} <span className="font-mono text-white ml-1">{strategy.timeframe}</span>
          <Tooltip text={t("sc.timeframeTooltip", language)} />
        </span>
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
              {isSaving ? t("sc.saving", language) : t("sc.saveStrategy", language)}
            </button>
          )}
          {isSaved && (
            <span className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#22C55E15] text-[#22C55E] text-center border border-[#22C55E30]">
              {t("sc.saved", language)}
            </span>
          )}
          {onRunBacktest && (
            <button
              onClick={onRunBacktest}
              className="flex-1 py-2 text-xs font-semibold rounded-lg gradient-accent text-[#0A0F1C] cursor-pointer hover:opacity-90 transition-opacity"
            >
              {t("sc.runBacktest", language)}
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] cursor-pointer hover:border-[#22D3EE50] transition-colors"
            >
              {t("sc.editStrategy", language)}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

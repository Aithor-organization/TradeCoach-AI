"use client";

import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import PortalTooltip from "@/components/common/PortalTooltip";

interface SignalIndicatorProps {
  signal: "long" | "short" | "wait" | "BUY_LONG" | "SELL_SHORT" | null;
  strength?: number;
}

const SIGNAL_CONFIG = {
  long: {
    icon: "arrow_upward",
    color: "text-[#22C55E]",
    bg: "bg-[#22C55E]/10",
    border: "border-[#22C55E]/30",
    pulse: "animate-pulse",
  },
  short: {
    icon: "arrow_downward",
    color: "text-[#EF4444]",
    bg: "bg-[#EF4444]/10",
    border: "border-[#EF4444]/30",
    pulse: "animate-pulse",
  },
  wait: {
    icon: "hourglass_empty",
    color: "text-[#F59E0B]",
    bg: "bg-[#F59E0B]/10",
    border: "border-[#F59E0B]/30",
    pulse: "",
  },
};

export default function SignalIndicator({ signal, strength }: SignalIndicatorProps) {
  const { language } = useLanguageStore();

  if (!signal) {
    return (
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-3 text-center">
        <p className="text-xs text-[#475569]">{t("td.noSignal", language)}</p>
      </div>
    );
  }

  // 4종 신호를 기존 표시로 매핑
  const normalizedSignal = signal === "BUY_LONG" ? "long" : signal === "SELL_SHORT" ? "short" : signal;
  const config = SIGNAL_CONFIG[normalizedSignal as keyof typeof SIGNAL_CONFIG] || SIGNAL_CONFIG.wait;
  const label = normalizedSignal === "long"
    ? t("td.signalLong", language)
    : normalizedSignal === "short"
      ? t("td.signalShort", language)
      : t("td.signalWait", language);

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} p-3 ${config.pulse}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-xl ${config.color}`}>
            {normalizedSignal === "long" ? "▲" : normalizedSignal === "short" ? "▼" : "◆"}
          </span>
          <div>
            <p className={`text-sm font-bold ${config.color}`}>{label}</p>
            <p className="text-[10px] text-[#475569] flex items-center">Signal <PortalTooltip text={language === "ko" ? "전략 조건에 의해 자동 생성된 진입 신호. Long=매수, Short=매도, Wait=대기" : "Auto-generated entry signal from strategy conditions. Long=buy, Short=sell, Wait=standby"} /></p>
          </div>
        </div>
        {strength != null && (
          <div className="text-right">
            <p className={`text-sm font-mono font-bold ${config.color}`}>
              {(strength * 100).toFixed(0)}%
            </p>
            <p className="text-[10px] text-[#475569]">{t("td.strength", language)}</p>
          </div>
        )}
      </div>
    </div>
  );
}

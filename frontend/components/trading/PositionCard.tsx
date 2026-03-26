"use client";

import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import PortalTooltip from "@/components/common/PortalTooltip";

interface PositionCardProps {
  position: {
    side: string;
    entry_price: number;
    quantity: number;
    leverage: number;
  } | null;
  balance: number;
  unrealizedPnl: number;
}

export default function PositionCard({ position, balance, unrealizedPnl }: PositionCardProps) {
  const { language } = useLanguageStore();

  return (
    <div className="grid grid-cols-2 gap-3">
      {/* 포지션 */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-4">
        <p className="text-xs text-[#475569] mb-2 flex items-center">{t("td.position", language)} <PortalTooltip text={language === "ko" ? "현재 진입된 포지션. Long=가격 상승 시 수익, Short=가격 하락 시 수익" : "Current open position. Long=profit on price up, Short=profit on price down"} /></p>
        {position ? (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-bold ${position.side === "long" ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                {position.side.toUpperCase()}
              </span>
              <span className="text-xs text-[#F59E0B]">{position.leverage}x</span>
            </div>
            <p className="text-xs text-[#94A3B8]">
              @ <span className="font-mono text-white">${position.entry_price.toLocaleString()}</span>
            </p>
            <p className={`text-sm font-mono font-bold ${unrealizedPnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
              {unrealizedPnl >= 0 ? "+" : ""}${unrealizedPnl.toFixed(2)}
            </p>
          </div>
        ) : (
          <p className="text-sm text-[#475569]">{t("td.noPosition", language)}</p>
        )}
      </div>

      {/* 잔고 */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-4">
        <p className="text-xs text-[#475569] mb-2 flex items-center">{t("td.balance", language)} <PortalTooltip text={language === "ko" ? "현재 가용 잔고 (USDT). 수수료와 실현 손익이 반영됩니다" : "Available balance (USDT). Reflects fees and realized P&L"} /></p>
        <p className="text-lg font-mono font-bold text-[#22D3EE]">
          ${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </p>
        {position && (
          <p className="text-xs text-[#475569] mt-1">
            Margin: <span className="font-mono text-white">
              ${(position.entry_price * position.quantity / position.leverage).toFixed(2)}
            </span>
          </p>
        )}
      </div>
    </div>
  );
}

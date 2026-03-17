"use client";

import type { BacktestResult as BacktestResultType } from "@/lib/types";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface BacktestResultProps {
  result: BacktestResultType;
}

export default function BacktestResult({ result }: BacktestResultProps) {
  const { metrics } = result;
  const { language } = useLanguageStore();

  const getReturnColor = (val: number) => val >= 0 ? "text-[#22C55E]" : "text-[#EF4444]";
  const getMddStatus = (mdd: number) => {
    const absMdd = Math.abs(mdd);
    if (absMdd > 30) return { color: "text-[#EF4444]", label: t("bt.risk", language) };
    if (absMdd > 20) return { color: "text-[#EAB308]", label: t("bt.caution", language) };
    return { color: "text-[#22C55E]", label: t("bt.safe", language) };
  };
  const getSharpeStatus = (sr: number) => {
    if (sr > 1.0) return { color: "text-[#22C55E]", label: t("bt.good", language) };
    if (sr > 0.5) return { color: "text-[#EAB308]", label: t("bt.moderate", language) };
    return { color: "text-[#EF4444]", label: t("bt.insufficient", language) };
  };

  const mddStatus = getMddStatus(metrics.max_drawdown);
  const sharpeStatus = getSharpeStatus(metrics.sharpe_ratio);

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden max-w-md">
      {/* 헤더 */}
      <div className="px-5 py-3 border-b border-[#0F172A]">
        <span className="font-semibold text-white text-sm">{"📈 " + t("bt.title", language)}</span>
      </div>

      {/* 지표 그리드 */}
      <div className="grid grid-cols-2 gap-px bg-[#0F172A]">
        <MetricCell
          label={t("bt.totalReturn", language)}
          value={`${metrics.total_return > 0 ? "+" : ""}${metrics.total_return}%`}
          valueClass={getReturnColor(metrics.total_return)}
          badge={t("bt.finalReturn", language)}
        />
        <MetricCell
          label={t("bt.mdd", language)}
          value={`${metrics.max_drawdown}%`}
          valueClass={mddStatus.color}
          badge={mddStatus.label}
        />
        <MetricCell
          label="Sharpe Ratio"
          value={`${metrics.sharpe_ratio}`}
          valueClass={sharpeStatus.color}
          badge={sharpeStatus.label}
        />
        <MetricCell
          label={t("bt.winRate", language)}
          value={`${metrics.win_rate}%`}
          valueClass="text-white"
        />
      </div>

      {/* 거래 수 + 초기자본 */}
      <div className="px-5 py-2.5 border-t border-[#0F172A] flex items-center justify-center gap-3">
        <span className="text-xs text-[#475569]">
          {t("bt.total", language)} <span className="font-mono text-white">{metrics.total_trades}</span> {t("bt.trades", language)}
        </span>
        <span className="text-[#1E293B]">|</span>
        <span className="text-xs text-[#475569]">
          {t("bt.initCapital", language)} <span className="font-mono text-[#22D3EE]">${metrics.init_cash?.toLocaleString() ?? "1,000"}</span>
        </span>
      </div>
    </div>
  );
}

function MetricCell({ label, value, valueClass, badge }: {
  label: string;
  value: string;
  valueClass: string;
  badge?: string;
}) {
  return (
    <div className="bg-[#1E293B] px-5 py-3">
      <p className="text-xs text-[#475569] mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <span className={`font-mono text-lg font-bold ${valueClass}`}>{value}</span>
        {badge && (
          <span className={`text-xs px-1.5 py-0.5 rounded ${valueClass} bg-current/10`}>
            {badge}
          </span>
        )}
      </div>
    </div>
  );
}

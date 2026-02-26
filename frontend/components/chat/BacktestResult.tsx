"use client";

import type { BacktestResult as BacktestResultType } from "@/lib/types";

interface BacktestResultProps {
  result: BacktestResultType;
}

export default function BacktestResult({ result }: BacktestResultProps) {
  const { metrics } = result;

  const getReturnColor = (val: number) => val >= 0 ? "text-[#22C55E]" : "text-[#EF4444]";
  const getMddStatus = (mdd: number) => {
    const absMdd = Math.abs(mdd);
    if (absMdd > 30) return { color: "text-[#EF4444]", label: "위험" };
    if (absMdd > 20) return { color: "text-[#EAB308]", label: "주의" };
    return { color: "text-[#22C55E]", label: "적정" };
  };
  const getSharpeStatus = (sr: number) => {
    if (sr > 1.0) return { color: "text-[#22C55E]", label: "양호" };
    if (sr > 0.5) return { color: "text-[#EAB308]", label: "보통" };
    return { color: "text-[#EF4444]", label: "부족" };
  };

  const mddStatus = getMddStatus(metrics.max_drawdown);
  const sharpeStatus = getSharpeStatus(metrics.sharpe_ratio);

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden max-w-md">
      {/* 헤더 */}
      <div className="px-5 py-3 border-b border-[#0F172A]">
        <span className="font-semibold text-white text-sm">📈 백테스트 결과</span>
      </div>

      {/* 지표 그리드 */}
      <div className="grid grid-cols-2 gap-px bg-[#0F172A]">
        <MetricCell
          label="총 수익률"
          value={`${metrics.total_return > 0 ? "+" : ""}${metrics.total_return}%`}
          valueClass={getReturnColor(metrics.total_return)}
          badge="최종 수익률"
        />
        <MetricCell
          label="최대 낙폭 (MDD)"
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
          label="승률"
          value={`${metrics.win_rate}%`}
          valueClass="text-white"
        />
      </div>

      {/* 거래 수 */}
      <div className="px-5 py-2.5 border-t border-[#0F172A] text-center">
        <span className="text-xs text-[#475569]">
          총 <span className="font-mono text-white">{metrics.total_trades}</span>회 거래
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

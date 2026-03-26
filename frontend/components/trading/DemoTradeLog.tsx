"use client";

import type { DemoTrade } from "@/lib/tradingApi";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface DemoTradeLogProps {
  trades: DemoTrade[];
}

export default function DemoTradeLog({ trades }: DemoTradeLogProps) {
  const { language } = useLanguageStore();

  if (trades.length === 0) {
    return (
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-4">
        <p className="text-xs text-[#475569] text-center">{t("td.noTrades", language)}</p>
      </div>
    );
  }

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#0F172A]">
        <span className="text-xs font-semibold text-white">{t("td.tradeLog", language)}</span>
      </div>
      <div className="max-h-60 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="text-[#475569] border-b border-[#0F172A] sticky top-0 bg-[#1E293B]">
            <tr>
              <th className="py-1.5 px-3 text-left">#</th>
              <th className="py-1.5 px-3 text-left">Side</th>
              <th className="py-1.5 px-3 text-right">PnL</th>
              <th className="py-1.5 px-3 text-right">Reason</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, i) => (
              <tr key={i} className="border-b border-[#0F172A]/30 text-[#94A3B8]">
                <td className="py-1.5 px-3 font-mono">{trades.length - i}</td>
                <td className="py-1.5 px-3">
                  <span className={`font-semibold ${trade.side === "long" ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                    {trade.side.toUpperCase()}
                  </span>
                </td>
                <td className={`py-1.5 px-3 text-right font-mono ${trade.pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                  {trade.pnl >= 0 ? "+" : ""}{trade.pnl.toFixed(2)}
                </td>
                <td className="py-1.5 px-3 text-right text-[10px]">{trade.exit_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

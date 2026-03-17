"use client";

import type { TradeRecord } from "@/lib/types";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface TradeLogTableProps {
    trades?: TradeRecord[];
}

export default function TradeLogTable({ trades }: TradeLogTableProps) {
    if (!trades || trades.length === 0) return null;
    const { language } = useLanguageStore();

    return (
        <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden w-full mt-4">
            <div className="px-5 py-3 border-b border-[#0F172A]">
                <span className="font-semibold text-white text-sm">{"📋 " + t("tl.title", language)}</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-[#94A3B8]">
                    <thead className="bg-[#0F172A] text-[#475569]">
                        <tr>
                            <th className="px-5 py-3 font-medium">{t("tl.entryDate", language)}</th>
                            <th className="px-5 py-3 font-medium">{t("tl.exitDate", language)}</th>
                            <th className="px-5 py-3 font-medium text-right">{t("tl.pnl", language)}</th>
                            <th className="px-5 py-3 font-medium text-right">{t("tl.returnPct", language)}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#0F172A]">
                        {trades.map((trade, idx) => (
                            <tr key={idx} className="hover:bg-[#0F172A]/50 transition-colors">
                                <td className="px-5 py-3 font-mono">
                                    {new Date(Number(trade.entry_date) * 1000).toLocaleString(language === "en" ? "en-US" : "ko-KR", {
                                        year: '2-digit', month: '2-digit', day: '2-digit',
                                        hour: '2-digit', minute: '2-digit'
                                    })}
                                </td>
                                <td className="px-5 py-3 font-mono">
                                    {new Date(Number(trade.exit_date) * 1000).toLocaleString(language === "en" ? "en-US" : "ko-KR", {
                                        year: '2-digit', month: '2-digit', day: '2-digit',
                                        hour: '2-digit', minute: '2-digit'
                                    })}
                                </td>
                                <td className={`px-5 py-3 font-mono font-bold text-right ${trade.pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                                    {trade.pnl > 0 ? "+" : ""}{trade.pnl.toFixed(2)}
                                </td>
                                <td className={`px-5 py-3 font-mono font-bold text-right ${trade.return_pct >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                                    {trade.return_pct > 0 ? "+" : ""}{trade.return_pct.toFixed(2)}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

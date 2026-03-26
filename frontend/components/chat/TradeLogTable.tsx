"use client";

import type { TradeRecord } from "@/lib/types";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface TradeLogTableProps {
    trades?: TradeRecord[];
}

// 날짜 파싱: Unix초, Unix밀리초, ISO문자열, 숫자문자열 모두 처리
function parseTradeDate(val: string | number | undefined): Date {
    if (!val) return new Date(NaN);
    if (typeof val === "string") {
        // ISO 문자열 (2026-01-15T...)
        if (val.includes("T") || val.includes("-")) return new Date(val);
        // 숫자 문자열
        const n = Number(val);
        if (!isNaN(n)) return n > 1e12 ? new Date(n) : new Date(n * 1000);
    }
    if (typeof val === "number") {
        // 밀리초 (13자리+) vs 초 (10자리)
        return val > 1e12 ? new Date(val) : new Date(val * 1000);
    }
    return new Date(NaN);
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
                            <th className="px-5 py-3 font-medium">Side</th>
                            <th className="px-5 py-3 font-medium">{t("tl.entryDate", language)}</th>
                            <th className="px-5 py-3 font-medium">{t("tl.exitDate", language)}</th>
                            <th className="px-5 py-3 font-medium text-right">{t("tl.pnl", language)}</th>
                            <th className="px-5 py-3 font-medium text-right">{t("tl.returnPct", language)}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#0F172A]">
                        {trades.map((trade, idx) => (
                            <tr key={idx} className="hover:bg-[#0F172A]/50 transition-colors">
                                <td className="px-5 py-3">
                                    <span className={`text-xs font-bold ${trade.side === "long" ? "text-[#22C55E]" : trade.side === "short" ? "text-[#EF4444]" : "text-[#94A3B8]"}`}>
                                        {trade.side ? trade.side.toUpperCase() : "-"}
                                    </span>
                                </td>
                                <td className="px-5 py-3 font-mono">
                                    {parseTradeDate(trade.entry_date).toLocaleString(language === "en" ? "en-US" : "ko-KR", {
                                        year: '2-digit', month: '2-digit', day: '2-digit',
                                        hour: '2-digit', minute: '2-digit'
                                    })}
                                </td>
                                <td className="px-5 py-3 font-mono">
                                    {parseTradeDate(trade.exit_date).toLocaleString(language === "en" ? "en-US" : "ko-KR", {
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

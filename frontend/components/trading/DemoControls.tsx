"use client";

import { useState, useEffect } from "react";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import PortalTooltip from "@/components/common/PortalTooltip";

interface DemoControlsProps {
  onStart: (config: { symbol: string; leverage: number; balance: number }) => void;
  onStop: () => void;
  onSymbolChange?: (symbol: string) => void;
  isActive: boolean;
  isLoading: boolean;
  defaultSymbol?: string;
  defaultLeverage?: number;
  defaultBalance?: number;
}

export default function DemoControls({ onStart, onStop, onSymbolChange, isActive, isLoading, defaultSymbol, defaultLeverage, defaultBalance }: DemoControlsProps) {
  const { language } = useLanguageStore();
  const [symbol, setSymbol] = useState(defaultSymbol || "SOLUSDT");
  const [leverage, setLeverage] = useState(defaultLeverage || 10);
  const [balance, setBalance] = useState(defaultBalance || 1000);

  // 전략 변경 시 값 동기화
  useEffect(() => { if (defaultSymbol) setSymbol(defaultSymbol); }, [defaultSymbol]);
  useEffect(() => { if (defaultLeverage !== undefined) setLeverage(defaultLeverage); }, [defaultLeverage]);
  useEffect(() => { if (defaultBalance !== undefined) setBalance(defaultBalance); }, [defaultBalance]);

  // 레버리지 옵션: 기본 + 전략 레버리지 포함
  const leverageOptions = Array.from(new Set([1, 2, 3, 5, 10, 20, 50, 100, ...(defaultLeverage ? [defaultLeverage] : [])])).sort((a, b) => a - b);

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-4 space-y-3">
      <h3 className="text-sm font-semibold text-white">{t("td.controls", language)}</h3>

      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-[10px] text-[#475569] flex items-center mb-1">Symbol <PortalTooltip text={language === "ko" ? "거래할 코인 페어를 선택합니다" : "Select the trading pair"} /></label>
          <select
            value={symbol}
            onChange={e => { setSymbol(e.target.value); onSymbolChange?.(e.target.value); }}
            disabled={isActive}
            className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-2 py-1.5 border border-[#47556933] focus:outline-none disabled:opacity-50"
          >
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="SOLUSDT">SOL/USDT</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-[#475569] flex items-center mb-1">Leverage <PortalTooltip text={language === "ko" ? "레버리지 배수. 높을수록 수익/손실이 증폭됩니다. 전략 설정값으로 자동 적용됩니다" : "Leverage multiplier. Higher means amplified gains/losses. Auto-applied from strategy"} /></label>
          <select
            value={leverage}
            onChange={e => setLeverage(Number(e.target.value))}
            disabled={isActive}
            className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-2 py-1.5 border border-[#47556933] focus:outline-none disabled:opacity-50"
          >
            {leverageOptions.map(v => (
              <option key={v} value={v}>{v}x</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-[#475569] flex items-center mb-1">Balance <PortalTooltip text={language === "ko" ? "모의투자 시작 자본금 (USDT). 실제 돈이 아닌 가상 자금입니다" : "Starting capital for paper trading (USDT). Virtual funds, not real money"} /></label>
          <input
            type="number"
            value={balance}
            onChange={e => setBalance(Number(e.target.value))}
            disabled={isActive}
            min={100}
            step={100}
            className="w-full bg-[#0F172A] text-white text-xs font-mono rounded-lg px-2 py-1.5 border border-[#47556933] focus:outline-none disabled:opacity-50"
          />
        </div>
      </div>

      <div className="flex gap-2">
        {!isActive ? (
          <button
            onClick={() => onStart({ symbol, leverage, balance })}
            disabled={isLoading}
            className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#22C55E] text-white cursor-pointer hover:bg-[#16A34A] disabled:opacity-50 transition"
          >
            {isLoading ? "Starting..." : t("td.start", language)}
          </button>
        ) : (
          <button
            onClick={onStop}
            disabled={isLoading}
            className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#EF4444] text-white cursor-pointer hover:bg-[#DC2626] disabled:opacity-50 transition"
          >
            {isLoading ? "Stopping..." : t("td.stop", language)}
          </button>
        )}
      </div>
    </div>
  );
}

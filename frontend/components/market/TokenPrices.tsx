"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getTokenPrices } from "@/lib/api";

const TOKEN_INFO: Record<string, { name: string; ticker: string }> = {
  SOL: { name: "Solana", ticker: "SOL" },
  JUP: { name: "Jupiter", ticker: "JUP" },
  RAY: { name: "Raydium", ticker: "RAY" },
  BONK: { name: "Bonk", ticker: "BONK" },
  WIF: { name: "dogwifhat", ticker: "WIF" },
};

const DISPLAY_ORDER = ["SOL", "JUP", "RAY", "BONK", "WIF"];
const REFRESH_INTERVAL = 30_000;

function formatPrice(price: number): string {
  if (price >= 1) return `$${price.toFixed(2)}`;
  if (price >= 0.001) return `$${price.toFixed(4)}`;
  return `$${price.toFixed(6)}`;
}

export default function TokenPrices() {
  const [prices, setPrices] = useState<Record<string, number | null>>({});
  const [loading, setLoading] = useState(true);
  const prevPrices = useRef<Record<string, number | null>>({});

  const fetchPrices = useCallback(async () => {
    try {
      const data = await getTokenPrices();
      prevPrices.current = prices;
      setPrices(data.prices);
    } catch {
      // 가격 조회 실패 시 기존 값 유지
    } finally {
      setLoading(false);
    }
  }, [prices]);

  useEffect(() => {
    fetchPrices();
    const id = setInterval(fetchPrices, REFRESH_INTERVAL);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-3 overflow-x-auto pb-1">
        {DISPLAY_ORDER.map((sym) => (
          <div key={sym} className="flex-shrink-0 w-32 h-14 rounded-lg bg-[#1E293B] animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 overflow-x-auto pb-1">
      {DISPLAY_ORDER.map((symbol) => {
        const price = prices[symbol];
        const prev = prevPrices.current[symbol];
        const info = TOKEN_INFO[symbol];
        const direction = price && prev ? (price > prev ? "up" : price < prev ? "down" : "same") : "same";

        return (
          <div
            key={symbol}
            className="flex-shrink-0 px-4 py-2.5 rounded-lg bg-[#1E293B] border border-[#22D3EE10] hover:border-[#22D3EE30] transition-colors"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold text-[#94A3B8]">{info.ticker}</span>
            </div>
            <div className={`text-sm font-mono font-bold ${
              direction === "up" ? "text-[#14F195]" : direction === "down" ? "text-[#EF4444]" : "text-white"
            }`}>
              {price != null ? formatPrice(price) : "—"}
              {direction === "up" && <span className="ml-1 text-xs">▲</span>}
              {direction === "down" && <span className="ml-1 text-xs">▼</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

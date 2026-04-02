"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// 트레이딩 신호 마커 타입
export interface TradeMarker {
  time: number; // UNIX timestamp (seconds)
  type: "entry_long" | "entry_short" | "exit_long" | "exit_short";
  label?: string;
}

interface LiveChartProps {
  symbol: string;
  isActive: boolean;
  markers?: TradeMarker[];
}

const BINANCE_KLINES = "https://fapi.binance.com/fapi/v1/klines";
const BINANCE_WS = "wss://fstream.binance.com/ws";

export default function LiveChart({ symbol, isActive, markers }: LiveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<unknown>(null);
  const seriesRef = useRef<unknown>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [wsConnected, setWsConnected] = useState(false);
  const prevCloseRef = useRef<number>(0);

  // 차트 초기화
  useEffect(() => {
    if (!containerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let chart: any = null;
    let mounted = true;

    (async () => {
      const lc = await import("lightweight-charts");
      if (!mounted || !containerRef.current) return;

      containerRef.current.innerHTML = "";

      chart = lc.createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 360,
        layout: {
          background: { color: "#0F172A" },
          textColor: "#94A3B8",
        },
        grid: {
          vertLines: { color: "#1E293B" },
          horzLines: { color: "#1E293B" },
        },
        crosshair: { mode: 0 },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: "#1E293B",
        },
        rightPriceScale: { borderColor: "#1E293B" },
        localization: {
          timeFormatter: (t: number) => {
            const d = new Date(t * 1000);
            return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          },
        },
      });

      const series = chart.addSeries(lc.CandlestickSeries, {
        upColor: "#22C55E",
        downColor: "#EF4444",
        borderDownColor: "#EF4444",
        borderUpColor: "#22C55E",
        wickDownColor: "#EF4444",
        wickUpColor: "#22C55E",
      });

      chartRef.current = chart;
      seriesRef.current = series;

      // 과거 klines 200개 로드
      try {
        const res = await fetch(`${BINANCE_KLINES}?symbol=${symbol}&interval=1m&limit=200`);
        if (res.ok) {
          const klines = await res.json();
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const data = klines.map((k: any) => ({
            time: Math.floor(k[0] / 1000) as number,
            open: parseFloat(k[1]),
            high: parseFloat(k[2]),
            low: parseFloat(k[3]),
            close: parseFloat(k[4]),
          }));
          series.setData(data);

          if (data.length >= 2) {
            const last = data[data.length - 1];
            const prev = data[data.length - 2];
            setCurrentPrice(last.close);
            prevCloseRef.current = prev.close;
            setPriceChange(((last.close - prev.close) / prev.close) * 100);
          }
        }
      } catch {
        // Binance API 실패
      }

      // 리사이즈
      const observer = new ResizeObserver(() => {
        if (containerRef.current && chart) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      observer.observe(containerRef.current);
    })();

    return () => {
      mounted = false;
      if (chart) {
        chart.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, [symbol]);

  // 마커 업데이트: lightweight-charts v5 createSeriesMarkers API
  // 에러 발생해도 차트 자체는 정상 동작하도록 전체를 try-catch로 보호
  const markersRef = useRef<{ destroy: () => void } | null>(null);
  useEffect(() => {
    if (!seriesRef.current) return;

    // 이전 마커 primitive 제거
    try {
      if (markersRef.current) {
        markersRef.current.destroy();
        markersRef.current = null;
      }
    } catch { /* 무시 */ }

    if (!markers || markers.length === 0) return;

    const sorted = [...markers]
      .sort((a, b) => a.time - b.time)
      .map(m => {
        const isEntry = m.type.startsWith("entry");
        const isLong = m.type.includes("long");
        return {
          time: m.time,
          position: isEntry ? (isLong ? "belowBar" : "aboveBar") : (isLong ? "aboveBar" : "belowBar"),
          color: isEntry ? (isLong ? "#22C55E" : "#EF4444") : "#06B6D4",
          shape: isLong ? (isEntry ? "arrowUp" : "arrowDown") : (isEntry ? "arrowDown" : "arrowUp"),
          text: m.label || (isEntry ? (isLong ? "L" : "S") : "X"),
        };
      });

    (async () => {
      try {
        const lc = await import("lightweight-charts");
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const createFn = (lc as any).createSeriesMarkers;
        if (createFn && seriesRef.current) {
          const wrapper = createFn(seriesRef.current, sorted);
          markersRef.current = {
            destroy: () => {
              try { wrapper?.detach?.(); } catch { /* v5 cleanup */ }
              try { wrapper?.setMarkers?.([]); } catch { /* fallback */ }
            },
          };
        }
      } catch {
        // lightweight-charts 마커 API 미지원 — 조용히 무시
      }
    })();
  }, [markers]);

  // Binance WebSocket 실시간 연결
  const connectWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const stream = `${symbol.toLowerCase()}@kline_1m`;
    const ws = new WebSocket(`${BINANCE_WS}/${stream}`);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const k = msg.k;
        if (!k || !seriesRef.current) return;

        const price = parseFloat(k.c);
        setCurrentPrice(price);
        if (prevCloseRef.current > 0) {
          setPriceChange(((price - prevCloseRef.current) / prevCloseRef.current) * 100);
        }

        // 봉이 완성되면 prevClose 갱신
        if (k.x) {
          prevCloseRef.current = price;
        }

        // 차트 업데이트
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (seriesRef.current as any).update({
          time: Math.floor(k.t / 1000) as number,
          open: parseFloat(k.o),
          high: parseFloat(k.h),
          low: parseFloat(k.l),
          close: price,
        });
      } catch {
        // 파싱 실패
      }
    };

    return ws;
  }, [symbol]);

  // WebSocket 연결 관리
  useEffect(() => {
    // 차트가 초기화된 후 약간 지연
    const timer = setTimeout(() => {
      if (seriesRef.current) {
        connectWs();
      }
    }, 500);

    return () => {
      clearTimeout(timer);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
        setWsConnected(false);
      }
    };
  }, [symbol, connectWs]);

  // 심볼 → 표시 이름
  const displaySymbol = symbol.replace("USDT", "/USDT");

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#0F172A]">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-white">{displaySymbol}</span>
          {currentPrice && (
            <span className="text-sm font-mono text-white">
              ${currentPrice < 1 ? currentPrice.toFixed(4) : currentPrice.toFixed(2)}
            </span>
          )}
          {priceChange !== 0 && (
            <span className={`text-[10px] font-mono ${priceChange >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
              {priceChange >= 0 ? "+" : ""}{priceChange.toFixed(2)}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isActive && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#22C55E]/20 text-[#22C55E] animate-pulse">
              TRADING
            </span>
          )}
          <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-[#22C55E]" : "bg-[#475569]"}`} />
          <span className="text-[10px] text-[#475569]">1m</span>
        </div>
      </div>

      {/* 차트 */}
      <div
        ref={containerRef}
        className="w-full [&_a[href*='tradingview']]:!hidden [&_a[target='_blank']]:!hidden"
        style={{ minHeight: 360 }}
      />
    </div>
  );
}

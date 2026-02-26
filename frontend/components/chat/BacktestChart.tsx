"use client";

import { useEffect, useRef } from "react";
import type { EquityPoint, BacktestMetrics } from "@/lib/types";

interface BacktestChartProps {
  equityCurve: EquityPoint[];
  metrics: BacktestMetrics;
}

export default function BacktestChart({ equityCurve, metrics }: BacktestChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || equityCurve.length === 0) return;

    let chart: any;
    let isMounted = true;

    const initChart = async () => {
      const { createChart, AreaSeries } = await import("lightweight-charts");

      if (!isMounted || !chartRef.current) return;

      // 기존 차트 요소가 있다면 초기화 (React Strict Mode 중복 방지)
      chartRef.current.innerHTML = "";

      chart = createChart(chartRef.current, {
        width: chartRef.current!.clientWidth,
        height: 260,
        layout: {
          background: { color: "#0F172A" },
          textColor: "#94A3B8",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#1E293B" },
          horzLines: { color: "#1E293B" },
        },
        crosshair: {
          vertLine: { color: "#22D3EE50", labelBackgroundColor: "#1E293B" },
          horzLine: { color: "#22D3EE50", labelBackgroundColor: "#1E293B" },
        },
        timeScale: { borderColor: "#1E293B" },
        rightPriceScale: { borderColor: "#1E293B" },
      });

      const series = chart.addSeries(AreaSeries, {
        lineColor: "#22D3EE",
        topColor: "rgba(34, 211, 238, 0.3)",
        bottomColor: "rgba(34, 211, 238, 0.0)",
        lineWidth: 2,
      });

      const data = equityCurve.map((p) => ({
        time: p.date as any,
        value: p.value,
      }));

      series.setData(data);
      chart.timeScale().fitContent();
    };

    initChart();

    const handleResize = () => {
      if (chart && chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      isMounted = false;
      window.removeEventListener("resize", handleResize);
      if (chart) {
        chart.remove();
      }
    };
  }, [equityCurve]);

  const getColor = (val: number) => (val >= 0 ? "text-[#22C55E]" : "text-[#EF4444]");

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden w-full">
      <div className="px-5 py-3 border-b border-[#0F172A] flex items-center justify-between">
        <span className="font-semibold text-white text-sm">📈 백테스트 결과</span>
        <div className="flex items-center gap-1.5">
          <span className={`text-xs font-mono font-bold ${getColor(metrics.total_return)}`}>
            {metrics.total_return > 0 ? "+" : ""}{metrics.total_return}%
          </span>
          <span className="text-[10px] text-[#475569] bg-[#0F172A] px-1.5 py-0.5 rounded border border-[#1E293B]">
            최종 수익률
          </span>
        </div>
      </div>

      {/* 차트 영역 */}
      <div ref={chartRef} className="w-full" />

      {/* 지표 그리드 */}
      <div className="grid grid-cols-4 gap-px bg-[#0F172A]">
        <Metric label="MDD" value={`${metrics.max_drawdown}%`} color="text-[#EF4444]" />
        <Metric label="Sharpe" value={`${metrics.sharpe_ratio}`} color="text-[#22D3EE]" />
        <Metric label="승률" value={`${metrics.win_rate}%`} color="text-white" />
        <Metric label="거래" value={`${metrics.total_trades}회`} color="text-white" />
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-[#1E293B] px-3 py-2 text-center">
      <p className="text-[10px] text-[#475569]">{label}</p>
      <span className={`font-mono text-sm font-bold ${color}`}>{value}</span>
    </div>
  );
}

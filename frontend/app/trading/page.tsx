"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

const LiveChart = dynamic(() => import("@/components/trading/LiveChart"), { ssr: false });
import AuthGuard from "@/components/common/AuthGuard";
import DemoControls from "@/components/trading/DemoControls";
import PositionCard from "@/components/trading/PositionCard";
import DemoTradeLog from "@/components/trading/DemoTradeLog";
import SignalIndicator from "@/components/trading/SignalIndicator";
import { startDemo, stopDemo, getDemoStatus } from "@/lib/tradingApi";
import type { DemoTrade, DemoStatus, SignalRecording } from "@/lib/tradingApi";
import { getStrategies, publishToMarketplace } from "@/lib/api";
import { getStrategyPerformance, getStrategyTxHistory } from "@/lib/blockchainApi";
import type { StrategyPerformance, OnchainTxRecord } from "@/lib/blockchainApi";
import type { Strategy } from "@/lib/types";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

export default function TradingPage() {
  const { language } = useLanguageStore();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [trades, setTrades] = useState<DemoTrade[]>([]);
  const [signal, setSignal] = useState<"long" | "short" | "wait" | null>(null);
  const [symbol, setSymbol] = useState("SOLUSDT");
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [loadingStrategies, setLoadingStrategies] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [signalRecording, setSignalRecording] = useState<SignalRecording | null>(null);
  const [onchainPerf, setOnchainPerf] = useState<StrategyPerformance | null>(null);
  const [onchainTxs, setOnchainTxs] = useState<OnchainTxRecord[]>([]);
  const [loadingTxs, setLoadingTxs] = useState(false);
  const [showStopModal, setShowStopModal] = useState(false);
  const [publishing, setPublishing] = useState(false);

  // 전략 목록 로드
  useEffect(() => {
    (async () => {
      try {
        const res = await getStrategies() as { strategies: Strategy[] };
        const list = res?.strategies || [];
        setStrategies(list);
        const minted = list.filter(s => s.status === "verified");
        if (minted.length > 0) setSelectedStrategy(minted[0]);
        else if (list.length > 0) setSelectedStrategy(list[0]);
      } catch { /* 로그인 안 된 경우 */ }
      finally { setLoadingStrategies(false); }
    })();
  }, []);

  // 선택된 전략의 온체인 TX 히스토리 로드 (Solana에서 직접 조회)
  useEffect(() => {
    if (!selectedStrategy?.id) return;
    setLoadingTxs(true);
    (async () => {
      try {
        // 인메모리 성과 (있으면)
        const perf = await getStrategyPerformance(selectedStrategy.id);
        if (perf && perf.total_trades > 0) setOnchainPerf(perf);
        else setOnchainPerf(null);
      } catch { setOnchainPerf(null); }

      try {
        // 온체인 TX 히스토리 (서버 재시작 무관)
        const txResult = await getStrategyTxHistory(selectedStrategy.id);
        setOnchainTxs(txResult.transactions || []);
      } catch { setOnchainTxs([]); }
      finally { setLoadingTxs(false); }
    })();
  }, [selectedStrategy?.id]);

  // 상태 폴링 (2초 간격)
  const pollStatus = useCallback(async (sid: string) => {
    try {
      const s = await getDemoStatus(sid) as DemoStatus & { last_signal?: string; current_price?: number; trades?: DemoTrade[] };
      setStatus(s);
      if (s.trades && s.trades.length > 0) {
        setTrades(s.trades);
      }
      if (s.position) {
        setSignal(s.position.side as "long" | "short");
      } else if (s.last_signal) {
        setSignal(s.last_signal as "long" | "short" | "wait");
      } else {
        setSignal("wait");
      }
    } catch {
      // 세션 종료 시 폴링 중지
    }
  }, []);

  useEffect(() => {
    if (isActive && sessionId) {
      pollingRef.current = setInterval(() => pollStatus(sessionId), 2000);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [isActive, sessionId, pollStatus]);

  const handleStart = async (config: { symbol: string; leverage: number; balance: number }) => {
    setIsLoading(true);
    try {
      const session = await startDemo({
        symbol: config.symbol,
        leverage: config.leverage,
        initial_balance: config.balance,
        parsed_strategy: selectedStrategy?.parsed_strategy as unknown as Record<string, unknown>,
        strategy_nft_id: selectedStrategy?.id,
      });
      setSessionId(session.session_id);
      setIsActive(true);
      setTrades([]);
      setStatus(null);
      setSignal("wait");
      setSymbol(config.symbol);
      setSignalRecording(null);
    } catch {
      // 에러
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopClick = () => {
    setShowStopModal(true);
  };

  const handleStop = async (mode: "test" | "verify") => {
    if (!sessionId) return;
    setShowStopModal(false);
    setIsLoading(true);
    try {
      const result = await stopDemo(sessionId, mode);
      setTrades(result.trades);
      setIsActive(false);
      if (result.signal_recording) {
        setSignalRecording(result.signal_recording);
      }
      if (selectedStrategy?.id) {
        try {
          const perf = await getStrategyPerformance(selectedStrategy.id);
          if (perf && perf.total_trades > 0) setOnchainPerf(perf);
        } catch { /* 무시 */ }
        // 2초 후 온체인 TX 갱신 (TX 확인 대기)
        setTimeout(async () => {
          try {
            const txResult = await getStrategyTxHistory(selectedStrategy.id);
            setOnchainTxs(txResult.transactions || []);
          } catch { /* 무시 */ }
        }, 3000);
      }
    } catch {
      // 에러
    } finally {
      setIsLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedStrategy?.id) return;
    setPublishing(true);
    try {
      const result = await publishToMarketplace(selectedStrategy.id);
      const txInfo = result.blockchain?.tx_signature
        ? `\nTX: ${result.blockchain.tx_signature.slice(0, 20)}...`
        : "";
      alert((language === "ko" ? "마켓플레이스에 등록되었습니다!" : "Published to marketplace!") + txInfo);
    } catch (e) {
      alert(`Failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-[#0A0F1C] text-white">
        {/* 헤더 */}
        <header className="h-14 flex items-center px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-base font-bold">TradeCoach</span>
              <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">AI</span>
            </Link>
            <span className="text-[#475569]">/</span>
            <span className="text-sm text-white">{t("td.title", language)}</span>
            {isActive && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#22C55E]/20 text-[#22C55E] animate-pulse">
                LIVE
              </span>
            )}
          </div>
        </header>

        {/* 메인 레이아웃 */}
        <div className="flex flex-1 overflow-hidden" style={{ height: "calc(100vh - 56px)" }}>
          {/* 민팅된 전략만 필터 */}
          {(() => {
            const mintedStrategies = strategies.filter(s => s.status === "verified");
            const hasNoMinted = !loadingStrategies && mintedStrategies.length === 0;
            return hasNoMinted ? (
            <main className="flex-1 flex items-center justify-center">
              <div className="flex flex-col items-center space-y-6">
                <div className="w-20 h-20 rounded-full bg-[#1E293B] flex items-center justify-center">
                  <span className="text-4xl">🔗</span>
                </div>
                <div className="text-center space-y-2">
                  <h2 className="text-xl font-bold text-white">
                    {language === "ko" ? "민팅된 전략이 없습니다" : "No Minted Strategies"}
                  </h2>
                  <p className="text-sm text-[#94A3B8] max-w-md">
                    {language === "ko"
                      ? "전략을 먼저 생성하고 NFT로 민팅한 후 모의투자를 시작하세요."
                      : "Create a strategy, mint it as NFT, then start paper trading."}
                  </p>
                </div>
                <div className="flex gap-3">
                  <Link
                    href="/chat"
                    className="px-6 py-3 text-sm font-semibold rounded-lg gradient-accent text-[#0A0F1C] hover:opacity-90 transition"
                  >
                    {t("td.createStrategy", language)}
                  </Link>
                  <Link
                    href="/strategies"
                    className="px-6 py-3 text-sm font-semibold rounded-lg bg-[#1E293B] text-[#94A3B8] border border-[#22D3EE20] hover:border-[#22D3EE50] transition"
                  >
                    {language === "ko" ? "내 전략 보기" : "My Strategies"}
                  </Link>
                </div>
              </div>
            </main>
          ) : (
          <>
            {/* 왼쪽 사이드바: 전략 목록 */}
            <aside className="w-64 shrink-0 border-r border-[#1E293B] bg-[#0F172A] overflow-y-auto">
              <div className="px-4 py-3 border-b border-[#1E293B]">
                <h3 className="text-xs font-semibold text-[#475569] uppercase tracking-wider">
                  {language === "ko" ? "민팅된 전략" : "Minted Strategies"}
                </h3>
              </div>
              <div className="p-2 space-y-1">
                {mintedStrategies.map(s => {
                  const ps = s.parsed_strategy;
                  const isSelected = selectedStrategy?.id === s.id;
                  const sLeverage = (ps as any)?.futures?.leverage || ps?.leverage;
                  const entryCount = ps?.entry?.conditions?.length || 0;
                  return (
                    <button
                      key={s.id}
                      onClick={() => !isActive && setSelectedStrategy(s)}
                      disabled={isActive && !isSelected}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-all ${
                        isActive && !isSelected
                          ? "opacity-40 cursor-not-allowed border border-transparent"
                          : isSelected
                          ? "bg-[#22D3EE]/10 border border-[#22D3EE]/30"
                          : "hover:bg-[#1E293B] border border-transparent"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-medium truncate ${isSelected ? "text-[#22D3EE]" : "text-white"}`}>
                          {s.name}
                        </span>
                        {s.status === "verified" && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#9945FF]/20 text-[#14F195] font-bold shrink-0 ml-1">
                            NFT
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        {sLeverage && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#F59E0B]/10 text-[#F59E0B]">
                            {sLeverage}x
                          </span>
                        )}
                        <span className="text-[9px] text-[#475569]">
                          {entryCount} {language === "ko" ? "조건" : "cond"}
                        </span>
                        <span className="text-[9px] text-[#475569]">
                          TP {ps?.exit?.take_profit?.value || "-"}%
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
              <div className="p-2 border-t border-[#1E293B]">
                <Link
                  href="/strategies"
                  className="flex items-center justify-center gap-1.5 w-full px-3 py-2 text-xs font-medium text-[#22D3EE] rounded-lg hover:bg-[#22D3EE]/10 transition"
                >
                  <span>+</span> {language === "ko" ? "전략 민팅하기" : "Mint Strategy"}
                </Link>
              </div>
            </aside>

            {/* 메인 컨텐츠 */}
            <main className="flex-1 overflow-y-auto p-6">
              <div className="max-w-5xl mx-auto">
                {/* 선택된 전략 상세 정보 */}
                {selectedStrategy && (() => {
                  const ps = selectedStrategy.parsed_strategy;
                  const isFutures = (ps as any)?.futures?.enabled || ps?.market_type === "futures";
                  const leverage = (ps as any)?.futures?.leverage || ps?.leverage;
                  return (
                    <div className="bg-[#1E293B] rounded-xl mb-4 border border-[#22D3EE20] overflow-hidden">
                      {/* 헤더 */}
                      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#0F172A]">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-white">{selectedStrategy.name}</span>
                          {leverage && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-[#F59E0B]/10 text-[#F59E0B] font-medium">
                              {isFutures ? "Futures " : ""}{leverage}x
                            </span>
                          )}
                          {selectedStrategy.status === "verified" && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-[#9945FF]/10 text-[#14F195] font-medium">
                              On-chain Verified
                            </span>
                          )}
                        </div>
                        <Link
                          href={`/strategies/${selectedStrategy.id}`}
                          className="text-[10px] text-[#475569] hover:text-[#22D3EE] transition"
                        >
                          {language === "ko" ? "전략 수정" : "Edit"} →
                        </Link>
                      </div>
                      {/* 상세 정보 그리드 */}
                      <div className="px-4 py-3 flex flex-wrap gap-x-6 gap-y-2 text-[11px]">
                        {/* 진입 조건 */}
                        <div className="min-w-[200px]">
                          <div className="text-[#475569] font-semibold mb-1 text-[10px] uppercase tracking-wider">
                            {language === "ko" ? "진입 조건" : "Entry"} ({ps?.entry?.logic || "AND"})
                          </div>
                          {ps?.entry?.conditions?.map((c, i) => (
                            <div key={i} className="text-[#94A3B8] pl-2 border-l border-[#22D3EE]/20 mb-0.5">
                              <span className="text-[#22D3EE]">{c.indicator}</span>{" "}
                              {c.operator} {c.value}{c.unit ? ` ${c.unit}` : ""}
                            </div>
                          ))}
                        </div>

                        {/* 익절 */}
                        <div>
                          <div className="text-[#475569] font-semibold mb-1 text-[10px] uppercase tracking-wider">
                            {language === "ko" ? "익절" : "Take Profit"}
                          </div>
                          <div className="text-[#22C55E] font-mono">
                            {ps?.exit?.take_profit?.value || "-"}%
                          </div>
                          {ps?.exit?.take_profit?.partial?.enabled && (
                            <div className="text-[#475569] text-[10px]">
                              {language === "ko" ? "분할" : "Partial"}: {ps.exit.take_profit.partial.at_percent}% @ {(ps.exit.take_profit.partial.sell_ratio * 100)}%
                            </div>
                          )}
                        </div>

                        {/* 손절 */}
                        <div>
                          <div className="text-[#475569] font-semibold mb-1 text-[10px] uppercase tracking-wider">
                            {language === "ko" ? "손절" : "Stop Loss"}
                          </div>
                          <div className="text-[#EF4444] font-mono">
                            {ps?.exit?.stop_loss?.value || "-"}%
                          </div>
                        </div>

                        {/* 트레일링 스탑 */}
                        {ps?.exit?.trailing_stop?.enabled && (
                          <div>
                            <div className="text-[#475569] font-semibold mb-1 text-[10px] uppercase tracking-wider">
                              {language === "ko" ? "추적 손절" : "Trailing"}
                            </div>
                            <div className="text-[#94A3B8] font-mono">
                              {ps.exit.trailing_stop.trigger_pct}% / {ps.exit.trailing_stop.callback_pct}%
                            </div>
                          </div>
                        )}

                        {/* 방향 */}
                        {((ps as any)?.futures?.direction || ps?.direction) && (
                          <div>
                            <div className="text-[#475569] font-semibold mb-1 text-[10px] uppercase tracking-wider">
                              {language === "ko" ? "방향" : "Direction"}
                            </div>
                            <div className="text-[#94A3B8]">
                              {((ps as any)?.futures?.direction || ps?.direction) === "both" ? "Long / Short" : ((ps as any)?.futures?.direction || ps?.direction)}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* 왼쪽: 차트 + 거래 로그 */}
                  <div className="lg:col-span-2 space-y-4">
                    <LiveChart symbol={symbol} isActive={isActive} />
                    <DemoTradeLog trades={trades} />

                    {/* Phase 5: 신호 온체인 기록 결과 */}
                    {signalRecording && signalRecording.signals_recorded > 0 && (
                      <div className="bg-[#1E293B] rounded-xl p-4 border border-[#9945FF]/20">
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-[#14F195]">⛓️</span>
                          <h4 className="text-sm font-semibold text-white">
                            {language === "ko" ? "온체인 거래 기록" : "On-chain Trade Record"}
                          </h4>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#14F195]/10 text-[#14F195] font-mono">
                            {signalRecording.network}
                          </span>
                          {signalRecording.tx_signature && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#22C55E]/10 text-[#22C55E]">
                              ✓ Confirmed
                            </span>
                          )}
                        </div>

                        {/* TX Signature + Explorer 링크 */}
                        {signalRecording.tx_signature && (
                          <div className="mb-3 p-3 bg-[#0F172A] rounded-lg border border-[#9945FF]/10">
                            <div className="text-[10px] text-[#475569] mb-1">Transaction Signature</div>
                            <div className="flex items-center gap-2">
                              <code className="text-[11px] font-mono text-[#14F195] truncate flex-1">
                                {signalRecording.tx_signature}
                              </code>
                              {signalRecording.explorer_url && (
                                <a
                                  href={signalRecording.explorer_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="shrink-0 text-[10px] px-2.5 py-1 rounded bg-[#9945FF]/20 text-[#9945FF] hover:bg-[#9945FF]/30 transition font-medium"
                                >
                                  Solana Explorer ↗
                                </a>
                              )}
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <div className="text-lg font-bold text-[#22D3EE]">{signalRecording.signals_recorded}</div>
                            <div className="text-[10px] text-[#475569]">
                              {language === "ko" ? "기록된 신호" : "Signals Recorded"}
                            </div>
                          </div>
                          <div>
                            <div className="text-lg font-bold text-[#14F195]">{signalRecording.flushed}</div>
                            <div className="text-[10px] text-[#475569]">
                              {language === "ko" ? "온체인 플러시" : "Flushed On-chain"}
                            </div>
                          </div>
                          <div>
                            <div className="text-lg font-bold text-[#9945FF]">
                              {signalRecording.merkle_root ? "✓" : "—"}
                            </div>
                            <div className="text-[10px] text-[#475569]">Merkle Root</div>
                          </div>
                        </div>

                        {/* Trade Hash */}
                        {signalRecording.trade_hash && (
                          <div className="mt-2 px-2 py-1.5 bg-[#0F172A] rounded">
                            <div className="text-[9px] text-[#475569] mb-0.5">Trade Log SHA256</div>
                            <div className="text-[10px] font-mono text-[#475569] truncate">
                              {signalRecording.trade_hash}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* 오른쪽: 컨트롤 + 포지션 */}
                  <div className="space-y-4">
                    <SignalIndicator signal={isActive ? (signal ?? "wait") : null} />
                    <DemoControls
                      key={selectedStrategy?.id || "default"}
                      onStart={handleStart}
                      onStop={handleStopClick}
                      onSymbolChange={setSymbol}
                      isActive={isActive}
                      isLoading={isLoading}
                      defaultSymbol="SOLUSDT"
                      defaultLeverage={selectedStrategy?.parsed_strategy?.futures?.leverage || selectedStrategy?.parsed_strategy?.leverage || 10}
                      defaultBalance={1000}
                    />
                    <PositionCard
                      position={status?.position ?? null}
                      balance={status?.current_balance ?? status?.balance ?? 0}
                      unrealizedPnl={status?.unrealized_pnl ?? 0}
                    />

                    {/* 온체인 거래 기록 (Solana에서 직접 조회 — 서버 재시작 무관) */}
                    {(onchainTxs.length > 0 || loadingTxs) && (
                      <div className="bg-[#1E293B] rounded-xl border border-[#9945FF]/20 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-[#14F195]">⛓️</span>
                            <span className="text-xs font-semibold text-white">
                              {language === "ko" ? "온체인 기록" : "On-chain Records"}
                            </span>
                          </div>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#14F195]/10 text-[#14F195]">
                            {loadingTxs ? "..." : `${onchainTxs.length} TX`}
                          </span>
                        </div>

                        {/* 인메모리 성과 요약 (있으면) */}
                        {onchainPerf && (
                          <div className="grid grid-cols-3 gap-2 text-center bg-[#0F172A] rounded-lg p-2">
                            <div>
                              <div className={`text-sm font-bold ${onchainPerf.win_rate >= 50 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                                {onchainPerf.win_rate}%
                              </div>
                              <div className="text-[8px] text-[#475569]">Win Rate</div>
                            </div>
                            <div>
                              <div className={`text-sm font-bold ${onchainPerf.total_pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                                {onchainPerf.total_pnl >= 0 ? "+" : ""}{onchainPerf.total_pnl.toFixed(1)}
                              </div>
                              <div className="text-[8px] text-[#475569]">PnL</div>
                            </div>
                            <div>
                              <div className="text-sm font-bold text-white">{onchainPerf.total_trades}</div>
                              <div className="text-[8px] text-[#475569]">Trades</div>
                            </div>
                          </div>
                        )}

                        {/* TX 링크 목록 (Solana 온체인에서 직접 조회) */}
                        {loadingTxs ? (
                          <div className="text-center text-[10px] text-[#475569] py-2">
                            Solana에서 TX 조회 중...
                          </div>
                        ) : (
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {onchainTxs.map((tx, i) => (
                              <a
                                key={i}
                                href={tx.explorer_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-between px-2 py-1.5 bg-[#0F172A] rounded hover:bg-[#0F172A]/80 transition"
                              >
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] font-mono text-[#94A3B8] truncate">
                                    {tx.tx_signature.slice(0, 20)}...
                                  </span>
                                  {tx.block_time && (
                                    <span className="text-[8px] text-[#475569]">
                                      {new Date(tx.block_time * 1000).toLocaleDateString()}
                                    </span>
                                  )}
                                </div>
                                <span className="text-[9px] text-[#9945FF] shrink-0 ml-2">Explorer ↗</span>
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* 마켓플레이스 등록 버튼 */}
                    {selectedStrategy && !isActive && (
                      <button
                        onClick={handlePublish}
                        disabled={publishing}
                        className="w-full py-2.5 text-xs font-semibold rounded-lg bg-[#9945FF]/20 text-[#9945FF] border border-[#9945FF]/30 hover:bg-[#9945FF]/30 transition disabled:opacity-50"
                      >
                        {publishing
                          ? (language === "ko" ? "등록 중..." : "Publishing...")
                          : (language === "ko" ? "🏪 마켓플레이스에 등록" : "🏪 Publish to Marketplace")}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </main>
          </>
          );
          })()}
        </div>

        {/* Stop 모드 선택 모달 */}
        {showStopModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-6 max-w-sm w-full mx-4 space-y-4">
              <h3 className="text-sm font-bold text-white text-center">
                {language === "ko" ? "트레이딩 기록 방식 선택" : "Select Recording Mode"}
              </h3>
              <p className="text-xs text-[#94A3B8] text-center">
                {language === "ko"
                  ? "검증용은 블록체인에 기록되어 마켓플레이스 검증에 사용됩니다."
                  : "Verify mode records on blockchain for marketplace verification."}
              </p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleStop("test")}
                  className="py-3 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#1E293B] hover:border-[#475569] transition"
                >
                  <div className="text-lg mb-1">🧪</div>
                  {language === "ko" ? "테스트" : "Test"}
                  <div className="text-[9px] text-[#475569] mt-0.5">DB only</div>
                </button>
                <button
                  onClick={() => handleStop("verify")}
                  className="py-3 text-xs font-semibold rounded-lg bg-[#22D3EE]/10 text-[#22D3EE] border border-[#22D3EE]/30 hover:bg-[#22D3EE]/20 transition"
                >
                  <div className="text-lg mb-1">⛓️</div>
                  {language === "ko" ? "검증용" : "Verify"}
                  <div className="text-[9px] text-[#475569] mt-0.5">Blockchain</div>
                </button>
              </div>
              <button
                onClick={() => setShowStopModal(false)}
                className="w-full py-2 text-[10px] text-[#475569] hover:text-[#94A3B8] transition"
              >
                {language === "ko" ? "취소" : "Cancel"}
              </button>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}

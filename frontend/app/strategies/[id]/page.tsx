"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getStrategy, runBacktest, updateStrategy, forkStrategy, getBacktestHistory, deleteBacktestHistory, deleteStrategy } from "@/lib/api";
import StrategyCard from "@/components/chat/StrategyCard";
import BacktestChart from "@/components/chat/BacktestChart";
import BacktestResult from "@/components/chat/BacktestResult";
import BacktestSummary from "@/components/chat/BacktestSummary";
import TradeLogTable from "@/components/chat/TradeLogTable";
import StrategyChatPanel from "@/components/chat/StrategyChatPanel";
import type { Strategy, ParsedStrategy, BacktestResult as BtResult, BacktestHistoryItem, BacktestMetrics, EquityPoint, TradeRecord } from "@/lib/types";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

export default function StrategyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const isExample = id.startsWith("example-");
  const forkingRef = useRef(false);
  const { language } = useLanguageStore();

  const [strategy, setStrategy] = useState<Strategy | null>(null);

  // Backtest History State
  const [history, setHistory] = useState<BacktestHistoryItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);

  // 백테스트 기간 설정 (기본값: 최근 90일)
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 90);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split("T")[0];
  });

  // 투자금 (사용자 직접 입력)
  const [investmentAmount, setInvestmentAmount] = useState<number>(1000);

  // 가져오기 모달
  const [showImportModal, setShowImportModal] = useState(false);
  const [importName, setImportName] = useState("");
  const [importing, setImporting] = useState(false);

  // 직접 수정 모달 (JSON 편집)
  const [showEditModal, setShowEditModal] = useState(false);
  const [editJson, setEditJson] = useState("");
  const [editError, setEditError] = useState("");

  useEffect(() => {
    if (!id) return;

    const loadData = async () => {
      try {
        const data = await getStrategy(id);
        setStrategy(data as Strategy);
        // 투자금 초기값: 전략의 size_value
        const ps = (data as Strategy).parsed_strategy;
        if (ps?.position?.size_value) {
          setInvestmentAmount(ps.position.size_value);
        }

        // 과거 백테스트 기록 로드
        if (isExample) {
          // 예시 전략은 localStorage에서 복원
          try {
            const cached = localStorage.getItem(`bt-history-${id}`);
            if (cached) {
              const parsed = JSON.parse(cached) as Array<Record<string, unknown>>;
              const restored: BacktestHistoryItem[] = parsed.map((h) => ({
                ...h,
                timestamp: new Date(h.timestamp as string),
              })) as unknown as BacktestHistoryItem[];
              setHistory(restored);
            }
          } catch { /* 파싱 실패 시 무시 */ }
        } else {
          const historyData = await getBacktestHistory(id);
          if (historyData && Array.isArray(historyData)) {
            const mappedHistory: BacktestHistoryItem[] = historyData.map((h: Record<string, unknown>) => ({
              id: h.id as string,
              timestamp: new Date(h.created_at as string | number | Date),
              strategy: (h.parsed_strategy as ParsedStrategy) || (data as Strategy).parsed_strategy,
              result: {
                id: h.id as string,
                strategy_id: h.strategy_id as string,
                metrics: h.metrics as BacktestMetrics,
                equity_curve: (h.equity_curve || []) as EquityPoint[],
                trade_log: (h.trade_log || []) as TradeRecord[],
                ai_summary: (h.ai_summary as string) || undefined,
              },
              startDate: (h.start_date as string) || "",
              endDate: (h.end_date as string) || ""
            }));
            setHistory(mappedHistory);
          }
        }
      } catch (e) {
        setStrategy(null);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id, isExample]);

  // 가져오기 모달 열 때 기본 이름 설정
  useEffect(() => {
    if (showImportModal && strategy) {
      setImportName(strategy.name);
    }
  }, [showImportModal, strategy]);

  // 채팅으로 전략이 수정되었는지 추적 (최신 전략 우선 표시용)
  const [strategyUpdatedByChat, setStrategyUpdatedByChat] = useState(false);

  // AI가 전략을 수정하면 즉시 페이지 반영 + DB 업데이트
  const handleStrategyUpdate = useCallback(async (updated: ParsedStrategy) => {
    setStrategy(prev => {
      if (!prev) return prev;
      return { ...prev, parsed_strategy: updated };
    });
    setStrategyUpdatedByChat(true);

    if (!id || isExample) return;

    // 내 전략은 바로 DB 업데이트
    updateStrategy(id, { parsed_strategy: updated as unknown as Record<string, unknown> }).catch(() => { });
  }, [id, isExample]);

  const handleDeleteHistory = async (historyId: string, idx: number, e: React.MouseEvent) => {
    e.stopPropagation(); // 탭 선택 방지
    if (!window.confirm(t("sd.deleteHistoryConfirm", language))) return;

    try {
      if (!isExample) {
        await deleteBacktestHistory(historyId);
      }

      setHistory(prev => {
        const newHistory = [...prev];
        newHistory.splice(idx, 1);
        // 예시 전략은 localStorage도 업데이트
        if (isExample) {
          try {
            const serialized = newHistory.map(h => ({
              ...h,
              timestamp: h.timestamp instanceof Date ? h.timestamp.toISOString() : h.timestamp,
            }));
            localStorage.setItem(`bt-history-${id}`, JSON.stringify(serialized));
          } catch { /* 무시 */ }
        }
        return newHistory;
      });

      if (selectedIndex === idx) {
        setSelectedIndex(0);
      } else if (selectedIndex > idx) {
        setSelectedIndex(selectedIndex - 1);
      }
    } catch (err) {
      alert(t("sd.deleteHistoryFailed", language));
      console.error(err);
    }
  };

  // 전략 가져오기 (포크)
  const handleImport = async () => {
    if (!strategy || importing || !importName.trim()) return;
    setImporting(true);
    try {
      const forked = await forkStrategy(id, importName.trim());
      router.push(`/strategies/${forked.id}`);
    } catch {
      // 실패 시 모달 유지
    } finally {
      setImporting(false);
    }
  };

  const handleBacktest = async () => {
    if (!strategy) return;
    setTesting(true);
    try {
      const ps = strategy.parsed_strategy;
      const pair = ps.target_pair || "SOL/USDC";
      const tf = ps.timeframe || "1h";
      // 투자금 반영: max_positions=1 고정, size_value=사용자 입력값
      const strategyWithInvestment = {
        ...ps as unknown as Record<string, unknown>,
        position: {
          ...(ps.position || {}),
          size_value: investmentAmount,
          max_positions: 1,
        },
      };
      const result = await runBacktest(
        strategy.id,
        pair,
        tf,
        strategyWithInvestment,
        startDate || undefined,
        endDate || undefined,
        language,
      ) as BtResult;

      const newItem: BacktestHistoryItem = {
        id: result.id || Math.random().toString(36).substring(7),
        timestamp: new Date(),
        strategy: ps,
        result,
        startDate,
        endDate
      };

      setHistory(prev => {
        const updated = [newItem, ...prev];
        // 예시 전략은 DB 저장 안 되므로 localStorage에 캐싱
        if (isExample) {
          try {
            const serialized = updated.map(h => ({
              ...h,
              timestamp: h.timestamp.toISOString(),
            }));
            localStorage.setItem(`bt-history-${id}`, JSON.stringify(serialized));
          } catch { /* localStorage 용량 초과 시 무시 */ }
        }
        return updated;
      });
      setSelectedIndex(0);

    } catch {
      // MVP
    } finally {
      setTesting(false);
    }
  };

  // 현재 화면에 띄워진(선택된) 전략 컨텍스트
  // 채팅으로 수정된 직후에는 최신 전략을 우선 표시, 아니면 선택된 히스토리 전략
  const currentViewStrategy = strategyUpdatedByChat
    ? strategy?.parsed_strategy
    : (history.length > 0 && history[selectedIndex]?.strategy)
      ? (history[selectedIndex].strategy as ParsedStrategy)
      : strategy?.parsed_strategy;

  const handleDeleteStrategy = async () => {
    if (!window.confirm(t("sp.deleteConfirm", language))) return;
    try {
      await deleteStrategy(id);
      router.push("/strategies");
    } catch {
      alert(t("sp.deleteFailed", language));
    }
  };

  const handleOpenEditModal = () => {
    if (!currentViewStrategy) return;
    setEditJson(JSON.stringify(currentViewStrategy, null, 2));
    setEditError("");
    setShowEditModal(true);
  };

  const handleSaveEditModal = async () => {
    try {
      const parsed = JSON.parse(editJson);
      if (!parsed || !parsed.name || !parsed.target_pair || !parsed.timeframe) {
        throw new Error(t("sd.requiredFields", language));
      }

      // AI에 의한 업데이트 처리기 활용
      await handleStrategyUpdate(parsed as ParsedStrategy);
      setShowEditModal(false);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : t("sd.invalidJson", language));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] flex items-center justify-center text-[#475569]">
        {t("sd.loading", language)}
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] flex flex-col items-center justify-center gap-4">
        <p className="text-[#94A3B8]">{t("sd.notFound", language)}</p>
        <Link href="/strategies" className="text-[#22D3EE] hover:underline">
          {t("sd.backToList", language)}
        </Link>
      </div>
    );
  }

  // 예시 템플릿: 1-Column (읽기 전용 + 백테스트 + 가져오기 버튼)
  if (isExample) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] text-white">
        {/* 헤더 */}
        <header className="h-14 flex items-center px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-base font-bold">TradeCoach</span>
              <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
                AI
              </span>
            </Link>
            <span className="text-[#475569]">/</span>
            <Link href="/strategies" className="text-sm text-[#94A3B8] hover:text-white transition">
              {t("sp.breadcrumb", language)}
            </Link>
            <span className="text-[#475569]">/</span>
            <span className="text-sm text-white">{strategy.name}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[#22D3EE]/10 text-[#22D3EE] ml-2">
              {t("sp.exampleTemplates", language)}
            </span>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
          <StrategyCard
            strategy={strategy.parsed_strategy}
            investmentAmount={investmentAmount}
            onInvestmentChange={setInvestmentAmount}
          />

          {/* 가져오기 버튼 */}
          <button
            onClick={() => setShowImportModal(true)}
            className="w-full px-6 py-4 rounded-xl font-semibold text-base bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 transition cursor-pointer"
          >
            {t("sd.importToMy", language)}
          </button>

          {/* 백테스트 섹션 */}
          <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE10] p-5 space-y-4">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-[#94A3B8]">{t("sd.backtest", language)}</h3>
              <span className="text-[10px] text-[#475569] font-normal">
                {t("sd.apiLimit", language)}
              </span>
            </div>

            {/* 기간 선택 */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[130px]">
                <label className="text-xs text-[#475569] mb-1 block">{t("sd.startDate", language)}</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none [color-scheme:dark]"
                />
              </div>
              <div className="flex-1 min-w-[130px]">
                <label className="text-xs text-[#475569] mb-1 block">{t("sd.endDate", language)}</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none [color-scheme:dark]"
                />
              </div>
              <div className="flex-shrink-0 pt-4">
                <button
                  onClick={handleBacktest}
                  disabled={testing}
                  className="px-5 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
                >
                  {testing ? t("sd.running", language) : t("sd.runBacktest", language)}
                </button>
              </div>
            </div>
          </div>

          {/* 백테스트 결과 및 히스토리 탭 */}
          {history.length > 0 && (
            <div className="space-y-4">
              {/* 탭 네비게이션 */}
              <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-[#1E293B] scrollbar-track-transparent">
                {history.map((item, idx) => (
                  <div key={item.id} className="inline-flex items-center">
                    <button
                      onClick={() => { setSelectedIndex(idx); setStrategyUpdatedByChat(false); }}
                      className={`whitespace-nowrap px-4 py-2 text-xs font-semibold transition-colors border-y border-l rounded-l-lg pr-2
                        ${selectedIndex === idx
                          ? "bg-[#22D3EE]/10 text-[#22D3EE] border-[#22D3EE]/30"
                          : "bg-[#1E293B] text-[#94A3B8] border-[#1E293B] hover:bg-[#1E293B]/80 hover:text-white"
                        }`}
                    >
                      {idx === 0 ? t("sd.latestRun", language) : `${t("sd.previousRun", language)} ${idx}`}
                      <span className="ml-2 text-[10px] opacity-60 font-mono">
                        {item.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </button>
                    <button
                      onClick={(e) => handleDeleteHistory(item.id, idx, e)}
                      title={t("sd.deleteRecord", language)}
                      className={`px-2 py-2 border-y border-r rounded-r-lg flex items-center transition-colors group
                        ${selectedIndex === idx
                          ? "bg-[#22D3EE]/10 border-[#22D3EE]/30 hover:bg-[#EF4444]/20"
                          : "bg-[#1E293B] border-[#1E293B] hover:bg-[#EF4444]/20"
                        }`}
                    >
                      <svg className={`w-3.5 h-3.5 ${selectedIndex === idx ? "text-[#22D3EE]" : "text-[#94A3B8]"} group-hover:text-[#EF4444] transition-colors`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>

              {/* 선택된 결과 */}
              {history[selectedIndex] && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  {/* 적용 버튼 */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 bg-[#1E293B] rounded-xl border border-[#22D3EE20] gap-3">
                    <span className="text-xs text-[#94A3B8]">
                      {t("sd.period", language)} {history[selectedIndex].startDate} ~ {history[selectedIndex].endDate}
                    </span>
                    <button
                      onClick={() => handleStrategyUpdate(history[selectedIndex].strategy as ParsedStrategy)}
                      className="whitespace-nowrap px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#22D3EE] border border-[#22D3EE30] hover:bg-[#22D3EE10] transition-colors"
                    >
                      {t("sd.applyStrategy", language)}
                    </button>
                  </div>

                  {history[selectedIndex].result.equity_curve && history[selectedIndex].result.equity_curve.length > 0 ? (
                    <BacktestChart equityCurve={history[selectedIndex].result.equity_curve} metrics={history[selectedIndex].result.metrics} tradeLog={history[selectedIndex].result.trade_log} actualPeriod={history[selectedIndex].result.actual_period} />
                  ) : (
                    <BacktestResult result={history[selectedIndex].result} />
                  )}

                  {/* AI 요약 분석 리포트 카드 (백테스트 실행 시 생성, 저장된 것만 표시) */}
                  <BacktestSummary aiSummary={history[selectedIndex].result.ai_summary} />

                  <TradeLogTable trades={history[selectedIndex].result.trade_log} />
                </div>
              )}
            </div>
          )}
        </main>

        {/* 가져오기 모달 */}
        {showImportModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] w-full max-w-md mx-4 overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-[#0F172A]">
                <h2 className="text-lg font-bold text-white">{t("sd.importModalTitle", language)}</h2>
                <button
                  onClick={() => { setShowImportModal(false); setImportName(""); }}
                  className="text-[#475569] hover:text-white transition cursor-pointer text-xl"
                >
                  ✕
                </button>
              </div>

              <div className="px-6 py-5">
                <p className="text-sm text-[#94A3B8] mb-4">
                  {t("sd.importModalDesc", language)}
                </p>
                <input
                  type="text"
                  value={importName}
                  onChange={e => setImportName(e.target.value)}
                  placeholder={t("sd.strategyTitle", language)}
                  className="w-full bg-[#0F172A] text-white text-sm rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none placeholder-[#475569]"
                  onKeyDown={e => { if (e.key === "Enter") handleImport(); }}
                  autoFocus
                />
              </div>

              <div className="flex gap-3 px-6 py-4 border-t border-[#0F172A]">
                <button
                  onClick={() => { setShowImportModal(false); setImportName(""); }}
                  className="flex-1 py-3 text-sm font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] hover:border-[#22D3EE50] transition cursor-pointer"
                >
                  {t("sp.cancel", language)}
                </button>
                <button
                  onClick={handleImport}
                  disabled={importing || !importName.trim()}
                  className="flex-1 py-3 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
                >
                  {importing ? t("sd.importing", language) : t("sd.save", language)}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 내 전략: 2-Column (편집 가능 + AI 채팅)
  return (
    <div className="h-screen flex flex-col bg-[#0A0F1C] text-white">
      {/* 헤더 */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
              AI
            </span>
          </Link>
          <span className="text-[#475569]">/</span>
          <Link href="/strategies" className="text-sm text-[#94A3B8] hover:text-white transition">
            {t("sp.breadcrumb", language)}
          </Link>
          <span className="text-[#475569]">/</span>
          <span className="text-sm text-white">{strategy.name}</span>
        </div>
        <button
          onClick={handleDeleteStrategy}
          className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-[#EF4444]/30 text-[#EF4444] hover:bg-[#EF4444]/10 transition cursor-pointer"
        >
          {t("sp.deleteStrategy", language)}
        </button>
      </header>

      {/* 메인 3-Column 레이아웃 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 왼쪽 1: 백테스트 기록 사이드바 */}
        <aside className="w-64 flex-shrink-0 border-r border-[#1E293B] bg-[#0F172A] overflow-y-auto hidden md:flex flex-col relative text-white">
          <div className="p-4 border-b border-[#1E293B] sticky top-0 bg-[#0F172A]/90 backdrop-blur-sm z-10 flex flex-col gap-3">
            <Link
              href="/strategies"
              className="text-[11px] font-semibold text-[#94A3B8] hover:text-white transition flex items-center gap-1.5 group w-fit"
            >
              <svg className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              {t("sd.myStrategiesList", language)}
            </Link>
            <h2 className="text-sm font-bold text-[#F8FAFC]">{t("sd.backtestHistory", language)}</h2>
          </div>

          <div className="p-3 mb-10 space-y-2">
            {history.length === 0 ? (
              <p className="text-xs text-[#475569] text-center py-4">{t("sd.noHistory", language)}</p>
            ) : (
              history.map((item, idx) => (
                <div key={item.id} className="relative group">
                  <button
                    onClick={() => { setSelectedIndex(idx); setStrategyUpdatedByChat(false); }}
                    className={`block w-full text-left p-3 rounded-lg border transition-colors ${selectedIndex === idx
                      ? "bg-[#22D3EE]/10 border-[#22D3EE]/30"
                      : "bg-[#1E293B] border-[#1E293B] hover:border-[#475569] hover:bg-[#1E293B]/80"
                      }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <h3 className={`text-sm font-medium ${selectedIndex === idx ? "text-[#22D3EE]" : "text-[#F8FAFC]"}`}>
                        {idx === 0 ? t("sd.latestRun", language) : `${t("sd.previousRecord", language)} ${idx}`}
                      </h3>
                      <span className="text-[10px] opacity-60 font-mono text-[#94A3B8]">
                        {item.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-[#94A3B8]">
                      <span>{item.startDate.substring(5)} ~ {item.endDate.substring(5)}</span>
                      {item.result.metrics?.total_return !== undefined && (
                        <span className={`${item.result.metrics.total_return >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                          {item.result.metrics.total_return > 0 ? "+" : ""}{item.result.metrics.total_return}%
                        </span>
                      )}
                    </div>
                  </button>
                  <button
                    onClick={(e) => handleDeleteHistory(item.id, idx, e)}
                    title={t("sd.deleteRecord", language)}
                    className="absolute top-2 right-2 p-1.5 rounded-md hover:bg-[#EF4444]/20 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <svg className={`w-3.5 h-3.5 ${selectedIndex === idx ? "text-[#22D3EE]" : "text-[#94A3B8]"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* 중앙: 전략 정보 + 백테스트 (기존 왼쪽 칼럼) */}
        <main className="flex-1 min-w-0 overflow-y-auto p-6 space-y-6 flex flex-col items-center">
          <div className="w-full max-w-3xl space-y-6">
            {currentViewStrategy && (
              <StrategyCard
                strategy={currentViewStrategy}
                onEdit={handleOpenEditModal}
                investmentAmount={investmentAmount}
                onInvestmentChange={setInvestmentAmount}
              />
            )}

            {/* 백테스트 섹션 */}
            <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE10] p-5 space-y-4">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[#94A3B8]">{t("sd.backtest", language)}</h3>
                <span className="text-[10px] text-[#475569] font-normal">
                  {t("sd.apiLimit", language)}
                </span>
              </div>

              {/* 기간 선택 */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex-1 min-w-[130px]">
                  <label className="text-xs text-[#475569] mb-1 block">{t("sd.startDate", language)}</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                    className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none [color-scheme:dark]"
                  />
                </div>
                <div className="flex-1 min-w-[130px]">
                  <label className="text-xs text-[#475569] mb-1 block">{t("sd.endDate", language)}</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={e => setEndDate(e.target.value)}
                    className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none [color-scheme:dark]"
                  />
                </div>
                <div className="flex-shrink-0 pt-4">
                  <button
                    onClick={handleBacktest}
                    disabled={testing}
                    className="px-5 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
                  >
                    {testing ? t("sd.running", language) : t("sd.runBacktest", language)}
                  </button>
                </div>
              </div>
            </div>

            {/* 백테스트 결과 */}
            {history.length > 0 && (
              <div className="space-y-4">
                {/* 선택된 결과 */}
                {history[selectedIndex] && (
                  <div className="space-y-4 animate-in fade-in duration-200">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 bg-[#1E293B] rounded-xl border border-[#22D3EE20] gap-3">
                      <span className="text-xs text-[#94A3B8]">
                        {t("sd.period", language)} {history[selectedIndex].startDate} ~ {history[selectedIndex].endDate}
                      </span>
                      <button
                        onClick={() => handleStrategyUpdate(history[selectedIndex].strategy as ParsedStrategy)}
                        className="whitespace-nowrap px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#22D3EE] border border-[#22D3EE30] hover:bg-[#22D3EE10] transition-colors"
                      >
                        {t("sd.applyStrategy", language)}
                      </button>
                    </div>

                    {history[selectedIndex].result.equity_curve && history[selectedIndex].result.equity_curve.length > 0 ? (
                      <BacktestChart equityCurve={history[selectedIndex].result.equity_curve} metrics={history[selectedIndex].result.metrics} tradeLog={history[selectedIndex].result.trade_log} actualPeriod={history[selectedIndex].result.actual_period} />
                    ) : (
                      <BacktestResult result={history[selectedIndex].result} />
                    )}

                    {/* AI 요약 분석 리포트 카드 (백테스트 실행 시 생성, 저장된 것만 표시) */}
                    <BacktestSummary aiSummary={history[selectedIndex].result.ai_summary} />

                    <TradeLogTable trades={history[selectedIndex].result.trade_log} />
                  </div>
                )}
              </div>
            )}
          </div>
        </main>

        {/* 오른쪽 3: 방어/공격 모드 채팅 (AI 코칭) */}
        <aside className="w-96 flex-shrink-0 bg-[#0A0F1C] border-l border-[#1E293B] hidden lg:flex flex-col relative">
          {!isExample && (
            <div className="absolute top-0 right-full w-4 h-full bg-gradient-to-r from-transparent to-[#0A0F1C]/50 pointer-events-none z-10" />
          )}
          {currentViewStrategy && (
            <StrategyChatPanel
              strategyId={strategy.id}
              strategy={currentViewStrategy}
              onStrategyUpdate={handleStrategyUpdate}
              investmentAmount={investmentAmount}
            />
          )}
        </aside>
      </div>

      {/* 전략 수동 편집(JSON) 모달 */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] w-full max-w-2xl mx-4 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#0F172A]">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>⚙️</span> {t("sd.editModalTitle", language)}
              </h2>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-[#475569] hover:text-white transition cursor-pointer text-xl"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <p className="text-sm text-[#94A3B8] mb-4">
                {t("sd.editModalDesc", language)}
              </p>
              <textarea
                value={editJson}
                onChange={e => setEditJson(e.target.value)}
                className="w-full h-[400px] bg-[#0F172A] text-[#22D3EE] font-mono text-xs rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none resize-none"
                spellCheck={false}
              />
              {editError && (
                <p className="mt-3 text-sm text-[#EF4444] bg-[#EF4444]/10 p-3 rounded-lg border border-[#EF4444]/20">
                  {editError}
                </p>
              )}
            </div>

            <div className="flex gap-3 px-6 py-4 border-t border-[#0F172A]">
              <button
                onClick={() => setShowEditModal(false)}
                className="flex-1 py-3 text-sm font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] hover:border-[#22D3EE50] transition cursor-pointer"
              >
                {t("sp.cancel", language)}
              </button>
              <button
                onClick={handleSaveEditModal}
                className="flex-1 py-3 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 transition cursor-pointer"
              >
                {t("sd.applyChanges", language)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

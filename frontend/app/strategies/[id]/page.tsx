"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getStrategy, runBacktest, updateStrategy, forkStrategy } from "@/lib/api";
import StrategyCard from "@/components/chat/StrategyCard";
import BacktestChart from "@/components/chat/BacktestChart";
import BacktestResult from "@/components/chat/BacktestResult";
import StrategyChatPanel from "@/components/chat/StrategyChatPanel";
import type { Strategy, ParsedStrategy, BacktestResult as BtResult } from "@/lib/types";

export default function StrategyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const isExample = id.startsWith("example-");
  const forkingRef = useRef(false);

  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [btResult, setBtResult] = useState<BtResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);

  // 백테스트 기간 설정
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // 가져오기 모달
  const [showImportModal, setShowImportModal] = useState(false);
  const [importName, setImportName] = useState("");
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (!id) return;
    getStrategy(id)
      .then((data) => setStrategy(data as Strategy))
      .catch(() => setStrategy(null))
      .finally(() => setLoading(false));
  }, [id]);

  // 가져오기 모달 열 때 기본 이름 설정
  useEffect(() => {
    if (showImportModal && strategy) {
      setImportName(strategy.name);
    }
  }, [showImportModal, strategy]);

  // AI가 전략을 수정하면 즉시 페이지 반영 + DB 업데이트
  const handleStrategyUpdate = useCallback(async (updated: ParsedStrategy) => {
    setStrategy(prev => {
      if (!prev) return prev;
      return { ...prev, parsed_strategy: updated };
    });

    if (!id || isExample) return;

    // 내 전략은 바로 DB 업데이트
    updateStrategy(id, { parsed_strategy: updated as unknown as Record<string, unknown> }).catch(() => {});
  }, [id, isExample]);

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
      const result = await runBacktest(
        strategy.id,
        pair,
        tf,
        ps as unknown as Record<string, unknown>,
        startDate || undefined,
        endDate || undefined,
      ) as BtResult;
      setBtResult(result);
    } catch {
      // MVP
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] flex items-center justify-center text-[#475569]">
        로딩 중...
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] flex flex-col items-center justify-center gap-4">
        <p className="text-[#94A3B8]">전략을 찾을 수 없습니다.</p>
        <Link href="/strategies" className="text-[#22D3EE] hover:underline">
          목록으로 돌아가기
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
              전략
            </Link>
            <span className="text-[#475569]">/</span>
            <span className="text-sm text-white">{strategy.name}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[#22D3EE]/10 text-[#22D3EE] ml-2">
              예시 템플릿
            </span>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
          <StrategyCard strategy={strategy.parsed_strategy} />

          {/* 가져오기 버튼 */}
          <button
            onClick={() => setShowImportModal(true)}
            className="w-full px-6 py-4 rounded-xl font-semibold text-base bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 transition cursor-pointer"
          >
            내 전략으로 가져오기
          </button>

          {/* 백테스트 섹션 */}
          <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE10] p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#94A3B8]">백테스트</h3>

            {/* 기간 선택 */}
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className="text-xs text-[#475569] mb-1 block">시작일</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none [color-scheme:dark]"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs text-[#475569] mb-1 block">종료일</label>
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
                  {testing ? "실행 중..." : "백테스트 실행"}
                </button>
              </div>
            </div>
          </div>

          {/* 백테스트 결과 */}
          {btResult && (
            <div className="space-y-4">
              {btResult.equity_curve && btResult.equity_curve.length > 0 ? (
                <BacktestChart equityCurve={btResult.equity_curve} metrics={btResult.metrics} />
              ) : (
                <BacktestResult result={btResult} />
              )}
            </div>
          )}
        </main>

        {/* 가져오기 모달 */}
        {showImportModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] w-full max-w-md mx-4 overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-[#0F172A]">
                <h2 className="text-lg font-bold text-white">내 전략으로 가져오기</h2>
                <button
                  onClick={() => { setShowImportModal(false); setImportName(""); }}
                  className="text-[#475569] hover:text-white transition cursor-pointer text-xl"
                >
                  ✕
                </button>
              </div>

              <div className="px-6 py-5">
                <p className="text-sm text-[#94A3B8] mb-4">
                  전략의 제목을 입력하세요. 가져온 후 AI와 대화하며 자유롭게 수정할 수 있습니다.
                </p>
                <input
                  type="text"
                  value={importName}
                  onChange={e => setImportName(e.target.value)}
                  placeholder="전략 제목"
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
                  취소
                </button>
                <button
                  onClick={handleImport}
                  disabled={importing || !importName.trim()}
                  className="flex-1 py-3 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
                >
                  {importing ? "가져오는 중..." : "저장"}
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
      <header className="h-14 flex items-center px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
              AI
            </span>
          </Link>
          <span className="text-[#475569]">/</span>
          <Link href="/strategies" className="text-sm text-[#94A3B8] hover:text-white transition">
            전략
          </Link>
          <span className="text-[#475569]">/</span>
          <span className="text-sm text-white">{strategy.name}</span>
        </div>
      </header>

      {/* 2-Column 레이아웃 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 왼쪽: 전략 정보 + 백테스트 */}
        <div className="w-1/2 overflow-y-auto p-6 space-y-6 border-r border-[#1E293B]">
          <StrategyCard strategy={strategy.parsed_strategy} />

          {/* 백테스트 섹션 */}
          <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE10] p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#94A3B8]">백테스트</h3>

            {/* 기간 선택 */}
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className="text-xs text-[#475569] mb-1 block">시작일</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="w-full bg-[#0F172A] text-white text-xs rounded-lg px-3 py-2 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none [color-scheme:dark]"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs text-[#475569] mb-1 block">종료일</label>
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
                  {testing ? "실행 중..." : "백테스트 실행"}
                </button>
              </div>
            </div>
          </div>

          {/* 백테스트 결과 */}
          {btResult && (
            <div className="space-y-4">
              {btResult.equity_curve && btResult.equity_curve.length > 0 ? (
                <BacktestChart equityCurve={btResult.equity_curve} metrics={btResult.metrics} />
              ) : (
                <BacktestResult result={btResult} />
              )}
            </div>
          )}
        </div>

        {/* 오른쪽: AI 채팅 패널 */}
        <div className="w-1/2 p-4">
          <StrategyChatPanel
            strategyId={strategy.id}
            strategy={strategy.parsed_strategy}
            onStrategyUpdate={handleStrategyUpdate}
          />
        </div>
      </div>
    </div>
  );
}

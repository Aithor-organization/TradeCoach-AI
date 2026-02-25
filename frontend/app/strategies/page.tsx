"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getStrategies, sendMessage, saveStrategy } from "@/lib/api";
import type { Strategy, ChatResponse } from "@/lib/types";

type Tab = "examples" | "my";

export default function StrategiesPage() {
  const router = useRouter();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("examples");

  // 새 전략 생성 모달 상태
  const [showModal, setShowModal] = useState(false);
  const [newStrategyText, setNewStrategyText] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    getStrategies()
      .then((data: unknown) => {
        const d = data as { strategies?: Strategy[] };
        const list = Array.isArray(data) ? data : (d?.strategies ?? []);
        setStrategies(list as Strategy[]);
      })
      .catch(() => setStrategies([]))
      .finally(() => setLoading(false));
  }, []);

  const exampleStrategies = strategies.filter(s => s.id.startsWith("example-"));
  const myStrategies = strategies.filter(s => !s.id.startsWith("example-"));
  const displayList = activeTab === "examples" ? exampleStrategies : myStrategies;

  const handleCreateStrategy = async () => {
    if (!newStrategyText.trim() || creating) return;
    setCreating(true);
    setCreateError("");

    try {
      const response = await sendMessage(newStrategyText.trim()) as ChatResponse;

      if (!response.parsed_strategy) {
        setCreateError("전략을 파싱할 수 없습니다. 더 구체적으로 설명해주세요.");
        setCreating(false);
        return;
      }

      const saved = await saveStrategy(
        response.parsed_strategy.name || "새 전략",
        response.parsed_strategy as unknown as Record<string, unknown>,
        newStrategyText.trim(),
      ) as { id?: string };

      if (saved?.id && saved.id !== "local-strategy") {
        router.push(`/strategies/${saved.id}`);
      } else {
        setCreateError("전략이 생성되었지만 DB 저장에 실패했습니다.");
        setCreating(false);
      }
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "전략 생성 실패");
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0F1C] text-white">
      {/* 헤더 */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
              AI
            </span>
          </Link>
          <span className="text-[#475569]">/</span>
          <span className="text-sm text-[#94A3B8]">전략</span>
        </div>
        <button
          onClick={() => { setActiveTab("my"); setShowModal(true); }}
          className="px-4 py-2 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 transition cursor-pointer"
        >
          + 새 전략
        </button>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {/* 탭 */}
        <div className="flex items-center gap-1 mb-8 bg-[#1E293B] rounded-lg p-1 w-fit">
          <button
            onClick={() => setActiveTab("examples")}
            className={`px-5 py-2 text-sm font-semibold rounded-md transition cursor-pointer ${
              activeTab === "examples"
                ? "bg-[#22D3EE] text-[#0A0F1C]"
                : "text-[#94A3B8] hover:text-white"
            }`}
          >
            예시 템플릿
            <span className="ml-1.5 text-xs opacity-70">({exampleStrategies.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("my")}
            className={`px-5 py-2 text-sm font-semibold rounded-md transition cursor-pointer ${
              activeTab === "my"
                ? "bg-[#22D3EE] text-[#0A0F1C]"
                : "text-[#94A3B8] hover:text-white"
            }`}
          >
            내 전략
            <span className="ml-1.5 text-xs opacity-70">({myStrategies.length})</span>
          </button>
        </div>

        {/* 탭 설명 */}
        <p className="text-sm text-[#475569] mb-6">
          {activeTab === "examples"
            ? "검증된 투자 전략 템플릿입니다. 클릭하여 상세 정보와 백테스트를 확인한 후 가져올 수 있습니다."
            : "AI와 대화하며 자유롭게 수정할 수 있는 내 전략입니다."}
        </p>

        {loading ? (
          <div className="text-center py-20 text-[#475569]">로딩 중...</div>
        ) : displayList.length === 0 ? (
          <div className="text-center py-20">
            <span className="text-5xl mb-4 block">{activeTab === "examples" ? "📋" : "🧠"}</span>
            <p className="text-[#94A3B8] mb-4">
              {activeTab === "examples"
                ? "예시 템플릿이 없습니다."
                : "아직 내 전략이 없습니다. 예시 템플릿에서 가져오거나 새로 만들어보세요."}
            </p>
            {activeTab === "my" && (
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => setActiveTab("examples")}
                  className="px-5 py-3 rounded-lg bg-[#1E293B] border border-[#22D3EE30] text-[#22D3EE] font-semibold hover:border-[#22D3EE60] transition cursor-pointer"
                >
                  예시 템플릿 보기
                </button>
                <button
                  onClick={() => setShowModal(true)}
                  className="px-5 py-3 rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] font-semibold hover:opacity-90 transition cursor-pointer"
                >
                  새 전략 만들기
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {displayList.map((s) => (
              <Link
                key={s.id}
                href={`/strategies/${s.id}`}
                className="block p-5 rounded-xl bg-[#1E293B] border border-[#22D3EE10] hover:border-[#22D3EE40] transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white">{s.name}</h3>
                  {activeTab === "examples" && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-[#22D3EE]/10 text-[#22D3EE]">
                      템플릿
                    </span>
                  )}
                </div>
                <p className="text-sm text-[#475569] line-clamp-2 mb-3">{s.raw_input}</p>
                <div className="flex items-center gap-4 text-xs text-[#475569]">
                  <span>{s.parsed_strategy.target_pair}</span>
                  <span>{s.parsed_strategy.timeframe}</span>
                  {activeTab === "my" && (
                    <span>{new Date(s.created_at).toLocaleDateString("ko-KR")}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {/* 새 전략 생성 모달 */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] w-full max-w-lg mx-4 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#0F172A]">
              <h2 className="text-lg font-bold text-white">새 전략 만들기</h2>
              <button
                onClick={() => { setShowModal(false); setCreateError(""); setNewStrategyText(""); }}
                className="text-[#475569] hover:text-white transition cursor-pointer text-xl"
              >
                ✕
              </button>
            </div>

            <div className="px-6 py-5">
              <p className="text-sm text-[#94A3B8] mb-4">
                트레이딩 전략을 자연어로 설명해주세요. AI가 구조화된 전략으로 변환합니다.
              </p>
              <textarea
                value={newStrategyText}
                onChange={e => setNewStrategyText(e.target.value)}
                placeholder="예: RSI가 30 이하일 때 매수하고, 15% 익절, 8% 손절하는 SOL/USDC 전략"
                className="w-full bg-[#0F172A] text-white text-sm rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none resize-none placeholder-[#475569] min-h-[120px]"
                rows={4}
                disabled={creating}
              />
              {createError && (
                <p className="mt-2 text-xs text-[#EF4444]">{createError}</p>
              )}
            </div>

            <div className="flex gap-3 px-6 py-4 border-t border-[#0F172A]">
              <button
                onClick={() => { setShowModal(false); setCreateError(""); setNewStrategyText(""); }}
                className="flex-1 py-3 text-sm font-semibold rounded-lg bg-[#0F172A] text-[#94A3B8] border border-[#22D3EE20] hover:border-[#22D3EE50] transition cursor-pointer"
              >
                취소
              </button>
              <button
                onClick={handleCreateStrategy}
                disabled={creating || !newStrategyText.trim()}
                className="flex-1 py-3 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
              >
                {creating ? "AI가 전략 생성 중..." : "전략 생성 및 저장"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthGuard from "@/components/common/AuthGuard";
import { getStrategies, sendMessage, saveStrategy, deleteStrategy } from "@/lib/api";
import type { Strategy, ChatResponse } from "@/lib/types";
import TokenPrices from "@/components/market/TokenPrices";
import Skeleton from "@/components/common/Skeleton";
import OnboardingBanner from "@/components/common/OnboardingBanner";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

type Tab = "examples" | "my";

export default function StrategiesPage() {
  const router = useRouter();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("my");

  // 새 전략 생성 모달 상태
  const [showModal, setShowModal] = useState(false);
  const [newStrategyText, setNewStrategyText] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const { language } = useLanguageStore();

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

  const handleDeleteStrategy = async (e: React.MouseEvent, strategyId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(t("sp.deleteConfirm", language))) return;
    try {
      await deleteStrategy(strategyId);
      setStrategies(prev => prev.filter(s => s.id !== strategyId));
    } catch {
      alert(t("sp.deleteFailed", language));
    }
  };

  const handleCreateStrategy = async () => {
    if (!newStrategyText.trim() || creating) return;
    setCreating(true);
    setCreateError("");

    try {
      const response = await sendMessage(newStrategyText.trim()) as ChatResponse;

      if (!response.parsed_strategy) {
        setCreateError(t("sp.parseFailed", language));
        setCreating(false);
        return;
      }

      const saved = await saveStrategy(
        response.parsed_strategy.name || (language === "en" ? "New Strategy" : "새 전략"),
        response.parsed_strategy as unknown as Record<string, unknown>,
        newStrategyText.trim(),
      ) as { id?: string };

      if (saved?.id && saved.id !== "local-strategy") {
        router.push(`/strategies/${saved.id}`);
      } else {
        setCreateError(t("sp.dbSaveFailed", language));
        setCreating(false);
      }
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : t("sp.createFailed", language));
      setCreating(false);
    }
  };

  return (
    <AuthGuard>
    <div className="min-h-screen bg-[#0A0F1C] text-white">
      {/* 헤더 */}
      <header className="h-14 flex items-center justify-between px-4 sm:px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
              AI
            </span>
          </Link>
          <span className="text-[#475569]">/</span>
          <span className="text-sm text-[#94A3B8]">{t("sp.breadcrumb", language)}</span>
        </div>
        <button
          onClick={() => { setActiveTab("my"); setShowModal(true); }}
          className="px-4 py-2 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 transition cursor-pointer"
        >
          {t("sp.newStrategy", language)}
        </button>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* 온보딩 배너 */}
        <OnboardingBanner />

        {/* 실시간 토큰 가격 */}
        <div className="mb-8">
          <h2 className="text-xs font-semibold text-[#475569] uppercase tracking-wider mb-3">{t("sp.realtimePrices", language)}</h2>
          <TokenPrices />
        </div>

        {/* 탭 */}
        <div className="flex items-center gap-1 mb-8 bg-[#1E293B] rounded-lg p-1 w-fit">
          <button
            onClick={() => setActiveTab("my")}
            className={`px-5 py-2 text-sm font-semibold rounded-md transition cursor-pointer ${activeTab === "my"
                ? "bg-[#22D3EE] text-[#0A0F1C]"
                : "text-[#94A3B8] hover:text-white"
              }`}
          >
            {t("sp.myStrategies", language)}
            <span className="ml-1.5 text-xs opacity-70">({myStrategies.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("examples")}
            className={`px-5 py-2 text-sm font-semibold rounded-md transition cursor-pointer ${activeTab === "examples"
                ? "bg-[#22D3EE] text-[#0A0F1C]"
                : "text-[#94A3B8] hover:text-white"
              }`}
          >
            {t("sp.exampleTemplates", language)}
            <span className="ml-1.5 text-xs opacity-70">({exampleStrategies.length})</span>
          </button>
        </div>

        {/* 탭 설명 */}
        <p className="text-sm text-[#475569] mb-6">
          {activeTab === "examples"
            ? t("sp.examplesDesc", language)
            : t("sp.myDesc", language)}
        </p>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-5 rounded-xl bg-[#1E293B] border border-[#22D3EE10]">
                <Skeleton width="40%" height="1.25rem" className="mb-3" />
                <Skeleton width="80%" height="0.875rem" className="mb-2" />
                <div className="flex gap-4">
                  <Skeleton width="4rem" height="0.75rem" />
                  <Skeleton width="3rem" height="0.75rem" />
                </div>
              </div>
            ))}
          </div>
        ) : displayList.length === 0 ? (
          <div className="text-center py-20">
            <span className="text-5xl mb-4 block text-[#475569]">{activeTab === "examples" ? "--" : "+"}</span>
            <p className="text-[#94A3B8] mb-4">
              {activeTab === "examples"
                ? t("sp.noExamples", language)
                : t("sp.noStrategies", language)}
            </p>
            {activeTab === "my" && (
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={() => setActiveTab("examples")}
                  className="px-5 py-3 rounded-lg bg-[#1E293B] border border-[#22D3EE30] text-[#22D3EE] font-semibold hover:border-[#22D3EE60] transition cursor-pointer"
                >
                  {t("sp.viewExamples", language)}
                </button>
                <button
                  onClick={() => setShowModal(true)}
                  className="px-5 py-3 rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] font-semibold hover:opacity-90 transition cursor-pointer"
                >
                  {t("sp.createNew", language)}
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
                className="block p-5 rounded-xl bg-[#1E293B] border border-[#22D3EE10] hover:border-[#22D3EE40] transition-colors group relative"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white">{s.name}</h3>
                  <div className="flex items-center gap-2">
                    {activeTab === "examples" && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[#22D3EE]/10 text-[#22D3EE]">
                        {t("sp.template", language)}
                      </span>
                    )}
                    {activeTab === "my" && (
                      <button
                        onClick={(e) => handleDeleteStrategy(e, s.id)}
                        className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-[#EF4444]/20 transition cursor-pointer"
                        title={t("sp.deleteStrategy", language)}
                      >
                        <svg className="w-4 h-4 text-[#94A3B8] hover:text-[#EF4444]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-sm text-[#475569] line-clamp-2 mb-3">{s.raw_input}</p>
                <div className="flex items-center gap-4 text-xs text-[#475569]">
                  <span>{s.parsed_strategy.target_pair}</span>
                  <span>{s.parsed_strategy.timeframe}</span>
                  {activeTab === "my" && (
                    <span>{new Date(s.created_at).toLocaleDateString(language === "en" ? "en-US" : "ko-KR")}</span>
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
              <h2 className="text-lg font-bold text-white">{t("sp.modalTitle", language)}</h2>
              <button
                onClick={() => { setShowModal(false); setCreateError(""); setNewStrategyText(""); }}
                className="text-[#475569] hover:text-white transition cursor-pointer text-xl"
              >
                ✕
              </button>
            </div>

            <div className="px-6 py-5">
              <p className="text-sm text-[#94A3B8] mb-4">
                {t("sp.modalDesc", language)}
              </p>
              <textarea
                value={newStrategyText}
                onChange={e => setNewStrategyText(e.target.value)}
                placeholder={t("sp.modalPlaceholder", language)}
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
                {t("sp.cancel", language)}
              </button>
              <button
                onClick={handleCreateStrategy}
                disabled={creating || !newStrategyText.trim()}
                className="flex-1 py-3 text-sm font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
              >
                {creating ? t("sp.creating", language) : t("sp.createAndSave", language)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
    </AuthGuard>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getPublicStrategies,
  getPlatformInfo,
  getStrategyPerformance,
} from "@/lib/blockchainApi";
import type { PublicStrategy, PlatformInfo, StrategyPerformance } from "@/lib/blockchainApi";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

type SortKey = "newest" | "winRate" | "pnl" | "trades";

export default function MarketplacePage() {
  const { language } = useLanguageStore();
  const [strategies, setStrategies] = useState<PublicStrategy[]>([]);
  const [perfMap, setPerfMap] = useState<Record<string, StrategyPerformance>>({});
  const [platform, setPlatform] = useState<PlatformInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<SortKey>("newest");
  const [filterVerified, setFilterVerified] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [stratRes, platRes] = await Promise.all([
          getPublicStrategies(),
          getPlatformInfo().catch(() => null),
        ]);
        const strats = stratRes.strategies || [];
        setStrategies(strats);
        setPlatform(platRes);

        // 각 전략의 성과 데이터를 병렬 조회
        const perfs = await Promise.all(
          strats.map(s =>
            getStrategyPerformance(s.id).catch(() => null)
          )
        );
        const map: Record<string, StrategyPerformance> = {};
        perfs.forEach((p, i) => {
          if (p && p.total_trades > 0) map[strats[i].id] = p;
        });
        setPerfMap(map);
      } catch { /* API 에러 */ }
      finally { setLoading(false); }
    })();
  }, []);

  // 필터 + 정렬
  const filtered = strategies
    .filter(s => !filterVerified || s.onchain)
    .sort((a, b) => {
      const pa = perfMap[a.id];
      const pb = perfMap[b.id];
      switch (sortBy) {
        case "winRate": return (pb?.win_rate ?? 0) - (pa?.win_rate ?? 0);
        case "pnl": return (pb?.total_pnl ?? 0) - (pa?.total_pnl ?? 0);
        case "trades": return (pb?.total_trades ?? 0) - (pa?.total_trades ?? 0);
        default: return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  return (
    <div className="min-h-screen bg-[#0A0F1C] text-white">
      {/* 헤더 */}
      <header className="h-14 flex items-center px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">AI</span>
          </Link>
          <span className="text-[#475569]">/</span>
          <span className="text-sm text-white">{t("mp.title", language)}</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* 히어로 */}
        <div className="text-center space-y-3 mb-8">
          <h1 className="text-2xl font-bold">{t("mp.hero", language)}</h1>
          <p className="text-sm text-[#94A3B8] max-w-xl mx-auto">{t("mp.heroDesc", language)}</p>
        </div>

        {/* Platform 상태 배너 */}
        {platform?.initialized && (
          <div className="flex items-center justify-between bg-[#0F172A] rounded-lg border border-[#22D3EE20] px-4 py-2 mb-6 text-xs">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#22C55E] animate-pulse" />
                Solana Devnet
              </span>
              <span className="text-[#94A3B8]">
                {platform.strategy_count ?? 0} strategies on-chain
              </span>
              <span className="text-[#94A3B8]">
                Fee: {(platform.fee_bps ?? 0) / 100}%
              </span>
            </div>
            <span className="font-mono text-[#475569]">
              {platform.pda?.slice(0, 8)}...
            </span>
          </div>
        )}

        {/* 기능 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-2">
            <span className="text-2xl">🔗</span>
            <h3 className="text-sm font-bold">{t("mp.verifiedStrategies", language)}</h3>
            <p className="text-xs text-[#94A3B8]">{t("mp.verifiedDesc", language)}</p>
          </div>
          <div className="bg-[#1E293B] rounded-xl border border-[#9945FF20] p-5 space-y-2">
            <span className="text-2xl">📈</span>
            <h3 className="text-sm font-bold">{t("mp.signalHistory", language)}</h3>
            <p className="text-xs text-[#94A3B8]">{t("mp.signalDesc", language)}</p>
          </div>
          <div className="bg-[#1E293B] rounded-xl border border-[#14F19520] p-5 space-y-2">
            <span className="text-2xl">🤝</span>
            <h3 className="text-sm font-bold">{t("mp.copyTrading", language)}</h3>
            <p className="text-xs text-[#94A3B8]">{t("mp.copyDesc", language)}</p>
          </div>
        </div>

        {/* 필터/정렬 바 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold">{t("mp.publicStrategies", language)}</h2>
            <span className="text-xs text-[#475569]">{filtered.length} {t("mp.strategiesCount", language)}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterVerified(!filterVerified)}
              className={`text-[10px] px-3 py-1 rounded-full border transition ${
                filterVerified
                  ? "bg-[#14F195]/10 text-[#14F195] border-[#14F195]/30"
                  : "bg-transparent text-[#94A3B8] border-[#1E293B] hover:border-[#475569]"
              }`}
            >
              ✓ Verified Only
            </button>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as SortKey)}
              className="text-[10px] px-2 py-1 rounded-lg bg-[#0F172A] border border-[#1E293B] text-[#94A3B8] outline-none"
            >
              <option value="newest">Newest</option>
              <option value="winRate">Win Rate</option>
              <option value="pnl">Total PnL</option>
              <option value="trades">Most Trades</option>
            </select>
          </div>
        </div>

        {/* 전략 목록 */}
        {loading ? (
          <div className="text-center py-12 text-[#475569]">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-12 text-center space-y-4">
            <span className="text-4xl">🏪</span>
            <p className="text-sm text-[#94A3B8]">{t("mp.noPublicStrategies", language)}</p>
            <p className="text-xs text-[#475569]">{t("mp.noPublicDesc", language)}</p>
            <Link
              href="/chat"
              className="inline-block px-4 py-2 text-xs font-semibold rounded-lg gradient-accent text-[#0A0F1C] hover:opacity-90 transition"
            >
              {t("mp.createAndMint", language)}
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(s => {
              const ps = s.parsed_strategy || {};
              const perf = perfMap[s.id];
              return (
                <Link
                  key={s.id}
                  href={`/marketplace/${s.id}`}
                  className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-3 hover:border-[#22D3EE50] transition group"
                >
                  {/* 헤더 */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-base">📊</span>
                      <h3 className="font-semibold text-sm text-white truncate">{s.name}</h3>
                    </div>
                    {s.onchain && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#14F195]/10 text-[#14F195] border border-[#14F195]/30 shrink-0">
                        ✓ Verified
                      </span>
                    )}
                  </div>

                  {/* 태그 */}
                  <div className="flex flex-wrap gap-1.5 text-[10px]">
                    {Boolean(ps.leverage) && Number(ps.leverage) > 1 && (
                      <span className="px-2 py-0.5 rounded bg-[#F59E0B]/10 text-[#F59E0B]">{Number(ps.leverage)}x</span>
                    )}
                    {Boolean(ps.direction) && (
                      <span className="px-2 py-0.5 rounded bg-[#A78BFA]/10 text-[#A78BFA]">{String(ps.direction)}</span>
                    )}
                    {Boolean(ps.timeframe) && (
                      <span className="px-2 py-0.5 rounded bg-[#22D3EE]/10 text-[#22D3EE]">{String(ps.timeframe)}</span>
                    )}
                    {Boolean(ps.target_pair) && (
                      <span className="px-2 py-0.5 rounded bg-[#475569]/30 text-[#94A3B8]">{String(ps.target_pair)}</span>
                    )}
                  </div>

                  {/* 성과 데이터 */}
                  {perf ? (
                    <div className="grid grid-cols-3 gap-2 bg-[#0F172A] rounded-lg p-3">
                      <div className="text-center">
                        <div className={`text-sm font-bold ${perf.win_rate >= 50 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                          {perf.win_rate}%
                        </div>
                        <div className="text-[9px] text-[#475569]">Win Rate</div>
                      </div>
                      <div className="text-center">
                        <div className={`text-sm font-bold ${perf.total_pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                          {perf.total_pnl >= 0 ? "+" : ""}{perf.total_pnl.toFixed(1)}%
                        </div>
                        <div className="text-[9px] text-[#475569]">Total PnL</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm font-bold text-white">{perf.total_trades}</div>
                        <div className="text-[9px] text-[#475569]">Trades</div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-[#0F172A] rounded-lg p-3 text-center">
                      <span className="text-[10px] text-[#475569]">No performance data yet</span>
                    </div>
                  )}

                  {/* 온체인 해시 */}
                  {s.onchain && (
                    <div className="text-[10px] text-[#475569] font-mono truncate">
                      Hash: {s.onchain.strategy_hash.slice(0, 24)}...
                    </div>
                  )}

                  {/* CTA */}
                  <div className="pt-1">
                    <span className="block py-1.5 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#22D3EE] border border-[#22D3EE20] text-center group-hover:bg-[#22D3EE10] transition">
                      View Details →
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

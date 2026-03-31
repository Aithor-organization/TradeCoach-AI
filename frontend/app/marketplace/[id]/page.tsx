"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getStrategyPerformance,
  getStrategyTradeHistory,
  getStrategyTxHistory,
  verifyStrategy,
  purchaseStrategy,
  rentStrategy,
} from "@/lib/blockchainApi";
import type { StrategyPerformance, TradeHistoryResponse, OnchainTxRecord } from "@/lib/blockchainApi";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StrategyDetail {
  id: string;
  name: string;
  parsed_strategy: Record<string, unknown>;
  created_at: string;
  onchain: { asset_id: string; strategy_hash: string } | null;
  marketplace_summary?: string;
  marketplace_metrics?: {
    total_sessions: number;
    total_trades: number;
    winning_trades: number;
    win_rate: number;
    total_pnl: number;
    avg_session_pnl: number;
  };
}

export default function MarketplaceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [strategy, setStrategy] = useState<StrategyDetail | null>(null);
  const [perf, setPerf] = useState<StrategyPerformance | null>(null);
  const [trades, setTrades] = useState<TradeHistoryResponse | null>(null);
  const [verification, setVerification] = useState<{ verified: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "trades" | "onchain">("overview");
  const [onchainTxs, setOnchainTxs] = useState<OnchainTxRecord[]>([]);
  const [purchasing, setPurchasing] = useState(false);
  const [renting, setRenting] = useState(false);
  const [txResult, setTxResult] = useState<{ type: string; tx: string; url: string } | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        // 전략 기본 정보 조회 (공개 API, 인증 불필요, IP 보호)
        const res = await fetch(`${API_URL}/strategy/public/${id}`);
        if (res.ok) setStrategy(await res.json());

        // 병렬로 성과 + 거래 히스토리 + TX 히스토리 조회
        const [perfRes, tradeRes, txRes] = await Promise.all([
          getStrategyPerformance(id).catch(() => null),
          getStrategyTradeHistory(id, 100).catch(() => null),
          getStrategyTxHistory(id).catch(() => null),
        ]);
        if (perfRes && perfRes.total_trades > 0) setPerf(perfRes);
        if (tradeRes) setTrades(tradeRes);
        if (txRes?.transactions) setOnchainTxs(txRes.transactions);
      } catch { /* 에러 무시 */ }
      finally { setLoading(false); }
    })();
  }, [id]);

  const handleVerify = async () => {
    if (!id) return;
    try {
      const result = await verifyStrategy(id);
      setVerification(result);
    } catch { setVerification({ verified: false }); }
  };

  const handlePurchase = async () => {
    if (!strategy?.onchain) return;
    setPurchasing(true);
    try {
      const result = await purchaseStrategy(
        strategy.onchain.asset_id,
        strategy.onchain.asset_id, // owner = strategy PDA for devnet
      );
      setTxResult({ type: "Purchase", tx: result.tx_signature, url: result.explorer_url });
    } catch (e) {
      alert(`Purchase failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    } finally { setPurchasing(false); }
  };

  const handleRent = async () => {
    if (!strategy?.onchain) return;
    setRenting(true);
    try {
      const result = await rentStrategy(strategy.onchain.asset_id, 30);
      setTxResult({ type: "Rent (30d)", tx: result.tx_signature, url: result.explorer_url });
    } catch (e) {
      alert(`Rent failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    } finally { setRenting(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] flex items-center justify-center">
        <div className="text-[#475569]">Loading...</div>
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="min-h-screen bg-[#0A0F1C] flex items-center justify-center">
        <div className="text-center space-y-4">
          <span className="text-4xl">🔍</span>
          <p className="text-[#94A3B8]">Strategy not found</p>
          <Link href="/marketplace" className="text-xs text-[#22D3EE] hover:underline">
            ← Back to Marketplace
          </Link>
        </div>
      </div>
    );
  }

  const ps = strategy.parsed_strategy || {};
  const tradeList = trades?.trades || [];

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
          <Link href="/marketplace" className="text-sm text-[#94A3B8] hover:text-white transition">
            Marketplace
          </Link>
          <span className="text-[#475569]">/</span>
          <span className="text-sm text-white truncate max-w-[200px]">{strategy.name}</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* 전략 헤더 카드 */}
        <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold">{strategy.name}</h1>
                {strategy.onchain && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#14F195]/10 text-[#14F195] border border-[#14F195]/30">
                    ✓ On-Chain Verified
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-2 text-[10px]">
                {Boolean(ps.leverage) && Number(ps.leverage) > 1 && (
                  <span className="px-2 py-0.5 rounded bg-[#F59E0B]/10 text-[#F59E0B]">{Number(ps.leverage)}x Leverage</span>
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
            </div>
            <div className="flex gap-2">
              {strategy.onchain && (
                <>
                  <button
                    onClick={handlePurchase}
                    disabled={purchasing}
                    className="px-4 py-2 text-xs font-semibold rounded-lg gradient-accent text-[#0A0F1C] hover:opacity-90 transition disabled:opacity-50"
                  >
                    {purchasing ? "Processing..." : "Buy (0.1 SOL)"}
                  </button>
                  <button
                    onClick={handleRent}
                    disabled={renting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#9945FF] text-white hover:opacity-90 transition disabled:opacity-50"
                  >
                    {renting ? "Processing..." : "Rent 30d (0.3 SOL)"}
                  </button>
                </>
              )}
              {/* 전략 상세는 구매 후에만 공개 */}
            </div>
          </div>

          {/* 성과 요약 그리드 */}
          {/* TX 결과 배너 */}
          {txResult && (
            <div className="bg-[#22C55E]/10 border border-[#22C55E]/30 rounded-lg p-3 flex items-center justify-between mb-3">
              <span className="text-xs text-[#22C55E] font-semibold">{txResult.type} successful!</span>
              <a href={txResult.url} target="_blank" rel="noopener noreferrer" className="text-[10px] font-mono text-[#22D3EE] hover:underline">
                {txResult.tx.slice(0, 20)}... →
              </a>
            </div>
          )}

          {perf ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <StatCard label="Win Rate" value={`${perf.win_rate}%`} positive={perf.win_rate >= 50} />
              <StatCard label="Total PnL" value={`${perf.total_pnl >= 0 ? "+" : ""}${perf.total_pnl.toFixed(2)}%`} positive={perf.total_pnl >= 0} />
              <StatCard label="Total Trades" value={String(perf.total_trades)} />
              <StatCard label="Max Drawdown" value={`${perf.max_drawdown.toFixed(2)}%`} positive={false} />
              <StatCard label="Sessions" value={String(perf.sessions)} />
            </div>
          ) : (
            <div className="bg-[#0F172A] rounded-lg p-6 text-center">
              <span className="text-sm text-[#475569]">No performance data yet — start demo trading to generate metrics</span>
            </div>
          )}
        </div>

        {/* 탭 네비게이션 */}
        <div className="flex gap-1 bg-[#0F172A] rounded-lg p-1">
          {(["overview", "trades", "onchain"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition ${
                activeTab === tab
                  ? "bg-[#1E293B] text-white"
                  : "text-[#475569] hover:text-[#94A3B8]"
              }`}
            >
              {tab === "overview" ? "📊 Overview" : tab === "trades" ? "📋 Trade History" : "🔗 On-Chain"}
            </button>
          ))}
        </div>

        {/* 탭 콘텐츠 */}
        {activeTab === "overview" && (
          <OverviewTab ps={ps} perf={perf} tradeCount={tradeList.length} aiSummary={strategy?.marketplace_summary} mpMetrics={strategy?.marketplace_metrics} />
        )}

        {activeTab === "trades" && (
          <TradesTab trades={tradeList} />
        )}

        {activeTab === "onchain" && (
          <OnChainTab
            strategy={strategy}
            perf={perf}
            verification={verification}
            onVerify={handleVerify}
            onchainTxs={onchainTxs}
          />
        )}
      </main>
    </div>
  );
}

// ─── 하위 컴포넌트 ───

function StatCard({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  const color = positive === undefined ? "text-white" : positive ? "text-[#22C55E]" : "text-[#EF4444]";
  return (
    <div className="bg-[#0F172A] rounded-lg p-3 text-center">
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      <div className="text-[9px] text-[#475569] mt-0.5">{label}</div>
    </div>
  );
}

function OverviewTab({ ps, perf, tradeCount, aiSummary, mpMetrics }: {
  ps: Record<string, unknown>;
  perf: StrategyPerformance | null;
  tradeCount: number;
  aiSummary?: string;
  mpMetrics?: StrategyDetail["marketplace_metrics"];
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* 전략 요약 (상세 내용은 숨김) */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-3">
        <h3 className="text-sm font-bold">Strategy Overview</h3>
        <div className="space-y-2 text-xs">
          {Boolean(ps.timeframe) && <InfoRow label="Timeframe" value={String(ps.timeframe)} />}
          {Boolean(ps.target_pair) && <InfoRow label="Target Pair" value={String(ps.target_pair)} />}
          {Boolean(ps.market_type) && <InfoRow label="Market" value={String(ps.market_type)} />}
          {Boolean(ps.leverage) && <InfoRow label="Leverage" value={`${ps.leverage}x`} />}
          {Boolean(ps.direction) && <InfoRow label="Direction" value={String(ps.direction)} />}
          <InfoRow
            label="Indicators"
            value={`${((ps.entry as Record<string, unknown>)?.conditions as unknown[])?.length ?? "?"} conditions`}
          />
        </div>
        <div className="mt-4 p-3 bg-[#0F172A] rounded-lg border border-[#F59E0B20]">
          <p className="text-[10px] text-[#F59E0B]">
            Strategy details (entry/exit conditions) are hidden to protect intellectual property.
            Purchase or rent to access the full strategy.
          </p>
        </div>
      </div>

      {/* 성과 분석 */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-3">
        <h3 className="text-sm font-bold">Performance Analysis</h3>
        {perf ? (
          <div className="space-y-3">
            <ProgressBar label="Win Rate" value={perf.win_rate} max={100} color="#22C55E" />
            <ProgressBar label="Winning Trades" value={perf.winning_trades} max={perf.total_trades} color="#22D3EE" />
            <div className="grid grid-cols-2 gap-2 text-xs mt-3">
              <div className="bg-[#0F172A] rounded p-2">
                <span className="text-[#475569]">Sessions: </span>
                <span className="text-white font-semibold">{perf.sessions}</span>
              </div>
              <div className="bg-[#0F172A] rounded p-2">
                <span className="text-[#475569]">Period: </span>
                <span className="text-white font-semibold">{perf.period_days ?? "—"}d</span>
              </div>
              <div className="bg-[#0F172A] rounded p-2">
                <span className="text-[#475569]">Max DD: </span>
                <span className="text-[#EF4444] font-semibold">{perf.max_drawdown}%</span>
              </div>
              <div className="bg-[#0F172A] rounded p-2">
                <span className="text-[#475569]">Total PnL: </span>
                <span className={`font-semibold ${perf.total_pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                  {perf.total_pnl >= 0 ? "+" : ""}{perf.total_pnl}%
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-[#475569] py-4 text-center">
            No performance data yet. The creator needs to run demo trading.
          </div>
        )}
      </div>

      {/* 거래 요약 + 신뢰도 분석 */}
      <div className="md:col-span-2 bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold">Track Record</h3>
          <span className="text-[10px] text-[#475569]">{tradeCount} trades recorded</span>
        </div>
        {perf && perf.total_trades > 0 ? (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-[#0F172A] rounded-lg p-3">
                <div className="text-lg font-bold text-white">{perf.total_trades}</div>
                <div className="text-[9px] text-[#475569]">Total Trades</div>
              </div>
              <div className="bg-[#0F172A] rounded-lg p-3">
                <div className={`text-lg font-bold ${perf.win_rate >= 50 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                  {perf.win_rate}%
                </div>
                <div className="text-[9px] text-[#475569]">Win Rate</div>
              </div>
              <div className="bg-[#0F172A] rounded-lg p-3">
                <div className={`text-lg font-bold ${perf.total_pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                  {perf.total_pnl >= 0 ? "+" : ""}{perf.total_pnl}%
                </div>
                <div className="text-[9px] text-[#475569]">Total PnL</div>
              </div>
            </div>
            {perf.verified && (
              <div className="flex items-center gap-2 p-2 bg-[#14F195]/10 rounded-lg">
                <span className="text-[#14F195] text-xs font-semibold">Verified on Solana</span>
                <span className="text-[9px] text-[#475569]">Track record is immutable and verifiable on-chain</span>
              </div>
            )}
            {perf.tx_signatures && perf.tx_signatures.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {perf.tx_signatures.slice(0, 5).map((sig, i) => (
                  <a
                    key={i}
                    href={`https://explorer.solana.com/tx/${sig}?cluster=devnet`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] font-mono px-2 py-1 rounded bg-[#0F172A] text-[#22D3EE] hover:bg-[#22D3EE10] transition"
                  >
                    TX #{i + 1}: {sig.slice(0, 12)}...
                  </a>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-[#475569] py-4 text-center">
            No trading records yet. Check the Trade History tab for backtest results.
          </div>
        )}
      </div>

      {/* AI 분석 보고서 */}
      {aiSummary && (
        <div className="md:col-span-2 bg-[#1E293B] rounded-xl border border-[#9945FF20] p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">🤖</span>
            <h3 className="text-sm font-bold">AI Strategy Analysis</h3>
          </div>
          <div className="prose prose-sm prose-invert max-w-none text-[#94A3B8] text-xs leading-relaxed whitespace-pre-line">
            {aiSummary}
          </div>
        </div>
      )}
    </div>
  );
}

function TradesTab({ trades }: { trades: Array<Record<string, unknown>> }) {
  if (trades.length === 0) {
    return (
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-12 text-center">
        <span className="text-4xl">📋</span>
        <p className="text-sm text-[#94A3B8] mt-3">No trade history yet</p>
      </div>
    );
  }

  return (
    <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#0F172A] text-[#475569]">
              <th className="text-left p-3 font-medium">#</th>
              <th className="text-left p-3 font-medium">Symbol</th>
              <th className="text-left p-3 font-medium">Side</th>
              <th className="text-right p-3 font-medium">PnL</th>
              <th className="text-left p-3 font-medium">Exit Reason</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, i) => {
              const pnl = Number(trade.pnl ?? 0);
              return (
                <tr key={i} className="border-b border-[#0F172A]/50 hover:bg-[#0F172A]/30">
                  <td className="p-3 text-[#475569]">{i + 1}</td>
                  <td className="p-3 font-mono">{String(trade.symbol ?? "—")}</td>
                  <td className="p-3">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      String(trade.side).toLowerCase() === "long"
                        ? "bg-[#22C55E]/10 text-[#22C55E]"
                        : "bg-[#EF4444]/10 text-[#EF4444]"
                    }`}>
                      {String(trade.side ?? "—")}
                    </span>
                  </td>
                  <td className={`p-3 text-right font-mono font-semibold ${pnl >= 0 ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                    {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}%
                  </td>
                  <td className="p-3 text-[#94A3B8]">{String(trade.exit_reason ?? "—")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OnChainTab({ strategy, perf, verification, onVerify, onchainTxs }: {
  strategy: StrategyDetail;
  perf: StrategyPerformance | null;
  verification: { verified: boolean } | null;
  onVerify: () => void;
  onchainTxs: OnchainTxRecord[];
}) {
  const hasTxs = onchainTxs.length > 0 || (perf?.tx_signatures && perf.tx_signatures.length > 0);

  return (
    <div className="space-y-4">
      {/* 온체인 상태 */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-4">
        <h3 className="text-sm font-bold">On-Chain Status</h3>

        {strategy.onchain ? (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-[#0F172A] rounded-lg p-3">
                <div className="text-[#475569] mb-1">Asset ID</div>
                <div className="font-mono text-[#22D3EE] break-all">{strategy.onchain.asset_id}</div>
              </div>
              <div className="bg-[#0F172A] rounded-lg p-3">
                <div className="text-[#475569] mb-1">Strategy Hash</div>
                <div className="font-mono text-[#94A3B8] break-all">{strategy.onchain.strategy_hash}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={onVerify}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#0F172A] text-[#22D3EE] border border-[#22D3EE20] hover:bg-[#22D3EE10] transition"
              >
                🔍 Verify Integrity
              </button>
              {verification && (
                <span className={`text-xs font-semibold ${verification.verified ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                  {verification.verified ? "✓ Integrity Verified" : "✗ Verification Failed"}
                </span>
              )}
            </div>
          </div>
        ) : hasTxs ? (
          <div className="bg-[#0F172A] rounded-lg p-4 text-center text-xs">
            <span className="text-[#14F195]">⛓️ {onchainTxs.length} on-chain transactions found</span>
            <div className="text-[#475569] mt-1">Registered via Anchor instruction on Solana Devnet</div>
          </div>
        ) : (
          <div className="bg-[#0F172A] rounded-lg p-6 text-center text-xs text-[#475569]">
            This strategy has not been registered on-chain yet
          </div>
        )}
      </div>

      {/* TX 히스토리 (온체인 직접 조회) */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-3">
        <h3 className="text-sm font-bold">Transaction History</h3>
        {onchainTxs.length > 0 ? (
          <div className="space-y-2">
            {onchainTxs.map((tx, i) => (
              <a
                key={i}
                href={tx.explorer_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between bg-[#0F172A] rounded-lg p-3 hover:bg-[#0F172A]/80 transition group"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[#22D3EE] text-xs">TX #{i + 1}</span>
                  <span className="font-mono text-[10px] text-[#94A3B8]">{tx.tx_signature.slice(0, 28)}...</span>
                  {tx.block_time && (
                    <span className="text-[8px] text-[#475569]">{new Date(tx.block_time * 1000).toLocaleDateString()}</span>
                  )}
                </div>
                <span className="text-[10px] text-[#475569] group-hover:text-[#22D3EE] transition">Explorer →</span>
              </a>
            ))}
          </div>
        ) : perf?.tx_signatures && perf.tx_signatures.length > 0 ? (
          <div className="space-y-2">
            {perf.tx_signatures.map((sig, i) => (
              <a
                key={i}
                href={`https://explorer.solana.com/tx/${sig}?cluster=devnet`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between bg-[#0F172A] rounded-lg p-3 hover:bg-[#0F172A]/80 transition group"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[#22D3EE] text-xs">TX #{i + 1}</span>
                  <span className="font-mono text-[10px] text-[#94A3B8]">{sig.slice(0, 28)}...</span>
                </div>
                <span className="text-[10px] text-[#475569] group-hover:text-[#22D3EE] transition">Explorer →</span>
              </a>
            ))}
          </div>
        ) : (
          <div className="text-xs text-[#475569] text-center py-4">No transactions recorded yet</div>
        )}
      </div>

      {/* Merkle Proof 설명 */}
      <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-5 space-y-3">
        <h3 className="text-sm font-bold">Merkle Proof Verification</h3>
        <p className="text-xs text-[#94A3B8]">
          Every trading session records a Merkle root on Solana. Individual trades can be verified
          against this root using cryptographic proofs, ensuring no trade data was tampered with
          after recording.
        </p>
        <div className="flex items-center gap-2 text-[10px]">
          <span className="px-2 py-1 rounded bg-[#22C55E]/10 text-[#22C55E]">SHA-256 Hashing</span>
          <span className="px-2 py-1 rounded bg-[#22D3EE]/10 text-[#22D3EE]">Binary Merkle Tree</span>
          <span className="px-2 py-1 rounded bg-[#9945FF]/10 text-[#9945FF]">On-Chain Root</span>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1 border-b border-[#0F172A]">
      <span className="text-[#475569]">{label}</span>
      <span className="text-white font-medium">{value}</span>
    </div>
  );
}

function ProgressBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-[#94A3B8]">{label}</span>
        <span className="text-white font-semibold">{value}/{max}</span>
      </div>
      <div className="h-1.5 bg-[#0F172A] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

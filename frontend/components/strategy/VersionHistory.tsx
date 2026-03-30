"use client";

import { useEffect, useState } from "react";
import { getStrategyVersions, restoreStrategyVersion, type StrategyVersion } from "@/lib/api";
import { getExplorerUrl } from "@/lib/solanaUtils";

interface VersionHistoryProps {
  strategyId: string;
  currentStatus?: string;
  onRestore?: () => void;
  refreshKey?: number;
}

export default function VersionHistory({ strategyId, currentStatus, onRestore, refreshKey = 0 }: VersionHistoryProps) {
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!strategyId || strategyId.startsWith("example-")) return;
    getStrategyVersions(strategyId)
      .then((res) => {
        setVersions(res.versions || []);
        if (refreshKey > 0) setExpanded(true);
      })
      .catch(() => {});
  }, [strategyId, refreshKey]);

  if (versions.length === 0) return null;

  const handleRestore = async (versionId: string) => {
    if (!confirm("이 버전으로 전략을 되돌리시겠습니까?")) return;
    setRestoring(versionId);
    try {
      await restoreStrategyVersion(strategyId, versionId);
      onRestore?.();
      window.location.reload();
    } catch (e) {
      console.error("Restore failed:", e);
    } finally {
      setRestoring(null);
    }
  };

  return (
    <div className="rounded-lg border border-[#9945FF20] bg-[#0F172A] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-[#9945FF08] transition"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#9945FF20] text-[#9945FF] font-bold">
            {versions.length}
          </span>
          <span className="text-xs text-[#94A3B8]">Minted Versions</span>
        </div>
        <span className="text-[#475569] text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="border-t border-[#1E293B] max-h-48 overflow-y-auto">
          {versions.map((v) => (
            <div
              key={v.id}
              className="flex items-center justify-between px-4 py-2 border-b border-[#1E293B] last:border-0 hover:bg-[#1E293B40]"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-[11px] font-mono text-[#9945FF] font-bold shrink-0">
                  v{v.version}
                </span>
                <span className="text-[11px] text-[#94A3B8] truncate">
                  {v.label || `Version ${v.version}`}
                </span>
                <span className="text-[9px] text-[#475569] shrink-0">
                  {new Date(v.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-2">
                {v.mint_tx && (
                  <a
                    href={getExplorerUrl(v.mint_tx, v.mint_network || "devnet")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[9px] text-[#14F195] hover:underline"
                  >
                    TX
                  </a>
                )}
                {currentStatus !== "verified" && (
                  <button
                    onClick={() => handleRestore(v.id)}
                    disabled={restoring === v.id}
                    className="text-[9px] px-2 py-0.5 rounded bg-[#9945FF20] text-[#9945FF] hover:bg-[#9945FF30] disabled:opacity-50 cursor-pointer transition"
                  >
                    {restoring === v.id ? "..." : "Restore"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

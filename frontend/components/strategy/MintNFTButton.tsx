"use client";

import { useEffect, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useConnection } from "@solana/wallet-adapter-react";
import { WalletReadyState } from "@solana/wallet-adapter-base";
import { prepareMintStrategy, confirmMint } from "@/lib/blockchainApi";
import { buildMemoTransaction, confirmTransaction, getExplorerUrl } from "@/lib/solanaUtils";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import type { ParsedStrategy } from "@/lib/types";
import { useToast } from "@/components/common/Toast";

interface MintNFTButtonProps {
  strategyId: string;
  strategy: ParsedStrategy;
  status?: string;
  onMintComplete?: () => void;
}

export default function MintNFTButton({ strategyId, strategy, status: initialStatus, onMintComplete }: MintNFTButtonProps) {
  const { publicKey, connected, sendTransaction, select, wallets } = useWallet();
  const { connection } = useConnection();
  const { language } = useLanguageStore();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ hash: string; signature: string; network: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [minted, setMinted] = useState(initialStatus === "verified");
  const { showToast } = useToast();

  // props 변경 시 minted 상태 동기화 (전략 수정 → status "draft"로 리셋)
  useEffect(() => {
    setMinted(initialStatus === "verified");
  }, [initialStatus]);

  const handleMint = async () => {
    if (!connected || !publicKey || !sendTransaction) {
      // 지갑 미연결 시 Phantom 자동 연결 시도
      const phantom = wallets.find(
        (w) =>
          w.adapter.name === "Phantom" &&
          (w.readyState === WalletReadyState.Installed ||
           w.readyState === WalletReadyState.Loadable)
      );
      if (phantom) {
        try { select(phantom.adapter.name); } catch { /* 사용자 취소 */ }
      } else {
        window.open("https://phantom.app/", "_blank");
        setError(t("bc.connectWalletFirst", language));
      }
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // 1. 백엔드에서 메타데이터 + 해시 준비
      const res = await prepareMintStrategy(
        strategyId,
        strategy as unknown as Record<string, unknown>,
      );

      // 2. Memo 트랜잭션 빌드 (전략 해시를 온체인에 기록)
      const memo = `TCAI:${res.strategy_hash}:${strategyId}`;
      const tx = await buildMemoTransaction(connection, publicKey, memo);

      // 3. Phantom 지갑으로 서명 + 전송
      const signature = await sendTransaction(tx, connection);

      // 4. 트랜잭션 확인 대기
      const confirmed = await confirmTransaction(connection, signature);

      if (confirmed) {
        // 백엔드에 민팅 완료 확인 → DB에 verified 상태 저장
        try {
          await confirmMint(strategyId, signature, res.strategy_hash, res.network);
        } catch (err) {
          console.warn("Failed to confirm mint status:", err);
        }
        setMinted(true);
        setResult({
          hash: res.strategy_hash,
          signature,
          network: res.network,
        });
        onMintComplete?.();
      } else {
        setError(t("bc.mintFailed", language));
      }
    } catch (e) {
      showToast("Minting failed", "error");
      setError(e instanceof Error ? e.message : t("bc.mintFailed", language));
    } finally {
      setLoading(false);
    }
  };

  // 이미 민팅된 전략 (DB에서 로드 시)
  if (minted && !result) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#9945FF]/10 border border-[#9945FF]/30">
        <span className="text-[#14F195] text-xs font-semibold">Verified on Solana</span>
        <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#14F195]/20 text-[#14F195] font-bold">NFT</span>
      </div>
    );
  }

  // 방금 민팅 완료 (시그니처 포함)
  if (result) {
    return (
      <div className="space-y-1">
        <a
          href={getExplorerUrl(result.signature, result.network)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#9945FF]/10 border border-[#9945FF]/30 hover:bg-[#9945FF]/20 transition"
        >
          <span className="text-[#14F195] text-xs font-semibold">Verified on Solana</span>
          <span className="text-[10px] text-[#94A3B8] font-mono">{result.signature.slice(0, 8)}...</span>
        </a>
        <p className="text-[9px] text-[#475569]">
          {t("bc.viewOnExplorer", language)}
        </p>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={handleMint}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white cursor-pointer hover:opacity-90 disabled:opacity-50 transition"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {t("bc.minting", language)}
          </span>
        ) : connected ? t("bc.mintAsNFT", language) : t("bc.connectWallet", language)}
      </button>
      {error && (
        <p className="text-[10px] text-[#EF4444] mt-1">{error}</p>
      )}
    </div>
  );
}

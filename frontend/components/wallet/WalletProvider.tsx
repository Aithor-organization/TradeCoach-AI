"use client";

import { useMemo, useCallback, ReactNode } from "react";
import { ConnectionProvider, WalletProvider as SolanaWalletProvider } from "@solana/wallet-adapter-react";
import { WalletError } from "@solana/wallet-adapter-base";

const RPC_URL = process.env.NEXT_PUBLIC_SOLANA_RPC || "https://api.mainnet-beta.solana.com";

export default function WalletProvider({ children }: { children: ReactNode }) {
  // Phantom은 Wallet Standard를 지원하므로 수동 어댑터 불필요 (자동 감지됨)
  const wallets = useMemo(() => [], []);

  // 지갑 에러를 조용히 처리 (User rejected 등은 정상 흐름)
  const onError = useCallback((error: WalletError) => {
    // 사용자 거절은 콘솔에 노출하지 않음
    if (error.name === "WalletConnectionError" || error.name === "WalletNotSelectedError") {
      return;
    }
    console.error("[Wallet]", error.message);
  }, []);

  return (
    <ConnectionProvider endpoint={RPC_URL}>
      <SolanaWalletProvider wallets={wallets} autoConnect onError={onError}>
        {children}
      </SolanaWalletProvider>
    </ConnectionProvider>
  );
}

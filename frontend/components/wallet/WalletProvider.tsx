"use client";

import { useMemo, useCallback, ReactNode } from "react";
import { ConnectionProvider, WalletProvider as SolanaWalletProvider } from "@solana/wallet-adapter-react";
import { WalletError } from "@solana/wallet-adapter-base";

const RPC_URL = process.env.NEXT_PUBLIC_SOLANA_RPC || "https://api.mainnet-beta.solana.com";

export default function WalletProvider({ children }: { children: ReactNode }) {
  const wallets = useMemo(() => [], []);

  // 429 방지: commitment을 confirmed로, wsEndpoint를 비활성화하여 불필요한 WebSocket 연결 차단
  const connectionConfig = useMemo(() => ({
    commitment: "confirmed" as const,
    wsEndpoint: "",  // WebSocket 구독 비활성화 → RPC 요청 대폭 감소
    confirmTransactionInitialTimeout: 60000,
  }), []);

  const onError = useCallback((error: WalletError) => {
    if (error.name === "WalletConnectionError" || error.name === "WalletNotSelectedError") {
      return;
    }
    console.error("[Wallet]", error.message);
  }, []);

  return (
    <ConnectionProvider endpoint={RPC_URL} config={connectionConfig}>
      <SolanaWalletProvider wallets={wallets} autoConnect onError={onError}>
        {children}
      </SolanaWalletProvider>
    </ConnectionProvider>
  );
}

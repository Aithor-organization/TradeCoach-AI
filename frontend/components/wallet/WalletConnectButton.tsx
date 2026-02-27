"use client";

import { useWallet } from "@solana/wallet-adapter-react";
import { WalletReadyState } from "@solana/wallet-adapter-base";
import { useCallback, useEffect, useState } from "react";
import { requestNonce, verifyWallet } from "@/lib/api";
import WalletBalance from "./WalletBalance";

export default function WalletConnectButton() {
  const { publicKey, select, disconnect, connected, connecting, wallets, wallet } = useWallet();
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = useCallback(async () => {
    if (connected && publicKey) {
      disconnect();
      localStorage.removeItem("tc_token");
      setError(null);
      return;
    }

    // Phantom 지갑 찾기 (설치 + 로드 가능 상태)
    const phantom = wallets.find(
      (w) =>
        w.adapter.name === "Phantom" &&
        (w.readyState === WalletReadyState.Installed ||
         w.readyState === WalletReadyState.Loadable)
    );

    if (!phantom) {
      window.open("https://phantom.app/", "_blank");
      setError("Phantom을 설치해주세요");
      setTimeout(() => setError(null), 5000);
      return;
    }

    try {
      // select()만 호출 - WalletProvider의 autoConnect가 자동으로 연결 처리
      // connect()를 직접 호출하면 select 상태 업데이트 전에 실행되어 WalletNotSelectedError 발생
      select(phantom.adapter.name);
      setError(null);
    } catch {
      setError("연결 취소됨");
      setTimeout(() => setError(null), 3000);
    }
  }, [connected, publicKey, disconnect, select, wallets]);

  // 지갑 연결 후 자동 인증
  useEffect(() => {
    if (!connected || !publicKey || isAuthenticating) return;
    if (typeof window !== "undefined" && localStorage.getItem("tc_token")) return;

    const doAuth = async () => {
      setIsAuthenticating(true);
      try {
        const address = publicKey.toBase58();
        const { nonce } = (await requestNonce(address)) as { nonce: string };
        const res = (await verifyWallet(address, nonce, nonce)) as { access_token: string };
        localStorage.setItem("tc_token", res.access_token);
      } catch {
        // 인증 실패 시 조용히 넘어감 (MVP)
      } finally {
        setIsAuthenticating(false);
      }
    };
    doAuth();
  }, [connected, publicKey, isAuthenticating]);

  const shortenAddress = (addr: string) =>
    `${addr.slice(0, 4)}...${addr.slice(-4)}`;

  return (
    <div className="relative">
      <button
        onClick={handleConnect}
        disabled={connecting || isAuthenticating}
        className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-200 cursor-pointer bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white hover:opacity-90 disabled:opacity-50"
      >
        {connecting || isAuthenticating
          ? "연결 중..."
          : connected && publicKey
            ? (<>{shortenAddress(publicKey.toBase58())} <WalletBalance /></>)
            : "🔮 Phantom 연결"}
      </button>
      {error && (
        <div className="absolute top-full right-0 mt-2 px-3 py-1.5 text-xs bg-[#EF4444] text-white rounded-lg whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
}

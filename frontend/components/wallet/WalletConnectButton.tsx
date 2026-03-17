"use client";

import { useWallet } from "@solana/wallet-adapter-react";
import { WalletReadyState } from "@solana/wallet-adapter-base";
import { useCallback, useEffect, useState } from "react";
import { requestNonce, verifyWallet } from "@/lib/api";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import WalletBalance from "./WalletBalance";

export default function WalletConnectButton() {
  const { publicKey, select, disconnect, connected, connecting, wallets, wallet } = useWallet();
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { language } = useLanguageStore();

  const handleConnect = useCallback(async () => {
    if (connected && publicKey) {
      disconnect();
      localStorage.removeItem("tc_token");
      setError(null);
      return;
    }

    const phantom = wallets.find(
      (w) =>
        w.adapter.name === "Phantom" &&
        (w.readyState === WalletReadyState.Installed ||
         w.readyState === WalletReadyState.Loadable)
    );

    if (!phantom) {
      window.open("https://phantom.app/", "_blank");
      setError(t("wallet.installPhantom", language));
      setTimeout(() => setError(null), 5000);
      return;
    }

    try {
      select(phantom.adapter.name);
      setError(null);
    } catch {
      setError(t("wallet.cancelled", language));
      setTimeout(() => setError(null), 3000);
    }
  }, [connected, publicKey, disconnect, select, wallets, language]);

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
          ? t("wallet.connecting", language)
          : connected && publicKey
            ? (<>{shortenAddress(publicKey.toBase58())} <WalletBalance /></>)
            : t("wallet.connect", language)}
      </button>
      {error && (
        <div className="absolute top-full right-0 mt-2 px-3 py-1.5 text-xs bg-[#EF4444] text-white rounded-lg whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
}

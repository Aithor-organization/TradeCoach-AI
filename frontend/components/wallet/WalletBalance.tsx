"use client";

import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { LAMPORTS_PER_SOL } from "@solana/web3.js";
import { useCallback, useEffect, useState } from "react";

const REFRESH_INTERVAL = 30_000; // 30초

export default function WalletBalance() {
  const { connection } = useConnection();
  const { publicKey, connected } = useWallet();
  const [solBalance, setSolBalance] = useState<number | null>(null);

  const fetchBalance = useCallback(async () => {
    if (!publicKey) return;
    try {
      const lamports = await connection.getBalance(publicKey);
      setSolBalance(lamports / LAMPORTS_PER_SOL);
    } catch {
      // 잔액 조회 실패 시 무시
    }
  }, [connection, publicKey]);

  useEffect(() => {
    if (!connected || !publicKey) {
      setSolBalance(null);
      return;
    }

    fetchBalance();
    const id = setInterval(fetchBalance, REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [connected, publicKey, fetchBalance]);

  if (!connected || solBalance === null) return null;

  return (
    <span className="text-xs font-mono text-[#14F195]">
      {solBalance.toFixed(3)} SOL
    </span>
  );
}

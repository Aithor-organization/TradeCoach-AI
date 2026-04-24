"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletReadyState } from "@solana/wallet-adapter-base";
import bs58 from "bs58";
import {
  requestPasswordResetNonce,
  confirmPasswordResetWithWallet,
  RESET_MESSAGE_PREFIX,
} from "@/lib/api";
import { useLanguageStore } from "@/stores/languageStore";

type Step = "connect" | "reset" | "done";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { language } = useLanguageStore();
  const { publicKey, connected, signMessage, select, wallets } = useWallet();

  const [step, setStep] = useState<Step>("connect");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isKo = language === "ko";

  const connectPhantom = useCallback(() => {
    const phantom = wallets.find(
      (w) =>
        w.adapter.name === "Phantom" &&
        (w.readyState === WalletReadyState.Installed ||
          w.readyState === WalletReadyState.Loadable),
    );
    if (!phantom) {
      window.open("https://phantom.app/", "_blank");
      setError(isKo ? "Phantom 지갑을 설치해주세요." : "Please install Phantom wallet.");
      return;
    }
    select(phantom.adapter.name);
    setError(null);
  }, [wallets, select, isKo]);

  const handleReset = useCallback(async () => {
    setError(null);

    if (!connected || !publicKey || !signMessage) {
      setError(isKo ? "지갑을 먼저 연결하세요." : "Connect your wallet first.");
      return;
    }
    if (newPassword.length < 6) {
      setError(isKo ? "비밀번호는 6자 이상이어야 합니다." : "Password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(isKo ? "비밀번호가 일치하지 않습니다." : "Passwords don't match.");
      return;
    }

    const walletAddress = publicKey.toBase58();
    setIsSubmitting(true);
    try {
      const { nonce } = await requestPasswordResetNonce(walletAddress);
      const message = `${RESET_MESSAGE_PREFIX}${nonce}`;
      const signatureBytes = await signMessage(new TextEncoder().encode(message));
      const signatureB58 = bs58.encode(signatureBytes);
      await confirmPasswordResetWithWallet(walletAddress, nonce, signatureB58, newPassword);
      setStep("done");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg || (isKo ? "재설정 실패" : "Reset failed"));
    } finally {
      setIsSubmitting(false);
    }
  }, [connected, publicKey, signMessage, newPassword, confirmPassword, isKo]);

  return (
    <div className="min-h-screen bg-[#0A0F1C] flex flex-col">
      <header className="h-16 flex items-center px-6 border-b border-[#1E293B]">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-lg font-bold text-white">TradeCoach</span>
          <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
            AI
          </span>
        </Link>
      </header>

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] p-8 w-full max-w-md shadow-2xl">
          <div className="text-center mb-6">
            <h2 className="text-xl font-bold text-white mb-2">
              {isKo ? "비밀번호 재설정" : "Reset Password"}
            </h2>
            <p className="text-sm text-[#94A3B8]">
              {isKo
                ? "Phantom 지갑 서명으로 본인을 증명합니다."
                : "Prove ownership by signing with your Phantom wallet."}
            </p>
          </div>

          {step === "connect" && !connected && (
            <>
              <p className="text-xs text-[#94A3B8] mb-4">
                {isKo
                  ? "계정에 연결된 Phantom 지갑으로 로그인 후 새 비밀번호를 설정할 수 있습니다."
                  : "Connect the Phantom wallet linked to your account, then set a new password."}
              </p>
              <button
                onClick={connectPhantom}
                className="w-full py-2.5 rounded-lg font-semibold text-sm bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white hover:opacity-90 transition"
              >
                {isKo ? "Phantom 지갑 연결" : "Connect Phantom"}
              </button>
            </>
          )}

          {(step === "reset" || (step === "connect" && connected && publicKey)) && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleReset();
              }}
              className="space-y-4"
            >
              <div className="text-xs text-[#94A3B8] px-3 py-2 rounded bg-[#0F172A] border border-[#1E293B]">
                <span className="text-[#475569]">{isKo ? "연결된 지갑:" : "Connected wallet:"}</span>{" "}
                <span className="font-mono text-[#22D3EE]">
                  {publicKey
                    ? `${publicKey.toBase58().slice(0, 6)}...${publicKey.toBase58().slice(-6)}`
                    : "-"}
                </span>
              </div>
              <div>
                <label className="block text-xs text-[#94A3B8] mb-1.5">
                  {isKo ? "새 비밀번호" : "New Password"}
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  className="w-full px-4 py-2.5 rounded-lg bg-[#0F172A] border border-[#22D3EE20] text-white text-sm placeholder-[#475569] outline-none focus:border-[#22D3EE] transition"
                />
              </div>
              <div>
                <label className="block text-xs text-[#94A3B8] mb-1.5">
                  {isKo ? "비밀번호 확인" : "Confirm Password"}
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  className="w-full px-4 py-2.5 rounded-lg bg-[#0F172A] border border-[#22D3EE20] text-white text-sm placeholder-[#475569] outline-none focus:border-[#22D3EE] transition"
                />
              </div>
              {error && <p className="text-xs text-[#EF4444]">{error}</p>}
              <button
                type="submit"
                disabled={isSubmitting || !connected}
                className="w-full py-2.5 rounded-lg font-semibold text-sm bg-[#22D3EE] text-[#0A0F1C] hover:bg-[#06B6D4] transition disabled:opacity-50"
              >
                {isSubmitting
                  ? isKo
                    ? "서명 및 재설정 중..."
                    : "Signing & resetting..."
                  : isKo
                    ? "지갑으로 서명하고 비밀번호 재설정"
                    : "Sign with wallet & reset password"}
              </button>
              <p className="text-[10px] text-[#475569] text-center">
                {isKo
                  ? "Phantom 팝업에서 서명 요청을 승인해주세요."
                  : "Approve the signing request in the Phantom popup."}
              </p>
            </form>
          )}

          {step === "done" && (
            <div className="space-y-4 text-center">
              <div className="text-[#14F195] text-4xl">✓</div>
              <p className="text-sm text-white">
                {isKo
                  ? "비밀번호가 재설정되었습니다."
                  : "Your password has been reset."}
              </p>
              <button
                onClick={() => router.push("/login")}
                className="w-full py-2.5 rounded-lg font-semibold text-sm bg-[#22D3EE] text-[#0A0F1C] hover:bg-[#06B6D4] transition"
              >
                {isKo ? "로그인으로 이동" : "Go to login"}
              </button>
            </div>
          )}

          <div className="mt-6 text-center space-y-2">
            <Link href="/login" className="block text-xs text-[#475569] hover:text-[#94A3B8]">
              {isKo ? "← 로그인으로 돌아가기" : "← Back to login"}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

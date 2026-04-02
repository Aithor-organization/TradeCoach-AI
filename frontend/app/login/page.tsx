"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import AuthModal from "@/components/common/AuthModal";
import Link from "next/link";

export default function LoginPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const router = useRouter();

  // 이미 로그인된 상태면 채팅 페이지로 이동
  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/chat");
    }
  }, [isAuthenticated, router]);

  if (isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-[#0A0F1C] flex flex-col">
      {/* 간단한 헤더 */}
      <header className="h-16 flex items-center px-6 border-b border-[#1E293B]">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-lg font-bold text-white">TradeCoach</span>
          <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">AI</span>
        </Link>
      </header>

      {/* 로그인 폼 */}
      <div className="flex-1 flex items-center justify-center">
        <AuthModal onClose={() => router.replace("/chat")} />
      </div>
    </div>
  );
}

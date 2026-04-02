"use client";

import { useAuthStore } from "@/stores/authStore";
import AuthModal from "./AuthModal";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, _hydrated } = useAuthStore();

  // Zustand persist hydration이 완료될 때까지 스피너 표시
  // (새로고침 시 localStorage → store 동기화 대기)
  if (!_hydrated) {
    return (
      <div className="h-screen bg-[#0A0F1C] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#22D3EE] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="h-screen bg-[#0A0F1C]">
        <AuthModal />
      </div>
    );
  }

  return <>{children}</>;
}

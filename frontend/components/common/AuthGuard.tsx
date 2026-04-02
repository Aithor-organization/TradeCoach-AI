"use client";

import { useAuthStore, useAuthHydration } from "@/stores/authStore";
import AuthModal from "./AuthModal";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hydrated = useAuthHydration((s) => s.hydrated);

  // Zustand persist hydration 완료 대기
  if (!hydrated) {
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

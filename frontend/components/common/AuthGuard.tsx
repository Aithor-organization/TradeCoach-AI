"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import AuthModal from "./AuthModal";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Zustand persist의 onFinishHydration 구독
    const unsub = useAuthStore.persist.onFinishHydration(() => {
      console.log("[AuthGuard] hydration 완료, isAuthenticated:", useAuthStore.getState().isAuthenticated);
      setReady(true);
    });

    // 이미 hydration이 완료된 경우 (hot reload 등)
    if (useAuthStore.persist.hasHydrated()) {
      console.log("[AuthGuard] 이미 hydrated, isAuthenticated:", useAuthStore.getState().isAuthenticated);
      setReady(true);
    }

    // 안전장치: 3초 후에도 hydration 안 되면 강제 ready (무한 스피너 방지)
    const timeout = setTimeout(() => {
      if (!useAuthStore.persist.hasHydrated()) {
        console.warn("[AuthGuard] hydration 3초 타임아웃 — 강제 진행");
      }
      setReady(true);
    }, 3000);

    return () => {
      unsub();
      clearTimeout(timeout);
    };
  }, []);

  // 디버그 로그
  useEffect(() => {
    console.log("[AuthGuard] ready:", ready, "isAuthenticated:", isAuthenticated);
  }, [ready, isAuthenticated]);

  if (!ready) {
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

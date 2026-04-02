"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => {
      setReady(true);
    });

    if (useAuthStore.persist.hasHydrated()) {
      setReady(true);
    }

    // 3초 타임아웃 안전장치
    const timeout = setTimeout(() => setReady(true), 3000);

    return () => {
      unsub();
      clearTimeout(timeout);
    };
  }, []);

  // 미인증 시 랜딩페이지로 redirect (모달 대신)
  useEffect(() => {
    if (ready && !isAuthenticated) {
      console.log("[AuthGuard] 미인증 — 랜딩페이지로 이동");
      router.replace(`/?login=true&from=${encodeURIComponent(pathname)}`);
    }
  }, [ready, isAuthenticated, router, pathname]);

  if (!ready || !isAuthenticated) {
    return (
      <div className="h-screen bg-[#0A0F1C] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#22D3EE] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}

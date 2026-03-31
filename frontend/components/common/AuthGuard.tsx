"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import AuthModal from "./AuthModal";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // SSR/hydration 중에는 스피너 표시 (최대 1프레임)
  if (!mounted) {
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

"use client";

import { useAuthStore } from "@/stores/authStore";
import AuthModal from "./AuthModal";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return (
      <div className="h-screen bg-[#0A0F1C]">
        <AuthModal />
      </div>
    );
  }

  return <>{children}</>;
}

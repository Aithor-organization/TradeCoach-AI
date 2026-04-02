"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";
import { useAuthStore } from "@/stores/authStore";
import AuthModal from "./AuthModal";

function LoginOverlayInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const showLogin = searchParams.get("login") === "true";
  const from = searchParams.get("from");

  if (!showLogin || isAuthenticated) return null;

  const handleClose = () => {
    // 로그인 성공 후 원래 페이지로 이동, 없으면 랜딩에 유지
    if (from) {
      router.replace(from);
    } else {
      router.replace("/");
    }
  };

  return <AuthModal onClose={handleClose} />;
}

// useSearchParams는 Suspense boundary 필요
export default function LoginOverlay() {
  return (
    <Suspense fallback={null}>
      <LoginOverlayInner />
    </Suspense>
  );
}

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import { useLanguageStore } from "@/stores/languageStore";
import { loginWithEmail } from "@/lib/api";

export default function LoginPage() {
  const { isAuthenticated, login } = useAuthStore();
  const { language } = useLanguageStore();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/chat");
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setIsSubmitting(true);
    setError("");
    try {
      const res = await loginWithEmail(email.trim(), password);
      login(res.access_token, res.user_id, res.name, res.email);
    } catch {
      setError(language === "ko" ? "이메일 또는 비밀번호가 올바르지 않습니다." : "Invalid email or password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-[#0A0F1C] flex flex-col">
      <header className="h-16 flex items-center px-6 border-b border-[#1E293B]">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-lg font-bold text-white">TradeCoach</span>
          <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">AI</span>
        </Link>
      </header>

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] p-8 w-full max-w-md shadow-2xl">
          <div className="text-center mb-6">
            <h2 className="text-xl font-bold text-white mb-2">
              {language === "ko" ? "로그인" : "Login"}
            </h2>
            <p className="text-sm text-[#94A3B8]">
              {language === "ko" ? "이메일로 로그인하세요" : "Sign in with your email"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-[#94A3B8] mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="example@email.com"
                required
                className="w-full px-4 py-2.5 rounded-lg bg-[#0F172A] border border-[#22D3EE20] text-white text-sm placeholder-[#475569] outline-none focus:border-[#22D3EE] transition"
              />
            </div>
            <div>
              <label className="block text-xs text-[#94A3B8] mb-1.5">
                {language === "ko" ? "비밀번호" : "Password"}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={6}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0F172A] border border-[#22D3EE20] text-white text-sm placeholder-[#475569] outline-none focus:border-[#22D3EE] transition"
              />
            </div>
            {error && (
              <p className="text-xs text-[#EF4444]">{error}</p>
            )}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-lg font-semibold text-sm bg-[#22D3EE] text-[#0A0F1C] hover:bg-[#06B6D4] transition disabled:opacity-50"
            >
              {isSubmitting ? "..." : (language === "ko" ? "로그인" : "Login")}
            </button>
          </form>

          <div className="mt-6 text-center space-y-2">
            <p className="text-xs text-[#475569]">
              {language === "ko" ? "계정이 없으신가요?" : "Don't have an account?"}
              {" "}
              <Link href="/signup" className="text-[#22D3EE] hover:underline font-semibold">
                {language === "ko" ? "회원가입" : "Sign Up"}
              </Link>
            </p>
            <Link
              href="/forgot-password"
              className="block text-xs text-[#22D3EE] hover:underline"
            >
              {language === "ko"
                ? "비밀번호를 잊으셨나요? (Phantom 지갑으로 재설정)"
                : "Forgot password? (reset with Phantom wallet)"}
            </Link>
            <Link href="/" className="block text-xs text-[#475569] hover:text-[#94A3B8]">
              {language === "ko" ? "← 홈으로 돌아가기" : "← Back to home"}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

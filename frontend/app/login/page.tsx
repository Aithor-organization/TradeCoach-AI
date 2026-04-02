"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import { useLanguageStore } from "@/stores/languageStore";
import { registerWithEmail } from "@/lib/api";
import { t } from "@/lib/i18n";

export default function LoginPage() {
  const { isAuthenticated, login } = useAuthStore();
  const { language } = useLanguageStore();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/chat");
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    setIsSubmitting(true);
    setError("");
    try {
      const res = await registerWithEmail(name.trim(), email.trim());
      login(res.access_token, res.user_id, res.name, res.email);
    } catch {
      setError(t("auth.error", language));
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
              {t("auth.title", language)}
            </h2>
            <p className="text-sm text-[#94A3B8]">
              {t("auth.subtitle", language)}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-[#94A3B8] mb-1.5">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                required
                className="w-full px-4 py-2.5 rounded-lg bg-[#0F172A] border border-[#22D3EE20] text-white text-sm placeholder-[#475569] outline-none focus:border-[#22D3EE] transition"
              />
            </div>
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
            {error && (
              <p className="text-xs text-[#EF4444]">{error}</p>
            )}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-lg font-semibold text-sm bg-[#22D3EE] text-[#0A0F1C] hover:bg-[#06B6D4] transition disabled:opacity-50"
            >
              {isSubmitting ? "..." : "Get Started"}
            </button>
          </form>

          <p className="text-center text-xs text-[#475569] mt-4">
            <Link href="/" className="text-[#22D3EE] hover:underline">
              {language === "ko" ? "← 홈으로 돌아가기" : "← Back to home"}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

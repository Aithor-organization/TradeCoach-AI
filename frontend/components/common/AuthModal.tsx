"use client";

import { useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import { registerWithEmail } from "@/lib/api";
import Button from "./Button";

export default function AuthModal({ onClose }: { onClose?: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuthStore();
  const { language } = useLanguageStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;

    setIsSubmitting(true);
    setError("");
    try {
      const res = await registerWithEmail(name.trim(), email.trim());
      login(res.access_token, res.user_id, res.name, res.email);
      onClose?.();
    } catch {
      setError(t("auth.error", language));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0A0F1C] backdrop-blur-sm">
      <div className="bg-[#1E293B] rounded-2xl border border-[#22D3EE20] p-8 w-full max-w-md mx-4 shadow-2xl">
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-2 mb-3">
            <span className="text-2xl font-bold text-white">TradeCoach</span>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
              AI
            </span>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">
            {t("auth.title", language)}
          </h2>
          <p className="text-sm text-[#94A3B8]">
            {t("auth.subtitle", language)}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#94A3B8] mb-1.5">
              {t("auth.name", language)}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("auth.namePlaceholder", language)}
              className="w-full bg-[#0F172A] text-white text-sm rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none placeholder-[#475569]"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#94A3B8] mb-1.5">
              {t("auth.email", language)}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t("auth.emailPlaceholder", language)}
              className="w-full bg-[#0F172A] text-white text-sm rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none placeholder-[#475569]"
              required
            />
          </div>

          {error && (
            <p className="text-xs text-[#EF4444]">{error}</p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting || !name.trim() || !email.trim()}
          >
            {isSubmitting ? t("auth.submitting", language) : t("auth.submit", language)}
          </Button>
        </form>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import Button from "@/components/common/Button";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

export default function Hero() {
  const { language } = useLanguageStore();

  return (
    <section className="relative pt-32 pb-16 px-6 lg:px-[120px] text-center">
      {/* 배경 글로우 효과 */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#22D3EE08] rounded-full blur-3xl pointer-events-none" />

      {/* 뱃지 */}
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#22D3EE15] border border-[#22D3EE30] mb-8">
        <span className="font-mono text-xs font-medium text-[#22D3EE]">
          Powered by Solana
        </span>
        <span className="text-xs text-[#475569]">•</span>
        <span className="font-mono text-xs text-[#94A3B8]">
          Gemini AI
        </span>
      </div>

      {/* 헤드라인 */}
      <h1 className="text-4xl md:text-[64px] font-bold leading-tight mb-6 max-w-4xl mx-auto">
        {language === "en" ? (
          <>
            AI makes you a better{" "}
            <span className="gradient-text">trader</span>
          </>
        ) : (
          <>
            AI가 당신을 더 나은{" "}
            <span className="gradient-text">트레이더</span>로
            <br />
            만들어줍니다
          </>
        )}
      </h1>

      {/* 서브헤드 */}
      <p className="text-lg text-[#94A3B8] mb-10 max-w-2xl mx-auto">
        {t("hero.sub1", language)}
        <br />
        {t("hero.sub2", language)}
      </p>

      {/* CTA 버튼 */}
      <div className="flex items-center justify-center gap-4">
        <Link href="/chat">
          <Button size="lg">
            {t("hero.cta", language)}
          </Button>
        </Link>
        <a href="#how-it-works">
          <Button variant="secondary" size="lg">
            {t("hero.howItWorks", language)}
          </Button>
        </a>
      </div>
    </section>
  );
}

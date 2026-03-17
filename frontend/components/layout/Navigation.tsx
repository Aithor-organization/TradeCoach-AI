"use client";

import Link from "next/link";
import Button from "@/components/common/Button";
import WalletConnectButton from "@/components/wallet/WalletConnectButton";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

const NAV_LINKS = [
  { labelKey: "nav.features" as const, href: "#features" },
  { labelKey: "nav.howItWorks" as const, href: "#how-it-works" },
  { labelKey: "nav.strategies" as const, href: "/strategies" },
  { labelKey: "nav.pricing" as const, href: "#pricing" },
];

export default function Navigation() {
  const { language, toggleLanguage } = useLanguageStore();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 md:h-20 bg-[#0A0F1CCC] backdrop-blur-md border-b border-[#22D3EE10]">
      <div className="max-w-7xl mx-auto h-full flex items-center justify-between px-4 md:px-6 lg:px-[120px]">
        {/* 로고 */}
        <Link href="/" className="flex items-center gap-2 flex-shrink-0">
          <span className="text-lg md:text-xl font-bold text-white">TradeCoach</span>
          <span className="text-xs font-mono font-bold px-1.5 md:px-2 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
            AI
          </span>
        </Link>

        {/* 네비게이션 링크 (데스크톱만) */}
        <div className="hidden lg:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            link.href.startsWith("/") ? (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-[#94A3B8] hover:text-white transition-colors"
              >
                {t(link.labelKey, language)}
              </Link>
            ) : (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-[#94A3B8] hover:text-white transition-colors"
              >
                {t(link.labelKey, language)}
              </a>
            )
          ))}
        </div>

        {/* CTA */}
        <div className="flex items-center gap-2 md:gap-3">
          {/* 언어 토글 */}
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-[#1E293B] border border-[#22D3EE20] hover:border-[#22D3EE50] transition-colors cursor-pointer flex-shrink-0"
            title={language === "ko" ? "Switch to English" : "한국어로 전환"}
          >
            <span className={`text-xs font-bold ${language === "ko" ? "text-[#22D3EE]" : "text-[#475569]"}`}>한</span>
            <span className="text-xs text-[#475569]">/</span>
            <span className={`text-xs font-bold ${language === "en" ? "text-[#22D3EE]" : "text-[#475569]"}`}>EN</span>
          </button>
          {/* 지갑 (데스크톱만) */}
          <div className="hidden md:block">
            <WalletConnectButton />
          </div>
          {/* CTA 버튼 */}
          <Link href="/chat">
            <Button size="sm" className="text-xs md:text-sm whitespace-nowrap">
              {t("nav.freeStart", language)}
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}

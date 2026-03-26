"use client";

import { useState } from "react";
import Link from "next/link";
import { useLanguageStore } from "@/stores/languageStore";
import { useAuthStore } from "@/stores/authStore";
import { t } from "@/lib/i18n";

type PageKey = "chat" | "strategies" | "trading" | "marketplace" | "learn";

const NAV_ITEMS = [
  { key: "chat" as const, href: "/chat", labelKey: "nav.chat" as const },
  { key: "strategies" as const, href: "/strategies", labelKey: "nav.strategies" as const },
  { key: "trading" as const, href: "/trading", labelKey: "nav.trading" as const },
  { key: "marketplace" as const, href: "/marketplace", labelKey: "nav.marketplace" as const },
  { key: "learn" as const, href: "/learn", labelKey: "nav.learn" as const },
];

interface AppHeaderProps {
  activePage: PageKey;
  /** 헤더 오른쪽에 추가 요소 (breadcrumb 등) */
  rightSlot?: React.ReactNode;
}

export default function AppHeader({ activePage, rightSlot }: AppHeaderProps) {
  const { language } = useLanguageStore();
  const { isAuthenticated, name, logout } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="relative h-14 flex items-center justify-between px-4 sm:px-6 border-b border-[#1E293B] bg-[#0A0F1CCC] backdrop-blur-md z-40">
      {/* 왼쪽: 로고 */}
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-base font-bold text-white">TradeCoach</span>
          <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
            AI
          </span>
        </Link>
      </div>

      {/* 센터/오른쪽: 데스크톱 네비게이션 */}
      <div className="flex items-center gap-4">
        <nav className="hidden sm:flex items-center gap-3 text-xs text-[#94A3B8]">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className={
                item.key === activePage
                  ? "text-[#22D3EE]"
                  : "hover:text-white transition"
              }
            >
              {t(item.labelKey, language)}
            </Link>
          ))}
        </nav>

        {rightSlot}

        {/* 사용자 상태 */}
        <div className="hidden sm:flex items-center gap-2 text-xs">
          {isAuthenticated ? (
            <>
              <span className="text-[#22D3EE] font-medium truncate max-w-[100px]">
                {name || "User"}
              </span>
              <button
                onClick={logout}
                className="text-[#475569] hover:text-[#EF4444] transition cursor-pointer"
              >
                {language === "ko" ? "로그아웃" : "Logout"}
              </button>
            </>
          ) : (
            <Link
              href="/strategies"
              className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] font-semibold hover:opacity-90 transition"
            >
              {language === "ko" ? "로그인" : "Login"}
            </Link>
          )}
        </div>

        {/* 모바일 햄버거 버튼 */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="sm:hidden p-2 text-[#94A3B8] hover:text-white transition cursor-pointer"
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {mobileMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* 모바일 메뉴 오버레이 */}
      {mobileMenuOpen && (
        <div className="absolute top-14 left-0 right-0 bg-[#0A0F1C] border-b border-[#1E293B] sm:hidden z-50">
          <nav className="flex flex-col py-2">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`px-6 py-3 text-sm ${
                  item.key === activePage
                    ? "text-[#22D3EE] bg-[#22D3EE10]"
                    : "text-[#94A3B8] hover:text-white hover:bg-[#1E293B]"
                } transition`}
              >
                {t(item.labelKey, language)}
              </Link>
            ))}
            {/* 모바일 사용자 상태 */}
            <div className="px-6 py-3 border-t border-[#1E293B] mt-1">
              {isAuthenticated ? (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#22D3EE]">{name || "User"}</span>
                  <button onClick={() => { logout(); setMobileMenuOpen(false); }} className="text-xs text-[#475569] hover:text-[#EF4444] cursor-pointer">
                    {language === "ko" ? "로그아웃" : "Logout"}
                  </button>
                </div>
              ) : (
                <Link href="/strategies" onClick={() => setMobileMenuOpen(false)} className="block text-center py-2 rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] text-sm font-semibold">
                  {language === "ko" ? "로그인" : "Login"}
                </Link>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}

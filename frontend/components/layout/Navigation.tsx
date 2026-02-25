"use client";

import Link from "next/link";
import Button from "@/components/common/Button";
import WalletConnectButton from "@/components/wallet/WalletConnectButton";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Strategies", href: "/strategies" },
  { label: "Pricing", href: "#pricing" },
];

export default function Navigation() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-20 bg-[#0A0F1CCC] backdrop-blur-md border-b border-[#22D3EE10]">
      <div className="max-w-7xl mx-auto h-full flex items-center justify-between px-6 lg:px-[120px]">
        {/* 로고 */}
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-white">TradeCoach</span>
          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
            AI
          </span>
        </Link>

        {/* 네비게이션 링크 */}
        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            link.href.startsWith("/") ? (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-[#94A3B8] hover:text-white transition-colors"
              >
                {link.label}
              </Link>
            ) : (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-[#94A3B8] hover:text-white transition-colors"
              >
                {link.label}
              </a>
            )
          ))}
        </div>

        {/* CTA */}
        <div className="flex items-center gap-3">
          <WalletConnectButton />
          <Link href="/chat">
            <Button size="sm">무료로 시작하기</Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}

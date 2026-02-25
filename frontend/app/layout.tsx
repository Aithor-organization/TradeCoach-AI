import type { Metadata } from "next";
import "./globals.css";
import WalletProvider from "@/components/wallet/WalletProvider";

export const metadata: Metadata = {
  title: "TradeCoach AI - AI 트레이딩 코치",
  description: "AI가 당신을 더 나은 트레이더로 만들어줍니다. 솔라나 DEX 트레이딩 전략 분석, 백테스트, AI 코칭.",
  keywords: ["TradeCoach", "AI", "trading", "Solana", "DEX", "backtesting"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        <WalletProvider>
          {children}
        </WalletProvider>
      </body>
    </html>
  );
}

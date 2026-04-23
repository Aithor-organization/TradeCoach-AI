import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import WalletProvider from "@/components/wallet/WalletProvider";
import { ToastProvider } from "@/components/common/Toast";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import AuthExpiryWatcher from "@/components/common/AuthExpiryWatcher";

const GA_ID = "G-2YJY4GB90E";

export const metadata: Metadata = {
  title: "TradeCoach AI - AI Trading Coach",
  description: "AI makes you a better trader. Solana DEX trading strategy analysis, backtesting, and AI coaching.",
  keywords: ["TradeCoach", "AI", "trading", "Solana", "DEX", "backtesting"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${GA_ID}');
          `}
        </Script>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        <ErrorBoundary>
          <WalletProvider>
            <ToastProvider>
              <AuthExpiryWatcher />
              {children}
            </ToastProvider>
          </WalletProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}

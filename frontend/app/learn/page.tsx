"use client";

import Link from "next/link";
import AppHeader from "@/components/layout/AppHeader";
import { useLanguageStore } from "@/stores/languageStore";

const sections = [
  {
    id: "strategy",
    icon: "📊",
    title: { ko: "AI 전략 생성", en: "AI Strategy Creation" },
    desc: {
      ko: "AI 채팅에서 자연어로 트레이딩 전략을 설명하면, AI가 자동으로 구조화된 JSON 전략으로 변환합니다. RSI, MACD, 볼린저밴드 등 다양한 지표를 조합할 수 있고, 차트 이미지를 업로드하면 AI가 패턴을 인식하여 전략을 생성합니다.",
      en: "Describe your trading strategy in natural language in the AI chat, and AI automatically converts it into a structured JSON strategy. You can combine various indicators like RSI, MACD, Bollinger Bands, and upload chart images for AI pattern recognition."
    },
    color: "#22D3EE",
  },
  {
    id: "backtest",
    icon: "📈",
    title: { ko: "선물 백테스트", en: "Futures Backtesting" },
    desc: {
      ko: "Binance Futures 실제 가격 데이터로 전략을 백테스트합니다. 레버리지(1x~125x), 롱/숏 양방향, 분할 익절, 추적 손절, 강제 청산까지 실제 선물 거래 환경을 시뮬레이션합니다. 결과에는 총 수익률, MDD, Sharpe Ratio, Profit Factor 등 상세 메트릭이 포함됩니다.",
      en: "Backtest your strategy with real Binance Futures price data. Simulates actual futures trading with leverage (1x-125x), long/short, partial exits, trailing stops, and liquidation. Results include total return, MDD, Sharpe Ratio, Profit Factor, and more."
    },
    color: "#22C55E",
  },
  {
    id: "optimize",
    icon: "🔧",
    title: { ko: "파라미터 최적화 (Grid Search)", en: "Parameter Optimization (Grid Search)" },
    desc: {
      ko: "레버리지, 익절/손절 비율, 지표 파라미터 등의 범위를 지정하면, 모든 조합을 자동으로 백테스트하여 최적의 파라미터를 찾습니다. 목적 함수(Sharpe, Calmar, Profit Factor)를 선택할 수 있고, 상위 10개 결과를 테이블로 보여줍니다. 'Apply'를 클릭하면 해당 파라미터가 전략에 바로 적용됩니다.",
      en: "Specify ranges for leverage, TP/SL ratios, and indicator parameters. All combinations are automatically backtested to find optimal parameters. Choose objective function (Sharpe, Calmar, Profit Factor) and see top 10 results. Click 'Apply' to instantly update your strategy."
    },
    color: "#F59E0B",
  },
  {
    id: "walkforward",
    icon: "🔍",
    title: { ko: "Walk-Forward 전진분석", en: "Walk-Forward Analysis" },
    desc: {
      ko: "백테스트 결과가 좋다고 실전에서도 좋을까? Walk-Forward는 데이터를 훈련(In-Sample)과 검증(Out-of-Sample)으로 나누어, 훈련에서 찾은 최적 파라미터가 검증 기간에서도 작동하는지 확인합니다. OOS/IS 비율이 50% 이상이면 'Pass' — 과최적화(오버피팅)가 아니라는 뜻입니다. 여러 윈도우를 반복하여 전략의 강건성을 검증합니다.",
      en: "Good backtest results don't guarantee real performance. Walk-Forward splits data into training (In-Sample) and validation (Out-of-Sample), checking if optimal parameters from training work in validation too. OOS/IS ratio above 50% = Pass (no overfitting). Multiple windows verify strategy robustness."
    },
    color: "#A78BFA",
  },
  {
    id: "trading",
    icon: "🎮",
    title: { ko: "모의투자 (Demo Trading)", en: "Demo Trading" },
    desc: {
      ko: "실제 돈 없이 가상 자본으로 전략을 실시간 테스트합니다. Binance Futures WebSocket으로 실시간 가격을 받아 DDIF 전략 엔진이 자동으로 매수/매도 신호를 생성합니다. 포지션, 잔고, 미실현 PnL을 실시간으로 확인할 수 있습니다.",
      en: "Test your strategy in real-time with virtual capital. Receives live prices via Binance Futures WebSocket, and the DDIF strategy engine automatically generates buy/sell signals. Monitor positions, balance, and unrealized PnL in real-time."
    },
    color: "#14F195",
  },
  {
    id: "blockchain",
    icon: "🔗",
    title: { ko: "블록체인 검증 (Solana cNFT)", en: "Blockchain Verification (Solana cNFT)" },
    desc: {
      ko: "전략을 Solana 블록체인에 cNFT(compressed NFT)로 등록하면, 전략 내용의 SHA256 해시가 온체인에 기록되어 변조가 불가능합니다. 매매 신호도 Merkle Tree에 압축 기록되어 투명하게 검증할 수 있습니다. State Compression 기술로 100만 건 기록에 ~$1의 비용만 들어갑니다.",
      en: "Register your strategy as a cNFT on Solana blockchain. The SHA256 hash is recorded on-chain, making it tamper-proof. Trading signals are compressed into Merkle Trees for transparent verification. State Compression technology keeps costs to ~$1 for 1M records."
    },
    color: "#9945FF",
  },
  {
    id: "coaching",
    icon: "🤖",
    title: { ko: "AI 코칭", en: "AI Coaching" },
    desc: {
      ko: "전략 상세 페이지 오른쪽의 AI 채팅에서 전략에 대한 코칭을 받을 수 있습니다. '익절을 20%로 변경해줘', '최적화 범위 추천해줘' 같은 자연어 요청으로 전략을 수정하거나 최적화 범위를 추천받을 수 있습니다. AI는 리스크 관리, 지표 조합, 레버리지 위험을 자동으로 안내합니다.",
      en: "Get AI coaching in the chat panel on the strategy detail page. Request changes like 'change TP to 20%' or 'recommend optimization ranges' in natural language. AI automatically guides risk management, indicator combinations, and leverage risks."
    },
    color: "#EF4444",
  },
];

export default function LearnPage() {
  const { language } = useLanguageStore();

  return (
    <div className="min-h-screen bg-[#0A0F1C] text-white">
      <AppHeader activePage="learn" />

      <main className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold">{language === "ko" ? "TradeCoach AI 기능 가이드" : "TradeCoach AI Feature Guide"}</h1>
          <p className="text-sm text-[#94A3B8]">
            {language === "ko" ? "각 기능이 무엇이고 어떻게 사용하는지 알아보세요" : "Learn what each feature does and how to use it"}
          </p>
        </div>

        {sections.map((s) => (
          <div key={s.id} id={s.id} className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] p-6 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{s.icon}</span>
              <h2 className="text-lg font-bold" style={{ color: s.color }}>
                {language === "ko" ? s.title.ko : s.title.en}
              </h2>
            </div>
            <p className="text-sm text-[#94A3B8] leading-relaxed whitespace-pre-line">
              {language === "ko" ? s.desc.ko : s.desc.en}
            </p>
          </div>
        ))}

        <div className="text-center pt-4">
          <Link
            href="/chat"
            className="inline-block px-6 py-3 text-sm font-semibold rounded-lg gradient-accent text-[#0A0F1C] hover:opacity-90 transition"
          >
            {language === "ko" ? "지금 시작하기" : "Get Started"}
          </Link>
        </div>
      </main>
    </div>
  );
}

import Button from "@/components/common/Button";
import Link from "next/link";

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "유저 획득 보조",
    features: [
      "기본 전략 빌딩",
      "월 3회 백테스트",
      "기본 AI 코칭",
      "SOL/USDC 페어",
    ],
    cta: "무료로 시작",
    variant: "secondary" as const,
    highlight: false,
  },
  {
    name: "Premium",
    price: "$19.99",
    period: "/month",
    description: "프리미엄 구독",
    features: [
      "무제한 백테스트",
      "심층 AI 코칭",
      "실시간 전략 알림",
      "전략 무제한 저장",
      "모든 토큰 페어 지원",
    ],
    cta: "Premium 시작하기",
    variant: "primary" as const,
    highlight: true,
  },
  {
    name: "Web3 Native",
    price: "성과 기반",
    period: "",
    description: "Web3 네이티브 모델",
    features: [
      "Premium 전체 기능 포함",
      "전략 NFT 마켓플레이스",
      "검증된 전략 공유 → 로열티 수익",
      "카피트레이딩 연동",
      "수익 발생 시에만 과금",
    ],
    cta: "곧 출시 예정",
    variant: "secondary" as const,
    highlight: false,
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 px-6 lg:px-[120px]">
      <div className="max-w-7xl mx-auto">
        {/* 섹션 헤더 */}
        <div className="text-center mb-16">
          <span className="font-mono text-xs font-medium text-[#22D3EE] tracking-wider uppercase">
            Pricing
          </span>
          <h2 className="text-3xl md:text-[40px] font-bold mt-3">
            심플한 가격 정책
          </h2>
        </div>

        {/* 가격 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-xl p-8 ${
                plan.highlight
                  ? "bg-[#1E293B] border-2 border-[#22D3EE] relative"
                  : "bg-[#1E293B] border border-[#22D3EE15]"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="font-mono text-xs font-bold px-3 py-1 rounded-full gradient-accent text-[#0A0F1C]">
                    POPULAR
                  </span>
                </div>
              )}

              <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
              <p className="text-sm text-[#94A3B8] mb-4">{plan.description}</p>

              <div className="flex items-baseline gap-1 mb-6">
                <span className="font-mono text-4xl font-bold text-white">{plan.price}</span>
                <span className="text-sm text-[#475569]">{plan.period}</span>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm text-[#94A3B8]">
                    <span className="text-[#22D3EE]">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <Link href="/chat" className="block">
                <Button variant={plan.variant} className="w-full">
                  {plan.cta}
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

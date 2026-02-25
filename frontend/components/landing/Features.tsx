const FEATURES = [
  {
    title: "자연어 전략 빌더",
    description: "한국어로 전략을 설명하면 AI가 구조화된 트레이딩 전략으로 변환합니다.",
    icon: "🗣️",
  },
  {
    title: "차트 이미지 분석",
    description: "차트 스크린샷을 업로드하면 AI가 패턴을 인식하고 전략을 생성합니다.",
    icon: "📸",
  },
  {
    title: "실전 백테스트",
    description: "솔라나 DEX 실제 가격 데이터로 전략 성과를 검증합니다.",
    icon: "📈",
  },
  {
    title: "AI 코칭 대화",
    description: "백테스트 결과를 분석하고 리스크 관리, 전략 개선을 코칭합니다.",
    icon: "🎓",
  },
  {
    title: "솔라나 네이티브",
    description: "Phantom 지갑으로 로그인, SOL/USDC 등 주요 페어 지원.",
    icon: "⚡",
  },
];

export default function Features() {
  return (
    <section id="features" className="py-24 px-6 lg:px-[120px]">
      <div className="max-w-7xl mx-auto">
        {/* 섹션 헤더 */}
        <div className="text-center mb-16">
          <span className="font-mono text-xs font-medium text-[#22D3EE] tracking-wider uppercase">
            Features
          </span>
          <h2 className="text-3xl md:text-[40px] font-bold mt-3">
            트레이딩 실력을 키우는 핵심 기능
          </h2>
        </div>

        {/* 3+2 그리드 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {FEATURES.slice(0, 3).map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
          {FEATURES.slice(3).map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ title, description, icon }: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="bg-[#0F172A] rounded-xl p-7 border border-[#22D3EE10] hover:border-[#22D3EE30] transition-all group">
      <span className="text-3xl mb-4 block">{icon}</span>
      <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-[#22D3EE] transition-colors">
        {title}
      </h3>
      <p className="text-sm text-[#94A3B8] leading-relaxed">
        {description}
      </p>
    </div>
  );
}

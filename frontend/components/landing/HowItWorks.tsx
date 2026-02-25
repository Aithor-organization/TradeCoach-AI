const STEPS = [
  {
    number: "01",
    title: "전략 설명",
    description: "자연어로 트레이딩 전략을 설명하거나, 차트 이미지를 업로드하세요.",
    icon: "💬",
  },
  {
    number: "02",
    title: "AI 분석",
    description: "Gemini AI가 전략을 구조화하고, 리스크를 사전 분석합니다.",
    icon: "🤖",
  },
  {
    number: "03",
    title: "백테스트",
    description: "솔라나 DEX 과거 데이터로 전략의 실제 성과를 검증합니다.",
    icon: "📊",
  },
  {
    number: "04",
    title: "AI 코칭",
    description: "결과를 기반으로 개선점을 제안하고 전략을 함께 발전시킵니다.",
    icon: "🎯",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-6 lg:px-[120px] bg-[#0F172A]">
      <div className="max-w-7xl mx-auto">
        {/* 섹션 헤더 */}
        <div className="text-center mb-16">
          <span className="font-mono text-xs font-medium text-[#22D3EE] tracking-wider uppercase">
            How It Works
          </span>
          <h2 className="text-3xl md:text-[40px] font-bold mt-3">
            4단계로 시작하는 AI 트레이딩 코칭
          </h2>
        </div>

        {/* 스텝 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {STEPS.map((step) => (
            <div
              key={step.number}
              className="bg-[#1E293B] rounded-xl p-7 border border-[#22D3EE15] hover:border-[#22D3EE40] transition-colors"
            >
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">{step.icon}</span>
                <span className="font-mono text-xs font-bold text-[#22D3EE]">
                  STEP {step.number}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-[#94A3B8] leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

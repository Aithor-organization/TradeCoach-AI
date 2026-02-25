import Link from "next/link";
import Button from "@/components/common/Button";

export default function Hero() {
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
        AI가 당신을 더 나은{" "}
        <span className="gradient-text">트레이더</span>로
        <br />
        만들어줍니다
      </h1>

      {/* 서브헤드 */}
      <p className="text-lg text-[#94A3B8] mb-10 max-w-2xl mx-auto">
        자연어로 전략을 설명하면, AI가 분석하고 백테스트하고 개선점을 코칭합니다.
        <br />
        솔라나 DEX에서 더 현명한 트레이딩을 시작하세요.
      </p>

      {/* CTA 버튼 */}
      <div className="flex items-center justify-center gap-4">
        <Link href="/chat">
          <Button size="lg">
            전략 만들기 시작 →
          </Button>
        </Link>
        <a href="#how-it-works">
          <Button variant="secondary" size="lg">
            어떻게 작동하나요?
          </Button>
        </a>
      </div>
    </section>
  );
}

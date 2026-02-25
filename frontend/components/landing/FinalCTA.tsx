import Link from "next/link";
import Button from "@/components/common/Button";

export default function FinalCTA() {
  return (
    <section className="py-24 px-6 lg:px-[120px]">
      <div className="max-w-3xl mx-auto text-center relative">
        {/* 배경 글로우 */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#22D3EE10] via-[#06B6D420] to-[#22D3EE10] rounded-3xl blur-2xl" />

        <div className="relative bg-[#0F172A] rounded-2xl p-12 border border-[#22D3EE20]">
          <h2 className="text-3xl md:text-[40px] font-bold mb-4">
            지금 바로 시작하세요
          </h2>
          <p className="text-lg text-[#94A3B8] mb-8">
            무료로 AI 트레이딩 코칭을 체험하세요.
            <br />
            지갑 연결 없이도 3번의 백테스트가 가능합니다.
          </p>
          <Link href="/chat">
            <Button size="lg">
              무료로 전략 만들기 →
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}

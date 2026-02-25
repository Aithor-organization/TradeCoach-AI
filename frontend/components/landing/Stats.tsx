const STATS = [
  { value: "$18B+", label: "Solana DEX 일일 거래량" },
  { value: "10B+", label: "일일 트랜잭션 수" },
  { value: "4 Steps", label: "전략 빌딩 프로세스" },
  { value: "0.3%", label: "백테스트 수수료 반영" },
];

export default function Stats() {
  return (
    <section className="py-20 px-6 lg:px-[120px] bg-[#0F172A]">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="font-mono text-4xl font-bold text-[#22D3EE] mb-2">
                {stat.value}
              </p>
              <p className="text-sm text-[#94A3B8]">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

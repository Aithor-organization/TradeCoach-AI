"use client";

export default function ChatMockup() {
  return (
    <section className="py-8 px-6 lg:px-[120px]">
      <div className="max-w-4xl mx-auto">
        {/* 브라우저 프레임 */}
        <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden shadow-2xl">
          {/* 타이틀바 */}
          <div className="flex items-center gap-2 px-4 py-3 bg-[#0F172A] border-b border-[#1E293B]">
            <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
            <div className="w-3 h-3 rounded-full bg-[#EAB308]" />
            <div className="w-3 h-3 rounded-full bg-[#22C55E]" />
            <span className="ml-3 text-xs text-[#475569] font-mono">tradecoach.ai/demo</span>
          </div>

          {/* YouTube 영상 (자동재생, 음소거, 반복) */}
          <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
            <iframe
              className="absolute inset-0 w-full h-full"
              src="https://www.youtube.com/embed/pTnbKeb9dg0?autoplay=1&mute=1&loop=1&playlist=pTnbKeb9dg0&controls=0&showinfo=0&rel=0&modestbranding=1&playsinline=1&vq=hd1080&hd=1"
              title="TradeCoach AI Demo"
              allow="autoplay; encrypted-media"
              allowFullScreen
            />
          </div>
        </div>
      </div>
    </section>
  );
}

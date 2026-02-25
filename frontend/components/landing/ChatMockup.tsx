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
            <span className="ml-3 text-xs text-[#475569] font-mono">tradecoach.ai/chat</span>
          </div>

          {/* 채팅 내용 */}
          <div className="p-6 space-y-4">
            {/* 사용자 메시지 */}
            <div className="flex justify-end">
              <div className="bg-[#22D3EE15] border border-[#22D3EE30] rounded-lg px-4 py-3 max-w-md">
                <p className="text-sm text-white">
                  거래량 3배 터진 코인 소액 진입, 20% 익절 10% 손절
                </p>
              </div>
            </div>

            {/* AI 응답 */}
            <div className="flex justify-start">
              <div className="bg-[#0F172A] rounded-lg px-4 py-3 max-w-md border border-[#22D3EE10]">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono font-bold text-[#22D3EE]">TradeCoach AI</span>
                </div>
                <p className="text-sm text-[#94A3B8]">
                  전략을 분석했습니다. 거래량 급증 전략으로 구조화했어요.
                </p>
                {/* 미니 전략 카드 */}
                <div className="mt-3 bg-[#1E293B] rounded-lg p-3 border border-[#22D3EE15]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-white">📊 거래량 급증 전략</span>
                    <span className="text-xs font-mono text-[#475569]">v1</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-xs text-[#475569]">익절</p>
                      <p className="text-sm font-mono font-bold text-[#22C55E]">+20%</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#475569]">손절</p>
                      <p className="text-sm font-mono font-bold text-[#EF4444]">-10%</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#475569]">포지션</p>
                      <p className="text-sm font-mono font-bold text-[#22D3EE]">$100</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 입력바 */}
          <div className="flex items-center gap-3 px-4 py-3 bg-[#0F172A] border-t border-[#1E293B]">
            <div className="flex-1 bg-[#1E293B] rounded-lg px-4 py-2.5 border border-[#47556933]">
              <span className="text-sm text-[#475569]">트레이딩 전략을 설명해주세요...</span>
            </div>
            <div className="w-10 h-10 rounded-lg gradient-accent flex items-center justify-center">
              <span className="text-[#0A0F1C] text-lg">↑</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

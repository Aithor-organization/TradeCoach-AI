export default function Footer() {
  return (
    <footer className="bg-[#0A0F1C] border-t border-[#1E293B] py-12 px-6 lg:px-[120px]">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start gap-8">
          {/* 로고 */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg font-bold text-white">TradeCoach</span>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#22D3EE20] text-[#22D3EE]">
                AI
              </span>
            </div>
            <p className="text-sm text-[#64748B] max-w-xs">
              AI가 당신을 더 나은 트레이더로 만들어줍니다.
            </p>
          </div>

          {/* 링크 */}
          <div className="flex gap-12">
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Product</h4>
              <ul className="space-y-2">
                <li><a href="#features" className="text-sm text-[#64748B] hover:text-[#94A3B8]">Features</a></li>
                <li><a href="#pricing" className="text-sm text-[#64748B] hover:text-[#94A3B8]">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Resources</h4>
              <ul className="space-y-2">
                <li><a href="#how-it-works" className="text-sm text-[#64748B] hover:text-[#94A3B8]">How It Works</a></li>
                <li><a href="#" className="text-sm text-[#64748B] hover:text-[#94A3B8]">Documentation</a></li>
              </ul>
            </div>
          </div>
        </div>

        {/* 하단 */}
        <div className="mt-8 pt-8 border-t border-[#1E293B] text-center">
          <p className="text-xs text-[#475569]">
            &copy; 2026 TradeCoach AI. Built on Solana. Not financial advice.
          </p>
        </div>
      </div>
    </footer>
  );
}

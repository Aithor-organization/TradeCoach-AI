import type { Language } from "@/stores/languageStore";

const translations = {
  ko: {
    // 채팅 페이지
    "chat.strategies": "전략 목록",
    "chat.newChat": "새 대화",
    "chat.coaching": "코칭 중",
    "chat.loading": "로딩 중...",

    // 빈 상태
    "empty.title": "TradeCoach AI",
    "empty.description": "트레이딩 전략을 설명하거나, 차트 이미지를 업로드하세요.\nAI가 분석하고, 백테스트하고, 개선점을 코칭합니다.",

    // 입력
    "input.placeholder": "트레이딩 전략을 설명해주세요... (이미지 Ctrl+V 가능)",
    "input.attachImage": "이미지 첨부",

    // 백테스트
    "backtest.running": "백테스트 실행 중...",
    "backtest.complete": "백테스트 완료",
    "backtest.failed": "백테스트 실행 실패",

    // 에러
    "error.aiResponse": "오류가 발생했습니다",
    "error.checkServer": "백엔드 서버가 실행 중인지 확인해주세요.",
    "error.coaching": "코칭 요청 중 오류",

    // 네비게이션
    "nav.freeStart": "무료로 시작하기",
    "nav.features": "Features",
    "nav.howItWorks": "How It Works",
    "nav.strategies": "Strategies",
    "nav.pricing": "Pricing",

    // 전략
    "strategy.newChat": "새 대화",
    "strategy.save": "저장",
    "strategy.saveFailed": "전략 저장 실패",
    "strategy.imageAnalysis": "차트 이미지 분석 요청",

    // Hero
    "hero.headline1": "AI가 당신을 더 나은 ",
    "hero.trader": "트레이더",
    "hero.headline2": "로",
    "hero.headline3": "만들어줍니다",
    "hero.sub1": "자연어로 전략을 설명하면, AI가 분석하고 백테스트하고 개선점을 코칭합니다.",
    "hero.sub2": "솔라나 DEX에서 더 현명한 트레이딩을 시작하세요.",
    "hero.cta": "전략 만들기 시작 →",
    "hero.howItWorks": "어떻게 작동하나요?",

    // HowItWorks
    "hiw.title": "4단계로 시작하는 AI 트레이딩 코칭",
    "hiw.step1.title": "전략 설명",
    "hiw.step1.desc": "자연어로 트레이딩 전략을 설명하거나, 차트 이미지를 업로드하세요.",
    "hiw.step2.title": "AI 분석",
    "hiw.step2.desc": "Gemini AI가 전략을 구조화하고, 리스크를 사전 분석합니다.",
    "hiw.step3.title": "백테스트",
    "hiw.step3.desc": "솔라나 DEX 과거 데이터로 전략의 실제 성과를 검증합니다.",
    "hiw.step4.title": "AI 코칭",
    "hiw.step4.desc": "결과를 기반으로 개선점을 제안하고 전략을 함께 발전시킵니다.",

    // Features
    "feat.title": "트레이딩 실력을 키우는 핵심 기능",
    "feat.1.title": "자연어 전략 빌더",
    "feat.1.desc": "한국어로 전략을 설명하면 AI가 구조화된 트레이딩 전략으로 변환합니다.",
    "feat.2.title": "차트 이미지 분석",
    "feat.2.desc": "차트 스크린샷을 업로드하면 AI가 패턴을 인식하고 전략을 생성합니다.",
    "feat.3.title": "실전 백테스트",
    "feat.3.desc": "솔라나 DEX 실제 가격 데이터로 전략 성과를 검증합니다.",
    "feat.4.title": "AI 코칭 대화",
    "feat.4.desc": "백테스트 결과를 분석하고 리스크 관리, 전략 개선을 코칭합니다.",
    "feat.5.title": "솔라나 네이티브",
    "feat.5.desc": "Phantom 지갑으로 로그인, SOL/USDC 등 주요 페어 지원.",

    // Stats
    "stats.1": "Solana DEX 일일 거래량",
    "stats.2": "일일 트랜잭션 수",
    "stats.3": "전략 빌딩 프로세스",
    "stats.4": "백테스트 수수료 반영",

    // Pricing
    "pricing.title": "심플한 가격 정책",
    "pricing.free.desc": "유저 획득 보조",
    "pricing.free.f1": "기본 전략 빌딩",
    "pricing.free.f2": "월 3회 백테스트",
    "pricing.free.f3": "기본 AI 코칭",
    "pricing.free.f4": "SOL/USDC 페어",
    "pricing.free.cta": "무료로 시작",
    "pricing.premium.desc": "프리미엄 구독",
    "pricing.premium.f1": "무제한 백테스트",
    "pricing.premium.f2": "심층 AI 코칭",
    "pricing.premium.f3": "실시간 전략 알림",
    "pricing.premium.f4": "전략 무제한 저장",
    "pricing.premium.f5": "모든 토큰 페어 지원",
    "pricing.premium.cta": "Premium 시작하기",
    "pricing.web3.price": "성과 기반",
    "pricing.web3.desc": "Web3 네이티브 모델",
    "pricing.web3.f1": "Premium 전체 기능 포함",
    "pricing.web3.f2": "전략 NFT 마켓플레이스",
    "pricing.web3.f3": "검증된 전략 공유 → 로열티 수익",
    "pricing.web3.f4": "카피트레이딩 연동",
    "pricing.web3.f5": "수익 발생 시에만 과금",
    "pricing.web3.cta": "곧 출시 예정",

    // FinalCTA
    "cta.title": "지금 바로 시작하세요",
    "cta.sub1": "무료로 AI 트레이딩 코칭을 체험하세요.",
    "cta.sub2": "지갑 연결 없이도 3번의 백테스트가 가능합니다.",
    "cta.button": "무료로 전략 만들기 →",

    // ChatMockup
    "mockup.user": "거래량 3배 터진 코인 소액 진입, 20% 익절 10% 손절",
    "mockup.ai": "전략을 분석했습니다. 거래량 급증 전략으로 구조화했어요.",
    "mockup.stratName": "📊 거래량 급증 전략",
    "mockup.tp": "익절",
    "mockup.sl": "손절",
    "mockup.pos": "포지션",
    "mockup.placeholder": "트레이딩 전략을 설명해주세요...",

    // Footer
    "footer.tagline": "AI가 당신을 더 나은 트레이더로 만들어줍니다.",

    // Wallet
    "wallet.connecting": "연결 중...",
    "wallet.connect": "🔮 Phantom 연결",
    "wallet.installPhantom": "Phantom을 설치해주세요",
    "wallet.cancelled": "연결 취소됨",

    // 예시 전략 (ChatWindow)
    "example.1": "SOL/USDC 1시간봉, RSI(14) 30 이하 + 볼린저밴드 하단 터치 시 $500 매수, 익절 8% 손절 -5%",
    "example.2": "BTC/USDT 4시간봉, MACD 골든크로스 + 거래량 150% 급증 AND 조건으로 $1000 진입, 익절 7% 손절 -4%",
    "example.3": "ETH/USDT 1일봉, EMA(12/26) 골든크로스 + RSI(20) 40 이하 시 $300 매수, 익절 10% 손절 -5%",
    "example.4": "SOL/USDC 4시간봉, Stochastic RSI 20 이하 + ATR 3% 이상 변동 시 $500 매수, 익절 6% 손절 -3%",

    // 전략 카드
    "sc.entryConditions": "진입 조건",
    "sc.entryTooltip": "이 조건이 충족되면 매수 주문을 실행합니다",
    "sc.logic": "로직:",
    "sc.takeProfit": "익절",
    "sc.takeProfitTooltip": "목표 수익에 도달하면 자동 매도합니다",
    "sc.stopLoss": "손절",
    "sc.stopLossTooltip": "손실 한도에 도달하면 자동 매도하여 손실을 제한합니다",
    "sc.investment": "투자금",
    "sc.investmentTooltip": "백테스트에 사용할 총 투자 금액 (USD)",
    "sc.investmentSetting": "투자금 설정",
    "sc.target": "대상:",
    "sc.targetTooltip": "매매할 토큰 페어 (예: SOL/USDC)",
    "sc.timeframe": "타임프레임:",
    "sc.timeframeTooltip": "차트 분석에 사용되는 캔들 간격",
    "sc.saving": "저장 중...",
    "sc.saveStrategy": "전략 저장",
    "sc.saved": "저장 완료",
    "sc.runBacktest": "백테스트 실행",
    "sc.editStrategy": "전략 수정",

    // 백테스트 결과
    "bt.title": "백테스트 결과",
    "bt.totalReturn": "총 수익률",
    "bt.finalReturn": "최종 수익률",
    "bt.mdd": "최대 낙폭 (MDD)",
    "bt.risk": "위험",
    "bt.caution": "주의",
    "bt.safe": "적정",
    "bt.good": "양호",
    "bt.moderate": "보통",
    "bt.insufficient": "부족",
    "bt.winRate": "승률",
    "bt.total": "총",
    "bt.trades": "회 거래",
    "bt.initCapital": "초기자본",

    // 백테스트 차트
    "btChart.candles": "캔들",
    "btChart.basis": "기준",

    // 백테스트 요약
    "btSummary.title": "AI 전략 분석 리포트",
    "btSummary.quickImprove": "바로 개선",
    "btSummary.improvePrompt": "위 AI 전략 분석 리포트를 기반으로 전략을 개선해주세요:",

    // 거래 내역
    "tl.title": "거래 내역 (Trade Log)",
    "tl.entryDate": "진입일",
    "tl.exitDate": "청산일",
    "tl.pnl": "수익금(PnL)",
    "tl.returnPct": "수익률",

    // 전략 채팅 패널
    "cp.none": "없음",
    "cp.imageAttached": "[📎 이미지 첨부]",
    "cp.systemContext": "[시스템 컨텍스트] 사용자가 설정한 투자금:",
    "cp.systemContextSuffix": "포지션은 1개로 고정. 이 금액을 기준으로 분석해주세요.",
    "cp.analyzeChart": "이 차트를 분석해주세요",
    "cp.error": "오류가 발생했습니다.",
    "cp.loadingHistory": "대화 기록 불러오는 중...",
    "cp.aiReady": "AI Coach가 이 전략을 이미 파악하고 있습니다.",
    "cp.exampleQuestions": "예시 질문:",
    "cp.example1": "이 전략의 강점과 약점을 분석해줘",
    "cp.example2": "익절 비율을 20%로 올려줘",
    "cp.example3": "RSI 조건 외에 볼린저밴드도 추가해줘",
    "cp.strategyUpdate": "✨ 전략 업데이트 제안",
    "cp.attachImage": "이미지 첨부",
    "cp.placeholder": "전략에 대해 질문하거나 수정을 요청하세요... (이미지 Ctrl+V 가능)",
    "cp.attachedImage": "첨부 이미지",

    // 온보딩 배너
    "ob.title": "시작 가이드",
    "ob.step1Title": "전략 생성",
    "ob.step1Desc": "AI와 대화하며 트레이딩 전략을 만드세요",
    "ob.step2Title": "백테스트",
    "ob.step2Desc": "과거 데이터로 전략 성과를 검증하세요",
    "ob.step3Title": "AI 코칭",
    "ob.step3Desc": "결과 분석과 개선 방향을 제안받으세요",
    "ob.dismiss": "배너 닫기",

    // 에러 바운더리
    "eb.title": "오류가 발생했습니다",
    "eb.defaultMsg": "예상치 못한 오류가 발생했습니다.",
    "eb.retry": "다시 시도",
    "eb.home": "홈으로",

    // 전략 페이지
    "sp.breadcrumb": "전략",
    "sp.newStrategy": "+ 새 전략",
    "sp.realtimePrices": "실시간 시세",
    "sp.myStrategies": "내 전략",
    "sp.exampleTemplates": "예시 템플릿",
    "sp.examplesDesc": "검증된 투자 전략 템플릿입니다. 클릭하여 상세 정보와 백테스트를 확인한 후 가져올 수 있습니다.",
    "sp.myDesc": "AI와 대화하며 자유롭게 수정할 수 있는 내 전략입니다.",
    "sp.noExamples": "예시 템플릿이 없습니다.",
    "sp.noStrategies": "아직 내 전략이 없습니다. 예시 템플릿에서 가져오거나 새로 만들어보세요.",
    "sp.viewExamples": "예시 템플릿 보기",
    "sp.createNew": "새 전략 만들기",
    "sp.template": "템플릿",
    "sp.deleteStrategy": "전략 삭제",
    "sp.deleteConfirm": "이 전략을 삭제하시겠습니까? 관련 백테스트 기록도 함께 삭제됩니다.",
    "sp.deleteFailed": "전략 삭제에 실패했습니다.",
    "sp.parseFailed": "전략을 파싱할 수 없습니다. 더 구체적으로 설명해주세요.",
    "sp.dbSaveFailed": "전략이 생성되었지만 DB 저장에 실패했습니다.",
    "sp.createFailed": "전략 생성 실패",
    "sp.modalTitle": "새 전략 만들기",
    "sp.modalDesc": "트레이딩 전략을 자연어로 설명해주세요. AI가 구조화된 전략으로 변환합니다.",
    "sp.modalPlaceholder": "예: RSI가 30 이하일 때 매수하고, 15% 익절, 8% 손절하는 SOL/USDC 전략",
    "sp.cancel": "취소",
    "sp.creating": "AI가 전략 생성 중...",
    "sp.createAndSave": "전략 생성 및 저장",

    // 채팅 페이지 컨텍스트
    "ctx.none": "없음",
    "ctx.strategyRequest": "[전략 분석 요청]",
    "ctx.strategyName": "전략명:",
    "ctx.entryCondition": "진입조건:",
    "ctx.takeProfit": "익절:",
    "ctx.stopLoss": "손절:",
    "ctx.timeframe": "타임프레임:",
    "ctx.target": "대상:",
    "ctx.notSet": "미설정",
    "ctx.backtestResult": "[백테스트 결과]",
    "ctx.totalReturn": "총 수익률:",
    "ctx.mdd": "최대 낙폭(MDD):",
    "ctx.sharpe": "샤프비율:",
    "ctx.winRate": "승률:",
    "ctx.totalTrades": "총 거래수:",
    "ctx.coachingPrompt": "이 전략의 강점과 약점을 분석하고, 개선 방향을 제안해주세요.",

    // 전략 상세 페이지
    "sd.loading": "로딩 중...",
    "sd.notFound": "전략을 찾을 수 없습니다.",
    "sd.backToList": "목록으로 돌아가기",
    "sd.importToMy": "내 전략으로 가져오기",
    "sd.backtest": "백테스트",
    "sd.apiLimit": "(API 데이터 제한으로 시작일로부터 41.6일 치만 조회됩니다)",
    "sd.startDate": "시작일",
    "sd.endDate": "종료일",
    "sd.running": "실행 중...",
    "sd.runBacktest": "백테스트 실행",
    "sd.latestRun": "최근 실행",
    "sd.previousRun": "이전 실행",
    "sd.previousRecord": "이전 기록",
    "sd.deleteRecord": "이 기록 삭제",
    "sd.period": "조회 기간:",
    "sd.applyStrategy": "이 전략(조건)으로 덮어쓰기",
    "sd.myStrategiesList": "내 전략 목록",
    "sd.backtestHistory": "백테스트 리포트 목록",
    "sd.noHistory": "저장된 이전 백테스트 기록이 없습니다.",
    "sd.importModalTitle": "내 전략으로 가져오기",
    "sd.importModalDesc": "전략의 제목을 입력하세요. 가져온 후 AI와 대화하며 자유롭게 수정할 수 있습니다.",
    "sd.strategyTitle": "전략 제목",
    "sd.importing": "가져오는 중...",
    "sd.save": "저장",
    "sd.editModalTitle": "전략 직접 수정 (JSON)",
    "sd.editModalDesc": "전략의 구조를 직접 커스터마이징할 수 있습니다. 수치를 변경하거나 새로운 지표 문법 체계를 덮어쓸 수 있습니다.",
    "sd.applyChanges": "수정 사항 반영 (덮어쓰기)",
    "sd.deleteHistoryConfirm": "이 백테스트 기록을 삭제하시겠습니까? (사용 전략 및 거래 내역 포함)",
    "sd.deleteHistoryFailed": "백테스트 기록 삭제에 실패했습니다.",
    "sd.requiredFields": "필수 필드(name, target_pair, timeframe)가 누락되었습니다.",
    "sd.invalidJson": "JSON 형식이 올바르지 않습니다.",

    // StrategyCard 추가
    "sc.half": "(절반)",
  },
  en: {
    // 채팅 페이지
    "chat.strategies": "Strategies",
    "chat.newChat": "New Chat",
    "chat.coaching": "Coaching",
    "chat.loading": "Loading...",

    // 빈 상태
    "empty.title": "TradeCoach AI",
    "empty.description": "Describe your trading strategy or upload a chart image.\nAI will analyze, backtest, and coach you on improvements.",

    // 입력
    "input.placeholder": "Describe your trading strategy... (Ctrl+V for images)",
    "input.attachImage": "Attach image",

    // 백테스트
    "backtest.running": "Running backtest...",
    "backtest.complete": "Backtest complete",
    "backtest.failed": "Backtest execution failed",

    // 에러
    "error.aiResponse": "An error occurred",
    "error.checkServer": "Please check if the backend server is running.",
    "error.coaching": "Error during coaching request",

    // 네비게이션
    "nav.freeStart": "Get Started Free",
    "nav.features": "Features",
    "nav.howItWorks": "How It Works",
    "nav.strategies": "Strategies",
    "nav.pricing": "Pricing",

    // 전략
    "strategy.newChat": "New Chat",
    "strategy.save": "Save",
    "strategy.saveFailed": "Failed to save strategy",
    "strategy.imageAnalysis": "Chart image analysis request",

    // Hero
    "hero.headline1": "AI makes you a better ",
    "hero.trader": "trader",
    "hero.headline2": "",
    "hero.headline3": "",
    "hero.sub1": "Describe your strategy in plain language — AI analyzes, backtests, and coaches improvements.",
    "hero.sub2": "Start smarter trading on Solana DEX.",
    "hero.cta": "Start Building Strategy →",
    "hero.howItWorks": "How does it work?",

    // HowItWorks
    "hiw.title": "AI Trading Coaching in 4 Steps",
    "hiw.step1.title": "Describe Strategy",
    "hiw.step1.desc": "Describe your trading strategy in plain language or upload a chart image.",
    "hiw.step2.title": "AI Analysis",
    "hiw.step2.desc": "Gemini AI structures your strategy and pre-analyzes risk factors.",
    "hiw.step3.title": "Backtest",
    "hiw.step3.desc": "Verify strategy performance with real Solana DEX historical data.",
    "hiw.step4.title": "AI Coaching",
    "hiw.step4.desc": "Get improvement suggestions based on results and evolve your strategy.",

    // Features
    "feat.title": "Core Features to Level Up Your Trading",
    "feat.1.title": "Natural Language Strategy Builder",
    "feat.1.desc": "Describe your strategy in plain language and AI converts it into a structured trading strategy.",
    "feat.2.title": "Chart Image Analysis",
    "feat.2.desc": "Upload chart screenshots and AI recognizes patterns to generate strategies.",
    "feat.3.title": "Real Backtesting",
    "feat.3.desc": "Verify strategy performance with real Solana DEX price data.",
    "feat.4.title": "AI Coaching Chat",
    "feat.4.desc": "Analyze backtest results and get coaching on risk management and strategy improvements.",
    "feat.5.title": "Solana Native",
    "feat.5.desc": "Login with Phantom wallet, supporting major pairs like SOL/USDC.",

    // Stats
    "stats.1": "Solana DEX Daily Volume",
    "stats.2": "Daily Transactions",
    "stats.3": "Strategy Building Process",
    "stats.4": "Backtest Fee Reflected",

    // Pricing
    "pricing.title": "Simple Pricing",
    "pricing.free.desc": "Get started for free",
    "pricing.free.f1": "Basic strategy building",
    "pricing.free.f2": "3 backtests/month",
    "pricing.free.f3": "Basic AI coaching",
    "pricing.free.f4": "SOL/USDC pair",
    "pricing.free.cta": "Start Free",
    "pricing.premium.desc": "Premium subscription",
    "pricing.premium.f1": "Unlimited backtests",
    "pricing.premium.f2": "Advanced AI coaching",
    "pricing.premium.f3": "Real-time strategy alerts",
    "pricing.premium.f4": "Unlimited strategy storage",
    "pricing.premium.f5": "All token pairs supported",
    "pricing.premium.cta": "Start Premium",
    "pricing.web3.price": "Performance-based",
    "pricing.web3.desc": "Web3 Native Model",
    "pricing.web3.f1": "All Premium features included",
    "pricing.web3.f2": "Strategy NFT Marketplace",
    "pricing.web3.f3": "Share verified strategies → earn royalties",
    "pricing.web3.f4": "Copy trading integration",
    "pricing.web3.f5": "Pay only when you profit",
    "pricing.web3.cta": "Coming Soon",

    // FinalCTA
    "cta.title": "Get Started Now",
    "cta.sub1": "Experience AI trading coaching for free.",
    "cta.sub2": "3 backtests available without connecting a wallet.",
    "cta.button": "Build Strategy Free →",

    // ChatMockup
    "mockup.user": "Small entry on 3x volume coin, 20% TP 10% SL",
    "mockup.ai": "Strategy analyzed. Structured as a volume surge strategy.",
    "mockup.stratName": "📊 Volume Surge Strategy",
    "mockup.tp": "TP",
    "mockup.sl": "SL",
    "mockup.pos": "Position",
    "mockup.placeholder": "Describe your trading strategy...",

    // Footer
    "footer.tagline": "AI makes you a better trader.",

    // Wallet
    "wallet.connecting": "Connecting...",
    "wallet.connect": "🔮 Connect Phantom",
    "wallet.installPhantom": "Please install Phantom",
    "wallet.cancelled": "Connection cancelled",

    // 예시 전략 (ChatWindow)
    "example.1": "SOL/USDC 1h, buy $500 when RSI(14) ≤ 30 + BB lower touch, TP 8% SL -5%",
    "example.2": "BTC/USDT 4h, MACD golden cross + 150% volume surge AND logic, $1000 entry, TP 7% SL -4%",
    "example.3": "ETH/USDT 1d, EMA(12/26) golden cross + RSI(20) ≤ 40, buy $300, TP 10% SL -5%",
    "example.4": "SOL/USDC 4h, Stochastic RSI ≤ 20 + ATR ≥ 3% move, buy $500, TP 6% SL -3%",

    // 전략 카드
    "sc.entryConditions": "Entry Conditions",
    "sc.entryTooltip": "Buy order executes when these conditions are met",
    "sc.logic": "Logic:",
    "sc.takeProfit": "Take Profit",
    "sc.takeProfitTooltip": "Automatically sells when target profit is reached",
    "sc.stopLoss": "Stop Loss",
    "sc.stopLossTooltip": "Automatically sells to limit losses when threshold is reached",
    "sc.investment": "Investment",
    "sc.investmentTooltip": "Total investment amount for backtesting (USD)",
    "sc.investmentSetting": "Set Investment",
    "sc.target": "Pair:",
    "sc.targetTooltip": "Token pair to trade (e.g., SOL/USDC)",
    "sc.timeframe": "Timeframe:",
    "sc.timeframeTooltip": "Candle interval used for chart analysis",
    "sc.saving": "Saving...",
    "sc.saveStrategy": "Save Strategy",
    "sc.saved": "Saved",
    "sc.runBacktest": "Run Backtest",
    "sc.editStrategy": "Edit Strategy",

    // 백테스트 결과
    "bt.title": "Backtest Result",
    "bt.totalReturn": "Total Return",
    "bt.finalReturn": "Final Return",
    "bt.mdd": "Max Drawdown (MDD)",
    "bt.risk": "Risky",
    "bt.caution": "Caution",
    "bt.safe": "Safe",
    "bt.good": "Good",
    "bt.moderate": "Moderate",
    "bt.insufficient": "Poor",
    "bt.winRate": "Win Rate",
    "bt.total": "Total",
    "bt.trades": "trades",
    "bt.initCapital": "Initial Capital",

    // 백테스트 차트
    "btChart.candles": "candles",
    "btChart.basis": "basis",

    // 백테스트 요약
    "btSummary.title": "AI Strategy Analysis Report",
    "btSummary.quickImprove": "Quick Improve",
    "btSummary.improvePrompt": "Please improve the strategy based on the above AI analysis report:",

    // 거래 내역
    "tl.title": "Trade Log",
    "tl.entryDate": "Entry Date",
    "tl.exitDate": "Exit Date",
    "tl.pnl": "PnL",
    "tl.returnPct": "Return %",

    // 전략 채팅 패널
    "cp.none": "None",
    "cp.imageAttached": "[📎 Image attached]",
    "cp.systemContext": "[System Context] User-set investment:",
    "cp.systemContextSuffix": "Fixed to 1 position. Please analyze based on this amount.",
    "cp.analyzeChart": "Please analyze this chart",
    "cp.error": "An error occurred.",
    "cp.loadingHistory": "Loading chat history...",
    "cp.aiReady": "AI Coach already understands this strategy.",
    "cp.exampleQuestions": "Example questions:",
    "cp.example1": "Analyze this strategy's strengths and weaknesses",
    "cp.example2": "Increase take profit ratio to 20%",
    "cp.example3": "Add Bollinger Band condition besides RSI",
    "cp.strategyUpdate": "✨ Strategy Update Suggestion",
    "cp.attachImage": "Attach image",
    "cp.placeholder": "Ask questions or request changes to the strategy... (Ctrl+V for images)",
    "cp.attachedImage": "Attached image",

    // 온보딩 배너
    "ob.title": "Getting Started",
    "ob.step1Title": "Create Strategy",
    "ob.step1Desc": "Chat with AI to build your trading strategy",
    "ob.step2Title": "Backtest",
    "ob.step2Desc": "Verify strategy performance with historical data",
    "ob.step3Title": "AI Coaching",
    "ob.step3Desc": "Get analysis and improvement suggestions",
    "ob.dismiss": "Dismiss banner",

    // 에러 바운더리
    "eb.title": "An error occurred",
    "eb.defaultMsg": "An unexpected error occurred.",
    "eb.retry": "Try Again",
    "eb.home": "Go Home",

    // 전략 페이지
    "sp.breadcrumb": "Strategies",
    "sp.newStrategy": "+ New Strategy",
    "sp.realtimePrices": "Real-time Prices",
    "sp.myStrategies": "My Strategies",
    "sp.exampleTemplates": "Example Templates",
    "sp.examplesDesc": "Verified trading strategy templates. Click to view details and backtest, then import.",
    "sp.myDesc": "Your strategies that you can freely modify through AI conversations.",
    "sp.noExamples": "No example templates available.",
    "sp.noStrategies": "No strategies yet. Import from examples or create a new one.",
    "sp.viewExamples": "View Examples",
    "sp.createNew": "Create New Strategy",
    "sp.template": "Template",
    "sp.deleteStrategy": "Delete Strategy",
    "sp.deleteConfirm": "Delete this strategy? Associated backtest records will also be deleted.",
    "sp.deleteFailed": "Failed to delete strategy.",
    "sp.parseFailed": "Could not parse strategy. Please describe more specifically.",
    "sp.dbSaveFailed": "Strategy created but database save failed.",
    "sp.createFailed": "Strategy creation failed",
    "sp.modalTitle": "Create New Strategy",
    "sp.modalDesc": "Describe your trading strategy in natural language. AI will convert it into a structured strategy.",
    "sp.modalPlaceholder": "e.g., Buy SOL/USDC when RSI < 30, TP 15%, SL 8%",
    "sp.cancel": "Cancel",
    "sp.creating": "AI creating strategy...",
    "sp.createAndSave": "Create & Save",

    // 채팅 페이지 컨텍스트
    "ctx.none": "None",
    "ctx.strategyRequest": "[Strategy Analysis Request]",
    "ctx.strategyName": "Strategy:",
    "ctx.entryCondition": "Entry:",
    "ctx.takeProfit": "TP:",
    "ctx.stopLoss": "SL:",
    "ctx.timeframe": "Timeframe:",
    "ctx.target": "Pair:",
    "ctx.notSet": "Not set",
    "ctx.backtestResult": "[Backtest Result]",
    "ctx.totalReturn": "Total Return:",
    "ctx.mdd": "Max Drawdown (MDD):",
    "ctx.sharpe": "Sharpe Ratio:",
    "ctx.winRate": "Win Rate:",
    "ctx.totalTrades": "Total Trades:",
    "ctx.coachingPrompt": "Analyze this strategy's strengths and weaknesses, and suggest improvements.",

    // 전략 상세 페이지
    "sd.loading": "Loading...",
    "sd.notFound": "Strategy not found.",
    "sd.backToList": "Back to list",
    "sd.importToMy": "Import to My Strategies",
    "sd.backtest": "Backtest",
    "sd.apiLimit": "(Due to API data limits, only ~41.6 days from start date are fetched)",
    "sd.startDate": "Start Date",
    "sd.endDate": "End Date",
    "sd.running": "Running...",
    "sd.runBacktest": "Run Backtest",
    "sd.latestRun": "Latest Run",
    "sd.previousRun": "Previous Run",
    "sd.previousRecord": "Previous",
    "sd.deleteRecord": "Delete this record",
    "sd.period": "Period:",
    "sd.applyStrategy": "Apply this strategy",
    "sd.myStrategiesList": "My Strategies",
    "sd.backtestHistory": "Backtest Report History",
    "sd.noHistory": "No previous backtest records.",
    "sd.importModalTitle": "Import to My Strategies",
    "sd.importModalDesc": "Enter a title for the strategy. After importing, you can modify it freely through AI conversation.",
    "sd.strategyTitle": "Strategy title",
    "sd.importing": "Importing...",
    "sd.save": "Save",
    "sd.editModalTitle": "Edit Strategy (JSON)",
    "sd.editModalDesc": "Customize strategy structure directly. You can change values or override indicator syntax.",
    "sd.applyChanges": "Apply Changes (Overwrite)",
    "sd.deleteHistoryConfirm": "Delete this backtest record? (Including strategy and trade log)",
    "sd.deleteHistoryFailed": "Failed to delete backtest record.",
    "sd.requiredFields": "Required fields (name, target_pair, timeframe) are missing.",
    "sd.invalidJson": "Invalid JSON format.",

    // StrategyCard 추가
    "sc.half": "(half)",
  },
} as const;

type TranslationKey = keyof typeof translations.ko;

export function t(key: TranslationKey, lang: Language): string {
  return translations[lang][key] || translations.ko[key] || key;
}

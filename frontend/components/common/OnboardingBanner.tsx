"use client";

import { useState, useEffect } from "react";

const STORAGE_KEY = "tc_onboarding_dismissed";

const STEPS = [
  { num: "1", title: "전략 생성", desc: "AI와 대화하며 트레이딩 전략을 만드세요" },
  { num: "2", title: "백테스트", desc: "과거 데이터로 전략 성과를 검증하세요" },
  { num: "3", title: "AI 코칭", desc: "결과 분석과 개선 방향을 제안받으세요" },
];

export default function OnboardingBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) setVisible(true);
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  };

  return (
    <div className="mb-6 bg-gradient-to-r from-[#22D3EE08] to-[#06B6D408] border border-[#22D3EE20] rounded-xl p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-[#22D3EE] text-xs font-semibold uppercase tracking-wider mb-3">
            시작 가이드
          </p>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-6">
            {STEPS.map((s) => (
              <div key={s.num} className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#22D3EE] text-[#0A0F1C] text-xs font-bold flex items-center justify-center">
                  {s.num}
                </span>
                <div>
                  <span className="text-white text-sm font-medium">{s.title}</span>
                  <p className="text-[#475569] text-xs mt-0.5">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <button
          onClick={dismiss}
          aria-label="배너 닫기"
          className="flex-shrink-0 text-[#475569] hover:text-white transition text-lg leading-none cursor-pointer"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

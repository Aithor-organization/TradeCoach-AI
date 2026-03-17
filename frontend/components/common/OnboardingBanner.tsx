"use client";

import { useState, useEffect } from "react";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

const STORAGE_KEY = "tc_onboarding_dismissed";

export default function OnboardingBanner() {
  const [visible, setVisible] = useState(false);
  const { language } = useLanguageStore();

  const steps = [
    { num: "1", title: t("ob.step1Title", language), desc: t("ob.step1Desc", language) },
    { num: "2", title: t("ob.step2Title", language), desc: t("ob.step2Desc", language) },
    { num: "3", title: t("ob.step3Title", language), desc: t("ob.step3Desc", language) },
  ];

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
            {t("ob.title", language)}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-6">
            {steps.map((s) => (
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
          aria-label={t("ob.dismiss", language)}
          className="flex-shrink-0 text-[#475569] hover:text-white transition text-lg leading-none cursor-pointer"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

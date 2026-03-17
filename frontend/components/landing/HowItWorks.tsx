"use client";

import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

const STEP_ICONS = ["💬", "🤖", "📊", "🎯"];

export default function HowItWorks() {
  const { language } = useLanguageStore();

  const steps = [
    { number: "01", title: t("hiw.step1.title", language), description: t("hiw.step1.desc", language), icon: STEP_ICONS[0] },
    { number: "02", title: t("hiw.step2.title", language), description: t("hiw.step2.desc", language), icon: STEP_ICONS[1] },
    { number: "03", title: t("hiw.step3.title", language), description: t("hiw.step3.desc", language), icon: STEP_ICONS[2] },
    { number: "04", title: t("hiw.step4.title", language), description: t("hiw.step4.desc", language), icon: STEP_ICONS[3] },
  ];

  return (
    <section id="how-it-works" className="py-24 px-6 lg:px-[120px] bg-[#0F172A]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <span className="font-mono text-xs font-medium text-[#22D3EE] tracking-wider uppercase">
            How It Works
          </span>
          <h2 className="text-3xl md:text-[40px] font-bold mt-3">
            {t("hiw.title", language)}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step) => (
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

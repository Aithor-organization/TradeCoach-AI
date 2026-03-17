"use client";

import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

const FEATURE_ICONS = ["🗣️", "📸", "📈", "🎓", "⚡"];

export default function Features() {
  const { language } = useLanguageStore();

  const features = [
    { title: t("feat.1.title", language), description: t("feat.1.desc", language), icon: FEATURE_ICONS[0] },
    { title: t("feat.2.title", language), description: t("feat.2.desc", language), icon: FEATURE_ICONS[1] },
    { title: t("feat.3.title", language), description: t("feat.3.desc", language), icon: FEATURE_ICONS[2] },
    { title: t("feat.4.title", language), description: t("feat.4.desc", language), icon: FEATURE_ICONS[3] },
    { title: t("feat.5.title", language), description: t("feat.5.desc", language), icon: FEATURE_ICONS[4] },
  ];

  return (
    <section id="features" className="py-24 px-6 lg:px-[120px]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <span className="font-mono text-xs font-medium text-[#22D3EE] tracking-wider uppercase">
            Features
          </span>
          <h2 className="text-3xl md:text-[40px] font-bold mt-3">
            {t("feat.title", language)}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {features.slice(0, 3).map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
          {features.slice(3).map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ title, description, icon }: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="bg-[#0F172A] rounded-xl p-7 border border-[#22D3EE10] hover:border-[#22D3EE30] transition-all group">
      <span className="text-3xl mb-4 block">{icon}</span>
      <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-[#22D3EE] transition-colors">
        {title}
      </h3>
      <p className="text-sm text-[#94A3B8] leading-relaxed">
        {description}
      </p>
    </div>
  );
}

"use client";

import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

export default function Stats() {
  const { language } = useLanguageStore();

  const stats = [
    { value: "$18B+", label: t("stats.1", language) },
    { value: "10B+", label: t("stats.2", language) },
    { value: "4 Steps", label: t("stats.3", language) },
    { value: "0.3%", label: t("stats.4", language) },
  ];

  return (
    <section className="py-20 px-6 lg:px-[120px] bg-[#0F172A]">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat) => (
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

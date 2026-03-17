"use client";

import Button from "@/components/common/Button";
import Link from "next/link";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

export default function Pricing() {
  const { language } = useLanguageStore();

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      description: t("pricing.free.desc", language),
      features: [
        t("pricing.free.f1", language),
        t("pricing.free.f2", language),
        t("pricing.free.f3", language),
        t("pricing.free.f4", language),
      ],
      cta: t("pricing.free.cta", language),
      variant: "secondary" as const,
      highlight: false,
    },
    {
      name: "Premium",
      price: "$19.99",
      period: "/month",
      description: t("pricing.premium.desc", language),
      features: [
        t("pricing.premium.f1", language),
        t("pricing.premium.f2", language),
        t("pricing.premium.f3", language),
        t("pricing.premium.f4", language),
        t("pricing.premium.f5", language),
      ],
      cta: t("pricing.premium.cta", language),
      variant: "primary" as const,
      highlight: true,
    },
    {
      name: "Web3 Native",
      price: t("pricing.web3.price", language),
      period: "",
      description: t("pricing.web3.desc", language),
      features: [
        t("pricing.web3.f1", language),
        t("pricing.web3.f2", language),
        t("pricing.web3.f3", language),
        t("pricing.web3.f4", language),
        t("pricing.web3.f5", language),
      ],
      cta: t("pricing.web3.cta", language),
      variant: "secondary" as const,
      highlight: false,
    },
  ];

  return (
    <section id="pricing" className="py-24 px-6 lg:px-[120px]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <span className="font-mono text-xs font-medium text-[#22D3EE] tracking-wider uppercase">
            Pricing
          </span>
          <h2 className="text-3xl md:text-[40px] font-bold mt-3">
            {t("pricing.title", language)}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-xl p-8 ${
                plan.highlight
                  ? "bg-[#1E293B] border-2 border-[#22D3EE] relative"
                  : "bg-[#1E293B] border border-[#22D3EE15]"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="font-mono text-xs font-bold px-3 py-1 rounded-full gradient-accent text-[#0A0F1C]">
                    POPULAR
                  </span>
                </div>
              )}

              <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
              <p className="text-sm text-[#94A3B8] mb-4">{plan.description}</p>

              <div className="flex items-baseline gap-1 mb-6">
                <span className="font-mono text-4xl font-bold text-white">{plan.price}</span>
                <span className="text-sm text-[#475569]">{plan.period}</span>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm text-[#94A3B8]">
                    <span className="text-[#22D3EE]">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <Link href="/chat" className="block">
                <Button variant={plan.variant} className="w-full">
                  {plan.cta}
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

"use client";

import Link from "next/link";
import Button from "@/components/common/Button";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

export default function FinalCTA() {
  const { language } = useLanguageStore();

  return (
    <section className="py-24 px-6 lg:px-[120px]">
      <div className="max-w-3xl mx-auto text-center relative">
        {/* 배경 글로우 */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#22D3EE10] via-[#06B6D420] to-[#22D3EE10] rounded-3xl blur-2xl" />

        <div className="relative bg-[#0F172A] rounded-2xl p-12 border border-[#22D3EE20]">
          <h2 className="text-3xl md:text-[40px] font-bold mb-4">
            {t("cta.title", language)}
          </h2>
          <p className="text-lg text-[#94A3B8] mb-8">
            {t("cta.sub1", language)}
            <br />
            {t("cta.sub2", language)}
          </p>
          <Link href="/chat">
            <Button size="lg">
              {t("cta.button", language)}
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}

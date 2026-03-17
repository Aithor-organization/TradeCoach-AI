import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Language = "ko" | "en";

interface LanguageState {
  language: Language;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
}

export const useLanguageStore = create<LanguageState>()(
  persist(
    (set) => ({
      language: "ko",
      setLanguage: (lang) => set({ language: lang }),
      toggleLanguage: () =>
        set((state) => ({ language: state.language === "ko" ? "en" : "ko" })),
    }),
    { name: "tc-language" }
  )
);

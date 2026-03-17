import { create } from "zustand";

export type Language = "ko" | "en";

interface LanguageState {
  language: Language;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
}

export const useLanguageStore = create<LanguageState>()((set) => ({
  language: "en",
  setLanguage: (lang) => set({ language: lang }),
  toggleLanguage: () =>
    set((state) => ({ language: state.language === "ko" ? "en" : "ko" })),
}));

import React, { createContext, useContext, useState } from "react";
import { type Locale, type Translations, translations } from "./translations";

interface I18nContextValue {
  locale: Locale;
  setLocale: (loc: Locale) => void;
  t: Translations;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem("avrig-lang");
    if (saved === "en" || saved === "id") return saved;
    return "en";
  });

  const setLocale = (loc: Locale) => {
    setLocaleState(loc);
    localStorage.setItem("avrig-lang", loc);
  };

  const t = translations[locale];

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = (): I18nContextValue => {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
};

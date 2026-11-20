import React, { useState, useRef, useEffect } from "react";
import { Languages, Check } from "lucide-react";
import { useI18n } from "../i18n/I18nContext";
import type { Locale } from "../i18n/translations";

interface LanguageSelectorProps {
  className?: string;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({ className = "" }) => {
  const { locale, setLocale } = useI18n();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const languages: Array<{ code: Locale; name: string; nativeName: string }> = [
    { code: "en", name: "English", nativeName: "English" },
    { code: "id", name: "Indonesian", nativeName: "Bahasa Indonesia" },
  ];

  return (
    <div className={`relative inline-block text-left ${className}`} ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Select language"
        aria-haspopup="true"
        aria-expanded={open}
        className="flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 text-xs text-text-secondary transition-colors duration-[120ms] ease-out hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring active:scale-[0.99]"
        title="Select language"
      >
        <Languages className="size-4" strokeWidth={1.5} />
        <span className="font-mono">{locale}</span>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Language options"
          className="absolute right-0 z-50 mt-1.5 w-44 rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-sm focus:outline-hidden"
        >
          {languages.map((lang) => {
            const isSelected = locale === lang.code;
            return (
              <button
                key={lang.code}
                role="menuitemradio"
                aria-checked={isSelected}
                type="button"
                onClick={() => {
                  setLocale(lang.code);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded p-2 text-left text-xs transition-colors duration-[120ms] ease-out ${
                  isSelected
                    ? "bg-accent text-accent-foreground"
                    : "text-text-secondary hover:bg-accent/60 hover:text-foreground"
                }`}
              >
                <span className="flex flex-col gap-0.5">
                  <span className="text-foreground">{lang.nativeName}</span>
                  <span className="text-[11px] text-muted-foreground">{lang.name}</span>
                </span>
                {isSelected && (
                  <Check className="size-4 text-accent-text" strokeWidth={1.5} aria-hidden="true" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

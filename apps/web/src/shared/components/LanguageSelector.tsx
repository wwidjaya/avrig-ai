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
        className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-background/80 px-2 text-xs font-mono font-semibold text-foreground shadow-xs transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden cursor-pointer"
        title="Select Language"
      >
        <Languages className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="uppercase tracking-wider">{locale}</span>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Language options"
          className="absolute right-0 mt-1.5 w-44 origin-top-right rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md backdrop-blur-md z-50 focus:outline-hidden"
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
                className={`flex w-full items-center justify-between rounded-sm px-2.5 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                  isSelected
                    ? "bg-accent text-accent-foreground font-semibold"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                }`}
              >
                <div className="flex flex-col text-left">
                  <span className="font-medium text-foreground">{lang.nativeName}</span>
                  <span className="text-[10px] text-muted-foreground">{lang.name}</span>
                </div>
                {isSelected && <Check className="h-3.5 w-3.5 text-primary" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

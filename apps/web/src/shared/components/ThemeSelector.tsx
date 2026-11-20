import React, { useState, useRef, useEffect } from "react";
import { Sun, Moon, Monitor, Check } from "lucide-react";
import { useTheme, type Theme } from "../theme/ThemeContext";
import { useI18n } from "../i18n/I18nContext";

interface ThemeSelectorProps {
  className?: string;
}

export const ThemeSelector: React.FC<ThemeSelectorProps> = ({ className = "" }) => {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { t } = useI18n();
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

  const themeOptions: Array<{ id: Theme; label: string; icon: React.ComponentType<{ className?: string; strokeWidth?: number }> }> = [
    { id: "light", label: t.theme.light, icon: Sun },
    { id: "dark", label: t.theme.dark, icon: Moon },
    { id: "system", label: t.theme.system, icon: Monitor },
  ];

  const currentIcon = theme === "system" ? Monitor : resolvedTheme === "dark" ? Moon : Sun;
  const CurrentIconComponent = currentIcon;

  return (
    <div className={`relative inline-block text-left ${className}`} ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Select theme"
        aria-haspopup="true"
        aria-expanded={open}
        className="flex size-9 items-center justify-center rounded-lg border border-border bg-background text-text-secondary transition-colors duration-[120ms] ease-out hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring active:scale-[0.99]"
        title={`Theme: ${theme}`}
      >
        <CurrentIconComponent className="size-4" strokeWidth={1.5} />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Theme options"
          className="absolute right-0 z-50 mt-1.5 w-40 rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-sm focus:outline-hidden"
        >
          {themeOptions.map((opt) => {
            const Icon = opt.icon;
            const isSelected = theme === opt.id;
            return (
              <button
                key={opt.id}
                role="menuitemradio"
                aria-checked={isSelected}
                type="button"
                onClick={() => {
                  setTheme(opt.id);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded p-2 text-xs transition-colors duration-[120ms] ease-out ${
                  isSelected
                    ? "bg-accent text-accent-foreground"
                    : "text-text-secondary hover:bg-accent/60 hover:text-foreground"
                }`}
              >
                <span className="flex items-center gap-2">
                  <Icon className="size-4" strokeWidth={1.5} />
                  <span>{opt.label}</span>
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

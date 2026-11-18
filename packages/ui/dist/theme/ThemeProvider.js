import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useEffect, useState } from "react";
const ThemeContext = createContext(undefined);
export function ThemeProvider({ children, defaultTheme = "system", storageKey = "avrig-ui-theme" }) {
    const [theme, setThemeState] = useState(() => {
        if (typeof window !== "undefined") {
            try {
                const stored = localStorage.getItem(storageKey);
                if (stored)
                    return stored;
            }
            catch {
                // fallback
            }
        }
        return defaultTheme;
    });
    const [resolvedTheme, setResolvedTheme] = useState("dark");
    useEffect(() => {
        const root = window.document.documentElement;
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
        const applyTheme = () => {
            let active = "dark";
            if (theme === "system") {
                active = mediaQuery.matches ? "dark" : "light";
            }
            else {
                active = theme;
            }
            setResolvedTheme(active);
            root.classList.remove("light", "dark");
            root.classList.add(active);
        };
        applyTheme();
        const listener = () => {
            if (theme === "system")
                applyTheme();
        };
        mediaQuery.addEventListener("change", listener);
        return () => mediaQuery.removeEventListener("change", listener);
    }, [theme]);
    const setTheme = (newTheme) => {
        try {
            localStorage.setItem(storageKey, newTheme);
        }
        catch {
            // storage unavailable
        }
        setThemeState(newTheme);
    };
    return (_jsx(ThemeContext.Provider, { value: { theme, resolvedTheme, setTheme }, children: children }));
}
export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return context;
}
//# sourceMappingURL=ThemeProvider.js.map
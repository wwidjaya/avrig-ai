import React from "react";
export type Theme = "dark" | "light" | "system";
export interface ThemeContextType {
    theme: Theme;
    resolvedTheme: "dark" | "light";
    setTheme: (theme: Theme) => void;
}
export interface ThemeProviderProps {
    children: React.ReactNode;
    defaultTheme?: Theme;
    storageKey?: string;
}
export declare function ThemeProvider({ children, defaultTheme, storageKey }: ThemeProviderProps): React.JSX.Element;
export declare function useTheme(): ThemeContextType;
//# sourceMappingURL=ThemeProvider.d.ts.map
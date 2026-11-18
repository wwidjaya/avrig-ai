import { createContext, useContext } from "react";
import type { AppConfig } from "./types";

export const ConfigContext = createContext<AppConfig | null>(null);

export function useAppConfig(): AppConfig {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error("useAppConfig must be used within a ConfigContext.Provider");
  }
  return context;
}

import type { AppConfig } from "./types";

export async function loadConfig(): Promise<AppConfig> {
  const response = await fetch("/config.json", {
    cache: "no-store",
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(
      `Failed to load runtime configuration (/config.json): ${response.status} ${response.statusText}`
    );
  }

  const config: AppConfig = await response.json();

  // Dynamically align redirectUri, postLogoutRedirectUri, and apiBaseUrl to current origin if in browser
  if (typeof window !== "undefined" && window.location) {
    const origin = window.location.origin;
    // When running under app.avrig.ai, ensure apiBaseUrl is empty relative path
    if (origin.includes("app.avrig.ai")) {
      config.apiBaseUrl = "";
      config.wsBaseUrl = `wss://${window.location.host}/ws`;
    }
    if (config.auth) {
      if (config.auth.redirectUri && !config.auth.redirectUri.startsWith(origin)) {
        config.auth.redirectUri = `${origin}/auth/callback`;
      }
      if (config.auth.postLogoutRedirectUri && !config.auth.postLogoutRedirectUri.startsWith(origin)) {
        config.auth.postLogoutRedirectUri = `${origin}/`;
      }
    }
  }

  return config;
}

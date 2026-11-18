import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { loadConfig } from "./shared/config/loadConfig";
import { ConfigContext } from "./shared/config/ConfigContext";
import { UniversalAuthProvider } from "./shared/auth/UniversalAuthProvider";
import { ApiProvider } from "./shared/api/ApiContext";
import { ThemeProvider } from "./shared/theme/ThemeContext";
import { I18nProvider } from "./shared/i18n/I18nContext";
import { App } from "./app/App";
import "./styles/globals.css";

function renderBootstrapError(error: unknown) {
  const root = document.getElementById("root");
  if (!root) return;

  const message = error instanceof Error ? error.message : String(error);
  root.innerHTML = `
    <div style="display:flex;min-height:100vh;flex-direction:column;align-items:center;justify-content:center;background:#09090b;color:#f43f5e;font-family:sans-serif;padding:24px;text-align:center;">
      <h1 style="font-size:20px;font-weight:bold;margin-bottom:8px;">Command Center Bootstrap Failure</h1>
      <p style="color:#a1a1aa;font-size:14px;max-width:480px;line-height:1.5;margin-bottom:16px;">
        Failed to load runtime configuration from <code>/config.json</code>. Ensure the configuration file exists and is accessible.
      </p>
      <pre style="background:#18181b;padding:12px;border-radius:6px;font-size:12px;color:#fca5a5;max-width:600px;overflow-x:auto;">${message}</pre>
    </div>
  `;
}

async function bootstrap() {
  try {
    const config = await loadConfig();

    const rootElement = document.getElementById("root");
    if (!rootElement) {
      throw new Error("Root element '#root' not found in DOM");
    }

    createRoot(rootElement).render(
      <StrictMode>
        <ConfigContext.Provider value={config}>
          <UniversalAuthProvider>
            <ThemeProvider>
              <I18nProvider>
                <ApiProvider>
                  <App />
                </ApiProvider>
              </I18nProvider>
            </ThemeProvider>
          </UniversalAuthProvider>
        </ConfigContext.Provider>
      </StrictMode>
    );
  } catch (err) {
    renderBootstrapError(err);
  }
}

bootstrap();

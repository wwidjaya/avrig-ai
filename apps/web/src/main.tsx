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

// This screen renders text that comes from an exception, on a path that is
// already running because the app failed to start, so the message is escaped
// rather than trusted: it must never be able to inject markup.
function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderBootstrapError(error: unknown) {
  const root = document.getElementById("root");
  if (!root) return;

  const message = error instanceof Error ? error.message : String(error);
  root.innerHTML = `
    <div class="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-center font-sans text-destructive">
      <h1 class="mb-2 text-xl font-semibold">Command Center Bootstrap Failure</h1>
      <p class="mb-4 max-w-md text-sm leading-relaxed text-muted-foreground">
        Failed to load runtime configuration from <code>/config.json</code>. Ensure the configuration file exists and is accessible.
      </p>
      <pre class="max-w-xl overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs text-destructive">${escapeHtml(message)}</pre>
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

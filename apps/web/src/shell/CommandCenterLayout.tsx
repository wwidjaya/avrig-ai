import React, { useRef, useState } from "react";
import {
  Building2,
  Users,
  Kanban,
  Database,
  Cpu,
  LogOut,
  MessageSquareText,
} from "lucide-react";
import { useAuth } from "react-oidc-context";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  Button,
} from "@avrig/ui";
import { useApi } from "../shared/api/ApiContext";
import { SystemInfoDialog } from "../shared/components/SystemInfoDialog";
import { ThemeSelector } from "../shared/components/ThemeSelector";
import { LanguageSelector } from "../shared/components/LanguageSelector";

export type ActiveDomain = "office" | "deliberations" | "sdlc" | "knowledge" | "chat";

interface CommandCenterLayoutProps {
  currentDomain: ActiveDomain;
  onSelectDomain: (domain: ActiveDomain) => void;
  onOpenSearch?: () => void;
  onSignOut?: () => void;
  onReturnHome?: () => void;
  children: React.ReactNode;
}

/** The stamped approval seal. Neutral by default, accent when it marks an approved gate. */
const Seal: React.FC<{ approved?: boolean }> = ({ approved }) => (
  <span
    className={`inline-flex items-center rounded-[4px] border-[1.5px] px-1.5 py-0.5 font-mono text-[10px] leading-none tracking-normal ${
      approved ? "border-accent-text text-accent-text" : "border-border text-muted-foreground"
    }`}
  >
    AVRIG-00002
  </span>
);

export const CommandCenterLayout: React.FC<CommandCenterLayoutProps> = ({
  currentDomain,
  onSelectDomain,
  onOpenSearch: _onOpenSearch,
  onSignOut,
  onReturnHome,
  children
}) => {
  const auth = useAuth();
  const { wsStatus } = useApi();

  const [signOutConfirmOpen, setSignOutConfirmOpen] = useState(false);
  const [systemInfoOpen, setSystemInfoOpen] = useState(false);
  const versionBadgeRef = useRef<HTMLButtonElement>(null);
  const clientAppVersion = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.1.0";

  const operatorName =
    auth.user?.profile?.name || auth.user?.profile?.preferred_username || "Operator";

  const handleConfirmSignOut = async () => {
    setSignOutConfirmOpen(false);
    const idToken = auth.user?.id_token;
    try {
      if (typeof window !== "undefined") {
        localStorage.removeItem("avrig-logged-in");
        localStorage.removeItem("avrig-operator-mode");
        sessionStorage.clear();
      }
      await auth.removeUser();
      if (auth.isAuthenticated || idToken) {
        await auth.signoutRedirect({
          id_token_hint: idToken,
          post_logout_redirect_uri: typeof window !== "undefined" ? `${window.location.origin}/` : undefined,
        });
      } else {
        if (typeof window !== "undefined") {
          window.history.pushState({}, document.title, window.location.origin + "/");
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
        if (onSignOut) {
          onSignOut();
        } else if (onReturnHome) {
          onReturnHome();
        }
      }
    } catch (err) {
      console.warn("Signout error:", err);
      try {
        await auth.removeUser();
      } catch (removeErr) {
        console.warn("Error removing user:", removeErr);
      }
      if (typeof window !== "undefined") {
        window.history.pushState({}, document.title, window.location.origin + "/");
        window.dispatchEvent(new PopStateEvent("popstate"));
      }
      if (onSignOut) {
        onSignOut();
      } else if (onReturnHome) {
        onReturnHome();
      }
    }
  };

  const navItems: Array<{ id: ActiveDomain; label: string; icon: React.ComponentType<{ className?: string; strokeWidth?: number }> }> = [
    { id: "office", label: "Office and org", icon: Building2 },
    { id: "deliberations", label: "Deliberations", icon: Users },
    { id: "sdlc", label: "SDLC pipeline", icon: Kanban },
    { id: "knowledge", label: "Knowledge and trace", icon: Database },
    { id: "chat", label: "Knowledge chat", icon: MessageSquareText }
  ];

  const wsTone =
    wsStatus === "connected"
      ? "bg-positive"
      : wsStatus === "connecting" || wsStatus === "reconnecting"
        ? "bg-warning"
        : "bg-muted-foreground/60";

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background md:flex-row">
      {/* Accessible Skip Link */}
      <a
        href="#main-viewport"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:shadow-lg focus:outline-hidden"
      >
        Skip to main content
      </a>

      {/* Sidebar Navigation */}
      <aside className="flex shrink-0 flex-col border-b border-sidebar-border bg-sidebar-background text-sidebar-foreground md:h-full md:w-64 md:border-r md:border-b-0">
        {/* Org Brand Header */}
        <button
          type="button"
          onClick={onReturnHome}
          className="flex h-14 w-full items-center gap-3 border-b border-sidebar-border px-4 text-left transition-colors duration-[120ms] ease-out hover:bg-sidebar-accent/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden"
          title="Return to landing page"
          aria-label="avrig-ai command center, return to landing page"
        >
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Cpu className="size-4" strokeWidth={1.5} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold tracking-tight">avrig-ai</h1>
            <p className="truncate text-xs text-muted-foreground">Command center</p>
          </div>
        </button>

        {/* Navigation Section */}
        <nav
          className="flex gap-1 overflow-x-auto px-3 py-2 md:flex-1 md:flex-col md:gap-0.5 md:overflow-visible"
          aria-label="Product domains"
        >
          <div className="mb-2 hidden px-2 text-xs text-muted-foreground md:mt-4 md:block">
            Product domains
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentDomain === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectDomain(item.id)}
                aria-current={isActive ? "page" : undefined}
                className={`flex h-[34px] w-auto shrink-0 items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-[180ms] ease-out focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden md:w-full ${
                  isActive
                    ? "bg-sidebar-accent font-semibold text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                }`}
              >
                <Icon
                  className={`size-4 shrink-0 ${
                    isActive ? "text-sidebar-accent-foreground" : "text-muted-foreground"
                  }`}
                  strokeWidth={1.5}
                  aria-hidden="true"
                />
                <span className="whitespace-nowrap">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* System & Connection Telemetry */}
        <div className="border-t border-sidebar-border px-4 py-3 md:p-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3 md:block md:space-y-3">
            <div className="flex items-center gap-2 text-xs">
              <span className="hidden text-muted-foreground md:inline">Gateway stream</span>
              <span className="flex items-center gap-1.5">
                <span className={`size-1.5 rounded-full ${wsTone}`} aria-hidden="true" />
                <span className="font-mono text-[11px] text-text-secondary">{wsStatus}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="hidden text-muted-foreground md:inline">Version</span>
              <button
                ref={versionBadgeRef}
                type="button"
                data-testid="sidebar-version-badge"
                onClick={() => setSystemInfoOpen(true)}
                className="flex items-center rounded-md px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground transition-colors duration-[120ms] ease-out hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                title="System information and telemetry"
              >
                v{clientAppVersion}
              </button>
              <Seal approved />
            </div>

            {/* Active Operator / Logout */}
            <div className="flex items-center justify-between gap-2 md:border-t md:border-sidebar-border md:pt-3">
              <div className="flex min-w-0 items-center gap-2">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted font-mono text-[11px] font-medium">
                  {auth.user?.profile?.name?.[0] || auth.user?.profile?.preferred_username?.[0] || "O"}
                </div>
                <div className="hidden min-w-0 md:block">
                  <div className="truncate text-xs font-medium">{operatorName}</div>
                  <div className="truncate text-[11px] text-muted-foreground">
                    {auth.user?.profile?.email || "Founder"}
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="size-7 p-0 text-muted-foreground hover:text-negative"
                title="Sign out"
                aria-label="Sign out"
                onClick={() => setSignOutConfirmOpen(true)}
              >
                <LogOut className="size-4" strokeWidth={1.5} aria-hidden="true" />
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Sign Out Confirmation Dialog */}
      <AlertDialog open={signOutConfirmOpen} onOpenChange={setSignOutConfirmOpen}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm sign out</AlertDialogTitle>
            <AlertDialogDescription>
              This ends the current session and returns you to the landing page.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleConfirmSignOut}>
              Sign out
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* System Telemetry & Information Dialog */}
      <SystemInfoDialog
        open={systemInfoOpen}
        onOpenChange={setSystemInfoOpen}
        returnFocusRef={versionBadgeRef}
      />

      {/* Main Command Center Viewport */}
      <main
        id="main-viewport"
        tabIndex={-1}
        className="flex min-w-0 flex-1 flex-col overflow-hidden bg-background focus:outline-hidden"
      >
        {/* Top operational bar */}
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-card px-4 md:px-8">
          <h2 className="min-w-0 truncate text-sm font-semibold">
            {navItems.find((n) => n.id === currentDomain)?.label}
          </h2>

          <div className="flex shrink-0 items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <span className="hidden truncate sm:inline">{operatorName}</span>
              <Seal />
            </div>

            <div className="hidden h-4 w-px bg-border sm:block" aria-hidden="true" />

            <LanguageSelector />

            <ThemeSelector />
          </div>
        </header>

        {/* Content canvas */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
          <div className="mx-auto w-full max-w-[1440px]">{children}</div>
        </div>
      </main>
    </div>
  );
};

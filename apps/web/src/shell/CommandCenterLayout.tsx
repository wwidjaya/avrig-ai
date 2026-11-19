import React, { useState } from "react";
import {
  Building2,
  Users,
  Kanban,
  Database,
  Cpu,
  Layers,
  Activity,
  LogOut,
  Radio,
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
  Badge,
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
  const clientAppVersion = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.1.0";

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

  const navItems: Array<{ id: ActiveDomain; label: string; icon: React.ComponentType<{ className?: string }>; tag: string }> = [
    { id: "office", label: "Office & Org", icon: Building2, tag: "OG/WF" },
    { id: "deliberations", label: "Deliberation Rooms", icon: Users, tag: "MT" },
    { id: "sdlc", label: "SDLC Pipeline", icon: Kanban, tag: "RE-TE" },
    { id: "knowledge", label: "Knowledge & Trace", icon: Database, tag: "KM/TR" },
    { id: "chat", label: "Knowledge Chat", icon: MessageSquareText, tag: "KM/AI" }
  ];

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Accessible Skip Link */}
      <a
        href="#main-viewport"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg focus:outline-hidden"
      >
        Skip to main content
      </a>

      {/* Sidebar Navigation */}
      <aside className="flex w-64 flex-col border-r border-border bg-sidebar-background text-sidebar-foreground">
        {/* Org Brand Header */}
        <button
          type="button"
          onClick={onReturnHome}
          className="flex h-16 w-full items-center gap-3 border-b border-sidebar-border px-4 text-left cursor-pointer hover:bg-sidebar-accent/50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden transition-colors"
          title="Return to Landing Page"
          aria-label="avrig-ai Command Center, return to landing page"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">avrig-ai</h1>
            <p className="text-xs text-muted-foreground">Autonomous Command</p>
          </div>
        </button>

        {/* Navigation Section */}
        <nav className="flex-1 space-y-1 px-3 py-2" aria-label="Product Domains">
          <div className="px-2 pb-1 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
            Product Domains
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
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden cursor-pointer ${
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                  <span>{item.label}</span>
                </div>
                <Badge variant={isActive ? "default" : "outline"} className="text-[10px] py-0 px-1.5 h-4">
                  {item.tag}
                </Badge>
              </button>
            );
          })}
        </nav>

        {/* System & Connection Telemetry */}
        <div className="border-t border-sidebar-border p-4">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Gateway Stream</span>
            <div className="flex items-center gap-1.5">
              <Radio
                className={`h-3 w-3 ${
                  wsStatus === "connected"
                    ? "text-emerald-500 animate-pulse"
                    : wsStatus === "reconnecting"
                    ? "text-amber-500 animate-spin"
                    : "text-muted-foreground"
                }`}
              />
              <span className="capitalize font-mono text-[11px]">{wsStatus}</span>
            </div>
          </div>

          <div className="mb-3 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Version</span>
            <button
              type="button"
              data-testid="sidebar-version-badge"
              onClick={() => setSystemInfoOpen(true)}
              className="group flex items-center gap-1.5 rounded-md px-1.5 py-0.5 hover:bg-sidebar-accent/50 transition-colors cursor-pointer"
              title="System Information & Telemetry"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="font-mono text-[11px] text-muted-foreground group-hover:text-sidebar-foreground">
                v{clientAppVersion}
              </span>
            </button>
          </div>

          {/* Active Operator / Logout */}
          <div className="flex items-center justify-between pt-2 border-t border-sidebar-border">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary font-mono text-xs font-semibold">
                {auth.user?.profile?.name?.[0] || auth.user?.profile?.preferred_username?.[0] || "O"}
              </div>
              <div className="overflow-hidden text-left">
                <div className="truncate text-xs font-medium">
                  {auth.user?.profile?.name || auth.user?.profile?.preferred_username || "Operator"}
                </div>
                <div className="truncate text-[10px] text-muted-foreground">
                  {auth.user?.profile?.email || "Founder / Lead"}
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="size-7 p-0 text-muted-foreground hover:text-destructive cursor-pointer"
              title="Sign Out"
              onClick={() => setSignOutConfirmOpen(true)}
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Sign Out Confirmation Dialog */}
      <AlertDialog open={signOutConfirmOpen} onOpenChange={setSignOutConfirmOpen}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Sign Out</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to end your active command session and return to the main landing page?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleConfirmSignOut}>
              Sign Out
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* System Telemetry & Information Dialog */}
      <SystemInfoDialog open={systemInfoOpen} onOpenChange={setSystemInfoOpen} />

      {/* Main Command Center Viewport */}
      <main id="main-viewport" tabIndex={-1} className="flex flex-1 flex-col overflow-hidden bg-background focus:outline-hidden">
        {/* Top Operational Status Bar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-6">
          <div className="flex items-center gap-3">
            <Layers className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold tracking-wide">
              {navItems.find((n) => n.id === currentDomain)?.label}
            </h2>
            <span className="text-muted-foreground/40">/</span>
            <span className="text-xs text-muted-foreground font-mono">
              Autonomous Governance
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2.5 py-1 rounded-full">
              <Activity className="h-3.5 w-3.5 text-emerald-500" />
              <span>Consensus Engine: Active</span>
            </div>

            <div className="h-4 w-px bg-border/60" />

            {/* Language Selector */}
            <LanguageSelector />

            {/* 3-Way Theme Selector */}
            <ThemeSelector />
          </div>
        </header>

        {/* Content Canvas */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

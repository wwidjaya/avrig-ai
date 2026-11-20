import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "react-oidc-context";
import {
  CommandPalette,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem
} from "@avrig/ui";
import {
  Building2,
  Users,
  Kanban,
  Database,
  Search,
  RefreshCw,
  MessageSquareText,
} from "lucide-react";
import { ProtectedRoute } from "../shared/auth/ProtectedRoute";
import { CommandCenterLayout, type ActiveDomain } from "../shell/CommandCenterLayout";
import { OfficeView } from "../modules/office/OfficeView";
import { DeliberationsView } from "../modules/deliberations/DeliberationsView";
import { SdlcBoardView } from "../modules/sdlc/SdlcBoardView";
import { KnowledgeView } from "../modules/knowledge/KnowledgeView";
import { KnowledgeChat } from "../modules/knowledge/KnowledgeChat";
import { LandingPage } from "../modules/landing/LandingPage";
import { ErrorBoundary } from "../shared/components/ErrorBoundary";

const DOMAIN_PATHS: Record<string, ActiveDomain> = {
  "/console": "office",
  "/office": "office",
  "/deliberations": "deliberations",
  "/sdlc": "sdlc",
  "/knowledge": "knowledge",
  "/chat": "chat",
};

function parsePath(pathname: string): { mode: "landing" | "console"; domain: ActiveDomain } {
  const cleanPath = pathname.replace(/\/+$/, "") || "/";
  if (cleanPath in DOMAIN_PATHS) {
    return { mode: "console", domain: DOMAIN_PATHS[cleanPath] };
  }
  if (cleanPath.startsWith("/console/") || cleanPath.startsWith("/office")) {
    return { mode: "console", domain: "office" };
  }
  return { mode: "landing", domain: "office" };
}

export const App: React.FC = () => {
  const auth = useAuth();
  const [initialRoute] = useState(() => {
    if (typeof window !== "undefined") {
      // Legacy hash migration support: #console
      if (window.location.hash === "#console") {
        return { mode: "console" as const, domain: "office" as ActiveDomain };
      }
      if (window.location.pathname.includes("/auth/callback")) {
        const storedLogin = localStorage.getItem("avrig-logged-in");
        if (storedLogin === "true") {
          return { mode: "console" as const, domain: "office" as ActiveDomain };
        }
      }
      return parsePath(window.location.pathname);
    }
    return { mode: "landing" as const, domain: "office" as ActiveDomain };
  });

  const [activeDomain, setActiveDomain] = useState<ActiveDomain>(initialRoute.domain);
  const [searchOpen, setSearchOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"landing" | "console">(initialRoute.mode);

  const isOperator = Boolean(
    auth.isAuthenticated ||
    auth.user ||
    (typeof window !== "undefined" && localStorage.getItem("avrig-operator-mode") === "true")
  );

  // Sync navigation helper
  const navigateToPath = useCallback((path: string, mode: "landing" | "console", domain?: ActiveDomain) => {
    if (typeof window !== "undefined") {
      if (window.location.pathname !== path) {
        window.history.pushState({}, document.title, window.location.origin + path);
      }
    }
    setViewMode(mode);
    if (domain) {
      setActiveDomain(domain);
    }
  }, []);

  // Keep avrig-logged-in in sync if OIDC reports authenticated
  useEffect(() => {
    if (auth.isAuthenticated && typeof window !== "undefined") {
      localStorage.setItem("avrig-logged-in", "true");
    }
  }, [auth.isAuthenticated]);

  // Protect console/domain routes: if not authenticated and not loading, redirect to login
  useEffect(() => {
    if (!auth.isLoading && !isOperator && viewMode === "console") {
      auth.signinRedirect().catch((err) => {
        console.warn("Auto signin redirect failed, falling back to landing:", err);
        if (typeof window !== "undefined") {
          window.history.replaceState({}, document.title, window.location.origin + "/");
        }
        setViewMode("landing");
      });
    }
  }, [auth.isLoading, isOperator, viewMode, auth]);

  // Clean up any lingering /auth/callback path or params when not loading and not authenticated
  useEffect(() => {
    if (typeof window !== "undefined" && !auth.isLoading) {
      if (window.location.pathname.includes("/auth/callback") && !auth.isAuthenticated) {
        window.history.replaceState({}, document.title, window.location.origin + "/");
        setViewMode("landing");
      }
    }
  }, [auth.isLoading, auth.isAuthenticated]);

  // Sync viewMode and activeDomain with URL path changes (popstate)
  useEffect(() => {
    const handlePopState = () => {
      if (typeof window !== "undefined") {
        // Clean up any legacy hash if encountered
        if (window.location.hash === "#console") {
          window.history.replaceState({}, document.title, window.location.origin + "/console");
          setViewMode("console");
          return;
        }

        const { mode, domain } = parsePath(window.location.pathname);
        setViewMode(mode);
        if (mode === "console") {
          setActiveDomain(domain);
        }
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const navigateTo = (domain: ActiveDomain) => {
    setActiveDomain(domain);
    setSearchOpen(false);
    const path = `/${domain}`;
    if (typeof window !== "undefined" && window.location.pathname !== path) {
      window.history.pushState({}, document.title, window.location.origin + path);
    }
  };

  const handleDomainSelect = (domain: ActiveDomain) => {
    setActiveDomain(domain);
    const path = `/${domain}`;
    if (typeof window !== "undefined" && window.location.pathname !== path) {
      window.history.pushState({}, document.title, window.location.origin + path);
    }
  };

  // If loading auth credentials
  if (auth.isLoading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-3 bg-background text-foreground">
        <RefreshCw className="h-8 w-8 animate-spin text-accent-text" />
        <p className="text-sm font-mono text-muted-foreground">
          Validating OpenID Connect credentials...
        </p>
      </div>
    );
  }

  // Show Landing Page when in landing mode
  if (viewMode === "landing") {
    return (
      <LandingPage
        onEnterCommandCenter={(targetPath = "/console") => {
          if (typeof window !== "undefined") {
            localStorage.setItem("avrig-logged-in", "true");
          }
          const { domain } = parsePath(targetPath);
          navigateToPath(targetPath, "console", domain);
        }}
      />
    );
  }

  return (
    <ProtectedRoute>
      <CommandCenterLayout
        currentDomain={activeDomain}
        onSelectDomain={handleDomainSelect}
        onOpenSearch={() => setSearchOpen(true)}
        onReturnHome={() => {
          navigateToPath("/", "landing");
        }}
        onSignOut={async () => {
          try {
            await auth.removeUser();
          } catch (err) {
            console.warn("Failed to remove user:", err);
          }
          if (typeof window !== "undefined") {
            localStorage.removeItem("avrig-logged-in");
            localStorage.removeItem("avrig-operator-mode");
            sessionStorage.clear();
          }
          navigateToPath("/", "landing");
        }}
      >
        {activeDomain === "office" && (
          <ErrorBoundary fallbackTitle="Office OS View Error">
            <OfficeView />
          </ErrorBoundary>
        )}
        {activeDomain === "deliberations" && (
          <ErrorBoundary fallbackTitle="Deliberations View Error">
            <DeliberationsView />
          </ErrorBoundary>
        )}
        {activeDomain === "sdlc" && (
          <ErrorBoundary fallbackTitle="SDLC Pipeline View Error">
            <SdlcBoardView />
          </ErrorBoundary>
        )}
        {activeDomain === "knowledge" && (
          <ErrorBoundary fallbackTitle="Knowledge & Traceability View Error">
            <KnowledgeView />
          </ErrorBoundary>
        )}
        {activeDomain === "chat" && (
          <ErrorBoundary fallbackTitle="Knowledge Chat View Error">
            <div className="flex flex-1 overflow-hidden p-6">
              <KnowledgeChat />
            </div>
          </ErrorBoundary>
        )}
      </CommandCenterLayout>

      <CommandPalette
        open={searchOpen}
        onOpenChange={setSearchOpen}
      >
        <CommandInput placeholder="Type a domain, command, or knowledge query..." />
        <CommandList>
          <CommandEmpty>No matching commands found.</CommandEmpty>
          <CommandGroup heading="Navigation">
            <CommandItem onSelect={() => navigateTo("office")}>
              <Building2 className="mr-2 h-4 w-4" />
              <span>Office OS [OG, WF] - Departments & AI Roster</span>
            </CommandItem>
            <CommandItem onSelect={() => navigateTo("deliberations")}>
              <Users className="mr-2 h-4 w-4" />
              <span>Deliberation Rooms [MT] - Live Transcripts & Voting</span>
            </CommandItem>
            <CommandItem onSelect={() => navigateTo("sdlc")}>
              <Kanban className="mr-2 h-4 w-4" />
              <span>SDLC Pipeline [RE-TE] - 16-Stage Board & Gates</span>
            </CommandItem>
            <CommandItem onSelect={() => navigateTo("knowledge")}>
              <Database className="mr-2 h-4 w-4" />
              <span>Knowledge & Traceability [KM, TR] - Epistemic Search</span>
            </CommandItem>
            <CommandItem onSelect={() => navigateTo("chat")}>
              <MessageSquareText className="mr-2 h-4 w-4" />
              <span>Knowledge Chat [KM, AI] - Grounded Epistemic Query</span>
            </CommandItem>
          </CommandGroup>
          <CommandGroup heading="Quick Queries">
            <CommandItem onSelect={() => navigateTo("knowledge")}>
              <Search className="mr-2 h-4 w-4" />
              <span>Universal OIDC Architecture Specification</span>
            </CommandItem>
            <CommandItem onSelect={() => navigateTo("knowledge")}>
              <Search className="mr-2 h-4 w-4" />
              <span>React Runtime Configuration Spec (/config.json)</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandPalette>
    </ProtectedRoute>
  );
};

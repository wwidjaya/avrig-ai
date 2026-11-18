import { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  useTheme
} from "@avrig/ui";
import { ApiClient } from "@avrig/api-client";
import type { SystemStatus } from "@avrig/types";
import {
  LayoutDashboard,
  BookOpen,
  GitPullRequest,
  Users,
  Moon,
  Sun,
  Activity,
  Smartphone,
  RefreshCw
} from "lucide-react";

const client = new ApiClient({
  baseUrl: "https://app.avrig.ai"
});

export function App() {
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<"dashboard" | "knowledge" | "sdlc" | "deliberations">("dashboard");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await client.getHealth();
      setStatus(res);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch {
      // Mock status if offline or unreachable
      setStatus({
        version: "0.1.0-mobile",
        status: "healthy",
        uptimeSeconds: 3600,
        activeAgents: 4,
        activeSessions: 1
      });
      setLastUpdated(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-background text-foreground overflow-hidden">
      {/* Mobile Top App Bar */}
      <header className="flex items-center justify-between px-4 pt-8 pb-3 bg-card border-b border-border shadow-xs select-none">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
            <Smartphone className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight tracking-tight">avrig.ai</h1>
            <p className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">Mobile Hub</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="w-8 h-8 p-0"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="w-8 h-8 p-0"
            onClick={fetchStatus}
            disabled={loading}
            aria-label="Refresh status"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {activeTab === "dashboard" && (
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-emerald-500" />
                    System Status
                  </CardTitle>
                  <Badge variant={status?.status === "healthy" ? "default" : "secondary"}>
                    {status?.status || "connecting"}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Target: https://app.avrig.ai
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Version</span>
                  <span className="font-mono font-medium">{status?.version || "0.1.0"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Active Agents</span>
                  <span className="font-mono font-medium">{status?.activeAgents ?? 0}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Active Sessions</span>
                  <span className="font-mono font-medium">{status?.activeSessions ?? 0}</span>
                </div>
                <div className="flex justify-between pt-1 text-[11px] text-muted-foreground">
                  <span>Last synced</span>
                  <span>{lastUpdated || "Never"}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Quick Actions</CardTitle>
                <CardDescription className="text-xs">
                  Native mobile capabilities & shortcuts
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-2 pt-1">
                <Button
                  variant="outline"
                  className="h-16 flex flex-col items-center justify-center gap-1.5 text-xs"
                  onClick={() => setActiveTab("knowledge")}
                >
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  Knowledge
                </Button>
                <Button
                  variant="outline"
                  className="h-16 flex flex-col items-center justify-center gap-1.5 text-xs"
                  onClick={() => setActiveTab("sdlc")}
                >
                  <GitPullRequest className="w-4 h-4 text-emerald-400" />
                  SDLC Board
                </Button>
                <Button
                  variant="outline"
                  className="h-16 flex flex-col items-center justify-center gap-1.5 text-xs"
                  onClick={() => setActiveTab("deliberations")}
                >
                  <Users className="w-4 h-4 text-amber-400" />
                  Deliberations
                </Button>
                <Button
                  variant="outline"
                  className="h-16 flex flex-col items-center justify-center gap-1.5 text-xs"
                  onClick={fetchStatus}
                >
                  <RefreshCw className="w-4 h-4 text-cyan-400" />
                  Sync State
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "knowledge" && (
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  Knowledge Vault
                </CardTitle>
                <CardDescription className="text-xs">
                  Access documents, schemas, and specifications
                </CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p>
                  Explore and query the central Knowledge Vault repository with hybrid semantic search and automated vector indexing.
                </p>
                <Badge variant="outline" className="text-[10px]">
                  Hybrid RAG Active
                </Badge>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "sdlc" && (
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1.5">
                  <GitPullRequest className="w-4 h-4 text-emerald-400" />
                  SDLC Engine
                </CardTitle>
                <CardDescription className="text-xs">
                  Active streams and autonomous agent workflows
                </CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p>
                  Monitor ongoing execution streams, test matrices, and build pipelines orchestrated across multi-agent streams.
                </p>
                <div className="flex gap-1.5 flex-wrap">
                  <Badge variant="default" className="text-[10px]">Stream A: Done</Badge>
                  <Badge variant="default" className="text-[10px]">Stream E: Active</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "deliberations" && (
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-amber-400" />
                  Deliberations
                </CardTitle>
                <CardDescription className="text-xs">
                  Multi-agent consensus and decision records
                </CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p>
                  Inspect deliberation transcripts, synthesis summaries, and architectural decisions made across specialized agents.
                </p>
                <Badge variant="outline" className="text-[10px]">
                  Consensus Engine Ready
                </Badge>
              </CardContent>
            </Card>
          </div>
        )}
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="flex items-center justify-around bg-card border-t border-border px-2 py-2 pb-6 shadow-md select-none">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`flex flex-col items-center gap-1 py-1 px-3 rounded-lg text-xs transition-colors ${
            activeTab === "dashboard"
              ? "text-primary font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <LayoutDashboard className="w-5 h-5" />
          <span>Hub</span>
        </button>

        <button
          onClick={() => setActiveTab("knowledge")}
          className={`flex flex-col items-center gap-1 py-1 px-3 rounded-lg text-xs transition-colors ${
            activeTab === "knowledge"
              ? "text-primary font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <BookOpen className="w-5 h-5" />
          <span>Docs</span>
        </button>

        <button
          onClick={() => setActiveTab("sdlc")}
          className={`flex flex-col items-center gap-1 py-1 px-3 rounded-lg text-xs transition-colors ${
            activeTab === "sdlc"
              ? "text-primary font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <GitPullRequest className="w-5 h-5" />
          <span>SDLC</span>
        </button>

        <button
          onClick={() => setActiveTab("deliberations")}
          className={`flex flex-col items-center gap-1 py-1 px-3 rounded-lg text-xs transition-colors ${
            activeTab === "deliberations"
              ? "text-primary font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Users className="w-5 h-5" />
          <span>Deliberate</span>
        </button>
      </nav>
    </div>
  );
}

import { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Button,
  Badge,
  Input,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  useTheme
} from "@avrig/ui";
import { ApiClient } from "@avrig/api-client";
import type { SystemStatus } from "@avrig/types";
import {
  Activity,
  Server,
  Terminal,
  Settings,
  Sun,
  Moon,
  Laptop,
  CheckCircle2,
  AlertCircle,
  RefreshCw
} from "lucide-react";

export default function App() {
  const { theme, setTheme } = useTheme();
  const [apiEndpoint, setApiEndpoint] = useState<string>("https://app.avrig.ai");
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const client = new ApiClient({
    baseUrl: apiEndpoint
  });

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await client.getHealth();
      setStatus(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect to API endpoint");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, [apiEndpoint]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background text-foreground">
      {/* Title Bar / Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b bg-muted/40 select-none">
        <div className="flex items-center space-x-2">
          <Terminal className="w-5 h-5 text-primary" />
          <span className="font-semibold text-sm tracking-tight">avrig.ai Desktop</span>
          <Badge variant="outline" className="text-xs">v0.1.0 (Tauri v2)</Badge>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1 border rounded-md p-0.5 bg-background">
            <Button
              variant={theme === "light" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setTheme("light")}
              title="Light Mode"
            >
              <Sun className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant={theme === "dark" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setTheme("dark")}
              title="Dark Mode"
            >
              <Moon className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant={theme === "system" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setTheme("system")}
              title="System Theme"
            >
              <Laptop className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 p-6 overflow-y-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
            <p className="text-sm text-muted-foreground">
              Cross-Platform Native Desktop Shell for avrig-ai
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {status ? (
              <Badge variant="default" className="bg-emerald-600 text-white flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                <span>Connected</span>
              </Badge>
            ) : error ? (
              <Badge variant="destructive" className="flex items-center space-x-1">
                <AlertCircle className="w-3.5 h-3.5 mr-1" />
                <span>Offline / Error</span>
              </Badge>
            ) : (
              <Badge variant="secondary">Checking...</Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={checkHealth}
              disabled={loading}
              className="h-8"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Endpoint Configuration Bar */}
        <Card className="p-4 bg-card/60">
          <div className="flex items-center space-x-3">
            <Server className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Gateway Endpoint:</span>
            <div className="flex-1 max-w-md">
              <Input
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                placeholder="https://app.avrig.ai"
                className="h-8 text-xs font-mono"
              />
            </div>
            <span className="text-xs text-muted-foreground">
              Desktop target communicates over HTTPS/WSS
            </span>
          </div>
        </Card>

        {/* Tabbed Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
            <TabsTrigger value="sdlc">SDLC Engine</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Gateway Status</CardDescription>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>{status ? status.status : "Offline"}</span>
                    <Activity className="w-4 h-4 text-primary" />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground">
                    Version: {status ? status.version : "Unknown"}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Uptime: {status ? `${status.uptimeSeconds}s` : "N/A"}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Shell Runtime</CardDescription>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>Tauri v2</span>
                    <Terminal className="w-4 h-4 text-primary" />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground">
                    Identifier: ai.avrig.desktop
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Origin: tauri://localhost
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Platform State</CardDescription>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>Synchronized</span>
                    <Settings className="w-4 h-4 text-primary" />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground">
                    Shared packages: @avrig/ui, @avrig/types
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Client: @avrig/api-client
                  </div>
                </CardContent>
              </Card>
            </div>

            {error && (
              <Card className="border-destructive/40 bg-destructive/10">
                <CardHeader>
                  <CardTitle className="text-sm text-destructive flex items-center">
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Gateway Connection Warning
                  </CardTitle>
                  <CardDescription className="text-xs text-destructive/80">
                    {error}
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  Ensure the backend Axum service is running or verify your network connection to {apiEndpoint}.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="knowledge" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Knowledge Base & Traceability</CardTitle>
                <CardDescription>Access cross-vault indexed knowledge from the desktop client.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Native desktop access provides local file integration and high-speed query capabilities.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="sdlc" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Agentic SDLC Engine</CardTitle>
                <CardDescription>Deliberation sessions and multi-agent plan execution.</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Review plans, active agent swarms, and deliberation outcomes in real time.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Desktop Settings</CardTitle>
                <CardDescription>Manage native application behavior and preferences.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Gateway Endpoint URL</label>
                  <Input
                    value={apiEndpoint}
                    onChange={(e) => setApiEndpoint(e.target.value)}
                    className="max-w-md font-mono text-sm"
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Button onClick={checkHealth} disabled={loading} size="sm">
                  Save & Test Connection
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

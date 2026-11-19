import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Button,
  Badge
} from "@avrig/ui";
import { Check, Copy, RefreshCw, Server, Laptop, AlertCircle, ShieldCheck } from "lucide-react";
import { useApi } from "../api/ApiContext";
import type { VersionInfo } from "../types/version";

interface SystemInfoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const SystemInfoDialog: React.FC<SystemInfoDialogProps> = ({ open, onOpenChange }) => {
  const { api } = useApi();
  const [backendVersion, setBackendVersion] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedSha, setCopiedSha] = useState(false);

  const clientVersion = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.1.0";

  const fetchVersion = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.request<VersionInfo>("/api/v1/version");
      setBackendVersion(data);
    } catch (err) {
      console.error("Failed to fetch backend version info:", err);
      setError(err instanceof Error ? err.message : "Failed to connect to backend version service");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchVersion();
    }
  }, [open]);

  const copyToClipboard = (text: string) => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedSha(true);
      setTimeout(() => setCopiedSha(false), 2000);
    }
  };

  const isVersionSynced = backendVersion ? backendVersion.semver === clientVersion : true;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-base font-semibold">
              <ShieldCheck className="h-5 w-5 text-primary" />
              System Telemetry & Architecture
            </DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
              onClick={fetchVersion}
              disabled={loading}
              title="Refresh version details"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Authoritative build, runtime deployment, and client synchronization details.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2 text-xs">
          {/* Version Parity Comparison */}
          <div className="rounded-lg border border-border bg-card p-3 flex flex-col gap-2">
            <div className="flex items-center justify-between font-medium">
              <div className="flex items-center gap-2">
                <Laptop className="h-4 w-4 text-muted-foreground" />
                <span>Client Shell</span>
              </div>
              <Badge variant="outline" className="font-mono text-[11px]">
                v{clientVersion}
              </Badge>
            </div>

            <div className="flex items-center justify-between font-medium">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                <span>Backend Gateway</span>
              </div>
              {loading ? (
                <span className="text-muted-foreground font-mono">Checking...</span>
              ) : backendVersion ? (
                <div className="flex items-center gap-1.5">
                  <Badge variant="default" className="font-mono text-[11px]">
                    v{backendVersion.semver}
                  </Badge>
                  {backendVersion.dirty && (
                    <Badge variant="outline" className="text-amber-500 border-amber-500/30 text-[10px]">
                      dirty
                    </Badge>
                  )}
                </div>
              ) : (
                <span className="text-muted-foreground font-mono">Offline / Unavailable</span>
              )}
            </div>

            {backendVersion && !isVersionSynced && (
              <div className="flex items-center gap-2 rounded-md bg-amber-500/10 p-2 text-amber-500">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span className="text-[11px] leading-tight">
                  Client version (v{clientVersion}) differs from backend (v{backendVersion.semver}). A browser refresh or rebuild may be required.
                </span>
              </div>
            )}
          </div>

          {/* Backend Detailed Metadata */}
          {error ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-destructive text-[11px]">
              {error}
            </div>
          ) : backendVersion ? (
            <div className="rounded-lg border border-border bg-card p-3 flex flex-col gap-2 font-mono">
              <div className="flex items-center justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Git Commit:</span>
                <div className="flex items-center gap-1.5">
                  <span>{backendVersion.commit_short_sha}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 hover:bg-muted cursor-pointer"
                    onClick={() => copyToClipboard(backendVersion.commit_sha)}
                    title={`Copy full SHA: ${backendVersion.commit_sha}`}
                  >
                    {copiedSha ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3 text-muted-foreground" />}
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-border/50">
                <span className="text-muted-foreground">Build Timestamp:</span>
                <span className="text-foreground">{backendVersion.build_timestamp}</span>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-muted-foreground">Target Architecture:</span>
                <span className="text-foreground">{backendVersion.target_triple}</span>
              </div>
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

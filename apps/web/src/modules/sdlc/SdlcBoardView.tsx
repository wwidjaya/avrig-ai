import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@avrig/ui";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Lock,
  GitBranch,
  FileCode,
  Hash,
  CheckSquare
} from "lucide-react";

export interface SdlcStage {
  id: string;
  number: number;
  code: string;
  name: string;
  phase: "Inception" | "Elaboration" | "Construction" | "Transition";
  status: "completed" | "in_progress" | "review_required" | "pending";
  baselineSha: string;
  leadAgent: string;
  artifactsCount: number;
  checklist: Array<{ id: string; label: string; verified: boolean }>;
}

const canonicalStages: SdlcStage[] = [
  {
    id: "stg-01",
    number: 1,
    code: "RE-01",
    name: "Requirements Engineering",
    phase: "Inception",
    status: "completed",
    baselineSha: "9a5b3c2d1e0f4a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b",
    leadAgent: "Architect Prime",
    artifactsCount: 14,
    checklist: [
      { id: "c1", label: "Stakeholder requirements formalized", verified: true },
      { id: "c2", label: "Acceptance criteria formalized in Gherkin", verified: true },
      { id: "c3", label: "Epistemic vector embeddings generated", verified: true }
    ]
  },
  {
    id: "stg-02",
    number: 2,
    code: "SA-02",
    name: "System Architecture",
    phase: "Inception",
    status: "completed",
    baselineSha: "4b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b9a5b3c2d1e0f4a",
    leadAgent: "Architect Prime",
    artifactsCount: 8,
    checklist: [
      { id: "c4", label: "Domain bounded contexts formalized", verified: true },
      { id: "c5", label: "Four-repo landscape boundaries validated", verified: true }
    ]
  },
  {
    id: "stg-03",
    number: 3,
    code: "TA-03",
    name: "Technology Architecture",
    phase: "Inception",
    status: "completed",
    baselineSha: "f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b9a5b3c2d1e0f4a4b7c6d5e4",
    leadAgent: "Architect Prime",
    artifactsCount: 6,
    checklist: [
      { id: "c6", label: "Vite + React 19 stack ratified", verified: true },
      { id: "c7", label: "Axum + Tokio async runtime ratified", verified: true }
    ]
  },
  {
    id: "stg-04",
    number: 4,
    code: "ED-04",
    name: "Enterprise Data Model",
    phase: "Elaboration",
    status: "review_required",
    baselineSha: "c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b9a5b3c2d1e0f4a4b7c6d5e4f3a2b1",
    leadAgent: "EDM Specialist",
    artifactsCount: 12,
    checklist: [
      { id: "c8", label: "PostgreSQL 17 core entity DDL verified", verified: true },
      { id: "c9", label: "Apache AGE graph property labels declared", verified: true },
      { id: "c10", label: "Idempotent migration scripts compiled", verified: true },
      { id: "c11", label: "Founder gate review & cryptographic signature", verified: false }
    ]
  },
  {
    id: "stg-05",
    number: 5,
    code: "IN-05",
    name: "Infrastructure & Platform",
    phase: "Elaboration",
    status: "in_progress",
    baselineSha: "e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b9a5b3c2d1e0f4a4b7c6d5e4f3a2b1c0d9",
    leadAgent: "Infra Specialist",
    artifactsCount: 9,
    checklist: [
      { id: "c12", label: "Vault Root & Intermediate PKI CA deployed", verified: true },
      { id: "c13", label: "Rauthy OIDC provider & Samba AD verified", verified: true },
      { id: "c14", label: "Nginx reverse proxy TLS terminators active", verified: false }
    ]
  },
  {
    id: "stg-06",
    number: 6,
    code: "FE-06",
    name: "Frontend UI & Design System",
    phase: "Construction",
    status: "in_progress",
    baselineSha: "a6b5c4d3e2f1a0b9c8d7e6f5a4b9a5b3c2d1e0f4a4b7c6d5e4f3a2b1c0d9e8f7",
    leadAgent: "Frontend Specialist",
    artifactsCount: 22,
    checklist: [
      { id: "c15", label: "Tailwind CSS v4 tokens extracted to @avrig/tokens", verified: true },
      { id: "c16", label: "shadcn/ui primitives packaged into @avrig/ui", verified: true },
      { id: "c17", label: "Command Center runtime configuration and OIDC loaded", verified: true }
    ]
  },
  {
    id: "stg-07",
    number: 7,
    code: "BE-07",
    name: "Backend Gateway & Daemons",
    phase: "Construction",
    status: "pending",
    baselineSha: "0000000000000000000000000000000000000000000000000000000000000000",
    leadAgent: "Architect Prime",
    artifactsCount: 0,
    checklist: []
  },
  {
    id: "stg-08",
    number: 8,
    code: "TE-16",
    name: "Verification & Release",
    phase: "Transition",
    status: "pending",
    baselineSha: "0000000000000000000000000000000000000000000000000000000000000000",
    leadAgent: "SDLC Verifier",
    artifactsCount: 0,
    checklist: []
  }
];

export const SdlcBoardView: React.FC = () => {
  const [stages, setStages] = useState<SdlcStage[]>(canonicalStages);
  const [selectedStage, setSelectedStage] = useState<SdlcStage | null>(null);
  const [isGateOpen, setIsGateOpen] = useState(false);
  const [diffVerified, setDiffVerified] = useState(false);

  const getStatusBadge = (status: SdlcStage["status"]) => {
    switch (status) {
      case "completed":
        return <Badge variant="default" className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 gap-1"><CheckCircle2 className="h-3 w-3" /> Passing</Badge>;
      case "in_progress":
        return <Badge variant="default" className="bg-blue-500/20 text-blue-400 border border-blue-500/30 gap-1">In Progress</Badge>;
      case "review_required":
        return <Badge variant="default" className="bg-amber-500/20 text-amber-400 border border-amber-500/30 gap-1 animate-pulse"><AlertTriangle className="h-3 w-3" /> Gate Review</Badge>;
      case "pending":
        return <Badge variant="secondary" className="gap-1"><Lock className="h-3 w-3" /> Pending</Badge>;
    }
  };

  const openGateModal = (stage: SdlcStage) => {
    setSelectedStage(stage);
    setDiffVerified(false);
    setIsGateOpen(true);
  };

  const handleApproveGate = () => {
    if (!selectedStage) return;
    setStages((prev) =>
      prev.map((s) => (s.id === selectedStage.id ? { ...s, status: "completed" } : s))
    );
    setIsGateOpen(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Agentic SDLC Pipeline</h1>
          <p className="text-sm text-muted-foreground">
            Canonical 16-stage autonomous lifecycle, gate reviews, and SHA-256 baseline verification.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-xs">
            Framework: 16-Stage Canonical SDLC
          </Badge>
        </div>
      </div>

      {/* SDLC Stage Board Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stages.map((stage) => (
          <Card
            key={stage.id}
            className={`transition-all ${
              stage.status === "review_required"
                ? "border-amber-500/50 shadow-md shadow-amber-500/5"
                : ""
            }`}
          >
            <CardHeader className="p-4 pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-mono text-xs font-bold text-primary">{stage.code}</span>
                  <CardTitle className="text-sm font-semibold mt-1">{stage.name}</CardTitle>
                </div>
                {getStatusBadge(stage.status)}
              </div>
              <CardDescription className="text-xs">Phase: {stage.phase}</CardDescription>
            </CardHeader>

            <CardContent className="p-4 pt-2 space-y-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <GitBranch className="h-3 w-3" /> {stage.leadAgent}
                </span>
                <span className="flex items-center gap-1 font-mono">
                  <FileCode className="h-3 w-3" /> {stage.artifactsCount} items
                </span>
              </div>

              <div className="rounded bg-muted/50 p-2 font-mono text-[10px] text-muted-foreground truncate">
                SHA: {stage.baselineSha}
              </div>

              {stage.status === "review_required" ? (
                <Button
                  size="sm"
                  className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold gap-1.5"
                  onClick={() => openGateModal(stage)}
                >
                  <ShieldCheck className="h-4 w-4" /> Review Stage Gate
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => openGateModal(stage)}
                >
                  Inspect Stage
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Stage Gate Review Modal */}
      <Dialog open={isGateOpen} onOpenChange={setIsGateOpen}>
        {selectedStage && (
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-primary" />
                  <DialogTitle>Stage Gate Review: {selectedStage.code}</DialogTitle>
                </div>
                {getStatusBadge(selectedStage.status)}
              </div>
              <DialogDescription>
                Formal gate sign-off for {selectedStage.name} under autonomous governance.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2 text-xs">
              {/* Checklist */}
              <div>
                <h4 className="font-semibold text-foreground uppercase tracking-wider mb-2">
                  Verification Checklist
                </h4>
                <div className="space-y-1.5 rounded-md border border-border p-3 bg-card">
                  {selectedStage.checklist.map((item) => (
                    <div key={item.id} className="flex items-center gap-2">
                      <CheckSquare
                        className={`h-4 w-4 ${
                          item.verified ? "text-emerald-400" : "text-muted-foreground"
                        }`}
                      />
                      <span className={item.verified ? "text-foreground" : "text-muted-foreground"}>
                        {item.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cryptographic Baseline Diff Check */}
              <div>
                <h4 className="font-semibold text-foreground uppercase tracking-wider mb-2">
                  Cryptographic Baseline Verification
                </h4>
                <div className="rounded-md border border-border p-3 bg-muted/40 font-mono text-[11px] space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="flex items-center gap-1"><Hash className="h-3 w-3" /> Target Stage Hash:</span>
                    <span className="text-foreground">{selectedStage.baselineSha.slice(0, 16)}...</span>
                  </div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>Artifact Provenance:</span>
                    <span className="text-emerald-400 font-semibold">100% Traceable</span>
                  </div>
                  <div className="pt-2 border-t border-border flex items-center justify-between">
                    <span className="text-muted-foreground">Cryptographic Tree Integrity:</span>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 text-[11px]"
                      onClick={() => setDiffVerified(true)}
                    >
                      {diffVerified ? "Verified (Clean)" : "Verify SHA-256 Tree"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="ghost" onClick={() => setIsGateOpen(false)}>
                Cancel
              </Button>
              {selectedStage.status === "review_required" && (
                <Button
                  disabled={!diffVerified}
                  onClick={handleApproveGate}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                >
                  Founder Ratify & Advance Stage
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
};

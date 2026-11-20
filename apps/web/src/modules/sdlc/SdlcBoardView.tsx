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

const STATUS_META: Record<
  SdlcStage["status"],
  { label: string; variant: "default" | "secondary" | "success" | "warning" }
> = {
  completed: { label: "Passing", variant: "success" },
  in_progress: { label: "In progress", variant: "default" },
  review_required: { label: "Gate review", variant: "warning" },
  pending: { label: "Pending", variant: "secondary" }
};

export const SdlcBoardView: React.FC = () => {
  const [stages, setStages] = useState<SdlcStage[]>(canonicalStages);
  const [selectedStage, setSelectedStage] = useState<SdlcStage | null>(null);
  const [isGateOpen, setIsGateOpen] = useState(false);
  const [diffVerified, setDiffVerified] = useState(false);

  const getStatusBadge = (status: SdlcStage["status"]) => {
    const meta = STATUS_META[status];
    return <Badge variant={meta.variant}>{meta.label}</Badge>;
  };

  // The approved gate is the furthest-along completed stage. The seal marks that one
  // gate, so the board carries a single seal rather than one per completed stage.
  const approvedGate = stages.reduce<SdlcStage | null>(
    (furthest, stage) =>
      stage.status === "completed" && (!furthest || stage.number > furthest.number)
        ? stage
        : furthest,
    null
  );

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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight">Agentic SDLC pipeline</h1>
          <p className="text-sm text-text-secondary">
            The canonical 16-stage lifecycle, its gate reviews, and the baseline hash behind each stage.
          </p>
        </div>
        <span className="font-mono text-xs text-muted-foreground">16-stage canonical SDLC</span>
      </div>

      {/* SDLC Stage Board Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {stages.map((stage) => (
          <Card
            key={stage.id}
            className={`transition-colors duration-[180ms] ease-out ${
              stage.status === "review_required" ? "border-warning/50" : ""
            }`}
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <span className="font-mono text-[11px] font-medium tracking-normal text-accent-text">
                    {stage.code}
                  </span>
                  <CardTitle className="mt-1 text-sm font-semibold">{stage.name}</CardTitle>
                </div>
                {approvedGate?.id === stage.id ? (
                  <span className="inline-flex shrink-0 items-center rounded-[4px] border-[1.5px] border-accent-text px-1.5 py-0.5 font-mono text-[10px] leading-none tracking-normal text-accent-text">
                    {stage.code} approved
                  </span>
                ) : (
                  getStatusBadge(stage.status)
                )}
              </div>
              <CardDescription className="text-xs">{stage.phase}</CardDescription>
            </CardHeader>

            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                <span className="flex min-w-0 items-center gap-1.5">
                  <GitBranch className="size-3.5 shrink-0" strokeWidth={1.5} aria-hidden="true" />
                  <span className="truncate">{stage.leadAgent}</span>
                </span>
                <span className="flex shrink-0 items-center gap-1.5 font-mono tabular-nums">
                  <FileCode className="size-3.5" strokeWidth={1.5} aria-hidden="true" />
                  {stage.artifactsCount}
                </span>
              </div>

              <div className="truncate rounded border border-border/70 bg-muted/40 px-2 py-1.5 font-mono text-[11px] text-muted-foreground">
                {stage.baselineSha}
              </div>

              {stage.status === "review_required" ? (
                <Button
                  size="sm"
                  className="w-full gap-1.5 font-medium"
                  onClick={() => openGateModal(stage)}
                >
                  <ShieldCheck className="size-4" strokeWidth={1.5} aria-hidden="true" />
                  Review stage gate
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => openGateModal(stage)}
                >
                  Inspect stage
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
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                  <DialogTitle>Stage gate: {selectedStage.code}</DialogTitle>
                </div>
                {getStatusBadge(selectedStage.status)}
              </div>
              <DialogDescription>
                Sign-off record for {selectedStage.name}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2 text-xs">
              {/* Checklist */}
              <div>
                <h4 className="mb-2 text-xs font-medium text-text-secondary">Verification checklist</h4>
                <div className="space-y-1.5 rounded border border-border bg-muted/30 p-3">
                  {selectedStage.checklist.map((item) => (
                    <div key={item.id} className="flex items-center gap-2">
                      <CheckSquare
                        className={`size-4 shrink-0 ${
                          item.verified ? "text-positive" : "text-muted-foreground"
                        }`}
                        strokeWidth={1.5}
                        aria-hidden="true"
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
                <h4 className="mb-2 text-xs font-medium text-text-secondary">
                  Baseline verification
                </h4>
                <div className="space-y-2 rounded border border-border bg-muted/30 p-3 font-mono text-[11px]">
                  <div className="flex items-center justify-between gap-3 text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <Hash className="size-3.5" strokeWidth={1.5} aria-hidden="true" />
                      Stage hash
                    </span>
                    <span className="truncate text-foreground">{selectedStage.baselineSha.slice(0, 16)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3 text-muted-foreground">
                    <span>Recorded artifacts</span>
                    <span className="text-foreground tabular-nums">{selectedStage.artifactsCount}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3 border-t border-border pt-2">
                    <span className="text-muted-foreground">Tree integrity</span>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 text-[11px]"
                      onClick={() => setDiffVerified(true)}
                    >
                      {diffVerified ? "Verified clean" : "Verify tree hash"}
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
                <Button disabled={!diffVerified} onClick={handleApproveGate}>
                  Ratify and advance stage
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
};

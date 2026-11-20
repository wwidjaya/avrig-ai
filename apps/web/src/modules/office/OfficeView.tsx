import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
  Button,
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription
} from "@avrig/ui";
import { Bot } from "lucide-react";

export interface AIEmployee {
  id: string;
  name: string;
  handle: string;
  role: string;
  department: string;
  status: "idle" | "thinking" | "working" | "deliberating";
  currentTask?: string;
  model: string;
  capabilities: string[];
}

const mockEmployees: AIEmployee[] = [
  {
    id: "emp-001",
    name: "Architect Prime",
    handle: "@arch-prime",
    role: "Chief Systems Architect",
    department: "Executive Office",
    status: "deliberating",
    currentTask: "Consensus deliberation on Distributed Transaction Baseline (ADR-042)",
    model: "claude-3-7-sonnet",
    capabilities: ["System Architecture", "ADR Formulation", "Security Threat Modeling"]
  },
  {
    id: "emp-002",
    name: "EDM Specialist",
    handle: "@edm-agent",
    role: "Principal Data Modeler",
    department: "Core Engineering",
    status: "working",
    currentTask: "Deploying Apache AGE entity tables for epistemic knowledge graph",
    model: "gemini-2.5-pro",
    capabilities: ["PostgreSQL Schema", "Apache AGE Graph", "Vector Index Optimization"]
  },
  {
    id: "emp-003",
    name: "Frontend Specialist",
    handle: "@fe-agent",
    role: "Staff UI Engineer",
    department: "User Experience",
    status: "working",
    currentTask: "Synthesizing Command Center domain modules with @avrig/ui primitives",
    model: "gemini-3.8-flash-low",
    capabilities: ["React 19", "Tailwind CSS v4", "Design Systems", "Universal OIDC"]
  },
  {
    id: "emp-004",
    name: "Infra Specialist",
    handle: "@infra-agent",
    role: "DevOps & SRE Lead",
    department: "Infrastructure & Platform",
    status: "idle",
    currentTask: "Standing by for PKI certificate rotation and Nginx reverse proxy routing",
    model: "claude-3-7-sonnet",
    capabilities: ["WSL Ubuntu", "Vault / PKI", "Samba AD", "Rauthy OIDC", "Nginx Proxy"]
  },
  {
    id: "emp-005",
    name: "SDLC Verifier",
    handle: "@verifier-bot",
    role: "Autonomous SDLC Inspector",
    department: "Quality & Governance",
    status: "thinking",
    currentTask: "Validating SHA-256 cryptographic hashes for Stage 04 Architecture Baseline",
    model: "gpt-4o",
    capabilities: ["Gate Checklists", "Cryptographic Hashing", "Lineage Traceability"]
  }
];

const STATUS_META: Record<
  AIEmployee["status"],
  { label: string; variant: "default" | "secondary" | "success" | "warning" }
> = {
  idle: { label: "Idle", variant: "secondary" },
  thinking: { label: "Thinking", variant: "warning" },
  working: { label: "Working", variant: "success" },
  deliberating: { label: "Deliberating", variant: "default" }
};

export const OfficeView: React.FC = () => {
  const [selectedEmployee, setSelectedEmployee] = useState<AIEmployee | null>(null);

  const getStatusBadge = (status: AIEmployee["status"]) => {
    const meta = STATUS_META[status];
    return <Badge variant={meta.variant}>{meta.label}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Top Domain Context */}
      <div className="flex flex-col gap-1">
        <h1 className="text-[28px] leading-tight font-semibold tracking-tight">Office operating system</h1>
        <p className="text-sm text-text-secondary">
          Department reporting lines and the current operational state of every AI employee.
        </p>
      </div>

      {/* Department Organization Topology */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { name: "Executive Office", lead: "Architect Prime", count: "1 autonomous agent" },
          { name: "Core Engineering", lead: "EDM Specialist", count: "2 autonomous agents" },
          { name: "User Experience", lead: "Frontend Specialist", count: "1 autonomous agent" },
          { name: "Infrastructure", lead: "Infra Specialist", count: "1 autonomous agent" }
        ].map((dept, idx) => (
          <Card key={idx}>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">{dept.name}</CardTitle>
              <CardDescription className="text-xs">Lead: {dept.lead}</CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground tabular-nums">
              {dept.count}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* AI Employee Roster */}
      <div className="space-y-4">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-sm font-medium text-text-secondary">AI employee roster</h2>
          <span className="font-mono text-xs text-muted-foreground tabular-nums">
            {mockEmployees.length} registered
          </span>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {mockEmployees.map((emp) => (
            <Card
              key={emp.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedEmployee(emp)}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelectedEmployee(emp);
                }
              }}
              aria-label={`View details for ${emp.name}, ${emp.role}`}
              className="cursor-pointer transition-colors duration-[120ms] ease-out hover:border-text-secondary/40 hover:bg-muted/30 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <Bot className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                    <div className="min-w-0">
                      <CardTitle className="truncate text-sm font-semibold">{emp.name}</CardTitle>
                      <CardDescription className="truncate font-mono text-xs">{emp.handle}</CardDescription>
                    </div>
                  </div>
                  {getStatusBadge(emp.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-xs font-medium text-text-secondary">{emp.role}</div>
                {emp.currentTask && (
                  <div className="rounded border border-border/70 bg-muted/40 p-3 text-xs text-text-secondary line-clamp-2">
                    <span className="font-medium text-foreground">Task: </span>
                    {emp.currentTask}
                  </div>
                )}
                <div className="flex items-center justify-between gap-2 border-t border-border pt-3 text-[11px] text-muted-foreground">
                  <span className="truncate">{emp.department}</span>
                  <span className="shrink-0 font-mono">{emp.model}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* AI Employee Detail Sheet */}
      <Sheet open={!!selectedEmployee} onOpenChange={(open: boolean) => !open && setSelectedEmployee(null)}>
        {selectedEmployee && (
          <SheetContent className="w-full sm:max-w-md">
            <SheetHeader>
              <div className="flex items-center gap-3">
                <Bot className="size-5 shrink-0 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                <div className="min-w-0">
                  <SheetTitle>{selectedEmployee.name}</SheetTitle>
                  <SheetDescription className="font-mono text-xs">{selectedEmployee.handle}</SheetDescription>
                </div>
              </div>
            </SheetHeader>

            <div className="mt-6 space-y-5 text-sm">
              <div>
                <span className="block text-xs font-medium text-muted-foreground">Role and department</span>
                <div className="mt-1 font-medium">{selectedEmployee.role}</div>
                <div className="text-xs text-text-secondary">{selectedEmployee.department}</div>
              </div>

              <div>
                <span className="block text-xs font-medium text-muted-foreground">Current status</span>
                <div className="mt-1">{getStatusBadge(selectedEmployee.status)}</div>
              </div>

              <div>
                <span className="block text-xs font-medium text-muted-foreground">Active task</span>
                <div className="mt-1 rounded border border-border/70 bg-muted/40 p-3 text-xs text-foreground">
                  {selectedEmployee.currentTask || "No active task"}
                </div>
              </div>

              <div>
                <span className="block text-xs font-medium text-muted-foreground">Capabilities</span>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {selectedEmployee.capabilities.map((cap, i) => (
                    <Badge key={i} variant="outline" className="font-normal">
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <span className="block text-xs font-medium text-muted-foreground">Runtime model</span>
                <div className="mt-1 rounded border border-border bg-background p-3 font-mono text-xs">
                  {selectedEmployee.model}
                </div>
              </div>

              <div className="flex justify-end border-t border-border pt-4">
                <Button variant="outline" onClick={() => setSelectedEmployee(null)}>
                  Close profile
                </Button>
              </div>
            </div>
          </SheetContent>
        )}
      </Sheet>
    </div>
  );
};

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
import {
  Users,
  Bot,
  BrainCircuit,
  Hammer,
  Clock,
  Sparkles,
  Workflow
} from "lucide-react";

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

export const OfficeView: React.FC = () => {
  const [selectedEmployee, setSelectedEmployee] = useState<AIEmployee | null>(null);

  const getStatusBadge = (status: AIEmployee["status"]) => {
    switch (status) {
      case "idle":
        return <Badge variant="secondary" className="gap-1"><Clock className="h-3 w-3" /> Idle</Badge>;
      case "thinking":
        return <Badge variant="default" className="bg-amber-600/20 text-amber-500 border border-amber-500/30 gap-1"><BrainCircuit className="h-3 w-3 animate-pulse" /> Thinking</Badge>;
      case "working":
        return <Badge variant="default" className="bg-blue-600/20 text-blue-400 border border-blue-500/30 gap-1"><Hammer className="h-3 w-3" /> Working</Badge>;
      case "deliberating":
        return <Badge variant="default" className="bg-purple-600/20 text-purple-400 border border-purple-500/30 gap-1"><Sparkles className="h-3 w-3 animate-spin" /> Deliberating</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Domain Context */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-bold tracking-tight">Office Operating System</h1>
        <p className="text-sm text-muted-foreground">
          Autonomous organizational hierarchy, department reporting lines, and live AI employee operational statuses.
        </p>
      </div>

      {/* Department Organization Topology */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { name: "Executive Office", lead: "Architect Prime", count: "1 Autonomous Agent" },
          { name: "Core Engineering", lead: "EDM Specialist", count: "2 Autonomous Agents" },
          { name: "User Experience", lead: "Frontend Specialist", count: "1 Autonomous Agent" },
          { name: "Infrastructure", lead: "Infra Specialist", count: "1 Autonomous Agent" }
        ].map((dept, idx) => (
          <Card key={idx} className="bg-card/60 backdrop-blur-xs">
            <CardHeader className="p-4 pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">{dept.name}</CardTitle>
                <Workflow className="h-4 w-4 text-primary/70" />
              </div>
              <CardDescription className="text-xs">Lead: {dept.lead}</CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-1 text-xs text-muted-foreground">
              {dept.count}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* AI Employee Roster */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">AI Employee Roster</h2>
          </div>
          <span className="text-xs text-muted-foreground font-mono">{mockEmployees.length} registered agents</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockEmployees.map((emp) => (
            <Card
              key={emp.id}
              onClick={() => setSelectedEmployee(emp)}
              className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-md"
            >
              <CardHeader className="p-4 pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold">{emp.name}</CardTitle>
                      <CardDescription className="text-xs font-mono">{emp.handle}</CardDescription>
                    </div>
                  </div>
                  {getStatusBadge(emp.status)}
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <div className="text-xs font-medium text-foreground/90">{emp.role}</div>
                {emp.currentTask && (
                  <div className="rounded-md bg-muted/60 p-2 text-xs text-muted-foreground line-clamp-2">
                    <span className="font-semibold text-foreground/80">Active Task: </span>
                    {emp.currentTask}
                  </div>
                )}
                <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border">
                  <span>{emp.department}</span>
                  <span className="font-mono">{emp.model}</span>
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
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Bot className="h-6 w-6" />
                </div>
                <div>
                  <SheetTitle>{selectedEmployee.name}</SheetTitle>
                  <SheetDescription className="font-mono text-xs">{selectedEmployee.handle}</SheetDescription>
                </div>
              </div>
            </SheetHeader>

            <div className="mt-6 space-y-5 text-sm">
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Role & Department</label>
                <div className="mt-1 font-medium">{selectedEmployee.role}</div>
                <div className="text-xs text-muted-foreground">{selectedEmployee.department}</div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Current Status</label>
                <div className="mt-1">{getStatusBadge(selectedEmployee.status)}</div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Active Task Trace</label>
                <div className="mt-1 rounded-md bg-muted p-3 text-xs text-foreground">
                  {selectedEmployee.currentTask || "No active task execution"}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Core Capabilities</label>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {selectedEmployee.capabilities.map((cap, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Runtime Model</label>
                <div className="mt-1 font-mono text-xs bg-card p-2 rounded-md border border-border">
                  {selectedEmployee.model}
                </div>
              </div>

              <div className="pt-4 border-t border-border flex justify-end">
                <Button variant="outline" onClick={() => setSelectedEmployee(null)}>
                  Close Profile
                </Button>
              </div>
            </div>
          </SheetContent>
        )}
      </Sheet>
    </div>
  );
};

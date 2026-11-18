import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
} from "@avrig/ui";
import {
  Network,
  ArrowRight,
} from "lucide-react";

interface TraceLink {
  from: string;
  fromType: "Requirement" | "ADR" | "Entity";
  to: string;
  toType: "Component" | "Pipeline Stage" | "Test Suite";
  relationship: "implements" | "verifies" | "constrains";
}

export const KnowledgeView: React.FC = () => {
  const traceLinks: TraceLink[] = [
    {
      from: "REQ-AUTH-01 (Universal OIDC)",
      fromType: "Requirement",
      to: "FE-06 (UniversalAuthProvider)",
      toType: "Component",
      relationship: "implements"
    },
    {
      from: "ADR-042 (Distributed Baseline)",
      fromType: "ADR",
      to: "STG-04 (Enterprise Data Model)",
      toType: "Pipeline Stage",
      relationship: "constrains"
    },
    {
      from: "EDM-DOC-VEC (Document Vector Entity)",
      fromType: "Entity",
      to: "TEST-SUITE-KM (Knowledge Ingestion)",
      toType: "Test Suite",
      relationship: "verifies"
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-bold tracking-tight">Knowledge Management & Lineage Traceability</h1>
        <p className="text-sm text-muted-foreground">
          Inspect formal cryptographic graph lineage and relationships connecting architecture requirements, design decisions, EDM entities, and deployed code artifacts.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                Lineage & Traceability Graph
              </h2>
            </div>
            <Badge variant="outline" className="text-xs font-mono">Apache AGE Traversal</Badge>
          </div>

          <Card>
            <CardHeader className="p-4 pb-2 border-b border-border">
              <CardTitle className="text-sm font-semibold">Active Graph Lineage</CardTitle>
              <CardDescription className="text-xs">
                Formal cryptographic graph relationships connecting specifications to deployed components.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {traceLinks.map((link, idx) => (
                <div
                  key={idx}
                  className="flex flex-col gap-2 rounded-lg border border-border/70 bg-muted/30 p-3 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary" className="text-[10px]">
                      {link.fromType}
                    </Badge>
                    <span className="font-mono text-[11px] font-semibold text-primary uppercase">
                      [{link.relationship}]
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {link.toType}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between gap-2 text-foreground font-medium pt-1">
                    <span className="truncate">{link.from}</span>
                    <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                    <span className="truncate text-right">{link.to}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

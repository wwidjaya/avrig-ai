import React, { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
  Button
} from "@avrig/ui";
import { FileCheck2 } from "lucide-react";
import { useApi } from "../../shared/api/ApiContext";

interface TranscriptMessage {
  id: string;
  speaker: string;
  role: string;
  timestamp: string;
  content: string;
}

interface SpeakerQueueItem {
  name: string;
  role: string;
  status: "speaking" | "queued";
  timeRemaining?: string;
}

export const DeliberationsView: React.FC = () => {
  const { ws } = useApi();
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([
    {
      id: "tr-1",
      speaker: "Architect Prime",
      role: "Chief Systems Architect",
      timestamp: "10:14:02",
      content: "Reviewing ADR-042 on distributed transaction boundaries across avrig-api and avrig-lib. I recommend adopting an outbox pattern backed by PostgreSQL event logs."
    },
    {
      id: "tr-2",
      speaker: "EDM Specialist",
      role: "Principal Data Modeler",
      timestamp: "10:14:48",
      content: "Concur. The relational schema in PostgreSQL 17 can handle idempotent transaction logs while Apache AGE updates graph nodes asynchronously."
    },
    {
      id: "tr-3",
      speaker: "Frontend Specialist",
      role: "Staff UI Engineer",
      timestamp: "10:15:30",
      content: "From the client perspective, the ResilientWebSocketManager will subscribe to outbox events without blocking REST queries."
    }
  ]);

  const [votes, setVotes] = useState<{ agree: number; disagree: number; abstain: number }>({
    agree: 3,
    disagree: 0,
    abstain: 1
  });
  const [hasVoted, setHasVoted] = useState(false);

  // Subscribe to live meeting websocket transcripts
  useEffect(() => {
    const unsub = ws.subscribe<TranscriptMessage>("meeting:deliberation", (msg) => {
      setTranscripts((prev) => [...prev, msg]);
    });
    return unsub;
  }, [ws]);

  const speakers: SpeakerQueueItem[] = [
    { name: "Architect Prime", role: "Chief Systems Architect", status: "speaking", timeRemaining: "01:14" },
    { name: "EDM Specialist", role: "Principal Data Modeler", status: "queued" },
    { name: "Infra Specialist", role: "DevOps & SRE Lead", status: "queued" }
  ];

  const handleVote = (choice: "agree" | "disagree" | "abstain") => {
    if (hasVoted) return;
    setVotes((prev) => ({ ...prev, [choice]: prev[choice] + 1 }));
    setHasVoted(true);
    ws.send("meeting:deliberation:vote", { choice });
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight">Meeting deliberations</h1>
          <p className="text-sm text-text-secondary">
            Speaker turns, the live transcript, and the founder vote that closes a motion.
          </p>
        </div>
        <Badge variant="success">Room live · ADR-042</Badge>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Deliberation Transcript Stream (2 cols) */}
        <div className="lg:col-span-2">
          <Card className="flex h-[600px] flex-col">
            <CardHeader className="flex flex-row items-center justify-between gap-3 border-b border-border pb-4">
              <CardTitle className="text-sm font-semibold">Transcript</CardTitle>
              <span className="font-mono text-xs text-muted-foreground tabular-nums">
                {transcripts.length} entries
              </span>
            </CardHeader>
            <CardContent className="flex-1 space-y-4 overflow-y-auto">
              {transcripts.map((msg) => (
                <div key={msg.id} className="flex flex-col gap-1 rounded border border-border/70 bg-muted/30 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-baseline gap-2">
                      <span className="truncate text-xs font-medium text-foreground">{msg.speaker}</span>
                      <span className="truncate text-[11px] text-muted-foreground">{msg.role}</span>
                    </div>
                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                      {msg.timestamp}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-text-secondary">{msg.content}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right Sidebar: Speaker Queue & Consensus Panel */}
        <div className="space-y-6">
          {/* Speaker Queue */}
          <Card>
            <CardHeader className="border-b border-border pb-4">
              <CardTitle className="text-sm font-semibold">Speaker queue</CardTitle>
              <CardDescription className="text-xs">Ordered deliberation turns</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {speakers.map((spk, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between gap-3 rounded border p-3 ${
                    spk.status === "speaking"
                      ? "border-border bg-muted/50"
                      : "border-border/60 bg-transparent"
                  }`}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                      {idx + 1}
                    </span>
                    <div className="min-w-0">
                      <div className="truncate text-xs font-medium text-foreground">{spk.name}</div>
                      <div className="truncate text-[11px] text-muted-foreground">{spk.role}</div>
                    </div>
                  </div>
                  {spk.status === "speaking" ? (
                    <span className="flex shrink-0 items-center gap-1.5 font-mono text-[11px] text-text-secondary tabular-nums">
                      <span className="size-1.5 rounded-full bg-positive" aria-hidden="true" />
                      {spk.timeRemaining}
                    </span>
                  ) : (
                    <span className="shrink-0 text-[11px] text-muted-foreground">Queued</span>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Voting & Formal Resolution Panel */}
          <Card>
            <CardHeader className="border-b border-border pb-4">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-sm font-semibold">Consensus vote</CardTitle>
                <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                  Quorum 4 / 5
                </span>
              </div>
              <CardDescription className="text-xs">
                Motion: ratify ADR-042 distributed baseline
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded border border-border p-3">
                  <div className="text-xl font-medium text-foreground tabular-nums">{votes.agree}</div>
                  <div className="mt-1 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="size-1.5 rounded-full bg-positive" aria-hidden="true" />
                    Agree
                  </div>
                </div>
                <div className="rounded border border-border p-3">
                  <div className="text-xl font-medium text-foreground tabular-nums">{votes.disagree}</div>
                  <div className="mt-1 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="size-1.5 rounded-full bg-negative" aria-hidden="true" />
                    Disagree
                  </div>
                </div>
                <div className="rounded border border-border p-3">
                  <div className="text-xl font-medium text-foreground tabular-nums">{votes.abstain}</div>
                  <div className="mt-1 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="size-1.5 rounded-full bg-muted-foreground/60" aria-hidden="true" />
                    Abstain
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <div className="text-xs font-medium text-text-secondary">Founder vote</div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    disabled={hasVoted}
                    onClick={() => handleVote("agree")}
                  >
                    Agree
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    disabled={hasVoted}
                    onClick={() => handleVote("disagree")}
                  >
                    Disagree
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="flex-1 text-muted-foreground"
                    disabled={hasVoted}
                    onClick={() => handleVote("abstain")}
                  >
                    Abstain
                  </Button>
                </div>
              </div>

              {hasVoted && (
                <div className="flex items-center gap-2 rounded border border-border bg-muted/40 p-3 text-xs text-text-secondary">
                  <FileCheck2 className="size-4 shrink-0 text-positive" strokeWidth={1.5} aria-hidden="true" />
                  <span>Vote recorded against the motion.</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

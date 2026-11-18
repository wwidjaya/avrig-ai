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
import {
  Mic,
  MessageSquare,
  Vote,
  Clock,
  Radio,
  FileCheck2
} from "lucide-react";
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Meeting Deliberations</h1>
          <p className="text-sm text-muted-foreground">
            Synchronous consensus engine, multi-agent speaker queues, real-time speech transcription, and formal resolutions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="default" className="bg-red-500/20 text-red-400 border border-red-500/30 gap-1.5 animate-pulse">
            <Radio className="h-3 w-3" /> LIVE ROOM: ADR-042 Deliberation
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Deliberation Transcript Stream (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm font-semibold">Live Deliberation Transcript</CardTitle>
                </div>
                <span className="text-xs text-muted-foreground font-mono">Stream: wss://api.avrig.ai/ws</span>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
              {transcripts.map((msg) => (
                <div key={msg.id} className="flex flex-col gap-1 rounded-lg border border-border/60 bg-muted/30 p-3">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground">{msg.speaker}</span>
                      <span className="text-muted-foreground">({msg.role})</span>
                    </div>
                    <span className="font-mono text-[11px] text-muted-foreground">{msg.timestamp}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/90">{msg.content}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right Sidebar: Speaker Queue & Consensus Panel */}
        <div className="space-y-6">
          {/* Speaker Queue */}
          <Card>
            <CardHeader className="p-4 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Mic className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm font-semibold">Speaker Turn Queue</CardTitle>
              </div>
              <CardDescription className="text-xs">Ordered deliberation turns</CardDescription>
            </CardHeader>
            <CardContent className="p-4 space-y-3">
              {speakers.map((spk, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between p-2.5 rounded-md border text-xs ${
                    spk.status === "speaking"
                      ? "border-primary/50 bg-primary/10 text-primary-foreground font-medium"
                      : "border-border bg-card text-muted-foreground"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] font-bold">#{idx + 1}</span>
                    <div>
                      <div className="font-semibold text-foreground">{spk.name}</div>
                      <div className="text-[10px] text-muted-foreground">{spk.role}</div>
                    </div>
                  </div>
                  {spk.status === "speaking" ? (
                    <Badge variant="default" className="text-[10px] py-0 px-1.5 h-4 gap-1">
                      <Clock className="h-2.5 w-2.5 animate-spin" /> {spk.timeRemaining}
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-[10px] py-0 px-1.5 h-4">
                      Queued
                    </Badge>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Voting & Formal Resolution Panel */}
          <Card>
            <CardHeader className="p-4 pb-2 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Vote className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm font-semibold">Consensus Vote</CardTitle>
                </div>
                <Badge variant="outline" className="text-xs">Quorum: 4/5</Badge>
              </div>
              <CardDescription className="text-xs">Motion: Ratify ADR-042 Distributed Baseline</CardDescription>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-2">
                  <div className="text-lg font-bold text-emerald-400">{votes.agree}</div>
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground">Agree</div>
                </div>
                <div className="rounded-md border border-red-500/30 bg-red-500/10 p-2">
                  <div className="text-lg font-bold text-red-400">{votes.disagree}</div>
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground">Disagree</div>
                </div>
                <div className="rounded-md border border-border bg-muted/40 p-2">
                  <div className="text-lg font-bold text-muted-foreground">{votes.abstain}</div>
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground">Abstain</div>
                </div>
              </div>

              <div className="pt-2 border-t border-border flex flex-col gap-2">
                <div className="text-xs font-semibold text-muted-foreground">Cast Founder Vote:</div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
                    disabled={hasVoted}
                    onClick={() => handleVote("agree")}
                  >
                    Agree
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 text-red-400 border-red-500/30 hover:bg-red-500/20"
                    disabled={hasVoted}
                    onClick={() => handleVote("disagree")}
                  >
                    Disagree
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs text-muted-foreground"
                    disabled={hasVoted}
                    onClick={() => handleVote("abstain")}
                  >
                    Abstain
                  </Button>
                </div>
              </div>

              {hasVoted && (
                <div className="flex items-center gap-2 rounded-md bg-primary/10 p-2.5 text-xs text-primary">
                  <FileCheck2 className="h-4 w-4 shrink-0" />
                  <span>Vote registered on consensus ledger.</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

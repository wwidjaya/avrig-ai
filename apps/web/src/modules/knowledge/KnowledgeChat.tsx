import React, { useState, useRef, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Badge,
  Button,
  ScrollArea,
  Avatar,
  AvatarFallback,
} from "@avrig/ui";
import {
  Bot,
  User,
  Send,
  Sparkles,
  ChevronDown,
  ChevronUp,
  FileText,
  Trash2,
  Database,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { useApi } from "../../shared/api/ApiContext";
import type { SearchResult as SearchDocumentHit } from "@avrig/types";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  results?: SearchDocumentHit[];
  reranked?: boolean;
  isStreaming?: boolean;
}

const SUGGESTED_QUERIES = [
  "Explain React runtime config pattern",
  "Universal OIDC authentication architecture",
  "What is the EDM document vector entity?",
  "How does the consensus deliberation engine work?",
];

export const KnowledgeChat: React.FC = () => {
  const { api } = useApi();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      sender: "assistant",
      text: "Welcome to the avrig-ai Knowledge Assistant. Ask any question to query the live vector embeddings, technical architecture specs, and Obsidian Vault artifacts.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleCitation = (hitId: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [hitId]: !prev[hitId],
    }));
  };

  const handleCopy = async (messageId: string, text: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => {
        setCopiedMessageId((prev) => (prev === messageId ? null : prev));
      }, 2000);
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
    }
  };

  const handleSend = async (queryToSend?: string) => {
    const q = (queryToSend ?? inputQuery).trim();
    if (!q || isLoading) return;

    setInputQuery("");

    const userMsgId = `msg-${Date.now()}-user`;
    const assistantMsgId = `msg-${Date.now()}-assistant`;

    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: "user",
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    let streamedText = "";
    let capturedResults: SearchDocumentHit[] = [];
    let isReranked = false;
    let streamFailed = false;

    // Initialize assistant message container for streaming
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        sender: "assistant",
        text: "",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isStreaming: true,
      },
    ]);

    try {
      await api.searchDocumentsStream(
        q,
        {
          onMetadata: (meta) => {
            if (meta.reranked !== undefined) {
              isReranked = meta.reranked;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId ? { ...msg, reranked: isReranked } : msg
                )
              );
            }
          },
          onAnswerDelta: (delta) => {
            streamedText += delta;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId ? { ...msg, text: streamedText } : msg
              )
            );
          },
          onCitations: (results) => {
            capturedResults = results;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId ? { ...msg, results: capturedResults } : msg
              )
            );
          },
          onError: (errMsg) => {
            console.warn("SSE error event:", errMsg);
            streamFailed = true;
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
              )
            );
          },
        },
        { signal: abortController.signal, limit: 5 }
      );
    } catch (sseErr) {
      console.warn("SSE streaming attempt failed, falling back to JSON search:", sseErr);
      streamFailed = true;
    }

    // Fall back to non-streaming searchDocuments(q) if stream failed or produced nothing
    if (streamFailed || (!streamedText && capturedResults.length === 0)) {
      try {
        const resp = await api.searchDocuments(q, 5);
        let summaryText = "";
        if (resp.results.length === 0) {
          summaryText = `No grounded documents were found matching "${q}". Try rephrasing or checking your query against the system architecture specifications.`;
        } else {
          summaryText = `Found ${resp.count} relevant document chunk(s) across the knowledge repository. Grounded context and matching excerpts are referenced below:`;
        }

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  text: summaryText,
                  results: resp.results,
                  reranked: resp.reranked,
                  isStreaming: false,
                }
              : msg
          )
        );
      } catch (err) {
        console.error("Knowledge search fallback error:", err);
        const errMsg =
          err instanceof Error ? err.message : "Failed to query epistemic knowledge base.";

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  text: `Error connecting to knowledge search endpoint: ${errMsg}. Please verify that the API service is reachable and your authentication token is valid.`,
                  isStreaming: false,
                }
              : msg
          )
        );
      }
    } else {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
        )
      );
    }

    setIsLoading(false);
    abortControllerRef.current = null;
  };

  const clearHistory = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setMessages([
      {
        id: "welcome-reset",
        sender: "assistant",
        text: "Session cleared. What would you like to investigate in the knowledge repository?",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  return (
    <Card className="flex flex-col h-[680px] border-border bg-card shadow-md">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border py-3 px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <div>
            <CardTitle className="text-base font-semibold tracking-tight flex items-center gap-2">
              Knowledge Assistant
              <Badge variant="outline" className="text-[10px] font-mono py-0 h-4 border-primary/30 text-primary">
                v1 / sse + pgvector
              </Badge>
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Conversational hybrid query directly connected to /api/v1/knowledge/search
            </CardDescription>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={clearHistory}
            className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
            title="Clear Chat History"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Clear
          </Button>
        </div>
      </CardHeader>

      {/* Suggested Quick Queries Banner */}
      <div className="flex items-center gap-2 px-5 py-2 border-b border-border/60 bg-muted/20 overflow-x-auto text-xs">
        <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider shrink-0 flex items-center gap-1">
          <Database className="h-3 w-3" />
          Suggestions:
        </span>
        <div className="flex items-center gap-1.5">
          {SUGGESTED_QUERIES.map((sq, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(sq)}
              disabled={isLoading}
              className="text-[11px] whitespace-nowrap rounded-md bg-secondary px-2.5 py-1 text-secondary-foreground hover:bg-primary/20 hover:text-primary transition-colors cursor-pointer disabled:opacity-50"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <CardContent className="flex-1 p-0 overflow-hidden relative">
        <ScrollArea className="h-full p-5">
          <div className="space-y-5">
            {messages.map((msg) => {
              const isUser = msg.sender === "user";
              const isCopied = copiedMessageId === msg.id;

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 group/msg ${isUser ? "flex-row-reverse" : "flex-row"}`}
                >
                  <Avatar className="h-8 w-8 shrink-0 mt-0.5">
                    <AvatarFallback
                      className={`text-xs font-semibold ${
                        isUser
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-secondary-foreground border border-border"
                      }`}
                    >
                      {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-primary" />}
                    </AvatarFallback>
                  </Avatar>

                  <div className={`flex flex-col max-w-[85%] space-y-2 ${isUser ? "items-end" : "items-start"}`}>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground px-1">
                      <span>{isUser ? "Operator" : "Knowledge Assistant"}</span>
                      <span>•</span>
                      <span>{msg.timestamp}</span>
                      <button
                        onClick={() => handleCopy(msg.id, msg.text)}
                        title={isCopied ? "Copied" : isUser ? "Copy prompt" : "Copy response"}
                        className="ml-1 opacity-0 group-hover/msg:opacity-100 hover:text-foreground text-muted-foreground transition-opacity cursor-pointer p-0.5 rounded"
                      >
                        {isCopied ? (
                          <Check className="h-3 w-3 text-emerald-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>

                    <div
                      className={`rounded-xl px-4 py-3 text-sm leading-relaxed shadow-xs ${
                        isUser
                          ? "bg-primary text-primary-foreground whitespace-pre-wrap"
                          : "bg-muted/60 text-foreground border border-border/70"
                      }`}
                    >
                      {isUser ? (
                        msg.text
                      ) : msg.text ? (
                        <MarkdownRenderer
                          content={msg.text}
                          onCitationClick={(idx) => {
                            if (msg.results && msg.results[idx - 1]) {
                              toggleCitation(msg.results[idx - 1].id);
                            }
                          }}
                        />
                      ) : msg.isStreaming ? (
                        <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                          Generating grounded response...
                        </span>
                      ) : null}
                    </div>

                    {/* Grounded Document Citations */}
                    {msg.results && msg.results.length > 0 && (
                      <div className="w-full mt-2 space-y-2 pt-2 border-t border-border/50">
                        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                          <span className="flex items-center gap-1.5 font-semibold text-foreground">
                            <FileText className="h-3.5 w-3.5 text-primary" />
                            Grounded Citations ({msg.results.length})
                          </span>
                          {msg.reranked && (
                            <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/30">
                              Reranked
                            </Badge>
                          )}
                        </div>

                        <div className="space-y-2">
                          {msg.results.map((hit) => {
                            const isExpanded = Boolean(expandedCitations[hit.id]);
                            // Handle both direct percentage [0, 100] and ratio [0, 1] gracefully
                            const rawScore = typeof hit.score === "number" && !isNaN(hit.score) ? hit.score : 0;
                            const scorePercent = rawScore <= 1.0 && rawScore > 0 ? rawScore * 100 : rawScore;
                            const formattedScore = scorePercent % 1 === 0 ? scorePercent.toFixed(0) : scorePercent.toFixed(1);

                            // Badge variant / color-coding:
                            // >= 70%: default (emerald/green accent)
                            // 30% - 69.9%: secondary (amber/yellow accent)
                            // < 30%: outline (muted)
                            const badgeVariant = scorePercent >= 70 ? "default" : scorePercent >= 30 ? "secondary" : "outline";
                            const badgeClass =
                              scorePercent >= 70
                                ? "bg-emerald-600/90 text-white hover:bg-emerald-600"
                                : scorePercent >= 30
                                ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30"
                                : "text-muted-foreground";

                            return (
                              <div
                                key={hit.id}
                                className="rounded-lg border border-border bg-card/70 p-3 text-xs transition-colors hover:border-primary/40"
                              >
                                <div
                                  role="button"
                                  tabIndex={0}
                                  aria-expanded={isExpanded}
                                  className="flex items-center justify-between cursor-pointer gap-2 focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden rounded"
                                  onClick={() => toggleCitation(hit.id)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                      e.preventDefault();
                                      toggleCitation(hit.id);
                                    }
                                  }}
                                >
                                  <div className="flex items-center gap-2 truncate">
                                    <Badge variant="secondary" className="font-mono text-[10px] h-4 px-1.5">
                                      Chunk #{hit.chunk_index}
                                    </Badge>
                                    <span className="font-medium text-foreground truncate">
                                      {hit.title || `Document ${hit.document_id}`}
                                    </span>
                                  </div>

                                  <div className="flex items-center gap-2 shrink-0">
                                    <Badge
                                      variant={badgeVariant}
                                      className={`font-mono text-[10px] h-4 px-1.5 ${badgeClass}`}
                                    >
                                      {formattedScore}% match
                                    </Badge>
                                    {isExpanded ? (
                                      <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
                                    ) : (
                                      <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                                    )}
                                  </div>
                                </div>

                                {isExpanded && (
                                  <div className="mt-2.5 space-y-2 border-t border-border/60 pt-2 text-muted-foreground">
                                    <p className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-muted/40 p-2.5 rounded border border-border/50 text-foreground">
                                      {hit.content}
                                    </p>
                                    <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground pt-1">
                                      <span>ID: {hit.document_id}</span>
                                      <span className="text-primary hover:underline cursor-pointer flex items-center gap-1">
                                        View in Vault <ExternalLink className="h-2.5 w-2.5" />
                                      </span>
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Pulsing Loading Indicator */}
            {isLoading && !messages.some((m) => m.isStreaming && m.text.length > 0) && (
              <div className="flex gap-3 items-center">
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-secondary text-secondary-foreground border border-border">
                    <Bot className="h-4 w-4 text-primary animate-pulse" />
                  </AvatarFallback>
                </Avatar>
                <div className="rounded-xl bg-muted/60 px-4 py-3 border border-border/70 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-primary animate-ping" />
                  <span className="text-xs text-muted-foreground font-mono">
                    Searching vector embeddings & documents...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </CardContent>

      {/* Query Input Box */}
      <CardFooter className="border-t border-border p-3 bg-card">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex w-full items-center gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isLoading}
            aria-label="Query architectural documents, schemas, or decisions"
            placeholder="Query architectural documents, schemas, or decisions..."
            className="flex-1 rounded-md border border-input bg-background px-3.5 py-2 text-sm text-foreground shadow-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!inputQuery.trim() || isLoading}
            className="gap-1.5 px-4 h-9 cursor-pointer"
          >
            <span>Ask</span>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
};

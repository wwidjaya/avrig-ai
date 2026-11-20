import React, { useState, useRef, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Button,
  ScrollArea,
  Avatar,
  AvatarFallback,
} from "@avrig/ui";
import {
  Bot,
  User,
  Send,
  ChevronDown,
  ChevronUp,
  Trash2,
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
      text: "Ask about the architecture, the data model, or any decision recorded in the vault. Answers cite the chunks they come from.",
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
          summaryText = `No documents matched "${q}". Try different words.`;
        } else {
          summaryText = `Found ${resp.count} relevant chunks. The excerpts are cited below.`;
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
          err instanceof Error ? err.message : "the search endpoint did not answer";

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  text: `Could not reach the search endpoint: ${errMsg}. The API service or your session token may be unavailable.`,
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
        text: "Session cleared. What would you like to look up?",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  return (
    <div className="flex w-full flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-[28px] leading-tight font-semibold tracking-tight">Knowledge chat</h1>
        <p className="text-sm text-text-secondary">
          Ask the knowledge base in plain words. Every answer cites the chunks it was built from.
        </p>
      </div>

      <Card className="flex h-[680px] flex-col">
        <CardHeader className="flex flex-row items-center justify-between gap-3 border-b border-border pb-4">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              Knowledge assistant
              <span className="font-mono text-[11px] font-normal text-muted-foreground">
                sse + pgvector
              </span>
            </CardTitle>
            <CardDescription className="text-xs text-text-secondary">
              Ask the knowledge base. Answers cite the chunks they came from.
            </CardDescription>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={clearHistory}
            className="h-8 shrink-0 px-2.5 text-xs text-muted-foreground hover:text-foreground"
            title="Clear chat history"
          >
            <Trash2 className="mr-1.5 size-3.5" strokeWidth={1.5} aria-hidden="true" />
            Clear
          </Button>
        </CardHeader>

        {/* Suggested Quick Queries Banner */}
        <div className="flex items-center gap-2 overflow-x-auto border-b border-border bg-muted/30 px-6 py-2">
          <span className="shrink-0 text-xs text-muted-foreground">Try</span>
          <div className="flex items-center gap-1.5">
            {SUGGESTED_QUERIES.map((sq, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(sq)}
                disabled={isLoading}
                className="whitespace-nowrap rounded-lg bg-secondary px-3 py-1.5 text-xs text-secondary-foreground transition-colors duration-[120ms] ease-out hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>

        {/* Messages Scroll Area */}
        <CardContent className="relative flex-1 overflow-hidden p-0">
          <ScrollArea className="h-full p-6">
            <div className="space-y-5">
              {messages.map((msg) => {
                const isUser = msg.sender === "user";
                const isCopied = copiedMessageId === msg.id;

                return (
                  <div
                    key={msg.id}
                    className={`group/msg flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    <Avatar className="mt-0.5 size-8 shrink-0">
                      <AvatarFallback
                        className={
                          isUser
                            ? "bg-primary text-primary-foreground"
                            : "border border-border bg-secondary text-secondary-foreground"
                        }
                      >
                        {isUser ? (
                          <User className="size-4" strokeWidth={1.5} aria-hidden="true" />
                        ) : (
                          <Bot className="size-4 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                        )}
                      </AvatarFallback>
                    </Avatar>

                    <div className={`flex max-w-[85%] flex-col space-y-2 ${isUser ? "items-end" : "items-start"}`}>
                      <div className="flex items-center gap-2 px-1 text-[11px] text-muted-foreground">
                        <span>{isUser ? "Operator" : "Knowledge assistant"}</span>
                        <span aria-hidden="true">·</span>
                        <span className="tabular-nums">{msg.timestamp}</span>
                        <button
                          onClick={() => handleCopy(msg.id, msg.text)}
                          title={isCopied ? "Copied" : isUser ? "Copy prompt" : "Copy response"}
                          aria-label={isCopied ? "Copied" : isUser ? "Copy prompt" : "Copy response"}
                          className="ml-1 rounded p-0.5 text-muted-foreground transition-colors duration-[120ms] ease-out hover:text-foreground"
                        >
                          {isCopied ? (
                            <Check className="size-3 text-positive" strokeWidth={1.5} aria-hidden="true" />
                          ) : (
                            <Copy className="size-3" strokeWidth={1.5} aria-hidden="true" />
                          )}
                        </button>
                      </div>

                      <div
                        className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
                          isUser
                            ? "bg-primary text-primary-foreground whitespace-pre-wrap"
                            : "border border-border bg-muted/40 text-foreground"
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
                            <span className="size-1.5 rounded-full bg-text-secondary" aria-hidden="true" />
                            Searching the knowledge base
                          </span>
                        ) : null}
                      </div>

                      {/* Grounded Document Citations */}
                      {msg.results && msg.results.length > 0 && (
                        <div className="mt-2 w-full space-y-2 border-t border-border pt-3">
                          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                            <span className="font-medium text-text-secondary">
                              Citations ({msg.results.length})
                            </span>
                            {msg.reranked && (
                              <span className="font-mono text-[11px] text-muted-foreground">
                                reranked
                              </span>
                            )}
                          </div>

                          <div className="space-y-2">
                            {msg.results.map((hit) => {
                              const isExpanded = Boolean(expandedCitations[hit.id]);
                              // Handle both direct percentage [0, 100] and ratio [0, 1] gracefully
                              const rawScore = typeof hit.score === "number" && !isNaN(hit.score) ? hit.score : 0;
                              const scorePercent = rawScore <= 1.0 && rawScore > 0 ? rawScore * 100 : rawScore;
                              const formattedScore = scorePercent % 1 === 0 ? scorePercent.toFixed(0) : scorePercent.toFixed(1);

                              // Match tone: strong, usable, weak
                              const scoreTone =
                                scorePercent >= 70
                                  ? "bg-positive"
                                  : scorePercent >= 30
                                    ? "bg-warning"
                                    : "bg-muted-foreground/60";

                              return (
                                <div
                                  key={hit.id}
                                  className="rounded border border-border bg-card p-3 text-xs transition-colors duration-[120ms] ease-out hover:border-text-secondary/40"
                                >
                                  <div
                                    role="button"
                                    tabIndex={0}
                                    aria-expanded={isExpanded}
                                    className="flex cursor-pointer items-center justify-between gap-2 rounded focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden"
                                    onClick={() => toggleCitation(hit.id)}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter" || e.key === " ") {
                                        e.preventDefault();
                                        toggleCitation(hit.id);
                                      }
                                    }}
                                  >
                                    <div className="flex min-w-0 items-center gap-2">
                                      <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                                        #{hit.chunk_index}
                                      </span>
                                      <span className="truncate font-medium text-foreground">
                                        {hit.title || `Document ${hit.document_id}`}
                                      </span>
                                    </div>

                                    <div className="flex shrink-0 items-center gap-2">
                                      <span className="flex items-center gap-1.5 font-mono text-[11px] text-text-secondary tabular-nums">
                                        <span className={`size-1.5 rounded-full ${scoreTone}`} aria-hidden="true" />
                                        {formattedScore}%
                                      </span>
                                      {isExpanded ? (
                                        <ChevronUp className="size-3.5 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                                      ) : (
                                        <ChevronDown className="size-3.5 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                                      )}
                                    </div>
                                  </div>

                                  {isExpanded && (
                                    <div className="mt-3 space-y-2 border-t border-border pt-3 text-muted-foreground">
                                      <p className="whitespace-pre-wrap rounded border border-border bg-muted/40 p-3 font-mono text-[11px] leading-relaxed text-foreground">
                                        {hit.content}
                                      </p>
                                      <div className="flex items-center justify-between gap-2 pt-1 font-mono text-[11px]">
                                        <span className="truncate">ID: {hit.document_id}</span>
                                        <span className="flex shrink-0 cursor-pointer items-center gap-1 text-accent-text hover:underline">
                                          View in vault
                                          <ExternalLink className="size-3" strokeWidth={1.5} aria-hidden="true" />
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

              {/* Loading indicator */}
              {isLoading && !messages.some((m) => m.isStreaming && m.text.length > 0) && (
                <div className="flex items-center gap-3">
                  <Avatar className="size-8 shrink-0">
                    <AvatarFallback className="border border-border bg-secondary text-secondary-foreground">
                      <Bot className="size-4 text-muted-foreground" strokeWidth={1.5} aria-hidden="true" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex items-center gap-2 rounded-xl border border-border bg-muted/40 px-4 py-3">
                    <span className="size-1.5 rounded-full bg-text-secondary" aria-hidden="true" />
                    <span className="font-mono text-xs text-muted-foreground">
                      Searching vector embeddings and documents
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </CardContent>

        {/* Query Input Box */}
        <CardFooter className="border-t border-border bg-card p-4">
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
              aria-label="Ask about documents, schemas, or decisions"
              placeholder="Ask about documents, schemas, or decisions"
              className="flex-1 rounded-lg border border-input bg-background px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!inputQuery.trim() || isLoading}
              className="h-9 gap-1.5 px-4"
            >
              <span>Ask</span>
              <Send className="size-3.5" strokeWidth={1.5} aria-hidden="true" />
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  );
};

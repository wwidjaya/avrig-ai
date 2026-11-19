import type { AppConfig } from "../config/types";

export interface RequestOptions extends RequestInit {
  token?: string | null;
}

export interface SearchDocumentHit {
  id: string;
  document_id: string;
  title?: string;
  chunk_index: number;
  content: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchDocumentsResponse {
  query: string;
  count: number;
  reranked: boolean;
  results: SearchDocumentHit[];
}

export interface StreamSearchCallbacks {
  onMetadata?: (meta: { query: string; count: number; reranked: boolean }) => void;
  onAnswerDelta?: (delta: string) => void;
  onCitations?: (results: SearchDocumentHit[]) => void;
  onError?: (error: string) => void;
  onDone?: () => void;
}

export class ApiClient {
  private config: AppConfig;
  private getToken: (() => string | null | undefined) | null = null;

  constructor(config: AppConfig) {
    this.config = config;
  }

  public setTokenProvider(provider: () => string | null | undefined) {
    this.getToken = provider;
  }

  public async request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
    const base = this.config.apiBaseUrl ? this.config.apiBaseUrl.replace(/\/$/, "") : "";
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const url = path.startsWith("http")
      ? path
      : `${base}${cleanPath}`;

    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    const token = options.token ?? (this.getToken ? this.getToken() : null);
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { message: errorText };
      }
      throw new Error(
        `API Error [${response.status}] ${response.statusText}: ${errorData.message || errorText}`
      );
    }

    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  public get<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  public post<T = unknown>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined
    });
  }

  public put<T = unknown>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined
    });
  }

  public delete<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }

  public searchDocuments(query: string, limit = 5, threshold?: number): Promise<SearchDocumentsResponse> {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    if (threshold !== undefined) params.set("threshold", String(threshold));
    return this.get<SearchDocumentsResponse>(`/api/v1/knowledge/search?${params.toString()}`);
  }

  public async searchDocumentsStream(
    query: string,
    callbacks: StreamSearchCallbacks,
    options?: { limit?: number; threshold?: number; signal?: AbortSignal }
  ): Promise<void> {
    const base = this.config.apiBaseUrl ? this.config.apiBaseUrl.replace(/\/$/, "") : "";
    const url = `${base}/api/v1/knowledge/search`;
    const headers = new Headers();
    headers.set("Content-Type", "application/json");
    headers.set("Accept", "text/event-stream");

    const token = this.getToken ? this.getToken() : null;
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const payload: { query: string; limit?: number; threshold?: number; stream?: boolean } = {
      query,
      limit: options?.limit ?? 5,
      stream: true
    };
    if (options?.threshold !== undefined) {
      payload.threshold = options.threshold;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal: options?.signal
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorData: { message?: string } = {};
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { message: errorText };
      }
      throw new Error(
        `SSE Stream Error [${response.status}] ${response.statusText}: ${errorData.message || errorText}`
      );
    }

    if (!response.body) {
      throw new Error("Response body is empty or streaming is not supported by the environment.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process completed lines split by newline
        const lines = buffer.split(/\r?\n/);
        // Keep the last partial line in buffer
        buffer = lines.pop() ?? "";

        let currentEvent = "message";
        let currentDataLines: string[] = [];

        const dispatchCurrentEvent = () => {
          if (currentDataLines.length === 0) return;
          const dataStr = currentDataLines.join("\n");
          currentDataLines = [];

          if (currentEvent === "metadata") {
            try {
              const meta = JSON.parse(dataStr);
              callbacks.onMetadata?.(meta);
            } catch {
              // Ignore or pass raw
            }
          } else if (currentEvent === "delta" || currentEvent === "answer" || currentEvent === "content") {
            try {
              const parsed = JSON.parse(dataStr);
              const delta = typeof parsed === "string" ? parsed : (parsed.delta ?? parsed.content ?? dataStr);
              callbacks.onAnswerDelta?.(delta);
            } catch {
              callbacks.onAnswerDelta?.(dataStr);
            }
          } else if (currentEvent === "citations" || currentEvent === "results") {
            try {
              const parsed = JSON.parse(dataStr);
              const results: SearchDocumentHit[] = Array.isArray(parsed) ? parsed : (parsed.results ?? []);
              callbacks.onCitations?.(results);
            } catch {
              // Ignore parse error
            }
          } else if (currentEvent === "error") {
            try {
              const parsed = JSON.parse(dataStr);
              callbacks.onError?.(parsed.message || dataStr);
            } catch {
              callbacks.onError?.(dataStr);
            }
          } else if (currentEvent === "done") {
            callbacks.onDone?.();
          } else {
            // General / unknown event: try delta or json
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.delta) callbacks.onAnswerDelta?.(parsed.delta);
              else if (parsed.results) callbacks.onCitations?.(parsed.results);
              else if (parsed.error) callbacks.onError?.(parsed.error);
            } catch {
              // If simple text delta
              callbacks.onAnswerDelta?.(dataStr);
            }
          }
        };

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            // Empty line marks the end of an event block
            dispatchCurrentEvent();
            currentEvent = "message";
            continue;
          }

          if (line.startsWith(":")) {
            // SSE comment / keep-alive
            continue;
          }

          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            currentDataLines.push(line.slice(5).trimStart());
          }
        }

        // Flush any pending event in the chunk if newline separated
        dispatchCurrentEvent();
      }

      callbacks.onDone?.();
    } finally {
      reader.releaseLock();
    }
  }
}

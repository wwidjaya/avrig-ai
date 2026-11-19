import type {
  AppConfig,
  SearchResult,
  SearchDocumentsResponse,
  SystemStatus,
  Session
} from "@avrig/types";

export interface RequestOptions extends RequestInit {
  token?: string | null;
}

export interface StreamSearchCallbacks {
  onMetadata?: (meta: { query: string; count: number; reranked: boolean }) => void;
  onAnswerDelta?: (delta: string) => void;
  onCitations?: (results: SearchResult[]) => void;
  onError?: (error: string) => void;
  onDone?: () => void;
}

export interface ClientConfig {
  baseUrl?: string;
  wsBaseUrl?: string;
  tokenProvider?: () => string | null | undefined;
}

export class ApiClient {
  private baseUrl: string;
  private wsBaseUrl: string;
  private getToken: (() => string | null | undefined) | null = null;

  constructor(config?: Partial<AppConfig> | ClientConfig) {
    const isBrowser = typeof window !== "undefined";
    const defaultOrigin = isBrowser && window.location ? window.location.origin : "https://app.avrig.ai";

    if (config && "apiBaseUrl" in config && config.apiBaseUrl) {
      this.baseUrl = config.apiBaseUrl;
    } else if (config && "baseUrl" in config && config.baseUrl) {
      this.baseUrl = config.baseUrl;
    } else {
      this.baseUrl = isBrowser ? "" : defaultOrigin;
    }

    if (config && "wsBaseUrl" in config && config.wsBaseUrl) {
      this.wsBaseUrl = config.wsBaseUrl;
    } else if (config && "wsBaseUrl" in config && (config as ClientConfig).wsBaseUrl) {
      this.wsBaseUrl = (config as ClientConfig).wsBaseUrl!;
    } else {
      if (isBrowser) {
        const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
        this.wsBaseUrl = `${proto}//${window.location.host}`;
      } else {
        this.wsBaseUrl = "wss://app.avrig.ai";
      }
    }

    if (config && "tokenProvider" in config && config.tokenProvider) {
      this.getToken = config.tokenProvider;
    }
  }

  public setTokenProvider(provider: () => string | null | undefined) {
    this.getToken = provider;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public getWsBaseUrl(): string {
    return this.wsBaseUrl;
  }

  public async request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
    let url: string;
    if (path.startsWith("http://") || path.startsWith("https://")) {
      url = path;
    } else {
      const cleanPath = path.startsWith("/") ? path : `/${path}`;
      if (!this.baseUrl || this.baseUrl === "/") {
        url = cleanPath;
      } else {
        url = `${this.baseUrl.replace(/\/$/, "")}${cleanPath}`;
      }
    }

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
      let errorData: { message?: string } = {};
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

  // Health and System Endpoints
  public getHealth(): Promise<SystemStatus> {
    return this.get<SystemStatus>("/api/v1/health");
  }

  // Auth and Session Endpoints
  public getSession(): Promise<Session> {
    return this.get<Session>("/api/v1/auth/session");
  }

  // Knowledge Search Endpoints
  public searchDocuments(query: string, limit = 5, threshold?: number): Promise<SearchDocumentsResponse> {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    if (threshold !== undefined) params.set("threshold", String(threshold));
    return this.get<SearchDocumentsResponse>(`/api/v1/knowledge/search?${params.toString()}`);
  }

  // SSE Event Streaming Listener
  public async searchDocumentsStream(
    query: string,
    callbacks: StreamSearchCallbacks,
    options?: { limit?: number; threshold?: number; signal?: AbortSignal }
  ): Promise<void> {
    let url: string;
    if (!this.baseUrl || this.baseUrl === "/") {
      url = "/api/v1/knowledge/search";
    } else {
      url = `${this.baseUrl.replace(/\/$/, "")}/api/v1/knowledge/search`;
    }

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
        const lines = buffer.split(/\r?\n/);
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
              // ignore
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
              const results: SearchResult[] = Array.isArray(parsed) ? parsed : (parsed.results ?? []);
              callbacks.onCitations?.(results);
            } catch {
              // ignore
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
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.delta) callbacks.onAnswerDelta?.(parsed.delta);
              else if (parsed.results) callbacks.onCitations?.(parsed.results);
              else if (parsed.error) callbacks.onError?.(parsed.error);
            } catch {
              callbacks.onAnswerDelta?.(dataStr);
            }
          }
        };

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            dispatchCurrentEvent();
            currentEvent = "message";
            continue;
          }

          if (line.startsWith(":")) {
            continue;
          }

          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            currentDataLines.push(line.slice(5).trimStart());
          }
        }

        dispatchCurrentEvent();
      }

      callbacks.onDone?.();
    } finally {
      reader.releaseLock();
    }
  }

  // Create resilient WebSocket manager
  public createWebSocketManager(path = "/ws"): ResilientWebSocketManager {
    return new ResilientWebSocketManager(this.wsBaseUrl, () => this.getToken ? this.getToken() : null, path);
  }
}

// WebSocket Manager
export type WebSocketMessageListener<T = unknown> = (data: T) => void;
export type WebSocketConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

export class ResilientWebSocketManager {
  private wsBaseUrl: string;
  private getToken: (() => string | null | undefined) | null = null;
  private defaultPath: string;
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<WebSocketMessageListener>> = new Map();
  private statusListeners: Set<(status: WebSocketConnectionStatus) => void> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isExplicitlyClosed = false;
  private status: WebSocketConnectionStatus = "disconnected";

  constructor(
    wsBaseUrl: string,
    tokenProvider?: (() => string | null | undefined) | null,
    defaultPath = "/ws"
  ) {
    this.wsBaseUrl = wsBaseUrl;
    this.getToken = tokenProvider ?? null;
    this.defaultPath = defaultPath;
  }

  public setTokenProvider(provider: () => string | null | undefined) {
    this.getToken = provider;
  }

  public getStatus(): WebSocketConnectionStatus {
    return this.status;
  }

  public onStatusChange(callback: (status: WebSocketConnectionStatus) => void): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => this.statusListeners.delete(callback);
  }

  private setStatus(status: WebSocketConnectionStatus) {
    this.status = status;
    this.statusListeners.forEach((fn) => fn(status));
  }

  public connect(path?: string) {
    const targetPath = path ?? this.defaultPath;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    const token = this.getToken ? this.getToken() : null;
    const base = this.wsBaseUrl.replace(/\/$/, "");
    const cleanPath = targetPath.replace(/^\//, "");
    const url = new URL(`${base}/${cleanPath}`);
    if (token) {
      url.searchParams.set("token", token);
    }

    try {
      this.ws = new WebSocket(url.toString());

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus("connected");
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const channel = payload.channel || payload.topic || "default";
          const subscribers = this.listeners.get(channel);
          if (subscribers) {
            subscribers.forEach((callback) => callback(payload.data || payload));
          }
        } catch {
          const rawSubscribers = this.listeners.get("raw");
          if (rawSubscribers) {
            rawSubscribers.forEach((callback) => callback(event.data));
          }
        }
      };

      this.ws.onerror = () => {
        // onclose will handle reconnection
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect(targetPath);
        } else {
          this.setStatus("disconnected");
        }
      };
    } catch {
      this.scheduleReconnect(targetPath);
    }
  }

  private scheduleReconnect(path: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus("disconnected");
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.setStatus("reconnecting");

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      this.connect(path);
    }, delay);
  }

  public subscribe<T = unknown>(channel: string, listener: WebSocketMessageListener<T>): () => void {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set());
    }
    const set = this.listeners.get(channel)!;
    set.add(listener as WebSocketMessageListener);

    return () => {
      set.delete(listener as WebSocketMessageListener);
      if (set.size === 0) {
        this.listeners.delete(channel);
      }
    };
  }

  public send(channel: string, data: unknown) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("Cannot send WebSocket message: connection is not open.");
    }
    const message = JSON.stringify({ channel, data });
    this.ws.send(message);
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus("disconnected");
  }
}

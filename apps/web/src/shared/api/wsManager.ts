import type { AppConfig } from "../config/types";

export type WebSocketMessageListener<T = unknown> = (data: T) => void;
export type WebSocketConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

export class ResilientWebSocketManager {
  private config: AppConfig;
  private ws: WebSocket | null = null;
  private getToken: (() => string | null | undefined) | null = null;
  private listeners: Map<string, Set<WebSocketMessageListener>> = new Map();
  private statusListeners: Set<(status: WebSocketConnectionStatus) => void> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isExplicitlyClosed = false;
  private status: WebSocketConnectionStatus = "disconnected";

  constructor(config: AppConfig) {
    this.config = config;
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

  public connect(path = "/ws") {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    const token = this.getToken ? this.getToken() : null;
    const base = this.config.wsBaseUrl.replace(/\/$/, "");
    const cleanPath = path.replace(/^\//, "");
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
          // If non-JSON message, broadcast on 'raw'
          const rawSubscribers = this.listeners.get("raw");
          if (rawSubscribers) {
            rawSubscribers.forEach((callback) => callback(event.data));
          }
        }
      };

      this.ws.onerror = () => {
        // Handled in onclose
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect(path);
        } else {
          this.setStatus("disconnected");
        }
      };
    } catch {
      this.scheduleReconnect(path);
    }
  }

  private scheduleReconnect(path: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus("disconnected");
      return;
    }

    this.setStatus("reconnecting");
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;

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
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ channel, data }));
    }
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

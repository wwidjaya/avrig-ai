import type { AppConfig, SearchResult, SearchDocumentsResponse, SystemStatus, Session } from "@avrig/types";
export interface RequestOptions extends RequestInit {
    token?: string | null;
}
export interface StreamSearchCallbacks {
    onMetadata?: (meta: {
        query: string;
        count: number;
        reranked: boolean;
    }) => void;
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
export declare class ApiClient {
    private baseUrl;
    private wsBaseUrl;
    private getToken;
    constructor(config?: Partial<AppConfig> | ClientConfig);
    setTokenProvider(provider: () => string | null | undefined): void;
    getBaseUrl(): string;
    getWsBaseUrl(): string;
    request<T = unknown>(path: string, options?: RequestOptions): Promise<T>;
    get<T = unknown>(path: string, options?: RequestOptions): Promise<T>;
    post<T = unknown>(path: string, data?: unknown, options?: RequestOptions): Promise<T>;
    put<T = unknown>(path: string, data?: unknown, options?: RequestOptions): Promise<T>;
    delete<T = unknown>(path: string, options?: RequestOptions): Promise<T>;
    getHealth(): Promise<SystemStatus>;
    getSession(): Promise<Session>;
    searchDocuments(query: string, limit?: number, threshold?: number): Promise<SearchDocumentsResponse>;
    searchDocumentsStream(query: string, callbacks: StreamSearchCallbacks, options?: {
        limit?: number;
        threshold?: number;
        signal?: AbortSignal;
    }): Promise<void>;
    createWebSocketManager(path?: string): ResilientWebSocketManager;
}
export type WebSocketMessageListener<T = unknown> = (data: T) => void;
export type WebSocketConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";
export declare class ResilientWebSocketManager {
    private wsBaseUrl;
    private getToken;
    private defaultPath;
    private ws;
    private listeners;
    private statusListeners;
    private reconnectAttempts;
    private maxReconnectAttempts;
    private reconnectTimer;
    private isExplicitlyClosed;
    private status;
    constructor(wsBaseUrl: string, tokenProvider?: (() => string | null | undefined) | null, defaultPath?: string);
    setTokenProvider(provider: () => string | null | undefined): void;
    getStatus(): WebSocketConnectionStatus;
    onStatusChange(callback: (status: WebSocketConnectionStatus) => void): () => void;
    private setStatus;
    connect(path?: string): void;
    private scheduleReconnect;
    subscribe<T = unknown>(channel: string, listener: WebSocketMessageListener<T>): () => void;
    send(channel: string, data: unknown): void;
    disconnect(): void;
}
//# sourceMappingURL=index.d.ts.map
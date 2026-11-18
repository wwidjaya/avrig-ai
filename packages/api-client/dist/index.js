export class ApiClient {
    baseUrl;
    wsBaseUrl;
    getToken = null;
    constructor(config) {
        const isBrowser = typeof window !== "undefined";
        const defaultOrigin = isBrowser && window.location ? window.location.origin : "https://app.avrig.ai";
        if (config && "apiBaseUrl" in config && config.apiBaseUrl) {
            this.baseUrl = config.apiBaseUrl;
        }
        else if (config && "baseUrl" in config && config.baseUrl) {
            this.baseUrl = config.baseUrl;
        }
        else {
            this.baseUrl = isBrowser ? "" : defaultOrigin;
        }
        if (config && "wsBaseUrl" in config && config.wsBaseUrl) {
            this.wsBaseUrl = config.wsBaseUrl;
        }
        else if (config && "wsBaseUrl" in config && config.wsBaseUrl) {
            this.wsBaseUrl = config.wsBaseUrl;
        }
        else {
            if (isBrowser) {
                const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
                this.wsBaseUrl = `${proto}//${window.location.host}`;
            }
            else {
                this.wsBaseUrl = "wss://app.avrig.ai";
            }
        }
        if (config && "tokenProvider" in config && config.tokenProvider) {
            this.getToken = config.tokenProvider;
        }
    }
    setTokenProvider(provider) {
        this.getToken = provider;
    }
    getBaseUrl() {
        return this.baseUrl;
    }
    getWsBaseUrl() {
        return this.wsBaseUrl;
    }
    async request(path, options = {}) {
        let url;
        if (path.startsWith("http://") || path.startsWith("https://")) {
            url = path;
        }
        else {
            const cleanPath = path.startsWith("/") ? path : `/${path}`;
            if (!this.baseUrl || this.baseUrl === "/") {
                url = cleanPath;
            }
            else {
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
            let errorData = {};
            try {
                errorData = JSON.parse(errorText);
            }
            catch {
                errorData = { message: errorText };
            }
            throw new Error(`API Error [${response.status}] ${response.statusText}: ${errorData.message || errorText}`);
        }
        if (response.status === 204) {
            return null;
        }
        return response.json();
    }
    get(path, options) {
        return this.request(path, { ...options, method: "GET" });
    }
    post(path, data, options) {
        return this.request(path, {
            ...options,
            method: "POST",
            body: data ? JSON.stringify(data) : undefined
        });
    }
    put(path, data, options) {
        return this.request(path, {
            ...options,
            method: "PUT",
            body: data ? JSON.stringify(data) : undefined
        });
    }
    delete(path, options) {
        return this.request(path, { ...options, method: "DELETE" });
    }
    // Health and System Endpoints
    getHealth() {
        return this.get("/api/v1/health");
    }
    // Auth and Session Endpoints
    getSession() {
        return this.get("/api/v1/auth/session");
    }
    // Knowledge Search Endpoints
    searchDocuments(query, limit = 5, threshold) {
        const params = new URLSearchParams({ q: query, limit: String(limit) });
        if (threshold !== undefined)
            params.set("threshold", String(threshold));
        return this.get(`/api/v1/documents/search?${params.toString()}`);
    }
    // SSE Event Streaming Listener
    async searchDocumentsStream(query, callbacks, options) {
        let url;
        if (!this.baseUrl || this.baseUrl === "/") {
            url = "/api/v1/documents/search/stream";
        }
        else {
            url = `${this.baseUrl.replace(/\/$/, "")}/api/v1/documents/search/stream`;
        }
        const headers = new Headers();
        headers.set("Content-Type", "application/json");
        headers.set("Accept", "text/event-stream");
        const token = this.getToken ? this.getToken() : null;
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }
        const payload = {
            query,
            limit: options?.limit ?? 5
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
            let errorData = {};
            try {
                errorData = JSON.parse(errorText);
            }
            catch {
                errorData = { message: errorText };
            }
            throw new Error(`SSE Stream Error [${response.status}] ${response.statusText}: ${errorData.message || errorText}`);
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
                if (done)
                    break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split(/\r?\n/);
                buffer = lines.pop() ?? "";
                let currentEvent = "message";
                let currentDataLines = [];
                const dispatchCurrentEvent = () => {
                    if (currentDataLines.length === 0)
                        return;
                    const dataStr = currentDataLines.join("\n");
                    currentDataLines = [];
                    if (currentEvent === "metadata") {
                        try {
                            const meta = JSON.parse(dataStr);
                            callbacks.onMetadata?.(meta);
                        }
                        catch {
                            // ignore
                        }
                    }
                    else if (currentEvent === "delta" || currentEvent === "answer" || currentEvent === "content") {
                        try {
                            const parsed = JSON.parse(dataStr);
                            const delta = typeof parsed === "string" ? parsed : (parsed.delta ?? parsed.content ?? dataStr);
                            callbacks.onAnswerDelta?.(delta);
                        }
                        catch {
                            callbacks.onAnswerDelta?.(dataStr);
                        }
                    }
                    else if (currentEvent === "citations" || currentEvent === "results") {
                        try {
                            const parsed = JSON.parse(dataStr);
                            const results = Array.isArray(parsed) ? parsed : (parsed.results ?? []);
                            callbacks.onCitations?.(results);
                        }
                        catch {
                            // ignore
                        }
                    }
                    else if (currentEvent === "error") {
                        try {
                            const parsed = JSON.parse(dataStr);
                            callbacks.onError?.(parsed.message || dataStr);
                        }
                        catch {
                            callbacks.onError?.(dataStr);
                        }
                    }
                    else if (currentEvent === "done") {
                        callbacks.onDone?.();
                    }
                    else {
                        try {
                            const parsed = JSON.parse(dataStr);
                            if (parsed.delta)
                                callbacks.onAnswerDelta?.(parsed.delta);
                            else if (parsed.results)
                                callbacks.onCitations?.(parsed.results);
                            else if (parsed.error)
                                callbacks.onError?.(parsed.error);
                        }
                        catch {
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
                    }
                    else if (line.startsWith("data:")) {
                        currentDataLines.push(line.slice(5).trimStart());
                    }
                }
                dispatchCurrentEvent();
            }
            callbacks.onDone?.();
        }
        finally {
            reader.releaseLock();
        }
    }
    // Create resilient WebSocket manager
    createWebSocketManager(path = "/ws") {
        return new ResilientWebSocketManager(this.wsBaseUrl, () => this.getToken ? this.getToken() : null, path);
    }
}
export class ResilientWebSocketManager {
    wsBaseUrl;
    getToken = null;
    defaultPath;
    ws = null;
    listeners = new Map();
    statusListeners = new Set();
    reconnectAttempts = 0;
    maxReconnectAttempts = 10;
    reconnectTimer = null;
    isExplicitlyClosed = false;
    status = "disconnected";
    constructor(wsBaseUrl, tokenProvider, defaultPath = "/ws") {
        this.wsBaseUrl = wsBaseUrl;
        this.getToken = tokenProvider ?? null;
        this.defaultPath = defaultPath;
    }
    setTokenProvider(provider) {
        this.getToken = provider;
    }
    getStatus() {
        return this.status;
    }
    onStatusChange(callback) {
        this.statusListeners.add(callback);
        callback(this.status);
        return () => this.statusListeners.delete(callback);
    }
    setStatus(status) {
        this.status = status;
        this.statusListeners.forEach((fn) => fn(status));
    }
    connect(path) {
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
                }
                catch {
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
                }
                else {
                    this.setStatus("disconnected");
                }
            };
        }
        catch {
            this.scheduleReconnect(targetPath);
        }
    }
    scheduleReconnect(path) {
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
    subscribe(channel, listener) {
        if (!this.listeners.has(channel)) {
            this.listeners.set(channel, new Set());
        }
        const set = this.listeners.get(channel);
        set.add(listener);
        return () => {
            set.delete(listener);
            if (set.size === 0) {
                this.listeners.delete(channel);
            }
        };
    }
    send(channel, data) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            throw new Error("Cannot send WebSocket message: connection is not open.");
        }
        const message = JSON.stringify({ channel, data });
        this.ws.send(message);
    }
    disconnect() {
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
//# sourceMappingURL=index.js.map
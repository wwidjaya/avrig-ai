// Auth & Session Types
export interface User {
  id: string;
  email: string;
  name?: string;
  roles: string[];
  avatarUrl?: string;
}

export interface Session {
  id: string;
  userId: string;
  clientType: "web" | "desktop" | "mobile";
  expiresAt: string;
  createdAt: string;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string;
  expiresIn?: number;
  refreshToken?: string;
  idToken?: string;
}

export interface OidcConfig {
  authority: string;
  clientId: string;
  scope?: string;
  redirectUri?: string;
  postLogoutRedirectUri?: string;
  responseType?: string;
  automaticSilentRenew?: boolean;
}

export interface AppConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  auth: OidcConfig;
  features: Record<string, boolean>;
}

// Knowledge & Search Types
export interface SearchResult {
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
  results: SearchResult[];
}

// Chat & Streaming Types
export interface StreamChunk {
  event: "metadata" | "delta" | "citations" | "error" | "done" | string;
  data: unknown;
}

export interface KnowledgeChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: SearchResult[];
  timestamp: string;
  pending?: boolean;
}

// SDLC & System Types
export interface SdlcTask {
  id: string;
  title: string;
  description?: string;
  status: "backlog" | "todo" | "in_progress" | "review" | "done";
  assignee?: string;
  priority?: "low" | "medium" | "high" | "critical";
  createdAt: string;
  updatedAt: string;
}

export interface DeliberationThread {
  id: string;
  title: string;
  topic: string;
  status: "open" | "deliberating" | "consensus" | "closed";
  participants: string[];
  createdAt: string;
}

export interface SystemStatus {
  version: string;
  status: "healthy" | "degraded" | "down";
  uptimeSeconds: number;
  activeAgents: number;
  activeSessions: number;
}

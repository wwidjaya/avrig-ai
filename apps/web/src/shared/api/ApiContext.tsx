import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "react-oidc-context";
import { useAppConfig } from "../config/ConfigContext";
import { ApiClient, ResilientWebSocketManager, type WebSocketConnectionStatus } from "@avrig/api-client";

interface ApiContextValue {
  api: ApiClient;
  ws: ResilientWebSocketManager;
  wsStatus: WebSocketConnectionStatus;
}

const ApiContext = createContext<ApiContextValue | null>(null);

export const ApiProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const config = useAppConfig();
  const auth = useAuth();
  const [wsStatus, setWsStatus] = useState<WebSocketConnectionStatus>("disconnected");

  const api = useMemo(() => new ApiClient(config), [config]);
  const ws = useMemo(() => new ResilientWebSocketManager(config.wsBaseUrl), [config.wsBaseUrl]);

  useEffect(() => {
    const tokenProvider = () => auth.user?.access_token;
    api.setTokenProvider(tokenProvider);
    ws.setTokenProvider(tokenProvider);
  }, [api, ws, auth.user?.access_token]);

  useEffect(() => {
    const unsub = ws.onStatusChange((status) => {
      setWsStatus(status);
    });

    if (auth.isAuthenticated) {
      ws.connect("/command-center");
    } else {
      ws.disconnect();
    }

    return () => {
      unsub();
      ws.disconnect();
    };
  }, [ws, auth.isAuthenticated]);

  return (
    <ApiContext.Provider value={{ api, ws, wsStatus }}>
      {children}
    </ApiContext.Provider>
  );
};

export function useApi(): ApiContextValue {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error("useApi must be used within an ApiProvider");
  }
  return context;
}

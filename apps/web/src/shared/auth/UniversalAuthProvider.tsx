import React, { useMemo } from "react";
import { AuthProvider, type AuthProviderProps } from "react-oidc-context";
import { WebStorageStateStore } from "oidc-client-ts";
import { useAppConfig } from "../config/ConfigContext";

interface UniversalAuthProviderProps {
  children: React.ReactNode;
}

export const UniversalAuthProvider: React.FC<UniversalAuthProviderProps> = ({ children }) => {
  const config = useAppConfig();

  const oidcConfig: AuthProviderProps = useMemo(() => {
    const auth = config.auth;
    const currentOrigin = typeof window !== "undefined" ? window.location.origin : "";

    const redirectUri = currentOrigin
      ? `${currentOrigin}/auth/callback`
      : auth.redirectUri;
    const postLogoutRedirectUri = currentOrigin
      ? `${currentOrigin}/`
      : auth.postLogoutRedirectUri;

    return {
      authority: auth.authority,
      client_id: auth.clientId,
      redirect_uri: redirectUri,
      post_logout_redirect_uri: postLogoutRedirectUri,
      response_type: auth.responseType || "code",
      scope: auth.scope || "openid profile email",
      automaticSilentRenew: auth.automaticSilentRenew ?? true,
      userStore: typeof window !== "undefined" ? new WebStorageStateStore({ store: window.sessionStorage }) : undefined,
      onSigninCallback: () => {
        // Strip callback query params and pathname, route cleanly to console view
        if (typeof window !== "undefined") {
          localStorage.setItem("avrig-logged-in", "true");
          window.history.replaceState({}, document.title, window.location.origin + "/console");
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
      }
    };
  }, [config.auth]);

  return <AuthProvider {...oidcConfig}>{children}</AuthProvider>;
};

import React from "react";
import { useAuth } from "react-oidc-context";
import { Button } from "@avrig/ui";
import { ShieldAlert, LogIn, RefreshCw } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const auth = useAuth();

  if (auth.isLoading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-3 bg-background text-foreground">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Validating authentication credentials...</p>
      </div>
    );
  }

  if (auth.error) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-background p-6 text-foreground">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold">Authentication Error</h2>
        <p className="max-w-md text-center text-sm text-muted-foreground">
          {auth.error.message || "An unexpected error occurred during OpenID Connect authentication."}
        </p>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => void auth.signinRedirect()}>
            <LogIn className="mr-2 h-4 w-4" />
            Try Sign-In Again
          </Button>
          <Button variant="ghost" onClick={() => window.location.reload()}>
            Reload Application
          </Button>
        </div>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-background p-6 text-foreground">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <LogIn className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold">avrig Command Center</h2>
        <p className="max-w-md text-center text-sm text-muted-foreground">
          Autonomous organizational command requires authorized founder or operator authentication.
        </p>
        <Button onClick={() => void auth.signinRedirect()}>
          Sign In via Universal OIDC
        </Button>
      </div>
    );
  }

  return <>{children}</>;
};

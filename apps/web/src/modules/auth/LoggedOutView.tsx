import React from "react";
import { useAuth } from "react-oidc-context";
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription } from "@avrig/ui";
import { ShieldCheck, LogIn, ArrowLeft, CheckCircle2 } from "lucide-react";

interface LoggedOutViewProps {
  onSignInAgain?: () => void;
  onReturnHome?: () => void;
}

export const LoggedOutView: React.FC<LoggedOutViewProps> = ({
  onSignInAgain,
  onReturnHome,
}) => {
  const auth = useAuth();

  const handleSignIn = async () => {
    if (onSignInAgain) {
      onSignInAgain();
      return;
    }
    try {
      await auth.signinRedirect();
    } catch (err) {
      console.error("Sign-in redirect failed:", err);
    }
  };

  const handleHome = () => {
    if (onReturnHome) {
      onReturnHome();
      return;
    }
    if (typeof window !== "undefined") {
      window.history.pushState({}, document.title, window.location.origin + "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-background px-4 py-12 text-foreground">
      <div className="w-full max-w-md">
        <Card className="border-border bg-card/95 shadow-xl backdrop-blur-sm">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <ShieldCheck className="size-8" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">
              Session Terminated
            </CardTitle>
            <CardDescription className="text-sm text-muted-foreground mt-2">
              Operator Logged Out
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-lg border border-border bg-muted/40 p-4 text-xs text-muted-foreground">
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" />
                <p className="leading-relaxed">
                  Your active session, cryptographic credentials, and local authorization tokens have been securely terminated from this browser and the upstream identity provider.
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <Button
                size="lg"
                className="w-full font-semibold shadow-xs cursor-pointer"
                onClick={handleSignIn}
              >
                <LogIn className="mr-2 size-4" />
                Sign In Again
              </Button>

              <Button
                variant="outline"
                size="lg"
                className="w-full font-semibold cursor-pointer"
                onClick={handleHome}
              >
                <ArrowLeft className="mr-2 size-4" />
                Return to Home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

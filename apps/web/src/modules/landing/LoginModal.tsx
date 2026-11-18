import React from "react";
import { useAuth } from "react-oidc-context";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  Button,
  Badge,
} from "@avrig/ui";
import { ShieldCheck, LogIn, Sparkles, ExternalLink, RefreshCw, Languages } from "lucide-react";
import { useAppConfig } from "../../shared/config/ConfigContext";
import { useI18n } from "../../shared/i18n/I18nContext";

interface LoginModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDemoAccess: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({
  open,
  onOpenChange,
  onDemoAccess,
}) => {
  const auth = useAuth();
  const config = useAppConfig();
  const { locale, setLocale, t } = useI18n();

  const toggleLocale = () => {
    setLocale(locale === "en" ? "id" : "en");
  };

  const handleSignIn = async () => {
    try {
      await auth.signinRedirect();
    } catch (err) {
      console.error("OpenID Connect redirect failed", err);
    }
  };

  const authorityHost = (() => {
    try {
      return new URL(config.auth.authority).host;
    } catch {
      return config.auth.authority;
    }
  })();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card/95 backdrop-blur-xl border-border shadow-2xl">
        <DialogHeader className="text-center sm:text-left">
          <div className="flex items-center justify-between mb-3">
            <div className="mx-auto sm:mx-0 flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShieldCheck className="size-6" />
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleLocale}
              className="gap-1.5 font-mono text-xs font-semibold cursor-pointer select-none"
              title={locale === "en" ? "Beralih ke Bahasa Indonesia (ID)" : "Switch to English (EN)"}
              aria-label="Toggle language"
            >
              <Languages className="size-4 text-muted-foreground" />
              <span className="uppercase font-bold tracking-wider">{locale}</span>
            </Button>
          </div>
          <DialogTitle className="text-2xl font-bold tracking-tight text-foreground">
            {t.login.title}
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground mt-1">
            {t.login.subtitle}
          </DialogDescription>
        </DialogHeader>

        {/* Runtime OIDC Connection Status */}
        <div className="rounded-lg border border-border bg-muted/30 p-3.5 my-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full size-2 bg-primary"></span>
            </span>
            <span className="text-muted-foreground">{t.login.authorityConnected}:</span>
          </div>
          <Badge variant="outline" className="font-mono text-[11px] font-semibold text-foreground bg-background">
            {authorityHost}
          </Badge>
        </div>

        {/* Action Controls */}
        <div className="flex flex-col gap-3 pt-2">
          <Button
            size="lg"
            className="w-full font-semibold shadow-sm cursor-pointer"
            disabled={auth.isLoading}
            onClick={handleSignIn}
          >
            {auth.isLoading ? (
              <>
                <RefreshCw className="mr-2 size-4 animate-spin" />
                {t.login.connecting}
              </>
            ) : (
              <>
                <LogIn className="mr-2 size-4" />
                {t.login.ssoButton}
                <ExternalLink className="ml-2 size-3.5 opacity-60" />
              </>
            )}
          </Button>

          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground font-medium">Or</span>
            </div>
          </div>

          <Button
            variant="outline"
            size="lg"
            className="w-full font-semibold cursor-pointer"
            onClick={() => {
              if (typeof window !== "undefined") {
                localStorage.setItem("avrig-logged-in", "true");
              }
              onDemoAccess();
            }}
          >
            <Sparkles className="mr-2 size-4 text-primary" />
            {t.login.demoButton}
          </Button>
          <p className="text-[11px] text-center text-muted-foreground">
            {t.login.demoNote}
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

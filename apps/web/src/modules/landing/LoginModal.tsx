import React from "react";
import { useAuth } from "react-oidc-context";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  Button,
} from "@avrig/ui";
import { Languages } from "lucide-react";
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
      <DialogContent className="sm:max-w-md rounded-2xl border-border bg-card p-6 shadow-none">
        <DialogHeader className="text-left">
          <div className="mb-6 flex items-start justify-between gap-4">
            <DialogTitle className="text-2xl font-medium tracking-tight text-foreground">
              {t.login.title}
            </DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleLocale}
              className="gap-1.5 text-text-secondary"
              title={locale === "en" ? "Beralih ke Bahasa Indonesia" : "Switch to English"}
              aria-label="Toggle language"
            >
              <Languages className="size-4" strokeWidth={1.5} />
              <span className="font-mono text-xs">{locale}</span>
            </Button>
          </div>
          <DialogDescription className="text-sm text-text-secondary">
            {t.login.subtitle}
          </DialogDescription>
        </DialogHeader>

        <div className="my-2 flex items-center justify-between border-y border-border py-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-positive" aria-hidden="true" />
            <span className="text-muted-foreground">{t.login.authorityConnected}</span>
          </div>
          <span className="font-mono text-xs text-foreground tabular-nums">{authorityHost}</span>
        </div>

        <div className="flex flex-col gap-3 pt-2">
          <Button size="lg" className="w-full" disabled={auth.isLoading} onClick={handleSignIn}>
            {auth.isLoading ? t.login.connecting : t.login.ssoButton}
          </Button>

          <div className="my-1 border-t border-border" aria-hidden="true" />

          <Button
            variant="outline"
            size="lg"
            className="w-full"
            onClick={onDemoAccess}
          >
            {t.login.demoButton}
          </Button>
          <p className="text-xs text-muted-foreground text-center">{t.login.demoNote}</p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

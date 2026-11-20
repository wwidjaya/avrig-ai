import React, { useState, useEffect } from "react";
import { useAuth } from "react-oidc-context";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@avrig/ui";
import { ArrowRight, Check } from "lucide-react";
import { useI18n } from "../../shared/i18n/I18nContext";
import { ThemeSelector } from "../../shared/components/ThemeSelector";
import { LanguageSelector } from "../../shared/components/LanguageSelector";
import { LoginModal } from "./LoginModal";

interface LandingPageProps {
  onEnterCommandCenter: (targetPath?: string) => void;
}

type StageCode = "RE" | "SA" | "DV" | "TE";

const STAGE_ORDER: StageCode[] = ["RE", "SA", "DV", "TE"];

const appVersion = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.1.0";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterCommandCenter }) => {
  const auth = useAuth();
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const { t } = useI18n();

  // Active stage on the hero gate certificate
  const [activeStage, setActiveStage] = useState<StageCode>("RE");

  // One entrance on load, skipped entirely when motion is reduced
  const [entered, setEntered] = useState<boolean>(prefersReducedMotion);

  useEffect(() => {
    if (entered) return;
    const frame = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(frame);
  }, [entered]);

  const enter = `transition-[transform,opacity] ease-out duration-[240ms] ${
    entered ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
  }`;

  const isLoggedIn = Boolean(
    auth.isAuthenticated ||
    auth.user ||
    (typeof window !== "undefined" && localStorage.getItem("avrig-logged-in") === "true")
  );

  const handleLaunchConsole = () => {
    if (isLoggedIn) {
      onEnterCommandCenter();
    } else {
      setLoginModalOpen(true);
    }
  };

  const handleDemoAccess = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("avrig-logged-in", "true");
    }
    setLoginModalOpen(false);
    onEnterCommandCenter();
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const sdlc = t.showcase.sdlc;

  const stages: Array<{
    code: StageCode;
    index: string;
    name: string;
    status: string;
    tone: string;
    approved: boolean;
    current: boolean;
    checks: [string, string];
  }> = [
    {
      code: "RE",
      index: "01",
      name: sdlc.item1Name,
      status: sdlc.item1Status,
      tone: "bg-positive",
      approved: true,
      current: false,
      checks: [t.certificate.reCheck1, t.certificate.reCheck2],
    },
    {
      code: "SA",
      index: "02",
      name: sdlc.item2Name,
      status: sdlc.item2Status,
      tone: "bg-positive",
      approved: true,
      current: false,
      checks: [t.certificate.saCheck1, t.certificate.saCheck2],
    },
    {
      code: "DV",
      index: "03",
      name: sdlc.item3Name,
      status: sdlc.item3Status,
      tone: "bg-accent-text",
      approved: false,
      current: true,
      checks: [t.certificate.dvCheck1, t.certificate.dvCheck2],
    },
    {
      code: "TE",
      index: "04",
      name: sdlc.item4Name,
      status: sdlc.item4Status,
      tone: "bg-muted-foreground/60",
      approved: false,
      current: false,
      checks: [t.certificate.teCheck1, t.certificate.teCheck2],
    },
  ];
  const stage = stages.find((item) => item.code === activeStage) ?? stages[0];

  const navLinks = [
    { id: "sdlc-cockpit", label: t.nav.sdlc },
    { id: "architecture", label: t.nav.architecture },
    { id: "workflow", label: t.nav.office },
    { id: "deliberations", label: t.nav.deliberations },
  ];

  const figures = [
    { value: "16", label: t.hero.telemetry.activeAgents },
    { value: "1", label: t.hero.telemetry.sdlcGates },
    { value: "0", label: t.hero.telemetry.routingLatency },
    { value: t.hero.telemetry.enforced, label: t.hero.telemetry.securityStatus },
  ];

  const officeRoles = [
    { tier: t.showcase.office.tier1, role: t.showcase.office.role1, desc: t.showcase.office.role1Desc },
    { tier: t.showcase.office.tier2, role: t.showcase.office.role2, desc: t.showcase.office.role2Desc },
    { tier: t.showcase.office.tier3, role: t.showcase.office.role3, desc: t.showcase.office.role3Desc },
  ];

  const bentoCards = [
    {
      anchor: undefined,
      label: t.bento.card1Badge,
      title: t.bento.card1Title,
      desc: t.bento.card1Desc,
      footer: t.bento.card1Footer,
    },
    {
      anchor: undefined,
      label: t.bento.card2Badge,
      title: t.bento.card2Title,
      desc: t.bento.card2Desc,
      footer: t.bento.card2Footer,
    },
    {
      anchor: undefined,
      label: t.bento.card3Badge,
      title: t.bento.card3Title,
      desc: t.bento.card3Desc,
      footer: t.bento.card3Footer,
    },
    {
      anchor: "deliberations",
      label: t.bento.card4Badge,
      title: t.bento.card4Title,
      desc: t.bento.card4Desc,
      footer: t.bento.card4Footer,
    },
  ];

  const workflowSteps = [
    { num: t.workflow.step1Num, title: t.workflow.step1Title, desc: t.workflow.step1Desc },
    { num: t.workflow.step2Num, title: t.workflow.step2Title, desc: t.workflow.step2Desc },
    { num: t.workflow.step3Num, title: t.workflow.step3Title, desc: t.workflow.step3Desc },
    { num: t.workflow.step4Num, title: t.workflow.step4Title, desc: t.workflow.step4Desc },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground selection:bg-primary/25 selection:text-foreground">
      <a
        href="#main-landing"
        className="sr-only rounded focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      {/* 1. Navigation */}
      <header className="sticky top-0 z-40 border-b border-border bg-background">
        <div className="mx-auto flex h-16 w-full max-w-[1440px] items-center justify-between gap-4 px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary font-mono text-xs text-primary-foreground">
              AV
            </span>
            <span className="truncate text-base leading-tight font-medium">
              avrig<span className="text-accent-text">.ai</span>
            </span>
            <span className="hidden font-mono text-[11px] tabular-nums text-muted-foreground sm:inline">
              v{appVersion}
            </span>
          </div>

          <nav
            className="hidden items-center gap-6 lg:flex"
            aria-label="Landing Navigation"
          >
            {navLinks.map((link) => (
              <button
                key={link.id}
                type="button"
                onClick={() => scrollToSection(link.id)}
                className="rounded text-sm text-text-secondary transition-colors duration-[120ms] ease-out hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                {link.label}
              </button>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <LanguageSelector />
            <ThemeSelector />
            <Button
              variant="ghost"
              size="sm"
              className="hidden sm:inline-flex"
              onClick={() => setLoginModalOpen(true)}
            >
              {t.nav.signIn}
            </Button>
            <Button
              size="sm"
              className="gap-1.5 px-2 sm:px-3"
              onClick={handleLaunchConsole}
            >
              <span className="hidden sm:inline">{t.nav.launchConsole}</span>
              <ArrowRight className="size-4" strokeWidth={1.5} />
            </Button>
          </div>
        </div>
      </header>

      {/* 2. Hero: copy and the gate certificate */}
      <section
        id="main-landing"
        tabIndex={-1}
        className="relative border-b border-border focus:outline-hidden"
      >
        <div className="mx-auto w-full max-w-[1440px] px-6 pt-12 pb-16 lg:px-8 lg:pt-24 lg:pb-20">
          <div className="grid grid-cols-1 gap-12 xl:grid-cols-12 xl:gap-16">
            <div className="xl:col-span-5 lg:flex lg:flex-col lg:justify-center">
              <div className={enter} style={{ transitionDelay: "0ms" }}>
                <p className="font-mono text-xs text-muted-foreground">{t.hero.badge}</p>
                <h1 className="mt-6 text-4xl leading-[1.05] font-medium tracking-tight text-balance sm:text-5xl lg:text-[56px]">
                  {t.hero.titleStart}{" "}
                  <span className="text-accent-text whitespace-nowrap">{t.hero.titleHighlight}</span>{" "}
                  {t.hero.titleEnd}
                </h1>
              </div>

              <div className={`${enter} mt-6`} style={{ transitionDelay: "40ms" }}>
                <p className="max-w-xl text-base leading-relaxed text-text-secondary sm:text-lg">
                  {t.hero.subtitle}
                </p>

                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <Button size="lg" className="gap-2" onClick={handleLaunchConsole}>
                    {t.hero.ctaPrimary}
                    <ArrowRight className="size-4" strokeWidth={1.5} />
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    onClick={() => scrollToSection("sdlc-cockpit")}
                  >
                    {t.hero.ctaSecondary}
                  </Button>
                </div>

                <ul className="mt-10 flex flex-col gap-1.5 border-t border-border pt-4 font-mono text-xs text-muted-foreground">
                  <li>{t.hero.trust.rustEngine}</li>
                  <li>{t.hero.trust.stageGates}</li>
                  <li>{t.hero.trust.traceability}</li>
                </ul>
              </div>
            </div>

            <div
              className={`xl:col-span-7 xl:flex xl:flex-col ${enter}`}
              style={{ transitionDelay: "80ms" }}
            >
              <div className="mb-3 flex items-center justify-between gap-4">
                <span className="font-mono text-xs text-muted-foreground">
                  {t.certificate.inspect}
                </span>
                <div
                  role="group"
                  aria-label={t.certificate.inspect}
                  className="inline-flex items-center gap-1 rounded-lg border border-border p-1"
                >
                  {STAGE_ORDER.map((code) => (
                    <button
                      key={code}
                      type="button"
                      aria-pressed={activeStage === code}
                      onClick={() => setActiveStage(code)}
                      className={`rounded px-2 py-1 font-mono text-xs tabular-nums transition-colors duration-[120ms] ease-out active:scale-[0.99] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                        activeStage === code
                          ? "bg-muted text-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {code}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex flex-1 flex-col rounded-2xl border border-border bg-card p-6 sm:p-8">
                <div className="flex items-baseline justify-between gap-4 border-b border-border pb-4 font-mono text-xs text-muted-foreground tabular-nums">
                  <span className="text-foreground">{stage.code}</span>
                  <span>
                    {stage.index} {t.certificate.stageOf}
                  </span>
                </div>

                <div className="flex items-start justify-between gap-4 pt-4">
                  <h2 className="text-xl leading-snug font-medium text-foreground sm:text-2xl">
                    {stage.name}
                  </h2>
                  <span className="mt-1 flex shrink-0 items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
                    <span
                      className={`size-1.5 rounded-full ${stage.tone}`}
                      aria-hidden="true"
                    />
                    {stage.status}
                  </span>
                </div>

                <ul className="mt-6 space-y-2.5">
                  {stage.checks.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-2.5 text-sm text-text-secondary"
                    >
                      <Check
                        className="mt-0.5 size-3.5 shrink-0 text-positive [stroke-linecap:square]"
                        strokeWidth={1.5}
                        aria-hidden="true"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>

                <dl className="mt-6 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 border-t border-border pt-4 font-mono text-xs tabular-nums">
                  <dt className="text-muted-foreground">{t.certificate.version}</dt>
                  <dd className="text-foreground">v{appVersion}</dd>
                  <dt className="text-muted-foreground">{t.certificate.pin}</dt>
                  <dd className="text-foreground">sha256:unset</dd>
                </dl>

                <div className="mt-auto flex items-center justify-between gap-3 pt-8">
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {stage.approved
                      ? t.certificate.approvalGiven
                      : t.certificate.approvalPending}
                  </span>
                  {stage.approved && (
                    <span className="inline-flex items-center rounded-[4px] border-[1.5px] border-accent-text px-1.5 py-0.5 font-mono text-[10px] leading-none tracking-normal text-accent-text">
                      AVRIG-00002
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-16 grid grid-cols-2 gap-x-8 gap-y-8 border-t border-border pt-8 lg:mt-20 lg:grid-cols-4">
            {figures.map((figure) => (
              <div key={figure.label}>
                <div className="font-mono text-2xl font-medium tabular-nums text-foreground">
                  {figure.value}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">{figure.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 3. Console views */}
      <section
        id="sdlc-cockpit"
        className="scroll-mt-16 border-b border-border bg-muted/20 py-20 lg:py-24"
      >
        <div className="mx-auto w-full max-w-[1440px] px-6 lg:px-8">
          <div className="mb-10 max-w-2xl">
            <p className="font-mono text-xs text-muted-foreground">{t.showcase.badge}</p>
            <h2 className="mt-3 text-[28px] leading-tight font-medium tracking-tight text-balance sm:text-4xl">
              {t.showcase.title}
            </h2>
            <p className="mt-3 text-sm text-text-secondary sm:text-base">
              {t.showcase.subtitle}
            </p>
          </div>

          <Tabs defaultValue="sdlc" className="w-full">
            <TabsList className="mb-6 h-10">
              <TabsTrigger value="sdlc" className="px-2 text-xs sm:px-3 sm:text-sm">
                {t.showcase.tabSdlc}
              </TabsTrigger>
              <TabsTrigger value="office" className="px-2 text-xs sm:px-3 sm:text-sm">
                {t.showcase.tabOffice}
              </TabsTrigger>
              <TabsTrigger value="deliberations" className="px-2 text-xs sm:px-3 sm:text-sm">
                {t.showcase.tabDeliberations}
              </TabsTrigger>
              <TabsTrigger value="knowledge" className="px-2 text-xs sm:px-3 sm:text-sm">
                {t.showcase.tabKnowledge}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="sdlc">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl font-medium">{sdlc.title}</CardTitle>
                  <CardDescription className="leading-relaxed">{sdlc.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {stages.map((item) => (
                      <div
                        key={item.code}
                        className={`flex flex-col gap-2 rounded-xl border bg-background p-4 ${
                          item.current ? "border-accent-text" : "border-border"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 font-mono text-xs tabular-nums">
                          <span className="text-foreground">[{item.code}]</span>
                          <span className="flex items-center gap-1.5 text-muted-foreground">
                            <span
                              className={`size-1.5 rounded-full ${item.tone}`}
                              aria-hidden="true"
                            />
                            {item.status}
                          </span>
                        </div>
                        <div className="text-sm text-text-secondary">{item.name}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
                <div className="border-t border-border px-6 py-4">
                  <span className="text-xs text-muted-foreground">{sdlc.footerText}</span>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="office">
              <Card>
                <CardHeader>
                  <div className="mb-1 font-mono text-xs text-muted-foreground">OG / WF</div>
                  <CardTitle className="text-xl font-medium">
                    {t.showcase.office.title}
                  </CardTitle>
                  <CardDescription className="leading-relaxed">
                    {t.showcase.office.desc}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    {officeRoles.map((role) => (
                      <div key={role.tier} className="rounded-xl border border-border bg-background p-4">
                        <div className="font-mono text-xs text-muted-foreground">{role.tier}</div>
                        <div className="mt-2 text-sm font-medium text-foreground">{role.role}</div>
                        <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                          {role.desc}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
                <div className="border-t border-border px-6 py-4">
                  <span className="text-xs text-muted-foreground">
                    {t.showcase.office.footerText}
                  </span>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="deliberations">
              <Card>
                <CardHeader>
                  <div className="mb-1 flex items-center justify-between font-mono text-xs text-muted-foreground">
                    <span>MT</span>
                    <span className="flex items-center gap-1.5 text-positive">
                      <span className="size-1.5 rounded-full bg-positive" aria-hidden="true" />
                      {t.showcase.deliberations.consensus}
                    </span>
                  </div>
                  <CardTitle className="text-xl font-medium">
                    {t.showcase.deliberations.title}
                  </CardTitle>
                  <CardDescription className="leading-relaxed">
                    {t.showcase.deliberations.desc}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col gap-3 rounded-xl border border-border bg-background p-4">
                    <div className="flex items-center justify-between gap-4 border-b border-border pb-3">
                      <span className="font-mono text-xs text-foreground">#MT-004</span>
                      <span className="font-mono text-xs text-muted-foreground tabular-nums">
                        {t.showcase.deliberations.quorum}
                      </span>
                    </div>
                    <p className="font-mono text-xs text-muted-foreground">
                      {t.showcase.deliberations.transcriptFeed}
                    </p>
                  </div>
                </CardContent>
                <div className="border-t border-border px-6 py-4">
                  <span className="text-xs text-muted-foreground">
                    {t.showcase.deliberations.footerText}
                  </span>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="knowledge">
              <Card>
                <CardHeader>
                  <div className="mb-1 font-mono text-xs text-muted-foreground">
                    AGE, pgvector
                  </div>
                  <CardTitle className="text-xl font-medium">
                    {t.showcase.knowledge.title}
                  </CardTitle>
                  <CardDescription className="leading-relaxed">
                    {t.showcase.knowledge.desc}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="divide-y divide-border border-t border-border">
                    <li className="py-3 text-sm leading-relaxed text-text-secondary">
                      {t.showcase.knowledge.hybridSearch}
                    </li>
                    <li className="py-3 text-sm leading-relaxed text-text-secondary">
                      {t.showcase.knowledge.graphLinks}
                    </li>
                  </ul>
                </CardContent>
                <div className="border-t border-border px-6 py-4">
                  <span className="text-xs text-muted-foreground">
                    {t.showcase.knowledge.footerText}
                  </span>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </section>

      {/* 4. Architecture */}
      <section
        id="architecture"
        className="scroll-mt-16 border-b border-border py-20 lg:py-24"
      >
        <div className="mx-auto w-full max-w-[1440px] px-6 lg:px-8">
          <div className="mb-10 max-w-2xl">
            <p className="font-mono text-xs text-muted-foreground">{t.bento.badge}</p>
            <h2 className="mt-3 text-[28px] leading-tight font-medium tracking-tight text-balance sm:text-4xl">
              {t.bento.title}
            </h2>
            <p className="mt-3 text-sm text-text-secondary sm:text-base">{t.bento.subtitle}</p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {bentoCards.map((card) => (
              <Card key={card.title} id={card.anchor} className="flex scroll-mt-24 flex-col">
                <CardHeader>
                  <div className="font-mono text-xs text-muted-foreground">{card.label}</div>
                  <CardTitle className="mt-2 text-xl font-medium">{card.title}</CardTitle>
                  <CardDescription className="mt-1 leading-relaxed">{card.desc}</CardDescription>
                </CardHeader>
                <div className="mt-auto border-t border-border px-6 py-4">
                  <span className="font-mono text-xs text-muted-foreground">{card.footer}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 5. Workflow */}
      <section
        id="workflow"
        className="scroll-mt-16 border-b border-border bg-muted/20 py-20 lg:py-24"
      >
        <div className="mx-auto w-full max-w-[1440px] px-6 lg:px-8">
          <div className="mb-10 max-w-2xl">
            <p className="font-mono text-xs text-muted-foreground">{t.workflow.badge}</p>
            <h2 className="mt-3 text-[28px] leading-tight font-medium tracking-tight text-balance sm:text-4xl">
              {t.workflow.title}
            </h2>
            <p className="mt-3 text-sm text-text-secondary sm:text-base">
              {t.workflow.subtitle}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
            {workflowSteps.map((step) => (
              <div key={step.num} className="border-t border-border pt-4">
                <span className="font-mono text-2xl font-medium tabular-nums text-muted-foreground">
                  {step.num}
                </span>
                <h3 className="mt-3 text-base font-medium text-foreground">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 6. Call to action */}
      <section className="py-20 lg:py-24">
        <div className="mx-auto w-full max-w-[1440px] px-6 lg:px-8">
          <div className="rounded-2xl border border-border bg-card p-8 sm:p-12">
            <div className="grid gap-8 lg:grid-cols-12 lg:items-end">
              <div className="lg:col-span-7">
                <p className="font-mono text-xs text-muted-foreground">{t.ctaBanner.badge}</p>
                <h2 className="mt-3 text-[28px] leading-tight font-medium tracking-tight text-balance sm:text-4xl">
                  {t.ctaBanner.title}
                </h2>
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-text-secondary sm:text-base">
                  {t.ctaBanner.subtitle}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 lg:col-span-5 lg:justify-end">
                <Button size="lg" className="gap-2" onClick={handleLaunchConsole}>
                  {t.ctaBanner.buttonPrimary}
                  <ArrowRight className="size-4" strokeWidth={1.5} />
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={handleDemoAccess}
                >
                  {t.ctaBanner.buttonSecondary}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Footer */}
      <footer className="mt-auto border-t border-border bg-muted/20 py-8 text-xs text-muted-foreground">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-6 sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-foreground">avrig-ai</span>
            <span className="text-muted-foreground">v{appVersion}</span>
          </div>
          <div className="font-mono tabular-nums">
            &copy; {new Date().getFullYear()} avrig
          </div>
        </div>
      </footer>

      <LoginModal
        open={loginModalOpen}
        onOpenChange={setLoginModalOpen}
        onDemoAccess={handleDemoAccess}
      />
    </div>
  );
};

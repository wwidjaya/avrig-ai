import React, { useState, useEffect } from "react";
import { useAuth } from "react-oidc-context";
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@avrig/ui";
import {
  ShieldCheck,
  Building2,
  Kanban,
  Users,
  Lock,
  ArrowRight,
  Activity,
  Cpu,
  Workflow,
  Sparkles,
  CheckCircle2,
  Layers,
  Network,
  Radio,
  FileCheck2,
} from "lucide-react";
import { useI18n } from "../../shared/i18n/I18nContext";
import { ThemeSelector } from "../../shared/components/ThemeSelector";
import { LanguageSelector } from "../../shared/components/LanguageSelector";
import { LoginModal } from "./LoginModal";

interface LandingPageProps {
  onEnterCommandCenter: (targetPath?: string) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterCommandCenter }) => {
  const auth = useAuth();
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const { t } = useI18n();

  // Active simulated stage in the hero interactive rig
  const [activeStage, setActiveStage] = useState<"RE" | "SA" | "DV" | "TE">("RE");

  // Simulated ticker time
  const [tickerIndex, setTickerIndex] = useState(0);
  const tickerEvents = [
    "[GATE_PASS] Stage [RE] signed by Human Founder (SHA-256: 7f83b165...)",
    "[CONSENSUS] Architecture Deliberation #004: Unanimous 4/4 Quorum",
    "[EVENT_BUS] Dispatching task packet to Specialist Agent #012 [DV]",
    "[RBAC_OK] OAuth 2.1 PKCE token validated via iam.avrig.ai",
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setTickerIndex((prev) => (prev + 1) % tickerEvents.length);
    }, 3800);
    return () => clearInterval(timer);
  }, [tickerEvents.length]);

  const isLoggedIn = Boolean(
    auth.isAuthenticated ||
    auth.user ||
    (typeof window !== "undefined" && localStorage.getItem("avrig-logged-in") === "true")
  );

  const handleLaunchConsole = async () => {
    if (isLoggedIn) {
      onEnterCommandCenter();
    } else {
      try {
        await auth.signinRedirect();
      } catch (err) {
        console.error("OpenID Connect redirect failed", err);
        setLoginModalOpen(true);
      }
    }
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/20 selection:text-primary transition-colors duration-300">
      {/* Accessible Skip Link */}
      <a
        href="#main-landing"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg focus:outline-hidden"
      >
        Skip to main content
      </a>

      {/* 1. Industrial Hairline Navigation Bar */}
      <header className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/90 backdrop-blur-md">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="flex size-9 items-center justify-center rounded bg-primary text-primary-foreground font-mono font-black tracking-wider text-sm shadow-xs">
              AV
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base leading-tight tracking-tight">
                  avrig<span className="text-primary font-mono ml-0.5">.ai</span>
                </span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded font-mono text-[9px] uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
                  <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  RIG.V1
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground font-mono tracking-widest uppercase">
                Autonomous Engineering Rig
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-7 text-xs font-mono font-medium text-muted-foreground" aria-label="Landing Navigation">
            <button
              type="button"
              onClick={() => scrollToSection("sdlc-cockpit")}
              className="hover:text-foreground transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden rounded px-1.5 py-0.5"
            >
              <span className="text-primary font-bold mr-1">01.</span>{t.nav.sdlc}
            </button>
            <button
              type="button"
              onClick={() => scrollToSection("architecture")}
              className="hover:text-foreground transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden rounded px-1.5 py-0.5"
            >
              <span className="text-primary font-bold mr-1">02.</span>{t.nav.architecture}
            </button>
            <button
              type="button"
              onClick={() => scrollToSection("workflow")}
              className="hover:text-foreground transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden rounded px-1.5 py-0.5"
            >
              <span className="text-primary font-bold mr-1">03.</span>{t.nav.office}
            </button>
            <button
              type="button"
              onClick={() => scrollToSection("deliberations")}
              className="hover:text-foreground transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-hidden rounded px-1.5 py-0.5"
            >
              <span className="text-primary font-bold mr-1">04.</span>{t.nav.deliberations}
            </button>
          </nav>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Language Selector */}
            <LanguageSelector />

            {/* 3-Way Theme Selector */}
            <ThemeSelector />

            {/* Console CTA */}
            <Button
              size="sm"
              className="font-mono text-xs font-semibold shadow-xs cursor-pointer gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/95 ring-1 ring-primary/20"
              onClick={handleLaunchConsole}
            >
              <span>{t.nav.launchConsole}</span>
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* 2. Asymmetric Hero Composition ("The Sovereign Rig") */}
      <section id="main-landing" tabIndex={-1} className="relative overflow-hidden pt-12 pb-16 lg:pt-20 lg:pb-24 border-b border-border/80 focus:outline-hidden">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
            {/* Left 7 Columns: Rig Manifest & Command Directives */}
            <div className="lg:col-span-7 flex flex-col items-start text-left">
              <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 font-mono text-xs font-medium border-l-2 border-primary bg-primary/5 text-primary border-y border-r border-border/60">
                <Sparkles className="size-3.5 text-primary" />
                <span className="uppercase tracking-widest">{t.hero.badge}</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.06] mb-6">
                {t.hero.titleStart}{" "}
                <span className="bg-gradient-to-r from-primary via-primary/90 to-foreground bg-clip-text text-transparent">
                  {t.hero.titleHighlight}
                </span>{" "}
                {t.hero.titleEnd}
              </h1>

              <p className="text-base sm:text-lg text-muted-foreground leading-relaxed mb-8 max-w-2xl font-normal">
                {t.hero.subtitle}
              </p>

              <div className="flex flex-wrap items-center gap-4 mb-8">
                <Button
                  size="lg"
                  className="gap-2 font-semibold shadow-sm cursor-pointer"
                  onClick={handleLaunchConsole}
                >
                  {t.hero.ctaPrimary}
                  <ArrowRight className="size-4" />
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="font-semibold cursor-pointer"
                  onClick={() => scrollToSection("sdlc-cockpit")}
                >
                  {t.hero.ctaSecondary}
                </Button>
              </div>

              {/* Technical Trust Strip */}
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-mono text-muted-foreground pt-4 border-t border-border/60 w-full">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-3.5 text-primary" />
                  <span>{t.hero.trust.rustEngine}</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-3.5 text-primary" />
                  <span>{t.hero.trust.stageGates}</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-3.5 text-primary" />
                  <span>{t.hero.trust.traceability}</span>
                </div>
              </div>
            </div>

            {/* Right 5 Columns: Interactive Sovereign Rig Terminal Simulator */}
            <div className="lg:col-span-5 w-full">
              <div className="rounded-xl border border-border bg-card/95 shadow-2xl overflow-hidden">
                {/* Terminal Header */}
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-muted/40 font-mono text-xs">
                  <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-destructive/70 inline-block"></span>
                    <span className="size-2.5 rounded-full bg-amber-500/70 inline-block"></span>
                    <span className="size-2.5 rounded-full bg-emerald-500 inline-block"></span>
                    <span className="text-[11px] text-muted-foreground ml-1">avrig-rig://cluster-01.local</span>
                  </div>
                  <Badge variant="outline" className="font-mono text-[10px] px-1.5 py-0">
                    STATUS: ONLINE
                  </Badge>
                </div>

                {/* Terminal Content: Interactive Stage Inspector */}
                <div className="p-4 sm:p-5 flex flex-col gap-4 font-mono text-xs">
                  <div className="flex items-center justify-between text-muted-foreground pb-2 border-b border-border/60 text-[11px]">
                    <span>CANONICAL SDLC GATE INSPECTOR</span>
                    <span className="text-primary font-bold">16 INVARIANTS ACTIVE</span>
                  </div>

                  {/* Stage Switcher Buttons */}
                  <div className="grid grid-cols-4 gap-1.5">
                    {(["RE", "SA", "DV", "TE"] as const).map((code) => {
                      const isActive = activeStage === code;
                      return (
                        <button
                          key={code}
                          onClick={() => setActiveStage(code)}
                          className={`p-2 rounded border text-center transition-all cursor-pointer ${
                            isActive
                              ? "bg-primary text-primary-foreground border-primary font-bold shadow-xs"
                              : "bg-muted/40 text-muted-foreground border-border hover:bg-muted"
                          }`}
                        >
                          <div className="text-[10px] opacity-70">STAGE</div>
                          <div className="text-sm tracking-wider font-bold">[{code}]</div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Stage Detail Box */}
                  <div className="rounded-lg border border-border/80 bg-background/80 p-3.5 flex flex-col gap-2">
                    {activeStage === "RE" && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-foreground">[RE] Requirements Engineering</span>
                          <Badge variant="success" className="text-[10px]">GATE VERIFIED</Badge>
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Baseline: <code className="text-primary">sha256:7f83b165...</code> signed by Founder. Invariant test: 12 user stories, 0 unmapped requirements.
                        </p>
                      </>
                    )}
                    {activeStage === "SA" && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-foreground">[SA] System Architecture</span>
                          <Badge variant="success" className="text-[10px]">GATE VERIFIED</Badge>
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Baseline: <code className="text-primary">sha256:3a91c01e...</code> signed. Topology contracts, database schema, and micro-role boundaries locked.
                        </p>
                      </>
                    )}
                    {activeStage === "DV" && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-foreground">[DV] Development Engineering</span>
                          <Badge variant="default" className="text-[10px]">ACTIVE COMPILATION</Badge>
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Rust Axum core building with cargo-clippy 0 warnings. Automated git commit signed via GPG key `agent-012`.
                        </p>
                      </>
                    )}
                    {activeStage === "TE" && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-foreground">[TE] Test & Verification</span>
                          <Badge variant="outline" className="text-[10px]">SCHEDULED</Badge>
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Integration test harness ready: 48 automated test cases, mock OIDC assertion check, WebSocket telemetry loop.
                        </p>
                      </>
                    )}
                  </div>

                  {/* Live WebSocket Event Ticker */}
                  <div className="pt-2 border-t border-border/60">
                    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-1">
                      <Radio className="size-3 text-emerald-500 animate-pulse" />
                      <span>GATEWAY EVENT BUS STREAM:</span>
                    </div>
                    <div className="bg-muted/50 rounded px-2.5 py-1.5 text-[10px] text-foreground truncate font-mono">
                      {tickerEvents[tickerIndex]}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Telemetry Strip under Hero */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-7xl mx-auto pt-10 text-left">
            <Card className="bg-card/60 border-border">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-mono uppercase tracking-wider">{t.hero.telemetry.activeAgents}</span>
                  <Users className="size-4 text-primary" />
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="text-2xl font-bold font-mono">14 Agents</div>
              </CardContent>
            </Card>

            <Card className="bg-card/60 border-border">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-mono uppercase tracking-wider">{t.hero.telemetry.sdlcGates}</span>
                  <Workflow className="size-4 text-primary" />
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="text-2xl font-bold font-mono">16 / 16 Invariant</div>
              </CardContent>
            </Card>

            <Card className="bg-card/60 border-border">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-mono uppercase tracking-wider">{t.hero.telemetry.routingLatency}</span>
                  <Cpu className="size-4 text-primary" />
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="text-2xl font-bold font-mono">&lt; 15 ms</div>
              </CardContent>
            </Card>

            <Card className="bg-card/60 border-border">
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-mono uppercase tracking-wider">{t.hero.telemetry.securityStatus}</span>
                  <Lock className="size-4 text-primary" />
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="text-2xl font-bold font-mono text-primary">{t.hero.telemetry.enforced}</div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* 3. The Dual-Engine Cockpit (Interactive Tabs Showcase) */}
      <section id="sdlc-cockpit" className="py-20 lg:py-24 bg-muted/20 border-b border-border scroll-mt-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <Badge variant="outline" className="gap-2 px-3 py-1 text-xs font-mono mb-3">
              <Layers className="size-3.5 text-primary" />
              <span>{t.showcase.badge}</span>
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">
              {t.showcase.title}
            </h2>
            <p className="text-muted-foreground text-sm sm:text-base">
              {t.showcase.subtitle}
            </p>
          </div>

          <Tabs defaultValue="sdlc" className="w-full">
            <div className="flex justify-center mb-8">
              <TabsList className="h-11 p-1 bg-card border border-border">
                <TabsTrigger value="sdlc" className="font-mono text-xs sm:text-sm cursor-pointer gap-2">
                  <Kanban className="size-4" />
                  <span>{t.showcase.tabSdlc}</span>
                </TabsTrigger>
                <TabsTrigger value="office" className="font-mono text-xs sm:text-sm cursor-pointer gap-2">
                  <Building2 className="size-4" />
                  <span>{t.showcase.tabOffice}</span>
                </TabsTrigger>
                <TabsTrigger value="deliberations" className="font-mono text-xs sm:text-sm cursor-pointer gap-2">
                  <Radio className="size-4" />
                  <span>{t.showcase.tabDeliberations}</span>
                </TabsTrigger>
                <TabsTrigger value="knowledge" className="font-mono text-xs sm:text-sm cursor-pointer gap-2">
                  <Network className="size-4" />
                  <span>{t.showcase.tabKnowledge}</span>
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Tab 1: SDLC Board Showcase */}
            <TabsContent value="sdlc">
              <Card className="bg-card border-border shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary" className="gap-1.5 font-mono text-xs">
                      <Kanban className="size-3.5 text-primary" />
                      <span>RE-TE Canonical Engine</span>
                    </Badge>
                    <span className="text-xs font-mono text-muted-foreground">SHA-256 Gate Checklists</span>
                  </div>
                  <CardTitle className="text-xl font-bold">{t.showcase.sdlc.title}</CardTitle>
                  <CardDescription className="text-sm leading-relaxed">{t.showcase.sdlc.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 my-2">
                    <div className="p-3.5 rounded-lg border border-border bg-background flex flex-col justify-between">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-primary">{t.showcase.sdlc.item1Code}</span>
                        <Badge variant="success" className="text-[10px] py-0 px-1.5">{t.showcase.sdlc.item1Status}</Badge>
                      </div>
                      <div className="text-xs font-semibold">{t.showcase.sdlc.item1Name}</div>
                    </div>
                    <div className="p-3.5 rounded-lg border border-border bg-background flex flex-col justify-between">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-primary">{t.showcase.sdlc.item2Code}</span>
                        <Badge variant="success" className="text-[10px] py-0 px-1.5">{t.showcase.sdlc.item2Status}</Badge>
                      </div>
                      <div className="text-xs font-semibold">{t.showcase.sdlc.item2Name}</div>
                    </div>
                    <div className="p-3.5 rounded-lg border border-primary/40 bg-primary/5 flex flex-col justify-between">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-primary">{t.showcase.sdlc.item3Code}</span>
                        <Badge variant="default" className="text-[10px] py-0 px-1.5">{t.showcase.sdlc.item3Status}</Badge>
                      </div>
                      <div className="text-xs font-semibold">{t.showcase.sdlc.item3Name}</div>
                    </div>
                    <div className="p-3.5 rounded-lg border border-border bg-background flex flex-col justify-between opacity-80">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold text-muted-foreground">{t.showcase.sdlc.item4Code}</span>
                        <Badge variant="outline" className="text-[10px] py-0 px-1.5 text-muted-foreground">{t.showcase.sdlc.item4Status}</Badge>
                      </div>
                      <div className="text-xs font-semibold text-muted-foreground">{t.showcase.sdlc.item4Name}</div>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground flex items-center gap-2">
                  <Activity className="size-3.5 text-primary" />
                  <span>{t.showcase.sdlc.footerText}</span>
                </CardFooter>
              </Card>
            </TabsContent>

            {/* Tab 2: Office OS Showcase */}
            <TabsContent value="office">
              <Card className="bg-card border-border shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary" className="gap-1.5 font-mono text-xs">
                      <Building2 className="size-3.5 text-primary" />
                      <span>OG / WF Subsystem</span>
                    </Badge>
                    <span className="text-xs font-mono text-muted-foreground">Persistent Identity</span>
                  </div>
                  <CardTitle className="text-xl font-bold">{t.showcase.office.title}</CardTitle>
                  <CardDescription className="text-sm leading-relaxed">{t.showcase.office.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-2">
                    <div className="p-4 rounded-lg border border-border bg-background">
                      <Badge variant="outline" className="mb-2 text-[10px]">Tier 2: Executive</Badge>
                      <div className="font-bold text-sm mb-1">{t.showcase.office.role1}</div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{t.showcase.office.role1Desc}</p>
                    </div>
                    <div className="p-4 rounded-lg border border-border bg-background">
                      <Badge variant="outline" className="mb-2 text-[10px]">Tier 3: Operational</Badge>
                      <div className="font-bold text-sm mb-1">{t.showcase.office.role2}</div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{t.showcase.office.role2Desc}</p>
                    </div>
                    <div className="p-4 rounded-lg border border-border bg-background">
                      <Badge variant="outline" className="mb-2 text-[10px]">Tier 4: Specialist</Badge>
                      <div className="font-bold text-sm mb-1">{t.showcase.office.role3}</div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{t.showcase.office.role3Desc}</p>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground flex items-center gap-2">
                  <ShieldCheck className="size-3.5 text-primary" />
                  <span>{t.showcase.office.footerText}</span>
                </CardFooter>
              </Card>
            </TabsContent>

            {/* Tab 3: Deliberations Showcase */}
            <TabsContent value="deliberations">
              <Card className="bg-card border-border shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary" className="gap-1.5 font-mono text-xs">
                      <Radio className="size-3.5 text-primary animate-pulse" />
                      <span>Live WebSocket Stream</span>
                    </Badge>
                    <span className="text-xs font-mono text-emerald-500 font-semibold">{t.showcase.deliberations.consensus}</span>
                  </div>
                  <CardTitle className="text-xl font-bold">{t.showcase.deliberations.title}</CardTitle>
                  <CardDescription className="text-sm leading-relaxed">{t.showcase.deliberations.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="p-4 rounded-lg border border-border bg-background flex flex-col gap-3 my-2">
                    <div className="flex items-center justify-between border-b border-border/60 pb-2">
                      <span className="text-xs font-mono font-bold text-primary">#MT-004: Architecture Sign-Off Deliberation</span>
                      <Badge variant="outline" className="text-[10px]">{t.showcase.deliberations.quorum}</Badge>
                    </div>
                    <div className="text-xs font-mono text-muted-foreground flex items-center gap-2">
                      <span className="size-2 rounded-full bg-emerald-500 animate-ping"></span>
                      <span>{t.showcase.deliberations.transcriptFeed}</span>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground flex items-center gap-2">
                  <FileCheck2 className="size-3.5 text-primary" />
                  <span>{t.showcase.deliberations.footerText}</span>
                </CardFooter>
              </Card>
            </TabsContent>

            {/* Tab 4: Knowledge Graph Showcase */}
            <TabsContent value="knowledge">
              <Card className="bg-card border-border shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary" className="gap-1.5 font-mono text-xs">
                      <Network className="size-3.5 text-primary" />
                      <span>Apache AGE + pgvector</span>
                    </Badge>
                    <span className="text-xs font-mono text-muted-foreground">Epistemic Recall</span>
                  </div>
                  <CardTitle className="text-xl font-bold">{t.showcase.knowledge.title}</CardTitle>
                  <CardDescription className="text-sm leading-relaxed">{t.showcase.knowledge.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-2">
                    <div className="p-4 rounded-lg border border-border bg-background">
                      <div className="text-xs font-bold text-primary mb-1">Vector Search (Dense Embeddings)</div>
                      <p className="text-xs text-muted-foreground">{t.showcase.knowledge.hybridSearch}</p>
                    </div>
                    <div className="p-4 rounded-lg border border-border bg-background">
                      <div className="text-xs font-bold text-primary mb-1">Graph Network Traversals</div>
                      <p className="text-xs text-muted-foreground">{t.showcase.knowledge.graphLinks}</p>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground flex items-center gap-2">
                  <Cpu className="size-3.5 text-primary" />
                  <span>{t.showcase.knowledge.footerText}</span>
                </CardFooter>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </section>

      {/* 4. Bento Architecture Section */}
      <section id="architecture" className="py-20 lg:py-24 border-b border-border scroll-mt-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <Badge variant="outline" className="gap-2 px-3 py-1 text-xs font-mono mb-3">
              <Cpu className="size-3.5 text-primary" />
              <span>{t.bento.badge}</span>
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">
              {t.bento.title}
            </h2>
            <p className="text-muted-foreground text-sm sm:text-base">
              {t.bento.subtitle}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Bento Card 1: 4-Tier Hierarchy */}
            <Card className="flex flex-col justify-between bg-card transition-all hover:border-primary/50">
              <CardHeader>
                <div className="flex items-center justify-between mb-3">
                  <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                    <Building2 className="size-5" />
                  </div>
                  <Badge variant="outline" className="font-mono text-[10px]">{t.bento.card1Badge}</Badge>
                </div>
                <CardTitle className="text-xl font-bold">{t.bento.card1Title}</CardTitle>
                <CardDescription className="text-sm leading-relaxed mt-2">
                  {t.bento.card1Desc}
                </CardDescription>
              </CardHeader>
              <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground">
                Human Sovereignty &bull; Delegated Authority
              </CardFooter>
            </Card>

            {/* Bento Card 2: Cryptographic Invariance */}
            <Card className="flex flex-col justify-between bg-card transition-all hover:border-primary/50">
              <CardHeader>
                <div className="flex items-center justify-between mb-3">
                  <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                    <ShieldCheck className="size-5" />
                  </div>
                  <Badge variant="outline" className="font-mono text-[10px]">{t.bento.card2Badge}</Badge>
                </div>
                <CardTitle className="text-xl font-bold">{t.bento.card2Title}</CardTitle>
                <CardDescription className="text-sm leading-relaxed mt-2">
                  {t.bento.card2Desc}
                </CardDescription>
              </CardHeader>
              <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground">
                SHA-256 Gate Checklists &bull; Immutable History
              </CardFooter>
            </Card>

            {/* Bento Card 3: Rust Event Bus */}
            <Card className="flex flex-col justify-between bg-card transition-all hover:border-primary/50">
              <CardHeader>
                <div className="flex items-center justify-between mb-3">
                  <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                    <Cpu className="size-5" />
                  </div>
                  <Badge variant="outline" className="font-mono text-[10px]">{t.bento.card3Badge}</Badge>
                </div>
                <CardTitle className="text-xl font-bold">{t.bento.card3Title}</CardTitle>
                <CardDescription className="text-sm leading-relaxed mt-2">
                  {t.bento.card3Desc}
                </CardDescription>
              </CardHeader>
              <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground">
                Axum Micro-Services &bull; Multi-Role Runtime
              </CardFooter>
            </Card>

            {/* Bento Card 4: Universal OIDC */}
            <Card id="deliberations" className="flex flex-col justify-between bg-card transition-all hover:border-primary/50 scroll-mt-24">
              <CardHeader>
                <div className="flex items-center justify-between mb-3">
                  <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                    <Lock className="size-5" />
                  </div>
                  <Badge variant="outline" className="font-mono text-[10px]">{t.bento.card4Badge}</Badge>
                </div>
                <CardTitle className="text-xl font-bold">{t.bento.card4Title}</CardTitle>
                <CardDescription className="text-sm leading-relaxed mt-2">
                  {t.bento.card4Desc}
                </CardDescription>
              </CardHeader>
              <CardFooter className="border-t border-border/60 pt-4 text-xs font-mono text-muted-foreground">
                Rauthy &bull; Keycloak &bull; Authentik Ready
              </CardFooter>
            </Card>
          </div>
        </div>
      </section>

      {/* 5. Autonomous Workflow Sequence */}
      <section id="workflow" className="py-20 lg:py-24 bg-muted/20 border-b border-border scroll-mt-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <Badge variant="outline" className="gap-2 px-3 py-1 text-xs font-mono mb-3">
              <Workflow className="size-3.5 text-primary" />
              <span>{t.workflow.badge}</span>
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">
              {t.workflow.title}
            </h2>
            <p className="text-muted-foreground text-sm sm:text-base">
              {t.workflow.subtitle}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-5 rounded-xl border border-border bg-card flex flex-col justify-between">
              <div>
                <span className="font-mono text-3xl font-black text-primary/40 block mb-3">{t.workflow.step1Num}</span>
                <h3 className="font-bold text-base mb-2">{t.workflow.step1Title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{t.workflow.step1Desc}</p>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-border bg-card flex flex-col justify-between">
              <div>
                <span className="font-mono text-3xl font-black text-primary/40 block mb-3">{t.workflow.step2Num}</span>
                <h3 className="font-bold text-base mb-2">{t.workflow.step2Title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{t.workflow.step2Desc}</p>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-border bg-card flex flex-col justify-between">
              <div>
                <span className="font-mono text-3xl font-black text-primary/40 block mb-3">{t.workflow.step3Num}</span>
                <h3 className="font-bold text-base mb-2">{t.workflow.step3Title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{t.workflow.step3Desc}</p>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-border bg-card flex flex-col justify-between">
              <div>
                <span className="font-mono text-3xl font-black text-primary/40 block mb-3">{t.workflow.step4Num}</span>
                <h3 className="font-bold text-base mb-2">{t.workflow.step4Title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{t.workflow.step4Desc}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Call to Action Banner */}
      <section className="py-20 lg:py-24">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-4xl text-center">
          <div className="rounded-2xl border border-primary/30 bg-gradient-to-b from-primary/10 to-background p-8 sm:p-12 shadow-xl">
            <Badge variant="outline" className="gap-2 px-3 py-1 text-xs font-mono mb-4">
              <Sparkles className="size-3.5 text-primary" />
              <span>{t.ctaBanner.badge}</span>
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-4">
              {t.ctaBanner.title}
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto mb-8 leading-relaxed">
              {t.ctaBanner.subtitle}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <Button
                size="lg"
                className="gap-2 font-semibold shadow-md cursor-pointer"
                onClick={handleLaunchConsole}
              >
                {t.ctaBanner.buttonPrimary}
                <ArrowRight className="size-4" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="font-semibold cursor-pointer"
                onClick={() => scrollToSection("sdlc-cockpit")}
              >
                {t.ctaBanner.buttonSecondary}
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Footer */}
      <footer className="mt-auto border-t border-border py-8 bg-muted/20 text-xs text-muted-foreground">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-foreground">avrig-ai</span>
            <span>— Sovereign AI Autonomous Engineering Organization Platform</span>
          </div>
          <div>© {new Date().getFullYear()} avrig. All rights reserved.</div>
        </div>
      </footer>

      {/* Login Dialog */}
      <LoginModal
        open={loginModalOpen}
        onOpenChange={setLoginModalOpen}
        onDemoAccess={() => {
          setLoginModalOpen(false);
          onEnterCommandCenter();
        }}
      />
    </div>
  );
};

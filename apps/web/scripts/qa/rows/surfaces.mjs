// The per-surface rows: style (ST), state adoption (SC-07), seal census (SC-08),
// font cascade (SC-09), token resolution (TK-03), version badge (CP-01), pill
// census (PIL-01), and the console/network reconciliation (BR-04).
//
// One render of each of the 14 surfaces feeds all of them. Re-measuring per row
// would multiply the render count by thirteen for no extra evidence.
import fs from "node:fs";
import path from "node:path";
import {
  ROUTES,
  THEMES,
  routeName,
  openSurface,
  gotoSurface,
  measureSurface,
  firstFamily,
  screenshot
} from "../lib/browser.mjs";
import { row, writeJson } from "../lib/harness.mjs";
import { parseLocale } from "./i18n.mjs";

export const ids = [
  "ST-01",
  "ST-02",
  "ST-03",
  "ST-04",
  "ST-05",
  "ST-06",
  "SC-07",
  "SC-08",
  "SC-09",
  "TK-03",
  "CP-01",
  "PIL-01",
  "BR-04"
];

// TK-03. The token layer writes HSL triplets into :root and maps them to
// utilities through @theme inline, which means no --color-* custom property is
// emitted to the DOM. The six new tokens are therefore read twice: as the
// triplet, and as the computed colour of the utility each one feeds.
export const NEW_TOKENS = [
  { triplet: "--accent-text", color: "--color-accent-text", utility: "text-accent-text", property: "color" },
  { triplet: "--positive", color: "--color-positive", utility: "text-positive", property: "color" },
  { triplet: "--negative", color: "--color-negative", utility: "text-negative", property: "color" },
  { triplet: "--warning", color: "--color-warning", utility: "text-warning", property: "color" },
  { triplet: "--text-secondary", color: "--color-text-secondary", utility: "text-text-secondary", property: "color" },
  { triplet: "--border", color: "--color-border", utility: "border-border", property: "borderTopColor" }
];

const TRIPLET = /^(\d{1,3}) (\d{1,3})% (\d{1,3})%$/;

export function hslTripletToRgb(triplet) {
  const match = TRIPLET.exec(String(triplet).trim());
  if (!match) return null;
  const h = Number(match[1]) / 360;
  const s = Number(match[2]) / 100;
  const l = Number(match[3]) / 100;
  const hue = (p, q, t) => {
    let value = t;
    if (value < 0) value += 1;
    if (value > 1) value -= 1;
    if (value < 1 / 6) return p + (q - p) * 6 * value;
    if (value < 1 / 2) return q;
    if (value < 2 / 3) return p + (q - p) * (2 / 3 - value) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return {
    r: Math.round(hue(p, q, h + 1 / 3) * 255),
    g: Math.round(hue(p, q, h) * 255),
    b: Math.round(hue(p, q, h - 1 / 3) * 255)
  };
}

function parseRgb(value) {
  const match = /rgba?\(([^)]+)\)/.exec(String(value || ""));
  if (!match) return null;
  const parts = match[1]
    .split(/[,\s/]+/)
    .filter(Boolean)
    .map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) return null;
  return { r: parts[0], g: parts[1], b: parts[2] };
}

// BR-04. Every entry names what is being tolerated and why. Anything that is
// not in this list fails the row with its own text.
const CONSOLE_EXCLUSIONS = [
  {
    id: "ws-production-host",
    reason:
      "loadConfig rewrites wsBaseUrl to the production host only when the origin contains app.avrig.ai, so a local harness origin dials the real wss endpoint and cannot complete a handshake. The constructed URL is asserted deterministically in BR-04(a); this entry covers only the handshake that follows it.",
    matches: (text) => /WebSocket connection to 'wss:\/\/app\.avrig\.ai\/ws\/command-center/.test(text)
  },
  {
    id: "absent-backend",
    reason: "no backend is running behind the dev server's /api proxy; a 4xx/5xx or a refused connection there is the expected state for a UI-only run",
    matches: (text) => /\/api\//.test(text) && /(Failed to load resource|net::ERR_|ECONNREFUSED|status of (401|404|500|502|503|504))/.test(text)
  }
];

function classifyConsole(entry) {
  for (const exclusion of CONSOLE_EXCLUSIONS) {
    if (exclusion.matches(entry.text)) return exclusion.id;
  }
  return null;
}

function classifyRequest(entry) {
  if (/\/api\//.test(entry.url)) return "absent-backend";
  return null;
}

function classifyResponse(entry) {
  if (/\/api\//.test(entry.url)) return "absent-backend";
  return null;
}

async function localeReadBack(ctx) {
  const source = fs.readFileSync(path.join(ctx.repo, "apps/web/src/shared/i18n/translations.ts"), "utf8");
  const expected = {
    en: parseLocale(source, "\n  en: {")["hero.badge"],
    id: parseLocale(source, "\n  id: {")["hero.badge"]
  };
  const readBacks = [];
  for (const lang of ["en", "id"]) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, lang, width: 1440, height: 900 });
      try {
        await gotoSurface(page, ctx.base, "/", theme);
        const rendered = await page.evaluate(() => {
          const first = document.querySelector("#main-landing p");
          return {
            text: first ? first.textContent.trim() : null,
            langAttribute: document.documentElement.getAttribute("lang"),
            storedLang: localStorage.getItem("avrig-lang")
          };
        });
        readBacks.push({
          requested: { lang, theme },
          rendered,
          expected: expected[lang],
          agrees: rendered.text === expected[lang]
        });
      } finally {
        await context.close();
      }
    }
  }
  return readBacks;
}

export async function run(ctx) {
  const surfaces = [];
  const consoleNetwork = [];
  let configWsBase = null;

  for (const route of ROUTES) {
    for (const theme of THEMES) {
      const { context, page, record } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
      try {
        const adopted = await gotoSurface(page, ctx.base, route, theme);
        const measured = await measureSurface(page, { route, theme, width: 1440, height: 900 });
        measured.adopted = adopted;
        measured.browser = record;

        const socketUrls = await page.evaluate(() => (window.__qaWsUrls || []).slice());
        measured.webSockets = socketUrls;

        if (configWsBase === null) {
          configWsBase = await page
            .evaluate(async () => {
              try {
                const response = await fetch("/config.json", { cache: "no-store" });
                if (!response.ok) return null;
                const body = await response.json();
                return body.wsBaseUrl ?? null;
              } catch {
                return null;
              }
            })
            .catch(() => null);
        }

        await screenshot(page, ctx.evidence, `${routeName(route)}-${theme}-1440.png`, { fullPage: true });
        await page.setViewportSize({ width: 390, height: 844 });
        await page.waitForFunction(() => window.innerWidth === 390, null, { timeout: 5000 }).catch(() => {});
        await screenshot(page, ctx.evidence, `${routeName(route)}-${theme}-390.png`, { fullPage: true });

        writeJson(ctx.evidence, `style-${theme}-${routeName(route)}.json`, {
          meta: measured.meta,
          adopted: measured.adopted,
          isDark: measured.isDark,
          colorScheme: measured.colorScheme,
          weight: measured.weight,
          gradient: measured.gradient,
          cliptext: measured.cliptext,
          motion: measured.motion,
          motionCandidateCount: measured.motionCandidateCount,
          transitionAll: measured.transitionAll,
          shadows: measured.shadows,
          emoji: measured.emoji,
          uppercase: measured.uppercase,
          overflow: measured.overflow
        });

        surfaces.push(measured);
        consoleNetwork.push({
          route,
          theme,
          consoleErrors: record.consoleErrors,
          pageErrors: record.pageErrors,
          failedRequests: record.failedRequests,
          responses: record.responses,
          webSockets: socketUrls
        });
      } finally {
        await context.close();
      }
    }
  }

  writeJson(ctx.evidence, "surfaces.json", surfaces);

  const results = [];
  const sum = (list) => list.reduce((total, s) => total + s.length, 0);
  const surfacesWith = (key) => surfaces.filter((s) => s[key].length > 0).length;
  const surfaceCount = surfaces.length;

  // ---- ST-01 to ST-06 ----
  const gradients = sum(surfaces.map((s) => s.gradient));
  results.push(row("ST-01", gradients === 0, `${gradients} elements with a gradient backgroundImage across ${surfaceCount} surfaces`));

  const cliptext = sum(surfaces.map((s) => s.cliptext));
  results.push(row("ST-02", cliptext === 0, `${cliptext} elements combining bg-clip-text with a transparent fill`));

  const maxWeight = surfaces.reduce((max, s) => Math.max(max, s.weight.max), 0);
  const weightOffenders = surfaces.flatMap((s) => s.weight.offenders.map((o) => `${s.meta.route}/${s.meta.theme} ${o.tag} ${o.w}`));
  results.push(
    row("ST-03", maxWeight <= 600 && weightOffenders.length === 0, `maximum computed font-weight ${maxWeight} across ${surfaceCount} surfaces, ${weightOffenders.length} above 600`)
  );

  const motion = sum(surfaces.map((s) => s.motion));
  results.push(row("ST-04", motion === 0, `${motion} elements animating pulse/spin/ping/bounce outside a live-status ancestor`));

  const transitionAll = sum(surfaces.map((s) => s.transitionAll));
  results.push(row("ST-05", transitionAll === 0, `${transitionAll} elements transitioning 'all' with a non-zero duration`));

  const shadows = sum(surfaces.map((s) => s.shadows));
  const emoji = sum(surfaces.map((s) => s.emoji));
  const uppercase = sum(surfaces.map((s) => s.uppercase));
  results.push(
    row("ST-06", shadows === 0 && emoji === 0 && uppercase === 0, `${shadows} saturated shadows with blur, ${emoji} emoji in rendered text, ${uppercase} uppercase tracked labels`)
  );

  // ---- SC-07 ----
  const localeReads = await localeReadBack(ctx);
  writeJson(ctx.evidence, "state-adopted.json", {
    note:
      "Theme is read from documentElement.classList and style.colorScheme, locale from a rendered landing string (documentElement.lang is never written by I18nContext), auth from the element id main-viewport, viewport from window.innerWidth/innerHeight. Every read happens before the assertion that depends on it.",
    locale: localeReads,
    surfaces: surfaces.map((s) => ({
      route: s.meta.route,
      theme: s.meta.theme,
      isDark: s.isDark,
      colorScheme: s.colorScheme,
      adoptedDark: s.adoptedDark,
      viewport: s.viewport,
      mainLanding: s.mainLanding,
      mainViewportId: s.mainViewportId,
      mainViewportTestId: s.mainViewportTestId,
      storage: s.storage,
      adopted: s.adopted
    }))
  });

  const stateFailures = [];
  for (const surface of surfaces) {
    const where = `${surface.meta.route}/${surface.meta.theme}`;
    if (!surface.adoptedDark) stateFailures.push(`${where} theme`);
    if (surface.viewport.w !== 1440 || surface.viewport.h !== 900) stateFailures.push(`${where} viewport`);
    if (surface.storage.theme !== surface.meta.theme) stateFailures.push(`${where} avrig-theme`);
    if (surface.storage.loggedIn !== "true" || surface.storage.operatorMode !== "true") stateFailures.push(`${where} session`);
    if (surface.meta.route === "/") {
      if (!surface.mainLanding) stateFailures.push(`${where} main-landing`);
    } else if (!surface.mainViewportId) {
      stateFailures.push(`${where} main-viewport`);
    }
  }
  for (const read of localeReads) if (!read.agrees) stateFailures.push(`locale ${read.requested.lang}/${read.requested.theme}`);
  results.push(
    row(
      "SC-07",
      stateFailures.length === 0,
      stateFailures.length
        ? stateFailures.join("; ")
        : `${surfaceCount} surfaces and ${localeReads.length} locale read-backs agree with the requested state`
    )
  );

  // ---- SC-08 ----
  const expectedSeals = (route) => (route === "/" ? 1 : route === "/sdlc" ? 3 : 2);
  const allowedSites = (route) => (route === "/" ? ["landing-hero-certificate"] : route === "/sdlc" ? ["sidebar", "topbar", "card"] : ["sidebar", "topbar"]);
  const sealFailures = [];
  for (const surface of surfaces) {
    const where = `${surface.meta.route}/${surface.meta.theme}`;
    const visible = surface.seals.filter((seal) => seal.visible);
    if (visible.length !== expectedSeals(surface.meta.route)) {
      sealFailures.push(`${where} ${visible.length} seals, expected ${expectedSeals(surface.meta.route)}`);
    }
    for (const seal of visible) {
      const allowed = allowedSites(surface.meta.route).some((site) => seal.site === site || seal.site.startsWith(site + "("));
      if (!allowed) sealFailures.push(`${where} seal ${seal.text} at ${seal.site}`);
    }
  }
  writeJson(ctx.evidence, "seals.json", surfaces.map((s) => ({ route: s.meta.route, theme: s.meta.theme, seals: s.seals })));
  results.push(
    row(
      "SC-08",
      sealFailures.length === 0,
      sealFailures.length
        ? sealFailures.join("; ")
        : `1 seal on /, 2 per console route, 3 on /sdlc, ${surfaces.reduce((n, s) => n + s.seals.filter((x) => x.visible).length, 0)} placements in ${surfaceCount} surfaces and none outside a designed site`
    )
  );

  // ---- SC-09 ----
  const fontTargets = surfaces.filter((s) => s.meta.route === "/" || s.meta.route === "/console");
  const fontFailures = [];
  for (const surface of fontTargets) {
    const where = `${surface.meta.route}/${surface.meta.theme}`;
    if (firstFamily(surface.fonts.body) !== "Geist") fontFailures.push(`${where} body first family ${firstFamily(surface.fonts.body)}`);
    if (firstFamily(surface.fonts.mono) !== "Geist Mono") fontFailures.push(`${where} mono first family ${firstFamily(surface.fonts.mono)}`);
    for (const family of ["Geist", "Geist Mono"]) {
      const face = surface.fonts.faces.find((f) => f.family.replace(/["']/g, "") === family);
      if (!face || face.status !== "loaded") fontFailures.push(`${where} ${family} ${face ? face.status : "absent"}`);
    }
  }
  writeJson(ctx.evidence, "fonts.json", fontTargets.map((s) => ({ route: s.meta.route, theme: s.meta.theme, ...s.fonts })));
  results.push(
    row(
      "SC-09",
      fontFailures.length === 0,
      fontFailures.length ? fontFailures.join("; ") : `Geist first on body and Geist Mono first on .font-mono, both faces loaded, on / and /console in both themes`
    )
  );

  // ---- TK-03 ----
  const tokenFailures = [];
  const tokenRows = [];
  for (const surface of surfaces) {
    const where = `${surface.meta.route}/${surface.meta.theme}`;
    const record = { route: surface.meta.route, theme: surface.meta.theme, tokens: {} };
    for (const token of NEW_TOKENS) {
      const triplet = surface.tokens[token.triplet];
      const utility = surface.tokenUtilities[token.utility];
      const entry = { triplet, utility: utility ? utility.value : null, colorProperty: surface.colorProperties[token.color] ?? "" };
      record.tokens[token.triplet] = entry;

      const shape = TRIPLET.exec(triplet ?? "");
      if (!triplet) tokenFailures.push(`${where} ${token.triplet} empty on :root`);
      else if (!shape) tokenFailures.push(`${where} ${token.triplet} "${triplet}" is not an HSL triplet`);

      const actual = utility ? parseRgb(utility.value) : null;
      if (!actual) {
        tokenFailures.push(`${where} .${token.utility} does not compute to an rgb() colour`);
        continue;
      }
      const expected = shape ? hslTripletToRgb(triplet) : null;
      if (expected && (Math.abs(expected.r - actual.r) > 1 || Math.abs(expected.g - actual.g) > 1 || Math.abs(expected.b - actual.b) > 1)) {
        tokenFailures.push(
          `${where} .${token.utility} computes rgb(${actual.r}, ${actual.g}, ${actual.b}) but ${token.triplet} "${triplet}" is rgb(${expected.r}, ${expected.g}, ${expected.b})`
        );
      }
    }
    tokenRows.push(record);
  }
  writeJson(ctx.evidence, "tokens-resolve.json", {
    note:
      "The --color-* family is deliberately absent from this read. @theme inline inlines hsl(var(--token)) into the utility instead of emitting a --color-* custom property, so a read of --color-<name> on documentElement returns the empty string by design, and TK-01 requires that mapping form. The triplets on :root are the values; the utilities are the mapping.",
    tokens: NEW_TOKENS,
    surfaces: tokenRows
  });
  results.push(
    row(
      "TK-03",
      tokenFailures.length === 0,
      tokenFailures.length
        ? tokenFailures.join("; ")
        : `${NEW_TOKENS.length} triplets present on :root and each utility computing to its hsl() value, in ${surfaceCount} surfaces`
    )
  );

  // ---- CP-01 ----
  const consoleSurfaces = surfaces.filter((s) => s.meta.route !== "/");
  const badgeFailures = consoleSurfaces.filter(
    (s) => !s.versionBadge || s.versionBadge.count !== 1 || !s.versionBadge.visible || !s.versionBadge.matchesShape
  );
  writeJson(ctx.evidence, "version-badge.json", consoleSurfaces.map((s) => ({ route: s.meta.route, theme: s.meta.theme, badge: s.versionBadge })));
  results.push(
    row(
      "CP-01",
      badgeFailures.length === 0,
      badgeFailures.length
        ? badgeFailures.map((s) => `${s.meta.route}/${s.meta.theme} ${JSON.stringify(s.versionBadge)}`).join("; ")
        : `exactly 1 visible badge matching v<semver> on all ${consoleSurfaces.length} console surfaces`
    )
  );

  // ---- PIL-01 ----
  const pillFailures = [];
  for (const surface of consoleSurfaces) {
    const where = `${surface.meta.route}/${surface.meta.theme}`;
    if (surface.pills.length > 2) pillFailures.push(`${where} ${surface.pills.length} pills`);
    for (const pill of surface.pills) if (!pill.live) pillFailures.push(`${where} "${pill.text}" without a live-status marker`);
  }
  writeJson(ctx.evidence, "pills.json", consoleSurfaces.map((s) => ({ route: s.meta.route, theme: s.meta.theme, count: s.pills.length, pills: s.pills })));
  results.push(
    row(
      "PIL-01",
      pillFailures.length === 0,
      pillFailures.length
        ? pillFailures.join("; ")
        : `${consoleSurfaces.reduce((n, s) => n + s.pills.length, 0)} pills on the shell across ${consoleSurfaces.length} console surfaces, every one carrying a live-status marker`
    )
  );

  // ---- BR-04 ----
  // (a) the constructed socket URL, read from the constructor itself.
  //
  // Two parties connect a socket from a page: the application, and Vite's
  // hot-module-reload channel. The dev server opens the second one against the
  // serving origin, and it is not the subject of this row. It is separated out
  // by identity, and by identity only: a socket is the application's when its
  // origin is not the serving origin, which is true whether the wsBaseUrl is
  // the shipped production host or a rewritten one.
  const baseHost = (() => {
    try {
      return new URL(ctx.base).host;
    } catch {
      return null;
    }
  })();

  const consoleSurfacesOnly = consoleNetwork.filter((entry) => entry.route !== "/");
  const socketFailure = [];
  const excludedSockets = [];
  const appSockets = [];
  for (const entry of consoleSurfacesOnly) {
    const where = `${entry.route}/${entry.theme}`;
    let appCount = 0;
    for (const raw of entry.webSockets) {
      let parsed;
      try {
        parsed = new URL(raw);
      } catch {
        socketFailure.push(`${where} unparseable socket URL ${raw}`);
        continue;
      }
      if (baseHost !== null && parsed.host === baseHost) {
        excludedSockets.push({
          surface: where,
          url: raw,
          reason:
            "the Vite dev server's hot-module-reload channel, opened by the client Vite injects into the served page against the serving origin. Not constructed by the application, and absent from a production build"
        });
        continue;
      }
      appCount++;
      appSockets.push({ surface: where, url: raw, pathname: parsed.pathname });
      if (parsed.pathname !== "/ws/command-center") {
        socketFailure.push(`${where} pathname ${parsed.pathname}, expected /ws/command-center`);
      }
      if ((parsed.pathname.match(/\/ws(\/|$)/g) || []).length !== 1) {
        socketFailure.push(`${where} pathname ${parsed.pathname} repeats the /ws segment`);
      }
      if (configWsBase) {
        const expected = new URL(`${String(configWsBase).replace(/\/$/, "")}/command-center`);
        if (`${parsed.origin}${parsed.pathname}` !== `${expected.origin}${expected.pathname}`) {
          socketFailure.push(
            `${where} ${parsed.origin}${parsed.pathname} is not ${expected.origin}${expected.pathname}`
          );
        }
      }
    }
    if (appCount === 0) socketFailure.push(`${where} the application constructed no WebSocket`);
  }

  // (b) console and network reconciled by name
  const consoleFailures = [];
  const classes = {};
  for (const entry of consoleNetwork) {
    const where = `${entry.route}/${entry.theme}`;
    for (const error of entry.consoleErrors) {
      const klass = classifyConsole(error);
      if (!klass) {
        consoleFailures.push(`${where} console.error: ${error.text.slice(0, 160)}`);
        continue;
      }
      classes[klass] = (classes[klass] ?? 0) + 1;
    }
    for (const error of entry.pageErrors) {
      consoleFailures.push(`${where} pageerror: ${String(error).slice(0, 160)}`);
    }
    for (const request of entry.failedRequests) {
      const klass = classifyRequest(request);
      if (!klass) {
        consoleFailures.push(`${where} failed request: ${request.method} ${request.url} ${request.reason}`);
        continue;
      }
      classes[klass] = (classes[klass] ?? 0) + 1;
    }
    for (const response of entry.responses) {
      const klass = classifyResponse(response);
      if (!klass) {
        consoleFailures.push(`${where} response ${response.status}: ${response.method} ${response.url}`);
        continue;
      }
      classes[klass] = (classes[klass] ?? 0) + 1;
    }
  }

  const firstSocket = appSockets[0] ?? null;
  writeJson(ctx.evidence, "br04-console-network.json", {
    configWsBase,
    applicationSockets: appSockets,
    firstConstructedSocketUrl: firstSocket ? firstSocket.url : null,
    excludedSockets,
    consoleExclusions: CONSOLE_EXCLUSIONS.map((e) => ({ id: e.id, reason: e.reason })),
    reconciled: classes,
    unexpectedConsole: consoleFailures,
    surfaces: consoleNetwork
  });

  const wsOk = socketFailure.length === 0;
  const consoleOk = consoleFailures.length === 0;
  const wsDetail = wsOk
    ? `${appSockets.length} application sockets across ${consoleSurfacesOnly.length} console surfaces all address ${configWsBase ?? "<wsBaseUrl>"}/command-center with a single /ws segment; ${excludedSockets.length} dev-server HMR sockets excluded${
        excludedSockets.length ? ` (first ${excludedSockets[0].url.replace(/\?.*$/, "")})` : ""
      }`
    : socketFailure.slice(0, 4).join("; ");
  const consoleDetail = consoleOk
    ? `0 unexpected console errors, page errors, failed requests or error responses; ${Object.entries(classes)
        .map(([k, n]) => `${k}=${n}`)
        .join(", ") || "nothing to reconcile"}`
    : consoleFailures.slice(0, 4).join("; ");
  results.push(row("BR-04", wsOk && consoleOk, `(a) ${wsDetail} (b) ${consoleDetail}`));

  return results;
}

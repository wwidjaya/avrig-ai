// Browser plumbing shared by every row: launch, seeded surface, adoption gate,
// and the measured snapshot of one rendered surface.
//
// `playwright` is resolved by Node from this file's location, which walks up to
// apps/web/node_modules. That makes the harness work from any working directory
// without a hardcoded absolute path.
import { chromium } from "playwright";
import path from "node:path";
import { seedSession } from "./session.mjs";

export const LANDING_ROUTE = "/";
export const CONSOLE_ROUTES = ["/console", "/office", "/deliberations", "/sdlc", "/knowledge", "/chat"];
export const ROUTES = [LANDING_ROUTE, ...CONSOLE_ROUTES];
export const THEMES = ["dark", "light"];

export function routeName(route) {
  return route === "/" ? "landing" : route.replace(/^\//, "");
}

export async function launch() {
  return chromium.launch({ headless: true });
}

// Runs in the page, before any application script. Kept as a real function so
// Node parses it: a string blob cannot be checked until it fails in a browser.
export function captureWebSocket() {
  const Native = window.WebSocket;
  if (!Native || window.__qaWsInstalled) return;
  window.__qaWsInstalled = true;
  window.__qaWsUrls = [];
  function Wrapped(url, protocols) {
    try {
      window.__qaWsUrls.push(String(url));
    } catch {
      // recording is best effort; never fail the connection attempt
    }
    return protocols === undefined ? new Native(url) : new Native(url, protocols);
  }
  Wrapped.prototype = Native.prototype;
  for (const key of ["CONNECTING", "OPEN", "CLOSING", "CLOSED"]) {
    try {
      Object.defineProperty(Wrapped, key, { value: Native[key] });
    } catch {
      // a frozen constructor is a browser detail, not a row failure
    }
  }
  window.WebSocket = Wrapped;
}

export function installQaHelpers() {
  const toRgb = (str) => {
    if (!str) return null;
    const m = String(str).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const parts = m[1]
      .split(/[,\s/]+/)
      .filter((s) => s !== "")
      .map(Number);
    if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) return null;
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1, raw: String(str) };
  };
  const blend = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
    raw: "blend"
  });
  const lum = (c) => {
    const f = (x) => {
      x /= 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  window.__qa = {
    rgb: toRgb,
    blend,
    lum,
    ratio(a, b) {
      const l1 = lum(a);
      const l2 = lum(b);
      return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    },
    // The first ancestor background that is not transparent, composited over
    // documentElement's own background.
    effBg(el) {
      const stack = [];
      let cur = el;
      while (cur) {
        const c = toRgb(getComputedStyle(cur).backgroundColor);
        if (c && c.a > 0) stack.push(c);
        if (c && c.a >= 0.999) break;
        cur = cur.parentElement;
      }
      const htmlBg = toRgb(getComputedStyle(document.documentElement).backgroundColor);
      let acc = htmlBg && htmlBg.a > 0 ? htmlBg : { r: 255, g: 255, b: 255, a: 1 };
      for (let i = stack.length - 1; i >= 0; i--) acc = blend(stack[i], acc);
      return acc;
    },
    vis(el) {
      const rect = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        cs.visibility !== "hidden" &&
        cs.display !== "none" &&
        parseFloat(cs.opacity) > 0.05
      );
    },
    path(el) {
      const bits = [];
      let cur = el;
      let n = 0;
      while (cur && n < 5) {
        let s = cur.tagName.toLowerCase();
        if (cur.id) s += "#" + cur.id;
        const tid = cur.getAttribute && cur.getAttribute("data-testid");
        if (tid) s += "[" + tid + "]";
        bits.unshift(s);
        cur = cur.parentElement;
        n++;
      }
      return bits.join(">");
    },
    saturated(c) {
      if (!c) return false;
      const mx = Math.max(c.r, c.g, c.b);
      const mn = Math.min(c.r, c.g, c.b);
      return mx - mn > 12 && c.a > 0.05;
    },
    shadowParts(str) {
      const c = toRgb(str);
      if (!c) return { c: null, blur: 0 };
      const nums = (String(str).match(/-?\d*\.?\d+px/g) || []).map(parseFloat);
      return { c, blur: nums.length >= 3 ? nums[2] : 0 };
    },
    // Where a seal sits, walking up from the seal element itself.
    sealSite(el) {
      let cur = el.parentElement;
      while (cur) {
        const tag = cur.tagName.toLowerCase();
        if (tag === "aside") return "sidebar";
        if (tag === "header") return "topbar";
        if (cur.id === "main-landing") return "landing-hero-certificate";
        if (cur.id === "main-viewport") return "main-viewport";
        const cls = typeof cur.className === "string" ? cur.className : "";
        if (cls.includes("rounded-xl")) {
          const heading = cur.querySelector("h3");
          return "card(" + (heading ? heading.textContent.trim() : "") + ")";
        }
        cur = cur.parentElement;
      }
      return "unknown";
    }
  };
}

// One seeded, instrumented surface. Console errors, page errors, failed
// requests and error responses are collected from the first byte, because
// BR-04 reconciles exactly those.
export async function openSurface(browser, { theme, lang = "en", width = 1440, height = 900, reduced = false } = {}) {
  const context = await browser.newContext({
    viewport: { width, height },
    locale: "en-US",
    reducedMotion: reduced ? "reduce" : "no-preference"
  });
  const record = { consoleErrors: [], pageErrors: [], failedRequests: [], responses: [] };
  const page = await context.newPage();
  page.on("console", (message) => {
    if (message.type() === "error") {
      const location = message.location();
      record.consoleErrors.push({ text: message.text(), url: location ? location.url : null });
    }
  });
  page.on("pageerror", (error) => record.pageErrors.push(String(error && error.message ? error.message : error)));
  page.on("requestfailed", (request) =>
    record.failedRequests.push({
      url: request.url(),
      method: request.method(),
      reason: request.failure() ? request.failure().errorText : null
    })
  );
  page.on("response", (response) => {
    if (response.status() >= 400) {
      record.responses.push({
        url: response.url(),
        status: response.status(),
        method: response.request().method()
      });
    }
  });
  await page.addInitScript(installQaHelpers);
  await page.addInitScript(captureWebSocket);
  await seedSession(page, { theme, lang });
  return { context, page, record };
}

// Navigates and refuses to report success until the requested state is on the
// DOM. SC-07 is the generalised form of this: measure only after read-back.
export async function gotoSurface(page, base, route, theme, { timeout = 30000 } = {}) {
  await page.goto(base + route, { waitUntil: "domcontentloaded", timeout });
  await page.waitForFunction(
    () => !!document.getElementById("main-landing") || !!document.getElementById("main-viewport"),
    null,
    { timeout }
  );
  const adopted = await page
    .waitForFunction(
      (wantDark) => document.documentElement.classList.contains("dark") === wantDark,
      theme === "dark",
      { timeout: 15000 }
    )
    .then(() => true)
    .catch(() => false);
  await page.evaluate(() => document.fonts.ready.then(() => true)).catch(() => {});
  await page
    .waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"), null, { timeout: 5000 })
    .catch(() => {});
  return adopted;
}

export async function screenshot(page, evidence, name, options = {}) {
  const target = path.join(evidence, "shots", name);
  await page.screenshot({ path: target, ...options });
  return target;
}

// The measured snapshot of one surface. Everything a per-surface row asserts is
// read here, once, so the 14 surfaces are not re-rendered per assertion.
export async function measureSurface(page, meta) {
  return page.evaluate((meta) => {
    const qa = window.__qa;
    const out = {
      meta,
      isDark: document.documentElement.classList.contains("dark"),
      colorScheme: document.documentElement.style.colorScheme,
      adoptedDark: document.documentElement.classList.contains("dark") === (meta.theme === "dark"),
      viewport: { w: window.innerWidth, h: window.innerHeight },
      mainLanding: !!document.getElementById("main-landing"),
      mainViewportId: !!document.getElementById("main-viewport"),
      mainViewportTestId: document.querySelectorAll('[data-testid="main-viewport"]').length,
      storage: {
        loggedIn: localStorage.getItem("avrig-logged-in"),
        operatorMode: localStorage.getItem("avrig-operator-mode"),
        theme: localStorage.getItem("avrig-theme"),
        lang: localStorage.getItem("avrig-lang")
      },
      bodyFontFamily: getComputedStyle(document.body).fontFamily,
      gradient: [],
      cliptext: [],
      weight: { max: 0, offenders: [] },
      motion: [],
      motionCandidateCount: 0,
      transitionAll: [],
      shadows: [],
      emoji: [],
      uppercase: [],
      seals: [],
      tokens: {},
      colorProperties: {},
      tokenUtilities: {},
      pills: [],
      versionBadge: null,
      headings: [],
      errorBoundary: null,
      fonts: null,
      overflow: null
    };

    const gradientRe = /(repeating-)?(linear|radial|conic)-gradient\(/;

    for (const el of document.querySelectorAll("*")) {
      const cs = getComputedStyle(el);
      const cls = typeof el.className === "string" ? el.className : "";

      // ST-01
      if (gradientRe.test(cs.backgroundImage)) {
        out.gradient.push({ path: qa.path(el), bg: cs.backgroundImage.slice(0, 120) });
      }

      // ST-02
      if (cls.includes("bg-clip-text")) {
        const fill = cs.webkitTextFillColor || cs.color;
        if (/rgba?\([^)]*,\s*0\s*\)|transparent/.test(fill)) {
          out.cliptext.push({ path: qa.path(el), fill, color: cs.color });
        }
      }

      // ST-04. A candidate is a rendered animation whose name is one of the
      // stock attention animations; a Tailwind entry animation (`animate-in`)
      // resolves to `enter` and is not one of them, so class presence alone is
      // counted separately rather than failed.
      const anim = cs.animationName || "";
      if (cls.includes("animate-")) out.motionCandidateCount++;
      if (/pulse|spin|ping|bounce/i.test(anim)) {
        const allowed = !!el.closest('[data-live-status],[role="status"]');
        if (!allowed) out.motion.push({ path: qa.path(el), anim, cls: cls.slice(0, 80) });
      }

      // ST-05. `transition-property`'s initial value is `all`, so the property
      // test alone matches every element. An element actually transitions only
      // when a duration is non-zero, so both are required.
      const props = (cs.transitionProperty || "").split(",").map((s) => s.trim());
      const durations = (cs.transitionDuration || "0s").split(",").map((s) => parseFloat(s) || 0);
      if (props.includes("all") && durations.some((d) => d > 0)) {
        out.transitionAll.push({ path: qa.path(el), tp: cs.transitionProperty, dur: cs.transitionDuration });
      }

      // ST-06 shadows
      for (const key of ["boxShadow", "textShadow"]) {
        const value = cs[key];
        if (value && value !== "none") {
          const { c, blur } = qa.shadowParts(value);
          if (c && qa.saturated(c) && blur > 0) {
            out.shadows.push({ path: qa.path(el), key, val: value.slice(0, 90) });
          }
        }
      }

      // ST-03 and ST-06 uppercase, over elements that render their own text
      const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
      if (ownText) {
        const weight = parseInt(cs.fontWeight, 10);
        if (!Number.isNaN(weight)) {
          if (weight > out.weight.max) out.weight.max = weight;
          if (weight > 600) {
            out.weight.offenders.push({ tag: el.tagName, w: weight, text: el.textContent.trim().slice(0, 60) });
          }
        }
        if (cs.textTransform === "uppercase" && cs.letterSpacing !== "normal" && parseFloat(cs.letterSpacing) !== 0) {
          out.uppercase.push({ path: qa.path(el), ls: cs.letterSpacing, text: el.textContent.trim().slice(0, 40) });
        }
      }

      // SC-08 seal census. Pass A reads the designed classes; pass B reads the
      // computed box, so a rebuilt seal with different classes is still counted.
      const text = (el.textContent || "").trim();
      const passA =
        cls.includes("rounded-[4px]") &&
        cls.includes("border-[1.5px]") &&
        cls.includes("font-mono") &&
        /^[A-Z][A-Z0-9]{1,9}-\d{5}$/.test(text);
      const borderWidth = parseFloat(cs.borderTopWidth);
      const mono = /mono|Consolas/i.test(cs.fontFamily);
      const passB =
        el.tagName === "SPAN" &&
        borderWidth >= 1 &&
        borderWidth <= 2 &&
        Math.abs(parseFloat(cs.borderTopLeftRadius) - 4) < 0.75 &&
        mono &&
        text.length > 0;
      if ((passA || passB) && el.children.length === 0) {
        const rect = el.getBoundingClientRect();
        out.seals.push({
          text,
          passA,
          passB,
          site: qa.sealSite(el),
          w: +rect.width.toFixed(2),
          h: +rect.height.toFixed(2),
          fontSize: cs.fontSize,
          borderTopWidth: cs.borderTopWidth,
          borderRadius: cs.borderTopLeftRadius,
          visible: qa.vis(el)
        });
      }
    }

    // ST-06 emoji, over rendered text only
    const emojiRe = /[\u{1F300}-\u{1FAFF}\u{1F000}-\u{1F2FF}\u{2600}-\u{27BF}\u{FE0F}\u{2B00}-\u{2BFF}]/gu;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const text = node.textContent;
      if (!text.trim()) continue;
      const matches = text.match(emojiRe);
      if (matches) out.emoji.push({ text: text.trim().slice(0, 60), chars: matches.slice(0, 5) });
    }

    // TK-03. The six tokens ship through @theme inline, so the custom property
    // that reaches the DOM is the triplet in :root, and the utility is the only
    // place the hsl() mapping is visible.
    const PROBES = [
      ["--accent-text", "--color-accent-text", "text-accent-text", "color"],
      ["--positive", "--color-positive", "text-positive", "color"],
      ["--negative", "--color-negative", "text-negative", "color"],
      ["--warning", "--color-warning", "text-warning", "color"],
      ["--text-secondary", "--color-text-secondary", "text-text-secondary", "color"],
      ["--border", "--color-border", "border-border", "borderTopColor"]
    ];
    for (const [triplet, colorName, utility, property] of PROBES) {
      const rootStyle = getComputedStyle(document.documentElement);
      out.tokens[triplet] = rootStyle.getPropertyValue(triplet).trim();
      out.colorProperties[colorName] = rootStyle.getPropertyValue(colorName).trim();
      const probe = document.createElement("span");
      probe.className = utility;
      probe.textContent = "probe";
      probe.style.cssText = "position:absolute;left:-9999px;top:0";
      document.body.appendChild(probe);
      out.tokenUtilities[utility] = { property, value: getComputedStyle(probe)[property] };
      probe.remove();
    }

    // PIL-01
    for (const scope of document.querySelectorAll("aside, header")) {
      for (const el of scope.querySelectorAll('[class*="rounded-full"]')) {
        const text = (el.textContent || "").trim();
        if (!text) continue;
        if (el.closest('[aria-hidden="true"]')) continue;
        out.pills.push({
          path: qa.path(el),
          text: text.slice(0, 40),
          live: !!(el.closest("[data-live-status]") || el.matches("[data-live-status]"))
        });
      }
    }

    // CP-01
    const badges = [...document.querySelectorAll('[data-testid="sidebar-version-badge"]')];
    if (badges.length) {
      const badge = badges[0];
      out.versionBadge = {
        count: badges.length,
        text: (badge.textContent || "").trim(),
        visible: qa.vis(badge),
        matchesShape: /^v\d+\.\d+\.\d+/.test((badge.textContent || "").trim())
      };
    }

    // Route heading and ErrorBoundary fallback
    out.headings = [...document.querySelectorAll("h1,h2")].filter(qa.vis).map((h) => h.textContent.trim().slice(0, 60));
    const bodyText = document.body.innerText || "";
    const boundary = bodyText.match(/.{0,40}(View Error|Bootstrap Failure).{0,40}/);
    out.errorBoundary = boundary ? boundary[0] : null;

    // SC-09 font cascade
    const monoEl = document.querySelector(".font-mono");
    out.fonts = {
      body: getComputedStyle(document.body).fontFamily,
      mono: monoEl ? getComputedStyle(monoEl).fontFamily : null,
      monoPath: monoEl ? qa.path(monoEl) : null,
      faces: [...document.fonts].map((f) => ({ family: f.family, status: f.status, weight: f.weight }))
    };

    // LY-01 / LY-02
    const de = document.documentElement;
    const body = document.body;
    out.overflow = {
      htmlScroll: de.scrollWidth,
      htmlClient: de.clientWidth,
      bodyScroll: body.scrollWidth,
      bodyClient: body.clientWidth,
      overflows: de.scrollWidth > de.clientWidth + 1 || body.scrollWidth > body.clientWidth + 1
    };

    return out;
  }, meta);
}

export function firstFamily(stack) {
  return String(stack || "")
    .split(",")[0]
    .replace(/["']/g, "")
    .trim();
}

// The interactive rows: focus visibility (SC-10), contrast (CT), the landing
// journey (BR-01), the reduced-motion path (BR-03), and keyboard operability
// (KB-01 to KB-04).
import { ROUTES, THEMES, openSurface, gotoSurface, screenshot } from "../lib/browser.mjs";
import { row, writeJson } from "../lib/harness.mjs";

export const ids = ["SC-10", "CT-01", "CT-02", "CT-03", "CT-04", "BR-01", "BR-03", "KB-01", "KB-02", "KB-03", "KB-04"];

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const NO_RING = new Set(["none", "0px", ""]);

function passFocusRead(read, resting) {
  if (!read) return false;
  if (read.focusVisible !== true) return false;
  const changedShadow = resting ? read.boxShadow !== resting.boxShadow : read.boxShadow !== "none";
  const changedOutline = resting ? read.outlineStyle !== resting.outlineStyle : read.outlineStyle !== "none";
  const paintedOutline = !NO_RING.has(read.outlineStyle) && read.outlineWidth !== "0px";
  return changedShadow || changedOutline || paintedOutline;
}

// A control may carry a resting shadow (`shadow-sm` on a Button). "No ring on
// mouse click" therefore means the shadow and the outline are unchanged from
// the resting state, which is the only reading that can distinguish a focus
// ring from a shadow that was always there.
//
// This applies to non-text controls only. Chromium matches :focus-visible for
// any focused text-entry control however focus arrived, so a text field is read
// symmetrically with passFocusRead on both paths: a missing ring on click there
// would mean the indicator is absent altogether, not correctly suppressed.
const NON_TEXT = "non-text";
const TEXT_ENTRY = "text-entry";

function noRing(read, resting) {
  if (!read) return false;
  if (read.focusVisible !== false) return false;
  const baseShadow = resting ? resting.boxShadow : "none";
  const baseOutline = resting ? resting.outlineStyle : "none";
  return read.boxShadow === baseShadow && read.outlineStyle === baseOutline;
}

async function readResting(page, selector) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    if (document.activeElement === el) el.blur();
    const cs = getComputedStyle(el);
    return { boxShadow: cs.boxShadow, outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth };
  }, selector);
}

async function readActive(page, selector) {
  return page.evaluate((sel) => {
    const el = sel ? document.querySelector(sel) : document.activeElement;
    if (!el) return null;
    const cs = getComputedStyle(el);
    return {
      tag: el.tagName,
      text: (el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 40),
      focusVisible: el.matches(":focus-visible"),
      boxShadow: cs.boxShadow,
      outlineStyle: cs.outlineStyle,
      outlineWidth: cs.outlineWidth
    };
  }, selector);
}

// Walks the real Tab order until it cycles, so "reachable" means reachable by a
// keyboard user rather than by a script that already knows the answer. Only
// elements the caller tagged with data-qa-focus are reported.
async function tabWalk(page, { max = 200 } = {}) {
  const seen = [];
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    const state = await page.evaluate(() => {
      const active = document.activeElement;
      if (!active || active === document.body) return { key: null };
      return { key: active.getAttribute("data-qa-focus") };
    });
    if (state.key === null) return { seen, leftDocument: true };
    if (seen.includes(state.key)) break; // cycled back into the order
    seen.push(state.key);
  }
  return { seen, leftDocument: false };
}

async function sc10(ctx) {
  const records = [];
  for (const route of ["/console", "/sdlc"]) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
      const record = { route, theme, targets: [] };
      try {
        await gotoSurface(page, ctx.base, route, theme);

        // ---- primary button ----
        const buttonFound = await page.evaluate(() => {
          const probe = document.createElement("div");
          probe.className = "bg-primary";
          document.body.appendChild(probe);
          const want = getComputedStyle(probe).backgroundColor;
          probe.remove();
          const button = [...document.querySelectorAll("button")].find(
            (b) => getComputedStyle(b).backgroundColor === want && want !== "rgba(0, 0, 0, 0)"
          );
          if (!button) return false;
          button.setAttribute("data-qa-target", "button");
          button.addEventListener(
            "click",
            (event) => {
              event.preventDefault();
              event.stopPropagation();
            },
            true
          );
          return (button.textContent || "").trim().slice(0, 40);
        });

        if (!buttonFound) {
          record.targets.push({ target: "button", control: NON_TEXT, status: "not-present", optional: true, note: "no button painted with bg-primary on this route" });
        } else {
          const buttonResting = await readResting(page, '[data-qa-target="button"]');
          await page.locator('[data-qa-target="button"]').first().click();
          const click = await readActive(page, '[data-qa-target="button"]');
          await page.keyboard.press("Tab");
          await page.keyboard.press("Shift+Tab");
          const keyboard = await readActive(page, '[data-qa-target="button"]');
          record.targets.push({
            target: "button",
            control: NON_TEXT,
            label: buttonFound,
            resting: buttonResting,
            click,
            keyboard,
            clickOk: noRing(click, buttonResting),
            keyboardOk: passFocusRead(keyboard, buttonResting)
          });
        }
        await page.keyboard.press("Escape").catch(() => {});
        await page.waitForFunction(() => !document.querySelector('[role="dialog"],[role="alertdialog"]'), null, { timeout: 5000 }).catch(() => {});

        // ---- badge ----
        const badgeLabel = await page.evaluate(() => {
          const badge = document.querySelector('#main-viewport [class*="rounded-md"][class*="gap-1.5"]');
          if (!badge) return null;
          badge.tabIndex = 0; // test-only, a div cannot match :focus-visible otherwise
          badge.setAttribute("data-qa-target", "badge");
          badge.addEventListener(
            "click",
            (event) => {
              event.preventDefault();
              event.stopPropagation();
            },
            true
          );
          return (badge.textContent || "").trim().slice(0, 40);
        });
        if (!badgeLabel) {
          record.targets.push({ target: "badge", control: NON_TEXT, status: "not-present" });
        } else {
          const badgeResting = await readResting(page, '[data-qa-target="badge"]');
          await page.locator('[data-qa-target="badge"]').first().click();
          const click = await readActive(page, '[data-qa-target="badge"]');
          // Leave and re-enter by keyboard, so the engine's last input was a
          // key press rather than the pointer that just clicked it.
          await page.keyboard.press("Tab");
          await page.keyboard.press("Shift+Tab");
          const keyboard = await readActive(page, '[data-qa-target="badge"]');
          record.targets.push({
            target: "badge",
            control: NON_TEXT,
            label: badgeLabel,
            resting: badgeResting,
            click,
            keyboard,
            clickOk: noRing(click, badgeResting),
            keyboardOk: passFocusRead(keyboard, badgeResting)
          });
        }

        // ---- dialog close ----
        await page.locator('[data-testid="sidebar-version-badge"]').first().click();
        await page.waitForFunction(() => !!document.querySelector('[role="dialog"]'), null, { timeout: 10000 }).catch(() => {});
        const dialog = await page.evaluate(() => {
          const container = document.querySelector('[role="dialog"],[role="alertdialog"]');
          if (!container) return null;
          const close = container.querySelector('[aria-label*="lose"], button[type="button"]');
          if (!close) return { opened: true, close: null };
          close.setAttribute("data-qa-target", "dialog-close");
          close.addEventListener("click", (event) => event.preventDefault(), true);
          return { opened: true, close: close.getAttribute("aria-label") || (close.textContent || "").trim() };
        });
        if (!dialog || !dialog.close) {
          record.targets.push({ target: "dialog-close", control: NON_TEXT, status: dialog ? "close-not-found" : "dialog-not-opened" });
        } else {
          const closeResting = await readResting(page, '[data-qa-target="dialog-close"]');
          await page.locator('[data-qa-target="dialog-close"]').first().click();
          const click = await readActive(page, '[data-qa-target="dialog-close"]');
          // Keyboard arrival: Tab inside the dialog until the close control holds focus.
          let keyboard = null;
          for (let i = 0; i < 20; i++) {
            await page.keyboard.press("Tab");
            const isClose = await page.evaluate(
              () => document.activeElement && document.activeElement.getAttribute("data-qa-target") === "dialog-close"
            );
            if (isClose) {
              keyboard = await readActive(page, null);
              break;
            }
          }
          record.targets.push({
            target: "dialog-close",
            control: NON_TEXT,
            label: dialog.close,
            resting: closeResting,
            click,
            keyboard,
            clickOk: noRing(click, closeResting),
            keyboardOk: passFocusRead(keyboard, closeResting)
          });
        }
        await page.keyboard.press("Escape").catch(() => {});

        // ---- command palette input ----
        await page.keyboard.press("Control+k");
        await page.waitForFunction(() => !!document.querySelector('[role="dialog"] input, [cmdk-input]'), null, { timeout: 10000 }).catch(() => {});

        // Keyboard half first, so the mouse click cannot have taught the engine
        // that the last input was a pointer.
        const keyboardInput = await readActive(page, null);
        const keyboardIsPaletteInput = await page.evaluate(() => {
          const active = document.activeElement;
          return Boolean(active && (active.hasAttribute("cmdk-input") || active.closest("[role=dialog]")));
        });

        const inputResting = await readResting(page, '[role="dialog"] input, [cmdk-input]');
        await page.locator('[role="dialog"] input, [cmdk-input]').first().click();
        const clickInput = await page.evaluate(() => {
          const el = document.activeElement;
          const cs = getComputedStyle(el);
          return {
            tag: el.tagName,
            focusVisible: el.matches(":focus-visible"),
            boxShadow: cs.boxShadow,
            outlineStyle: cs.outlineStyle,
            outlineWidth: cs.outlineWidth
          };
        });
        record.targets.push({
          target: "input",
          control: TEXT_ENTRY,
          status: keyboardIsPaletteInput ? "measured" : "palette-not-focused",
          resting: inputResting,
          click: clickInput,
          keyboard: keyboardInput,
          clickOk: passFocusRead(clickInput, inputResting),
          keyboardOk: passFocusRead(keyboardInput, inputResting)
        });

        // A Textarea inside the open surface is a text-entry control too, so it
        // is read symmetrically. This candidate's palette renders none, which is
        // recorded rather than silently skipped.
        const textareaLabel = await page.evaluate(() => {
          const el = document.querySelector('[role="dialog"] textarea, [cmdk-input] textarea');
          if (!el) return null;
          el.setAttribute("data-qa-target", "textarea");
          return (el.getAttribute("placeholder") || el.getAttribute("aria-label") || "").trim().slice(0, 40);
        });
        if (!textareaLabel) {
          record.targets.push({ target: "textarea", control: TEXT_ENTRY, status: "not-present", optional: true, note: "the open surface renders no textarea" });
        } else {
          const textareaResting = await readResting(page, '[data-qa-target="textarea"]');
          await page.locator('[data-qa-target="textarea"]').first().click();
          const click = await readActive(page, '[data-qa-target="textarea"]');
          await page.keyboard.press("Tab");
          await page.keyboard.press("Shift+Tab");
          const keyboard = await readActive(page, '[data-qa-target="textarea"]');
          record.targets.push({
            target: "textarea",
            control: TEXT_ENTRY,
            label: textareaLabel,
            resting: textareaResting,
            click,
            keyboard,
            clickOk: passFocusRead(click, textareaResting),
            keyboardOk: passFocusRead(keyboard, textareaResting)
          });
        }
        await page.keyboard.press("Escape").catch(() => {});

        await screenshot(page, ctx.evidence, `sc10-${route.replace(/\//g, "")}-${theme}.png`, { fullPage: true });
        records.push(record);
      } finally {
        await context.close();
      }
    }
  }

  writeJson(ctx.evidence, "focus-visible.json", records);

  const failures = [];
  let checks = 0;
  let textEntryTargets = 0;
  for (const record of records) {
    for (const target of record.targets) {
      if (target.status && target.status !== "measured") {
        // A target the surface does not render is recorded, not silently
        // dropped, and only an optional target decides nothing.
        if (target.status === "not-present" && target.optional) continue;
        failures.push(`${record.route}/${record.theme} ${target.target}: ${target.status}`);
        continue;
      }
      checks += 2;
      if (target.control === TEXT_ENTRY) textEntryTargets += 1;
      const where = `${record.route}/${record.theme} ${target.target} (${target.control})`;
      if (!target.clickOk) {
        failures.push(
          `${where} on mouse click: focus-visible=${target.click && target.click.focusVisible}, boxShadow=${target.click && target.click.boxShadow}, outline=${target.click && target.click.outlineStyle}`
        );
      }
      if (!target.keyboardOk) {
        failures.push(
          `${where} on keyboard focus: focus-visible=${target.keyboard && target.keyboard.focusVisible}, boxShadow=${target.keyboard && target.keyboard.boxShadow}, outline=${target.keyboard && target.keyboard.outlineStyle}`
        );
      }
    }
  }

  return [
    row(
      "SC-10",
      failures.length === 0,
      failures.length
        ? failures.join("; ")
        : `${checks} focus readings across ${records.length} surfaces: no ring on mouse click and a ring on keyboard focus for non-text controls; a ring and :focus-visible on both paths for ${textEntryTargets} text-entry control(s)`
    )
  ];
}

async function contrast(ctx) {
  const samples = [];
  for (const route of ["/", "/console", "/sdlc"]) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
      try {
        await gotoSurface(page, ctx.base, route, theme);
        const data = await page.evaluate(() => {
          const qa = window.__qa;
          const probe = (className) => {
            const el = document.createElement("div");
            el.className = className;
            document.body.appendChild(el);
            const value = getComputedStyle(el).backgroundColor;
            el.remove();
            return value;
          };
          const primaryBg = probe("bg-primary");
          const buttons = [...document.querySelectorAll("button")].filter(qa.vis);
          const primary =
            buttons.find((b) => getComputedStyle(b).backgroundColor === primaryBg && primaryBg !== "rgba(0, 0, 0, 0)") ||
            buttons.find((b) => {
              const alpha = qa.rgb(getComputedStyle(b).backgroundColor);
              return alpha && alpha.a > 0.9;
            });

          const accent = [...document.querySelectorAll('[class*="text-accent-text"]')]
            .filter(qa.vis)
            .slice(0, 5)
            .map((el) => {
              const cs = getComputedStyle(el);
              const backdrop = qa.effBg(el);
              return {
                text: (el.textContent || "").trim().slice(0, 40),
                color: cs.color,
                backdrop: `rgb(${Math.round(backdrop.r)}, ${Math.round(backdrop.g)}, ${Math.round(backdrop.b)})`,
                ratio: +qa.ratio(qa.rgb(cs.color), backdrop).toFixed(2)
              };
            });

          const forbidden = [];
          for (const el of document.querySelectorAll("body *")) {
            if (!qa.vis(el)) continue;
            const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
            if (!own) continue;
            const cs = getComputedStyle(el);
            const colour = qa.rgb(cs.color);
            if (colour && colour.r === 37 && colour.g === 99 && colour.b === 235) {
              const backdrop = qa.effBg(el);
              forbidden.push({
                path: qa.path(el),
                text: el.textContent.trim().slice(0, 40),
                color: cs.color,
                ratio: +qa.ratio(colour, backdrop).toFixed(2)
              });
            }
          }

          return {
            primary: primary
              ? {
                  text: (primary.textContent || "").trim().slice(0, 40),
                  color: getComputedStyle(primary).color,
                  background: getComputedStyle(primary).backgroundColor,
                  ratio: +qa.ratio(qa.rgb(getComputedStyle(primary).color), qa.rgb(getComputedStyle(primary).backgroundColor)).toFixed(2)
                }
              : null,
            accent,
            forbidden
          };
        });
        samples.push({ route, theme, ...data });
      } finally {
        await context.close();
      }
    }
  }
  writeJson(ctx.evidence, "contrast.json", samples);

  const results = [];
  const dark = samples.filter((s) => s.theme === "dark");
  const light = samples.filter((s) => s.theme === "light");

  // CT-01
  const primaryDark = dark.filter((s) => s.route === "/" || s.route === "/console");
  const ct01Fails = primaryDark.filter((s) => !s.primary || s.primary.ratio < 4.5);
  results.push(
    row(
      "CT-01",
      ct01Fails.length === 0 && primaryDark.length > 0,
      ct01Fails.length
        ? ct01Fails.map((s) => `${s.route} ${s.primary ? `${s.primary.color} on ${s.primary.background} = ${s.primary.ratio}` : "no primary button"}`).join("; ")
        : `lowest measured ${Math.min(...primaryDark.map((s) => s.primary.ratio))}:1 in ${primaryDark.length} dark surfaces`
    )
  );

  const accentRow = (id, pool, label) => {
    const measured = pool.flatMap((s) => s.accent.map((a) => ({ route: s.route, ...a })));
    const failures = measured.filter((a) => a.ratio < 4.5);
    return row(
      id,
      measured.length > 0 && failures.length === 0,
      measured.length === 0
        ? `no accent text element found in ${label}`
        : failures.length
          ? failures.map((f) => `${f.route} "${f.text}" ${f.color} on ${f.backdrop} = ${f.ratio}`).join("; ")
          : `${measured.length} accent samples, lowest ${Math.min(...measured.map((a) => a.ratio))}:1 in ${label}`
    );
  };
  results.push(accentRow("CT-02", dark.filter((s) => s.route === "/" || s.route === "/console"), "dark"));
  results.push(accentRow("CT-03", light.filter((s) => s.route === "/" || s.route === "/console"), "light"));

  // CT-04
  const forbidden = dark.flatMap((s) => s.forbidden.map((f) => ({ route: s.route, ...f })));
  const below = forbidden.filter((f) => f.ratio < 4.5);
  writeJson(ctx.evidence, "contrast-forbidden.json", forbidden);
  results.push(
    row(
      "CT-04",
      below.length === 0,
      below.length
        ? below.map((f) => `${f.route} "${f.text}" ${f.color} on ${f.backdrop || "resolved backdrop"} = ${f.ratio}`).join("; ")
        : `${forbidden.length} text elements painted rgb(37, 99, 235) on dark, none below 4.5:1`
    )
  );

  return results;
}

async function landingJourney(ctx) {
  const journeys = [];
  for (const theme of THEMES) {
    for (const [width, height] of [[1440, 900], [390, 844]]) {
      const { context, page } = await openSurface(ctx.browser, { theme, width, height });
      try {
        await gotoSurface(page, ctx.base, "/", theme);
        const sections = await page.evaluate(() => {
          const ids = ["main-landing", "sdlc-cockpit", "architecture", "workflow"];
          return ids.map((id) => {
            const el = document.getElementById(id);
            return {
              id,
              y: el ? +el.getBoundingClientRect().y.toFixed(1) : null,
              heading: el ? (el.querySelector("h1,h2,h3") ? el.querySelector("h1,h2,h3").textContent.trim().slice(0, 60) : null) : null
            };
          });
        });

        const ctaLabel = await page.evaluate(() => {
          const probe = document.createElement("div");
          probe.className = "bg-primary";
          document.body.appendChild(probe);
          const want = getComputedStyle(probe).backgroundColor;
          probe.remove();
          const button = [...document.querySelectorAll("button")].find((b) => getComputedStyle(b).backgroundColor === want);
          if (!button) return null;
          button.setAttribute("data-qa-cta", "1");
          return (button.textContent || "").trim().slice(0, 40);
        });

        let navigation = null;
        if (ctaLabel) {
          await page.locator('[data-qa-cta="1"]').first().click();
          await page
            .waitForFunction(() => !!document.getElementById("main-viewport"), null, { timeout: 15000 })
            .catch(() => {});
          navigation = {
            pathname: new URL(page.url()).pathname,
            hasViewport: await page.evaluate(() => !!document.getElementById("main-viewport"))
          };
        }
        await screenshot(page, ctx.evidence, `landing-${theme}-${width}x${height}.png`, { fullPage: true });

        const ascending = sections.every(
          (section, index) => index === 0 || (section.y !== null && sections[index - 1].y !== null && section.y > sections[index - 1].y)
        );
        journeys.push({ theme, viewport: `${width}x${height}`, sections, ascending, ctaLabel, navigation });
      } finally {
        await context.close();
      }
    }
  }
  writeJson(ctx.evidence, "journey-landing.json", journeys);

  const failures = [];
  for (const journey of journeys) {
    const where = `${journey.theme} ${journey.viewport}`;
    for (const section of journey.sections) {
      if (section.y === null) failures.push(`${where} #${section.id} missing`);
      else if (!section.heading) failures.push(`${where} #${section.id} has no heading`);
    }
    if (!journey.ascending) failures.push(`${where} sections are not in ascending y order`);
    if (!journey.ctaLabel) failures.push(`${where} no primary CTA`);
    else if (!journey.navigation || journey.navigation.pathname === "/" || !journey.navigation.hasViewport) {
      failures.push(`${where} CTA did not land on a console route`);
    }
  }
  return [
    row(
      "BR-01",
      failures.length === 0,
      failures.length
        ? failures.join("; ")
        : `${journeys.length} journeys: four sections in order with headings, CTA leaves / for a console route, both themes at 1440x900 and 390x844`
    )
  ];
}

async function reducedMotion(ctx) {
  const records = [];
  for (const route of ROUTES) {
    const { context, page } = await openSurface(ctx.browser, { theme: "dark", reduced: true, width: 1440, height: 900 });
    try {
      await gotoSurface(page, ctx.base, route, "dark");
      const data = await page.evaluate(() => {
        const animations = [];
        for (const el of document.querySelectorAll("*")) {
          const cs = getComputedStyle(el);
          if (cs.animationName && cs.animationName !== "none") {
            animations.push({ path: window.__qa.path(el), animationName: cs.animationName });
          }
        }
        const slowTransitions = [];
        for (const el of document.querySelectorAll("*")) {
          const cs = getComputedStyle(el);
          const properties = (cs.transitionProperty || "none").split(",").map((s) => s.trim());
          if (properties.every((p) => p === "none")) continue;
          const durations = (cs.transitionDuration || "0s").split(",").map((s) => parseFloat(s) || 0);
          if (durations.some((d) => d > 0.01)) {
            slowTransitions.push({ path: window.__qa.path(el), transitionDuration: cs.transitionDuration });
          }
        }
        return {
          animations,
          slowTransitions,
          running: document.getAnimations().filter((a) => a.playState === "running").length,
          matchesReduce: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
          rendered: !!(document.getElementById("main-landing") || document.getElementById("main-viewport"))
        };
      });
      records.push({ route, ...data });
    } finally {
      await context.close();
    }
  }
  writeJson(ctx.evidence, "reduced-motion.json", records);

  const failures = [];
  for (const record of records) {
    if (!record.matchesReduce) failures.push(`${record.route} media query not applied`);
    if (!record.rendered) failures.push(`${record.route} did not render`);
    if (record.animations.length) failures.push(`${record.route} ${record.animations.length} animations`);
    if (record.slowTransitions.length) failures.push(`${record.route} ${record.slowTransitions.length} transitions above 0.01s`);
  }
  return [
    row(
      "BR-03",
      failures.length === 0,
      failures.length
        ? failures.slice(0, 6).join("; ")
        : `${records.length} routes: 0 animations, 0 transitions above 0.01s, every surface still rendered`
    )
  ];
}

async function skipLink(ctx) {
  const records = [];
  for (const surface of ["/", "/console"]) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
      try {
        await gotoSurface(page, ctx.base, surface, theme);
        await page.evaluate(() => document.body.focus());
        await page.keyboard.press("Tab");
        const first = await page.evaluate(() => {
          const active = document.activeElement;
          const rect = active.getBoundingClientRect();
          return {
            tag: active.tagName,
            href: active.getAttribute("href"),
            text: (active.textContent || "").trim().slice(0, 40),
            width: +rect.width.toFixed(1),
            height: +rect.height.toFixed(1)
          };
        });
        await page.keyboard.press("Enter");
        await page.waitForFunction(() => document.activeElement && document.activeElement !== document.body, null, { timeout: 5000 }).catch(() => {});
        const after = await page.evaluate(() => ({
          id: document.activeElement ? document.activeElement.id : null,
          tag: document.activeElement ? document.activeElement.tagName : null
        }));
        records.push({ surface, theme, first, after });
      } finally {
        await context.close();
      }
    }
  }
  writeJson(ctx.evidence, "skip-link.json", records);

  const failures = [];
  for (const record of records) {
    const expectedHref = record.surface === "/" ? "#main-landing" : "#main-viewport";
    if (record.first.tag !== "A" || record.first.href !== expectedHref) {
      failures.push(`${record.surface}/${record.theme} first Tab focused ${record.first.tag} ${record.first.href}`);
    }
    if (record.first.width <= 0 || record.first.height <= 0) {
      failures.push(`${record.surface}/${record.theme} skip link has no box while focused`);
    }
    if (record.after.id !== expectedHref.slice(1)) {
      failures.push(`${record.surface}/${record.theme} Enter left focus on ${record.after.tag}#${record.after.id}`);
    }
  }
  return [
    row(
      "KB-01",
      failures.length === 0,
      failures.length ? failures.join("; ") : `first Tab reaches the skip link on / and /console in both themes, and Enter moves focus to its target`
    )
  ];
}

// KB-02. A roving-tabindex tab group is one Tab stop by design; counting its
// tabs as unreachable measures the ARIA pattern as a failure of itself.
async function tabReachability(ctx) {
  const records = [];

  for (const route of ROUTES) {
    const { context, page } = await openSurface(ctx.browser, { theme: "dark", width: 1440, height: 900 });
    const record = { route };
    try {
      await gotoSurface(page, ctx.base, route, "dark");

      const focusables = await page.evaluate((selector) => {
        const qa = window.__qa;
        return [...document.querySelectorAll(selector)]
          .filter(qa.vis)
          .map((el, index) => {
            const key = "f" + index;
            el.setAttribute("data-qa-focus", key);
            const tablist = el.closest('[role="tablist"]');
            return {
              key,
              tag: el.tagName,
              text: (el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30),
              role: el.getAttribute("role"),
              tabindex: el.getAttribute("tabindex"),
              inTablist: Boolean(tablist),
              tablistLabel: tablist ? tablist.getAttribute("aria-label") || "tablist" : null
            };
          });
      }, FOCUSABLE);

      const outside = focusables.filter((f) => !f.inTablist);
      const tablists = [...new Set(focusables.filter((f) => f.inTablist).map((f) => f.tablistLabel))];

      const walk = await tabWalk(page, { max: 200 });
      const reached = new Set(walk.seen);

      const outsideUnreached = outside.filter((f) => !reached.has(f.key));
      const tabsReached = focusables.filter((f) => f.inTablist && f.role === "tab" && reached.has(f.key));

      // Arrow traversal inside each tab group. Radix re-renders the panel on
      // selection, so each press is followed by a condition wait on the focused
      // tab rather than by a fixed delay.
      const groups = [];
      for (const label of tablists) {
        const group = await page.evaluate((groupLabel) => {
          const list = [...document.querySelectorAll('[role="tablist"]')].find(
            (el) => (el.getAttribute("aria-label") || "tablist") === groupLabel
          );
          if (!list) return null;
          const tabs = [...list.querySelectorAll('[role="tab"]')];
          const entry =
            tabs.find((t) => t.getAttribute("aria-selected") === "true") ||
            tabs.find((t) => t.getAttribute("tabindex") !== "-1") ||
            tabs[0];
          if (entry) entry.focus();
          return {
            label: groupLabel,
            tabs: tabs.map((t) => (t.textContent || "").trim()),
            entry: entry ? (entry.textContent || "").trim() : null,
            inTabOrder: tabs.filter((t) => t.getAttribute("tabindex") !== "-1").length
          };
        }, label);
        if (!group) continue;

        const visited = group.entry ? [group.entry] : [];
        for (let i = 0; i < group.tabs.length; i++) {
          const previous = visited[visited.length - 1] ?? "";
          await page.keyboard.press("ArrowRight");
          await page
            .waitForFunction(
              (prev) => {
                const active = document.activeElement;
                return (
                  Boolean(active) &&
                  active.getAttribute("role") === "tab" &&
                  (active.textContent || "").trim() !== prev
                );
              },
              previous,
              { timeout: 2000 }
            )
            .catch(() => {});
          const focused = await page.evaluate(() => {
            const active = document.activeElement;
            return {
              role: active ? active.getAttribute("role") : null,
              text: active ? (active.textContent || "").trim() : null
            };
          });
          if (focused.role === "tab" && focused.text && !visited.includes(focused.text)) {
            visited.push(focused.text);
          }
        }
        const missing = group.tabs.filter((text) => !visited.includes(text));
        groups.push({ ...group, visited, missing });
      }

      record.focusableCount = focusables.length;
      record.outside = { total: outside.length, reached: outside.length - outsideUnreached.length, unreached: outsideUnreached };
      record.tabs = {
        groups: groups.length,
        tabs: focusables.filter((f) => f.role === "tab").length,
        reachedByTab: tabsReached.length,
        tabOrderPerGroup: groups.map((g) => g.inTabOrder),
        arrowVisited: groups.map((g) => g.visited.length),
        missing: groups.flatMap((g) => g.missing)
      };
      record.leftDocument = walk.leftDocument;
      record.visitedCount = walk.seen.length;
      records.push(record);
    } catch (error) {
      records.push({ route, error: String(error.message).slice(0, 300) });
    } finally {
      await context.close();
    }
  }

  writeJson(ctx.evidence, "a11y-tab.json", records);

  const failures = [];
  for (const record of records) {
    if (record.error) {
      failures.push(`${record.route} ${record.error}`);
      continue;
    }
    if (record.outside.unreached.length) {
      failures.push(
        `${record.route} ${record.outside.unreached.length} of ${record.outside.total} focusables outside a tablist unreachable: ${record.outside.unreached.map((f) => `${f.tag}:${f.text}`).slice(0, 4).join(",")}`
      );
    }
    if (record.tabs.groups === 0) continue;
    if (record.tabs.reachedByTab !== record.tabs.groups) {
      failures.push(`${record.route} ${record.tabs.reachedByTab} tabs in the Tab order across ${record.tabs.groups} groups, expected one per group`);
    }
    for (const missing of record.tabs.missing) {
      failures.push(`${record.route} tab "${missing}" not reachable by arrow key`);
    }
  }

  const outsideTotal = records.reduce((n, r) => n + (r.outside ? r.outside.total : 0), 0);
  const outsideReached = records.reduce((n, r) => n + (r.outside ? r.outside.reached : 0), 0);
  const groupCount = records.reduce((n, r) => n + (r.tabs ? r.tabs.groups : 0), 0);
  const tabCount = records.reduce((n, r) => n + (r.tabs ? r.tabs.tabs : 0), 0);
  const arrowVisited = records.reduce((n, r) => n + (r.tabs ? r.tabs.arrowVisited.reduce((a, b) => a + b, 0) : 0), 0);

  return [
    row(
      "KB-02",
      failures.length === 0,
      failures.length
        ? failures.slice(0, 6).join("; ")
        : `${outsideReached}/${outsideTotal} focusables outside a tablist reached by Tab; ${groupCount} tab group(s) with ${tabCount} tabs, one in the Tab order each and ${arrowVisited} reached by arrow key`
    )
  ];
}

async function focusRing(ctx) {
  const records = [];
  for (const route of ROUTES) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
      try {
        await gotoSurface(page, ctx.base, route, theme);
        const reads = [];
        for (let i = 0; i < 10; i++) {
          await page.keyboard.press("Tab");
          const read = await page.evaluate(() => {
            const active = document.activeElement;
            if (!active || active === document.body) return null;
            const cs = getComputedStyle(active);
            return {
              tag: active.tagName,
              text: (active.textContent || active.getAttribute("aria-label") || "").trim().slice(0, 24),
              outlineStyle: cs.outlineStyle,
              outlineWidth: cs.outlineWidth,
              boxShadow: cs.boxShadow
            };
          });
          if (!read) break;
          reads.push({
            ...read,
            ok: (read.outlineStyle !== "none" && read.outlineWidth !== "0px") || read.boxShadow !== "none"
          });
        }
        records.push({ route, theme, sampled: reads.length, failures: reads.filter((r) => !r.ok) });
      } finally {
        await context.close();
      }
    }
  }
  writeJson(ctx.evidence, "a11y-ring.json", records);

  const failures = records.flatMap((r) => r.failures.map((f) => `${r.route}/${r.theme} ${f.tag} "${f.text}"`));
  const sampled = records.reduce((n, r) => n + r.sampled, 0);
  return [
    row(
      "KB-03",
      failures.length === 0 && sampled > 0,
      failures.length ? failures.slice(0, 6).join("; ") : `${sampled} focus reads across 7 routes and both themes, every one painted`
    )
  ];
}

async function focusTraps(ctx) {
  const records = [];
  for (const route of ["/console", "/sdlc"]) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
      const record = { route, theme };
      try {
        await gotoSurface(page, ctx.base, route, theme);

        // Command palette, opened by keyboard so there is no trigger to return to.
        await page.keyboard.press("Control+k");
        await page.waitForFunction(() => !!document.querySelector('[role="dialog"]'), null, { timeout: 10000 }).catch(() => {});
        const paletteOpen = await page.evaluate(() => !!document.querySelector('[role="dialog"]'));
        let paletteInside = 0;
        for (let i = 0; i < 15; i++) {
          await page.keyboard.press("Tab");
          const inside = await page.evaluate(() => {
            const dialog = document.querySelector('[role="dialog"]');
            return Boolean(dialog && dialog.contains(document.activeElement));
          });
          if (inside) paletteInside++;
        }
        await page.keyboard.press("Escape");
        await page.waitForFunction(() => !document.querySelector('[role="dialog"]'), null, { timeout: 5000 }).catch(() => {});
        record.palette = { opened: paletteOpen, inside: paletteInside, total: 15, closed: await page.evaluate(() => !document.querySelector('[role="dialog"]')) };

        // System info dialog, opened from the sidebar version badge.
        await page.locator('[data-testid="sidebar-version-badge"]').first().click();
        await page.waitForFunction(() => !!document.querySelector('[role="dialog"]'), null, { timeout: 10000 }).catch(() => {});
        const dialogOpen = await page.evaluate(() => !!document.querySelector('[role="dialog"]'));
        let dialogInside = 0;
        for (let i = 0; i < 15; i++) {
          await page.keyboard.press("Tab");
          const inside = await page.evaluate(() => {
            const dialog = document.querySelector('[role="dialog"]');
            return Boolean(dialog && dialog.contains(document.activeElement));
          });
          if (inside) dialogInside++;
        }
        await page.keyboard.press("Escape");
        await page.waitForFunction(() => !document.querySelector('[role="dialog"]'), null, { timeout: 5000 }).catch(() => {});
        const afterEscape = await page.evaluate(() => ({
          closed: !document.querySelector('[role="dialog"]'),
          testid: document.activeElement ? document.activeElement.getAttribute("data-testid") : null,
          tag: document.activeElement ? document.activeElement.tagName : null
        }));
        record.dialog = { opened: dialogOpen, inside: dialogInside, total: 15, afterEscape };
        records.push(record);
      } catch (error) {
        records.push({ route, theme, error: String(error.message).slice(0, 300) });
      } finally {
        await context.close();
      }
    }
  }
  writeJson(ctx.evidence, "a11y-traps.json", records);

  const failures = [];
  for (const record of records) {
    const where = `${record.route}/${record.theme}`;
    if (record.error) {
      failures.push(`${where} ${record.error}`);
      continue;
    }
    if (!record.palette.opened) failures.push(`${where} command palette did not open`);
    else {
      if (record.palette.inside !== record.palette.total) failures.push(`${where} palette focus escaped ${record.palette.total - record.palette.inside}/${record.palette.total}`);
      if (!record.palette.closed) failures.push(`${where} Escape did not close the palette`);
    }
    if (!record.dialog.opened) failures.push(`${where} system dialog did not open`);
    else {
      if (record.dialog.inside !== record.dialog.total) failures.push(`${where} dialog focus escaped ${record.dialog.total - record.dialog.inside}/${record.dialog.total}`);
      if (!record.dialog.afterEscape.closed) failures.push(`${where} Escape did not close the dialog`);
      if (record.dialog.afterEscape.testid !== "sidebar-version-badge") {
        failures.push(`${where} focus returned to ${record.dialog.afterEscape.tag} instead of the version badge`);
      }
    }
  }

  return [
    row(
      "KB-04",
      failures.length === 0,
      failures.length
        ? failures.slice(0, 6).join("; ")
        : `palette and system dialog trap focus for 15 presses, Escape closes both, and focus returns to the version badge, on /console and /sdlc in both themes`
    )
  ];
}

export async function run(ctx) {
  const results = [];
  results.push(...(await sc10(ctx)));
  results.push(...(await contrast(ctx)));
  results.push(...(await landingJourney(ctx)));
  results.push(...(await reducedMotion(ctx)));
  results.push(...(await skipLink(ctx)));
  results.push(...(await tabReachability(ctx)));
  results.push(...(await focusRing(ctx)));
  results.push(...(await focusTraps(ctx)));
  return results;
}

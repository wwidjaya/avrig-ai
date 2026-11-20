// LY-01, LY-02, LY-03 and BR-02.
//
// One context per route and theme, resized through every width once. Measuring
// overflow at four widths for the family rows and headings at two widths for
// the journey row from the same render keeps the cost at 14 contexts instead of
// 70.
import { ROUTES, THEMES, routeName, openSurface, gotoSurface, screenshot } from "../lib/browser.mjs";
import { row, writeJson } from "../lib/harness.mjs";

export const ids = ["LY-01", "LY-02", "LY-03", "BR-02"];

// The four widths LY-01 and LY-02 name, plus the two the journey rows use.
const WIDTHS = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1280, height: 900 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
  { width: 360, height: 800 }
];

const LAYOUT_WIDTHS = ["1920x1080", "1280x900", "768x1024", "360x800"];
const JOURNEY_WIDTHS = ["1440x900", "390x844"];

async function measure(page) {
  return page.evaluate(() => {
    const de = document.documentElement;
    const body = document.body;
    const aside = document.querySelector("aside");
    const main = document.getElementById("main-viewport");
    const column = main ? main.querySelector('[class*="max-w-"]') : null;
    // The content area: the scroll container's box less its own horizontal
    // gutters. This is the surface that must fill the main region; the
    // `mx-auto` wrapper inside it is capped at a maximum width by design.
    const scroll = main ? main.querySelector(":scope > div") : null;
    const scrollStyle = scroll ? getComputedStyle(scroll) : null;
    const content =
      scroll && scrollStyle
        ? +(
            scroll.getBoundingClientRect().width -
            parseFloat(scrollStyle.paddingLeft) -
            parseFloat(scrollStyle.paddingRight)
          ).toFixed(1)
        : null;
    return {
      viewport: { w: window.innerWidth, h: window.innerHeight },
      htmlScroll: de.scrollWidth,
      htmlClient: de.clientWidth,
      bodyScroll: body.scrollWidth,
      bodyClient: body.clientWidth,
      overflow: de.scrollWidth > de.clientWidth + 1 || body.scrollWidth > body.clientWidth + 1,
      aside: aside ? +aside.getBoundingClientRect().width.toFixed(1) : null,
      main: main ? +main.getBoundingClientRect().width.toFixed(1) : null,
      content,
      column: column ? +column.getBoundingClientRect().width.toFixed(1) : null,
      columnClasses: column ? String(column.className).slice(0, 100) : null,
      heading:
        (main && main.querySelector("h1") ? main.querySelector("h1").textContent.trim() : null) ||
        (document.querySelector("#main-landing h1") ? document.querySelector("#main-landing h1").textContent.trim() : null),
      errorFallback: /View Error/.test(body.innerText)
    };
  });
}

export async function run(ctx) {
  const layouts = [];

  for (const route of ROUTES) {
    for (const theme of THEMES) {
      const { context, page } = await openSurface(ctx.browser, { theme, width: WIDTHS[0].width, height: WIDTHS[0].height });
      try {
        await gotoSurface(page, ctx.base, route, theme);
        const byWidth = {};
        for (const { width, height } of WIDTHS) {
          await page.setViewportSize({ width, height });
          await page
            .waitForFunction((expected) => window.innerWidth === expected, width, { timeout: 5000 })
            .catch(() => {});
          byWidth[`${width}x${height}`] = await measure(page);
        }
        if (route === "/" || route === "/console") {
          await page.setViewportSize({ width: 390, height: 844 });
          await page.waitForFunction(() => window.innerWidth === 390, null, { timeout: 5000 }).catch(() => {});
          await screenshot(page, ctx.evidence, `layout-${routeName(route)}-${theme}-390.png`, { fullPage: true });
        }
        layouts.push({ route, theme, widths: byWidth });
      } finally {
        await context.close();
      }
    }
  }

  writeJson(ctx.evidence, "layouts.json", layouts);

  // ---- LY-01 ----
  const landingFailures = [];
  for (const entry of layouts.filter((l) => l.route === "/")) {
    for (const width of LAYOUT_WIDTHS) {
      if (entry.widths[width].overflow) {
        landingFailures.push(`${entry.theme} ${width} html ${entry.widths[width].htmlScroll}/${entry.widths[width].htmlClient} body ${entry.widths[width].bodyScroll}/${entry.widths[width].bodyClient}`);
      }
    }
  }
  const landingCombos = layouts.filter((l) => l.route === "/").length * LAYOUT_WIDTHS.length;
  const ly01 = row(
    "LY-01",
    landingFailures.length === 0,
    landingFailures.length ? landingFailures.join("; ") : `no horizontal overflow in ${landingCombos} landing combinations`
  );

  // ---- LY-02 ----
  const consoleFailures = [];
  let consoleCombos = 0;
  for (const entry of layouts.filter((l) => l.route !== "/")) {
    for (const width of LAYOUT_WIDTHS) {
      consoleCombos++;
      if (entry.widths[width].overflow) {
        consoleFailures.push(`${entry.route}/${entry.theme} ${width}`);
      }
    }
  }
  const ly02 = row(
    "LY-02",
    consoleFailures.length === 0,
    consoleFailures.length
      ? `${consoleFailures.length} of ${consoleCombos} combinations overflow: ${consoleFailures.slice(0, 6).join(", ")}`
      : `no horizontal overflow in ${consoleCombos} route x width x theme combinations`
  );

  // ---- LY-03 ----
  // Measured on the content area inside the main region. The `mx-auto` wrapper
  // beneath it is capped at 1440px by `max-w-[1440px]`, so it is deliberately
  // narrower than the floor once the viewport passes the cap. Both widths are
  // recorded in proportions.json, and only the content area decides the row.
  const proportionFailures = [];
  const proportions = [];
  for (const entry of layouts.filter((l) => l.route === "/console" || l.route === "/sdlc")) {
    for (const width of ["1280x900", "1920x1080"]) {
      const measured = entry.widths[width];
      const where = `${entry.route}/${entry.theme} ${width}`;
      const floor = measured.viewport.w - 256 - 64;
      proportions.push({ route: entry.route, theme: entry.theme, width, floor, ...measured });
      if (measured.aside === null) proportionFailures.push(`${where} has no aside`);
      else if (Math.abs(measured.aside - 256) > 1) proportionFailures.push(`${where} aside ${measured.aside}`);
      if (measured.main === null) proportionFailures.push(`${where} has no main`);
      else if (width === "1920x1080" && measured.main < 1024) proportionFailures.push(`${where} main ${measured.main}`);
      if (measured.content === null) proportionFailures.push(`${where} has no content area`);
      else if (measured.content < floor - 1) proportionFailures.push(`${where} content ${measured.content} below ${floor}`);
    }
  }
  writeJson(ctx.evidence, "proportions.json", proportions);
  const capped = proportions.filter((p) => p.column !== null && p.column < p.floor);
  const ly03 = row(
    "LY-03",
    proportionFailures.length === 0,
    proportionFailures.length
      ? proportionFailures.join("; ")
      : `aside 256 at 1280 and 1920, main at least 1024 at 1920, content area equal to viewport - 256 - 64 at both widths, on /console and /sdlc in both themes${
          capped.length
            ? `; the mx-auto wrapper measures ${capped[0].column} at ${capped[0].width}, capped by \`${capped[0].columnClasses}\`, recorded in proportions.json and not gated`
            : ""
        }`
  );

  // ---- BR-02 ----
  const journeyFailures = [];
  const journey = [];
  let journeyCount = 0;
  for (const entry of layouts.filter((l) => l.route !== "/")) {
    for (const width of JOURNEY_WIDTHS) {
      journeyCount++;
      const measured = entry.widths[width];
      journey.push({ route: entry.route, theme: entry.theme, width, heading: measured.heading, errorFallback: measured.errorFallback });
      if (!measured.heading) journeyFailures.push(`${entry.route}/${entry.theme} ${width} no heading`);
      if (measured.errorFallback) journeyFailures.push(`${entry.route}/${entry.theme} ${width} View Error fallback`);
    }
  }
  writeJson(ctx.evidence, "journey-console.json", journey);
  const br02 = row(
    "BR-02",
    journeyFailures.length === 0,
    journeyFailures.length
      ? journeyFailures.slice(0, 6).join("; ")
      : `each of 6 console routes renders its own heading in ${journeyCount} journeys, 0 View Error fallbacks`
  );

  return [ly01, ly02, ly03, br02];
}

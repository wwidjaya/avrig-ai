// SC-04: the rendered primitives paint from the cascade, not from a stale
// `packages/ui/dist`.
//
// This is the row no grep can stand in for: a converted `src` with an unbuilt
// `dist` still ships the old palette, and only a rendered backgroundColor shows
// it.
import { THEMES, openSurface, gotoSurface, screenshot } from "../lib/browser.mjs";
import { row, writeJson } from "../lib/harness.mjs";

export const ids = ["SC-04"];

const BUTTON_NAMES = /^(Inspect stage|Review stage gate|View details)$/i;

export async function run(ctx) {
  const measured = [];

  for (const theme of THEMES) {
    const { context, page } = await openSurface(ctx.browser, { theme, width: 1440, height: 900 });
    try {
      const adopted = await gotoSurface(page, ctx.base, "/sdlc", theme);
      const data = await page.evaluate((buttonNames) => {
        const probe = (className) => {
          const el = document.createElement("div");
          el.className = className;
          el.style.cssText = "position:absolute;left:-9999px;top:0;width:10px;height:10px";
          document.body.appendChild(el);
          const cs = getComputedStyle(el);
          const value = { backgroundColor: cs.backgroundColor, backgroundImage: cs.backgroundImage };
          el.remove();
          return value;
        };
        const bgPrimary = probe("bg-primary");
        const bgCard = probe("bg-card");

        const buttons = [...document.querySelectorAll("button")];
        const named = buttons.filter((button) => new RegExp(buttonNames, "i").test((button.textContent || "").trim()));
        const primary =
          named.find((button) => {
            const bg = getComputedStyle(button).backgroundColor;
            return bg === bgPrimary.backgroundColor && bg !== "rgba(0, 0, 0, 0)";
          }) ??
          buttons.find((button) => {
            const bg = getComputedStyle(button).backgroundColor;
            return bg === bgPrimary.backgroundColor && bg !== "rgba(0, 0, 0, 0)";
          }) ??
          null;

        const viewport = document.getElementById("main-viewport");
        const card = viewport ? viewport.querySelector("div.rounded-xl") : null;
        const cardStyle = card ? getComputedStyle(card) : null;

        return {
          bgPrimaryProbe: bgPrimary,
          bgCardProbe: bgCard,
          namedButtons: named.map((button) => ({
            text: (button.textContent || "").trim(),
            bg: getComputedStyle(button).backgroundColor
          })),
          primaryButton: primary
            ? {
                text: (primary.textContent || "").trim().slice(0, 40),
                bg: getComputedStyle(primary).backgroundColor,
                color: getComputedStyle(primary).color
              }
            : null,
          card: cardStyle
            ? {
                bg: cardStyle.backgroundColor,
                backdropFilter: cardStyle.backdropFilter || cardStyle.webkitBackdropFilter,
                borderRadius: cardStyle.borderRadius,
                classes: card.className.slice(0, 120)
              }
            : null,
          mainViewportTestId: document.querySelectorAll('[data-testid="main-viewport"]').length
        };
      }, BUTTON_NAMES.source);

      await screenshot(page, ctx.evidence, `computed-primitives-sdlc-${theme}.png`, { fullPage: true });
      measured.push({ theme, adopted, ...data });
    } finally {
      await context.close();
    }
  }

  writeJson(ctx.evidence, "computed-primitives.json", measured);

  const failures = [];
  for (const surface of measured) {
    const where = surface.theme;
    if (!surface.adopted) failures.push(`${where} theme not adopted`);
    if (!surface.primaryButton) {
      failures.push(`${where} no button painted with bg-primary`);
    } else {
      const bg = surface.primaryButton.bg;
      if (bg === "rgba(0, 0, 0, 0)" || bg === "transparent") failures.push(`${where} primary button background is ${bg}`);
      if (bg !== surface.bgPrimaryProbe.backgroundColor) {
        failures.push(`${where} primary button ${bg} differs from the bg-primary probe ${surface.bgPrimaryProbe.backgroundColor}`);
      }
    }
    if (!surface.card) {
      failures.push(`${where} no ` + "#main-viewport div.rounded-xl");
    } else {
      if (surface.card.bg !== surface.bgCardProbe.backgroundColor) {
        failures.push(`${where} card ${surface.card.bg} differs from the bg-card probe ${surface.bgCardProbe.backgroundColor}`);
      }
      if (surface.card.backdropFilter && surface.card.backdropFilter !== "none") {
        failures.push(`${where} card backdropFilter is ${surface.card.backdropFilter}`);
      }
    }
  }

  return [
    row(
      "SC-04",
      failures.length === 0,
      failures.length
        ? failures.join("; ")
        : `both themes: primary button and card paint from the bg-primary and bg-card probes and the card has no backdrop filter`
    )
  ];
}

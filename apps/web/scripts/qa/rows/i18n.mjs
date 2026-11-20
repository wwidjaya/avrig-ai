// I18-01 and I18-02.
//
// I18-02 is deliberately not "every id value differs from its en value". Proper
// nouns, product names, stage codes and numerals are identical in every locale
// by design, so that criterion would fail on correct work. The criterion here is
// that every identical value is on the in-row non-translatable list with a
// category, and that the list itself has no stale entries: a list nobody reads
// is the defect this repository already carries once (`hex-allow.txt`).
import fs from "node:fs";
import path from "node:path";
import { git, row, blocked, writeJson, writeText } from "../lib/harness.mjs";

export const ids = ["I18-01", "I18-02"];

const CATEGORIES = ["proper noun", "product name", "token tag", "numeral"];

// Values that are correct in both locales. `value` is asserted against the
// current `en` string, so a reworded source key invalidates its own entry.
export const NON_TRANSLATABLE = {
  "bento.card4Badge": { value: "OIDC", category: "product name" },
  "bento.card4Footer": { value: "Rauthy, Keycloak, Authentik", category: "product name" },
  "certificate.pin": { value: "Pin", category: "proper noun" },
  "showcase.sdlc.item1Code": { value: "[RE]", category: "token tag" },
  "showcase.sdlc.item2Code": { value: "[SA]", category: "token tag" },
  "showcase.sdlc.item3Code": { value: "[DV]", category: "token tag" },
  "showcase.sdlc.item4Code": { value: "[TE]", category: "token tag" },
  "workflow.step1Num": { value: "01", category: "numeral" },
  "workflow.step2Num": { value: "02", category: "numeral" },
  "workflow.step3Num": { value: "03", category: "numeral" },
  "workflow.step4Num": { value: "04", category: "numeral" }
};

// Reads one locale object literal out of a TypeScript module. The file is data,
// not logic, so this needs neither a bundler nor a dev server. Only the locale
// object is walked; the interface above it declares types, not values.
export function parseLocale(source, marker) {
  const at = source.indexOf(marker);
  if (at < 0) throw new Error(`marker not found: ${JSON.stringify(marker)}`);
  let i = source.indexOf("{", at);
  const values = {};
  const stack = [];

  const skipWhitespace = () => {
    while (i < source.length) {
      if (source[i] === "/" && source[i + 1] === "/") {
        const next = source.indexOf("\n", i);
        if (next < 0) return;
        i = next;
        continue;
      }
      if (source[i] === "/" && source[i + 1] === "*") {
        i = source.indexOf("*/", i) + 2;
        continue;
      }
      if (/\s/.test(source[i])) {
        i++;
        continue;
      }
      return;
    }
  };

  const readQuoted = () => {
    const quote = source[i];
    let j = i + 1;
    let value = "";
    while (j < source.length && source[j] !== quote) {
      if (source[j] === "\\") {
        const next = source[j + 1];
        value += next === "n" ? "\n" : next === "t" ? "\t" : next;
        j += 2;
        continue;
      }
      value += source[j];
      j++;
    }
    i = j + 1;
    return value;
  };

  const parseObject = () => {
    i++; // consume '{'
    for (;;) {
      skipWhitespace();
      if (i >= source.length) return;
      const c = source[i];
      if (c === "}") {
        i++;
        return;
      }
      if (c === ",") {
        i++;
        continue;
      }
      let key;
      if (c === '"' || c === "'") key = readQuoted();
      else {
        const match = /^[A-Za-z_$][\w$]*/.exec(source.slice(i));
        if (!match) {
          i++;
          continue;
        }
        key = match[0];
        i += match[0].length;
      }
      skipWhitespace();
      if (source[i] !== ":") {
        i++;
        continue;
      }
      i++;
      skipWhitespace();
      stack.push(key);
      if (source[i] === "{") {
        parseObject();
        stack.pop();
      } else if (source[i] === '"' || source[i] === "'" || source[i] === "`") {
        values[stack.join(".")] = readQuoted();
        stack.pop();
      } else {
        // A number, boolean or expression: captured verbatim, never treated as
        // a translation.
        const start = i;
        let depth = 0;
        while (i < source.length) {
          const ch = source[i];
          if (ch === '"' || ch === "'") {
            readQuoted();
            continue;
          }
          if (ch === "{") depth++;
          else if (ch === "}") {
            if (depth === 0) break;
            depth--;
          } else if (ch === "," && depth === 0) break;
          i++;
        }
        values[stack.join(".")] = source.slice(start, i).trim();
        stack.pop();
      }
    }
  };

  parseObject();
  return values;
}

export async function run(ctx) {
  const relative = "apps/web/src/shared/i18n/translations.ts";
  const file = path.join(ctx.repo, relative);
  if (!fs.existsSync(file)) return [blocked("I18-01", `${relative} not found`)];

  let en;
  let idLocale;
  try {
    const source = fs.readFileSync(file, "utf8");
    en = parseLocale(source, "\n  en: {");
    idLocale = parseLocale(source, "\n  id: {");
  } catch (error) {
    return [
      blocked("I18-01", `translations parse failed: ${error.message}`),
      blocked("I18-02", `translations parse failed: ${error.message}`)
    ];
  }

  const enKeys = Object.keys(en).sort();
  const idKeys = Object.keys(idLocale).sort();
  const missingInId = enKeys.filter((k) => !(k in idLocale));
  const missingInEn = idKeys.filter((k) => !(k in en));

  if (!ctx.defaultBranch) {
    return [
      blocked("I18-01", "default branch could not be resolved, so no baseline key set exists"),
      blocked("I18-02", "default branch could not be resolved, so no baseline key set exists")
    ];
  }
  const baselineResult = git(ctx.repo, ["show", `${ctx.defaultBranch}:${relative}`]);
  const baselineKeys =
    baselineResult.status === 0 ? Object.keys(parseLocale(baselineResult.stdout, "\n  en: {")).sort() : [];
  const removedFromBaseline = baselineKeys.filter((k) => !(k in en));

  const parity = {
    enCount: enKeys.length,
    idCount: idKeys.length,
    missingInId,
    missingInEn,
    baselineBranch: ctx.defaultBranch,
    baselineCount: baselineKeys.length,
    removedFromBaseline,
    parityOk: missingInId.length === 0 && missingInEn.length === 0,
    noBaselineKeyRemoved: removedFromBaseline.length === 0
  };
  writeJson(ctx.evidence, "i18n-parity.json", parity);

  const empty = enKeys.filter((k) => typeof idLocale[k] !== "string" || idLocale[k].trim() === "");
  const identical = enKeys.filter((k) => idLocale[k] === en[k]);

  const undeclared = [];
  const staleValue = [];
  const badCategory = [];
  for (const key of identical) {
    const entry = NON_TRANSLATABLE[key];
    if (!entry) {
      undeclared.push(key);
      continue;
    }
    if (entry.value !== en[key]) staleValue.push({ key, declared: entry.value, actual: en[key] });
    if (!CATEGORIES.includes(entry.category)) badCategory.push({ key, category: entry.category });
  }

  // A declaration whose key is translated again, or no longer exists, would
  // otherwise sit here forever as an unread authority.
  const staleEntries = Object.keys(NON_TRANSLATABLE).filter((key) => !(key in en) || idLocale[key] !== en[key]);

  writeText(
    ctx.evidence,
    "i18n-untranslated.txt",
    [
      "# keys whose id value is empty, or identical to en without a declared category",
      ...empty.map((k) => `${k}\tempty\t${JSON.stringify(en[k])}`),
      ...identical
        .filter((k) => !NON_TRANSLATABLE[k])
        .map((k) => `${k}\tidentical-not-declared\t${JSON.stringify(en[k])}`)
    ].join("\n") + "\n"
  );
  writeJson(ctx.evidence, "i18n-nontranslatable.json", {
    categories: CATEGORIES,
    declared: NON_TRANSLATABLE,
    identicalCount: identical.length,
    identicalKeys: identical,
    empty,
    undeclared,
    staleValue,
    badCategory,
    staleEntries
  });

  const i18n01ok = parity.parityOk && parity.noBaselineKeyRemoved;
  const i18n02ok =
    empty.length === 0 &&
    undeclared.length === 0 &&
    staleValue.length === 0 &&
    badCategory.length === 0 &&
    staleEntries.length === 0;

  return [
    row(
      "I18-01",
      i18n01ok,
      `${enKeys.length} en keys, ${idKeys.length} id keys, ${missingInId.length} missing in id, ${missingInEn.length} missing in en, ${removedFromBaseline.length} baseline keys removed`
    ),
    row(
      "I18-02",
      i18n02ok,
      `${empty.length} empty, ${identical.length} identical to en of which ${identical.length - undeclared.length} declared non-translatable, ${undeclared.length} undeclared, ${staleEntries.length} stale declarations`
    )
  ];
}

// Source-level rows. None of these needs a browser or a served candidate: they
// read the commit under test through git and the built package on disk.
import fs from "node:fs";
import path from "node:path";
import { git, row, blocked, writeJson, writeText, runProcess } from "../lib/harness.mjs";

export const ids = ["SC-01", "SC-02", "SC-03", "SC-05", "TK-01", "TK-02", "EX-01"];

const PALETTE = [
  "bg-(slate|blue|emerald|red|amber|purple|zinc|gray|neutral)-[0-9]",
  "text-(slate|blue|emerald|red|amber|purple)-[0-9]",
  "border-(slate|blue|emerald|red|amber|purple)-[0-9]",
  "ring-blue-"
].join("|");

// `git grep` exit 1 means "no match", which is the passing case. Each scan keeps
// its own text artifact even when empty, so an absent file can never be read as
// an absent scan.
function grepScan(ctx, { id, label, args, evidenceName }) {
  const result = runProcess("git", ["-C", ctx.repo, "grep", "-n", ...args]);
  const command = `git -C <repo> grep -n ${args.join(" ")}`;
  const matches = result.stdout.split("\n").filter(Boolean);
  writeText(
    ctx.evidence,
    evidenceName,
    [
      `row: ${id}`,
      `label: ${label}`,
      `command: ${command}`,
      `exit: ${result.status}`,
      `matches: ${matches.length}`,
      result.stderr ? `stderr: ${result.stderr.trim()}` : "",
      "",
      matches.join("\n"),
      matches.length ? "" : "(no matches)"
    ]
      .filter((line) => line !== "")
      .join("\n") + "\n"
  );
  if (result.status > 1) {
    return blocked(id, `git grep failed with exit ${result.status}: ${result.stderr.trim().slice(0, 200)}`);
  }
  const paths = args.slice(args.indexOf("--") + 1).join(", ");
  return { id, ok: matches.length === 0, blocked: false, detail: `${matches.length} matches in ${paths}` };
}

const DIST_PRIMITIVES = [
  "Card",
  "Button",
  "Badge",
  "Tabs",
  "Table",
  "Input",
  "ScrollArea",
  "Sheet",
  "CommandPalette",
  "Avatar"
];

function distRow(ctx) {
  const componentDir = path.join(ctx.repo, "packages", "ui", "dist", "components");
  const paletteRe = /(bg|text|border|ring)-(slate|blue|emerald|red|amber|purple|zinc|gray|neutral)-[0-9]/;
  const files = [];
  const missing = [];

  for (const name of DIST_PRIMITIVES) {
    const file = path.join(componentDir, `${name}.js`);
    if (!fs.existsSync(file)) {
      missing.push(name);
      continue;
    }
    const source = fs.readFileSync(file, "utf8");
    const paletteMatches = source.match(new RegExp(paletteRe.source, "g")) || [];
    files.push({
      name,
      paletteMatches,
      focusRing: /focus:ring/.test(source),
      hasBgPrimary: source.includes("bg-primary"),
      hasBgCard: source.includes("bg-card"),
      hasRoundedLg: source.includes("rounded-lg"),
      hasBackdropBlur: source.includes("backdrop-blur")
    });
  }

  // Reported, never decisive: a clock is not content.
  const newest = (dir) => {
    let newestMs = 0;
    const walk = (current) => {
      for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
        const full = path.join(current, entry.name);
        if (entry.isDirectory()) walk(full);
        else {
          const mtime = fs.statSync(full).mtimeMs;
          if (mtime > newestMs) newestMs = mtime;
        }
      }
    };
    if (fs.existsSync(dir)) walk(dir);
    return newestMs ? new Date(newestMs).toISOString() : null;
  };
  const freshness = {
    newestSrc: newest(path.join(ctx.repo, "packages", "ui", "src")),
    oldestDist: files.length
      ? new Date(Math.min(...files.map((f) => fs.statSync(path.join(componentDir, `${f.name}.js`)).mtimeMs))).toISOString()
      : null
  };

  const failures = [];
  if (missing.length) failures.push(`missing dist files: ${missing.join(", ")}`);
  for (const file of files) {
    if (file.paletteMatches.length) failures.push(`${file.name}.js carries ${file.paletteMatches.join(",")}`);
    if (file.focusRing) failures.push(`${file.name}.js carries focus:ring`);
  }
  const button = files.find((f) => f.name === "Button");
  if (button && !(button.hasBgPrimary && button.hasRoundedLg)) {
    failures.push("Button.js is missing bg-primary or rounded-lg");
  }
  const card = files.find((f) => f.name === "Card");
  if (card && !(card.hasBgCard && !card.hasBackdropBlur)) {
    failures.push("Card.js is missing bg-card or still carries backdrop-blur");
  }

  writeJson(ctx.evidence, "dist-scan.json", files);
  writeJson(ctx.evidence, "dist-freshness.json", freshness);

  return row(
    "SC-05",
    failures.length === 0,
    failures.length
      ? failures.join("; ")
      : `${files.length}/${DIST_PRIMITIVES.length} primitives clean; Button.js bg-primary+rounded-lg, Card.js bg-card without backdrop-blur`
  );
}

function blockOf(source, name) {
  const at = source.indexOf(name + " {");
  if (at < 0) return null;
  const start = source.indexOf("{", at) + 1;
  let depth = 1;
  let i = start;
  while (i < source.length && depth > 0) {
    if (source[i] === "{") depth++;
    else if (source[i] === "}") depth--;
    i++;
  }
  return source.slice(start, i - 1);
}

function declarations(text) {
  return [...text.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => ({ name: m[1], value: m[2].trim() }));
}

function tokensRow(ctx) {
  const file = path.join(ctx.uiRepo, "packages", "tokens", "theme.css");
  if (!fs.existsSync(file)) return blocked("TK-01", `theme.css not found at ${file}`);
  const source = fs.readFileSync(file, "utf8");

  const root = blockOf(source, ":root") || "";
  const dark = blockOf(source, ".dark") || "";
  const theme = blockOf(source, "@theme inline") || blockOf(source, "@theme") || "";

  const triplet = /^\d{1,3} \d{1,3}% \d{1,3}%$/;
  const isColour = (name) => !/^--(radius|font|motion|space|breakpoint)/.test(name);

  const rootColours = declarations(root).filter((d) => isColour(d.name));
  const darkColours = declarations(dark).filter((d) => isColour(d.name));
  const mappings = declarations(theme).filter((d) => d.name.startsWith("--color-"));

  const badTriplets = [...rootColours, ...darkColours].filter((d) => !triplet.test(d.value));
  const badMappings = mappings.filter((d) => !/^hsl\(var\(--[\w-]+\)\)$/.test(d.value));
  const sha = git(ctx.uiRepo, ["log", "-1", "--format=%H", "--", "packages/tokens/theme.css"]).stdout.trim();

  writeJson(ctx.evidence, "tokens-triplets.json", {
    file,
    themeCssCommit: sha,
    rootColourCount: rootColours.length,
    darkColourCount: darkColours.length,
    mappingCount: mappings.length,
    badTriplets,
    badMappings,
    sample: { root: rootColours.slice(0, 4), mappings: mappings.slice(0, 4) }
  });
  writeText(ctx.evidence, "theme-css-sha.txt", `${sha}\n`);

  const ok = rootColours.length > 0 && mappings.length > 0 && badTriplets.length === 0 && badMappings.length === 0;
  return row(
    "TK-01",
    ok,
    `${rootColours.length} :root and ${darkColours.length} .dark colour declarations, ${mappings.length} --color-* mappings, ${badTriplets.length} triplets outside the shape, ${badMappings.length} mappings missing hsl()`
  );
}

function exportsOf(readFile) {
  const names = new Set();
  for (const file of readFile.files) {
    const source = readFile.get(file);
    if (!source) continue;
    for (const m of source.matchAll(/export\s+(?:declare\s+)?(?:async\s+)?(?:const|let|function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)/g)) {
      names.add(m[1]);
    }
    for (const m of source.matchAll(/export\s*\{([^}]+)\}/g)) {
      for (const part of m[1].split(",")) {
        const name = part.trim().split(/\s+as\s+/).pop().trim();
        if (name) names.add(name);
      }
    }
    if (/export\s+default\b/.test(source)) names.add("default:" + file);
  }
  return names;
}

function exportsRow(ctx) {
  if (!ctx.defaultBranch) return blocked("EX-01", "default branch could not be resolved, so no baseline exists");
  const listing = (rev) =>
    git(ctx.repo, ["ls-tree", "-r", "--name-only", rev, "--", "packages/ui/src"]).stdout
      .split("\n")
      .filter((f) => f.endsWith(".ts") || f.endsWith(".tsx"));

  const read = (rev) => {
    const files = listing(rev);
    const get = (file) => {
      const result = git(ctx.repo, ["show", `${rev}:${file}`]);
      return result.status === 0 ? result.stdout : null;
    };
    return exportsOf({ files, get });
  };

  const candidate = read(ctx.aiSha);
  const baseline = read(ctx.defaultBranch);
  const missing = [...baseline].filter((name) => !candidate.has(name)).sort();
  const added = [...candidate].filter((name) => !baseline.has(name)).sort();

  writeJson(ctx.evidence, "ui-exports.json", {
    baselineBranch: ctx.defaultBranch,
    baselineCommit: git(ctx.repo, ["rev-parse", ctx.defaultBranch]).stdout.trim(),
    candidateCommit: ctx.aiSha,
    baselineExports: baseline.size,
    candidateExports: candidate.size,
    missing,
    added,
    baseline: [...baseline].sort(),
    candidate: [...candidate].sort()
  });

  return row(
    "EX-01",
    missing.length === 0,
    `${baseline.size} baseline exports, ${candidate.size} at the candidate, ${missing.length} missing${added.length ? `, ${added.length} added (informational)` : ""}`
  );
}

export async function run(ctx) {
  const results = [];

  results.push(
    grepScan(ctx, {
      id: "SC-01",
      label: "no stock slate background in the primitive layer",
      args: ["bg-slate-", ctx.aiSha, "--", "packages/ui/src"],
      evidenceName: "scan-sc01-bg-slate.txt"
    })
  );
  results.push(
    grepScan(ctx, {
      id: "SC-02",
      label: "no gradient utility in the landing module",
      args: ["bg-gradient", ctx.aiSha, "--", "apps/web/src/modules/landing"],
      evidenceName: "scan-sc02-bg-gradient.txt"
    })
  );
  results.push(
    grepScan(ctx, {
      id: "SC-03",
      label: "no stock palette utility survives anywhere",
      args: ["-E", PALETTE, ctx.aiSha, "--", "packages/ui/src", "apps/web/src"],
      evidenceName: "scan-sc03-palette.txt"
    })
  );
  results.push(
    grepScan(ctx, {
      id: "TK-02",
      label: "no raw hex in consumers",
      args: ["-E", "#[0-9a-fA-F]{3,8}", ctx.aiSha, "--", "apps/web/src", "packages/ui/src"],
      evidenceName: "scan-tk02-hex.txt"
    })
  );

  results.push(distRow(ctx));
  results.push(tokensRow(ctx));
  results.push(exportsRow(ctx));

  return results;
}

// SC-06: the scan roots the negative-assertion rows declare must cover the
// module closure the app actually mounts, not a hand-written file list.
//
// Defect this exists for: a scan over `modules/landing` reported zero while a
// palette utility lived in `modules/office`, outside the scanned surface.
import fs from "node:fs";
import path from "node:path";
import { row, blocked, writeJson, writeText } from "../lib/harness.mjs";

export const ids = ["SC-06"];

// The declared roots, straight from the matrix rows that own them.
const DECLARED_ROOTS = {
  "SC-01": ["packages/ui/src"],
  "SC-02": ["apps/web/src/modules/landing"],
  "SC-03": ["packages/ui/src", "apps/web/src"],
  "SC-05": ["packages/ui/dist"],
  "TK-02": ["apps/web/src", "packages/ui/src"]
};

// Route entry points, used only to report which route reaches each file.
const ROUTE_ENTRIES = {
  "/": ["app/App.tsx", "modules/landing/LandingPage.tsx"],
  "/console": ["app/App.tsx", "shell/CommandCenterLayout.tsx"],
  "/office": ["app/App.tsx", "shell/CommandCenterLayout.tsx", "modules/office/OfficeView.tsx"],
  "/deliberations": ["app/App.tsx", "shell/CommandCenterLayout.tsx", "modules/deliberations/DeliberationsView.tsx"],
  "/sdlc": ["app/App.tsx", "shell/CommandCenterLayout.tsx", "modules/sdlc/SdlcBoardView.tsx"],
  "/knowledge": ["app/App.tsx", "shell/CommandCenterLayout.tsx", "modules/knowledge/KnowledgeView.tsx"],
  "/chat": ["app/App.tsx", "shell/CommandCenterLayout.tsx", "modules/knowledge/KnowledgeChat.tsx"]
};

const exists = (p) => {
  try {
    return fs.statSync(p).isFile();
  } catch {
    return false;
  }
};

function resolveSpecifier(srcRoot, fromFile, specifier) {
  if (specifier.startsWith("@/")) return path.join(srcRoot, specifier.slice(2));
  if (specifier.startsWith(".")) return path.resolve(path.dirname(fromFile), specifier);
  return null;
}

function withExtension(base) {
  const candidates = [
    base,
    `${base}.tsx`,
    `${base}.ts`,
    `${base}.js`,
    `${base}.jsx`,
    path.join(base, "index.tsx"),
    path.join(base, "index.ts")
  ];
  for (const candidate of candidates) if (exists(candidate)) return path.normalize(candidate);
  return null;
}

function walk(srcRoot, entry, seen, importedBy) {
  const stack = [entry];
  while (stack.length) {
    const file = stack.pop();
    if (!file || seen.has(file)) continue;
    seen.add(file);
    const source = fs.readFileSync(file, "utf8");
    const specifiers = [
      ...[...source.matchAll(/(?:import|export)[\s\S]{0,400}?from\s+["']([^"']+)["']/g)].map((m) => m[1]),
      ...[...source.matchAll(/import\(\s*["']([^"']+)["']\s*\)/g)].map((m) => m[1]),
      ...[...source.matchAll(/^import\s+["']([^"']+)["']/gm)].map((m) => m[1])
    ];
    for (const specifier of specifiers) {
      const base = resolveSpecifier(srcRoot, file, specifier);
      if (!base) continue;
      const resolved = withExtension(base);
      if (!resolved || !resolved.startsWith(srcRoot) || seen.has(resolved)) continue;
      if (!importedBy.has(resolved)) importedBy.set(resolved, new Set());
      importedBy.get(resolved).add(file);
      stack.push(resolved);
    }
  }
}

// A file under apps/web/src is covered when a declared root that names that tree
// is a prefix of it. SC-01 and SC-05 root at packages/ui and can never cover a
// web file, which is the point: the row that covers it must say so.
function coveredBy(webRelative) {
  const absolute = "apps/web/src/" + webRelative;
  const hits = [];
  for (const [id, roots] of Object.entries(DECLARED_ROOTS)) {
    for (const root of roots) {
      if (absolute === root || absolute.startsWith(root + "/")) hits.push(id);
    }
  }
  return [...new Set(hits)];
}

export async function run(ctx) {
  const srcRoot = path.join(ctx.repo, "apps", "web", "src");
  const entry = path.join(srcRoot, "main.tsx");
  if (!exists(entry)) return [blocked("SC-06", `no entry point at ${entry}`)];

  const seen = new Set();
  const importedBy = new Map();
  walk(srcRoot, entry, seen, importedBy);

  const files = [...seen].map((f) => path.relative(srcRoot, f).split(path.sep).join("/")).sort();
  const tsx = files.filter((f) => f.endsWith(".tsx"));

  const allTsxOnDisk = [];
  const collect = (dir) => {
    for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, item.name);
      if (item.isDirectory()) collect(full);
      else if (item.name.endsWith(".tsx")) allTsxOnDisk.push(path.relative(srcRoot, full).split(path.sep).join("/"));
    }
  };
  collect(srcRoot);

  const routeReach = {};
  for (const [route, entries] of Object.entries(ROUTE_ENTRIES)) {
    const reached = new Set();
    for (const relative of entries) {
      const file = path.join(srcRoot, relative);
      if (exists(file)) walk(srcRoot, file, reached, new Map());
    }
    routeReach[route] = [...reached].map((f) => path.relative(srcRoot, f).split(path.sep).join("/"));
  }

  const rows = files.map((file) => ({
    file,
    coveredBy: coveredBy(file),
    routes: Object.entries(routeReach)
      .filter(([, set]) => set.includes(file))
      .map(([route]) => route)
  }));

  const uncovered = rows.filter((r) => r.coveredBy.length === 0);
  const orphanTsx = allTsxOnDisk.filter((f) => !files.includes(f)).sort();

  writeJson(ctx.evidence, "scope-closure.json", {
    closureSize: files.length,
    tsxCount: tsx.length,
    tsxOnDisk: allTsxOnDisk.length,
    declaredRoots: DECLARED_ROOTS,
    files: rows,
    uncovered,
    orphanTsx
  });
  writeText(
    ctx.evidence,
    "scope-coverage.txt",
    rows.map((r) => `${r.file}\t${r.coveredBy.join(",") || "UNCOVERED"}\t${r.routes.join(" ")}`).join("\n") + "\n"
  );
  writeText(
    ctx.evidence,
    "scope-out-of-surface.txt",
    (uncovered.length ? uncovered.map((r) => `${r.file}\tno declared root covers this file`) : []).join("\n") +
      (uncovered.length ? "\n" : "")
  );

  const ok = uncovered.length === 0 && orphanTsx.length === 0;
  const detail = `${files.length} files in the closure from main.tsx, ${tsx.length} .tsx of ${allTsxOnDisk.length} on disk, ${uncovered.length} uncovered, ${orphanTsx.length} .tsx outside the closure`;
  return [row("SC-06", ok, detail)];
}

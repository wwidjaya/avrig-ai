#!/usr/bin/env node
// AVRIG-00002 QA harness. The only entry point a reader needs.
//
//   node apps/web/scripts/qa/run.mjs --base <url> --evidence <dir> --pair <sha>:<sha>
//
// It runs every row in the plan's Test Specification and Validation Matrix,
// prints one line per row, and finishes with the verdict line. Exit code 1 when
// any row fails, 2 when the run could not be performed at all.
import path from "node:path";
import {
  buildContext,
  parseArgs,
  resolveDefaultBranch,
  git,
  blocked,
  fail,
  writeJson,
  writeText,
  usage
} from "./lib/harness.mjs";
import { launch } from "./lib/browser.mjs";

import * as staticRows from "./rows/static.mjs";
import * as scopeRows from "./rows/scope.mjs";
import * as i18nRows from "./rows/i18n.mjs";
import * as surfacesRows from "./rows/surfaces.mjs";
import * as computedRows from "./rows/computed.mjs";
import * as layoutRows from "./rows/layout.mjs";
import * as interactiveRows from "./rows/interactive.mjs";

const MODULES = [
  { name: "static", module: staticRows },
  { name: "scope", module: scopeRows },
  { name: "i18n", module: i18nRows },
  { name: "surfaces", module: surfacesRows },
  { name: "computed", module: computedRows },
  { name: "layout", module: layoutRows },
  { name: "interactive", module: interactiveRows }
];

// Every row the matrix declares, in matrix order. A module that forgets one, or
// invents one, fails the run rather than quietly shrinking the denominator.
const EXPECTED = [
  "ST-01",
  "ST-02",
  "ST-03",
  "ST-04",
  "ST-05",
  "ST-06",
  "SC-01",
  "SC-02",
  "SC-03",
  "SC-04",
  "SC-05",
  "SC-06",
  "SC-07",
  "SC-08",
  "SC-09",
  "SC-10",
  "TK-01",
  "TK-02",
  "TK-03",
  "CT-01",
  "CT-02",
  "CT-03",
  "CT-04",
  "LY-01",
  "LY-02",
  "LY-03",
  "CP-01",
  "EX-01",
  "I18-01",
  "I18-02",
  "PIL-01",
  "BR-01",
  "BR-02",
  "BR-03",
  "BR-04",
  "KB-01",
  "KB-02",
  "KB-03",
  "KB-04"
];

async function reachable(baseUrl) {
  try {
    const response = await fetch(baseUrl, { redirect: "follow", signal: AbortSignal.timeout(8000) });
    return { ok: true, status: response.status };
  } catch (error) {
    return { ok: false, error: String(error && error.message ? error.message : error) };
  }
}

function verdictLine(ctx, status, passed, total, extra = "") {
  return `AVRIG-00002 ${ctx.candidate} avrig-ai@${ctx.aiSha} avrig-ui@${ctx.uiSha} ${status} ${passed}/${total} evidence ${ctx.evidenceLabel}${extra}`;
}

function sortByExpected(results) {
  const index = new Map(EXPECTED.map((id, i) => [id, i]));
  return [...results].sort((a, b) => (index.get(a.id) ?? 999) - (index.get(b.id) ?? 999));
}

// HEAD proves the working tree is the candidate. It does not prove the candidate
// is the commit the candidate tag names, so --tag is resolved in both
// repositories and compared with the pair. An untagged tree is not a candidate.
function resolveTag(ctx) {
  const resolve = (repo) => {
    const result = git(repo, ["rev-parse", "--verify", "--quiet", `${ctx.tag}^{commit}`]);
    return result.status === 0 ? result.stdout.trim() : null;
  };
  const ai = resolve(ctx.repo);
  const ui = resolve(ctx.uiRepo);
  return {
    name: ctx.tag,
    ai: { commit: ai, matchesPair: Boolean(ai) && ai.startsWith(ctx.aiSha) },
    ui: { commit: ui, matchesPair: Boolean(ui) && ui.startsWith(ctx.uiSha) }
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const ctx = buildContext(args);

  // A subset run is a development run. It reports only the rows it selected and
  // never prints the plan's verdict line, so a green subset can never be read as
  // a green candidate.
  const selected = ctx.only
    ? EXPECTED.filter((id) => ctx.only.includes(id))
    : EXPECTED;
  if (ctx.only) {
    const unknown = ctx.only.filter((id) => !EXPECTED.includes(id));
    if (unknown.length) fail(`--only names rows that are not in the matrix: ${unknown.join(", ")}`);
    if (!selected.length) fail("--only selected nothing");
  }

  // The pair names the tree under test. If HEAD has moved on, the evidence
  // would describe a tree nobody can check out again.
  const head = git(ctx.repo, ["rev-parse", "HEAD"]);
  const headSha = head.status === 0 ? head.stdout.trim() : null;
  const headMatches = Boolean(headSha) && headSha.startsWith(ctx.aiSha);
  const resolved = resolveDefaultBranch(ctx.repo);
  ctx.defaultBranch = resolved.name;
  const tag = ctx.tag ? resolveTag(ctx) : null;

  const preflight = {
    base: ctx.base,
    evidence: ctx.evidenceLabel,
    candidate: ctx.candidate,
    pair: `${ctx.aiSha}:${ctx.uiSha}`,
    tag,
    repo: ctx.repo,
    uiRepo: ctx.uiRepo,
    head: headSha,
    headMatchesPair: headMatches,
    defaultBranch: resolved,
    node: process.version
  };

  const probe = await reachable(ctx.base);
  preflight.baseReachable = probe;

  const results = [];
  const only = ctx.only;

  if (!probe.ok) {
    for (const id of selected) results.push(blocked(id, `base ${ctx.base} is not reachable: ${probe.error}`));
    ctx.browser = null;
  } else {
    ctx.browser = await launch();
    try {
      for (const entry of MODULES) {
        const declared = entry.module.ids ?? [];
        if (only && !declared.some((id) => only.includes(id))) continue;
        try {
          const moduleResults = await entry.module.run(ctx);
          results.push(
            ...(ctx.only ? moduleResults.filter((result) => selected.includes(result.id)) : moduleResults)
          );
        } catch (error) {
          const message = String(error && error.message ? error.message : error).slice(0, 300);
          const failing = ctx.only ? declared.filter((id) => selected.includes(id)) : declared;
          for (const id of failing) results.push(blocked(id, `${entry.name} module threw: ${message}`));
        }
      }
    } finally {
      await ctx.browser.close();
    }
  }

  // Coverage: exactly the declared rows, no duplicates, nothing missing.
  const seen = new Map();
  for (const result of results) seen.set(result.id, (seen.get(result.id) ?? 0) + 1);
  const missing = selected.filter((id) => !seen.has(id));
  const duplicated = [...seen.entries()].filter(([, count]) => count > 1).map(([id]) => id);
  const unexpected = [...seen.keys()].filter((id) => !selected.includes(id));
  for (const id of missing) results.push(blocked(id, "no module produced this row"));

  const ordered = sortByExpected(results);
  const passed = ordered.filter((result) => result.ok).length;
  const blockedRows = ordered.filter((result) => result.blocked);
  const total = selected.length;
  const failed = ordered.filter((result) => !result.ok && !result.blocked);

  // A structural problem is not an advisory: evidence that describes a tree
  // nobody can check out again, or a tree the candidate tag does not name, is
  // not evidence. Each one forces BLOCKED and exit 2 rather than printing a
  // warning above a green verdict line.
  const structural = [];
  if (missing.length) structural.push({ code: "rows-missing", message: `rows missing: ${missing.join(",")}` });
  if (duplicated.length) structural.push({ code: "rows-duplicated", message: `rows duplicated: ${duplicated.join(",")}` });
  if (unexpected.length) structural.push({ code: "rows-unexpected", message: `rows not in the matrix: ${unexpected.join(",")}` });
  if (!headMatches) structural.push({ code: "head-mismatch", message: `HEAD ${headSha} does not equal the pair's avrig-ai commit ${ctx.aiSha}` });
  if (tag) {
    if (!tag.ai.commit) {
      structural.push({ code: "tag-ai-missing", message: `--tag ${tag.name} does not resolve in avrig-ai (${ctx.repo})` });
    } else if (!tag.ai.matchesPair) {
      structural.push({ code: "tag-ai-mismatch", message: `--tag ${tag.name} resolves to ${tag.ai.commit} in avrig-ai, not the pair's ${ctx.aiSha}` });
    }
    if (!tag.ui.commit) {
      structural.push({ code: "tag-ui-missing", message: `--tag ${tag.name} does not resolve in avrig-ui (${ctx.uiRepo})` });
    } else if (!tag.ui.matchesPair) {
      structural.push({ code: "tag-ui-mismatch", message: `--tag ${tag.name} resolves to ${tag.ui.commit} in avrig-ui, not the pair's ${ctx.uiSha}` });
    }
  }
  const fatalStructural = structural.length > 0;

  const status = !probe.ok || blockedRows.length || fatalStructural ? "BLOCKED" : failed.length ? "FAIL" : "PASS";
  const extraParts = [];
  if (blockedRows.length) extraParts.push(`blocked=${blockedRows.map((r) => r.id).join(",")}`);
  if (fatalStructural) extraParts.push(`structural=${structural.map((p) => p.code).join(",")}`);
  const extra = extraParts.length ? ` ${extraParts.join(" ")}` : "";
  const verdict = ctx.only
    ? `SUBSET ${selected.join(",")} ${verdictLine(ctx, status, passed, total, extra)}`
    : verdictLine(ctx, status, passed, total, extra);

  for (const result of ordered) {
    const label = result.blocked ? "BLOCK" : result.ok ? "pass" : "FAIL";
    process.stdout.write(`${result.id.padEnd(6)} ${label.padEnd(5)} ${result.detail}\n`);
  }

  for (const problem of structural) process.stdout.write(`HARNESS ${problem.message}\n`);

  process.stdout.write(`\n${verdict}\n`);

  writeJson(ctx.evidence, "run.json", {
    ...preflight,
    verdict,
    status,
    passed,
    total,
    subset: ctx.only ? selected : null,
    fatal: fatalStructural,
    structural,
    structuralCodes: structural.map((problem) => problem.code)
  });
  writeJson(
    ctx.evidence,
    "result.json",
    ordered.map((result) => ({ id: result.id, ok: result.ok, blocked: result.blocked, detail: result.detail }))
  );
  writeText(
    ctx.evidence,
    "RESULT.md",
    [
      `# ${ctx.candidate} QA result`,
      "",
      ctx.only ? `Subset run: ${selected.join(", ")}. This is not the plan verdict line.` : "",
      "",
      "```text",
      verdict,
      "```",
      "",
      `Base URL: ${ctx.base}`,
      `Pair: avrig-ai@${ctx.aiSha} avrig-ui@${ctx.uiSha}`,
      `HEAD at run time: ${headSha ?? "unknown"}`,
      `Candidate tag: ${tag ? `${tag.name} avrig-ai=${tag.ai.commit ?? "unresolved"} avrig-ui=${tag.ui.commit ?? "unresolved"}` : "not asserted (--tag was not given)"}`,
      `Default branch: ${resolved.name ?? "unresolved"} (${resolved.decided})`,
      "",
      "| Row | Verdict | Detail |",
      "|---|---|---|",
      ...ordered.map((result) => `| ${result.id} | ${result.blocked ? "block" : result.ok ? "pass" : "fail"} | ${result.detail.replace(/\|/g, "\\|")} |`),
      "",
      structural.length
        ? `Harness: FATAL, ${structural.map((problem) => problem.message).join("; ")}`
        : "Harness: every declared row was produced exactly once",
      ""
    ].join("\n")
  );

  if (!probe.ok || blockedRows.length || fatalStructural) process.exit(2);
  process.exit(failed.length ? 1 : 0);
}

main().catch((error) => {
  process.stderr.write(`qa: fatal: ${error && error.stack ? error.stack : error}\n`);
  process.stderr.write(`${usage()}\n`);
  process.exit(2);
});

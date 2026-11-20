// Shared plumbing for the AVRIG-00002 QA matrix.
//
// Nothing here knows about a port, a worktree path or a candidate number. Every
// one of those arrives as an argument, so the same file runs against a worktree
// candidate and against a deployment.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const FLAGS = {
  "--base": "base",
  "--evidence": "evidence",
  "--pair": "pair",
  "--candidate": "candidate",
  "--repo": "repo",
  "--ui-repo": "uiRepo",
  "--only": "only"
};

export function fail(message) {
  process.stderr.write(`qa: ${message}\n`);
  process.exit(2);
}

export function usage() {
  return [
    "usage: node apps/web/scripts/qa/run.mjs --base <url> --evidence <dir> --pair <avrig-ai-sha>:<avrig-ui-sha>",
    "",
    "  --base        base URL of the served candidate, for example http://127.0.0.1:5173",
    "  --evidence    evidence directory, for example plans/evidence/AVRIG-00002/rc.002",
    "  --pair        the two commits under test, colon separated",
    "  --candidate   candidate label used in the verdict line (default: evidence folder name)",
    "  --repo        avrig-ai checkout (default: this repository)",
    "  --ui-repo     avrig-ui checkout (default: sibling ../avrig-ui)",
    "  --only        comma separated row ids, for working on a failing row"
  ].join("\n");
}

export function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    let raw = argv[i];
    if (raw === "--help" || raw === "-h") {
      process.stdout.write(usage() + "\n");
      process.exit(0);
    }
    if (!raw.startsWith("--")) fail(`unexpected argument: ${raw}\n\n${usage()}`);
    let value = null;
    const eq = raw.indexOf("=");
    if (eq > 0) {
      value = raw.slice(eq + 1);
      raw = raw.slice(0, eq);
    }
    const key = FLAGS[raw];
    if (!key) fail(`unknown flag: ${raw}\n\n${usage()}`);
    if (value === null) {
      value = argv[++i];
      if (value === undefined) fail(`flag ${raw} needs a value`);
    }
    out[key] = value;
  }
  return out;
}

// Never throws: exit status 1 from `git grep` means "no match", which is a
// result rather than an error.
export function runProcess(bin, args, opts = {}) {
  try {
    const stdout = execFileSync(bin, args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      maxBuffer: 64 * 1024 * 1024,
      ...opts
    });
    return { status: 0, stdout, stderr: "" };
  } catch (error) {
    return {
      status: typeof error.status === "number" ? error.status : -1,
      stdout: error.stdout ? String(error.stdout) : "",
      stderr: error.stderr ? String(error.stderr) : String(error.message ?? error)
    };
  }
}

export function git(repo, args, opts) {
  return runProcess("git", ["-C", repo, ...args], opts);
}

// Default branch per repository, resolved rather than assumed. The deciding
// step is reported so a reader can see why the name was chosen.
export function resolveDefaultBranch(repo) {
  const remoteHead = git(repo, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]);
  if (remoteHead.status === 0) {
    const name = remoteHead.stdout.trim().replace(/^origin\//, "");
    if (name && git(repo, ["rev-parse", "--verify", "--quiet", `refs/heads/${name}`]).status === 0) {
      return { name, decided: "origin/HEAD" };
    }
  }
  const refs = git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads"]);
  const branches = refs.status === 0 ? refs.stdout.split("\n").map((s) => s.trim()).filter(Boolean) : [];
  for (const candidate of ["main", "master"]) {
    if (branches.includes(candidate)) return { name: candidate, decided: "local long-lived branch" };
  }
  if (branches.length === 1) return { name: branches[0], decided: "only local branch" };
  return { name: null, decided: "unresolved", branches };
}

export function buildContext(args) {
  if (!args.base) fail(`--base is required\n\n${usage()}`);
  if (!args.evidence) fail(`--evidence is required\n\n${usage()}`);
  if (!args.pair) fail(`--pair is required\n\n${usage()}`);

  const [aiSha, uiSha] = String(args.pair).split(":");
  const sha = /^[0-9a-f]{7,40}$/i;
  if (!sha.test(aiSha ?? "") || !sha.test(uiSha ?? "")) {
    fail(`--pair must be <avrig-ai-sha>:<avrig-ui-sha>, got "${args.pair}"`);
  }

  // HERE is apps/web/scripts/qa/lib, so the repository root is five levels up.
  const repo = path.resolve(args.repo ?? path.join(HERE, "..", "..", "..", "..", ".."));
  const uiRepo = path.resolve(args.uiRepo ?? path.join(repo, "..", "avrig-ui"));
  const evidence = path.resolve(args.evidence);
  fs.mkdirSync(evidence, { recursive: true });

  const relativeEvidence = path.relative(repo, evidence);
  const insideRepo = !relativeEvidence.startsWith("..") && !path.isAbsolute(relativeEvidence);
  const evidenceLabel = insideRepo
    ? relativeEvidence.split(path.sep).join("/") + "/"
    : evidence.split(path.sep).join("/") + "/";

  const candidate = args.candidate ?? path.basename(evidence);

  return {
    base: String(args.base).replace(/\/+$/, ""),
    evidence,
    evidenceLabel,
    candidate,
    repo,
    uiRepo,
    aiSha,
    uiSha,
    only: args.only ? args.only.split(",").map((s) => s.trim()).filter(Boolean) : null
  };
}

export function writeJson(dir, name, data) {
  const target = path.join(dir, name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(data, null, 1));
  return target;
}

export function writeText(dir, name, text) {
  const target = path.join(dir, name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, text);
  return target;
}

// A row result. `ok` is the verdict; `detail` is the one line a reader needs.
export function row(id, ok, detail, extra = {}) {
  return { id, ok: Boolean(ok), detail, blocked: false, ...extra };
}

export function blocked(id, reason) {
  return { id, ok: false, blocked: true, detail: reason };
}

export function countBy(list, key) {
  const out = {};
  for (const item of list) {
    const k = typeof key === "function" ? key(item) : item[key];
    out[k] = (out[k] ?? 0) + 1;
  }
  return out;
}

export function unique(list) {
  return [...new Set(list)];
}

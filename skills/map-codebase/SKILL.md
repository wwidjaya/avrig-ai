---
name: map-codebase
description: "Use for any question about a codebase, its architecture, file relationships, or project content — especially when graphify-out/ exists, where the question should be treated as a graphify query first. Turns any input (code, docs, papers, images, videos) into a persistent knowledge graph with god nodes, community detection, and query/path/explain tools."
---

# /map-codebase

Build and query a persistent knowledge graph from code, documents, papers, images, and media.

## Core Rules

1. If `graphify-out/graph.json` exists and the user asks a codebase question, run:

   ```powershell
   graphify.exe query "<question>"
   ```
   (On Windows, if `graphify.exe` is not resolved in PATH, use `D:\miniconda3\envs\kb\Scripts\graphify.exe query "<question>"`).

   Do not rebuild unless explicitly requested.

2. If no path is supplied, use `.`.

3. Never ask for an API key. Code extraction is AST-based. Semantic extraction may use Gemini when `GEMINI_API_KEY` or `GOOGLE_API_KEY` exists; otherwise use the host agent.

4. Never invent relationships. Mark uncertain relationships `AMBIGUOUS`.

5. Preserve token costs, cohesion scores, extraction failures, skipped files, and graph-health warnings.

## Commands

```text
/map-codebase [path]                 Build graph
/map-codebase [path] --mode deep     Deeper semantic extraction
/map-codebase [path] --update        Process changed files only
/map-codebase [path] --directed      Preserve edge direction
/map-codebase [path] --cluster-only  Recluster existing graph
/map-codebase [path] --no-viz        Skip HTML
/map-codebase [path] --wiki          Generate wiki
/map-codebase [path] --obsidian      Generate Obsidian vault
/map-codebase [path] --svg           Export SVG
/map-codebase [path] --graphml       Export GraphML
/map-codebase [path] --neo4j         Export Neo4j Cypher
/map-codebase [path] --falkordb      Export FalkorDB Cypher
/map-codebase [path] --mcp           Start MCP server
/map-codebase [path] --watch         Watch for changes

/map-codebase query "<question>"      Query graph
/map-codebase path "<A>" "<B>"        Find shortest path
/map-codebase explain "<node>"        Explain node
/map-codebase add <url>               Add external content
```

For `--help` or `-h`, print the command list and stop.

## Build Workflow

### 1. Prepare

Ensure `graphify` is installed and record its Python interpreter in:

```text
graphify-out/.graphify_python
```

For GitHub URLs, multiple repositories, or merged paths, follow `references/github-and-merge.md`.

### 2. Detect

Run graphify detection and summarize:

```text
Corpus: X files · ~Y words
  code: N
  docs: N
  papers: N
  images: N
  video: N
```

Stop if no supported files exist.

Report skipped sensitive files.

If the corpus exceeds 500 files or 2M words, warn the user and suggest narrowing to a major subdirectory when possible.

For audio/video, follow `references/transcribe.md`.

### 3. Extract

Run structural and semantic extraction in parallel.

**Code**

* Use graphify AST extraction.
* No LLM required.

**Docs / papers / images**

* Check semantic cache first.
* Process only uncached files.
* Group related files into chunks of ~20–25.
* Images get individual chunks.
* Dispatch all extraction agents in parallel.
* Use `references/extraction-spec.md`.
* Pass `DEEP_MODE=true` when `--mode deep`.

If Gemini credentials exist, graphify may perform semantic extraction directly instead.

Failed chunks must be reported. Stop if more than half fail.

Merge:

```text
AST + cached semantic + new semantic
    ↓
graphify-out/.graphify_extract.json
```

### 4. Build and Analyze

Build the graph, then:

* cluster communities
* calculate cohesion
* identify god nodes
* identify surprising connections
* generate suggested questions
* run graph-health diagnostics
* assign short community labels

Never overwrite a valid graph with an empty or unexpectedly smaller graph.

Generate:

```text
graphify-out/
├── graph.json
├── GRAPH_REPORT.md
└── graph.html
```

Generate optional exports only when requested.

See `references/exports.md`.

### 5. Finalize

Save the manifest for incremental updates, update `cost.json`, and remove temporary extraction files.

Report:

```text
Graph complete.

graph.html       Interactive graph
GRAPH_REPORT.md  Audit/report
graph.json       GraphRAG-ready graph
```

Also summarize:

* God Nodes
* Surprising Connections
* Suggested Questions
* graph-health warnings
* token usage

Then offer the most interesting suggested question for exploration.

## Query Existing Graph

Existing graph always takes priority for codebase questions.

```bash
graphify query "<question>"
```

Use BFS by default and DFS when tracing a specific path.

Expand user terminology against graph vocabulary before traversal.

Answer only from graph evidence and include `source_location` for specific claims.

If the CLI query fails, use NetworkX over `graphify-out/graph.json`.

Detailed query behavior:
`references/query.md`

## Specialized Operations

Use reference files instead of duplicating their procedures here:

```text
references/github-and-merge.md  GitHub/multi-repo
references/transcribe.md        Audio/video
references/extraction-spec.md   Semantic extraction
references/update.md            Update/recluster
references/query.md             Query/path/explain
references/add-watch.md         Add/watch
references/exports.md           Export formats
references/hooks.md             Commit hooks/CLAUDE.md
```

## Integrity Rules

* Never invent edges.
* Use `AMBIGUOUS` when uncertain.
* Never hide extraction failures.
* Never silently overwrite a larger graph with a smaller one.
* Always report token cost.
* Always expose raw cohesion scores.
* Warn before visualizing graphs above 5,000 nodes.


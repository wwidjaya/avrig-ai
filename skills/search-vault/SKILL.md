---
name: search-vault
description: Search D:/Cloud/OneDrive/AI/Personal/vault — PRIMARY: hybrid RAG via /search service; FALLBACK: weighted keyword grep
---

## search-vault

Hybrid vault search: semantic retrieval via the KB `/search` service (Qdrant dense+sparse → rerank → SearXNG web fallback), falling back to a weighted keyword grep when the service is unreachable or returns nothing.

### Primary (semantic)

- **Windows:** `pwsh "$env:OPENCODE_CONFIG_DIR/.opencode/skills/search-vault/rag-search.ps1" -Query "<question>"` — optional `-TopK 5` (1–10, default 5)
- **Linux/WSL:** `bash "$OPENCODE_CONFIG_DIR/.opencode/skills/search-vault/rag-search.sh" -q "<question>"` — optional `-n 5`

Each hit prints `[rank] [type] score | title`, filepath, snippet. `type: vault` = local note (read full file at Path); `type: web` = external source. Bracketed params like `[-TopK 5]` are docs only — never include literal `[ ]` in a real command.

### Fallback (keyword grep)

Used only if primary is empty/unreachable:

- **Linux/WSL:** `bash "$OPENCODE_CONFIG_DIR/.opencode/skills/search-vault/search-vault.sh" -k "term1" -k "term2"` — optional `-n 5`
- **Windows:** `pwsh "$env:OPENCODE_CONFIG_DIR/.opencode/skills/search-vault/search-vault.ps1" -Keywords "term1 term2"` — optional `-TopN 5`, `-VaultPath "<path>"`

Returns top N files with relevance scores (title match ×10, heading ×5, body ×1).

### Synthesize

Read the top hits; open the full vault file at `Path` for complete info (snippets truncate to ~200 chars).
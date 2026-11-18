---
name: config-deerflow
description: Update DeerFlow LLM model configuration and API keys in WSL research instance.
---

# config-deerflow

Skill for managing DeerFlow model providers and API keys.

## Usage

### WSL (bash)
Run from within the WSL research instance to update the lead agent model:
```bash
./update-model.sh -n "model-name" -u "provider-class" -m "llm-model-id" -b "api-base-url" -k "api-key"
```

### PowerShell (Host)
Update from Windows host:
```powershell
./update-model.ps1 -Name "model-name" -Use "provider-class" -Model "llm-model-id" -BaseUrl "api-base-url" -Key "api-key"
```

## Arguments
- `-n` / `--name`: Internal name for the model (e.g., `free`).
- `-u` / `--use`: Provider class path (e.g., `deerflow.models.patched_openai:PatchedChatOpenAI`).
- `-m` / `--model`: The specific LLM model ID (e.g., `free`).
- `-b` / `--base-url`: API base URL (e.g., `https://llmrouter.wirianto.ai/v1`).
- `-k` / `--key`: API key. If omitted, uses `$LLMROUTER_API_KEY` or existing env var.

## Workflow
1. Backs up `/etc/deer-flow/config.yaml`.
2. Updates the `models` list.
3. Sets the target model as the first entry (DeerFlow default lead agent).
4. Updates `/etc/deer-flow/.env` with API key if provided.
5. Restarts `deerflow` service via systemd.
6. Verifies update via `/api/models` endpoint.

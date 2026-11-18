---
title: "Plan: Switch Windows Native Reranker to CPU Execution Provider"
status: done
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - backend
  - performance
  - reranker
---

# Plan: Switch Windows Native Reranker to CPU Execution Provider

## Objective
Reduce knowledge rerank latency on the Windows native daemon from ~17.2s to ~0.1s by changing `device = "xpu"` (DirectML GPU EP) to `device = "cpu"` (AVX2/AVX-512 CPU EP) in `D:\avrig\config\reranker.toml`.

---

## 1. Problem Statement & Root Cause
- Benchmark verified that `bge-reranker-v2-m3` on the integrated Intel Arc GPU via ONNX DirectML takes **17,200 ms** per batch of 2 documents due to DirectX 12 buffer transfer and shader compilation overhead.
- Running the exact same model on CPU (`CPUExecutionProvider`) takes **105 ms** (a 160x speedup).

---

## 2. Implementation Steps

### Phase 1: Configuration Update
- **Assignee:** `Infra`
- Modify `D:\avrig\config\reranker.toml`:
  - Set `device = "cpu"` under `[reranker]`.
- Modify repository baseline `D:\Cloud\OneDrive\AI\Agentic\avrig-api\config\reranker.toml`:
  - Set `device = "cpu"` under `[reranker]`.
- **Pass Criteria:** Both TOML files parse cleanly and have `device = "cpu"`.

### Phase 2: Service Restart
- **Assignee:** `Infra`
- Restart Windows `avrig` service via elevated PowerShell:
  ```powershell
  Restart-Service avrig
  Get-Service avrig
  ```
- Inspect startup log at `D:\avrig\logs\avrig.log` to confirm initialization with CPU Execution Provider.
- **Pass Criteria:** Service status is `Running` and no crash or initialization errors appear in logs.

### Phase 3: Live Verification & Testing
- **Assignee:** `Infra`
- **Isolated Component Verification (Windows Host):**
  - Execute probe via PowerShell:
    ```powershell
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/reranker" -Method Post -ContentType "application/json" -Body '{"query":"what is the purpose of life","documents":["42 is the answer","france is in europe"]}'
    ```
  - **Pass Criteria:** Response status is HTTP 200, returns scored documents, and execution latency is < 300 ms.
- **End-to-End Integration Verification (WSL):**
  - Run `ks_timing.sh` or curl via `https://api.avrig.ai/reranker` and `POST /v1/search`.
  - **Pass Criteria:** Total search latency drops from ~18s to < 1.0s, returning proper relevance ranking and citations.
- **Documentation:**
  - Record the CPU latency benchmark and configuration change in `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\avrig-ai\infra\Infrastructure.md` under recent operational changes.

---

## 3. Rollback Strategy
If the service fails to start or CPU execution provider fails:
1. Revert `device = "cpu"` back to `device = "xpu"` in `D:\avrig\config\reranker.toml`.
2. Run `Restart-Service avrig` in elevated PowerShell.
3. Confirm service health at `http://127.0.0.1:8000/reranker`.

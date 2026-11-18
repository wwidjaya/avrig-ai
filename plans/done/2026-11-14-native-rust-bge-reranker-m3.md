# Plan: Native Rust BGE-M3 Reranker Service (`/reranker`) with XPU on Windows `avrig` Service
status: completed
source-of-truth: true

## 1. Executive Summary & Architecture

The Windows background service is consolidated under a single, unified name: **`avrig`** (renamed from `avrig-watcher`).
- **Service Name:** `avrig`
- **Display Name:** `avrig Windows Runtime Node`
- **Description:** `Unified cross-platform avrig runtime node hosting directory ingestion watcher and hardware-accelerated (XPU) neural cross-encoder reranker.`
- **Active Node Roles on Windows:** Both `"watcher"` and `"reranker"` are activated concurrently in `D:\avrig\config\config.toml`:
  ```toml
  [node]
  id = "avrig-windows-node"
  roles = ["watcher", "reranker"]
  ```
- **Reranker Endpoint:** `POST /reranker` (and `POST /api/v1/reranker`) listening on `127.0.0.1:8001`.
- **Hardware Acceleration (XPU):** DirectML (`ort::ep::DirectML`) running natively on the Windows host to leverage GPUs, iGPUs, and NPUs with low-latency cross-encoder scoring.

---

## 2. Configuration & Role Topology

### 2.1 Node Configuration (`D:\avrig\config\config.toml` & `avrig-api\config\config.toml`)
```toml
[node]
id = "avrig-windows-node"
roles = ["watcher", "reranker"]

[logging]
level = "info"
directory = "logs"
max_size_mb = 10
max_archive_files = 5
```

### 2.2 Reranker Role Configuration (`config/reranker.toml`)
```toml
[reranker]
host = "127.0.0.1"
port = 8001
model = "bge-reranker-v2-m3"
cache_dir = "data/models/cache"
device = "xpu" # Uses DirectML execution provider
default_top_k = 5
max_candidates = 100
```

---

## 3. Subagent Assignments

| Phase | Description | Assignee |
|:---|:---|:---|
| **Phase 1: Cargo Feature Configuration** | Add `fastembed` with DirectML support on Windows in `avrig-api/Cargo.toml` | `Assignee: be` |
| **Phase 2: Reranker Engine Implementation** | Implement `RerankerConfig` and `RerankerEngine` with DirectML XPU acceleration | `Assignee: be` |
| **Phase 3: Reranker Role Runtime Dispatcher** | Implement `run_reranker` task spawned when `"reranker"` is in `node.roles` exposing `POST /reranker` on `127.0.0.1:8001` | `Assignee: be` |
| **Phase 4: Windows Service Re-provisioning (`avrig`)** | Stop/remove `avrig-watcher`, install unified NSSM service `avrig` with descriptive metadata, and deploy to `D:\avrig` | `Assignee: Infra` |
| **Phase 5: XPU Benchmarking & Verification** | Verify concurrent operation of watcher and reranker on Windows; test `POST http://127.0.0.1:8001/reranker` | `Assignee: be` |

---

## 4. Implementation Details

### Phase 1: Cargo Dependencies (`Assignee: be`)
In `avrig-api/Cargo.toml`:
```toml
[target.'cfg(windows)'.dependencies]
fastembed = { version = "7", default-features = false, features = ["onnx", "ort-download-binaries", "directml"] }

[target.'cfg(not(windows))'.dependencies]
fastembed = { version = "7", default-features = false, features = ["onnx", "ort-download-binaries"] }
```

### Phase 2: Reranker Engine (`src/reranker.rs`) (`Assignee: be`)
- Wrap `fastembed::TextRerank` with `RerankerModel::BGERerankerV2M3`.
- Configure `ort::ep::DirectML` on Windows when `device = "xpu"`.
- Return ranked items with original index, normalized score, and document text.

### Phase 3: Runtime Role Dispatching (`src/main.rs`) (`Assignee: be`)
- In `main()` / runtime loop, spawn `run_reranker` whenever `"reranker"` is present in `config.node.roles`.
- Axum router for the reranker role binds `reranker.host:reranker.port` (default `127.0.0.1:8001`):
  - `GET /health`
  - `POST /reranker`
- Run inference inside `tokio::task::spawn_blocking` to prevent starving async threads.

### Phase 4: Service Deployment (`Assignee: Infra`)
Update `scripts/deploy.ps1`:
```powershell
$serviceName = "avrig"
$displayName = "avrig Windows Runtime Node"
$description = "Unified cross-platform avrig runtime node hosting directory ingestion watcher and hardware-accelerated (XPU) neural cross-encoder reranker."

# Stop & remove legacy avrig-watcher if present
if (Get-Service avrig-watcher -ErrorAction SilentlyContinue) {
    nssm stop avrig-watcher
    nssm remove avrig-watcher confirm
}

# Install unified service
nssm install $serviceName "D:\avrig\avrig.exe" "--config D:\avrig\config run"
nssm set $serviceName AppDirectory "D:\avrig"
nssm set $serviceName DisplayName $displayName
nssm set $serviceName Description $description
nssm set $serviceName Start SERVICE_AUTO_START
nssm start $serviceName
```

### Phase 5: Verification (`Assignee: be`)
1. Verify both watcher loop and reranker HTTP listener are active simultaneously under process `D:\avrig\avrig.exe`.
2. Post test batch to `http://127.0.0.1:8001/reranker`.
3. Confirm DirectML GPU/XPU usage and low inference latency.

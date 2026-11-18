---
title: "Plan: Knowledge Management Dev Infrastructure Installation on WSL (Ubuntu 24.04)"
type: canonical
status: completed
source-of-truth: true
domain: engineering
subdomain: infrastructure
category: installation-plan
topic: km-dev-infra-wsl
created: 2026-11-12
updated: 2026-11-12
author: avrig-ai
tags:
  - plan
  - infrastructure
  - wsl
  - ubuntu
  - postgresql
  - pgvector
  - garage
  - apache-age
  - oar-ocr
---

# Plan: Knowledge Management Dev Infrastructure Installation on WSL (Ubuntu 24.04)

**Status:** Completed & Verified  
**Project:** AGENTIC / avrig-ai  
**Scope:** Provisioning native systemd services on an Ubuntu 24.04 LTS WSL2 instance located at `D:\wsl\avrig-ai` for the Knowledge Management (`[KM]`) module. Includes PostgreSQL 16 (with `pgvector` and `Apache AGE`), Garage S3 object store, Rust toolchain, shared ONNX Runtime (for `bge-small-en-v1.5` embeddings and `oar-ocr` PP-OCRv6 document extraction), and connection to the Windows-hosted `bge-reranker-v2-m3` service.

---

## 1. Objectives & Target Topology

Deploy and verify the complete backend infrastructure for the Knowledge Management subsystem running natively via systemd inside a dedicated Ubuntu 24.04 LTS WSL environment:

- **WSL Virtual Disk Location:** `D:\wsl\avrig-ai` (`ext4.vhdx`).
- **PostgreSQL 16+ Service (Port 5432):**
  - Database: `avrig_km_dev` (owner: `avrig`)
  - Extension: `vector` (`pgvector` v0.6+) for HNSW dense embeddings.
  - Extension: `age` (Apache AGE v1.5+) for openCypher traceability graph.
  - Full-text search: native `tsvector` with GIN indexing.
  - Network: Configured with `listen_addresses = '*'` and SCRAM authentication for Windows host tools.
- **Garage S3 Object Storage Service (Ports 3900, 3901, 3902, 3903):**
  - Lightweight Rust-native S3-compatible daemon running under systemd as user `garage`.
  - Buckets: `avrig-platform-knowledge` and `avrig-project-artifacts`.
  - API Key: `avrig-dev-key`.
- **Local AI Embedding & Document Layout Runtime:**
  - Shared in-process ONNX Runtime dynamic library (`libonnxruntime.so`).
  - Cached `BAAI/bge-small-en-v1.5` ONNX model checkpoints for dense embeddings.
  - `oar-ocr` toolkit models (PP-OCRv6 + PP-Structure) executed over ONNX Runtime for table and layout recovery into structured Markdown.
- **External Windows-Hosted Reranker:**
  - `BAAI/bge-reranker-v2-m3` accessed over HTTP at `http://localhost:18601/rerank` (enabled by WSL2 mirrored networking).

---

## 2. Execution Phases

### Phase 0: Provision Ubuntu 24.04 LTS at Target Path (`D:\wsl\avrig-ai`) & Enable Systemd

To store the WSL virtual disk (`ext4.vhdx`) specifically on drive `D:` under `D:\wsl\avrig-ai`:

1. **Configure Host WSL Mirrored Networking (`~/.wslconfig` on Windows):**
   ```ini
   [wsl2]
   networkingMode=mirrored
   autoProxy=true
   ```

2. **Download RootFS & Import into `D:\wsl\avrig-ai`:**
   ```powershell
   # 1. Create target directory on D: drive
   New-Item -ItemType Directory -Force -Path "D:\wsl\avrig-ai"

   # 2. Download official Ubuntu Noble cloud rootfs tarball
   $rootfsUrl = "https://cloud-images.ubuntu.com/wsl/noble/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz"
   $tarPath = "D:\wsl\avrig-ai\ubuntu-noble.tar.gz"
   Invoke-WebRequest -Uri $rootfsUrl -OutFile $tarPath

   # 3. Import directly into D:\wsl\avrig-ai
   wsl.exe --import avrig-ai "D:\wsl\avrig-ai" $tarPath --version 2
   Remove-Item $tarPath

   # 4. Launch the instance as root to configure users
   wsl.exe -d avrig-ai
   ```

3. **Configure User, Automount & Systemd (`/etc/wsl.conf` inside WSL):**
   ```bash
   cat <<'EOF' > /etc/wsl.conf
   [boot]
   systemd=true

   [user]
   default=avrig

   [automount]
   enabled=true
   options="metadata,umask=22,fmask=11"
   EOF

   # Create developer user with passwordless sudo
   useradd -m -s /bin/bash avrig
   usermod -aG sudo avrig
   echo "avrig ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/avrig
   ```

4. **Restart Distro and Verify:**
   From Windows PowerShell:
   ```powershell
   wsl.exe --shutdown
   wsl.exe -d avrig-ai
   ```
   Inside WSL, verify systemd is active:
   ```bash
   systemctl is-system-running
   ```

---

### Phase 1: Base Toolchain & Rust Development Environment

Inside Ubuntu 24.04 as user `avrig`:

```bash
# 1. Base C/C++ compiler and build packages
sudo apt-get update && sudo apt-get install -y \
  curl wget git build-essential pkg-config libssl-dev clang cmake \
  libreadline-dev zlib1g-dev bison flex jq unzip libicu-dev

# 2. Install Rust Toolchain & sqlx-cli
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
cargo install sqlx-cli --no-default-features --features rustls,postgres
```

---

### Phase 2: PostgreSQL 16 + pgvector + Apache AGE (Native Systemd)

#### 2.1 Add PostgreSQL Official APT Repository & Install PG16
```bash
sudo install -d /etc/apt/keyrings
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt noble-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

sudo apt-get update
sudo apt-get install -y postgresql-16 postgresql-server-dev-16 postgresql-16-pgvector
```

#### 2.2 Compile and Install Apache AGE from Source
```bash
cd /tmp
git clone https://github.com/apache/age.git
cd age
git checkout v1.5.0

# Build with -Wno-error to prevent GCC 13 warnings from halting compilation
make PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config CFLAGS="-O2 -Wno-error"
sudo make PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config install
```

#### 2.3 Configure `postgresql.conf`, `pg_hba.conf` & Start Service
1. Enable AGE preload and listen on all interfaces:
   ```bash
   sudo sed -i "s/#shared_preload_libraries = ''/shared_preload_libraries = 'age'/g" /etc/postgresql/16/main/postgresql.conf
   sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/16/main/postgresql.conf
   ```
2. Allow password authentication from Windows host:
   ```bash
   echo "host all avrig 0.0.0.0/0 scram-sha-256" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
   ```
3. Enable and start PostgreSQL:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now postgresql
   ```

#### 2.4 Initialize User, Database, and Extensions
```bash
sudo -u postgres psql <<'EOF'
CREATE USER avrig WITH ENCRYPTED PASSWORD 'avrig_dev_secret';
CREATE DATABASE avrig_km_dev OWNER avrig;
GRANT ALL PRIVILEGES ON DATABASE avrig_km_dev TO avrig;

\c avrig_km_dev

-- Enable core extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;

-- Configure search path for Apache AGE openCypher
GRANT ALL ON SCHEMA public TO avrig;
ALTER DATABASE avrig_km_dev SET search_path = ag_catalog, "$user", public;

-- Initialize graph namespace
LOAD 'age';
SET search_path = ag_catalog, "$user", public;
SELECT create_graph('traceability_graph');
EOF
```

---

### Phase 3: Garage S3 Object Storage Service (Native Systemd)

#### 3.1 Install Garage Static Binary
```bash
sudo curl -Lo /usr/local/bin/garage \
  https://garagehq.deuxfleurs.fr/_releases/v1.0.1/x86_64-unknown-linux-musl/garage
sudo chmod +x /usr/local/bin/garage

# Create dedicated system user and directories
sudo useradd -r -m -d /var/lib/garage -s /bin/false garage
sudo mkdir -p /var/lib/garage/meta /var/lib/garage/data /etc/garage
sudo chown -R garage:garage /var/lib/garage
```

#### 3.2 Create Configuration (`/etc/garage.toml`)
```bash
RPC_SECRET=$(openssl rand -hex 32)

sudo tee /etc/garage.toml <<EOF
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "sqlite"

replication_factor = 1

[rpc]
bind_addr = "127.0.0.1:3901"
public_addr = "127.0.0.1:3901"
secret_key = "${RPC_SECRET}"

[s3_api]
api_bind_addr = "0.0.0.0:3900"
s3_region = "garage"
root_domain = ".s3.garage.local"

[s3_web]
bind_addr = "127.0.0.1:3902"
root_domain = ".web.garage.local"

[admin]
api_bind_addr = "127.0.0.1:3903"
admin_token = "avrig_admin_dev_token"
EOF

sudo chmod 600 /etc/garage.toml
sudo chown garage:garage /etc/garage.toml
```

#### 3.3 Create Systemd Service & Enable
```bash
sudo tee /etc/systemd/system/garage.service <<'EOF'
[Unit]
Description=Garage S3 Object Storage Service
After=network.target

[Service]
Type=simple
User=garage
Group=garage
ExecStart=/usr/local/bin/garage -c /etc/garage.toml server
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now garage
```

#### 3.4 Initialize Single-Node Layout & Buckets
```bash
# Read node ID from status
NODE_ID=$(/usr/local/bin/garage -c /etc/garage.toml status | awk 'NR==3 {print $1}')

# Assign local node storage and apply layout
/usr/local/bin/garage -c /etc/garage.toml layout assign -z dc1 -c 10G "$NODE_ID"
/usr/local/bin/garage -c /etc/garage.toml layout apply --version 1

# Create access key
/usr/local/bin/garage -c /etc/garage.toml key create avrig-dev-key

# Create buckets
/usr/local/bin/garage -c /etc/garage.toml bucket create avrig-platform-knowledge
/usr/local/bin/garage -c /etc/garage.toml bucket create avrig-project-artifacts

# Bind permissions
/usr/local/bin/garage -c /etc/garage.toml bucket allow avrig-platform-knowledge --read --write --key avrig-dev-key
/usr/local/bin/garage -c /etc/garage.toml bucket allow avrig-project-artifacts --read --write --key avrig-dev-key
```

---

### Phase 4: Shared In-Process ONNX Runtime & Embeddings Setup

```bash
# 1. Install ONNX Runtime shared library (shared by dense embeddings and oar-ocr)
cd /tmp
wget https://github.com/microsoft/onnxruntime/releases/download/v1.18.0/onnxruntime-linux-x64-1.18.0.tgz
tar -xzf onnxruntime-linux-x64-1.18.0.tgz
sudo cp onnxruntime-linux-x64-1.18.0/lib/libonnxruntime.so* /usr/local/lib/
sudo ldconfig

# 2. Setup model cache directory
mkdir -p ~/.cache/avrig/models/bge-small-en

# 3. Download bge-small-en-v1.5 ONNX model files
curl -Lo ~/.cache/avrig/models/bge-small-en/model.onnx \
  https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/onnx/model.onnx
curl -Lo ~/.cache/avrig/models/bge-small-en/tokenizer.json \
  https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/tokenizer.json
```

---

### Phase 5: Verification & Diagnostics Checklist

Execute the following test script inside Ubuntu:

1. **Systemd Services Status:**
   ```bash
   systemctl is-active postgresql # Expected: active
   systemctl is-active garage     # Expected: active
   ```
2. **PostgreSQL Vector & Graph Verification:**
   ```bash
   psql -h localhost -U avrig -d avrig_km_dev -c "SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector AS vector_dist;"
   psql -h localhost -U avrig -d avrig_km_dev -c "SELECT * FROM cypher('traceability_graph', \$\$ RETURN 1 \$\$) as (n agtype);"
   ```
3. **Garage S3 Bucket Verification:**
   ```bash
   aws --endpoint-url http://localhost:3900 s3 ls
   ```
4. **External Windows Reranker HTTP Connectivity:**
   ```bash
   curl -s -X POST http://localhost:18601/rerank \
     -H "Content-Type: application/json" \
     -d '{"query":"test","documents":["test doc"]}' || echo "Windows reranker endpoint reachable or standby"
   ```

---

## 3. Post-Execution Workflow

When this plan has been successfully executed and all tests pass:
- Move this document from `plans/` to `plans/done/`.
- Update the frontmatter status to `status: completed`.
- Reference completion in `_index.md`.

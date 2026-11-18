# Plan: Backend Multi-Format Document Ingestion, Chunking, BGE-M3 Vectorization, and Semantic Search

## 1. Executive Summary & Objectives
Build and verify an end-to-end document ingestion pipeline in `avrig-api`:
1. Receive multi-format document uploads via `POST /api/v1/documents/upload` (`multipart/form-data`).
2. Parse content across multiple document types:
   - Plain text / Markdown (`.txt`, `.md`)
   - Structured data (`.json`, `.csv`)
   - Rich documents (`.pdf`, `.docx`, `.html`)
3. Decompose parsed content into text chunks with character offsets and token estimation.
4. Generate 1024-dimensional dense embeddings using local Ollama `bge-m3:latest` configured via TOML (`config/embedding.toml`).
5. Persist document metadata and chunk embeddings to PostgreSQL (`avrig-db`) in `km.document` and `km.document_vector`.
6. Provide semantic vector search via `POST /api/v1/documents/search` and verify with all supported document types.

---

## 2. Subagent Responsibilities & Assignments

In accordance with project governance:

| Phase | Description | Assignee |
|:---|:---|:---|
| **Phase 1: Database Migration (1024-dim)** | Adjust EDM `km.document_vector.embedding` to `vector(1024)` and rebuild HNSW index | `Assignee: edm` |
| **Phase 2: Configuration & Dependencies** | Add `config/embedding.toml`, `config/database.toml`, and parser dependencies (`pdf-extract`, `docx-rs`, etc.) to `Cargo.toml` | `Assignee: primary` |
| **Phase 3: Multi-Format Parser & Chunker** | Implement format-specific text extractors (`.md`/`.txt`, `.json`, `.csv`, `.pdf`, `.docx`, `.html`) and sliding-window chunker | `Assignee: primary` |
| **Phase 4: Ollama BGE-M3 Client & DB Repository** | Implement async Ollama embedding client and PostgreSQL persistence (`tokio-postgres` / `sqlx`) | `Assignee: primary` |
| **Phase 5: API Endpoints Implementation** | Implement `POST /api/v1/documents/upload` and `POST /api/v1/documents/search` in Axum router | `Assignee: primary` |
| **Phase 6: Multi-Format Verification & Testing** | Create test fixtures for all 6 document types, ingest each, and verify semantic search recall | `Assignee: primary` |

---

## 3. Detailed Implementation Steps

### Phase 1: Database Schema Adjustment (`Assignee: edm`)
- Target: `avrig-db` (PostgreSQL 16)
- Modify `km.document_vector` column `embedding` from `vector(384)` to `vector(1024)` to accommodate `bge-m3:latest`.
- Rebuild HNSW vector cosine index:
  ```sql
  DROP INDEX IF EXISTS km.idx_document_vector_hnsw;
  ALTER TABLE km.document_vector ALTER COLUMN embedding TYPE vector(1024);
  CREATE INDEX idx_document_vector_hnsw ON km.document_vector 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
  ```
- Delegate via `agent: "edm"`.

### Phase 2: Configuration & Dependencies (`Assignee: primary`)
1. Create `config/embedding.toml`:
   ```toml
   [embedding]
   provider = "ollama"
   base_url = "http://127.0.0.1:11434"
   model = "bge-m3:latest"
   dimension = 1024
   chunk_size = 512
   chunk_overlap = 64
   batch_size = 8
   ```
2. Create `config/database.toml`:
   ```toml
   [database]
   url = "postgres://avrig-ai:h5iIo6p9QpK07h853QzHZWPA82aYTHy4@postgresql.avrig.ai:5432/avrig-db"
   max_connections = 10
   ```
3. Update `avrig-api/Cargo.toml` dependencies:
   - `tokio-postgres = { version = "0.7", features = ["with-uuid-1", "with-chrono-0_4"] }`
   - `pgvector = { version = "0.4", features = ["postgres"] }`
   - `pdf-extract = "0.7"` (or `lopdf`)
   - `docx-rs = "0.4"` (or lightweight docx zip xml extractor)
   - `quick-xml = "0.37"`
   - `csv = "1.3"`

### Phase 3: Multi-Format Document Extractors (`Assignee: primary`)
Create extractor module `src/extractor/mod.rs` handling:
1. **Markdown & Plain Text (`.md`, `.markdown`, `.txt`):** Direct UTF-8 decoding, stripped frontmatter if present.
2. **Structured JSON (`.json`):** Key-value flattening or stringified representation.
3. **Tabular CSV (`.csv`):** Row-by-row markdown table or sentence serialization.
4. **HTML (`.html`, `.htm`):** Stripped markup tags preserving readable inner text.
5. **PDF (`.pdf`):** Text extraction by page with `page_no` tracking via `pdf-extract`.
6. **Word DOCX (`.docx`):** Paragraph extraction from `word/document.xml`.

Output: `ExtractedDocument { text: String, pages: Vec<(i32, String)> }`.

### Phase 4: Text Chunker & Ollama Client (`Assignee: primary`)
1. **Chunking Engine:**
   - Paragraph- and sentence-boundary sliding window.
   - Respects `chunk_size = 512` and `chunk_overlap = 64`.
   - Populates `chunk_index`, `page_no`, `start_char_offset`, `end_char_offset`, and estimated `token_count`.
2. **Ollama Embedding Client:**
   - Issues requests to `POST http://127.0.0.1:11434/api/embeddings` with payload `{ "model": "bge-m3:latest", "prompt": chunk_text }`.
   - Validates that returned embedding dimension equals 1024.

### Phase 5: Database Persistence & Search Endpoints (`Assignee: primary`)
1. **Upload Endpoint (`POST /api/v1/documents/upload`):**
   - Parses multipart file upload.
   - Computes SHA-256 and detects MIME type / extension.
   - Extracts text -> chunks -> embeds with Ollama.
   - Inserts record into `km.document`.
   - Inserts all chunk vectors into `km.document_vector` with `tsv_content = to_tsvector('english', chunk_text)`.
   - Returns JSON: `{ "document_id": "...", "sha256": "...", "chunks_indexed": N, "format": "..." }`.
2. **Search Endpoint (`POST /api/v1/documents/search`):**
   - Body: `{ "query": "string", "limit": 5, "threshold": 0.5 }`.
   - Embeds query with `bge-m3:latest`.
   - Performs cosine similarity query:
     ```sql
     SELECT dv.id, dv.document_id, dv.chunk_index, dv.page_no, dv.chunk_text,
            1 - (dv.embedding <=> $1::vector) AS similarity,
            d.file_name, d.mime_type
     FROM km.document_vector dv
     JOIN km.document d ON d.id = dv.document_id
     WHERE dv.is_deleted = false
     ORDER BY dv.embedding <=> $1::vector ASC
     LIMIT $2;
     ```

### Phase 6: Multi-Format Verification Test Suite (`Assignee: primary`)
Create test fixtures in `tests/fixtures/`:
1. `sample.md` (Engineering SDLC process guide)
2. `sample.txt` (Server incident response log)
3. `sample.json` (System architecture configuration)
4. `sample.csv` (Microservice latency benchmark table)
5. `sample.html` (Knowledge base documentation page)
6. `sample.pdf` (Multi-page technical specification)
7. `sample.docx` (Project charter document)

**Execution & Validation Steps:**
1. Upload each fixture via `POST /api/v1/documents/upload`.
2. Verify HTTP 200 OK and chunk count > 0 in response.
3. For each document, execute a distinct semantic concept query via `POST /api/v1/documents/search`.
4. Assert that the top search result matches the corresponding file name with cosine similarity score > 0.70.

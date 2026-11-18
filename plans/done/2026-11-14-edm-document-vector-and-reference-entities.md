---
title: "Plan: Enterprise Data Model Design for Document Vector, Reference Data, and Taxonomies"
type: canonical
status: completed
source-of-truth: true
domain: engineering
subdomain: data-engineering
category: implementation-plan
topic: edm-document-vector-and-reference-entities
created: 2026-11-14
updated: 2026-11-14
author: avrig-ai
tags:
  - plan
  - edm
  - data-model
  - postgresql
  - pgvector
  - knowledge-management
  - reference-data
---

# Plan: Enterprise Data Model Design for Document Vector, Reference Data, and Taxonomies

**Status:** Active Implementation Plan  
**Project:** AGENTIC: Virtual AI Autonomous Engineering Organization & Agentic SDLC Platform  
**Parent Document:** `[[design/Technology-Architecture|Technology Architecture]]`, `[[design/Knowledge-Management|Knowledge Management]]`  
**Governing Standard:** `manage-edm` skill (`$env:OPENCODE_CONFIG_DIR/shared/skills/manage-edm`)  
**Scope:** Architectural specification, entity definitions, schema layouts, foreign key constraints, and execution steps for registering and managing five normalized EDM entities across schemas `rd` and `km`.

---

## 1. Executive Summary & Architectural Goals

The platform's knowledge ingestion, vector search, and Context Engine `[CX]` require structured persistence for document chunks, lexical search tokens, and dense embeddings.

Rather than storing denormalized string flags, this plan models:
1. Universal geographic and linguistic reference standards (`rd.country`, `rd.language`) under the shared Common Foundation domain (`co`, module `rd`).
2. A formal self-referencing knowledge taxonomy (`km.knowledge_category`) under the Agent Harness Knowledge Management module (`ah`, module `km`).
3. An updated canonical `km.document` entity referencing country, language, category, and recording its uniform embedding model.
4. Normalized semantic chunks with dense vector embeddings and page references in `km.document_vector`.

All entity, table, and column names use strict `snake_case`.

---

## 2. Domain & Schema Registry

| Domain Code | Domain Name | Module Code | Module Name | Schema | Entities Governed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`co`** | Common Foundation | **`rd`** | Reference Data | `rd` | `country`, `language` |
| **`ah`** | Agent Harness | **`km`** | Knowledge Management | `km` | `knowledge_category`, `document` (update), `document_vector` |

---

## 3. Entity Specifications

### 3.1 Entity: `country` (`rd.country`)
- **Domain**: `co` \| **Module**: `rd` \| **Schema**: `rd` \| **Template**: `reference`
- **Description**: Standard ISO 3166-1 country codes and jurisdictional references.

| Column Name | Logical Type | Physical Type | Nullable | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUIDv7 | `uuid` | No | Primary Key |
| `country_code` | Varchar(3) | `varchar(3)` | No | ISO 3166-1 alpha code (e.g. `"ID"`, `"US"`, `"SGP"`), `UNIQUE` |
| `country_name` | Varchar(100) | `varchar(100)` | No | Full display name |
| `numeric_code` | Varchar(3) | `varchar(3)` | Yes | ISO 3166-1 numeric code (e.g. `"360"`, `"840"`) |
| `is_active` | Boolean | `boolean` | No | Default `true` |
| `created_by` | Varchar(100) | `varchar(100)` | No | Standard EDM audit |
| `created_time` | Timestamp | `timestamptz` | No | Standard EDM audit |
| `updated_by` | Varchar(100) | `varchar(100)` | Yes | Standard EDM audit |
| `updated_time` | Timestamp | `timestamptz` | Yes | Standard EDM audit |
| `is_deleted` | Boolean | `boolean` | No | Default `false` |
| `deleted_by` | Varchar(100) | `varchar(100)` | Yes | Standard EDM audit |
| `deleted_time` | Timestamp | `timestamptz` | Yes | Standard EDM audit |

---

### 3.2 Entity: `language` (`rd.language`)
- **Domain**: `co` \| **Module**: `rd` \| **Schema**: `rd` \| **Template**: `reference`
- **Description**: Standard ISO 639-1 / BCP 47 language codes controlling tokenization and model dispatch.

| Column Name | Logical Type | Physical Type | Nullable | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUIDv7 | `uuid` | No | Primary Key |
| `language_code`| Varchar(10) | `varchar(10)` | No | ISO 639-1 / BCP 47 code (e.g. `"en"`, `"id"`, `"en-US"`), `UNIQUE` |
| `language_name`| Varchar(100) | `varchar(100)` | No | English display name |
| `native_name` | Varchar(100) | `varchar(100)` | Yes | Native script name (e.g. `"Bahasa Indonesia"`) |
| `is_active` | Boolean | `boolean` | No | Default `true` |
| `created_by` | Varchar(100) | `varchar(100)` | No | Standard EDM audit |
| `created_time` | Timestamp | `timestamptz` | No | Standard EDM audit |
| `updated_by` | Varchar(100) | `varchar(100)` | Yes | Standard EDM audit |
| `updated_time` | Timestamp | `timestamptz` | Yes | Standard EDM audit |
| `is_deleted` | Boolean | `boolean` | No | Default `false` |
| `deleted_by` | Varchar(100) | `varchar(100)` | Yes | Standard EDM audit |
| `deleted_time` | Timestamp | `timestamptz` | Yes | Standard EDM audit |

---

### 3.3 Entity: `knowledge_category` (`km.knowledge_category`)
- **Domain**: `ah` \| **Module**: `km` \| **Schema**: `km` \| **Template**: `reference`
- **Description**: Self-referencing hierarchical taxonomy for knowledge assets.

| Column Name | Logical Type | Physical Type | Nullable | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUIDv7 | `uuid` | No | Primary Key |
| `category_code` | Varchar(50) | `varchar(50)` | No | Stable programmatic code, `UNIQUE` |
| `category_name` | Varchar(100) | `varchar(100)` | No | Display title |
| `category_desc` | Text | `text` | Yes | Scope description and agent usage criteria |
| `parent_knowledge_category_id` | UUID | `uuid` | Yes | Self-reference foreign key to `km.knowledge_category(id) ON DELETE RESTRICT` |
| `sort_order` | Integer | `integer` | No | Sort order within parent level (default `0`) |
| `is_active` | Boolean | `boolean` | No | Default `true` |
| `created_by` | Varchar(100) | `varchar(100)` | No | Standard EDM audit |
| `created_time` | Timestamp | `timestamptz` | No | Standard EDM audit |
| `updated_by` | Varchar(100) | `varchar(100)` | Yes | Standard EDM audit |
| `updated_time` | Timestamp | `timestamptz` | Yes | Standard EDM audit |
| `is_deleted` | Boolean | `boolean` | No | Default `false` |
| `deleted_by` | Varchar(100) | `varchar(100)` | Yes | Standard EDM audit |
| `deleted_time` | Timestamp | `timestamptz` | Yes | Standard EDM audit |

---

### 3.4 Entity: `document` (`km.document` — Attribute Updates)
- **Domain**: `ah` \| **Module**: `km` \| **Schema**: `km` \| **Template**: `standard`
- **Description**: Canonical ingested binary file registry.

| Column Name | Logical Type | Physical Type | Nullable | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUIDv7 | `uuid` | No | Primary Key |
| `sha256` | Varchar(64) | `varchar(64)` | No | Globally unique content hash, `UNIQUE` |
| `file_name` | Varchar(255) | `varchar(255)` | No | Original filename |
| `mime_type` | Varchar(100) | `varchar(100)` | No | Detected MIME type |
| `size_bytes` | BigInt | `bigint` | No | File size in bytes |
| `storage_bucket`| Varchar(100) | `varchar(100)` | No | Garage S3 bucket |
| `storage_key` | Varchar(255) | `varchar(255)` | No | S3 object key |
| `country_id` | UUID | `uuid` | Yes | Foreign Key to `rd.country(id) ON DELETE RESTRICT` |
| `language_id` | UUID | `uuid` | Yes | Foreign Key to `rd.language(id) ON DELETE RESTRICT` |
| `knowledge_category_id` | UUID | `uuid` | Yes | Foreign Key to `km.knowledge_category(id) ON DELETE RESTRICT` |
| `embedding_model` | Varchar(100) | `varchar(100)` | Yes | Embedding model identifier used to index chunks |
| `is_active` | Boolean | `boolean` | No | Default `true` |
| *Audit fields* | Standard | Standard | Yes/No | Standard EDM audit attributes |

---

### 3.5 Entity: `document_vector` (`km.document_vector`)
- **Domain**: `ah` \| **Module**: `km` \| **Schema**: `km` \| **Template**: `standard`
- **Description**: Normalized semantic chunk vectors and lexical full-text tokens.

| Column Name | Logical Type | Physical Type | Nullable | Constraints & Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUIDv7 | `uuid` | No | Primary Key |
| `document_id` | UUID | `uuid` | No | Foreign Key to `km.document(id) ON DELETE CASCADE` |
| `chunk_index` | Integer | `integer` | No | Zero-based sequence number within document |
| `page_no` | Integer | `integer` | Yes | 1-based page or slide index in original document |
| `chunk_text` | Text | `text` | No | Verbatim chunk text content |
| `token_count` | Integer | `integer` | No | Exact token count using parent document's `embedding_model` |
| `embedding` | Vector(384) | `vector(384)` | No | Dense semantic vector (`bge-small-en-v1.5` 384 dimensions) |
| `tsv_content` | TSVector | `tsvector` | Yes | Generated full-text tokens (`to_tsvector('english', chunk_text)`) |
| `start_char_offset` | Integer | `integer` | Yes | Character start position |
| `end_char_offset` | Integer | `integer` | Yes | Character end position |
| `is_active` | Boolean | `boolean` | No | Default `true` |
| *Audit fields* | Standard | Standard | Yes/No | Standard EDM audit attributes |

**Indexes & Integrity**:
- `UNIQUE (document_id, chunk_index)`
- HNSW Vector index on `embedding` (`vector_cosine_ops`, `m = 16`, `ef_construction = 64`)
- GIN index on `tsv_content`
- B-Tree index on `(document_id, page_no)`

---

## 4. Relationship Diagram

```text
rd.country (PK id) ──────────────┐
                                 │
rd.language (PK id) ─────────────┼────────┐
                                 │        │
km.knowledge_category (PK id) ───┼────────┼────────┐
  │                              │        │        │
  └── parent_knowledge_category_id (self) │        │
                                 ▼        ▼        ▼
                          km.document (PK id, UNIQUE sha256)
                                 │
                                 ▼ ON DELETE CASCADE
                          km.document_vector (PK id, UNIQUE(document_id, chunk_index))
```

---

## 5. Execution Workflow via `manage-edm`

In accordance with project rules, no SQL or schema modification may be applied ad-hoc:
1. Ensure domain `co` and module `rd` exist in the EDM repository.
2. Model entities `country` and `language` in `rd`.
3. Model entity `knowledge_category` in `km`.
4. Update entity `document` in `km` with the three foreign keys and `embedding_model`.
5. Model entity `document_vector` in `km`.
6. Run `manage-edm validate` to ensure reference integrity and template compliance.
7. Generate DDL and ERD artifacts.
8. Physical deployment to PostgreSQL will occur only upon separate, explicit operator approval.

-- ============================================================
-- manage-edm generated DDL
-- entity:   document_vector
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.2
-- updated:  2026-11-14 03:49 UTC
-- update:   regenerated for version 0.0.2
-- ============================================================

-- document_vector DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."document_vector" (
    "document_id" uuid NOT NULL,
    "chunk_index" integer NOT NULL,
    "page_no" integer NULL,
    "chunk_text" text NOT NULL,
    "token_count" integer NOT NULL,
    "embedding" vector NOT NULL,
    "tsv_content" tsvector NULL,
    "start_char_offset" integer NULL,
    "end_char_offset" integer NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "document_vector_code" varchar(30) NOT NULL,
    "document_vector_name" varchar(100) NOT NULL,
    "document_vector_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_document_vector_document" FOREIGN KEY ("document_id") REFERENCES "km"."document"("id"),
    CONSTRAINT "ux_document_vector_document_vector_code" UNIQUE ("document_vector_code")
);

-- samples
INSERT INTO "km"."document_vector" ("document_id", "chunk_index", "page_no", "chunk_text", "token_count", "embedding", "tsv_content", "start_char_offset", "end_char_offset", "document_vector_code", "document_vector_name", "document_vector_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES (uuid_generate_v7(), 123, 123, 'Sample Text', 123, 'sample', 'sample', 123, 123, 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

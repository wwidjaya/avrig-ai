-- ============================================================
-- manage-edm generated DDL
-- entity:   document
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.2
-- updated:  2026-11-14 03:49 UTC
-- update:   regenerated for version 0.0.2
-- ============================================================

-- document DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."document" (
    "sha256" varchar NOT NULL,
    "file_name" varchar NOT NULL,
    "mime_type" varchar NOT NULL,
    "size_bytes" bigint NOT NULL,
    "storage_bucket" varchar NOT NULL,
    "storage_key" varchar NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "document_code" varchar(30) NOT NULL,
    "document_name" varchar(100) NOT NULL,
    "document_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    "country_id" uuid NULL,
    "language_id" uuid NULL,
    "knowledge_category_id" uuid NULL,
    "embedding_model" varchar(100) NULL,
    CONSTRAINT "fk_document_country" FOREIGN KEY ("country_id") REFERENCES "rd"."country"("id"),
    CONSTRAINT "fk_document_language" FOREIGN KEY ("language_id") REFERENCES "rd"."language"("id"),
    CONSTRAINT "fk_document_knowledge_category" FOREIGN KEY ("knowledge_category_id") REFERENCES "km"."knowledge_category"("id"),
    CONSTRAINT "ux_document_sha256" UNIQUE ("sha256"),
    CONSTRAINT "ux_document_document_code" UNIQUE ("document_code")
);

-- samples
INSERT INTO "km"."document" ("sha256", "file_name", "mime_type", "size_bytes", "storage_bucket", "storage_key", "document_code", "document_name", "document_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time", "country_id", "language_id", "knowledge_category_id", "embedding_model") VALUES ('Sample Text', 'Sample Text', 'Sample Text', 123, 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now(), uuid_generate_v7(), uuid_generate_v7(), uuid_generate_v7(), 'Sample Text');

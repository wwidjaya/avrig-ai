-- ============================================================
-- manage-edm generated DDL
-- entity:   Document
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.1
-- updated:  2026-11-13 12:57 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- Document DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."Document" (
    "sha256" varchar NOT NULL,
    "file_name" varchar NOT NULL,
    "mime_type" varchar NOT NULL,
    "size_bytes" bigint NOT NULL,
    "storage_bucket" varchar NOT NULL,
    "storage_key" varchar NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "Document_code" varchar(30) NOT NULL,
    "Document_name" varchar(100) NOT NULL,
    "Document_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "ux_Document_sha256" UNIQUE ("sha256"),
    CONSTRAINT "ux_Document_Document_code" UNIQUE ("Document_code")
);

-- samples
INSERT INTO "km"."Document" ("sha256", "file_name", "mime_type", "size_bytes", "storage_bucket", "storage_key", "Document_code", "Document_name", "Document_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES ('Sample Text', 'Sample Text', 'Sample Text', 123, 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

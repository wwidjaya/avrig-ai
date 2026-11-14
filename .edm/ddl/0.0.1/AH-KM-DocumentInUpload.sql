-- ============================================================
-- manage-edm generated DDL
-- entity:   DocumentInUpload
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.1
-- updated:  2026-11-13 12:57 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- DocumentInUpload DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."DocumentInUpload" (
    "sha256" varchar NOT NULL,
    "file_name" varchar NOT NULL,
    "source_path" varchar NOT NULL,
    "source_platform" varchar NOT NULL,
    "mime_type" varchar NOT NULL,
    "size_bytes" bigint NOT NULL,
    "project_id" uuid NULL,
    "knowledge_category" varchar NOT NULL,
    "process_status_flag" varchar(5) NOT NULL,
    "document_id" uuid NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "DocumentInUpload_code" varchar(30) NOT NULL,
    "DocumentInUpload_name" varchar(100) NOT NULL,
    "DocumentInUpload_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_DocumentInUpload_Project" FOREIGN KEY ("project_id") REFERENCES "Project"("id"),
    CONSTRAINT "fk_DocumentInUpload_Document" FOREIGN KEY ("document_id") REFERENCES "Document"("id"),
    CONSTRAINT "ux_DocumentInUpload_DocumentInUpload_code" UNIQUE ("DocumentInUpload_code")
);

-- samples
INSERT INTO "km"."DocumentInUpload" ("sha256", "file_name", "source_path", "source_platform", "mime_type", "size_bytes", "project_id", "knowledge_category", "process_status_flag", "document_id", "DocumentInUpload_code", "DocumentInUpload_name", "DocumentInUpload_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES ('Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 123, uuid_generate_v7(), 'Sample Text', 'Sample Text', uuid_generate_v7(), 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

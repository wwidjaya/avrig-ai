-- ============================================================
-- manage-edm generated DDL
-- entity:   DocumentSourceLocation
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.1
-- updated:  2026-11-13 12:57 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- DocumentSourceLocation DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."DocumentSourceLocation" (
    "document_id" uuid NOT NULL,
    "project_id" uuid NULL,
    "source_path" varchar NOT NULL,
    "source_platform" varchar NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "DocumentSourceLocation_code" varchar(30) NOT NULL,
    "DocumentSourceLocation_name" varchar(100) NOT NULL,
    "DocumentSourceLocation_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_DocumentSourceLocation_Document" FOREIGN KEY ("document_id") REFERENCES "Document"("id"),
    CONSTRAINT "fk_DocumentSourceLocation_Project" FOREIGN KEY ("project_id") REFERENCES "Project"("id"),
    CONSTRAINT "ux_DocumentSourceLocation_DocumentSourceLocation_code" UNIQUE ("DocumentSourceLocation_code")
);

-- samples
INSERT INTO "km"."DocumentSourceLocation" ("document_id", "project_id", "source_path", "source_platform", "DocumentSourceLocation_code", "DocumentSourceLocation_name", "DocumentSourceLocation_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES (uuid_generate_v7(), uuid_generate_v7(), 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

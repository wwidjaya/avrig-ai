-- ============================================================
-- manage-edm generated DDL
-- entity:   document_project
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.1
-- updated:  2026-11-13 13:11 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- document_project DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."document_project" (
    "document_id" uuid NOT NULL,
    "project_id" uuid NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "document_project_code" varchar(30) NOT NULL,
    "document_project_name" varchar(100) NOT NULL,
    "document_project_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_document_project_document" FOREIGN KEY ("document_id") REFERENCES "km"."document"("id"),
    CONSTRAINT "fk_document_project_project" FOREIGN KEY ("project_id") REFERENCES "re"."project"("id"),
    CONSTRAINT "ux_document_project_document_project_code" UNIQUE ("document_project_code")
);

-- samples
INSERT INTO "km"."document_project" ("document_id", "project_id", "document_project_code", "document_project_name", "document_project_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES (uuid_generate_v7(), uuid_generate_v7(), 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

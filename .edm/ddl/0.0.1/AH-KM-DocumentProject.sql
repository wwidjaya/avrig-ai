-- ============================================================
-- manage-edm generated DDL
-- entity:   DocumentProject
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.1
-- updated:  2026-11-13 12:57 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- DocumentProject DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."DocumentProject" (
    "document_id" uuid NOT NULL,
    "project_id" uuid NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "DocumentProject_code" varchar(30) NOT NULL,
    "DocumentProject_name" varchar(100) NOT NULL,
    "DocumentProject_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_DocumentProject_Document" FOREIGN KEY ("document_id") REFERENCES "Document"("id"),
    CONSTRAINT "fk_DocumentProject_Project" FOREIGN KEY ("project_id") REFERENCES "Project"("id"),
    CONSTRAINT "ux_DocumentProject_DocumentProject_code" UNIQUE ("DocumentProject_code")
);

-- samples
INSERT INTO "km"."DocumentProject" ("document_id", "project_id", "DocumentProject_code", "DocumentProject_name", "DocumentProject_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES (uuid_generate_v7(), uuid_generate_v7(), 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

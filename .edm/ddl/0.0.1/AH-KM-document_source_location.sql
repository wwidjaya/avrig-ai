-- ============================================================
-- manage-edm generated DDL
-- entity:   document_source_location
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.1
-- updated:  2026-11-13 13:11 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- document_source_location DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."document_source_location" (
    "document_id" uuid NOT NULL,
    "project_id" uuid NULL,
    "source_path" varchar NOT NULL,
    "source_platform" varchar NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "document_source_location_code" varchar(30) NOT NULL,
    "document_source_location_name" varchar(100) NOT NULL,
    "document_source_location_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_document_source_location_document" FOREIGN KEY ("document_id") REFERENCES "km"."document"("id"),
    CONSTRAINT "fk_document_source_location_project" FOREIGN KEY ("project_id") REFERENCES "re"."project"("id"),
    CONSTRAINT "ux_document_source_location_document_source_location_code" UNIQUE ("document_source_location_code")
);

-- samples
INSERT INTO "km"."document_source_location" ("document_id", "project_id", "source_path", "source_platform", "document_source_location_code", "document_source_location_name", "document_source_location_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES (uuid_generate_v7(), uuid_generate_v7(), 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

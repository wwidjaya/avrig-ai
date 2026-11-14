-- ============================================================
-- manage-edm generated DDL
-- entity:   language
-- domain:   CO
-- module:   RD
-- database: avrig-db
-- schema:   rd
-- version:  0.0.2
-- updated:  2026-11-14 03:49 UTC
-- update:   regenerated for version 0.0.2
-- ============================================================

-- language DDL
-- database: avrig-db
-- schema: rd

CREATE TABLE "rd"."language" (
    "native_name" varchar(100) NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "language_code" varchar(30) NOT NULL,
    "language_name" varchar(100) NOT NULL,
    "language_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "ux_language_language_code" UNIQUE ("language_code")
);

-- samples
INSERT INTO "rd"."language" ("native_name", "language_code", "language_name", "language_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES ('Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

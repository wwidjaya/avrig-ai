-- ============================================================
-- manage-edm generated DDL
-- entity:   Project
-- domain:   ES
-- module:   RE
-- database: avrig-db
-- schema:   re
-- version:  0.0.1
-- updated:  2026-11-13 12:57 UTC
-- update:   regenerated for version 0.0.1
-- ============================================================

-- Project DDL
-- database: avrig-db
-- schema: re

CREATE TABLE "re"."Project" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "Project_code" varchar(30) NOT NULL,
    "Project_name" varchar(100) NOT NULL,
    "Project_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "ux_Project_Project_code" UNIQUE ("Project_code")
);

-- samples
INSERT INTO "re"."Project" ("Project_code", "Project_name", "Project_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES ('Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

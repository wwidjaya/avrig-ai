-- ============================================================
-- manage-edm generated DDL
-- entity:   country
-- domain:   CO
-- module:   RD
-- database: avrig-db
-- schema:   rd
-- version:  0.0.2
-- updated:  2026-11-14 03:49 UTC
-- update:   regenerated for version 0.0.2
-- ============================================================

-- country DDL
-- database: avrig-db
-- schema: rd

CREATE TABLE "rd"."country" (
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "country_code" varchar(30) NOT NULL,
    "country_name" varchar(100) NOT NULL,
    "country_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    "numeric_code" varchar(3) NULL,
    CONSTRAINT "ux_country_country_code" UNIQUE ("country_code")
);

-- samples
INSERT INTO "rd"."country" ("country_code", "country_name", "country_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time", "numeric_code") VALUES ('Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now(), 'Sam');

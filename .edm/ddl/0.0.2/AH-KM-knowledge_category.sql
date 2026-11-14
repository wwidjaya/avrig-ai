-- ============================================================
-- manage-edm generated DDL
-- entity:   knowledge_category
-- domain:   AH
-- module:   KM
-- database: avrig-db
-- schema:   km
-- version:  0.0.2
-- updated:  2026-11-14 03:49 UTC
-- update:   regenerated for version 0.0.2
-- ============================================================

-- knowledge_category DDL
-- database: avrig-db
-- schema: km

CREATE TABLE "km"."knowledge_category" (
    "parent_knowledge_category_id" uuid NULL,
    "sort_order" integer NOT NULL,
    "id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "knowledge_category_code" varchar(30) NOT NULL,
    "knowledge_category_name" varchar(100) NOT NULL,
    "knowledge_category_desc" varchar(255) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by" uuid NOT NULL,
    "created_time" timestamp NOT NULL,
    "updated_by" uuid NOT NULL,
    "updated_time" timestamp NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_by" uuid NOT NULL,
    "deleted_time" timestamp NOT NULL,
    CONSTRAINT "fk_knowledge_category_parent" FOREIGN KEY ("parent_knowledge_category_id") REFERENCES "km"."knowledge_category"("id"),
    CONSTRAINT "ux_knowledge_category_knowledge_category_code" UNIQUE ("knowledge_category_code")
);

-- samples
INSERT INTO "km"."knowledge_category" ("parent_knowledge_category_id", "sort_order", "knowledge_category_code", "knowledge_category_name", "knowledge_category_desc", "is_active", "created_by", "created_time", "updated_by", "updated_time", "is_deleted", "deleted_by", "deleted_time") VALUES (uuid_generate_v7(), 123, 'Sample Text', 'Sample Text', 'Sample Text', false, uuid_generate_v7(), now(), uuid_generate_v7(), now(), false, uuid_generate_v7(), now());

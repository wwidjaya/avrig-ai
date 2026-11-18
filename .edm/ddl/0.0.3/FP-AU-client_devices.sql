-- ============================================================
-- manage-edm generated DDL
-- entity:   client_devices
-- domain:   FP
-- module:   AU
-- database: avrig-db
-- schema:   au
-- version:  0.0.3
-- updated:  2026-11-18 04:08 UTC
-- update:   regenerated for version 0.0.3
-- ============================================================

-- client_devices DDL
-- database: avrig-db
-- schema: au

CREATE TABLE "au"."client_devices" (
    "device_id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "user_id" varchar NOT NULL,
    "client_type" varchar NOT NULL,
    "device_name" varchar NULL,
    "push_token" varchar NULL,
    "platform_os" varchar NULL,
    "created_at" timestamp NOT NULL,
    "updated_at" timestamp NOT NULL
);

-- samples
INSERT INTO "au"."client_devices" ("user_id", "client_type", "device_name", "push_token", "platform_os", "created_at", "updated_at") VALUES ('Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', now(), now());

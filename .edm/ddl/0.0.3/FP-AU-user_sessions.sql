-- ============================================================
-- manage-edm generated DDL
-- entity:   user_sessions
-- domain:   FP
-- module:   AU
-- database: avrig-db
-- schema:   au
-- version:  0.0.3
-- updated:  2026-11-18 04:07 UTC
-- update:   regenerated for version 0.0.3
-- ============================================================

-- user_sessions DDL
-- database: avrig-db
-- schema: au

CREATE TABLE "au"."user_sessions" (
    "session_id" uuid PRIMARY KEY DEFAULT uuid_generate_v7(),
    "user_id" varchar NOT NULL,
    "client_type" varchar NOT NULL,
    "refresh_token_hash" varchar NULL,
    "user_agent" varchar NULL,
    "ip_address" inet NULL,
    "expires_at" timestamp NOT NULL,
    "created_at" timestamp NOT NULL,
    "last_active_at" timestamp NOT NULL
);

-- samples
INSERT INTO "au"."user_sessions" ("user_id", "client_type", "refresh_token_hash", "user_agent", "ip_address", "expires_at", "created_at", "last_active_at") VALUES ('Sample Text', 'Sample Text', 'Sample Text', 'Sample Text', 'sample', now(), now(), now());

-- ============================================================
-- SQLx Migration: 20261118000001_multi_client_sessions.sql
-- Description: Multi-client user sessions and device registration tables
-- Schema: au
-- ============================================================

-- Ensure uuid-ossp or pgcrypto extension for uuid_generate_v7 / uuid_generate_v4
CREATE SCHEMA IF NOT EXISTS au;

-- Table: au.user_sessions
CREATE TABLE IF NOT EXISTS au.user_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id TEXT NOT NULL,
    client_type VARCHAR(20) NOT NULL,
    refresh_token_hash TEXT NULL,
    user_agent TEXT NULL,
    ip_address INET NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_user_sessions_client_type CHECK (client_type IN ('web', 'desktop', 'mobile'))
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON au.user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON au.user_sessions (expires_at);

-- Table: au.client_devices
CREATE TABLE IF NOT EXISTS au.client_devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id TEXT NOT NULL,
    client_type VARCHAR(20) NOT NULL,
    device_name VARCHAR(100) NULL,
    push_token TEXT NULL,
    platform_os VARCHAR(50) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT ck_client_devices_client_type CHECK (client_type IN ('desktop', 'mobile'))
);

CREATE INDEX IF NOT EXISTS idx_client_devices_user_id ON au.client_devices (user_id);

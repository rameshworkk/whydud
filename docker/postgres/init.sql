-- ============================================================
-- Whydud — PostgreSQL schema initialization
-- Runs once on first container start (via docker-entrypoint-initdb.d)
-- ============================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---- Create custom schemas ----
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS email_intel;
CREATE SCHEMA IF NOT EXISTS scoring;
CREATE SCHEMA IF NOT EXISTS tco;
CREATE SCHEMA IF NOT EXISTS community;
CREATE SCHEMA IF NOT EXISTS admin;

-- Grant all schemas to app user
GRANT ALL PRIVILEGES ON SCHEMA public TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA users TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA email_intel TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA scoring TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA tco TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA community TO whydud;
GRANT ALL PRIVILEGES ON SCHEMA admin TO whydud;

-- ---- Default privileges for future tables ----
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO whydud;
ALTER DEFAULT PRIVILEGES IN SCHEMA users GRANT ALL ON TABLES TO whydud;
ALTER DEFAULT PRIVILEGES IN SCHEMA email_intel GRANT ALL ON TABLES TO whydud;
ALTER DEFAULT PRIVILEGES IN SCHEMA scoring GRANT ALL ON TABLES TO whydud;
ALTER DEFAULT PRIVILEGES IN SCHEMA tco GRANT ALL ON TABLES TO whydud;
ALTER DEFAULT PRIVILEGES IN SCHEMA community GRANT ALL ON TABLES TO whydud;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin GRANT ALL ON TABLES TO whydud;

-- NOTE: TimescaleDB hypertables for price_snapshots and dudscore_history
-- are created post-migration via:
--   SELECT create_hypertable('price_snapshots', 'time');
--   SELECT create_hypertable('scoring"."dudscore_history', 'time');
-- See docs/ARCHITECTURE.md Section 9 for full schema.

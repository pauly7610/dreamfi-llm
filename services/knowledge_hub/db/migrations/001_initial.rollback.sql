-- Rollback for 001_initial.sql
-- This reverses the initial schema creation

DROP TABLE IF EXISTS evaluation_results CASCADE;
DROP TABLE IF EXISTS variants CASCADE;
DROP TABLE IF EXISTS autoresearch_rounds CASCADE;
DROP TABLE IF EXISTS skill_specs CASCADE;
DROP TABLE IF EXISTS criteria CASCADE;
DROP TABLE IF EXISTS hardened_results CASCADE;
DROP TABLE IF EXISTS promotion_history CASCADE;
DROP TABLE IF EXISTS migration_log CASCADE;

DROP TYPE IF EXISTS eval_status CASCADE;
DROP TYPE IF EXISTS promotion_status CASCADE;

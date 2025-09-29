-- Database cleanup script - Remove obsolete test tables
-- Run this when setting up a clean production database

-- Remove test/debug tables that were used during development
DROP TABLE IF EXISTS async_test_results;
DROP TABLE IF EXISTS test_commands;  
DROP TABLE IF EXISTS test_results;
DROP TABLE IF EXISTS signals;

-- Clean up expired sessions periodically
DELETE FROM sessions WHERE expires_at < UTC_TIMESTAMP();

-- Show final table structure
SHOW TABLES;

-- Final production tables should be:
-- api_keys, command_templates, commands, redrat_devices, remote_files, 
-- remotes, schedules, sequence_commands, sequences, sessions, users
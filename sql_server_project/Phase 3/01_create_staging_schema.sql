-- MERIDIAN Phase 3 - Step 1
-- Creates the "staging" schema: one cleaned view per raw source table.
-- Same idempotent pattern as the raw schema in Phase 2.


USE MeridianDB;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging')
BEGIN
    EXEC('CREATE SCHEMA staging');
    PRINT 'Schema [staging] created.';
END
ELSE
BEGIN
    PRINT 'Schema [staging] already exists - nothing to do.';
END
GO
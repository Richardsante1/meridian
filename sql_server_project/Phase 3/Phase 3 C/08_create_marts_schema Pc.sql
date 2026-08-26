-- MERIDIAN Phase 3, Part C - Step 1
-- Creates the "marts" schema - the final, analysis-ready layer. Every
-- later analysis phase (RFM, cohorts, forecasting, etc.) will query
-- tables in THIS schema, not raw or staging directly.

USE MeridianDB;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'marts')
BEGIN
    EXEC('CREATE SCHEMA marts');
    PRINT 'Schema [marts] created.';
END
ELSE
BEGIN
    PRINT 'Schema [marts] already exists - nothing to do.';
END
GO

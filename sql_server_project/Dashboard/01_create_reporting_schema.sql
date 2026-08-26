-- MERIDIAN Dashboard Phase - Step 1
-- Creates a "reporting" schema: purpose-built views (and, soon, tables
-- of exported Python results) specifically for Power BI to connect to.
-- Keeps the dashboard layer separate from marts (which is for analysis
-- notebooks) - Power BI gets clean, pre-aggregated, dashboard-ready
-- sources instead of pulling from large raw fact tables directly.

USE MeridianDB;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'reporting')
BEGIN
    EXEC('CREATE SCHEMA reporting');
    PRINT 'Schema [reporting] created.';
END
ELSE
BEGIN
    PRINT 'Schema [reporting] already exists - nothing to do.';
END
GO

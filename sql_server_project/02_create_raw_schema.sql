-- MERIDIAN Phase 2 - Step 2
-- Creates a "raw" schema inside MeridianDB. This is the landing zone for
-- data exactly as it arrives from source - unclean, untyped, on purpose.
-- Cleaning happens later, in Phase 3's staging/mart layer.


USE MeridianDB;

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'raw')
BEGIN
    EXEC('CREATE SCHEMA raw');
    PRINT 'Schema [raw] created.';
END
ELSE
BEGIN
    PRINT 'Schema [raw] already exists - nothing to do.';
END
GO

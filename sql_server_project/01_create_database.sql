-- MERIDIAN Phase 2 - Step 1
-- Creates the MeridianDB database if it doesn't already exist.
-- Run this in SSMS: open a "New Query" window connected to your local
-- server, paste this in, and click Execute (or press F5).

IF DB_ID('MeridianDB') IS NULL
BEGIN
    CREATE DATABASE MeridianDB;
    PRINT 'MeridianDB created.';
END
ELSE
BEGIN
    PRINT 'MeridianDB already exists - nothing to do.';
END
GO

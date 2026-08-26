-- MERIDIAN Phase 3 - Step 2
-- A reusable helper function that tries several date formats in turn.
--
-- WHY THIS EXISTS: the synthetic data generator (Phase 1) deliberately
-- stored dates in 4 different text formats, to simulate different
-- upstream systems writing dates inconsistently - a genuinely common
-- real-world problem. This function tries each known format in order
-- and returns the first one that successfully parses.
--
-- TRY_CONVERT(datetime, value, style_code) attempts a conversion and
-- returns NULL instead of erroring if it fails (that's what "TRY" means
-- here - contrast with plain CONVERT, which would stop the whole query
-- with an error on a single bad value). COALESCE then picks the first
-- non-NULL result from the list - i.e. "use whichever attempt worked."
--
-- Style codes used:
--   120 = 'yyyy-mm-dd hh:mi:ss'  (ISO format)
--   101 = 'mm/dd/yyyy'            (US format)
--   104 = 'dd.mm.yyyy'            (German/EU dot format)
--   (no style) = SQL Server's general-purpose parser, which handles
--                formats like '26-May-2025' (day-month name-year)

USE MeridianDB;
GO

CREATE OR ALTER FUNCTION staging.fn_parse_messy_date(@raw_value NVARCHAR(50))
RETURNS DATETIME
AS
BEGIN
    RETURN COALESCE(
        TRY_CONVERT(datetime, @raw_value, 120),
        TRY_CONVERT(datetime, @raw_value, 101),
        TRY_CONVERT(datetime, @raw_value, 104),
        TRY_CONVERT(datetime, @raw_value)
    );
END
GO

-- MERIDIAN Phase 3 - Step 4 - VERIFICATION
-- Run this after creating the staging views above. It checks whether
-- fn_parse_messy_date successfully parsed every date it was given.
--
-- A NULL result here can mean two different things - important to tell
-- apart:
--   (a) the ORIGINAL raw value was already blank/missing (expected -
--       e.g. ~8% of delivered_date values were deliberately left empty
--       in Phase 1 to simulate missing delivery timestamps)
--   (b) the raw value had TEXT in it, but none of our 4 known date
--       formats matched it (a real bug - a format we didn't anticipate)
--
-- This query separates the two, so we only worry about case (b).

USE MeridianDB;
GO

SELECT
    'us_orders' AS source_table,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN order_date_raw IS NOT NULL AND order_date IS NULL THEN 1 ELSE 0 END) AS order_date_parse_failures,
    SUM(CASE WHEN delivered_date_raw IS NOT NULL AND delivered_date IS NULL THEN 1 ELSE 0 END) AS delivered_date_parse_failures
FROM (
    SELECT
        r.order_date AS order_date_raw,
        staging.fn_parse_messy_date(r.order_date) AS order_date,
        r.delivered_date AS delivered_date_raw,
        staging.fn_parse_messy_date(r.delivered_date) AS delivered_date
    FROM raw.us_orders r
) x

UNION ALL

SELECT
    'de_orders',
    COUNT(*),
    SUM(CASE WHEN order_date_raw IS NOT NULL AND order_date IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN delivered_date_raw IS NOT NULL AND delivered_date IS NULL THEN 1 ELSE 0 END)
FROM (
    SELECT
        r.order_date AS order_date_raw,
        staging.fn_parse_messy_date(r.order_date) AS order_date,
        r.delivered_date AS delivered_date_raw,
        staging.fn_parse_messy_date(r.delivered_date) AS delivered_date
    FROM raw.de_orders r
) x

UNION ALL

SELECT
    'gh_orders',
    COUNT(*),
    SUM(CASE WHEN order_date_raw IS NOT NULL AND order_date IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN delivered_date_raw IS NOT NULL AND delivered_date IS NULL THEN 1 ELSE 0 END)
FROM (
    SELECT
        r.order_date AS order_date_raw,
        staging.fn_parse_messy_date(r.order_date) AS order_date,
        r.delivered_date AS delivered_date_raw,
        staging.fn_parse_messy_date(r.delivered_date) AS delivered_date
    FROM raw.gh_orders r
) x;
GO

-- If any *_parse_failures column shows a number above 0, run this next
-- (swap in the right table name) to actually SEE the values that didn't
-- parse, so we can add a 5th format to the helper function if needed:
--
-- SELECT DISTINCT order_date
-- FROM raw.us_orders
-- WHERE order_date IS NOT NULL
--   AND staging.fn_parse_messy_date(order_date) IS NULL;

-- MERIDIAN Phase 3, Part B - VERIFICATION
-- Different risks here than Part A's date-parsing check: the risk with
-- joins is silently losing or duplicating rows. This checks row counts
-- match expectations, and measures how common the known gaps are.

USE MeridianDB;
GO

-- Check 1: row count sanity. staging.stg_olist_orders should have
-- close to the same row count as raw.olist_orders_dataset (a LEFT JOIN
-- can only keep the same count or fewer matched rows from the joins on
-- the right side - it should never multiply rows if the joins are
-- correct. If this comes back HIGHER than the raw count, one of the
-- joins is duplicating rows and needs fixing).
SELECT
    (SELECT COUNT(*) FROM raw.olist_orders_dataset) AS raw_olist_order_count,
    (SELECT COUNT(*) FROM staging.stg_olist_orders) AS staging_olist_order_count;

-- Check 2: how many Olist orders ended up with no matching review, no
-- matching category, or no matching customer? Some of this is expected
-- (not every order gets reviewed) - this just tells you the scale.
SELECT
    COUNT(*) AS total_orders,
    SUM(CASE WHEN review_score IS NULL THEN 1 ELSE 0 END) AS missing_review,
    SUM(CASE WHEN product_category IS NULL THEN 1 ELSE 0 END) AS missing_category,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS missing_customer,
    SUM(CASE WHEN amount_local IS NULL THEN 1 ELSE 0 END) AS missing_amount
FROM staging.stg_olist_orders;

-- Check 3: UCI row count sanity. staging.stg_uci_orders should have
-- roughly (number of DISTINCT Invoice values) rows, since it groups
-- line items up to one row per invoice.
SELECT
    (SELECT COUNT(DISTINCT Invoice) FROM raw.uci_online_retail_ii) AS raw_distinct_invoices,
    (SELECT COUNT(*) FROM staging.stg_uci_orders) AS staging_uci_order_count;

-- Check 4: how many UCI orders are flagged as refunds (the 'C' prefix
-- rule), and how many are missing a customer_id?
SELECT
    COUNT(*) AS total_orders,
    SUM(CASE WHEN is_refunded = 1 THEN 1 ELSE 0 END) AS flagged_as_refund,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS missing_customer
FROM staging.stg_uci_orders;
GO

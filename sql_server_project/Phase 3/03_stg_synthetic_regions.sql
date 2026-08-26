-- MERIDIAN Phase 3 - Step 3
-- Staging views for the synthetic regions (US, DE, GH) and fx_rates.
--
-- These three regions share an identical structure (same generator
-- script built all three), so the same cleaning logic is repeated per
-- region - one view each, so every region still has its own clearly
-- named table to query.
--
-- KEY DECISION: amount_local_currency is used as the trustworthy order
-- value. amount_display is deliberately NOT used here - it's a known
-- buggy field (simulates a real currency-conversion bug, see
-- PROJECT_LOG.md) and belongs in a later "data quality investigation"
-- write-up, not silently relied upon here.

USE MeridianDB;
GO

CREATE OR ALTER VIEW staging.stg_us_orders AS
SELECT
    order_id,
    customer_id,
    region,
    currency_code,
    amount_local_currency                              AS amount_local,
    product_category,
    staging.fn_parse_messy_date(order_date)             AS order_date,
    staging.fn_parse_messy_date(delivered_date)         AS delivered_date,
    CAST(is_refunded AS BIT)                            AS is_refunded,
    staging.fn_parse_messy_date(refund_date)            AS refund_date,
    review_score,
    order_status,
    'synthetic' AS source_system
FROM raw.us_orders;
GO

CREATE OR ALTER VIEW staging.stg_de_orders AS
SELECT
    order_id,
    customer_id,
    region,
    currency_code,
    amount_local_currency                              AS amount_local,
    product_category,
    staging.fn_parse_messy_date(order_date)             AS order_date,
    staging.fn_parse_messy_date(delivered_date)         AS delivered_date,
    CAST(is_refunded AS BIT)                            AS is_refunded,
    staging.fn_parse_messy_date(refund_date)            AS refund_date,
    review_score,
    order_status,
    'synthetic' AS source_system
FROM raw.de_orders;
GO

CREATE OR ALTER VIEW staging.stg_gh_orders AS
SELECT
    order_id,
    customer_id,
    region,
    currency_code,
    amount_local_currency                              AS amount_local,
    product_category,
    staging.fn_parse_messy_date(order_date)             AS order_date,
    staging.fn_parse_messy_date(delivered_date)         AS delivered_date,
    CAST(is_refunded AS BIT)                            AS is_refunded,
    staging.fn_parse_messy_date(refund_date)            AS refund_date,
    review_score,
    order_status,
    'synthetic' AS source_system
FROM raw.gh_orders;
GO

-- Customer staging views: cleaned up, email standardized to lowercase +
-- trimmed (helps with SOME duplicate matching later, though not all -
-- a duplicate with a dropped "." in the email won't be caught by this
-- alone. Full deduplication logic is deferred to the customer analysis
-- phase and will be documented there as a known limitation.)

CREATE OR ALTER VIEW staging.stg_us_customers AS
SELECT
    customer_id,
    first_name,
    last_name,
    LOWER(LTRIM(RTRIM(email)))                          AS email,
    city,
    region,
    staging.fn_parse_messy_date(signup_date)            AS signup_date
FROM raw.us_customers;
GO

CREATE OR ALTER VIEW staging.stg_de_customers AS
SELECT
    customer_id,
    first_name,
    last_name,
    LOWER(LTRIM(RTRIM(email)))                          AS email,
    city,
    region,
    staging.fn_parse_messy_date(signup_date)            AS signup_date
FROM raw.de_customers;
GO

CREATE OR ALTER VIEW staging.stg_gh_customers AS
SELECT
    customer_id,
    first_name,
    last_name,
    LOWER(LTRIM(RTRIM(email)))                          AS email,
    city,
    region,
    staging.fn_parse_messy_date(signup_date)            AS signup_date
FROM raw.gh_customers;
GO

-- FX rates: simple pass-through with clean column names. Note:
-- fetched_at_utc is left as raw text here rather than parsed - the API
-- returns it in a format (e.g. "Mon, 24 Aug 2026 00:02:33 +0000") that
-- fn_parse_messy_date wasn't built or tested against, and the exact
-- fetch timestamp isn't critical for the analysis phases ahead, so it
-- wasn't worth the added untested complexity right now.

CREATE OR ALTER VIEW staging.stg_fx_rates AS
SELECT
    currency_code,
    usd_to_currency_rate,
    fetched_at_utc AS fetched_at_utc_raw
FROM raw.fx_rates;
GO

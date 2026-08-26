-- MERIDIAN Dashboard Phase - Step 2
-- Pre-aggregated views for Power BI. These replicate logic already
-- built and verified in the Jupyter notebooks (Module 2 revenue,
-- Module 6 delivery), re-expressed in SQL so Power BI can pull ready-
-- made summaries instead of recomputing them itself.

USE MeridianDB;
GO

-- Revenue summary by region - same tracked/realized formula verified
-- and fixed in analysis/01_revenue_reporting.ipynb (see PROJECT_LOG.md
-- for the bug that was caught and corrected there). Tracked = value of
-- genuine sales only (amount_usd > 0); refund impact = absolute value
-- of anything flagged as refunded, regardless of which sign convention
-- the source used.
CREATE OR ALTER VIEW reporting.vw_revenue_by_region AS
SELECT
    region,
    SUM(CASE WHEN amount_usd > 0 THEN amount_usd ELSE 0 END) AS tracked_revenue_usd,
    SUM(CASE WHEN is_refunded = 1 THEN ABS(amount_usd) ELSE 0 END) AS revenue_lost_to_refunds_usd,
    SUM(CASE WHEN amount_usd > 0 THEN amount_usd ELSE 0 END)
        - SUM(CASE WHEN is_refunded = 1 THEN ABS(amount_usd) ELSE 0 END) AS realized_revenue_usd,
    CAST(SUM(CASE WHEN is_refunded = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS refund_rate,
    COUNT(*) AS total_orders
FROM marts.fct_orders
GROUP BY region;
GO

-- Delivery performance by region - mean delivery time, using only
-- orders with a valid (non-negative) delivery duration, same filter
-- used in analysis/04_logistics_delivery.ipynb.
--
-- IMPORTANT: uses DATEDIFF(second, ...) / 86400.0, then FLOOR(), rather
-- than DATEDIFF(day, ...) directly. SQL Server's day-level DATEDIFF
-- counts calendar-midnight crossings, not elapsed 24-hour periods - an
-- order placed at 11:31pm and delivered at 1:00am the next day would
-- count as "1 day" under DATEDIFF(day,...) despite only 90 minutes
-- elapsing. This matters here specifically because Brazil's real Olist
-- timestamps have genuine time-of-day components (the synthetic
-- regions' timestamps sit at midnight, masking the issue there). Using
-- seconds-elapsed / 86400, then flooring, matches Python's true-
-- elapsed-time behavior (pandas' .dt.days) exactly.
CREATE OR ALTER VIEW reporting.vw_delivery_performance AS
SELECT
    region,
    AVG(FLOOR(CAST(DATEDIFF(second, order_date, delivered_date) AS FLOAT) / 86400.0)) AS mean_delivery_days,
    COUNT(*) AS orders_with_delivery_data
FROM marts.fct_orders
WHERE delivered_date IS NOT NULL
  AND delivered_date >= order_date
GROUP BY region;
GO

-- Review score by delivery-time bucket - mirrors the bucket chart in
-- Module 6. Same true-elapsed-time fix applied as the view above.
--
-- Includes bucket_sort_order as an independent numeric column (not
-- derived from delivery_bucket in Power BI via DAX) specifically so
-- Power BI can sort the text buckets correctly without a circular
-- dependency - both columns come straight from this same CASE logic
-- at the SQL layer, neither one computed from the other downstream.
CREATE OR ALTER VIEW reporting.vw_review_by_delivery_bucket AS
WITH delivery_calc AS (
    SELECT
        review_score,
        FLOOR(CAST(DATEDIFF(second, order_date, delivered_date) AS FLOAT) / 86400.0) AS delivery_days
    FROM marts.fct_orders
    WHERE delivered_date IS NOT NULL
      AND delivered_date >= order_date
      AND review_score IS NOT NULL
),
bucketed AS (
    SELECT
        review_score,
        CASE
            WHEN delivery_days <= 2 THEN '0-2 days'
            WHEN delivery_days <= 5 THEN '3-5 days'
            WHEN delivery_days <= 10 THEN '6-10 days'
            WHEN delivery_days <= 20 THEN '11-20 days'
            ELSE '20+ days'
        END AS delivery_bucket,
        CASE
            WHEN delivery_days <= 2 THEN 1
            WHEN delivery_days <= 5 THEN 2
            WHEN delivery_days <= 10 THEN 3
            WHEN delivery_days <= 20 THEN 4
            ELSE 5
        END AS bucket_sort_order
    FROM delivery_calc
)
SELECT
    delivery_bucket,
    bucket_sort_order,
    AVG(CAST(review_score AS FLOAT)) AS avg_review_score,
    COUNT(*) AS order_count
FROM bucketed
GROUP BY delivery_bucket, bucket_sort_order;
GO

-- Simple pass-through views, giving Power BI clean, clearly-named
-- entry points into the order/customer detail without querying marts
-- directly - keeps a clean separation between "analysis layer" (marts)
-- and "dashboard layer" (reporting).
CREATE OR ALTER VIEW reporting.vw_orders_detail AS
SELECT * FROM marts.fct_orders;
GO

CREATE OR ALTER VIEW reporting.vw_customers_detail AS
SELECT * FROM marts.dim_customers;
GO

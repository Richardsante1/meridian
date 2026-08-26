-- MERIDIAN Phase 3, Part C - VERIFICATION + first real payoff query
--
-- Check 1: row count sanity - marts.fct_orders should equal the sum of
-- all 5 staging views' row counts (UNION ALL just stacks them, so
-- nothing should be gained or lost).

USE MeridianDB;
GO

SELECT
    (SELECT COUNT(*) FROM staging.stg_us_orders)
    + (SELECT COUNT(*) FROM staging.stg_de_orders)
    + (SELECT COUNT(*) FROM staging.stg_gh_orders)
    + (SELECT COUNT(*) FROM staging.stg_olist_orders)
    + (SELECT COUNT(*) FROM staging.stg_uci_orders) AS sum_of_staging_counts,
    (SELECT COUNT(*) FROM marts.fct_orders) AS marts_order_count;

-- Check 2: did every row get a currency conversion? (amount_usd should
-- never be NULL if amount_local wasn't NULL - a NULL here would mean a
-- currency_code that didn't match anything in fx_rates)
SELECT
    COUNT(*) AS total_orders,
    SUM(CASE WHEN amount_local IS NOT NULL AND amount_usd IS NULL THEN 1 ELSE 0 END) AS conversion_failures
FROM marts.fct_orders;

-- The payoff: your first real cross-region business question, now
-- answerable in one query across all 5 regions at once.
SELECT
    region,
    COUNT(*) AS total_orders,
    SUM(amount_usd) AS total_revenue_usd,
    AVG(amount_usd) AS avg_order_value_usd,
    SUM(CASE WHEN is_refunded = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS refund_rate
FROM marts.fct_orders
GROUP BY region
ORDER BY total_revenue_usd DESC;
GO

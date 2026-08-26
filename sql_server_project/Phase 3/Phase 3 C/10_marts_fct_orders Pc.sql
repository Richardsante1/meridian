-- MERIDIAN Phase 3, Part C - Step 3
-- marts.fct_orders - every order from all 5 regions, unified, WITH a
-- currency-normalized USD amount added. "fct" = "fact" table: records
-- an event (an order happening), as opposed to a "dim" table describing
-- an entity (a customer).
--
-- CURRENCY CONVERSION DIRECTION - worth being precise about, since this
-- is an easy thing to get backwards: staging.stg_fx_rates stores
-- "usd_to_currency_rate", meaning "1 USD equals this many units of the
-- currency" (e.g. if usd_to_currency_rate for GHS is 14.5, that means
-- 1 USD = 14.5 GHS). So converting a LOCAL amount back to USD means
-- DIVIDING by that rate, not multiplying: amount_usd = amount_local /
-- usd_to_currency_rate. Getting this backwards would make Ghana look
-- ~14x too expensive rather than converting correctly - exactly the
-- kind of currency-handling mistake worth documenting that you checked.

USE MeridianDB;
GO

CREATE OR ALTER VIEW marts.fct_orders AS
WITH all_orders AS (
    SELECT * FROM staging.stg_us_orders
    UNION ALL
    SELECT * FROM staging.stg_de_orders
    UNION ALL
    SELECT * FROM staging.stg_gh_orders
    UNION ALL
    SELECT * FROM staging.stg_olist_orders
    UNION ALL
    SELECT * FROM staging.stg_uci_orders
)
SELECT
    o.order_id,
    o.customer_id,
    o.region,
    o.currency_code,
    o.amount_local,
    -- USD is its own currency, so its "rate" is always 1 - handled with
    -- COALESCE in case fx_rates ever doesn't have a USD row for some reason
    o.amount_local / COALESCE(fx.usd_to_currency_rate, 1.0) AS amount_usd,
    o.product_category,
    o.order_date,
    o.delivered_date,
    o.is_refunded,
    o.refund_date,
    o.review_score,
    o.order_status,
    o.source_system
FROM all_orders o
LEFT JOIN staging.stg_fx_rates fx
    ON o.currency_code = fx.currency_code;
GO

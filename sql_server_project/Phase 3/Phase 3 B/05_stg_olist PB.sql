-- MERIDIAN Phase 3, Part B - Staging views for real Olist data (Brazil)
--
-- REAL-DATA QUIRK #1: Olist's customer_id is order-scoped, not
-- person-scoped - the same real person gets a different customer_id
-- for every order they place. The true, deduplicated per-person ID is
-- customer_unique_id, found in raw.olist_customers_dataset. We use
-- customer_unique_id as "the customer" everywhere below.
--
-- REAL-DATA QUIRK #2: an order can contain multiple line items, each
-- possibly a different product category. Since our unified model needs
-- ONE category per order (to match the synthetic regions' structure),
-- we tag each order with the category of its highest-value line item.
-- This is a simplification, documented here rather than hidden.
--
-- REAL-DATA QUIRK #3: Olist has no explicit refund/return flag. The
-- closest available proxy is order_status = 'canceled', which is NOT
-- the same thing as a monetary refund - a cancellation can happen
-- before a payment even completes. This is a genuine cross-source
-- limitation, worth a line in the case study's limitations section.

USE MeridianDB;
GO

-- Step 1: one row per order, aggregated from order_items, with the
-- dominant (highest-value) category attached.
CREATE OR ALTER VIEW staging.stg_olist_order_totals AS
WITH ranked_items AS (
    SELECT
        oi.order_id,
        oi.product_id,
        oi.price,
        oi.freight_value,
        ROW_NUMBER() OVER (PARTITION BY oi.order_id ORDER BY oi.price DESC) AS rn
    FROM raw.olist_order_items_dataset oi
)
SELECT
    order_id,
    SUM(price) + SUM(freight_value) AS amount_local,
    COUNT(*) AS item_count,
    MAX(CASE WHEN rn = 1 THEN product_id END) AS dominant_product_id
FROM ranked_items
GROUP BY order_id;
GO

-- Step 2: the main unified-shape staging view for Olist orders.
CREATE OR ALTER VIEW staging.stg_olist_orders AS
SELECT
    o.order_id,
    cust.customer_unique_id                                  AS customer_id,
    'BR'                                                       AS region,
    'BRL'                                                       AS currency_code,
    tot.amount_local,
    COALESCE(cat_en.product_category_name_english, prod.product_category_name) AS product_category,
    TRY_CONVERT(datetime, o.order_purchase_timestamp, 120)    AS order_date,
    TRY_CONVERT(datetime, o.order_delivered_customer_date, 120) AS delivered_date,
    CASE WHEN o.order_status = 'canceled' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_refunded,
    CAST(NULL AS DATETIME)                                     AS refund_date,  -- not tracked in Olist
    rev.review_score,
    o.order_status,
    'olist' AS source_system
FROM raw.olist_orders_dataset o
LEFT JOIN raw.olist_customers_dataset cust
    ON o.customer_id = cust.customer_id
LEFT JOIN staging.stg_olist_order_totals tot
    ON o.order_id = tot.order_id
LEFT JOIN raw.olist_products_dataset prod
    ON tot.dominant_product_id = prod.product_id
LEFT JOIN raw.product_category_name_translation cat_en
    ON prod.product_category_name = cat_en.product_category_name
LEFT JOIN (
    -- an order can technically have more than one review; keep the
    -- highest score per order as a simple, documented tie-break rule
    SELECT order_id, MAX(review_score) AS review_score
    FROM raw.olist_order_reviews_dataset
    GROUP BY order_id
) rev
    ON o.order_id = rev.order_id;
GO

-- Step 3: customers, deduplicated to the real person-level ID.
CREATE OR ALTER VIEW staging.stg_olist_customers AS
SELECT
    customer_unique_id AS customer_id,
    NULL AS first_name,     -- Olist doesn't include customer names at all
    NULL AS last_name,
    NULL AS email,           -- or emails - privacy-scrubbed in the public dataset
    MAX(customer_city)  AS city,
    'BR' AS region,
    NULL AS signup_date      -- no signup date tracked in Olist, only order history
FROM raw.olist_customers_dataset
GROUP BY customer_unique_id;
GO

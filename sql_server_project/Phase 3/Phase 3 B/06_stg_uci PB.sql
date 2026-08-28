-- MERIDIAN Phase 3, Part B - Staging views for real UCI data (UK)
--
-- REAL-DATA QUIRK: this dataset is transaction-LINE-level (one row per
-- product per invoice), not order-level - the same aggregation problem
-- as Olist, solved the same way: group by Invoice to get one row per
-- order.
--
-- REAL-DATA QUIRK: refunds/cancellations are encoded directly in the
-- Invoice number - any invoice starting with the letter 'C' is a
-- cancellation, per UCI's own documented convention. There is no
-- separate flag column for this.
--
-- REAL-DATA QUIRK: no product category field exists at all - only a
-- free-text Description per line item. Mapping thousands of free-text
-- descriptions to categories would need real NLP/manual work, which is
-- out of scope here - product_category is left NULL for this source,
-- documented as a limitation rather than guessed at.
--
-- REAL-DATA QUIRK: a meaningful share of rows have no Customer ID at
-- all (anonymous/guest-style transactions) - kept as NULL rather than
-- invented.

USE MeridianDB;
GO

CREATE staging.stg_uci_orders AS
SELECT
    Invoice                                             AS order_id,
    CAST([Customer ID] AS NVARCHAR(20))                 AS customer_id,
    'UK'                                                 AS region,
    'GBP'                                                AS currency_code,
    SUM(Quantity * Price)                               AS amount_local,
    CAST(NULL AS NVARCHAR(100))                          AS product_category,   -- not available in this source, see note above
    MIN(TRY_CONVERT(datetime, InvoiceDate))             AS order_date,
    CAST(NULL AS DATETIME)                               AS delivered_date,     -- no logistics tracking in this source
    CASE WHEN LEFT(Invoice, 1) = 'C' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_refunded,
    CASE WHEN LEFT(Invoice, 1) = 'C' THEN MIN(TRY_CONVERT(datetime, InvoiceDate)) ELSE NULL END AS refund_date,
    CAST(NULL AS INT)                                    AS review_score,        -- not available in this source
    CASE WHEN LEFT(Invoice, 1) = 'C' THEN 'cancelled' ELSE 'completed' END AS order_status,
    'uci' AS source_system
FROM raw.uci_online_retail_ii
   WHERE LEFT(Invoice, 1) <> 'A'
GROUP BY Invoice, [Customer ID];
GO

CREATE OR ALTER VIEW staging.stg_uci_customers AS
SELECT DISTINCT
    CAST([Customer ID] AS NVARCHAR(20)) AS customer_id,
    NULL AS first_name,      -- not available in this source
    NULL AS last_name,
    NULL AS email,
    Country AS city,          -- UCI only gives country, not city - kept in the "city" slot with that caveat documented
    'UK' AS region,
    NULL AS signup_date       -- not tracked in this source
FROM raw.uci_online_retail_ii
WHERE [Customer ID] IS NOT NULL;
GO

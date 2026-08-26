-- MERIDIAN Dashboard Phase - Step 3 - VERIFICATION
-- Quick sanity checks: the reporting views should produce numbers
-- matching what the Jupyter notebooks already found and verified.

USE MeridianDB;
GO

-- Should closely match Module 2's corrected revenue table (UK ~$28.6M
-- tracked, ~15% refund rate, after the UCI fix)
SELECT * FROM reporting.vw_revenue_by_region ORDER BY tracked_revenue_usd DESC;

-- Should closely match Module 6's corrected delivery table (DE ~4.0
-- days, US ~5.5, GH ~8.7, BR ~12.1 mean delivery days)
SELECT * FROM reporting.vw_delivery_performance ORDER BY mean_delivery_days;

-- Should show the same threshold pattern as Module 6's bucket chart:
-- steady ~4.3 avg score through 10 days, dipping past 20 days
SELECT * FROM reporting.vw_review_by_delivery_bucket
ORDER BY
    CASE delivery_bucket
        WHEN '0-2 days' THEN 1
        WHEN '3-5 days' THEN 2
        WHEN '6-10 days' THEN 3
        WHEN '11-20 days' THEN 4
        ELSE 5
    END;
GO

-- MERIDIAN Phase 3, Part C - Step 2
-- marts.dim_customers - every customer from all 5 regions, stacked into
-- one table. "dim" is short for "dimension" - standard data warehousing
-- naming for a table describing WHO/WHAT (customers, products), as
-- opposed to a "fact" table which records WHAT HAPPENED (orders).
--
-- UNION ALL simply stacks rows from multiple queries on top of each
-- other, as long as they have the same columns in the same order. It's
-- the SQL equivalent of pasting multiple spreadsheets underneath each
-- other. (UNION ALL keeps every row, including exact duplicates across
-- sources; plain UNION would also remove duplicate rows - ALL is used
-- here because there shouldn't be any real duplicate customers across
-- different regions, so there's nothing to remove.)

USE MeridianDB;
GO

CREATE OR ALTER VIEW marts.dim_customers AS
SELECT customer_id, first_name, last_name, email, city, region, signup_date FROM staging.stg_us_customers
UNION ALL
SELECT customer_id, first_name, last_name, email, city, region, signup_date FROM staging.stg_de_customers
UNION ALL
SELECT customer_id, first_name, last_name, email, city, region, signup_date FROM staging.stg_gh_customers
UNION ALL
SELECT customer_id, first_name, last_name, email, city, region, signup_date FROM staging.stg_olist_customers
UNION ALL
SELECT customer_id, first_name, last_name, email, city, region, signup_date FROM staging.stg_uci_customers;
GO

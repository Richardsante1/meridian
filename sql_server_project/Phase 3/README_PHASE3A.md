# MERIDIAN — Phase 3, Part A: Staging Layer for Synthetic Regions

This is the first half of Phase 3 — cleaning up your own US/DE/GH data.
The real Olist + UCI data (harder, more quirks) comes in Part B, once
this half is confirmed working.

## Step 1 — Get the files into place

In File Explorer, go to `Documents\Meridian\sql_server_project`. Create
a new folder called `phase3` (if it doesn't already exist from the
download). Drag these 4 files into it:
- `01_create_staging_schema.sql`
- `02_fn_parse_messy_date.sql`
- `03_stg_synthetic_regions.sql`
- `04_verify_date_parsing.sql`

## Step 2 — Run them in SSMS, in this exact order

Open a **New Query** window in SSMS for each one (or reuse one window,
clearing it between steps — either works).

1. Open `01_create_staging_schema.sql`, paste, Execute.
   Expect: `Schema [staging] created.`

2. Open `02_fn_parse_messy_date.sql`, paste, Execute.
   Expect: `Commands completed successfully` (no PRINT message this
   time — creating a function doesn't print anything, that's normal).

3. Open `03_stg_synthetic_regions.sql`, paste, Execute.
   Expect: `Commands completed successfully` — this creates 7 views
   (3 order views, 3 customer views, 1 fx_rates view). Nothing visible
   happens yet; a view is just a saved query, it doesn't show data
   until you ask it to.

## Step 3 — The important one: verify the date parsing worked

Open `04_verify_date_parsing.sql`, paste, Execute.

You'll get a results grid with 3 rows (one per region) and 4 columns:
`source_table`, `total_rows`, `order_date_parse_failures`,
`delivered_date_parse_failures`.

**What you want to see:** both failure columns showing **0** for all
three rows.

**If you see a number above 0** in any failure column: that's fine,
it just means one of your four date formats snuck through in a shape
the helper function didn't expect. Run the follow-up query at the
bottom of the same file (uncomment it — remove the `--` from the front
of each line, swap in the table name that showed a failure), which
will show you the actual raw text values that failed. **Paste that
result to me** and I'll add a 5th format to the helper function.

## Step 4 — Take a look at the cleaned data

Once verification shows all zeros, look at the result of your work:

```sql
SELECT TOP 20 * FROM staging.stg_us_orders;
SELECT TOP 20 * FROM staging.stg_gh_customers;
```

Compare this to `SELECT TOP 20 * FROM raw.us_orders` — same data, but
now `order_date` and `delivered_date` are real, proper datetime values
instead of a mix of text formats.

---

Once verification passes, tell me and we'll do Part B: staging views
for the real Olist and UCI data — which have their own real-world
quirks (Olist stores customer IDs strangely, UCI mixes returns into
the same table as regular orders) worth understanding properly.

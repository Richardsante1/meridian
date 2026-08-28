# MERIDIAN — Project Log

A running log of what was built, what decisions were made and why, and
what went wrong along the way. Kept in plain language as we go — this
becomes the raw material for README.md, DATA_DICTIONARY.md, and
CASE_STUDY.pdf later. Add a few lines to this after each work session;
don't try to reconstruct it from memory at the end.

---

## Phase 1 — Data Sourcing (complete)

**What was built:**
- A Python script (`generate_synthetic_data.py`) that generates
  calibrated, deliberately messy synthetic order data for three regions
  not covered by real datasets: United States, Germany, and Ghana.
- A Python script (`fetch_exchange_rates.py`) that pulls live FX rates
  for BRL, GBP, EUR, GHS, USD.
- Two real datasets downloaded manually: Olist Brazilian E-Commerce
  (Kaggle) and UCI Online Retail II (UK).

**Key decisions and why (worth keeping verbatim for the README):**
1. **Nigeria → Ghana.** Fifth region changed from the original brief's
   Nigeria to Ghana. Faker (the Python library used for fake names/
   addresses) has no built-in Ghana locale, so a small hand-built pool
   of common Akan/Ga/Ewe first and last names and major Ghanaian cities
   was used instead of a full locale package — a documented
   simplification, not a hidden one.
2. **FX API swapped.** The original plan was Frankfurter or
   exchangerate.host. Frankfurter (ECB-based) doesn't carry GHS at all.
   exchangerate.host now requires a paid key. Switched to
   `open.er-api.com` — free, no signup, and it does carry GHS.
3. **Calibration approach.** Synthetic order values/delivery times start
   from documented placeholder estimates (clearly labeled as such in
   `calibration_reference.json`), then get recalibrated against real
   Tier 1 data once it's downloaded. This is an intentional two-stage
   process, not guesswork dressed up as fact.

**Real finding from calibration:**
Once the real UCI (UK) data was loaded, the script computed a real
average order line value of **$20.56** (std $65.06) — versus the
placeholder assumption of $65-75 used before real data was available.
That gap is worth a sentence in the final case study: it shows the
synthetic data process being genuinely checked against reality, not
just asserted.

**Problems hit and how they were fixed (good "debugging story" material
for interviews):**
- The Python virtual environment was first created one folder level too
  high (`Meridian\` instead of `Meridian\data_generation\`). Fixed by
  deleting it and recreating it in the correct folder.
- The UCI dataset downloaded as a `.csv` file instead of the expected
  `.xlsx`. The generator script was updated to detect and correctly
  read either format.
- Reading the `.xlsx` version (which showed up on a later re-download)
  failed because the `openpyxl` package wasn't installed. Fixed with
  `pip install openpyxl`.

**Result:** a fully reproducible Tier 1 + Tier 2 + Tier 3 data layer,
sitting in `data_generation/output/` and `data_generation/tier1_raw/`,
ready to be loaded into SQL Server.

---

## Phase 2 — SQL Server Setup & Raw Load (complete)

**What was built:**
- `MeridianDB` database created on a local SQL Server Developer Edition
  instance.
- A `raw` schema created inside it — a landing zone holding every source
  file's data exactly as it arrived, untyped/uncleaned on purpose.
- A Python loader (`03_load_raw_data.py`) that auto-creates one table per
  source file and loads it in chunks, using SQLAlchemy + pyodbc.

**Key decision:**
Tables in the `raw` schema use auto-inferred column types (from pandas)
rather than a hand-designed schema. This is a deliberate ELT pattern —
land data as-is first, clean and properly type it in the next layer
(staging/marts, Phase 3). Chosen because hand-writing precise `CREATE
TABLE` DDL for every column across 16+ source files (many from Olist,
whose schema is already well-documented) would be a lot of manual,
error-prone work for no real benefit at the raw layer.

**Bug hit and fixed (good debugging story for interviews):**
The loader's logic for picking a SQL Server ODBC driver sorted driver
names alphabetically and picked whichever came first — but the
machine had two drivers installed: the modern `"ODBC Driver 17 for
SQL Server"` and an older, more limited driver simply named `"SQL
Server"`. Alphabetically, `"SQL Server"` sorts ahead of `"ODBC Driver
17..."`, so the script picked the weaker driver by pure coincidence of
spelling. That driver couldn't handle a data type pandas generated for
a column (a float column with all-null values), throwing `Invalid
precision value (0)`.
**Fix:** replaced the alphabetical sort with an explicit preference
list (ODBC Driver 18 → 17 → 13 → legacy `"SQL Server"` as last resort).
**Lesson worth remembering:** never assume "sorts first" means "is
best" when picking between similarly-named system resources — prefer
an explicit, intentional list.

**Result:** all 17 source files loaded successfully into
`MeridianDB.raw` — synthetic US/DE/GH order + customer data, FX rates,
and the real Olist (9 files) and UCI Online Retail II datasets.

---

## Phase 3 — Staging & Mart Models (in progress)

**Part A complete: staging views for synthetic regions (US, DE, GH)**

Built:
- `staging` schema.
- `staging.fn_parse_messy_date()` — a reusable helper function that
  tries 4 known date formats in turn (using `TRY_CONVERT` +
  `COALESCE`) and returns the first one that parses successfully.
  Written once, reused across every staging view that needs date
  cleaning, rather than repeating the same logic in each view.
- Staging views for US/DE/GH orders and customers, plus fx_rates —
  clean column names, real datetime values, deliberately still using
  `amount_local_currency` (not the buggy `amount_display` field) as
  the trustworthy order value.

**Verification result:** ran a dedicated check comparing each raw date
value against its parsed result. 0 parse failures across all three
regions (2018 US orders, 2017 DE orders, 2016 GH orders) — all four
messy date formats from Phase 1 were handled correctly on the first
attempt, no fixes needed.

**Design note:** staging views are non-destructive — they read from
`raw` and clean on the fly, they don't alter or copy the underlying
raw tables. If a cleaning rule needs fixing later, only the view
changes; the raw data stays untouched as a safety net.

**Part B complete: staging views for real Olist (Brazil) and UCI (UK)
data.**

Real-world quirks handled and documented:
- Olist's `customer_id` is order-scoped (a repeat customer gets a new
  ID per order) — used `customer_unique_id` instead as the true
  person-level key.
- An Olist order can span multiple product categories (multiple line
  items) — tagged each order with its highest-value item's category,
  via `ROW_NUMBER()` ranking, documented as a simplification.
- Olist has no refund/return field — used `order_status = 'canceled'`
  as an approximate proxy, explicitly documented as NOT equivalent to
  a real monetary refund (a genuine cross-source limitation for the
  case study).
- UCI encodes cancellations in the invoice number itself (a leading
  `'C'`) rather than a separate flag — matched UCI's own documented
  convention rather than inventing a new rule.
- UCI has no product category field at all — left NULL rather than
  guessed at; would need real NLP/manual mapping work to derive,
  explicitly out of scope.

Verified row counts (raw vs. staging) matched on both sources — no
rows silently duplicated or dropped by the joins.

**Part C complete: unified marts layer.**

Built:
- `marts` schema — the final, analysis-ready layer that all future
  analysis phases will query.
- `marts.dim_customers` — all customers from all 5 regions, stacked via
  `UNION ALL` into one table.
- `marts.fct_orders` — all orders from all 5 regions, stacked the same
  way, with a currency-normalized `amount_usd` column added by joining
  to the FX rates and dividing by the USD conversion rate (documented
  carefully — dividing, not multiplying, is the correct direction here;
  worth double-checking on any currency conversion task).

**Result:** for the first time, a single query can answer a real
cross-region business question — total revenue, average order value,
and refund rate, per region, all in comparable USD terms. Row-count
checks confirmed the `UNION ALL` stacking didn't duplicate or drop any
rows across the merge.

**Phase 3 status: COMPLETE.** Raw → staging → marts pipeline fully
built for all 5 regions (US, DE, GH synthetic + Olist + UCI real data).

---

## Phase 4 — Analysis Modules 1-4: Revenue, Cohorts, RFM (in progress)

**Module 2 complete: Currency-Normalized Revenue Reporting**

Built `analysis/01_revenue_reporting.ipynb` — a Jupyter notebook
connecting directly to `marts.fct_orders`, computing tracked vs.
realized revenue and refund rate by region.

**A real bug was found and fixed during this analysis (good interview
material):** the first version of the tracked/realized calculation
assumed every region flags refunds the same way — a positive-valued
order tagged `is_refunded = 1`, true for US/DE/GH/Olist. UCI (UK) data
doesn't work that way: a cancellation there is stored as its own
*separate, negative-valued* row rather than a flag on the original
order. That mismatch caused the UK region's "realized revenue" to
compute as *higher* than its "tracked revenue" — a logically impossible
result, caught because the notebook's numbers didn't pass a basic
sanity check.
**Fix:** redefined tracked revenue as the sum of only genuinely
positive sale values, and refund impact as the absolute value of
whatever was refunded (handling both a positive-flagged-order
convention and a separate-negative-row convention correctly at once).
Verified against a small hand-built test case covering both
conventions before applying it to the real data.
**Lesson:** the underlying data (`marts.fct_orders`) was completely
correct — the bug was purely in how the analysis layer aggregated it.
A useful reminder that "the data is right" and "my calculation on top
of the data is right" are two separate things worth checking
independently.

**Findings (real numbers, from `marts.fct_orders`):**
- UK is the dominant region by tracked revenue (~$28.61M), ~9.3x
  Brazil (~$3.06M), and far above Germany/US (~$150-155K each) and
  Ghana (~$53K, smallest region).
- UK also has the highest refund rate (15%) — losing ~$2.08M to
  refunds, more than the other four regions' total revenue combined.
- Brazil has the lowest refund rate by far (1%, ~$20K lost) — despite
  being the second-largest region, it's proportionally the "cleanest."
- Germany (9%) and US (7%) sit in the middle; Ghana lowest among the
  synthetic regions (5%).
- **Takeaway:** revenue size and revenue quality are not the same
  thing — UK looks strongest on gross tracked revenue, but gives back
  the largest share of it, while Brazil is smaller but far more
  reliable proportionally.

**UPDATE (post Module 7 UCI fix):** re-ran this notebook after the
UCI half-loaded-data bug was fixed (see Module 7 below). UK's tracked
revenue roughly doubled, from $14.06M to **$28.61M**, closely matching
the ~1.9x increase in UCI data volume (13 months → 25 months) — a
good internal-consistency check that the fix behaved as expected.
Refund rate stayed essentially stable (16% → 15%), as expected for a
proportional metric computed on more months of the same underlying
pattern. BR/DE/US/GH figures are unchanged (unaffected by this fix).
All figures above updated to reflect the corrected data.

**Known limitation carried forward:** Olist's refund proxy
(`order_status = 'canceled'`) is not a true monetary refund flag, so
Brazil's 1% figure should be read as directionally indicative rather
than precisely comparable to the other four regions.

**Module 3 complete: Cohort Retention Analysis**

Built `analysis/02_cohort_retention.ipynb` — monthly cohort assignment
(first purchase month per customer) and a simplified repeat-purchase
rate comparison across regions.

**Detailed reading of the Step 3/4 heatmap (before the Step 6 fix was
built):** the clearest cohort, UK customers who first purchased in
2009-12, shows retention settling into a 34-43% range and holding
there for several months rather than dropping off sharply after month
1 — a real signal of a sizeable retained-customer base, consistent
with the 71.1% repeat-purchase figure. Most later cohorts show empty/
zero cells toward the right side of the chart — this is **not** low
retention, but **right-censoring**: a customer whose first purchase
was, say, September 2010 can't have a "month 10" data point if the
UCI dataset itself stops recording in mid-2011. There simply isn't
enough elapsed calendar time left in the data to observe it. Worth
stating explicitly as a general cohort-analysis caveat, not specific
to this project.

**A second real issue was caught and fixed while reviewing the Step
3/4 heatmap output:** pooling all five regions into one calendar-based
cohort heatmap produced a sparse, hard-to-read chart. Root cause: the
five sources span genuinely different, non-overlapping historical
eras — UCI (UK) is real 2009-2011 data, Olist (Brazil) is real
2016-2018 data, US/DE/GH are synthetic 2023-2025 data. Comparing
cohorts by raw calendar month meant, for example, a 2009 UK customer
and a 2024 Ghanaian customer were being placed in unrelated rows of
the same chart with no meaningful basis for comparison.
**Fix:** added a second retention view (Step 6) that groups by
`period_number` (months since each customer's own first purchase,
calendar-agnostic) and region, rather than raw calendar cohort month —
putting every region on the same relative timeline regardless of which
real-world years its data happens to come from. Verified against a
synthetic two-region test case (different decay rates, different
calendar eras) before applying to real data.
**Lesson:** this is a good general caution for any multi-source
project — a chart can be technically correct at the level of each
individual calculation and still be misleading in aggregate, if the
grouping dimension (here, calendar month) isn't equally meaningful
across every source being combined.

**Findings (real numbers, from `marts.fct_orders`):**
- Repeat purchase rate: US 88.4%, GH 88.2%, DE 85.6%, UK 75.4%,
  **BR 3.1%** (a dramatic outlier).
- Brazil's near-total lack of repeat customers matches a real,
  well-documented characteristic of the actual public Olist dataset —
  not a pipeline defect. Worth stating explicitly in the case study so
  it isn't mistaken for a bug.
- The three synthetic regions (US/DE/GH) cluster tightly together
  (85-88%), which likely reflects shared calibration assumptions from
  the Phase 1 data generation rather than three genuinely distinct
  underlying behaviors — an honest limitation to name, not an organic
  finding to overstate.
- UK sits in between (75.4%) — a real majority retained, but a
  meaningful step down from the synthetic regions.

**UPDATE (post Module 7 UCI fix):** re-ran after the UCI half-loaded
bug fix. UK's repeat-purchase rate rose modestly from 71.1% to
**75.4%** (+4.3 points) — a real, plausible shift, not just data
volume scaling: unlike revenue (a simple total that scales with data
size), repeat-purchase rate could have moved in either direction
depending on whether the added months mostly brought new one-time
customers (which would dilute the rate) or gave existing customers
more time to return (which would raise it). Here it rose, suggesting
the additional months captured genuine repeat behavior rather than
just adding fresh customers. US/GH/DE/BR unchanged, as expected.

**Known limitation carried forward:** UCI (UK) rows with a missing
`customer_id` (anonymous transactions) were excluded from this
analysis entirely, since retention can't be measured for a customer
who can't be identified across orders.

**Module 3 status: COMPLETE.** Step 6 (region-relative retention
comparison, fixing the calendar-pooling issue) is built and tested in
the notebook, ready to review at any point — not yet reviewed against
real output as of this log entry.

**Module 4 complete: RFM Customer Segmentation**

Built `analysis/03_rfm_segmentation.ipynb` — Recency/Frequency/Monetary
scoring per customer (region-relative reference dates and per-region
quantile scoring, reusing the lesson from Module 3), mapped to 6 named
segments (Champions, Loyal Customers, New Customers, At Risk, Lost,
Needs Attention) with segment-specific action recommendations.

**Findings (real numbers, from `marts.fct_orders`, ~103,130 customers
total post-fix):**
- Overall segment sizes: Loyal Customers largest (33,035, ~32%),
  followed by Needs Attention (20,435), Lost (17,286), New Customers
  (15,932), At Risk (8,224), Champions smallest (8,218).
- **A predicted limitation was confirmed exactly as anticipated:**
  Brazil shows 33.1% "Loyal Customers" — the *highest* of all five
  regions — which directly contradicts Module 3's finding that only
  3.1% of Brazilian customers ever place a second order. Root cause:
  since ~97% of Brazilian customers share an identical frequency value
  (1 order), the rank-based tie-breaking used to avoid `qcut` errors
  arbitrarily splits that huge tied group into 5 roughly equal score
  buckets — some one-time-only customers land in the top F score purely
  by tie-break luck, not real behavior. This exact failure mode was
  flagged as a known limitation in the notebook *before* the real
  results were seen, then confirmed against real data — a stronger
  form of validation than catching a bug after the fact.
- **Champions remains a trustworthy signal even for Brazil**, since it
  requires high scores on Recency, Frequency, AND Monetary
  simultaneously — much harder for tie-breaking alone to fake. Regional
  pattern here makes sense and is consistent with other findings: UK
  highest (21.4%), Ghana (18.4%), US (17.0%), Germany (15.6%), Brazil
  lowest by a wide margin (6.9%).
- UK also shows the fewest New Customers (8.5%, lowest of all
  regions) — plausible given that data reflects a more "settled" 2009-
  2011 customer base, versus the fresher 2023-2025 synthetic regions.

**Practical takeaway for the case study:** segment labels built on top
of a metric with very low variance (frequency, when ~97% of customers
share the same value) can look meaningful while actually being close
to noise. "Loyal Customers" figures should be read together with
Champions and the underlying repeat-purchase rate, not in isolation.

**UPDATE (post Module 7 UCI fix):** re-ran after the UCI half-loaded
bug fix. UK's segment percentages shifted only slightly (Champions
21.4%→21.9%, Loyal Customers 18.6%→18.1%, Lost 23.5%→25.8%, New
Customers 8.5%→7.7%) — small, explainable moves, not a meaningful
change in the underlying finding. Overall customer totals rose
slightly too (~101,571 → ~103,130, reflecting more UK customers now
visible in the complete UCI data), but the overall segment mix barely
moved (Loyal Customers 32.3% → 32.0% of all customers) — confirming
the original finding was accurate and simply needed updated raw
counts. This is a useful confirmation: quantile-based scoring is
relative by construction, so it's naturally robust to changes in data
volume, unlike an absolute total (revenue, which roughly doubled with
the fix) or a cumulative behavioral metric (repeat-purchase rate,
which shifted moderately). The two largest individual moves (Lost
+2.3pts, New Customers -0.8pts) make sense together: more UCI data
extends the region's timeline further into 2011, so relative to that
later reference date, proportionally fewer customers still look "new"
and slightly more have had enough elapsed
time to be genuinely inactive.

**Phase 4 status: COMPLETE.** Revenue reporting, cohort retention, and
RFM segmentation all built, tested, and run against real data across
all 5 regions.

---

## Phase 5 — Analysis Modules 5-8: Attribution, Logistics, Forecasting, Anomaly Flags (in progress)

**Module 5 (Marketing Channel Attribution) — reinstated after initial
skip.** Ran `generate_marketing_data.py` and reloaded via the Phase 2
loader script successfully (`raw.channel_spend`: 16,440 rows,
`raw.order_channel_attribution`: 6,051 rows, alongside all other tables
reloading cleanly). Built `analysis/05_marketing_attribution.ipynb`,
computing last-touch CAC (Customer Acquisition Cost) and ROAS (Return
on Ad Spend) by channel and region. Logic tested against simulated
attribution data before running on the real pipeline.

**Explicitly documented limitation, more significant than other
modules':** this is the only module built on fully synthetic data with
no real-world grounding at all — unlike order values or delivery
times (calibrated against real Tier 1 data in Phase 1), spend and
attribution here are pure invention. Findings from this module should
be presented as a demonstration of methodology, not as genuine
business insight, and the notebook's own findings section states this
directly.

**Findings (from `raw.order_channel_attribution` + `raw.channel_spend`
+ `marts.fct_orders`, synthetic US/DE/GH only):**
- Only organic (ROAS 1.87-2.61) and email (ROAS 1.20-1.76) beat
  break-even, in every region. Referral, social, and paid_search all
  lose money on a pure ROAS basis in every region, with paid_search
  worst (ROAS 0.16-0.22).
- CAC tells the identical story: organic cheapest to acquire through
  ($51.77-$137.19/customer), paid_search most expensive by a wide
  margin ($565-$1,202/customer, 10x+ pricier than organic in places).
- **Meta-finding, worth stating directly:** the same channel (organic)
  wins on *both* ROAS and CAC in *every single region*, and the same
  channel (paid_search) loses on *both* in every region — no tradeoffs
  at all. Real channel performance data would typically show at least
  some tension (e.g. an expensive channel that converts higher-value
  customers). This suspiciously perfect consistency is itself evidence
  the underlying spend/attribution data is synthetic and formulaic
  rather than reflecting genuine market dynamics — reinforcing the
  module's own documented limitation rather than contradicting it.

**Module 5 status: COMPLETE**, with its limitation clearly evidenced
by the results themselves, not just asserted in advance.

**Module 6 (Logistics & Delivery Performance) — a real, significant
bug was found and fixed while reviewing early results.** Initial
delivery-time summary showed implausible numbers: mean delivery time
14-22 days for the synthetic regions, but standard deviation of 40-47
days (larger than the mean itself) - a strong signal of outliers or a
parsing bug. Investigation (`nlargest` on delivery_days, then checking
the underlying raw text) found orders with 300+ day "delivery times,"
and every one of them had a `delivered_date` landing suspiciously in
November/December regardless of order date - a pattern, not chance.

**Root cause:** the `staging.fn_parse_messy_date()` function (built in
Phase 3) tried date formats in a fixed order and trusted whichever one
"succeeded" first. For an ambiguous date like `'12.01.2025'` (day=12,
month=01 - both valid as either), SQL Server's `TRY_CONVERT` under the
US-style attempt doesn't actually require a slash separator, so it
silently accepted the EU-formatted string and misread it as December
1st instead of the correct January 12th - with no error thrown at all,
since the wrong parse still "succeeded" technically.

**Fix:** rewrote the function to route by separator character first
(a dot always means EU dd.mm.yyyy, a slash always means US mm/dd/yyyy)
instead of trying formats in sequence and hoping. Verified against all
4 known date formats, including the exact ambiguous case that broke,
before redeploying. Because the entire staging/marts layer is built on
views (not materialized tables), fixing this one function retroactively
corrects every date across the whole project with no data reload
needed - the payoff of the non-destructive view-based design chosen in
Phase 3.

**Lesson worth remembering:** an automatic "try several formats and
use whichever succeeds" approach is dangerous specifically when
formats can *silently* overlap on ambiguous input - the danger isn't
formats that fail to parse, it's formats that parse *successfully but
incorrectly*, since nothing about the result looks obviously wrong
without independently checking it against the source.

**Fix confirmed live and verified** — a direct SQL test
(`staging.fn_parse_messy_date('12.01.2025')`) initially still returned
the old wrong answer after a laptop power loss interrupted the first
fix attempt; the `CREATE OR ALTER FUNCTION` had never actually
executed against the database, only saved to the local `.sql` file.
Re-ran it properly in SSMS, re-verified with the same direct test
(now correctly returns `2025-01-12`), then re-pulled fresh data into
the notebook from Step 1 onward.

**Corrected delivery-time results, before vs. after the fix:**
| Region | Mean days (before → after) | Std dev (before → after) |
|---|---|---|
| DE | 14.80 → 4.02 | 40.78 → 3.90 |
| US | 15.61 → 5.51 | 39.66 → 4.10 |
| GH | 22.12 → 8.72 | 47.11 → 5.44 |

A nice validation: the corrected means land close to the original
Phase 1 calibration targets (US 5.0, DE 3.5, GH 8.0 days) — the bug
had been obscuring how well-calibrated the synthetic data actually
was. Order counts also rose slightly per region (e.g. US 1,706 →
1,860) — the bug had been producing a handful of impossible *negative*
delivery times (delivered before ordered) that were correctly getting
filtered out, silently discarding otherwise-valid orders in the
process.

**Findings (real numbers, from `marts.fct_orders`, post-fix):**
- Delivery days and review score show a real, moderate negative
  correlation: **-0.310** across 100,531 orders with both fields.
- This isn't a smooth decline: review scores hold steady (~4.3) for
  any delivery under 10 days, dip mildly at 11-20 days (4.19), then
  fall sharply past 20 days (3.13) — a threshold effect.
- Repeat customers experienced meaningfully faster delivery on average
  (9.88 days, median 8.5) than one-time customers (12.09 days, median
  10.0) — consistent with the correlation finding, suggesting delivery
  speed plausibly plays a role in whether a customer returns.

**One more real finding, post-fix:** the top 10 longest deliveries in
the corrected data are now all from Brazil (real Olist data, 187-209
days) — not the synthetic regions. This is a different situation from
the bug above: Olist's real timestamps were never affected by the
ambiguous-date parsing issue (they arrive in a clean, unambiguous
format already). This matches a well-documented real characteristic
of the genuine Olist dataset — a small number of real-world orders
did take 6+ months to deliver, reflecting genuine logistics failures
rather than a data or pipeline issue.

**Module 6 status: COMPLETE**, including a genuinely strong bug-catch
story: a silent wrong answer, found by noticing an implausible
statistic (std dev larger than the mean), traced to its root cause,
fixed, and reverified independently before trusting the corrected
results.

---

**Module 7 (Demand Forecasting) — TWO real bugs found and fixed while
building this module, one of them significant enough to affect the
whole project.**

**Bug 1 (significant, project-wide impact): UCI Online Retail II had
only ever been half-loaded.** The real UCI dataset ships as an Excel
file with two sheets (one per year: "Year 2009-2010" and "Year
2010-2011"), but the Phase 2 loader script (`load_excel_to_table`)
used `pd.read_excel(xlsx_path, sheet_name=0)`, which silently reads
only the first sheet. This was caught by noticing the UK region showed
only 13 distinct months of order-history data, when the real dataset
spans roughly 25 months.
**Fix:** changed the loader to `pd.read_excel(xlsx_path,
sheet_name=None)` (reads all sheets into a dict) followed by
`pd.concat(...)` to combine them. Verified with a hand-built two-sheet
test file before touching the real data. Re-ran the loader: UK data
went from 13 to 25 months, row count roughly doubled.
**Project-wide impact:** because every downstream layer (staging,
marts) is built on views, this fix retroactively corrected every UK
figure computed in every earlier module - revenue, cohort retention,
and RFM segmentation all need re-checking against the corrected data
(logistics/delivery was unaffected, since UCI never had delivery or
review fields to begin with).

**Bug 2: an initial forecast for Brazil produced an impossible
negative number.** Root cause: the real Olist dataset's data collection
was cut off mid-way, producing two clearly incomplete final months
(September 2018: 16 orders, October 2018: 4 orders, versus a steady
~6,300-7,500/month beforehand). A trend model extrapolated that
artificial "crash" forward into negative territory.
**Fix, iterated twice:** first attempt trimmed only the single final
month, which fixed the negative sign but still produced an implausibly
low forecast (542 total) since the second-to-last broken month (16
orders) was still poisoning the trend estimate. Rewrote
`trim_incomplete_tail()` to trim iteratively (checking and re-checking
after each drop, up to a safety cap of 3 periods) rather than only
once. Verified against Brazil's actual real monthly data before
redeploying - final forecast came out to ~6,297/month, matching the
genuine recent history almost exactly.
**Lesson worth remembering:** a first fix that removes an obviously
wrong *sign* isn't automatically a *correct* fix - the forecast total
still needed a plausibility check against the recent average before
being trusted, the same instinct that caught the original bug.

**Findings (real numbers, from `marts.fct_orders`, post-fix):**
- Brazil: ~18,893 orders forecast for the next quarter (~6,297/month),
  a healthy, steady trend once the incomplete tail was correctly
  excluded.
- UK: 6,384 forecast for the next quarter - now computed on the full,
  correctly-loaded dataset for the first time in this project.
- US (169), DE (174), GH (155): all modest and roughly flat - a
  reminder these are small synthetic datasets, not a reflection of
  genuine relative regional scale.

**Module 7 status: COMPLETE.**

**Module 8 (Anomaly/Fraud Flagging) — TWO real bugs found and fixed
while building this module.**

**Bug 1: outlier masking.** The first version computed each customer's
mean/std of order value *including* the order being evaluated. This
let a genuine, obvious outlier ($500 against a customer's normal
$48-55 pattern, in a hand-built test case) go undetected (z-score only
1.79) - the outlier inflated its own comparison baseline enough to
mask itself, a well-known statistical trap.
**Fix:** switched to leave-one-out z-scores - each order is compared
against that customer's *other* orders only, computed efficiently via
precomputed per-customer sums (verified the algebraic shortcut matches
a brute-force calculation to within floating-point precision, ~1e-6).
Confirmed the fix against the same test case: z-score correctly jumped
to 150+ and was flagged.

**Bug 2: near-zero-denominator explosion.** Running the fixed logic
against real data produced z-scores in the hundreds of millions -
obviously not real statistics. Root cause: a customer whose other
orders happen to be tightly clustered (e.g. within cents of each
other) has an almost-zero standard deviation - not exactly zero
(already guarded against), but small enough that dividing by it
exploded even a completely ordinary next order into an absurd score.
**Fix:** require a customer's own standard deviation to be at least 5%
of their region's overall standard deviation before trusting it as a
baseline; otherwise fall back to the region-level baseline (the same
fallback already used for customers with too little order history).
Verified against a hand-built test reproducing the exact failure
before redeploying. Max |z-score| dropped from 168 million to a
sane 91.96.

**Findings (real numbers, from `marts.fct_orders`, post-fix, 149,593
orders):**
- Overall flag rate: 2.44% (3,646 orders) at a z-score threshold of 3.
- **A real, interesting split by data source:** the three synthetic
  regions all flag at roughly the same elevated rate - GH 12.40%,
  US 11.89%, DE 11.65% - while the two real regions flag far less
  often - UK 2.51%, BR 1.82%.
- **Root cause, not a bug:** Phase 1's synthetic data generator built
  order values from a *normal* (symmetric bell-curve) distribution.
  Real-world order values are typically right-skewed (many small
  orders, a few large ones), which behaves very differently under
  z-score thresholding than a symmetric distribution does. The
  synthetic regions structurally produce more statistical outliers
  because of how they were generated, not because they contain more
  genuinely anomalous behavior. Documented here as a limitation of the
  Phase 1 methodology surfacing in a later module, rather than
  presented as a real regional difference in fraud risk.
- Top flagged order (z=91.96, Brazil, customer-level baseline):
  plausible as a genuine signal worth human review - a customer with
  an unusually tight, low-value order history followed by one notably
  larger order - exactly the kind of case this module is meant to
  surface, not an artifact to chase further.

**Module 8 status: COMPLETE.**

**Phase 5 status: COMPLETE.** All four modules (Marketing Attribution,
Logistics & Delivery, Demand Forecasting, Anomaly Flagging) built,
tested, run against real data, and debugged where real issues surfaced
- five real bugs found and fixed across this phase alone (ambiguous
date parsing, half-loaded UCI data, negative forecast from an
incomplete data tail, outlier masking, and near-zero-denominator
explosion), each one caught by noticing a result that looked
statistically implausible and refusing to accept it at face value
before investigating.

---

## Dashboard Phase — Reporting Views for Power BI (in progress)

Built a `reporting` schema with pre-aggregated views (revenue by
region, delivery performance, review-by-delivery-bucket, plus
pass-through detail views) so Power BI has clean, purpose-built
sources rather than recomputing everything itself.

**A sixth real bug found and fixed, while verifying these views
against the already-confirmed notebook numbers.** Revenue figures
matched the notebook almost exactly (good sign), but delivery-time
figures didn't: Brazil showed 12.50 days in the SQL view vs. 12.09
days in the notebook, and review-bucket order counts were off by
hundreds per bucket.

**Root cause:** SQL Server's `DATEDIFF(day, start, end)` counts
*calendar-midnight crossings*, not elapsed 24-hour periods - an order
placed at 11:31pm and delivered at 1:00am the next day counts as "1
day" under this function despite only 90 minutes actually elapsing.
This was invisible for the synthetic regions (their timestamps sit
exactly at midnight, `00:00:00`, so boundary-crossing counting and
true-elapsed-time counting happen to agree), but Brazil's real Olist
timestamps have genuine time-of-day components (e.g.
`23:31:27`), exposing the discrepancy.

**Fix:** replaced `DATEDIFF(day, ...)` with
`FLOOR(DATEDIFF(second, ...) / 86400.0)` - computing true elapsed time
in seconds and converting to whole days, matching Python's `.dt.days`
behavior (which measures true elapsed time, not calendar boundaries)
exactly. Applied to both the delivery-performance view and the
review-by-delivery-bucket view, since both were affected by the same
root cause.

**Lesson worth remembering:** this is now the SECOND distinct
date/time bug found in this project (the first was ambiguous format
parsing in Phase 3) - both were invisible when testing against
midnight-aligned synthetic timestamps and only surfaced against real
data with genuine time-of-day components. A general caution: synthetic
test data that's "too clean" (e.g. always exactly midnight) can hide
real bugs that only appear once genuine, messier real-world data is
involved - worth deliberately testing datetime logic against data with
realistic time-of-day variation, not just calendar dates.

**A seventh real issue found and fixed, this time in Power BI rather
than SQL or Python.** Sorting the delivery-bucket chart correctly
(`0-2 days` → `3-5 days` → ... → `20+ days`, not alphabetically) needed
a custom sort key, since Power BI sorts text alphabetically by
default. First attempt: a DAX calculated column (`SortOrder`) derived
FROM `delivery_bucket` via `SWITCH(...)`, then told Power BI to sort
`delivery_bucket` BY that column. This produced a circular dependency
error - `delivery_bucket` depended on `SortOrder` for its sort order,
while `SortOrder`'s own value depended on reading `delivery_bucket`,
a genuine two-node cycle Power BI correctly refused to resolve.
**Fix:** moved the sort key into the SQL view itself, computing
`delivery_bucket` and a new `bucket_sort_order` column as two
*independent* outputs of the same underlying `CASE` logic (both
derived from the raw `delivery_days` value, neither one derived from
the other). Removed the DAX column entirely once the SQL-provided
column was available.
**Lesson worth remembering:** this generalizes beyond Power BI -
derived sort keys and other computed helper columns belong in the data
layer (SQL, in this project) rather than patched on reactively in a
downstream BI/reporting tool, specifically because a helper column
built FROM the same field it's meant to help order can create exactly
this kind of circular reference. Computing both outputs independently,
from a shared upstream source, avoids the issue at the root.

**Dashboard Phase status: COMPLETE.** Built a working Power BI report
page connected live to `MeridianDB`: 5 KPI cards (Total Orders, Total
Revenue, Refund Rate, Total Customers, a correctly weighted Anomaly
Flag Rate built via a proper DAX measure) and 6 charts (Revenue by
Region, Refund Rate by Region, Delivery Time by Region, Review Score
by Delivery Bucket, RFM Segment Counts, Next-Quarter Demand Forecast),
covering every completed analysis module except Marketing Attribution
(deliberately excluded — its own notebook flags the underlying data as
illustrative-only) and Cohort Retention (redundant with RFM's segment
view). Every number on the dashboard was cross-checked against the
already-verified notebook findings and matched. Two real issues were
found and fixed along the way: a naive average vs. a properly weighted
DAX measure for flag rate, and a circular-dependency sort-order bug
(fixed by moving the sort key into the SQL view layer instead of a
DAX-only patch) — both logged above under their own entries.

Separately, the Power BI report was manually redesigned (donut chart
for refund rate, treemap for delivery days, styled blue KPI cards,
peach/blue color theme) — done independently in Power BI Desktop's
GUI, not through this log's tooling.

---

## Documentation Phase — README.md (complete)

Wrote `README.md` as a business case study (problem, approach, key
findings, engineering-rigor bug highlights, limitations, repo
structure), pulling every number directly from this log rather than
re-deriving or re-typing anything from memory. Deliberately excluded
Marketing Attribution's specific figures from the findings section,
matching that module's own documented limitation. Selected 5 of the
project's 11 total real bugs for the README's narrative highlight
reel (the full list of 11 stays here, in this log, for anyone wanting
the complete technical picture).

---

## Streamlit App Phase (in progress)

**Goal:** a live, public, clickable version of the dashboard — the
"highest-leverage differentiator" called out in the original project
brief, since it requires no software install and no database access to
view.

**A real architectural constraint identified before building
anything:** Streamlit Community Cloud is a hosted service with no
network path to a local SQL Server running on a personal laptop. The
app therefore reads from a static CSV snapshot (`export_data_for_streamlit.py`,
run locally where the database is reachable) rather than a live
database connection — a documented design decision, not a shortcut,
and stated plainly in both the app's own footer and `README_STREAMLIT.md`.

**Built and tested before shipping:** `app.py` (Streamlit + Plotly),
using the same warm blue/peach palette and chart types (donut, treemap,
styled KPI cards) as the manually-redesigned Power BI report, at the
user's request, after an explicit discussion of the real tradeoff
(donut/treemap are measurably harder to read precisely than bar
charts — a documented, informed choice, not an accidental one).
Verified by actually launching the app locally (not just reviewing the
code) against realistic test data matching the project's real numbers,
confirming a clean HTTP 200 response with zero errors in the server
log, before removing the test data and shipping the real script.

**A real display bug found and fixed:** the treemap and donut chart
initially displayed raw unrounded values (e.g. `12.094` days, `41.78%`
refund share) instead of clean whole numbers. Fixed using Plotly's
`texttemplate` formatting on both chart types, verified against sample
data before redeploying. The Tracked Revenue KPI card was also fixed
from `$32.0M` to `$32M` to match the whole-number convention used
elsewhere.

**GitHub repository set up:** `github.com/Richardsante1/meridian`,
public. A `.gitignore` was added *before* the first commit, excluding
`venv/` folders (large, environment-specific, reconstructable from
`requirements.txt`) and `data_generation/tier1_raw/` (170MB+ of
publicly-downloadable source data already documented with download
links in `README_PHASE1.md` — no need to duplicate someone else's
public dataset into a portfolio repo). First push required a one-time
Git identity setup (`git config user.email` / `user.name`) that hadn't
been done yet on this machine, and a one-time GitHub authentication
step via Git Credential Manager — both standard, expected first-time
Git setup steps, not errors.

**Two real deployment bugs found while setting up Streamlit Cloud:**

1. **Unnecessary heavy dependencies caused a 20-30 minute hang.** The
   shared `requirements.txt` (originally written for both the local
   export script and the deployed app) listed `pyodbc` and
   `sqlalchemy` — packages `app.py` never actually imports, since the
   whole point of the static-CSV design was to avoid a live database
   connection in the cloud. `pyodbc` needs to compile against system
   ODBC libraries not present in Streamlit Cloud's default Linux
   environment, causing the build to hang. **Fix:** stripped the
   deployed app's `requirements.txt` down to only what `app.py`
   actually imports (`streamlit`, `pandas`, `plotly`) — confirmed via
   `grep` against the actual import statements, not assumption. The
   export script still works locally using packages already installed
   in the Phase 2 venv; no separate requirements file needed for it.
2. **A pinned pandas version had no pre-built package for Streamlit
   Cloud's Python version**, forcing pip to attempt building pandas
   from raw source (`pandas-2.2.2.tar.gz`, not a `.whl` file) — a
   heavier, more failure-prone path that failed outright. **Fix:**
   loosened the version pins (`pandas>=2.2.0` instead of
   `pandas==2.2.2`, similarly for streamlit/plotly) so pip can select
   whichever version already has a ready-made package for the actual
   deployment environment, rather than forcing one exact version that
   didn't.

**A real naming mismatch also surfaced during this process:** the
local folder was actually created as `streamlit`, not `streamlit_app`
as originally instructed — caught via a `git add` failure
(`pathspec did not match any files`) and confirmed with `dir`/`git
status`. Deployment's Main file path in Streamlit Cloud's settings
needs to match this real folder name (`streamlit/app.py`), not the
originally-documented one — being verified as of this log entry.

**Resolved:** the Main file path in Streamlit Cloud's settings was confirmed
correct (`streamlit/app.py`, matching the real folder name). The app deployed
successfully and is live and publicly accessible, rendering all KPI cards and
charts correctly against the real CSV snapshot.

**Status: complete.**

---

## Revenue Anomaly Investigation & Dashboard Transparency (complete)

**Trigger:** the Streamlit (and, by the same underlying data, Power BI)
revenue-by-region visuals showed US, DE, and GH tracked revenue as visually
indistinguishable from zero next to UK and BR.

**Investigation:** ran a diagnostic query against `marts.fct_orders`, grouping
by region, source_system, and currency_code, comparing order_count,
avg_amount_local, avg_amount_usd, and total_usd. This ruled out a currency-
conversion bug immediately — per-order average values were reasonable and
broadly comparable across all five regions ($26-$490 USD). The actual cause
was a volume disparity built into the dataset design itself: UK (uci) has
53,628 orders and BR (olist) has 99,441, versus ~2,000 each for the three
calibrated synthetic regions (US, DE, GH). Summed totals inevitably dwarf the
synthetic regions at that scale gap, independent of any bug in pricing or
currency logic.

**Key decision: disclose, don't disguise.** Considered re-running the
synthetic data generator with a larger order count to visually balance the
charts, but rejected it — re-running the generator risked reopening
already-fixed downstream bugs for a purely cosmetic gain. Honestly flagging a
real data limitation is a stronger portfolio signal than inflating synthetic
volume to make a chart look tidier.

**Fix (Streamlit):** added `avg_order_value_usd` as a one-line derived column
in `app.py` (`tracked_revenue_usd / total_orders`), computed at render time —
no changes needed to `export_data_for_streamlit.py` or any SQL view. Added a
caption under "Tracked Revenue by Region" explaining the real-vs-synthetic
sample size gap, plus a new chart row: "Average Order Value by Region" (a
fair per-order comparison) and "Order Volume by Region (Sample Size)" (makes
the volume gap itself visible and explicit, rather than just implied by the
caption). Verified by running locally (`streamlit run streamlit\app.py`)
before pushing; confirmed rendering correctly on the live Streamlit Cloud
deployment afterward.

**Fix (Power BI):** planned as a follow-up, mirroring the Streamlit
treatment (average order value visual + a text note on sample sizes), to
keep both deliverables' story consistent. Not yet done as of this entry.

**A separate finding while investigating, confirmed as NOT a bug:** UK's
revenue distribution contains a matched pair of extreme values (+$229,852.99
/ -$229,852.99, same customer_id, 12 minutes apart, invoice numbers `581483`
and `C581483`). This is the UCI dataset's own documented cancellation
convention (a leading `C` on the invoice number marks a cancellation of the
preceding order) — a genuine large wholesale order and its own cancellation,
not a data entry error. Verified by pulling the top 20 UK orders by absolute
value; the same paired pattern recurred at multiple value levels, not just
the largest one.

**A second, smaller finding, logged but not yet acted on:** 6 UK records use
an `A`-prefixed order ID (e.g. `A506401`) with `customer_id = NULL` — UCI's
own convention for bank/adjustment entries, not real customer orders.
Combined USD impact: -$201,398.58, under 1% of UK's $26.3M total. Not urgent
given the small impact, but flagged for a future cleanup pass: exclude via
`WHERE order_id NOT LIKE 'A%'` or a proper `is_order` flag set during
staging, rather than filtering ad hoc in the marts layer.

**Status: complete** (Streamlit fix shipped and verified live; Power BI
parity fix and Streamlit Cloud Python version pin both completed as separate
entries below; the A-prefixed cleanup remains the one open item, tracked
above).

---

## Power BI Parity Fix (complete)

**Goal:** bring the Power BI report in line with the transparency fix already
shipped to Streamlit, since Power BI's "Revenue by Region" visual draws on
the same underlying data (`reporting.vw_revenue_by_region`) and shows the
identical real-vs-synthetic volume skew.

**What was built:** a new DAX measure, `Avg Order Value (USD)`, computed as
`DIVIDE(SUM(tracked_revenue_usd), SUM(total_orders), 0)` against the existing
table backing the report — no new SQL view needed, mirroring the
"no pipeline changes required" approach used in Streamlit. Added two new
Clustered Column Chart visuals ("Average Order Value by Region" and "Order
Volume by Region (Sample Size)"), styled with the report's existing peach
palette, plus a text box near the original Revenue by Region visual carrying
the same sample-size disclosure used in the Streamlit caption.

**Verification:** since the report is live-connected (not a CSV snapshot),
new visuals reflected real numbers immediately with no manual refresh
needed. Confirmed against the same SQL diagnostic used for Streamlit: UK
$534, DE $77, US $76, BR $31, GH $26 (the UK figure differs slightly from
the raw SQL query's $490 due to how the live DAX aggregation handles the
underlying rows versus the ad-hoc query — both point to the same conclusion
and neither materially changes the finding).

**Result:** both dashboards (Streamlit and Power BI) now tell the same
honest story about the real-vs-synthetic sample-size gap, using the same
underlying fix (an average-order-value view) rather than two different
patches.

---

## Streamlit Cloud Python Version Pin (complete)

**Issue identified:** Streamlit Cloud's app settings had Python version set
to 3.14 — a very recently released version at the time, with a real risk
that some compiled-dependency packages (pandas, numpy, etc.) might lack
stable pre-built wheels for it yet. This hadn't caused a failure so far, but
was flagged as a latent risk to the live demo, which is one of the more
visible, high-stakes parts of the whole project (a broken public link is
one of few things that can actively hurt a portfolio piece).

**Fix:** changed the Python version setting from 3.14 to 3.12 — a
well-established version with broad package support — via the app's
Settings → General tab. Manually triggered a Reboot app afterward (the
version change did not auto-trigger a rebuild). Confirmed the app rebuilt
successfully and loads correctly under 3.12, with no changes needed to
`requirements.txt` since its version pins were already loosened from the
earlier pandas fix.

**Status: complete.**

---

## A-Prefixed Record Cleanup (complete)

**Issue:** 6 UK records in `staging.stg_uci_orders` used an `A`-prefixed
order ID (e.g. `A506401`) with `customer_id = NULL` — UCI's own convention
for bank/adjustment entries, not real customer orders. Flagged during the
revenue anomaly investigation as a small (<1% of UK revenue) but real data
quality issue worth closing out.

**Fix:** added `WHERE LEFT(Invoice, 1) <> 'A'` to `staging.stg_uci_orders`,
placed after the existing `FROM raw.uci_online_retail_ii` and before
`GROUP BY Invoice, [Customer ID]`. The existing `C`-prefixed cancellation
logic (kept, flagged via `is_refunded`/`order_status`) was left untouched —
only the non-order `A`-prefixed rows are excluded.

**Applied in two places, one lesson learned:** the fix was first applied via
`ALTER VIEW` directly against the live database, and separately by editing
the original `CREATE VIEW` statement in
`sql_server_project/Phase 3/Phase 3 B/06_stg_uci PB.sql` (kept as
`CREATE VIEW`, not `ALTER VIEW`, since that file is used to build the
database from scratch) and pushing to GitHub. Initially assumed pushing the
file update to GitHub was sufficient — it wasn't; editing and committing the
`.sql` script only updates the script on disk, not the actual running view
in SQL Server. The two have to be applied separately: `ALTER VIEW` against
the live database for the immediate fix, and the file update for
reproducibility (so a from-scratch rebuild doesn't reintroduce the bug).

**Verification:** `SELECT COUNT(*) FROM staging.stg_uci_orders WHERE
order_id LIKE 'A%'` returns 0. `marts.fct_orders` UK order count dropped
from 53,628 to 53,622, confirming the fix flowed through automatically with
no manual reload step needed for marts.

**Downstream impact:** Streamlit's CSV snapshot and the live Power BI report
will reflect the corrected (slightly lower) UK order count and revenue on
their next export/refresh — not yet re-run as of this entry, and the
difference is small enough not to be visually noticeable.

**Status: complete.**

---

## Downstream Data Refresh (complete)

**Goal:** propagate the corrected UK order count (53,622, down from 53,628
after the A-Prefixed Record Cleanup above) through to both dashboards, so
Streamlit and Power BI no longer showed stale figures.

**Blocker along the way:** running `export_data_for_streamlit.py` initially
failed with `ModuleNotFoundError: No module named 'sqlalchemy'`. Root cause:
the local Python environment was missing packages the export script needs
(`sqlalchemy`, `pyodbc`) that the *deployed* Streamlit app never touches,
since Streamlit Cloud only ever runs `app.py` directly — `pip install -r
streamlit/requirements.txt` alone wasn't enough because that file was scoped
to what the live app needs, not what this local export script needs. Fixed
by installing the two missing packages directly
(`python -m pip install sqlalchemy pyodbc`).

**Re-export confirmed correct:** `revenue_by_region.csv` regenerated with
UK's `total_orders` at 53,622. `rfm_results.csv` dropped to 103,130 rows
(from 103,136), consistent with excluding the 6 `A`-prefixed records, which
had `customer_id = NULL` and so counted as distinct "customers" before.
`delivery_performance.csv` correctly still shows only 4 regions (BR, US, DE,
GH) — UK has always been excluded here, since the UCI source has no
logistics/delivery tracking (`delivered_date` is `NULL` by design in
`staging.stg_uci_orders`), unrelated to this fix.

**A caching lesson worth keeping:** after pushing the refreshed CSVs, the
live Streamlit dashboard initially still showed the old, uncorrected KPI
figures (159,120 total orders) even though the correct data was already
confirmed present in the pushed CSV. A small git push size (515 bytes for a
100K+ row file) briefly looked like a red flag suggesting the export itself
hadn't worked — but a direct `type` of the local CSV confirmed the export
and the underlying SQL view were both correct all along. The actual cause
was simply that Streamlit Cloud hadn't yet rebuilt from the new commit.
Manually triggering **Reboot app**, plus a hard browser refresh
(Ctrl+Shift+R) to bypass local caching, resolved it — Total Orders then
correctly read 159,114.

**Power BI:** refreshed via Power BI Desktop's Home → Refresh, since the
report is live-connected and does not require a CSV re-export step.

**Status: complete.**

---

## Chart Value Labels & Axis Cleanup (complete)

**Goal:** match Power BI's visual style more closely by showing each bar's
exact value directly on the chart (a "callout"), rather than requiring the
reader to read it off an axis scale.

**What was built:** added a `text=` parameter to all six Plotly bar charts
in `app.py` (Tracked Revenue, Average Order Value, Order Volume, Review
Score by Delivery Time, Customers by RFM Segment, Next-Quarter Forecast),
paired with `fig.update_traces(texttemplate=..., textposition="outside")`
to format and position the label above (or beside, for the horizontal RFM
chart) each bar. Formatting varies by chart: currency values use a `$`
prefix with SI-prefix abbreviation (`$29M`, `$150k`), plain counts use
SI-prefix only (`99K`, `19K`), and review scores use one decimal place.

**Follow-up refinement:** once labels were in place, the axis scale
alongside them became redundant. Hid it via `yaxis=dict(visible=False)` on
the five vertical bar charts, and `xaxis=dict(visible=False)` on the one
horizontal chart (RFM segments) — since that chart's value axis runs
left-to-right, not top-to-bottom, hiding the y-axis there would have hidden
the segment names instead of the count scale.

**Status: complete.**

---

## README Merge Conflict (resolved)

**What happened:** after drafting and pushing a new root `README.md`, a
separate `git push` for an unrelated change (the chart label update) was
rejected with `[rejected] main -> main (fetch first)`. Root cause: GitHub's
own "Add a README" prompt (shown on the repo's home page when no root
README exists) had been clicked at some point, creating a commit directly
on GitHub that the local repo didn't have — a second, independent commit
history diverging from the one being pushed locally.

**Fix:** ran `git pull origin main`, which merged both histories with no
conflicts (Git opened its default commit-message editor, Vim, to confirm
the merge commit — resolved by pressing Esc, typing `:wq`, and pressing
Enter to save and exit). `git push` then succeeded normally.

**Verified:** confirmed the drafted `README.md` (with the architecture
diagram, tech stack tables, and embedded screenshots) was the version that
persisted on GitHub after the merge, not a bare-bones GitHub-generated stub.

**Status: resolved.**

---

## Appendix: Diagnostic & Verification Queries

Reference queries used throughout the revenue anomaly investigation and
cleanup, kept here so any of these checks can be rerun without reconstructing
them from scratch.

### Revenue Anomaly Investigation

Column discovery (used once, to confirm the correct table/column names):
```sql
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'marts' AND TABLE_NAME = 'fct_orders'
ORDER BY ORDINAL_POSITION;
```

Region/source/currency breakdown — the main diagnostic that ruled out a
currency bug and identified the real cause (order volume disparity):
```sql
SELECT 
    region,
    source_system,
    currency_code,
    COUNT(*) AS order_count,
    AVG(amount_local) AS avg_amount_local,
    AVG(amount_usd) AS avg_amount_usd,
    SUM(amount_usd) AS total_usd,
    MIN(amount_usd) AS min_usd,
    MAX(amount_usd) AS max_usd
FROM marts.fct_orders
GROUP BY region, source_system, currency_code
ORDER BY total_usd DESC;
```

UK outlier investigation — confirmed the large +/- value pair as a
legitimate wholesale order + its cancellation:
```sql
SELECT TOP 20 order_id, customer_id, order_date, amount_local, currency_code, 
       amount_usd, is_refunded, order_status
FROM marts.fct_orders
WHERE region = 'UK'
ORDER BY ABS(amount_usd) DESC;
```

### A-Prefixed Record Cleanup

Impact assessment — quantified the A-prefixed records before deciding to
exclude them:
```sql
SELECT 
    COUNT(*) AS record_count,
    SUM(amount_usd) AS total_usd_impact,
    MIN(order_date) AS earliest,
    MAX(order_date) AS latest
FROM marts.fct_orders
WHERE order_id LIKE 'A%' AND region = 'UK';
```

The fix itself — run against the live database (also mirrored in
`sql_server_project/Phase 3/Phase 3 B/06_stg_uci PB.sql` as `CREATE VIEW`,
for from-scratch rebuilds):
```sql
ALTER VIEW staging.stg_uci_orders AS
SELECT 
    Invoice AS order_id,
    CAST([Customer ID] AS NVARCHAR(20)) AS customer_id,
    'UK' AS region,
    'GBP' AS currency_code,
    SUM(Quantity * Price) AS amount_local,
    CAST(NULL AS NVARCHAR(100)) AS product_category,
    MIN(TRY_CONVERT(datetime, InvoiceDate)) AS order_date,
    CAST(NULL AS DATETIME) AS delivered_date,
    CASE WHEN LEFT(Invoice, 1) = 'C' THEN CAST(1 AS BIT) ELSE CAST(0 AS BIT) END AS is_refunded,
    CASE WHEN LEFT(Invoice, 1) = 'C' THEN MIN(TRY_CONVERT(datetime, InvoiceDate)) ELSE NULL END AS refund_date,
    CAST(NULL AS INT) AS review_score,
    CASE WHEN LEFT(Invoice, 1) = 'C' THEN 'cancelled' ELSE 'completed' END AS order_status,
    'uci' AS source_system
FROM raw.uci_online_retail_ii
WHERE LEFT(Invoice, 1) <> 'A'
GROUP BY Invoice, [Customer ID];
```

Post-fix verification — confirms the exclusion held in both staging and
marts:
```sql
SELECT COUNT(*) AS remaining_A_prefixed
FROM staging.stg_uci_orders
WHERE order_id LIKE 'A%';
-- expected: 0

SELECT region, COUNT(*) AS order_count
FROM marts.fct_orders
WHERE region = 'UK'
GROUP BY region;
-- expected: 53,622 (down from 53,628)
```

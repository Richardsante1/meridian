<div align="center">
<img src="assets/latitude_logo.svg" width="440" alt="Latitude Retail Co. logo"/>

# MERIDIAN — Global Commerce Intelligence
*Internal analytics platform, Data & Analytics Engineering*

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Streamlit-FF4B4B)](https://meridian-ed8vjruy3zxytbr4buwv2v.streamlit.app)
[![Build](https://img.shields.io/badge/Pipeline-SQL%20Server%20ELT-2E6FDB)](#architecture)
[![Status](https://img.shields.io/badge/Status-Complete-4CAF50)](./PROJECT_LOG.md)

**[→ View the live dashboard](https://meridian-ed8vjruy3zxytbr4buwv2v.streamlit.app)** · **[→ Full build log](./PROJECT_LOG.md)**

</div>

---

## Table of Contents

- [Business Context](#business-context)
- [Northstar Metrics](#northstar-metrics)
- [Executive Summary](#executive-summary)
- [Insights Deep-Dive](#insights-deep-dive)
- [Dataset Structure](#dataset-structure)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Data Sources](#data-sources)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Dashboards & Sample Insights](#dashboards--sample-insights)
- [Data Transparency & Known Limitations](#data-transparency--known-limitations)

---

## Business Context

**Role:** Data & Analytics Engineer, reporting to the Head of Operations at
**Latitude Retail Co.**

Latitude Retail Co. operates in two established markets — **Brazil** and
the **UK** — with years of transaction history, and has recently expanded
into three newer markets: the **US**, **Germany**, and **Ghana**.
Leadership wants a single, unified view of performance across all five
regions to guide the next phase of expansion.

That request creates a real tension: the newer markets don't yet have
comparable data depth to the established ones, but a dashboard that treats
all five regions as equally mature risks leading leadership to the wrong
conclusion — reading a *data gap* as a *performance failure*.

MERIDIAN — the platform built to answer that brief — combines two
deliberately different data-engineering challenges, rather than treating
synthetic data as a stand-in for something missing:

- **Brazil and the UK** run on real, messy, publicly available transaction
  data. This is where the ELT cleaning, staging logic, and the data-quality
  investigation documented below actually happened.
- **The US, Germany, and Ghana** run on a calibrated synthetic dataset,
  built to demonstrate a second, equally real skill: producing
  production-realistic data for a market that doesn't have transaction
  history yet — a genuine, common need before a new market's data warehouse
  exists.

Both halves are disclosed openly throughout the reporting, rather than
blended into a single undifferentiated total.

At current scale, the dataset spans:

| Metric | Value |
|---|---|
| Total orders | 159,114 |
| Total customers | 103,130 |
| Tracked revenue | ~$32M USD ($31.7M real · $361K synthetic) |
| Regions covered | 5 |
| Time span | 2009–2025 (varies by region) |

## Northstar Metrics

The analysis is organized around five focus areas:

- **Sales trends** — revenue, order volume, and average order value, tracked across regions and normalized to USD
- **Customer segmentation (RFM)** — identifying loyal, at-risk, new, and lost customers to inform retention strategy
- **Logistics performance** — delivery time by region and its relationship to customer review scores
- **Demand forecasting** — projected order volume for the next quarter, by region
- **Anomaly detection** — automated flagging of irregular orders for review


## Executive Summary

<div align="center">
<img src="Analysis/revenue_by_region.png" width="600" alt="Revenue by region"/>
</div>

**Key findings:**

1. **Revenue is concentrated in the two established markets** — the UK and
   Brazil account for the large majority of tracked revenue — but this
   reflects **order volume, not underperformance** in the newer markets.
   Average order value is actually comparable across all five regions
   ($26–$80 USD). See the [Insights Deep-Dive](#insights-deep-dive) below
   for the full investigation.
2. **Refund rates vary meaningfully by region** (1.7%–25.2%), warranting
   region-specific follow-up rather than a single blended target.
3. **Delivery performance correlates with review scores** — orders
   delivered in 0–10 days average a ~4.3 review score; orders taking 20+
   days drop to ~3.1.
4. **Customer segmentation (RFM)** shows Loyal Customers as the largest
   single segment (~33K), with a meaningful At-Risk and Lost population
   worth targeted retention effort.

## Insights Deep-Dive

### Revenue by Region: a sample-size story, not a performance one

**The signal.** Partway through the build, the revenue-by-region chart
showed the US, Germany, and Ghana at close to zero next to Brazil and the
UK — the kind of pattern that, read at face value, would suggest the
expansion into those three markets was failing.

**The investigation.** Rather than take the chart at face value, a
diagnostic query grouped orders by region, source system, and currency,
comparing order count against average and total order value in both local
currency and USD. This immediately ruled out a currency-conversion bug —
average order value was reasonable and broadly comparable across all five
regions ($26–$80 USD). The real driver was order **volume**: the two
established regions had 50,000–99,000 orders each, versus ~2,000 each for
the three newer markets — a scale gap large enough to make the newer
markets disappear next to the established ones on any totals chart,
independent of how each individual order performed.

**A related finding, checked rather than assumed.** The UK data also
contained one striking outlier — a single ~$230,000 order. Rather than
treat it as a data error, the top 20 UK orders by value were pulled
directly; the outlier turned out to be paired with an identical negative
value a few minutes later, under the same customer, matching the source
dataset's own documented cancellation convention. Legitimate, not a bug —
confirmed with data rather than assumed away.

**The fix.** Rather than artificially inflating synthetic order volume to
make the chart "look balanced," the decision was to disclose the gap
directly: an average-order-value view alongside the totals (for a fair
per-region comparison regardless of sample size), plus an explicit note on
the volume difference in both dashboards. A separate, smaller data-quality
issue found during the same investigation — six UK records that were bank
adjustment entries, not real orders — was excluded at the source in the
staging layer.

Full diagnostic queries, SQL fixes, and verification steps are documented
in [`PROJECT_LOG.md`](./PROJECT_LOG.md).

## Dataset Structure

```mermaid
erDiagram
    DIM_CUSTOMERS ||--o{ FCT_ORDERS : places
    FCT_ORDERS {
        string order_id PK
        string customer_id FK
        string region
        string currency_code
        float amount_local
        float amount_usd
        string product_category
        date order_date
        date delivered_date
        bit is_refunded
        date refund_date
        int review_score
        string order_status
        string source_system
    }
```

`fct_orders` is the core fact table all reporting reads from. Full schema
for `dim_customers` and the reporting-layer views is in
[`sql_server_project/Phase 3/`](./sql_server_project/Phase%203/).

## Architecture

```mermaid
flowchart LR
    subgraph Sources
        A1[Olist - Brazil<br/>Kaggle]
        A2[UCI Online Retail II<br/>UK]
        A3[Synthetic Generator<br/>US · Germany · Ghana]
        A4[Live FX Rates]
    end

    subgraph SQL Server
        B[raw schema] --> C[staging schema<br/>cleaning & parsing]
        C --> D[marts schema<br/>fact & dim tables]
    end

    A1 --> B
    A2 --> B
    A3 --> B
    A4 --> D

    D --> E[Power BI<br/>live connection]
    D --> F[export_data_for_streamlit.py]
    F --> G[Streamlit Cloud<br/>CSV snapshot]
```

Power BI connects live to the marts layer. Streamlit Cloud has no network path to a local SQL Server instance, so it reads from a versioned CSV snapshot instead — a deliberate design decision, not a shortcut (see [`streamlit/README_STREAMLIT.md`](./streamlit/README_STREAMLIT.md)).

## Tech Stack

| Layer | Tools |
|---|---|
| Data sourcing | Kaggle (Olist), UCI Machine Learning Repository, Python (synthetic generation) |
| Database | Microsoft SQL Server, SSMS |
| Pipeline / ELT | T-SQL views, Python (pandas, pyodbc, SQLAlchemy) |
| Analysis | Jupyter, pandas, RFM/cohort/forecasting notebooks |
| Dashboards | Power BI (live), Streamlit + Plotly (public deployment) |
| Deployment | Streamlit Community Cloud, GitHub |

## Data Sources

| Region | Source | Type | Order Volume |
|---|---|---|---|
| 🇧🇷 Brazil | Olist Brazilian E-Commerce (Kaggle) | Real | ~99,000 |
| 🇬🇧 UK | UCI Online Retail II | Real | ~53,600 |
| 🇺🇸 US | Calibrated synthetic generator | Synthetic | ~2,000 |
| 🇩🇪 Germany | Calibrated synthetic generator | Synthetic | ~2,000 |
| 🇬🇭 Ghana | Calibrated synthetic generator | Synthetic | ~2,000 |

The order-volume gap between real and synthetic regions is intentional and disclosed directly in both dashboards — see [Data Transparency](#data-transparency--known-limitations) below.

## Repository Structure

```
meridian/
├── assets/                    # Logo and README images
├── data_generation/          # Synthetic data generator, FX rate fetcher
├── sql_server_project/
│   ├── Phase 3/               # raw → staging → marts SQL
│   └── Dashboard/             # Power BI-facing reporting views
├── Analysis/                  # Jupyter notebooks (7 phases of analysis)
├── streamlit/
│   ├── app.py                 # Live dashboard
│   ├── export_data_for_streamlit.py
│   └── data/                  # CSV snapshots powering the live app
└── PROJECT_LOG.md             # Full build history, bugs, and fixes
```

## Getting Started

To run this locally, you'll need SQL Server and Python installed.

```bash
git clone https://github.com/Richardsante1/meridian.git
cd meridian
```

1. Run the SQL scripts in `sql_server_project/` in order (`01_create_database.sql` through the Phase 3 subfolders) to build the raw → staging → marts pipeline
2. Run `data_generation/generate_synthetic_data.py` to produce the US, Germany, and Ghana datasets, and `fetch_exchange_rates.py` for current FX rates
3. Load the raw data with `sql_server_project/03_load_raw_data.py`
4. Explore the analysis notebooks in `Analysis/`
5. To run the dashboard locally:
   ```bash
   pip install -r streamlit/requirements.txt
   python -m streamlit run streamlit/app.py
   ```

## Dashboards & Sample Insights

<table>
<tr>
<td><img src="Analysis/revenue_by_region.png" width="400"/></td>
<td><img src="Analysis/rfm_segment_sizes.png" width="400"/></td>
</tr>
<tr>
<td><img src="Analysis/delivery_time_by_region.png" width="400"/></td>
<td><img src="Analysis/cohort_retention_heatmap.png" width="400"/></td>
</tr>
</table>

More visuals — demand forecasting, refund rates, marketing attribution, and anomaly flagging — are available in `Analysis/` and in the [live dashboard](https://meridian-ed8vjruy3zxytbr4buwv2v.streamlit.app).

## Data Transparency & Known Limitations

This project treats honest disclosure as part of the deliverable, not an afterthought:

- **Real vs. synthetic sample sizes differ substantially** (see table above). Both dashboards surface this directly, and average-order-value visuals are provided alongside raw totals so regions can be compared fairly regardless of volume.
- **Marketing attribution data is illustrative only** — it's built and functional, but its underlying spend figures have no real-world grounding, so it's intentionally excluded from the main dashboards.
- **Every bug found during the build — and how it was diagnosed and fixed — is documented in [`PROJECT_LOG.md`](./PROJECT_LOG.md)**, including a full diagnostic query appendix for anyone who wants to reproduce the checks themselves.

---

<div align="center">

Built by [Richard Asante](https://github.com/Richardsante1) as a portfolio data engineering project.

</div>

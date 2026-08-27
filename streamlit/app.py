"""
MERIDIAN - Streamlit App
==========================
Reads from static CSV exports (see export_data_for_streamlit.py) rather
than a live database connection - Streamlit Community Cloud has no
network path to a local SQL Server. This is a documented design
decision, not a shortcut: the underlying numbers are the same
verified, bug-fixed results from the notebooks and Power BI dashboard,
just snapshotted rather than queried live.

Run locally:
    streamlit run app.py
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

st.set_page_config(page_title="MERIDIAN — Global Commerce Intelligence", layout="wide")

# Custom styling to match the polished Power BI look: rounded, colored
# KPI cards with bold white text, rather than Streamlit's plain default
# metric styling.
st.markdown("""
<style>
.kpi-card {
    background-color: #2E6FDB;
    border-radius: 10px;
    padding: 18px 10px;
    text-align: center;
    color: white;
}
.kpi-label { font-size: 14px; opacity: 0.9; margin-bottom: 4px; }
.kpi-value { font-size: 28px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# Warm palette matching the Power BI redesign: primary blue + peach/
# orange/light-blue accents, used for the donut and treemap. Bar charts
# use a single warm peach tone, consistent with the reference dashboard.
WARM_CATEGORICAL = ["#2E6FDB", "#E8785A", "#A9D4F0", "#F4C7A8", "#1B4A8C"]
PEACH = "#F4C7A8"
TREEMAP_SCALE = ["#A9D4F0", "#2E6FDB", "#E8785A"]

REAL_REGIONS = {"BR", "UK"}  # regions built on genuine public datasets, vs. calibrated synthetic ones


@st.cache_data
def load_data():
    files = [
        "revenue_by_region", "delivery_performance", "review_by_delivery_bucket",
        "rfm_results", "demand_forecast_summary", "demand_forecast_monthly",
        "anomaly_summary_by_region", "anomaly_flagged_orders",
    ]
    data = {}
    for name in files:
        path = os.path.join(DATA_DIR, f"{name}.csv")
        data[name] = pd.read_csv(path)
    return data


data = load_data()

st.title("MERIDIAN — Global Commerce Intelligence")
st.caption(
    "A unified, currency-normalized view across five regions — two built on real public "
    "datasets (Brazil, UK), three on calibrated synthetic data (US, Germany, Ghana)."
)

all_regions = sorted(data["revenue_by_region"]["region"].unique())
selected_regions = st.multiselect("Filter by region", all_regions, default=all_regions)

rev = data["revenue_by_region"][data["revenue_by_region"]["region"].isin(selected_regions)]
rev = rev.assign(avg_order_value_usd=rev["tracked_revenue_usd"] / rev["total_orders"])
rfm = data["rfm_results"][data["rfm_results"]["region"].isin(selected_regions)]
anomaly = data["anomaly_summary_by_region"][data["anomaly_summary_by_region"]["region"].isin(selected_regions)]

# ----------------------------------------------------------------------
# KPI row
# ----------------------------------------------------------------------
total_revenue = rev["tracked_revenue_usd"].sum()
total_orders = rev["total_orders"].sum()
weighted_refund_rate = (rev["revenue_lost_to_refunds_usd"].sum() / total_revenue) if total_revenue else 0
total_customers = len(rfm)
weighted_flag_rate = (anomaly["flagged_count"].sum() / anomaly["total_orders"].sum()) if anomaly["total_orders"].sum() else 0

kpis = [
    ("Total Orders", f"{total_orders:,.0f}"),
    ("Tracked Revenue", f"${total_revenue/1e6:,.0f}M"),
    ("Refund Rate", f"{weighted_refund_rate:.1%}"),
    ("Total Customers", f"{total_customers:,}"),
    ("Orders Flagged", f"{weighted_flag_rate:.1%}"),
]
cols = st.columns(5)
for col, (label, value) in zip(cols, kpis):
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.divider()

region_colors = {r: PEACH for r in all_regions}

# ----------------------------------------------------------------------
# Row 1: revenue, refund rate, delivery
# ----------------------------------------------------------------------
c1, c2, c3 = st.columns(3)

# ----------------------------------------------------------------------
# Row 1: revenue, refund rate, delivery
# ----------------------------------------------------------------------
c1, c2, c3 = st.columns(3)

with c1:
    fig = px.bar(rev.sort_values("tracked_revenue_usd", ascending=False),
                 x="region", y="tracked_revenue_usd", title="Tracked Revenue by Region",
                 color_discrete_sequence=[PEACH])
    fig.update_layout(showlegend=False, yaxis_title="USD")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("BR and UK reflect full historical order volume (50K–99K orders each); "
               "US, DE, and GH are calibrated synthetic samples (~2K orders each) — "
               "totals aren't directly comparable across the two groups. See average "
               "order value below for a fair per-order comparison.")

c1b, c2b = st.columns(2)

with c1b:
    fig = px.bar(rev.sort_values("avg_order_value_usd", ascending=False),
                 x="region", y="avg_order_value_usd", title="Average Order Value by Region",
                 color_discrete_sequence=[PEACH])
    fig.update_layout(showlegend=False, yaxis_title="USD")
    st.plotly_chart(fig, use_container_width=True)

with c2b:
    fig = px.bar(rev.sort_values("total_orders", ascending=False),
                 x="region", y="total_orders", title="Order Volume by Region (Sample Size)",
                 color_discrete_sequence=[PEACH])
    fig.update_layout(showlegend=False, yaxis_title="Orders")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

with c2:    # Donut chart, matching the Power BI redesign - trades some precision
    # for visual variety on the KPI-adjacent row; the underlying values
    # are unchanged from the bar-chart version.
    fig = px.pie(rev.sort_values("refund_rate", ascending=False),
                 values="refund_rate", names="region", hole=0.55,
                 title="Refund Rate by Region", color_discrete_sequence=WARM_CATEGORICAL)
    fig.update_traces(texttemplate="%{label}: %{percent:.0%}")
    st.plotly_chart(fig, use_container_width=True)

with c3:
    delivery = data["delivery_performance"][data["delivery_performance"]["region"].isin(selected_regions)]
    fig = px.treemap(delivery, path=["region"], values="mean_delivery_days",
                      color="mean_delivery_days", color_continuous_scale=TREEMAP_SCALE,
                      title="Mean Delivery Days by Region")
    fig.update_traces(texttemplate="%{label}<br>%{value:.0f}")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------
# Row 2: review by delivery bucket, RFM segments, forecast
# ----------------------------------------------------------------------
c4, c5, c6 = st.columns(3)

with c4:
    bucket = data["review_by_delivery_bucket"].sort_values("bucket_sort_order")
    fig = px.bar(bucket, x="delivery_bucket", y="avg_review_score",
                 title="Review Score by Delivery Time", range_y=[1, 5],
                 color_discrete_sequence=[PEACH])
    st.plotly_chart(fig, use_container_width=True)

with c5:
    seg_counts = rfm["segment"].value_counts().reset_index()
    seg_counts.columns = ["segment", "count"]
    fig = px.bar(seg_counts.sort_values("count"), x="count", y="segment", orientation="h",
                 title="Customers by RFM Segment", color_discrete_sequence=[PEACH])
    st.plotly_chart(fig, use_container_width=True)

with c6:
    forecast = data["demand_forecast_summary"][data["demand_forecast_summary"]["region"].isin(selected_regions)]
    fig = px.bar(forecast.sort_values("next_3_months_total", ascending=False),
                 x="region", y="next_3_months_total", title="Next-Quarter Forecast by Region",
                 color_discrete_sequence=[PEACH])
    fig.update_layout(yaxis_title="orders")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(
    "Real data: Brazil (Olist, 2016-2018), UK (UCI Online Retail II, 2009-2011). "
    "Synthetic, calibrated data: US, Germany, Ghana (2023-2025). "
    "Marketing attribution is built but intentionally excluded here - its underlying "
    "spend data is illustrative only, with no real-world grounding. "
    "Full methodology, limitations, and every bug found along the way: see PROJECT_LOG.md."
)

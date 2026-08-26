"""
MERIDIAN - Streamlit App - Data Export
=========================================
Streamlit Community Cloud has no network path to your local SQL Server
(it runs on your laptop, not on the internet). So the deployed app
reads from static CSV files instead of a live database connection -
a one-time snapshot of your actual, verified results.

This script pulls that snapshot. Run it locally (where SQL Server is
reachable), then the resulting CSVs get bundled into the Streamlit app
folder and pushed to GitHub with it.

Run:
    python export_data_for_streamlit.py
"""

import os
import pandas as pd
from sqlalchemy import create_engine
import pyodbc

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "data")


def get_engine(server="localhost", database="MeridianDB"):
    available = pyodbc.drivers()
    preferred_order = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]
    driver = next((d for d in preferred_order if d in available), None)
    if driver is None:
        raise RuntimeError("No SQL Server ODBC driver found. Install 'ODBC Driver 17 for SQL Server'.")
    conn_str = f"mssql+pyodbc://@{server}/{database}?driver={driver.replace(' ', '+')}&trusted_connection=yes"
    return create_engine(conn_str)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    engine = get_engine()

    exports = {
        "revenue_by_region.csv": "SELECT * FROM reporting.vw_revenue_by_region",
        "delivery_performance.csv": "SELECT * FROM reporting.vw_delivery_performance",
        "review_by_delivery_bucket.csv": "SELECT * FROM reporting.vw_review_by_delivery_bucket ORDER BY bucket_sort_order",
        "rfm_results.csv": "SELECT * FROM reporting.rfm_results",
        "demand_forecast_summary.csv": "SELECT * FROM reporting.demand_forecast_summary",
        "demand_forecast_monthly.csv": "SELECT * FROM reporting.demand_forecast_monthly",
        "anomaly_summary_by_region.csv": "SELECT * FROM reporting.anomaly_summary_by_region",
        "anomaly_flagged_orders.csv": "SELECT * FROM reporting.anomaly_flagged_orders",
    }

    for filename, query in exports.items():
        df = pd.read_sql(query, engine)
        path = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(path, index=False)
        print(f"  {filename}: {len(df):,} rows")

    print(f"\nDone. All exports saved to {OUTPUT_DIR}")
    print("Next: run the Streamlit app locally to test it, then push everything to GitHub.")


if __name__ == "__main__":
    main()

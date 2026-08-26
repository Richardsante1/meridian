"""
MERIDIAN - Phase 2 - Load raw data into SQL Server
=====================================================
Reads every file from data_generation/output/ (your synthetic US/DE/GH
data + fx_rates) and data_generation/tier1_raw/ (real Olist + UCI data),
and loads each one into its own table in the [raw] schema of MeridianDB.

Table structure is auto-created from each file's own columns (pandas
infers the types). We do NOT clean or rename anything here on purpose -
this is the raw landing zone. Cleaning/typing/renaming happens in
Phase 3's staging layer.

BEFORE RUNNING:
1. You must have already run 01_create_database.sql and
   02_create_raw_schema.sql in SSMS.
2. You need a SQL Server ODBC driver installed (usually already present
   if SQL Server itself is installed). If this script errors out saying
   no driver was found, install "ODBC Driver 17 for SQL Server" or
   "ODBC Driver 18 for SQL Server" from Microsoft's download page.
3. If your SQL Server is a NAMED INSTANCE (e.g. "localhost\\SQLEXPRESS"
   instead of just a default local instance), change the SERVER variable
   below to match. You can see your server name in SSMS's connection
   dialog / top-left of SSMS after connecting.

Run:
    python 03_load_raw_data.py
"""

import os
import glob

import pandas as pd
from sqlalchemy import create_engine

# ----------------------------------------------------------------------
# CONFIG - edit these two if your setup differs from the default
# ----------------------------------------------------------------------
SERVER = "localhost"        # e.g. r"localhost\SQLEXPRESS" if using a named instance
DATABASE = "MeridianDB"
SCHEMA = "raw"
CHUNKSIZE = 20000            # rows per batch, keeps memory use low on big files

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_GEN_DIR = os.path.normpath(os.path.join(HERE, "..", "data_generation"))
OUTPUT_DIR = os.path.join(DATA_GEN_DIR, "output")
TIER1_DIR = os.path.join(DATA_GEN_DIR, "tier1_raw")
OLIST_DIR = os.path.join(TIER1_DIR, "olist")


def pick_odbc_driver():
    import pyodbc
    available = pyodbc.drivers()
    print(f"ODBC drivers detected on this machine: {available}")

    # Explicit preference order, newest/most capable first. The legacy
    # "SQL Server" driver (bundled with Windows by default) has known
    # problems with certain data types pandas creates automatically -
    # it threw "Invalid precision value (0)" on a float column with all
    # nulls. Naive alphabetical sorting picks "SQL Server" over "ODBC
    # Driver 17 for SQL Server" by coincidence of spelling, which is the
    # bug that caused that error - fixed by listing preferences explicitly
    # instead of sorting.
    preferred_order = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",  # legacy fallback - last resort only
    ]
    for name in preferred_order:
        if name in available:
            return name

    # last resort: any driver with "SQL Server" in the name at all
    candidates = [d for d in available if "SQL Server" in d]
    if candidates:
        return candidates[0]

    raise RuntimeError(
        "No SQL Server ODBC driver found on this machine.\n"
        "Install 'ODBC Driver 17 for SQL Server' (or 18) from Microsoft's "
        "download page, then re-run this script."
    )


def get_engine():
    driver = pick_odbc_driver()
    print(f"Using ODBC driver: {driver}")
    conn_str = (
        f"mssql+pyodbc://@{SERVER}/{DATABASE}"
        f"?driver={driver.replace(' ', '+')}&trusted_connection=yes"
    )
    return create_engine(conn_str, fast_executemany=True)


def load_csv_to_table(engine, csv_path, table_name, **read_kwargs):
    print(f"\nLoading {os.path.basename(csv_path)} -> {SCHEMA}.{table_name}")
    total_rows = 0
    first_chunk = True
    for chunk in pd.read_csv(csv_path, chunksize=CHUNKSIZE, **read_kwargs):
        chunk.to_sql(
            table_name, engine, schema=SCHEMA,
            if_exists="replace" if first_chunk else "append",
            index=False,
        )
        total_rows += len(chunk)
        first_chunk = False
    print(f"  loaded {total_rows} rows")
    return total_rows


def load_excel_to_table(engine, xlsx_path, table_name):
    print(f"\nLoading {os.path.basename(xlsx_path)} -> {SCHEMA}.{table_name}")
    # Real multi-year datasets (like UCI Online Retail II) are often
    # split across multiple sheets, one per year - reading only
    # sheet_name=0 silently drops every sheet after the first. Reading
    # ALL sheets and combining them avoids this.
    all_sheets = pd.read_excel(xlsx_path, sheet_name=None)
    if len(all_sheets) > 1:
        print(f"  found {len(all_sheets)} sheets: {list(all_sheets.keys())} - combining all of them")
    df = pd.concat(all_sheets.values(), ignore_index=True)
    df.to_sql(table_name, engine, schema=SCHEMA, if_exists="replace", index=False)
    print(f"  loaded {len(df)} rows")
    return len(df)


def main():
    engine = get_engine()
    summary = {}

    # --- Tier 2: your synthetic US/DE/GH data + fx_rates ---
    for csv_path in sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.csv"))):
        table_name = os.path.splitext(os.path.basename(csv_path))[0]
        summary[table_name] = load_csv_to_table(engine, csv_path, table_name, encoding="utf-8")

    # --- Tier 1: real Olist (Brazil) data ---
    for csv_path in sorted(glob.glob(os.path.join(OLIST_DIR, "*.csv"))):
        table_name = os.path.splitext(os.path.basename(csv_path))[0]
        summary[table_name] = load_csv_to_table(engine, csv_path, table_name, encoding="utf-8")

    # --- Tier 1: real UCI Online Retail II (UK) data - xlsx or csv ---
    uci_xlsx = os.path.join(TIER1_DIR, "online_retail_II.xlsx")
    uci_csv = os.path.join(TIER1_DIR, "online_retail_II.csv")
    if os.path.exists(uci_xlsx):
        summary["uci_online_retail_ii"] = load_excel_to_table(engine, uci_xlsx, "uci_online_retail_ii")
    elif os.path.exists(uci_csv):
        summary["uci_online_retail_ii"] = load_csv_to_table(engine, uci_csv, "uci_online_retail_ii", encoding="latin1")
    else:
        print("WARNING: no UCI Online Retail II file found - skipping.")

    print("\n=== Load summary ===")
    for table, rows in summary.items():
        print(f"  raw.{table}: {rows} rows")
    print(f"\nDone. {len(summary)} tables loaded into {DATABASE}.{SCHEMA}.")


if __name__ == "__main__":
    main()

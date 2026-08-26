# MERIDIAN — Phase 2: SQL Server Setup & Raw Data Load

Goal: get every CSV/xlsx file from Phase 1 sitting inside a real SQL
Server database, in a "raw" schema, exactly as-is (no cleaning yet).

## Step 1 — Create the project folder on your machine

In File Explorer, go to `Documents\Meridian` (the same folder that
already contains `data_generation`). Create a new folder here called
`sql_server_project`. Drag the 5 files from this chat
(`01_create_database.sql`, `02_create_raw_schema.sql`,
`03_load_raw_data.py`, `requirements_phase2.txt`, this README) into it.

You should now have:
```
Documents\Meridian\
  data_generation\   <- from Phase 1
  sql_server_project\   <- new, Phase 2
```

## Step 2 — Confirm your SQL Server connection details

Open **SSMS**. In the "Connect to Server" dialog:
- **Server name**: note exactly what's shown/typed here (often just a
  dot `.`, `localhost`, or your PC name — sometimes with `\SQLEXPRESS`
  after it if it's a named instance).
- **Authentication**: note if it says "Windows Authentication" (most
  common for local dev) or "SQL Server Authentication".

Click **Connect**. You should see your server appear in the left-hand
"Object Explorer" panel.

**If your server name is anything other than plain `localhost`**, keep
that noted — you'll need to edit one line in the Python script later.

## Step 3 — Create the database

1. In SSMS, click **"New Query"** (top-left toolbar button).
2. Open `01_create_database.sql` (from your `sql_server_project` folder)
   in a text editor, copy all its contents, and paste into the SSMS
   query window.
3. Click **Execute** (or press `F5`).
4. You should see `Commands completed successfully` and a message
   `MeridianDB created.` in the "Messages" tab at the bottom.

## Step 4 — Create the raw schema

1. Still in SSMS: at the top toolbar there's a database dropdown — make
   sure it now says **MeridianDB** (not "master"). If it still says
   master, select MeridianDB from that dropdown, or just make sure the
   query below starts with `USE MeridianDB;` (it does).
2. Open a **new query window** (or clear the current one).
3. Copy the contents of `02_create_raw_schema.sql`, paste, and Execute.
4. You should see `Schema [raw] created.`

## Step 5 — Set up Python for this phase

You already built a virtual environment in Phase 1 — we'll reuse it
rather than making a new one.

Open File Explorer, navigate into `sql_server_project`, click the
address bar, type `cmd`, hit Enter (same trick as Phase 1).

Then run:
```
..\data_generation\venv\Scripts\activate
```
Your prompt should show `(venv)` again.

```
pip install -r requirements_phase2.txt
```
This adds `pyodbc` (talks to SQL Server) and `openpyxl` (reads Excel
files) to your existing environment.

## Step 6 — Edit the server name if needed

Open `03_load_raw_data.py` in Notepad (or any text editor). Near the
top you'll see:
```python
SERVER = "localhost"
```
If your SSMS connection in Step 2 used something other than
`localhost` (e.g. `.` or `YOURPC\SQLEXPRESS`), change this line to
match exactly. Save the file.

## Step 7 — Run the loader

Back in your `(venv)` terminal:
```
python 03_load_raw_data.py
```

**What success looks like:** a line for every file it finds, e.g.:
```
Using ODBC driver: ODBC Driver 17 for SQL Server

Loading gh_orders.csv -> raw.gh_orders
  loaded 2016 rows

Loading olist_orders_dataset.csv -> raw.olist_orders_dataset
  loaded 99441 rows
...
=== Load summary ===
  raw.gh_orders: 2016 rows
  ...
Done. 16 tables loaded into MeridianDB.raw.
```

**If you see an error about no ODBC driver found:** download and
install "ODBC Driver 17 for SQL Server" from Microsoft's site, then
re-run.

**If you see a connection/login error:** double-check the `SERVER`
value from Step 6 matches your SSMS connection exactly.

## Step 8 — Verify in SSMS

Back in SSMS, in Object Explorer, expand:
`MeridianDB` → `Tables` (you may need to right-click MeridianDB →
Refresh first, or expand `raw.` prefixed tables under Tables).

Run this in a new query window to see everything that loaded, with row
counts:
```sql
USE MeridianDB;
SELECT
    t.name AS table_name,
    SUM(p.rows) AS row_count
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE s.name = 'raw' AND p.index_id IN (0,1)
GROUP BY t.name
ORDER BY t.name;
```

You should see one row per table, matching the row counts the Python
script printed.

---

Once you see that list, Phase 2 is done — real, messy, multi-region
data now lives in SQL Server. Tell me what the query above shows (a
screenshot is perfect) and we'll move to **Phase 3**: writing the T-SQL
that cleans this mess into one unified, analysis-ready model.

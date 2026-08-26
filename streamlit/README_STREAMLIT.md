# MERIDIAN — Streamlit App

A live, interactive version of the dashboard, viewable by anyone with a
browser - no Power BI, no database connection, no download required.

## Why this reads from CSV files, not a live database

Streamlit Community Cloud (the free hosting service) has no network
path to a database running on your own laptop. This app reads from
static CSV exports instead — a one-time snapshot of your real,
verified results. This is a documented design decision, not a
shortcut around the real work: the numbers come straight from the same
SQL views and notebooks already built and checked in this project.

## Step 1 — Export your real data

1. Copy `export_data_for_streamlit.py` into your
   `Documents\Meridian\streamlit_app\` folder (create this folder if
   it doesn't exist yet, as a sibling to `data_generation`,
   `sql_server_project`, and `analysis`).
2. Open a terminal there, reuse your existing venv:
   ```
   ..\data_generation\venv\Scripts\activate
   ```
3. Run it:
   ```
   python export_data_for_streamlit.py
   ```
   This creates 8 CSV files inside a new `data/` subfolder — your real,
   current numbers, ready for the app to read.

## Step 2 — Test the app locally

1. Copy `app.py` and `requirements.txt` into the same `streamlit_app`
   folder.
2. Install the app's packages:
   ```
   pip install -r requirements.txt
   ```
3. Run it:
   ```
   streamlit run app.py
   ```
   Your browser should open automatically to `localhost:8501`, showing
   the live dashboard built from your real exported data. Try the
   region filter at the top — this is genuinely interactive, something
   a static Power BI screenshot can't offer.

**Check this before moving on:** do the numbers on this page match
what you already know from your notebooks and Power BI dashboard? If
something looks off, it's worth checking the export step before
deploying anything publicly.

## Step 3 — Push to GitHub

Your `streamlit_app` folder (including the `data/` folder with your
real CSVs — these are just aggregated summary numbers, not sensitive,
so it's fine to commit them) needs to be in a GitHub repository before
Streamlit Community Cloud can deploy it.

## Step 4 — Deploy for free

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in
   with your GitHub account.
2. Click **"New app"**.
3. Select your repository, and point it at `streamlit_app/app.py` as
   the main file.
4. Click **Deploy**.

Streamlit will build and host it — you'll get a public URL like
`your-app-name.streamlit.app`, live in a minute or two.

## Step 5 — Add the link back to your README

Once deployed, replace the placeholder link at the top of your main
`README.md` with the real, live Streamlit URL.

---

**Note on keeping it updated:** since this reads from a static
snapshot, it won't automatically reflect new database changes. If you
make further fixes to the pipeline later, re-run the export script and
push the updated CSVs to GitHub — Streamlit Cloud will pick up the
change automatically.

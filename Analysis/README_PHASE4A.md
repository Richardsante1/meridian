# MERIDIAN — Phase 4, Part A: Revenue Reporting Notebook

## Step 1 — Create the folder and add the files

In `Documents\Meridian`, create a new folder called `analysis`. Drag in
`01_revenue_reporting.ipynb` and `requirements_phase4.txt`.

```
Documents\Meridian\
  data_generation\
  sql_server_project\
  analysis\        <- new
```

## Step 2 — Install Jupyter and the analysis packages

Open a terminal inside the `analysis` folder (same address-bar trick as
before: click the address bar, type `cmd`, Enter).

Reuse your existing venv:
```
..\data_generation\venv\Scripts\activate
pip install -r requirements_phase4.txt
```

## Step 3 — Launch Jupyter

Still in that terminal:
```
jupyter notebook
```

This opens a browser tab showing your `analysis` folder. **What you're
looking at:** this isn't a website — Jupyter started a small local
server on your own machine, and your browser is just displaying it.
Nothing leaves your computer.

Click on `01_revenue_reporting.ipynb` to open it.

## Step 4 — Run the notebook, one cell at a time

Click on the first code cell (the grey box, not the text above it),
then press **Shift + Enter**. This runs that cell and moves to the
next one. Keep pressing **Shift + Enter** to work through the notebook
top to bottom.

**What to expect at each step:**
- After the connection cell: `Connected.`
- After the data-loading cell: a row count, then a preview table of
  the first few orders.
- After the revenue summary cell: a table with 5 rows (one per
  region), showing tracked revenue, realized revenue, refund rate, and
  revenue lost to refunds.
- After the two chart cells: an actual bar chart appears right there
  in the notebook.

## Step 5 — Write down what you found

The last markdown cell in the notebook has a blank spot asking you to
summarize your findings in your own words, once you've seen the real
numbers. Fill that in directly in the notebook — it's meant to be
edited, that's the whole point of notebooks mixing writing and code.

---

Send me a screenshot of the revenue summary table and the two charts
once you've run through it — then we'll build the next notebook:
cohort retention analysis.

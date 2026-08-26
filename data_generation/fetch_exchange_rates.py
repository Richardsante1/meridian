"""
MERIDIAN - Phase 1 - Tier 3 Reference Data: FX Rates
======================================================
Fetches real exchange rates for BRL, GBP, EUR, GHS against USD.

WHY THIS API (documented decision):
The original brief suggested Frankfurter or exchangerate.host.
- Frankfurter is ECB-based and does NOT carry GHS (Ghanaian Cedi is not
  in the ECB reference basket) - a dealbreaker once Nigeria was swapped
  for Ghana.
- exchangerate.host now requires a paid API key (as of 2023+), breaking
  the project's "everything free" requirement.
Instead this uses open.er-api.com - free, no signup, no API key, and it
does carry GHS. This kind of "I picked X, here's exactly why" note is
worth keeping verbatim in the README's tech-decisions section.

NOTE: this script needs real internet access and won't run inside a
sandboxed environment with restricted network egress - run it on your
own machine.

Run:
    python fetch_exchange_rates.py
"""

import os
import csv
from datetime import datetime, timedelta

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fx_rates.csv")

CURRENCIES = ["BRL", "GBP", "EUR", "GHS", "USD"]

# open.er-api.com only serves *current* daily rates on its free tier
# (no historical time series without a key). For a portfolio project
# that's a fine, documented limitation: we snapshot today's rate and
# note in DATA_DICTIONARY.md that historical FX movement isn't modeled -
# this is exactly the kind of "what this doesn't tell you" caveat the
# README needs.
API_URL = "https://open.er-api.com/v6/latest/USD"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Fetching rates from {API_URL} ...")
    resp = requests.get(API_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("result") != "success":
        raise RuntimeError(f"API did not return success: {data}")

    rates = data["rates"]
    fetched_date = data.get("time_last_update_utc", datetime.utcnow().isoformat())

    rows = []
    for code in CURRENCIES:
        if code not in rates:
            print(f"  WARNING: {code} not found in API response - skipping.")
            continue
        rows.append({
            "currency_code": code,
            "usd_to_currency_rate": rates[code],
            "fetched_at_utc": fetched_date,
        })

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["currency_code", "usd_to_currency_rate", "fetched_at_utc"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} currency rates to {OUTPUT_FILE}")
    for r in rows:
        print(f"  1 USD = {r['usd_to_currency_rate']} {r['currency_code']}")


if __name__ == "__main__":
    main()

"""
MERIDIAN - Phase 5 - Marketing Channel Data Generator
========================================================
Generates two new synthetic datasets needed for Module 5 (marketing
attribution), which didn't exist from Phase 1:

1. order_channel_attribution.csv - which marketing channel gets credit
   for each order (last-touch: whichever channel the customer's final
   click came from before ordering).
2. channel_spend.csv - daily ad spend per region per channel.

LIMITATION, stated upfront: this only covers the three synthetic
regions (US, DE, GH). No real e-commerce dataset publicly tracks which
ad channel drove which order - Olist and UCI have no equivalent data at
all, so Module 5's attribution analysis will necessarily be limited to
synthetic regions only. This is documented here rather than silently
assumed.

Run:
    python generate_marketing_data.py
"""

import os
import random
import numpy as np
import pandas as pd

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "output")

CHANNELS = ["paid_search", "organic", "social", "email", "referral"]
# Realistic-ish weighting: organic search still drives the most volume
# for a mid-size e-commerce brand, paid search second, others smaller.
CHANNEL_WEIGHTS = [0.25, 0.30, 0.20, 0.15, 0.10]

# Rough daily spend baseline per channel, in USD, before per-region
# scaling. Referral and organic have no direct "spend" in reality
# (organic search isn't paid, referral is word-of-mouth) - modeled here
# with a small nominal spend representing indirect program costs
# (referral incentives, SEO tooling/content), documented as a
# simplification rather than a precise real-world cost model.
CHANNEL_DAILY_SPEND_BASELINE = {
    "paid_search": 180,
    "organic": 20,
    "social": 90,
    "email": 15,
    "referral": 25,
}

REGION_SCALE = {"US": 1.0, "DE": 0.85, "GH": 0.4}  # smaller markets, smaller ad budgets


def tag_orders_with_channel(orders_path, region):
    orders = pd.read_csv(orders_path, usecols=["order_id"])
    channel = np.random.choice(CHANNELS, size=len(orders), p=CHANNEL_WEIGHTS)
    return pd.DataFrame({
        "order_id": orders["order_id"],
        "region": region,
        "channel": channel,
    })


def generate_channel_spend(orders_path, region):
    orders = pd.read_csv(orders_path, usecols=["order_date"])
    # order_date is still in Phase 1's messy multi-format text at this
    # point (this script runs against the same raw output files as
    # Phase 1) - parse loosely just to get a date range, precision to
    # the day isn't critical for a spend calendar.
    dates = pd.to_datetime(orders["order_date"], format="mixed", errors="coerce").dropna()
    date_range = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

    rows = []
    for day in date_range:
        for channel in CHANNELS:
            baseline = CHANNEL_DAILY_SPEND_BASELINE[channel] * REGION_SCALE[region]
            spend = max(0, np.random.normal(baseline, baseline * 0.25))
            rows.append({
                "date": day.strftime("%Y-%m-%d"),
                "region": region,
                "channel": channel,
                "spend_usd": round(spend, 2),
            })
    return pd.DataFrame(rows)


def main():
    regions = {"US": "us_orders.csv", "DE": "de_orders.csv", "GH": "gh_orders.csv"}

    attribution_frames = []
    spend_frames = []

    for region, filename in regions.items():
        orders_path = os.path.join(OUTPUT_DIR, filename)
        print(f"Processing {region}...")
        attribution_frames.append(tag_orders_with_channel(orders_path, region))
        spend_frames.append(generate_channel_spend(orders_path, region))

    attribution = pd.concat(attribution_frames, ignore_index=True)
    spend = pd.concat(spend_frames, ignore_index=True)

    attribution_path = os.path.join(OUTPUT_DIR, "order_channel_attribution.csv")
    spend_path = os.path.join(OUTPUT_DIR, "channel_spend.csv")
    attribution.to_csv(attribution_path, index=False)
    spend.to_csv(spend_path, index=False)

    print(f"\n{len(attribution):,} orders tagged with a channel -> {attribution_path}")
    print(f"{len(spend):,} daily spend rows -> {spend_path}")
    print("\nChannel distribution (should roughly match the target weights):")
    print((attribution["channel"].value_counts(normalize=True) * 100).round(1))
    print(f"\nTotal simulated spend across all regions: ${spend['spend_usd'].sum():,.2f}")


if __name__ == "__main__":
    main()

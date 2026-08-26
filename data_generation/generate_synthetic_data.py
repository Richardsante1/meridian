"""
MERIDIAN - Phase 1 - Tier 2 Synthetic Data Generator
======================================================
Generates realistic, deliberately messy order + customer data for three
regions the real (Tier 1) datasets don't cover: United States, Germany,
and Ghana.

WHY SYNTHETIC + CALIBRATED (not pure random):
Pure random data has no relationship to real-world order value / delivery
time / refund patterns, so any "insight" from it would be meaningless.
Instead we anchor the random distributions to reference statistics -
either real ones computed from the Tier 1 files if you've downloaded them,
or documented placeholders in calibration_reference.json if you haven't yet.

WHY MESSY ON PURPOSE:
Real company data is never clean. Each "messiness" injected below is
labeled with a comment explaining what real-world problem it simulates.
This messiness is what the later dbt/SQL cleaning layer will need to solve
- that's the whole point of the project.

Run:
    python generate_synthetic_data.py
"""

import os
import json
import random
import string
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# ----------------------------------------------------------------------
# CONFIG - change these as you scale up from a test run to the full build
# ----------------------------------------------------------------------
RANDOM_SEED = 42
ORDERS_PER_REGION = 2000          # start small to sanity-check; raise to
                                    # 20000-30000 per region for the real build
CUSTOMERS_PER_REGION = 600         # fewer customers than orders -> repeat buyers
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 12, 31)

HERE = os.path.dirname(os.path.abspath(__file__))
TIER1_DIR = os.path.join(HERE, "tier1_raw")
OUTPUT_DIR = os.path.join(HERE, "output")
CALIBRATION_FILE = os.path.join(HERE, "calibration_reference.json")

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

PRODUCT_CATEGORIES = [
    "Electronics", "Fashion", "Home & Kitchen", "Beauty", "Sports",
    "Books", "Toys", "Grocery", "Health", "Automotive",
]

# ----------------------------------------------------------------------
# GHANA REFERENCE DATA
# Faker has no built-in Ghana locale, so this is a small hand-built pool
# of common Akan / Ga / Ewe first & last names and major Ghanaian cities.
# DOCUMENTED ASSUMPTION: this is a simplification versus a full locale
# package and will not capture the true diversity of Ghanaian names -
# note this explicitly in DATA_DICTIONARY.md.
# ----------------------------------------------------------------------
GH_FIRST_NAMES = [
    "Kwame", "Kwesi", "Kofi", "Yaw", "Kojo", "Kwabena", "Kwaku",
    "Ama", "Efua", "Akosua", "Abena", "Adjoa", "Esi", "Yaa",
    "Nana", "Emmanuel", "Grace", "Comfort", "Prince", "Gifty",
]
GH_LAST_NAMES = [
    "Mensah", "Asante", "Owusu", "Boateng", "Osei", "Appiah",
    "Agyeman", "Darko", "Amoah", "Adjei", "Nkrumah", "Sarpong",
    "Baffour", "Ofori", "Adu", "Frimpong",
]
GH_CITIES = [
    "Accra", "Kumasi", "Tamale", "Takoradi", "Cape Coast",
    "Tema", "Sunyani", "Koforidua", "Ho", "Bolgatanga",
]


def load_calibration():
    """Load placeholder calibration, then try to override with stats
    computed from real Tier 1 files if they exist on disk yet."""
    with open(CALIBRATION_FILE, "r") as f:
        calib = json.load(f)

    calib["_recalibrated"] = {"US": False, "DE": False, "GH": False}
    # US and DE have no direct Tier 1 analog (Tier 1 is Brazil + UK only),
    # so true recalibration for those only happens indirectly via the
    # Olist/UCI cross-market checks we'll do in the analysis phase.
    # What we CAN do here is recalibrate GH/US/DE order-value spread
    # using the UCI (UK) unit-price distribution as a sanity ceiling,
    # since Online Retail II is the closest real analog available.
    uci_path = os.path.join(TIER1_DIR, "online_retail_II.xlsx")
    if os.path.exists(uci_path):
        try:
            uci = pd.read_excel(uci_path, sheet_name=0, nrows=50000)
            uci["line_total"] = uci["Quantity"] * uci["Price"]
            uci = uci[uci["line_total"] > 0]
            real_mean = float(uci["line_total"].mean())
            real_std = float(uci["line_total"].std())
            print(f"[calibration] Found real UCI data. "
                  f"Real mean line total = {real_mean:.2f}, std = {real_std:.2f}")
            # UK data is wholesale-flavored (bulk quantities), so we use it
            # only as a directional check, not a direct override - documented
            # judgment call, not a silent overwrite.
            calib["_uci_reference_mean"] = real_mean
            calib["_uci_reference_std"] = real_std
        except Exception as e:
            print(f"[calibration] Found UCI file but couldn't parse it: {e}")
    else:
        print("[calibration] No Tier 1 UCI file found yet - using "
              "placeholder calibration only. This is expected if you "
              "haven't done Step 2 of README_PHASE1.md yet.")

    olist_orders_path = os.path.join(TIER1_DIR, "olist", "olist_orders_dataset.csv")
    if os.path.exists(olist_orders_path):
        print("[calibration] Found real Olist data - will cross-check "
              "delivery time distributions against it in the analysis phase.")
    else:
        print("[calibration] No Tier 1 Olist file found yet.")

    return calib


def random_messy_date(dt):
    """Deliberately stores the same underlying datetime in inconsistent
    string formats, mimicking different upstream systems writing dates
    differently. Simulates: 'inconsistent date formats across regions'."""
    fmt = random.choice([
        "%Y-%m-%d %H:%M:%S",   # ISO
        "%m/%d/%Y %H:%M",       # US style
        "%d.%m.%Y",             # EU/DE style, no time
        "%d-%b-%Y",              # 15-Mar-2024 style
    ])
    return dt.strftime(fmt)


def make_customers(region_code, faker, n, name_pool=None, city_pool=None):
    customers = []
    for i in range(n):
        if name_pool:
            first = random.choice(name_pool[0])
            last = random.choice(name_pool[1])
            city = random.choice(city_pool)
        else:
            first = faker.first_name()
            last = faker.last_name()
            city = faker.city()

        email = f"{first.lower()}.{last.lower()}{random.randint(1,999)}@example.com"
        customers.append({
            "customer_id": f"{region_code}-CUST-{i:05d}",
            "first_name": first,
            "last_name": last,
            "email": email,
            "city": city,
            "region": region_code,
            "signup_date": random_messy_date(
                START_DATE + timedelta(days=random.randint(0, (END_DATE - START_DATE).days))
            ),
        })

    df = pd.DataFrame(customers)

    # MESSINESS: duplicate ~3% of customers with a typo'd / re-cased email,
    # simulating the same real person signing up twice. Simulates:
    # 'duplicate customer records (same person, different email casing/typos)'
    n_dupes = max(1, int(n * 0.03))
    dupe_rows = df.sample(n=n_dupes, random_state=RANDOM_SEED).copy()
    dupe_rows["customer_id"] = dupe_rows["customer_id"] + "-DUP"
    dupe_rows["email"] = dupe_rows["email"].apply(
        lambda e: e.upper() if random.random() < 0.5
        else e.replace(".", "", 1)  # drops a "." to simulate a typo
    )
    df = pd.concat([df, dupe_rows], ignore_index=True)
    return df


def make_orders(region_code, currency, customers_df, calib, n):
    orders = []
    cust_ids = customers_df["customer_id"].tolist()

    for i in range(n):
        order_date = START_DATE + timedelta(
            days=random.randint(0, (END_DATE - START_DATE).days)
        )

        # Order value from a log-normal-ish distribution anchored to
        # the calibration mean/std for this region (see calibration_reference.json)
        mean = calib[region_code]["avg_order_value_local"]
        std = calib[region_code]["order_value_std"]
        value = max(3.0, np.random.normal(mean, std))
        value = round(value, 2)

        category = random.choice(PRODUCT_CATEGORIES)
        # MESSINESS: ~5% missing product category. Simulates:
        # 'missing/null product category tags on ~5% of rows'
        if random.random() < 0.05:
            category = None

        # Delivery timestamp
        delivery_days_mean = calib[region_code]["delivery_days_mean"]
        delivery_days_std = calib[region_code]["delivery_days_std"]
        delivery_offset = max(0, np.random.normal(delivery_days_mean, delivery_days_std))
        delivered_date = order_date + timedelta(days=delivery_offset)

        # MESSINESS: some orders have delayed or entirely missing delivery
        # timestamps. Simulates: 'orders with delayed or missing delivery
        # timestamps'
        delivery_status_roll = random.random()
        if delivery_status_roll < 0.08:
            delivered_date_str = None  # missing entirely
        elif delivery_status_roll < 0.15:
            delivered_date_str = random_messy_date(delivered_date + timedelta(days=random.randint(5, 20)))  # badly delayed
        else:
            delivered_date_str = random_messy_date(delivered_date)

        # Refund logic
        is_refunded = random.random() < calib[region_code]["refund_rate"]
        refund_date_str = None
        if is_refunded:
            # MESSINESS: refunds land 15-45 days after purchase - a real
            # accounting reconciliation problem (revenue recognized in one
            # period, reversed in another).
            refund_offset = random.randint(15, 45)
            refund_date_str = random_messy_date(order_date + timedelta(days=refund_offset))

        # MESSINESS: currency stored inconsistently - simulates a real
        # integration bug where some rows were pre-converted to USD by an
        # upstream system and some weren't, with NO flag distinguishing them.
        # amount_raw is always in local currency; amount_display sometimes
        # (incorrectly) holds a USD-converted number while currency_code
        # still (incorrectly) says the local currency. This inconsistency
        # is exactly what the SQL cleaning layer in Phase 3 will need to
        # detect and fix.
        currency_bug_roll = random.random()
        if currency_bug_roll < 0.07 and currency != "USD":
            # crude fake "conversion" just to create plausible-looking bad data
            fake_usd_rate = {"EUR": 1.08, "GHS": 0.065}.get(currency, 1.0)
            amount_display = round(value * fake_usd_rate, 2)
        else:
            amount_display = value

        review_score = None
        if delivered_date_str is not None and random.random() < 0.85:
            base = calib[region_code]["review_score_mean"]
            review_score = int(np.clip(np.random.normal(base, 0.9), 1, 5))

        orders.append({
            "order_id": f"{region_code}-ORD-{i:06d}",
            "customer_id": random.choice(cust_ids),
            "region": region_code,
            "currency_code": currency,
            "amount_local_currency": value,
            "amount_display": amount_display,
            "product_category": category,
            "order_date": random_messy_date(order_date),
            "delivered_date": delivered_date_str,
            "is_refunded": is_refunded,
            "refund_date": refund_date_str,
            "review_score": review_score,
            "order_status": "cancelled" if random.random() < 0.02 else "completed",
        })

    df = pd.DataFrame(orders)

    # MESSINESS: "phantom" cancelled-then-reordered transactions. Take a
    # small sample of cancelled orders and generate a near-duplicate
    # "reorder" a few days later, simulating a customer whose payment
    # failed, then re-purchased. Simulates: 'a subset of "phantom"
    # cancelled-then-reordered transactions'
    cancelled = df[df["order_status"] == "cancelled"]
    if len(cancelled) > 0:
        n_phantom = max(1, int(len(cancelled) * 0.4))
        phantom_source = cancelled.sample(n=min(n_phantom, len(cancelled)), random_state=RANDOM_SEED)
        phantom_rows = []
        for idx, row in phantom_source.iterrows():
            new_row = row.copy()
            new_row["order_id"] = row["order_id"] + "-REORDER"
            # a few days after the original cancelled order
            new_row["order_status"] = "completed"
            phantom_rows.append(new_row)
        df = pd.concat([df, pd.DataFrame(phantom_rows)], ignore_index=True)

    return df


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    calib = load_calibration()

    faker_us = Faker("en_US")
    faker_de = Faker("de_DE")

    regions = {
        "US": {"faker": faker_us, "currency": "USD", "name_pool": None, "city_pool": None},
        "DE": {"faker": faker_de, "currency": "EUR", "name_pool": None, "city_pool": None},
        "GH": {"faker": faker_us, "currency": "GHS",
               "name_pool": (GH_FIRST_NAMES, GH_LAST_NAMES), "city_pool": GH_CITIES},
    }

    for code, cfg in regions.items():
        print(f"\n--- Generating region: {code} ---")
        customers = make_customers(
            code, cfg["faker"], CUSTOMERS_PER_REGION,
            name_pool=cfg["name_pool"], city_pool=cfg["city_pool"]
        )
        orders = make_orders(code, cfg["currency"], customers, calib, ORDERS_PER_REGION)

        cust_path = os.path.join(OUTPUT_DIR, f"{code.lower()}_customers.csv")
        ord_path = os.path.join(OUTPUT_DIR, f"{code.lower()}_orders.csv")
        customers.to_csv(cust_path, index=False)
        orders.to_csv(ord_path, index=False)

        print(f"  customers: {len(customers)} rows -> {cust_path}")
        print(f"  orders:    {len(orders)} rows -> {ord_path}")
        print(f"  missing product_category: {orders['product_category'].isna().mean():.1%}")
        print(f"  missing delivered_date:   {orders['delivered_date'].isna().mean():.1%}")
        print(f"  refund rate:              {orders['is_refunded'].mean():.1%}")

    print("\nDone. See output/ for all files.")
    print("Next: run fetch_exchange_rates.py, then move to Phase 2.")


if __name__ == "__main__":
    main()

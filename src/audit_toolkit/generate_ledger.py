"""Generate a synthetic accounts-payable ledger with planted anomalies.

The ledger is made up. Problems are hidden in it on purpose, and their
locations are saved in a separate answer key, so every audit test can be
scored against known answers (how many planted problems it caught, and how
many innocent transactions it flagged by mistake).

Run from the project root:

    python src/audit_toolkit/generate_ledger.py

This writes three files to data/:

    ledger.csv            the transactions the tests work on (no labels)
    answer_key.csv        for each invoice: is it a planted anomaly, and which type
    missing_invoices.csv  invoice numbers deliberately removed from the sequence
"""
from pathlib import Path

import numpy as np
import pandas as pd

APPROVAL_LIMIT = 5000
YEAR = 2025
FIRST_INVOICE = 100001

# The company's public-holiday calendar for this synthetic ledger. The dates
# follow Brunei's 2025 holidays, but Islamic holiday dates depend on the moon
# sighting, so treat them as approximate. Tests should use this list.
HOLIDAYS = pd.to_datetime([
    "2025-01-01",  # New Year's Day
    "2025-01-27",  # Isra' Mi'raj
    "2025-01-29",  # Chinese New Year
    "2025-02-24",  # National Day (observed)
    "2025-03-03",  # First day of Ramadan (observed)
    "2025-03-18",  # Nuzul Al-Quran
    "2025-03-31",  # Hari Raya Aidilfitri
    "2025-04-01",  # Hari Raya Aidilfitri
    "2025-04-02",  # Hari Raya Aidilfitri
    "2025-06-02",  # Royal Brunei Armed Forces Day (observed)
    "2025-06-09",  # Hari Raya Aidiladha (observed)
    "2025-06-27",  # Islamic New Year
    "2025-07-15",  # Sultan's Birthday
    "2025-09-05",  # Prophet Muhammad's Birthday
    "2025-12-25",  # Christmas Day
])

# Typical amount for each category: (median in BND, spread on a log scale)
CATEGORIES = {
    "Office Supplies": (180, 0.9),
    "Travel": (650, 0.9),
    "Utilities": (900, 0.6),
    "Maintenance": (1400, 1.0),
    "IT Equipment": (2200, 0.9),
    "Consulting": (3800, 0.8),
}

# Planted anomalies: how many of each type
N_DUPLICATE = 30
N_BELOW_THRESHOLD = 25
N_ROUND = 25
N_WEEKEND_HOLIDAY = 25
N_OUTLIER = 10
N_FABRICATED = 120     # all transactions of one made-up vendor
N_MISSING_INVOICES = 12


def _business_days(rng, n):
    """n random working days (no weekends or holidays) in the year."""
    days = pd.bdate_range(f"{YEAR}-01-01", f"{YEAR}-12-31")
    days = days[~days.isin(HOLIDAYS)]
    return pd.Series(rng.choice(days, n))


def _next_working_day(date):
    while date.weekday() >= 5 or date in HOLIDAYS:
        date += pd.Timedelta(days=1)
    return date


def generate_ledger(n_clean=4600, seed=7):
    rng = np.random.default_rng(seed)

    vendors = [f"V{i:03d}" for i in range(1, 59)]          # V001 to V058
    vendor_category = {v: rng.choice(list(CATEGORIES)) for v in vendors}

    # 1. Ordinary (clean) transactions
    vendor = rng.choice(vendors, n_clean)
    category = np.array([vendor_category[v] for v in vendor])
    median = np.array([CATEGORIES[c][0] for c in category])
    spread = np.array([CATEGORIES[c][1] for c in category])
    # Log-normal amounts, redrawing the rare extreme values (beyond 3 spreads)
    # so that genuinely extreme payments are the planted outliers
    z = rng.standard_normal(n_clean)
    while (np.abs(z) > 3).any():
        bad = np.abs(z) > 3
        z[bad] = rng.standard_normal(bad.sum())
    amount = np.round(median * np.exp(spread * z), 2)

    df = pd.DataFrame({
        "date": _business_days(rng, n_clean),
        "vendor": vendor,
        "category": category,
        "amount": amount,
        "anomaly_type": "clean",
    })

    # Innocent repeated, round amounts: monthly rent and a software subscription.
    # These look like duplicates and round numbers, but they are normal.
    months = pd.date_range(f"{YEAR}-01-01", periods=12, freq="MS")
    recurring = []
    for m in months:
        first = _next_working_day(m)
        recurring.append({"date": first, "vendor": "V059", "category": "Rent",
                          "amount": 3000.00, "anomaly_type": "clean"})
        recurring.append({"date": _next_working_day(first + pd.Timedelta(days=14)),
                          "vendor": "V060", "category": "Software Subscription",
                          "amount": 250.00, "anomaly_type": "clean"})
    df = pd.concat([df, pd.DataFrame(recurring)], ignore_index=True)

    # Rows that may be turned into anomalies: ordinary clean rows only
    pool = rng.permutation(np.arange(n_clean))
    take = iter(pool)

    def pick(k):
        return [next(take) for _ in range(k)]

    # 2. Amounts just below the approval limit (95% to 99.9% of it)
    idx = pick(N_BELOW_THRESHOLD)
    df.loc[idx, "amount"] = np.round(rng.uniform(0.95, 0.999, len(idx)) * APPROVAL_LIMIT, 2)
    df.loc[idx, "anomaly_type"] = "below_threshold"

    # 3. Suspiciously round amounts
    idx = pick(N_ROUND)
    df.loc[idx, "amount"] = rng.choice([1000, 1500, 2000, 4000, 6000, 7500, 10000], len(idx)).astype(float)
    df.loc[idx, "anomaly_type"] = "round_number"

    # 4. Posted on a weekend or public holiday
    idx = pick(N_WEEKEND_HOLIDAY)
    all_days = pd.date_range(f"{YEAR}-01-01", f"{YEAR}-12-31")
    off_days = all_days[(all_days.weekday >= 5) | all_days.isin(HOLIDAYS)]
    df.loc[idx, "date"] = rng.choice(off_days, len(idx))
    df.loc[idx, "anomaly_type"] = "weekend_holiday"

    # 5. Extreme amounts: 15 to 40 times what the category normally costs
    idx = pick(N_OUTLIER)
    cat_median = df.loc[idx, "category"].map(lambda c: CATEGORIES[c][0]).to_numpy()
    df.loc[idx, "amount"] = np.round(cat_median * rng.uniform(15, 40, len(idx)), 2)
    df.loc[idx, "anomaly_type"] = "outlier"

    # 6. Duplicate payments: copies of clean rows, paid again 0 to 5 days later
    idx = pick(N_DUPLICATE)
    dups = df.loc[idx].copy()
    shift = pd.to_timedelta(rng.integers(0, 6, len(idx)), unit="D")
    dups["date"] = [_next_working_day(d) for d in dups["date"] + shift]
    dups["anomaly_type"] = "duplicate"

    # 7. A made-up vendor whose amounts were invented by a person:
    #    first digits are spread evenly instead of following Benford's Law
    first_digit = rng.integers(1, 10, N_FABRICATED)
    magnitude = 10.0 ** rng.integers(2, 4, N_FABRICATED)          # hundreds or thousands
    fake_amount = first_digit * magnitude + rng.uniform(0, 1, N_FABRICATED) * magnitude * 0.99
    fabricated = pd.DataFrame({
        "date": _business_days(rng, N_FABRICATED),
        "vendor": "V061",
        "category": "Consulting",
        "amount": np.round(fake_amount, 2),
        "anomaly_type": "fabricated",
    })

    df = pd.concat([df, dups, fabricated], ignore_index=True)

    # Invoice numbers run in date order, as an accounting system would assign them.
    # A stable sort keeps each duplicate after its original on the same day.
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    numbers = np.arange(FIRST_INVOICE, FIRST_INVOICE + len(df) + N_MISSING_INVOICES)
    removed = np.sort(rng.choice(numbers[1:-1], N_MISSING_INVOICES, replace=False))
    numbers = numbers[~np.isin(numbers, removed)]
    df["invoice"] = [f"INV-{n}" for n in numbers]

    ledger = df[["invoice", "date", "vendor", "category", "amount"]]
    answer_key = pd.DataFrame({
        "invoice": df["invoice"],
        "is_anomaly": df["anomaly_type"] != "clean",
        "anomaly_type": df["anomaly_type"],
    })
    missing = pd.DataFrame({"invoice": [f"INV-{n}" for n in removed]})
    return ledger, answer_key, missing


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    data = root / "data"
    data.mkdir(exist_ok=True)

    ledger, answer_key, missing = generate_ledger()
    ledger.to_csv(data / "ledger.csv", index=False)
    answer_key.to_csv(data / "answer_key.csv", index=False)
    missing.to_csv(data / "missing_invoices.csv", index=False)

    print(f"Transactions: {len(ledger)}")
    print(answer_key["anomaly_type"].value_counts().to_string())
    print(f"Missing invoice numbers: {len(missing)}")

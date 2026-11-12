"""Score a test's flags against the answer key.

A test produces flags: a True/False Series with one value per transaction in
the ledger (True = worth a closer look). `check()` compares those flags with
the planted anomalies and reports what the test caught and what it got wrong.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def load_ledger():
    """The ledger the tests work on. Dates are read as real dates."""
    return pd.read_csv(DATA / "ledger.csv", parse_dates=["date"])


def _answer_key(ledger):
    key = pd.read_csv(DATA / "answer_key.csv")
    labels = ledger[["invoice"]].merge(key, on="invoice", how="left")
    labels.index = ledger.index
    return labels


def _as_flags(flags, ledger):
    if not isinstance(flags, pd.Series):
        raise TypeError(
            "Your flags should be a pandas Series of True/False values, one per "
            "transaction, e.g. df['amount'] > 5000. You gave: " + type(flags).__name__
        )
    flags = flags.reindex(ledger.index)
    if flags.dtype != bool:
        flags = flags.fillna(False).astype(bool)
    return flags


def check(flags, anomaly_type, ledger=None):
    """Report how well `flags` finds the planted anomalies of `anomaly_type`.

    Caught:       planted anomalies of this type that were flagged
    False alarms: ordinary (clean) transactions that were flagged
    Precision:    of everything flagged, the share that was really a problem
    Recall:       of the planted problems of this type, the share caught
    """
    ledger = load_ledger() if ledger is None else ledger
    labels = _answer_key(ledger)
    flags = _as_flags(flags, ledger)

    is_target = labels["anomaly_type"] == anomaly_type
    if is_target.sum() == 0:
        types = sorted(labels["anomaly_type"].unique())
        raise ValueError(f"No planted anomalies called '{anomaly_type}'. Choose from: {types}")

    flagged = int(flags.sum())
    caught = int((flags & is_target).sum())
    planted = int(is_target.sum())
    false_alarms = int((flags & (labels["anomaly_type"] == "clean")).sum())
    other = labels.loc[flags & labels["is_anomaly"] & ~is_target, "anomaly_type"].value_counts()
    real_problems = caught + int(other.sum())

    recall = caught / planted
    precision = real_problems / flagged if flagged else 0.0

    print(f"Flagged:      {flagged} transactions")
    print(f"Caught:       {caught} of {planted} planted '{anomaly_type}' anomalies (recall {recall:.0%})")
    print(f"False alarms: {false_alarms} ordinary transactions flagged")
    if len(other):
        found = ", ".join(f"{n} {t}" for t, n in other.items())
        print(f"Bonus:        also flagged other planted problems: {found}")
    print(f"Precision:    {precision:.0%} of flagged transactions were real problems")

    if flagged == 0:
        print("\nNothing was flagged. Check your condition: is it ever True?")
    elif caught == planted and false_alarms == 0:
        print("\nPerfect: every planted anomaly caught, with no false alarms.")
    elif caught == planted:
        print("\nAll planted anomalies caught. See if you can reduce the false alarms.")
    elif recall >= 0.8:
        print("\nMost planted anomalies caught. Look at the ones you missed.")
    else:
        print("\nMany planted anomalies were missed. Compare your condition with the task.")

    return {"flagged": flagged, "caught": caught, "planted": planted,
            "false_alarms": false_alarms, "precision": precision, "recall": recall}


def missed(flags, anomaly_type, ledger=None):
    """The planted anomalies of this type that your flags did not catch."""
    ledger = load_ledger() if ledger is None else ledger
    labels = _answer_key(ledger)
    flags = _as_flags(flags, ledger)
    return ledger[(labels["anomaly_type"] == anomaly_type) & ~flags]


def false_alarms(flags, ledger=None):
    """The ordinary transactions your flags marked as suspicious."""
    ledger = load_ledger() if ledger is None else ledger
    labels = _answer_key(ledger)
    flags = _as_flags(flags, ledger)
    return ledger[(labels["anomaly_type"] == "clean") & flags]


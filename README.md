# Audit Anomaly Toolkit

A Python toolkit that screens a financial ledger for transactions worth an auditor's attention. It runs several standard audit analytics tests on the same data and ranks each transaction by how many tests flag it.

A flag means "worth investigating", not "fraud".

## Why several tests?

Each test catches a different kind of problem, and each one misses others. A payment that is just below the approval limit, posted on a Sunday, to a new vendor, with a round amount, is far more suspicious than one that trips a single test. This project builds on my earlier [Benford's Law anomaly detection](https://github.com/Suhayell/benford-anomaly-detection) project, which showed that combining rules more than doubled the coverage of the best single rule.

## Planned tests

| Test | What it looks for | Status |
|---|---|---|
| Duplicate payments | Same vendor and amount within a few days | Not started |
| Just below the approval limit | Amounts just under the limit, which may avoid extra approval | Not started |
| Round amounts | Exact round figures such as 5,000.00 | Not started |
| Weekend and holiday postings | Entries made when the office is normally closed | Not started |
| Sequence gaps | Missing invoice numbers | Not started |
| Statistical outliers | Amounts far from the usual (IQR or log Z-score) | Not started |
| Benford's Law | First-digit distribution compared with Benford's expected shares | Not started |
| Risk score | Combines the tests and ranks transactions | Not started |

## Roadmap

1. Set up the project in VS Code and GitHub
2. Build a sample ledger with planted anomalies, so each test can be checked against known answers
3. Write each test in a notebook, then move it into `src/audit_toolkit/checks.py`
4. Combine the tests into a risk score and evaluate precision and recall
5. Write up the findings in this README
6. Build a Streamlit app: upload a CSV and see the flagged transactions

## Project structure

```
data/                  sample ledgers (generated)
notebooks/             step-by-step analysis notebooks
src/audit_toolkit/     the reusable test functions
requirements.txt       Python packages used
```

## How to run

On Windows, double-click `setup_windows.bat`, or run these commands in a terminal:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then open `notebooks/00_setup_check.ipynb` in VS Code and choose the `.venv` kernel.

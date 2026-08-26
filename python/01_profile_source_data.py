from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "online_retail_II.xlsx"
INTERIM_FILE = PROJECT_ROOT / "data" / "interim" / "online_retail_combined.pkl"


if not RAW_FILE.exists():
    raise FileNotFoundError(f"Source file not found: {RAW_FILE}")


# Read the slow Excel source only once, then use a local cached copy.
if INTERIM_FILE.exists():
    print("Loading cached interim dataset...")
    transactions = pd.read_pickle(INTERIM_FILE)

else:
    print("Creating interim dataset from Excel...")

    workbook = pd.ExcelFile(RAW_FILE)

    yearly_data = pd.read_excel(
        RAW_FILE,
        sheet_name=workbook.sheet_names
    )

    transactions = pd.concat(
        yearly_data.values(),
        ignore_index=True
    )

    INTERIM_FILE.parent.mkdir(parents=True, exist_ok=True)
    transactions.to_pickle(INTERIM_FILE)

    print(f"Created: {INTERIM_FILE.name}")


print()
print("--- Combined dataset ---")
print(f"Rows: {len(transactions):,}")
print(f"Columns: {transactions.shape[1]}")
print(
    f"Date range: {transactions['InvoiceDate'].min()} "
    f"to {transactions['InvoiceDate'].max()}"
)

print()
print("Missing values:")
print(transactions.isna().sum())


print()
print("--- Initial data quality checks ---")

print(f"Duplicate rows: {transactions.duplicated().sum():,}")
print(f"Negative quantities: {(transactions['Quantity'] < 0).sum():,}")
print(f"Zero quantities: {(transactions['Quantity'] == 0).sum():,}")
print(f"Negative prices: {(transactions['Price'] < 0).sum():,}")
print(f"Zero prices: {(transactions['Price'] == 0).sum():,}")

cancelled = (
    transactions["Invoice"]
    .astype(str)
    .str.startswith("C")
)

print(f"Cancellation rows: {cancelled.sum():,}")
print(f"Unique invoices: {transactions['Invoice'].nunique():,}")
print(f"Identifiable customers: {transactions['Customer ID'].nunique():,}")
print(f"Countries: {transactions['Country'].nunique():,}")

from pathlib import Path
import sqlite3

import pandas as pd


# Anchor all paths to the repository root so the script works
# consistently regardless of the current PowerShell directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CLASSIFIED_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "cleaned"
    / "online_retail_transactions_classified.pkl"
)

DATABASE_FILE = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "online_retail.db"
)

TABLE_NAME = "classified_transactions"

EXPECTED_ROW_COUNT = 1_044_848
EXPECTED_COLUMN_COUNT = 32


def load_classified_transactions() -> pd.DataFrame:
    """Load the reproducible classified transaction layer."""

    if not CLASSIFIED_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Classified transaction file not found: {CLASSIFIED_DATA_FILE}"
        )

    transactions = pd.read_pickle(CLASSIFIED_DATA_FILE)

    # These checks protect the SQL layer from being built from an
    # unexpected version of the cleaned transaction dataset.
    if len(transactions) != EXPECTED_ROW_COUNT:
        raise ValueError(
            "Unexpected classified transaction row count: "
            f"{len(transactions):,}"
        )

    if len(transactions.columns) != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            "Unexpected classified transaction column count: "
            f"{len(transactions.columns)}"
        )

    return transactions


def build_database(transactions: pd.DataFrame) -> None:
    """Create the local SQLite database from the classified transaction layer."""

    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_FILE) as connection:
        # Replace the generated table so rerunning the script produces a
        # reproducible database rather than appending duplicate records.
        transactions.to_sql(
            TABLE_NAME,
            connection,
            if_exists="replace",
            index=False,
        )

        # These indexes support the invoice-, customer- and period-level
        # SQL analysis planned for the next stages without changing the data.
        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_invoice
            ON {TABLE_NAME} (invoice_clean)
            """
        )

        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_customer
            ON {TABLE_NAME} (customer_id_clean)
            """
        )

        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_period
            ON {TABLE_NAME} (analysis_period)
            """
        )

        connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_class
            ON {TABLE_NAME} (transaction_class)
            """
        )

        connection.commit()


def validate_database(transactions: pd.DataFrame) -> None:
    """Reconcile basic SQLite structure and row counts with the pandas source."""

    with sqlite3.connect(DATABASE_FILE) as connection:
        database_row_count = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME}"
        ).fetchone()[0]

        database_column_count = len(
            connection.execute(
                f"PRAGMA table_info({TABLE_NAME})"
            ).fetchall()
        )

        if database_row_count != len(transactions):
            raise ValueError(
                "SQLite row count does not reconcile with the classified "
                f"transaction layer: {database_row_count:,} vs "
                f"{len(transactions):,}"
            )

        if database_column_count != len(transactions.columns):
            raise ValueError(
                "SQLite column count does not reconcile with the classified "
                f"transaction layer: {database_column_count} vs "
                f"{len(transactions.columns)}"
            )

        database_period_counts = pd.read_sql_query(
            f"""
            SELECT
                analysis_period,
                COUNT(*) AS row_count
            FROM {TABLE_NAME}
            GROUP BY analysis_period
            ORDER BY analysis_period
            """,
            connection,
        )

    pandas_period_counts = (
        transactions["analysis_period"]
        .value_counts()
        .rename_axis("analysis_period")
        .reset_index(name="row_count")
    )

    # SQLite returns period labels as ordinary strings, whereas the cleaned
    # pandas layer stores them as a categorical field. Convert both to the
    # same representation before comparing the actual analytical values.
    database_period_counts["analysis_period"] = (
        database_period_counts["analysis_period"].astype("string")
    )

    pandas_period_counts["analysis_period"] = (
        pandas_period_counts["analysis_period"].astype("string")
    )

    database_period_counts = (
        database_period_counts
        .sort_values("analysis_period")
        .reset_index(drop=True)
    )

    pandas_period_counts = (
        pandas_period_counts
        .sort_values("analysis_period")
        .reset_index(drop=True)
    )

    # Period reconciliation matters because customer segmentation must use
    # the behavioural window while the validation period remains held out.
    pd.testing.assert_frame_equal(
        database_period_counts,
        pandas_period_counts,
        check_dtype=False,
    )

    print("\nDatabase validation passed.")
    print(f"SQLite rows: {database_row_count:,}")
    print(f"SQLite columns: {database_column_count}")

    print("\nRows by analytical period:")
    print(database_period_counts.to_string(index=False))


def main() -> None:
    print(f"Classified data: {CLASSIFIED_DATA_FILE}")
    print(f"SQLite database: {DATABASE_FILE}")

    transactions = load_classified_transactions()

    print(f"\nRows loaded: {len(transactions):,}")
    print(f"Columns loaded: {len(transactions.columns)}")

    print("\nBuilding SQLite database...")
    build_database(transactions)

    validate_database(transactions)

    print(f"\nDatabase created successfully: {DATABASE_FILE}")


if __name__ == "__main__":
    main()
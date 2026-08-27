# -*- coding: utf-8 -*-

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "online_retail_II.xlsx"
)

INTERIM_FILE = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "online_retail_combined.pkl"
)

SOURCE_SHEETS = (
    "Year 2009-2010",
    "Year 2010-2011",
)

EXPECTED_COLUMNS = (
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
)

DISPLAY_COLUMNS = list(EXPECTED_COLUMNS)

# Increment this if the construction logic for the interim dataset changes.
# This prevents an old cached DataFrame from silently bypassing new logic.
CACHE_VERSION = 2


def print_section(title):
    """Print a consistent heading for profiling output."""

    print()
    print(f"--- {title} ---")


def validate_source_columns(dataframe, source_name):
    """Confirm that a source table contains the expected transaction fields."""

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{source_name} is missing expected columns: "
            f"{missing_columns}"
        )


def build_interim_dataset():
    """
    Build the combined transaction dataset from the original Excel workbook.

    The two annual worksheets overlap exactly in early December 2010.
    The earlier worksheet is retained in full and only records after its final
    timestamp are appended from the later worksheet. This removes duplicated
    source coverage without deleting repeated lines that already exist within
    either individual worksheet.
    """

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {RAW_FILE}"
        )

    print("Creating interim dataset from Excel...")

    source_data = pd.read_excel(
        RAW_FILE,
        sheet_name=list(SOURCE_SHEETS),
    )

    earlier_sheet = source_data[SOURCE_SHEETS[0]].copy()
    later_sheet = source_data[SOURCE_SHEETS[1]].copy()

    validate_source_columns(
        earlier_sheet,
        SOURCE_SHEETS[0],
    )
    validate_source_columns(
        later_sheet,
        SOURCE_SHEETS[1],
    )

    earlier_sheet["InvoiceDate"] = pd.to_datetime(
        earlier_sheet["InvoiceDate"]
    )
    later_sheet["InvoiceDate"] = pd.to_datetime(
        later_sheet["InvoiceDate"]
    )

    source_columns = list(EXPECTED_COLUMNS)

    earlier_start = earlier_sheet["InvoiceDate"].min()
    earlier_end = earlier_sheet["InvoiceDate"].max()

    later_start = later_sheet["InvoiceDate"].min()
    later_end = later_sheet["InvoiceDate"].max()

    overlap_start = max(
        earlier_start,
        later_start,
    )

    overlap_end = min(
        earlier_end,
        later_end,
    )

    if overlap_start > overlap_end:
        raise ValueError(
            "The expected source worksheet overlap was not found."
        )

    earlier_overlap = earlier_sheet.loc[
        earlier_sheet["InvoiceDate"].between(
            overlap_start,
            overlap_end,
        ),
        source_columns,
    ].copy()

    later_overlap = later_sheet.loc[
        later_sheet["InvoiceDate"].between(
            overlap_start,
            overlap_end,
        ),
        source_columns,
    ].copy()

    # Compare multiplicities as well as distinct row values. This verifies
    # that repeated rows within the overlap occur the same number of times in
    # each source worksheet.
    earlier_counts = (
        earlier_overlap
        .groupby(
            source_columns,
            dropna=False,
        )
        .size()
        .rename("earlier_count")
        .reset_index()
    )

    later_counts = (
        later_overlap
        .groupby(
            source_columns,
            dropna=False,
        )
        .size()
        .rename("later_count")
        .reset_index()
    )

    overlap_comparison = earlier_counts.merge(
        later_counts,
        on=source_columns,
        how="outer",
    )

    overlap_comparison[
        ["earlier_count", "later_count"]
    ] = (
        overlap_comparison[
            ["earlier_count", "later_count"]
        ]
        .fillna(0)
        .astype(int)
    )

    same_count = (
        overlap_comparison["earlier_count"]
        == overlap_comparison["later_count"]
    )

    if not same_count.all():
        raise ValueError(
            "The overlapping source periods are not identical. "
            "Review the workbook before combining the worksheets."
        )

    matched_occurrences = (
        overlap_comparison[
            ["earlier_count", "later_count"]
        ]
        .min(axis=1)
        .sum()
    )

    # Keep all of the earlier worksheet. From the later worksheet, retain
    # only records occurring after the earlier worksheet has finished.
    later_non_overlap = later_sheet.loc[
        later_sheet["InvoiceDate"] > earlier_end
    ].copy()

    transactions = pd.concat(
        [
            earlier_sheet,
            later_non_overlap,
        ],
        ignore_index=True,
    )

    validate_source_columns(
        transactions,
        "Combined transactions",
    )

    overlap_summary = {
        "earlier_start": earlier_start,
        "earlier_end": earlier_end,
        "later_start": later_start,
        "later_end": later_end,
        "overlap_start": overlap_start,
        "overlap_end": overlap_end,
        "earlier_overlap_rows": len(earlier_overlap),
        "later_overlap_rows": len(later_overlap),
        "earlier_distinct_patterns": len(earlier_counts),
        "later_distinct_patterns": len(later_counts),
        "shared_patterns": int(
            (
                (overlap_comparison["earlier_count"] > 0)
                & (overlap_comparison["later_count"] > 0)
            ).sum()
        ),
        "identical_count_patterns": int(
            same_count.sum()
        ),
        "total_comparison_patterns": len(
            overlap_comparison
        ),
        "matched_occurrences": int(
            matched_occurrences
        ),
        "different_count_patterns": int(
            (~same_count).sum()
        ),
        "removed_later_overlap_rows": len(
            later_overlap
        ),
    }

    cache_payload = {
        "cache_version": CACHE_VERSION,
        "transactions": transactions,
        "overlap_summary": overlap_summary,
    }

    INTERIM_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.to_pickle(
        cache_payload,
        INTERIM_FILE,
    )

    print(f"Created: {INTERIM_FILE.name}")

    return transactions, overlap_summary


def load_transactions():
    """
    Load the validated interim dataset when possible.

    The cache is a performance optimisation only. The original Excel workbook
    remains the authoritative source and can regenerate the interim dataset.
    """

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {RAW_FILE}"
        )

    if INTERIM_FILE.exists():
        print("Checking cached interim dataset...")

        try:
            cached_object = pd.read_pickle(
                INTERIM_FILE
            )
        except Exception:
            print(
                "Cached interim dataset could not be read. "
                "Rebuilding from Excel."
            )
        else:
            if (
                isinstance(cached_object, dict)
                and cached_object.get("cache_version")
                == CACHE_VERSION
                and "transactions" in cached_object
                and "overlap_summary" in cached_object
            ):
                print(
                    "Loading validated cached interim dataset..."
                )

                return (
                    cached_object["transactions"],
                    cached_object["overlap_summary"],
                )

            print(
                "Existing interim cache uses older construction "
                "logic. Rebuilding from Excel."
            )

    return build_interim_dataset()


def main():
    transactions, overlap_summary = load_transactions()

    validate_source_columns(
        transactions,
        "Combined transactions",
    )

    # Reusable masks keep the profiling definitions consistent across the
    # different diagnostic sections.
    missing_customer = transactions[
        "Customer ID"
    ].isna()

    negative_quantity = (
        transactions["Quantity"] < 0
    )

    zero_quantity = (
        transactions["Quantity"] == 0
    )

    negative_price = (
        transactions["Price"] < 0
    )

    zero_price = (
        transactions["Price"] == 0
    )

    cancelled = (
        transactions["Invoice"]
        .astype("string")
        .str.startswith(
            "C",
            na=False,
        )
    )

    line_value = (
        transactions["Quantity"]
        * transactions["Price"]
    )

    # This diagnostic measure intentionally includes only positive-quantity,
    # positive-price lines. It is useful for assessing the commercial scale
    # of missing customer identifiers before final cleaning rules are known.
    positive_sale = (
        (transactions["Quantity"] > 0)
        & (transactions["Price"] > 0)
    )

    print_section("Source worksheet overlap")

    print(
        "Year 2009-2010 date range: "
        f"{overlap_summary['earlier_start']} to "
        f"{overlap_summary['earlier_end']}"
    )

    print(
        "Year 2010-2011 date range: "
        f"{overlap_summary['later_start']} to "
        f"{overlap_summary['later_end']}"
    )

    print(
        "Overlap period: "
        f"{overlap_summary['overlap_start']} to "
        f"{overlap_summary['overlap_end']}"
    )

    print(
        "Earlier-sheet overlap rows: "
        f"{overlap_summary['earlier_overlap_rows']:,}"
    )

    print(
        "Later-sheet overlap rows: "
        f"{overlap_summary['later_overlap_rows']:,}"
    )

    print(
        "Distinct row patterns in earlier overlap: "
        f"{overlap_summary['earlier_distinct_patterns']:,}"
    )

    print(
        "Distinct row patterns in later overlap: "
        f"{overlap_summary['later_distinct_patterns']:,}"
    )

    print(
        "Exact row patterns present in both sheets: "
        f"{overlap_summary['shared_patterns']:,}"
    )

    print(
        "Patterns with identical occurrence counts: "
        f"{overlap_summary['identical_count_patterns']:,} "
        f"of "
        f"{overlap_summary['total_comparison_patterns']:,}"
    )

    print(
        "Matched row occurrences across the two sheets: "
        f"{overlap_summary['matched_occurrences']:,}"
    )

    print(
        "Rows removed from the later worksheet as "
        "duplicate source coverage: "
        f"{overlap_summary['removed_later_overlap_rows']:,}"
    )

    print_section("Combined dataset")

    print(
        f"Rows: {len(transactions):,}"
    )

    print(
        f"Columns: {transactions.shape[1]}"
    )

    print(
        "Date range: "
        f"{transactions['InvoiceDate'].min()} "
        f"to "
        f"{transactions['InvoiceDate'].max()}"
    )

    print("\nData types:")
    print(
        transactions.dtypes.to_string()
    )

    print("\nMissing values:")
    print(
        transactions
        .isna()
        .sum()
        .to_string()
    )

    print_section(
        "Initial data quality checks"
    )

    print(
        "Duplicate rows: "
        f"{transactions.duplicated().sum():,}"
    )

    print(
        "Negative quantities: "
        f"{negative_quantity.sum():,}"
    )

    print(
        "Zero quantities: "
        f"{zero_quantity.sum():,}"
    )

    print(
        "Negative prices: "
        f"{negative_price.sum():,}"
    )

    print(
        "Zero prices: "
        f"{zero_price.sum():,}"
    )

    print(
        "Cancellation rows: "
        f"{cancelled.sum():,}"
    )

    print(
        "Unique invoices: "
        f"{transactions['Invoice'].nunique():,}"
    )

    print(
        "Identifiable customers: "
        f"{transactions['Customer ID'].nunique():,}"
    )

    print(
        "Countries: "
        f"{transactions['Country'].nunique():,}"
    )

    print_section(
        "Missing Customer ID impact"
    )

    missing_customer_rows = int(
        missing_customer.sum()
    )

    missing_customer_share = (
        missing_customer.mean()
    )

    missing_customer_invoices = (
        transactions.loc[
            missing_customer,
            "Invoice",
        ]
        .nunique()
    )

    missing_customer_positive_value = (
        line_value.loc[
            missing_customer
            & positive_sale
        ]
        .sum()
    )

    total_positive_value = (
        line_value.loc[
            positive_sale
        ]
        .sum()
    )

    if total_positive_value:
        missing_customer_value_share = (
            missing_customer_positive_value
            / total_positive_value
        )
    else:
        missing_customer_value_share = float("nan")

    print(
        "Rows without Customer ID: "
        f"{missing_customer_rows:,}"
    )

    print(
        "Share of source rows: "
        f"{missing_customer_share:.1%}"
    )

    print(
        "Invoices containing rows without Customer ID: "
        f"{missing_customer_invoices:,}"
    )

    print(
        "Raw positive transaction value without "
        "Customer ID: "
        f"£{missing_customer_positive_value:,.2f}"
    )

    print(
        "Share of raw positive transaction value: "
        f"{missing_customer_value_share:.1%}"
    )

    print(
        "\nNote: these are profiling figures before final "
        "cleaning rules. They should not be reported later "
        "as the final exclusion impact without recalculation."
    )

    print_section(
        "Negative quantity investigation"
    )

    negative_cancelled = (
        negative_quantity
        & cancelled
    )

    negative_not_cancelled = (
        negative_quantity
        & ~cancelled
    )

    cancelled_not_negative = (
        cancelled
        & ~negative_quantity
    )

    print(
        "Negative quantity rows: "
        f"{negative_quantity.sum():,}"
    )

    print(
        "Negative quantity rows on C invoices: "
        f"{negative_cancelled.sum():,}"
    )

    print(
        "Negative quantity rows not on C invoices: "
        f"{negative_not_cancelled.sum():,}"
    )

    print(
        "Cancellation rows without negative quantity: "
        f"{cancelled_not_negative.sum():,}"
    )

    print_section(
        "Non-cancellation negative rows"
    )

    negative_non_cancel_rows = (
        transactions.loc[
            negative_not_cancelled,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    print(
        f"Rows: {len(negative_non_cancel_rows):,}"
    )

    print(
        "Zero-price rows: "
        f"{(negative_non_cancel_rows['Price'] == 0).sum():,}"
    )

    print(
        "Missing Customer ID: "
        f"{negative_non_cancel_rows['Customer ID'].isna().sum():,}"
    )

    print(
        "\nMost common descriptions:"
    )

    print(
        negative_non_cancel_rows[
            "Description"
        ]
        .value_counts(
            dropna=False
        )
        .head(30)
        .to_string()
    )

    print_section(
        "Cancellation rows without negative quantity"
    )

    print(
        transactions.loc[
            cancelled_not_negative,
            DISPLAY_COLUMNS,
        ]
        .to_string(
            index=False
        )
    )

    print_section(
        "Price anomaly investigation"
    )

    print(
        "Negative-price rows: "
        f"{negative_price.sum():,}"
    )

    if negative_price.any():
        print(
            "\nNegative-price records:"
        )

        print(
            transactions.loc[
                negative_price,
                DISPLAY_COLUMNS,
            ]
            .to_string(
                index=False
            )
        )

    print(
        "\nZero-price rows with Customer ID: "
        f"{(zero_price & ~missing_customer).sum():,}"
    )

    print(
        "Zero-price rows without Customer ID: "
        f"{(zero_price & missing_customer).sum():,}"
    )

    print_section(
        "Zero-price identifiable customer rows"
    )

    zero_price_identified = (
        zero_price
        & ~missing_customer
    )

    zero_price_identified_rows = (
        transactions.loc[
            zero_price_identified,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    print(
        f"Rows: {len(zero_price_identified_rows):,}"
    )

    print(
        "Unique invoices: "
        f"{zero_price_identified_rows['Invoice'].nunique():,}"
    )

    print(
        "Unique customers: "
        f"{zero_price_identified_rows['Customer ID'].nunique():,}"
    )

    print(
        "Positive quantities: "
        f"{(zero_price_identified_rows['Quantity'] > 0).sum():,}"
    )

    print(
        "Negative quantities: "
        f"{(zero_price_identified_rows['Quantity'] < 0).sum():,}"
    )

    print(
        "\nMost common StockCodes:"
    )

    print(
        zero_price_identified_rows[
            "StockCode"
        ]
        .value_counts(
            dropna=False
        )
        .head(20)
        .to_string()
    )

    print(
        "\nMost common descriptions:"
    )

    print(
        zero_price_identified_rows[
            "Description"
        ]
        .value_counts(
            dropna=False
        )
        .head(20)
        .to_string()
    )

    print_section(
        "Potential special or non-product StockCodes"
    )

    # Most ordinary merchandise codes use five digits with up to two trailing
    # letters. Codes outside that pattern are surfaced for investigation only;
    # they are not automatically classified as invalid or non-commercial.
    stock_code_text = (
        transactions["StockCode"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    standard_product_code = (
        stock_code_text
        .str.fullmatch(
            r"\d{5}[A-Z]{0,2}",
            na=False,
        )
    )

    special_code_rows = (
        transactions.loc[
            ~standard_product_code,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    special_code_rows[
        "line_value"
    ] = (
        special_code_rows["Quantity"]
        * special_code_rows["Price"]
    )

    special_code_summary = (
        special_code_rows
        .groupby(
            "StockCode",
            dropna=False,
        )
        .agg(
            rows=(
                "Invoice",
                "size",
            ),
            invoices=(
                "Invoice",
                "nunique",
            ),
            customers=(
                "Customer ID",
                "nunique",
            ),
            total_quantity=(
                "Quantity",
                "sum",
            ),
            total_line_value=(
                "line_value",
                "sum",
            ),
        )
        .sort_values(
            "rows",
            ascending=False,
        )
    )

    print(
        "Rows with candidate special StockCodes: "
        f"{len(special_code_rows):,}"
    )

    print(
        "Distinct candidate StockCodes: "
        f"{special_code_rows['StockCode'].nunique():,}"
    )

    print(
        "\nCandidate StockCode summary:"
    )

    print(
        special_code_summary
        .head(50)
        .to_string()
    )

    print(
        "\nMost common descriptions for "
        "candidate StockCodes:"
    )

    print(
        special_code_rows[
            "Description"
        ]
        .value_counts(
            dropna=False
        )
        .head(50)
        .to_string()
    )

    print(
        "\nCandidate StockCodes with their "
        "most common descriptions:"
    )

    special_code_descriptions = (
        special_code_rows
        .groupby(
            [
                "StockCode",
                "Description",
            ],
            dropna=False,
        )
        .size()
        .rename("rows")
        .reset_index()
        .sort_values(
            [
                "StockCode",
                "rows",
            ],
            ascending=[
                True,
                False,
            ],
        )
    )

    print(
        special_code_descriptions
        .to_string(
            index=False
        )
    )

    print_section(
        "Manual StockCode investigation"
    )

    # Manual entries are common and commercially material. They are profiled
    # separately because they may contain corrections, reallocations and other
    # financially relevant activity rather than ordinary merchandise sales.
    manual_code = (
        transactions["StockCode"]
        .astype("string")
        .str.strip()
        .str.upper()
        .eq("M")
    )

    manual_rows = (
        transactions.loc[
            manual_code,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    manual_rows[
        "line_value"
    ] = (
        manual_rows["Quantity"]
        * manual_rows["Price"]
    )

    manual_cancelled = (
        manual_rows["Invoice"]
        .astype("string")
        .str.startswith(
            "C",
            na=False,
        )
    )

    print(
        f"Rows: {len(manual_rows):,}"
    )

    print(
        "Unique invoices: "
        f"{manual_rows['Invoice'].nunique():,}"
    )

    print(
        "Unique customers: "
        f"{manual_rows['Customer ID'].nunique():,}"
    )

    print(
        "Missing Customer ID: "
        f"{manual_rows['Customer ID'].isna().sum():,}"
    )

    print(
        "Cancellation rows: "
        f"{manual_cancelled.sum():,}"
    )

    print(
        "Positive quantities: "
        f"{(manual_rows['Quantity'] > 0).sum():,}"
    )

    print(
        "Negative quantities: "
        f"{(manual_rows['Quantity'] < 0).sum():,}"
    )

    print(
        "Positive prices: "
        f"{(manual_rows['Price'] > 0).sum():,}"
    )

    print(
        "Zero prices: "
        f"{(manual_rows['Price'] == 0).sum():,}"
    )

    print(
        "Negative prices: "
        f"{(manual_rows['Price'] < 0).sum():,}"
    )

    print(
        "Net line value: "
        f"£{manual_rows['line_value'].sum():,.2f}"
    )

    print(
        "\nLargest manual rows by absolute "
        "line value:"
    )

    print(
        manual_rows
        .assign(
            abs_line_value=manual_rows[
                "line_value"
            ].abs()
        )
        .sort_values(
            "abs_line_value",
            ascending=False,
        )
        .drop(
            columns="abs_line_value"
        )
        .head(30)
        .to_string(
            index=False
        )
    )

    print_section(
        "Manual rows by cancellation and "
        "customer identification"
    )

    manual_rows[
        "is_cancellation"
    ] = (
        manual_rows["Invoice"]
        .astype("string")
        .str.startswith(
            "C",
            na=False,
        )
    )

    manual_rows[
        "customer_status"
    ] = (
        manual_rows["Customer ID"]
        .notna()
        .map(
            {
                True: "Identified customer",
                False: "Missing Customer ID",
            }
        )
    )

    manual_status_summary = (
        manual_rows
        .groupby(
            [
                "is_cancellation",
                "customer_status",
            ],
            dropna=False,
        )
        .agg(
            rows=(
                "Invoice",
                "size",
            ),
            invoices=(
                "Invoice",
                "nunique",
            ),
            customers=(
                "Customer ID",
                "nunique",
            ),
            total_quantity=(
                "Quantity",
                "sum",
            ),
            total_line_value=(
                "line_value",
                "sum",
            ),
        )
    )

    print(
        manual_status_summary
        .to_string()
    )

    print_section(
        "Manual value reversal patterns"
    )

    # Matching positive and negative records at the same price and absolute
    # quantity can reveal systematic correction activity. It is evidence of a
    # reversal pattern, not proof that every individual record forms a pair.
    manual_rows[
        "absolute_quantity"
    ] = manual_rows[
        "Quantity"
    ].abs()

    manual_reversal_summary = (
        manual_rows
        .groupby(
            [
                "Price",
                "absolute_quantity",
            ],
            dropna=False,
        )
        .agg(
            positive_rows=(
                "Quantity",
                lambda values:
                (values > 0).sum(),
            ),
            negative_rows=(
                "Quantity",
                lambda values:
                (values < 0).sum(),
            ),
            rows=(
                "Invoice",
                "size",
            ),
            total_line_value=(
                "line_value",
                "sum",
            ),
        )
        .reset_index()
    )

    manual_reversal_candidates = (
        manual_reversal_summary.loc[
            (
                manual_reversal_summary[
                    "positive_rows"
                ] > 0
            )
            & (
                manual_reversal_summary[
                    "negative_rows"
                ] > 0
            )
        ]
        .sort_values(
            [
                "rows",
                "Price",
            ],
            ascending=[
                False,
                False,
            ],
        )
    )

    print(
        "Price/quantity combinations appearing "
        "in both directions: "
        f"{len(manual_reversal_candidates):,}"
    )

    print(
        "\nMost frequent potential reversal "
        "combinations:"
    )

    print(
        manual_reversal_candidates
        .head(40)
        .to_string(
            index=False
        )
    )

    print_section(
        "Balanced manual reversal combinations"
    )

    # Perfectly balanced combinations are strong evidence that manual entries
    # are often used as reversals or corrections, although individual record
    # pairing would require additional transaction-level evidence.
    balanced_manual_combinations = (
        manual_reversal_candidates.loc[
            (
                manual_reversal_candidates[
                    "positive_rows"
                ]
                == manual_reversal_candidates[
                    "negative_rows"
                ]
            )
            & (
                manual_reversal_candidates[
                    "total_line_value"
                ].abs()
                < 0.01
            )
        ]
        .copy()
    )

    balanced_manual_rows = (
        balanced_manual_combinations[
            "rows"
        ]
        .sum()
    )

    print(
        "Perfectly balanced price/quantity "
        "combinations: "
        f"{len(balanced_manual_combinations):,}"
    )

    if len(manual_rows):
        balanced_manual_share = (
            balanced_manual_rows
            / len(manual_rows)
        )
    else:
        balanced_manual_share = float("nan")

    print(
        "Manual rows in those combinations: "
        f"{balanced_manual_rows:,} "
        f"({balanced_manual_share:.1%} "
        "of manual rows)"
    )

    print(
        "\nLargest perfectly balanced "
        "combinations by price:"
    )

    print(
        balanced_manual_combinations
        .sort_values(
            "Price",
            ascending=False,
        )
        .head(30)
        .to_string(
            index=False
        )
    )

    print_section(
        "Exact duplicate investigation"
    )

    # The source-sheet overlap has already been removed. Duplicate profiling
    # here therefore concerns repeated rows that remain within the retained
    # source records, which must be investigated separately before removal.
    duplicate_group_mask = (
        transactions.duplicated(
            keep=False
        )
    )

    duplicate_rows = (
        transactions.loc[
            duplicate_group_mask,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    duplicate_rows[
        "line_value"
    ] = (
        duplicate_rows["Quantity"]
        * duplicate_rows["Price"]
    )

    duplicate_groups = (
        transactions.loc[
            duplicate_group_mask
        ]
        .groupby(
            list(EXPECTED_COLUMNS),
            dropna=False,
        )
        .size()
        .rename("group_size")
        .reset_index()
        .sort_values(
            "group_size",
            ascending=False,
        )
    )

    rows_in_duplicate_groups = len(
        duplicate_rows
    )

    duplicate_group_count = len(
        duplicate_groups
    )

    excess_duplicate_rows = (
        rows_in_duplicate_groups
        - duplicate_group_count
    )

    print(
        "Rows belonging to duplicate groups: "
        f"{rows_in_duplicate_groups:,}"
    )

    print(
        "Distinct exact duplicate groups: "
        f"{duplicate_group_count:,}"
    )

    print(
        "Excess rows beyond one row per group: "
        f"{excess_duplicate_rows:,}"
    )

    if duplicate_group_count:
        largest_duplicate_group = (
            duplicate_groups[
                "group_size"
            ]
            .max()
        )
    else:
        largest_duplicate_group = 0

    print(
        "Largest exact duplicate group: "
        f"{largest_duplicate_group:,} rows"
    )

    print(
        "\nDuplicate group-size distribution:"
    )

    print(
        duplicate_groups[
            "group_size"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nLargest exact duplicate groups:"
    )

    print(
        duplicate_groups
        .head(30)
        .to_string(
            index=False
        )
    )

    print_section(
        "Duplicate timing investigation"
    )

    if len(duplicate_rows):
        duplicate_rows[
            "duplicate_date"
        ] = (
            duplicate_rows[
                "InvoiceDate"
            ]
            .dt.date
        )

        duplicate_by_date = (
            duplicate_rows
            .groupby(
                "duplicate_date"
            )
            .size()
            .rename("rows")
            .sort_values(
                ascending=False
            )
        )

        historical_overlap_start = (
            pd.Timestamp(
                "2010-12-01"
            )
        )

        historical_overlap_end = (
            pd.Timestamp(
                "2010-12-09 23:59:59"
            )
        )

        in_historical_overlap_period = (
            duplicate_rows[
                "InvoiceDate"
            ]
            .between(
                historical_overlap_start,
                historical_overlap_end,
            )
        )

        print(
            "Duplicate-group rows from "
            "1-9 Dec 2010 after source-overlap "
            "removal: "
            f"{in_historical_overlap_period.sum():,}"
        )

        print(
            "Share of remaining duplicate-group "
            "rows: "
            f"{in_historical_overlap_period.mean():.1%}"
        )

        print(
            "\nDates with the most remaining "
            "duplicate-group rows:"
        )

        print(
            duplicate_by_date
            .head(30)
            .to_string()
        )

    else:
        print(
            "No exact duplicate groups remain."
        )


    print_section(
        "Repeated product lines within invoices"
    )

    # Check whether the same StockCode can legitimately appear more than once
    # within an invoice with different quantities, prices or descriptions.
    # If so, repeated invoice/product combinations are part of the source
    # structure and exact duplicates need more careful treatment.
    invoice_product_counts = (
        transactions
        .groupby(
            [
                "Invoice",
                "StockCode",
            ],
            dropna=False,
        )
        .size()
        .rename("rows")
        .reset_index()
    )

    repeated_invoice_products = (
        invoice_product_counts.loc[
            invoice_product_counts["rows"] > 1
        ]
        .copy()
    )

    repeated_keys = transactions.merge(
        repeated_invoice_products[
            [
                "Invoice",
                "StockCode",
            ]
        ],
        on=[
            "Invoice",
            "StockCode",
        ],
        how="inner",
    )

    repeated_pattern_summary = (
        repeated_keys
        .groupby(
            [
                "Invoice",
                "StockCode",
            ],
            dropna=False,
        )
        .agg(
            rows=("InvoiceDate", "size"),
            distinct_quantities=("Quantity", "nunique"),
            distinct_prices=("Price", "nunique"),
            distinct_descriptions=("Description", "nunique"),
        )
        .reset_index()
    )

    varied_repeated_products = (
        repeated_pattern_summary.loc[
            (repeated_pattern_summary["distinct_quantities"] > 1)
            | (repeated_pattern_summary["distinct_prices"] > 1)
            | (repeated_pattern_summary["distinct_descriptions"] > 1)
        ]
    )

    print(
        "Invoice/StockCode combinations appearing more than once: "
        f"{len(repeated_invoice_products):,}"
    )

    print(
        "Repeated combinations with differing quantity, price "
        "or description: "
        f"{len(varied_repeated_products):,}"
    )

    print(
        "\nExamples of repeated products with differing line details:"
    )

    print(
        varied_repeated_products
        .sort_values(
            "rows",
            ascending=False,
        )
        .head(30)
        .to_string(index=False)
    )

    print_section(
        "Exact duplicate commercial impact"
    )

    # These are the rows that would actually disappear if we applied a simple
    # drop_duplicates() rule. Quantifying their customer and value impact lets
    # us judge the materiality of that assumption before making it.
    excess_duplicate = transactions.duplicated(
        keep="first"
    )

    excess_duplicate_rows = (
        transactions.loc[
            excess_duplicate,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    excess_duplicate_rows[
        "line_value"
    ] = (
        excess_duplicate_rows["Quantity"]
        * excess_duplicate_rows["Price"]
    )

    excess_positive_sale = (
        excess_duplicate
        & positive_sale
    )

    excess_positive_value = (
        line_value.loc[
            excess_positive_sale
        ]
        .sum()
    )

    if total_positive_value:
        excess_positive_value_share = (
            excess_positive_value
            / total_positive_value
        )
    else:
        excess_positive_value_share = float("nan")

    print(
        f"Excess exact duplicate rows: "
        f"{excess_duplicate.sum():,}"
    )

    print(
        "Affected invoices: "
        f"{transactions.loc[excess_duplicate, 'Invoice'].nunique():,}"
    )

    print(
        "Affected identifiable customers: "
        f"{transactions.loc[
            excess_duplicate & ~missing_customer,
            'Customer ID'
        ].nunique():,}"
    )

    print(
        "Rows with missing Customer ID: "
        f"{(excess_duplicate & missing_customer).sum():,}"
    )

    print(
        "Cancellation rows: "
        f"{(excess_duplicate & cancelled).sum():,}"
    )

    print(
        "Positive-sale rows: "
        f"{excess_positive_sale.sum():,}"
    )

    print(
        "Net line value of excess duplicate rows: "
        f"£{excess_duplicate_rows['line_value'].sum():,.2f}"
    )

    print(
        "Raw positive transaction value represented by "
        "excess duplicate rows: "
        f"£{excess_positive_value:,.2f}"
    )

    print(
        "Share of total raw positive transaction value: "
        f"{excess_positive_value_share:.2%}"
    )

    print_section(
        "Exact duplicate customer-level impact"
    )

    # Overall duplicate value is small, but customer segmentation can still be
    # distorted if that value is concentrated among particular customers.
    # Compare each customer's positive transaction value with the amount that
    # would disappear under a simple exact-duplicate removal rule.
    identified_positive_sale = (
        positive_sale
        & ~missing_customer
    )

    customer_positive_value = (
        transactions.loc[
            identified_positive_sale
        ]
        .assign(
            line_value=line_value.loc[
                identified_positive_sale
            ]
        )
        .groupby("Customer ID")["line_value"]
        .sum()
        .rename("positive_value")
    )

    customer_duplicate_value = (
        transactions.loc[
            excess_duplicate
            & identified_positive_sale
        ]
        .assign(
            duplicate_line_value=line_value.loc[
                excess_duplicate
                & identified_positive_sale
            ]
        )
        .groupby("Customer ID")["duplicate_line_value"]
        .sum()
        .rename("duplicate_positive_value")
    )

    customer_duplicate_impact = (
        customer_positive_value
        .to_frame()
        .join(
            customer_duplicate_value,
            how="left",
        )
        .fillna(
            {
                "duplicate_positive_value": 0
            }
        )
    )

    customer_duplicate_impact[
        "duplicate_value_share"
    ] = (
        customer_duplicate_impact[
            "duplicate_positive_value"
        ]
        / customer_duplicate_impact[
            "positive_value"
        ]
    )

    affected_customers = (
        customer_duplicate_impact.loc[
            customer_duplicate_impact[
                "duplicate_positive_value"
            ] > 0
        ]
        .copy()
    )

    print(
        f"Customers with positive duplicate value: "
        f"{len(affected_customers):,}"
    )

    print(
        "Median duplicate share among affected customers: "
        f"{affected_customers['duplicate_value_share'].median():.2%}"
    )

    print(
        "95th percentile duplicate share: "
        f"{affected_customers['duplicate_value_share'].quantile(0.95):.2%}"
    )

    print(
        "Maximum duplicate share: "
        f"{affected_customers['duplicate_value_share'].max():.2%}"
    )

    print(
        "Affected customers with duplicate share above 1%: "
        f"{(affected_customers['duplicate_value_share'] > 0.01).sum():,}"
    )

    print(
        "Affected customers with duplicate share above 5%: "
        f"{(affected_customers['duplicate_value_share'] > 0.05).sum():,}"
    )

    print(
        "Affected customers with duplicate share above 10%: "
        f"{(affected_customers['duplicate_value_share'] > 0.10).sum():,}"
    )

    print(
        "\nCustomers with the largest duplicate-value shares:"
    )

    print(
        affected_customers
        .sort_values(
            "duplicate_value_share",
            ascending=False,
        )
        .head(20)
        .to_string()
    )

    print_section(
        "Invoice-to-customer consistency"
    )

    # Customer-level analysis assumes that an invoice belongs to one customer.
    # Profile both conflicting Customer IDs and invoices that mix identified
    # and unidentified lines before relying on invoice-level measures.
    invoice_customer_profile = (
        transactions
        .groupby(
            "Invoice",
            dropna=False,
        )
        .agg(
            rows=(
                "Invoice",
                "size",
            ),
            identifiable_customers=(
                "Customer ID",
                "nunique",
            ),
            missing_customer_rows=(
                "Customer ID",
                lambda values:
                values.isna().sum(),
            ),
        )
    )

    multi_customer_invoices = (
        invoice_customer_profile.loc[
            invoice_customer_profile[
                "identifiable_customers"
            ] > 1
        ]
    )

    mixed_customer_id_invoices = (
        invoice_customer_profile.loc[
            (
                invoice_customer_profile[
                    "identifiable_customers"
                ] > 0
            )
            & (
                invoice_customer_profile[
                    "missing_customer_rows"
                ] > 0
            )
        ]
    )

    all_missing_customer_invoices = (
        invoice_customer_profile.loc[
            invoice_customer_profile[
                "identifiable_customers"
            ] == 0
        ]
    )

    print(
        "Total invoices: "
        f"{len(invoice_customer_profile):,}"
    )

    print(
        "Invoices linked to more than one "
        "identifiable customer: "
        f"{len(multi_customer_invoices):,}"
    )

    print(
        "Invoices containing both identified and "
        "missing Customer ID rows: "
        f"{len(mixed_customer_id_invoices):,}"
    )

    print(
        "Invoices with no identifiable customer: "
        f"{len(all_missing_customer_invoices):,}"
    )

    if len(multi_customer_invoices):
        print(
            "\nInvoices with the most identifiable customers:"
        )

        print(
            multi_customer_invoices
            .sort_values(
                "identifiable_customers",
                ascending=False,
            )
            .head(30)
            .to_string()
        )

    if len(mixed_customer_id_invoices):
        print(
            "\nExamples of invoices mixing identified "
            "and missing Customer IDs:"
        )

        print(
            mixed_customer_id_invoices
            .sort_values(
                "missing_customer_rows",
                ascending=False,
            )
            .head(30)
            .to_string()
        )


    print_section(
        "Customer-to-country consistency"
    )

    # A customer can plausibly transact from more than one country, but this
    # should be understood before Country is used as a customer attribute.
    identified_transactions = (
        transactions.loc[
            ~missing_customer
        ]
        .copy()
    )

    customer_country_counts = (
        identified_transactions
        .groupby(
            "Customer ID"
        )["Country"]
        .nunique()
    )

    multi_country_customers = (
        customer_country_counts.loc[
            customer_country_counts > 1
        ]
    )

    customer_country_examples = (
        identified_transactions
        .groupby(
            "Customer ID"
        )["Country"]
        .agg(
            lambda values:
            " | ".join(
                sorted(
                    set(
                        values
                        .dropna()
                        .astype(str)
                    )
                )
            )
        )
    )

    print(
        "Identifiable customers: "
        f"{len(customer_country_counts):,}"
    )

    print(
        "Customers associated with more than "
        "one country: "
        f"{len(multi_country_customers):,}"
    )

    if len(customer_country_counts):
        print(
            "Share of identifiable customers with "
            "multiple countries: "
            f"{len(multi_country_customers) / len(customer_country_counts):.2%}"
        )

    print(
        "\nCountry-count distribution by customer:"
    )

    print(
        customer_country_counts
        .value_counts()
        .sort_index()
        .to_string()
    )

    if len(multi_country_customers):
        multi_country_detail = (
            multi_country_customers
            .rename(
                "country_count"
            )
            .to_frame()
            .join(
                customer_country_examples.rename(
                    "countries"
                )
            )
        )

        print(
            "\nCustomers associated with the most countries:"
        )

        print(
            multi_country_detail
            .sort_values(
                "country_count",
                ascending=False,
            )
            .head(30)
            .to_string()
        )


    print_section(
        "StockCode-to-description consistency"
    )

    # Product breadth will rely primarily on StockCode rather than description.
    # Normalise case and surrounding whitespace for this diagnostic so that
    # trivial formatting differences do not look like distinct products.
    stock_description_rows = (
        transactions.loc[
            transactions[
                "Description"
            ].notna(),
            [
                "StockCode",
                "Description",
            ],
        ]
        .copy()
    )

    stock_description_rows[
        "stock_code_normalised"
    ] = (
        stock_description_rows[
            "StockCode"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    stock_description_rows[
        "description_normalised"
    ] = (
        stock_description_rows[
            "Description"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    description_counts = (
        stock_description_rows
        .groupby(
            "stock_code_normalised"
        )[
            "description_normalised"
        ]
        .nunique()
        .rename(
            "distinct_descriptions"
        )
    )

    inconsistent_descriptions = (
        description_counts.loc[
            description_counts > 1
        ]
    )

    description_examples = (
        stock_description_rows
        .groupby(
            "stock_code_normalised"
        )[
            "description_normalised"
        ]
        .agg(
            lambda values:
            " | ".join(
                sorted(
                    set(values)
                )[:5]
            )
        )
        .rename(
            "description_examples"
        )
    )

    print(
        "Normalised StockCodes with at least "
        "one description: "
        f"{len(description_counts):,}"
    )

    print(
        "StockCodes associated with more than "
        "one normalised description: "
        f"{len(inconsistent_descriptions):,}"
    )

    if len(description_counts):
        print(
            "Share of described StockCodes with "
            "multiple descriptions: "
            f"{len(inconsistent_descriptions) / len(description_counts):.2%}"
        )

    if len(inconsistent_descriptions):
        description_detail = (
            inconsistent_descriptions
            .to_frame()
            .join(
                description_examples
            )
        )

        print(
            "\nStockCodes with the most distinct descriptions:"
        )

        print(
            description_detail
            .sort_values(
                "distinct_descriptions",
                ascending=False,
            )
            .head(30)
            .to_string()
        )

    # Also check whether the same code appears with different casing or
    # surrounding whitespace, which may justify normalising StockCode before
    # customer product-breadth measures are calculated.
    stock_code_variants = (
        transactions[
            [
                "StockCode",
            ]
        ]
        .copy()
    )

    stock_code_variants[
        "stock_code_normalised"
    ] = (
        stock_code_variants[
            "StockCode"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    stock_code_variant_counts = (
        stock_code_variants
        .groupby(
            "stock_code_normalised"
        )[
            "StockCode"
        ]
        .nunique()
        .rename(
            "raw_variant_count"
        )
    )

    multiple_raw_variants = (
        stock_code_variant_counts.loc[
            stock_code_variant_counts > 1
        ]
    )

    raw_variant_examples = (
        stock_code_variants
        .groupby(
            "stock_code_normalised"
        )[
            "StockCode"
        ]
        .agg(
            lambda values:
            " | ".join(
                sorted(
                    {
                        str(value).strip()
                        for value
                        in values.dropna()
                    }
                )
            )
        )
        .rename(
            "raw_variants"
        )
    )

    print(
        "\nNormalised StockCodes represented by "
        "multiple raw code variants: "
        f"{len(multiple_raw_variants):,}"
    )

    if len(multiple_raw_variants):
        variant_detail = (
            multiple_raw_variants
            .to_frame()
            .join(
                raw_variant_examples
            )
        )

        print(
            "\nExamples of StockCode formatting variants:"
        )

        print(
            variant_detail
            .sort_values(
                "raw_variant_count",
                ascending=False,
            )
            .head(30)
            .to_string()
        )


    print_section(
        "Commercial transaction outliers"
    )

    # Extreme values are not assumed to be errors. Surface them so that later
    # segmentation choices can distinguish genuine high-value behaviour from
    # administrative records or unusual transactions.
    commercial_rows = (
        transactions.loc[
            positive_sale
            & ~missing_customer,
            DISPLAY_COLUMNS,
        ]
        .copy()
    )

    commercial_rows[
        "line_value"
    ] = (
        commercial_rows[
            "Quantity"
        ]
        * commercial_rows[
            "Price"
        ]
    )

    quantity_percentiles = (
        commercial_rows[
            "Quantity"
        ]
        .quantile(
            [
                0.50,
                0.95,
                0.99,
                0.999,
                1.00,
            ]
        )
    )

    line_value_percentiles = (
        commercial_rows[
            "line_value"
        ]
        .quantile(
            [
                0.50,
                0.95,
                0.99,
                0.999,
                1.00,
            ]
        )
    )

    print(
        "Identifiable positive-sale rows: "
        f"{len(commercial_rows):,}"
    )

    print(
        "\nPositive quantity percentiles:"
    )

    for percentile, label in [
        (0.50, "50th"),
        (0.95, "95th"),
        (0.99, "99th"),
        (0.999, "99.9th"),
        (1.00, "Maximum"),
    ]:
        print(
            f"{label}: "
            f"{quantity_percentiles.loc[percentile]:,.0f}"
        )

    print(
        "\nPositive line-value percentiles:"
    )

    for percentile, label in [
        (0.50, "50th"),
        (0.95, "95th"),
        (0.99, "99th"),
        (0.999, "99.9th"),
        (1.00, "Maximum"),
    ]:
        print(
            f"{label}: "
            f"£{line_value_percentiles.loc[percentile]:,.2f}"
        )

    print(
        "\nLargest identifiable positive-sale "
        "rows by line value:"
    )

    print(
        commercial_rows
        .sort_values(
            "line_value",
            ascending=False,
        )
        .head(30)
        .to_string(
            index=False
        )
    )

    print(
        "\nLargest identifiable positive-sale "
        "rows by quantity:"
    )

    print(
        commercial_rows
        .sort_values(
            "Quantity",
            ascending=False,
        )
        .head(30)
        .to_string(
            index=False
        )
    )


    print_section(
        "Raw behavioural and validation populations"
    )

    # Use half-open date ranges so all transactions on the final calendar day
    # are included without depending on a particular time-of-day precision.
    behavioural_start = pd.Timestamp(
        "2010-06-01"
    )

    validation_start = pd.Timestamp(
        "2011-06-01"
    )

    validation_end = pd.Timestamp(
        "2011-12-01"
    )

    behavioural_period = (
        (
            transactions[
                "InvoiceDate"
            ] >= behavioural_start
        )
        & (
            transactions[
                "InvoiceDate"
            ] < validation_start
        )
    )

    validation_period = (
        (
            transactions[
                "InvoiceDate"
            ] >= validation_start
        )
        & (
            transactions[
                "InvoiceDate"
            ] < validation_end
        )
    )

    behavioural_identified = (
        behavioural_period
        & ~missing_customer
    )

    validation_identified = (
        validation_period
        & ~missing_customer
    )

    behavioural_identified_positive = (
        behavioural_period
        & ~missing_customer
        & positive_sale
    )

    validation_identified_positive = (
        validation_period
        & ~missing_customer
        & positive_sale
    )

    behavioural_customers = set(
        transactions.loc[
            behavioural_identified,
            "Customer ID",
        ]
        .unique()
    )

    validation_customers = set(
        transactions.loc[
            validation_identified,
            "Customer ID",
        ]
        .unique()
    )

    behavioural_positive_customers = set(
        transactions.loc[
            behavioural_identified_positive,
            "Customer ID",
        ]
        .unique()
    )

    validation_positive_customers = set(
        transactions.loc[
            validation_identified_positive,
            "Customer ID",
        ]
        .unique()
    )

    returning_validation_customers = (
        behavioural_customers
        & validation_customers
    )

    validation_only_customers = (
        validation_customers
        - behavioural_customers
    )

    behavioural_missing_rows = int(
        (
            behavioural_period
            & missing_customer
        ).sum()
    )

    behavioural_rows = int(
        behavioural_period.sum()
    )

    behavioural_positive_value = (
        line_value.loc[
            behavioural_period
            & positive_sale
        ]
        .sum()
    )

    behavioural_missing_positive_value = (
        line_value.loc[
            behavioural_period
            & positive_sale
            & missing_customer
        ]
        .sum()
    )

    if behavioural_positive_value:
        behavioural_missing_value_share = (
            behavioural_missing_positive_value
            / behavioural_positive_value
        )
    else:
        behavioural_missing_value_share = float(
            "nan"
        )

    print(
        "Behavioural window: "
        "1 Jun 2010 to 31 May 2011"
    )

    print(
        "Raw transaction rows in behavioural window: "
        f"{behavioural_rows:,}"
    )

    print(
        "Rows without Customer ID in behavioural window: "
        f"{behavioural_missing_rows:,}"
    )

    if behavioural_rows:
        print(
            "Share of behavioural rows without "
            "Customer ID: "
            f"{behavioural_missing_rows / behavioural_rows:.1%}"
        )

    print(
        "Raw identifiable customers in behavioural window: "
        f"{len(behavioural_customers):,}"
    )

    print(
        "Identifiable customers with at least one "
        "positive-sale row in behavioural window: "
        f"{len(behavioural_positive_customers):,}"
    )

    print(
        "Raw positive transaction value without "
        "Customer ID in behavioural window: "
        f"£{behavioural_missing_positive_value:,.2f}"
    )

    print(
        "Share of behavioural raw positive value "
        "without Customer ID: "
        f"{behavioural_missing_value_share:.1%}"
    )

    print(
        "\nValidation window: "
        "1 Jun 2011 to 30 Nov 2011"
    )

    print(
        "Raw transaction rows in validation window: "
        f"{validation_period.sum():,}"
    )

    print(
        "Raw identifiable customers in validation window: "
        f"{len(validation_customers):,}"
    )

    print(
        "Identifiable customers with at least one "
        "positive-sale row in validation window: "
        f"{len(validation_positive_customers):,}"
    )

    print(
        "Behavioural-window customers also observed "
        "in validation window: "
        f"{len(returning_validation_customers):,}"
    )

    print(
        "Identifiable validation customers not observed "
        "in behavioural window: "
        f"{len(validation_only_customers):,}"
    )


    print_section(
        "Profiling phase checkpoint"
    )

    # This section collects the main raw-data diagnostics in one place. These
    # figures describe the source after removal of proven worksheet overlap but
    # before the final transaction-cleaning rules are applied.
    print(
        "Corrected source rows: "
        f"{len(transactions):,}"
    )

    print(
        "Proven overlapping source rows removed: "
        f"{overlap_summary['removed_later_overlap_rows']:,}"
    )

    print(
        "Remaining excess exact duplicate rows retained "
        "pending sensitivity analysis: "
        f"{transactions.duplicated().sum():,}"
    )

    print(
        "Rows without Customer ID: "
        f"{missing_customer.sum():,}"
    )

    print(
        "Negative quantity rows: "
        f"{negative_quantity.sum():,}"
    )

    print(
        "Zero-price rows: "
        f"{zero_price.sum():,}"
    )

    print(
        "Negative-price rows: "
        f"{negative_price.sum():,}"
    )

    print(
        "Cancellation rows: "
        f"{cancelled.sum():,}"
    )

    print(
        "Invoices linked to multiple identifiable customers: "
        f"{len(multi_customer_invoices):,}"
    )

    print(
        "Customers associated with multiple countries: "
        f"{len(multi_country_customers):,}"
    )

    print(
        "Normalised StockCodes with multiple "
        "descriptions: "
        f"{len(inconsistent_descriptions):,}"
    )

    print(
        "Raw identifiable behavioural-window customers: "
        f"{len(behavioural_customers):,}"
    )

    print(
        "Raw identifiable behavioural-window customers "
        "with positive-sale activity: "
        f"{len(behavioural_positive_customers):,}"
    )

    print(
        "\nProfiling is descriptive only. Final cleaning "
        "rules and the resulting analytical population "
        "should be documented and recalculated separately."
    )

if __name__ == "__main__":
    main()